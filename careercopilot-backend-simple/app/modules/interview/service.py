from __future__ import annotations
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.ai_router import generate_structured
from app.core.config import settings
from app.db.models import EntrevistaModel, EvaluacionEntrevistaModel, JobMatchModel, MensajeModel
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
    QuestionFeedback,
)
from app.shared.text import clip

ROLE_INTERVIEWER = "asistente"
ROLE_CANDIDATE = "usuario"

# Límites de contexto: cada turno ≈ 3.000 tokens y la evaluación ≈ 5.000, dentro de los
# 8.000 tokens/minuto del plan gratuito de Groq (max_tokens también cuenta).
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


def qa_pairs(messages: list[MensajeModel]) -> list[tuple[str, str]]:
    """(pregunta, respuesta) por cada respuesta del candidato."""
    pairs: list[tuple[str, str]] = []
    last_question = ""
    for message in messages:
        if message.rol == ROLE_INTERVIEWER:
            last_question = question_text(message.contenido)
        elif message.rol == ROLE_CANDIDATE:
            pairs.append((last_question, message.contenido))
    return pairs


def _transcript(messages: list[tuple[str, str]], limit: int) -> str:
    """Transcripción legible. Si es muy larga se conservan los turnos más recientes."""
    lines = [f"{'Entrevistador' if rol == ROLE_INTERVIEWER else 'Candidato'}: {text}" for rol, text in messages]
    text = "\n\n".join(lines)
    if len(text) <= limit:
        return text
    return "[…inicio de la entrevista omitido]\n\n" + text[-limit:]


