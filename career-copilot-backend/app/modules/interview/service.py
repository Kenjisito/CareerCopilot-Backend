from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from supabase import AsyncClient

from app.core.ai_router import generate_structured
from app.core.config import settings
from app.modules.interview.prompts import (
    EVALUATION_SYSTEM_PROMPT,
    build_context,
    build_evaluation_prompt,
    build_first_turn_prompt,
    build_next_turn_prompt,
    interviewer_system_prompt,
)
from app.modules.interview.schemas import (
    AIEvaluation,
    CompetencyScore,
    InterviewerTurn,
    InterviewEvaluation,
    InterviewSessionOut,
    InterviewMessageOut,
    QuestionFeedback,
)
from app.shared.supabase_utils import first_row, response_rows
from app.shared.text import clip

ROLE_INTERVIEWER = "asistente"
ROLE_CANDIDATE = "usuario"

MAX_OFFER_CHARS = 2500
MAX_CV_CHARS = 2500
MAX_TRANSCRIPT_CHARS = 4000
MAX_EVAL_OFFER_CHARS = 2000
MAX_EVAL_TRANSCRIPT_CHARS = 9000

CLOSING_MESSAGE = (
    "Muchas gracias por tus respuestas, con esto terminamos la entrevista. "
    "Estoy preparando tu evaluación con puntaje y recomendaciones."
)
COMPETENCIES = ["Comunicación", "Conocimiento del puesto", "Ejemplos concretos (STAR)", "Motivación y encaje"]


def level_for(score: int) -> str:
    if score >= 85:
        return "Excelente"
    if score >= 70:
        return "Bueno"
    if score >= 50:
        return "Aceptable"
    return "Necesita mejorar"


def question_text(message: str) -> str:
    """La pregunta es el último párrafo del mensaje del entrevistador (antes va su reacción)."""
    paragraphs = [p.strip() for p in message.split("\n\n") if p.strip()]
    return paragraphs[-1] if paragraphs else message


def qa_pairs(messages: list[dict]) -> list[tuple[str, str]]:
    """(pregunta, respuesta) por cada respuesta del candidato."""
    pairs: list[tuple[str, str]] = []
    last_question = ""
    for message in messages:
        if message["rol"] == ROLE_INTERVIEWER:
            last_question = question_text(message["contenido"])
        elif message["rol"] == ROLE_CANDIDATE:
            pairs.append((last_question, message["contenido"]))
    return pairs


def _transcript(messages: list[tuple[str, str]], limit: int) -> str:
    """Transcripción legible. Si es muy larga se conservan los turnos más recientes."""
    lines = [f"{'Entrevistador' if rol == ROLE_INTERVIEWER else 'Candidato'}: {text}" for rol, text in messages]
    text = "\n\n".join(lines)
    if len(text) <= limit:
        return text
    return "[…inicio de la entrevista omitido]\n\n" + text[-limit:]