class InterviewService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.total = max(1, settings.INTERVIEW_QUESTIONS)

    # --- helpers ---------------------------------------------------------------

    async def _get_interview(self, user_id: UUID, entrevista_id: UUID) -> EntrevistaModel:
        interview = await self.db.scalar(
            select(EntrevistaModel)
            .options(
                selectinload(EntrevistaModel.job_match).selectinload(JobMatchModel.cv),
                selectinload(EntrevistaModel.evaluacion),
            )
            .where(EntrevistaModel.id == entrevista_id, EntrevistaModel.usuario_id == user_id)
        )
        if interview is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entrevista no encontrada.")
        return interview

    async def _messages(self, entrevista_id: UUID) -> list[MensajeModel]:
        result = await self.db.execute(
            select(MensajeModel).where(MensajeModel.entrevista_id == entrevista_id).order_by(MensajeModel.created_at, MensajeModel.id)
        )
        return list(result.scalars())

    @staticmethod
    def _next_timestamp(history: list[MensajeModel]) -> datetime:
        now = datetime.now(timezone.utc)
        if history:
            last = history[-1].created_at
            if last.tzinfo is None:  # SQLite devuelve fechas sin zona horaria
                last = last.replace(tzinfo=timezone.utc)
            now = max(now, last + timedelta(milliseconds=1))
        return now

    @staticmethod
    def _context(match: JobMatchModel) -> str:
        return build_context(
            match.nombre,
            clip(match.oferta_texto, MAX_OFFER_CHARS),
            clip(match.cv.parsed_text if match.cv else "", MAX_CV_CHARS),
            list(match.no_cumple or []),
        )

    # --- casos de uso ----------------------------------------------------------

    async def iniciar_entrevista(self, user_id: UUID, plan: str, job_match_id: UUID, tipo: str, seniority: str) -> tuple[EntrevistaModel, str]:
        if plan != "premium":
            used = await self.db.scalar(select(func.count(EntrevistaModel.id)).where(EntrevistaModel.usuario_id == user_id))
            if (used or 0) >= settings.FREE_INTERVIEW_LIMIT:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail=f"Alcanzaste el límite de {settings.FREE_INTERVIEW_LIMIT} entrevistas del plan gratuito.",
                )
        match = await self.db.scalar(
            select(JobMatchModel)
            .options(selectinload(JobMatchModel.cv))
            .where(JobMatchModel.id == job_match_id, JobMatchModel.usuario_id == user_id)
        )
        if match is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job Match no encontrado.")

        turn = await generate_structured(
            interviewer_system_prompt(tipo, seniority, self.total),
            build_first_turn_prompt(self._context(match), self.total),
            InterviewerTurn,
            premium=plan == "premium",
            temperature=0.7,
            max_tokens=400,
        )
        first_message = turn.mensaje.strip()
        interview = EntrevistaModel(usuario_id=user_id, job_match_id=job_match_id, tipo=tipo, seniority_inferido=seniority)
        self.db.add(interview)
        await self.db.flush()
        self.db.add(MensajeModel(entrevista_id=interview.id, rol=ROLE_INTERVIEWER, contenido=first_message, created_at=self._next_timestamp([])))
        await self.db.commit()
        await self.db.refresh(interview)
        return interview, first_message

    async def registrar_interaccion(self, user_id: UUID, plan: str, entrevista_id: UUID, contenido: str) -> tuple[str, bool, int]:
        """Guarda la respuesta del candidato y devuelve (mensaje del entrevistador,
        finalizada, número de la pregunta actual)."""
        interview = await self._get_interview(user_id, entrevista_id)
        if interview.estado != "activa":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Esta entrevista ya terminó. Inicia una nueva para seguir practicando.")

        history = await self._messages(entrevista_id)
        answered = sum(1 for m in history if m.rol == ROLE_CANDIDATE) + 1
        asked = sum(1 for m in history if m.rol == ROLE_INTERVIEWER)

        if answered >= self.total:
            reply, finished, current = CLOSING_MESSAGE, True, self.total
        else:
            turns = [(m.rol, m.contenido) for m in history] + [(ROLE_CANDIDATE, contenido)]
            current = min(asked + 1, self.total)
            turn = await generate_structured(
                interviewer_system_prompt(interview.tipo, interview.seniority_inferido or "Junior", self.total),
                build_next_turn_prompt(self._context(interview.job_match), _transcript(turns, MAX_TRANSCRIPT_CHARS), current, self.total),
                InterviewerTurn,
                premium=plan == "premium",
                temperature=0.7,
                max_tokens=400,
            )
            reply, finished = turn.mensaje.strip(), False

        # Marcas de tiempo explícitas y estrictamente crecientes: el orden de la conversación
        # no puede depender de la resolución del reloj (dos filas con la misma hora se desordenan).
        answer_at = self._next_timestamp(history)
        self.db.add(MensajeModel(entrevista_id=entrevista_id, rol=ROLE_CANDIDATE, contenido=contenido, created_at=answer_at))
        self.db.add(MensajeModel(entrevista_id=entrevista_id, rol=ROLE_INTERVIEWER, contenido=reply, created_at=answer_at + timedelta(milliseconds=1)))
        if finished:
            interview.estado = "respondida"  # no admite más mensajes; falta la evaluación
        await self.db.commit()
        return reply, finished, current

    async def finalizar_entrevista(self, user_id: UUID, plan: str, entrevista_id: UUID) -> InterviewEvaluation:
        """Cierra la entrevista y genera (o devuelve, si ya existe) la evaluación final."""
        interview = await self._get_interview(user_id, entrevista_id)
        if interview.evaluacion is not None:
            return InterviewEvaluation.model_validate(interview.evaluacion.resultado)

        messages = await self._messages(entrevista_id)
        pairs = qa_pairs(messages)
        if not pairs:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Responde al menos una pregunta para recibir tu evaluación.",
            )

        transcript = _transcript(
            [turn for q, a in pairs for turn in ((ROLE_INTERVIEWER, q), (ROLE_CANDIDATE, a))],
            MAX_EVAL_TRANSCRIPT_CHARS,
        )
        match = interview.job_match
        ai = await generate_structured(
            EVALUATION_SYSTEM_PROMPT,
            build_evaluation_prompt(match.nombre, clip(match.oferta_texto, MAX_EVAL_OFFER_CHARS), interview.seniority_inferido or "Junior", transcript, len(pairs)),
            AIEvaluation,
            premium=plan == "premium",
            temperature=0.2,
            max_tokens=1800,
        )
        evaluation = self._build_evaluation(interview.id, pairs, ai)

        interview.estado = "finalizada"
        interview.fecha_fin = datetime.now(timezone.utc)
        self.db.add(EvaluacionEntrevistaModel(entrevista_id=interview.id, puntaje=evaluation.puntaje, resultado=evaluation.model_dump(mode="json")))
        await self.db.commit()
        return evaluation

    def _build_evaluation(self, entrevista_id: UUID, pairs: list[tuple[str, str]], ai: AIEvaluation) -> InterviewEvaluation:
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
        # El puntaje global es el promedio de las respuestas: transparente y coherente con el detalle.
        overall = round(sum(q.puntaje for q in questions) / len(questions)) if questions else ai.puntaje_general

        by_name = {c.nombre.strip().lower(): c.puntaje for c in ai.competencias}
        competencies = [
            CompetencyScore(nombre=name, puntaje=by_name.get(name.lower(), ai.competencias[i].puntaje if i < len(ai.competencias) else overall))
            for i, name in enumerate(COMPETENCIES)
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