class InterviewService:
    def __init__(self, supabase: AsyncClient):
        self.supabase = supabase
        self.total = max(1, settings.INTERVIEW_QUESTIONS)

    async def _get_interview(self, user_id: UUID, entrevista_id: UUID) -> dict:
        response = await (
            self.supabase.table("entrevistas")
            .select("*")
            .eq("id", str(entrevista_id))
            .eq("usuario_id", str(user_id))
            .limit(1)
            .execute()
        )
        interview = first_row(response)
        if interview is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Entrevista no encontrada.",
            )

        match_response = await (
            self.supabase.table("job_matches")
            .select("*")
            .eq("id", interview["job_match_id"])
            .eq("usuario_id", str(user_id))
            .limit(1)
            .execute()
        )
        match = first_row(match_response)
        if match is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Entrevista no encontrada.",
            )

        cv_response = await (
            self.supabase.table("cvs")
            .select("parsed_text")
            .eq("id", match["cv_id"])
            .eq("usuario_id", str(user_id))
            .limit(1)
            .execute()
        )
        evaluation_response = await (
            self.supabase.table("entrevista_evaluaciones")
            .select("*")
            .eq("entrevista_id", str(entrevista_id))
            .limit(1)
            .execute()
        )
        return {
            "interview": interview,
            "match": match,
            "cv": first_row(cv_response),
            "evaluation": first_row(evaluation_response),
        }

    async def _messages(self, entrevista_id: UUID) -> list[dict]:
        response = await (
            self.supabase.table("mensajes")
            .select("*")
            .eq("entrevista_id", str(entrevista_id))
            .order("created_at")
            .order("id")
            .execute()
        )
        return response_rows(response)

    async def get_session(self, user_id: UUID, entrevista_id: UUID) -> InterviewSessionOut:
        bundle = await self._get_interview(user_id, entrevista_id)
        interview = bundle["interview"]
        evaluation = bundle["evaluation"]
        result = evaluation.get("resultado") or {} if evaluation else {}
        question_feedback = result.get("preguntas", [])
        feedback_by_answer = {
            index: item
            for index, item in enumerate(question_feedback)
            if isinstance(item, dict)
        }
        answer_index = 0
        output_messages = []
        for message in await self._messages(entrevista_id):
            is_candidate = message["rol"] == ROLE_CANDIDATE
            feedback = feedback_by_answer.get(answer_index) if is_candidate else None
            if is_candidate:
                answer_index += 1
            output_messages.append(InterviewMessageOut(
                id=message["id"],
                role="Candidate" if is_candidate else "Astro",
                content=message["contenido"],
                score=feedback.get("puntaje") if feedback else None,
                feedback=feedback.get("comentario") if feedback else None,
                createdAt=message["created_at"],
            ))
        return InterviewSessionOut(
            id=interview["id"],
            targetRole=bundle["match"]["nombre"],
            startedAt=interview["fecha_inicio"],
            completedAt=interview.get("fecha_fin"),
            score=evaluation["puntaje"] if evaluation else None,
            feedback=result.get("resumen") if evaluation else None,
            messages=output_messages,
        )

    @staticmethod
    def _next_timestamp(history: list[dict]) -> datetime:
        now = datetime.now(timezone.utc)
        if history:
            last_value = history[-1]["created_at"]
            last = datetime.fromisoformat(last_value.replace("Z", "+00:00")) if isinstance(last_value, str) else last_value
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            now = max(now, last + timedelta(milliseconds=1))
        return now

    @staticmethod
    def _context(match: dict, cv: dict | None) -> str:
        return build_context(
            match["nombre"],
            clip(match["oferta_texto"], MAX_OFFER_CHARS),
            clip(cv.get("parsed_text", "") if cv else "", MAX_CV_CHARS),
            list(match.get("no_cumple") or []),
        )

    async def iniciar_entrevista(
        self,
        user_id: UUID,
        plan: str,
        job_match_id: UUID,
        tipo: str,
        seniority: str,
    ) -> tuple[dict, str]:
        normalized_user_id = str(user_id)
        if plan != "premium":
            used_response = await (
                self.supabase.table("entrevistas")
                .select("id", count="exact")
                .eq("usuario_id", normalized_user_id)
                .execute()
            )
            if (used_response.count or 0) >= settings.FREE_INTERVIEW_LIMIT:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail=f"Alcanzaste el límite de {settings.FREE_INTERVIEW_LIMIT} entrevistas del plan gratuito.",
                )
        match_response = await (
            self.supabase.table("job_matches")
            .select("*")
            .eq("id", str(job_match_id))
            .eq("usuario_id", normalized_user_id)
            .limit(1)
            .execute()
        )
        match = first_row(match_response)
        if match is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job Match no encontrado.")
        cv_response = await (
            self.supabase.table("cvs")
            .select("parsed_text")
            .eq("id", match["cv_id"])
            .eq("usuario_id", normalized_user_id)
            .limit(1)
            .execute()
        )
        cv = first_row(cv_response)

        turn = await generate_structured(
            interviewer_system_prompt(tipo, seniority, self.total),
            build_first_turn_prompt(self._context(match, cv), self.total),
            InterviewerTurn,
            premium=plan == "premium",
            temperature=0.7,
            max_tokens=400,
        )
        first_message = turn.mensaje.strip()
        interview_id = str(uuid4())
        interview_response = await (
            self.supabase.table("entrevistas")
            .insert({
                "id": interview_id,
                "usuario_id": normalized_user_id,
                "job_match_id": str(job_match_id),
                "tipo": tipo,
                "seniority_inferido": seniority,
                "estado": "activa",
                "fecha_inicio": self._next_timestamp([]).isoformat(),
                "fecha_fin": None,
            })
            .select("*")
            .execute()
        )
        interview = first_row(interview_response)
        if interview is None:
            raise HTTPException(status_code=500, detail="No se pudo crear la entrevista.")
        try:
            await (
                self.supabase.table("mensajes")
                .insert({
                    "id": str(uuid4()),
                    "entrevista_id": interview_id,
                    "rol": ROLE_INTERVIEWER,
                    "contenido": first_message,
                    "created_at": self._next_timestamp([]).isoformat(),
                })
                .execute()
            )
        except Exception:
            await (
                self.supabase.table("entrevistas")
                .delete()
                .eq("id", interview_id)
                .eq("usuario_id", normalized_user_id)
                .execute()
            )
            raise
        return interview, first_message

    async def registrar_interaccion(
        self,
        user_id: UUID,
        plan: str,
        entrevista_id: UUID,
        contenido: str,
    ) -> tuple[str, bool, int]:
        """Guarda la respuesta del candidato y devuelve mensaje, estado y número actual."""
        bundle = await self._get_interview(user_id, entrevista_id)
        interview = bundle["interview"]
        if interview["estado"] != "activa":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Esta entrevista ya terminó. Inicia una nueva para seguir practicando.",
            )

        history = await self._messages(entrevista_id)
        answered = sum(1 for message in history if message["rol"] == ROLE_CANDIDATE) + 1
        asked = sum(1 for message in history if message["rol"] == ROLE_INTERVIEWER)

        if answered >= self.total:
            reply, finished, current = CLOSING_MESSAGE, True, self.total
        else:
            turns = [(message["rol"], message["contenido"]) for message in history]
            turns.append((ROLE_CANDIDATE, contenido))
            current = min(asked + 1, self.total)
            turn = await generate_structured(
                interviewer_system_prompt(interview["tipo"], interview.get("seniority_inferido") or "Junior", self.total),
                build_next_turn_prompt(
                    self._context(bundle["match"], bundle["cv"]),
                    _transcript(turns, MAX_TRANSCRIPT_CHARS),
                    current,
                    self.total,
                ),
                InterviewerTurn,
                premium=plan == "premium",
                temperature=0.7,
                max_tokens=400,
            )
            reply, finished = turn.mensaje.strip(), False

        answer_at = self._next_timestamp(history)
        created_messages = [
            {
                "id": str(uuid4()),
                "entrevista_id": str(entrevista_id),
                "rol": ROLE_CANDIDATE,
                "contenido": contenido,
                "created_at": answer_at.isoformat(),
            },
            {
                "id": str(uuid4()),
                "entrevista_id": str(entrevista_id),
                "rol": ROLE_INTERVIEWER,
                "contenido": reply,
                "created_at": (answer_at + timedelta(milliseconds=1)).isoformat(),
            },
        ]
        await self.supabase.table("mensajes").insert(created_messages).execute()
        if finished:
            try:
                await (
                    self.supabase.table("entrevistas")
                    .update({"estado": "respondida"})
                    .eq("id", str(entrevista_id))
                    .eq("usuario_id", str(user_id))
                    .execute()
                )
            except Exception:
                await (
                    self.supabase.table("mensajes")
                    .delete()
                    .in_("id", [message["id"] for message in created_messages])
                    .execute()
                )
                raise
        return reply, finished, current

    async def finalizar_entrevista(
        self,
        user_id: UUID,
        plan: str,
        entrevista_id: UUID,
    ) -> InterviewEvaluation:
        """Cierra la entrevista y genera (o devuelve) la evaluación final."""
        bundle = await self._get_interview(user_id, entrevista_id)
        interview = bundle["interview"]
        existing_evaluation = bundle["evaluation"]
        if existing_evaluation is not None:
            return InterviewEvaluation.model_validate(existing_evaluation["resultado"])

        pairs = qa_pairs(await self._messages(entrevista_id))
        if not pairs:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Responde al menos una pregunta para recibir tu evaluación.",
            )

        transcript = _transcript(
            [turn for question, answer in pairs for turn in ((ROLE_INTERVIEWER, question), (ROLE_CANDIDATE, answer))],
            MAX_EVAL_TRANSCRIPT_CHARS,
        )
        match = bundle["match"]
        ai = await generate_structured(
            EVALUATION_SYSTEM_PROMPT,
            build_evaluation_prompt(
                match["nombre"],
                clip(match["oferta_texto"], MAX_EVAL_OFFER_CHARS),
                interview.get("seniority_inferido") or "Junior",
                transcript,
                len(pairs),
            ),
            AIEvaluation,
            premium=plan == "premium",
            temperature=0.2,
            max_tokens=1800,
        )
        evaluation = self._build_evaluation(UUID(interview["id"]), pairs, ai)
        evaluation_id = str(uuid4())
        await (
            self.supabase.table("entrevista_evaluaciones")
            .insert({
                "id": evaluation_id,
                "entrevista_id": str(entrevista_id),
                "puntaje": evaluation.puntaje,
                "resultado": evaluation.model_dump(mode="json"),
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
            .execute()
        )
        try:
            await (
                self.supabase.table("entrevistas")
                .update({
                    "estado": "finalizada",
                    "fecha_fin": datetime.now(timezone.utc).isoformat(),
                })
                .eq("id", str(entrevista_id))
                .eq("usuario_id", str(user_id))
                .execute()
            )
        except Exception:
            await (
                self.supabase.table("entrevista_evaluaciones")
                .delete()
                .eq("id", evaluation_id)
                .eq("entrevista_id", str(entrevista_id))
                .execute()
            )
            raise
        return evaluation

    def _build_evaluation(
        self,
        entrevista_id: UUID,
        pairs: list[tuple[str, str]],
        ai: AIEvaluation,
    ) -> InterviewEvaluation:
        questions: list[QuestionFeedback] = []
        for index, (question, answer) in enumerate(pairs):
            item = ai.preguntas[index] if index < len(ai.preguntas) else None
            questions.append(QuestionFeedback(
                pregunta=question,
                respuesta=answer,
                puntaje=item.puntaje if item else ai.puntaje_general,
                comentario=(item.comentario if item else "") or "Sin comentario específico.",
                sugerencia=(item.sugerencia if item else "") or "",
            ))
        overall = round(sum(question.puntaje for question in questions) / len(questions)) if questions else ai.puntaje_general

        by_name = {competency.nombre.strip().lower(): competency.puntaje for competency in ai.competencias}
        competencies = [
            CompetencyScore(
                nombre=name,
                puntaje=by_name.get(
                    name.lower(),
                    ai.competencias[index].puntaje if index < len(ai.competencias) else overall,
                ),
            )
            for index, name in enumerate(COMPETENCIES)
        ]
        return InterviewEvaluation(
            entrevistaId=entrevista_id,
            puntaje=overall,
            nivel=level_for(overall),
            resumen=ai.resumen.strip(),
            preguntasRespondidas=len(pairs),
            totalPreguntas=self.total,
            competencias=competencies,
            preguntas=questions,
            fortalezas=ai.fortalezas,
            recomendaciones=ai.recomendaciones,
        )
