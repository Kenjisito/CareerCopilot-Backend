from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.ai_router import generate_json_response
from app.db.models import EntrevistaModel, JobMatchModel, MensajeModel
from app.modules.interview.prompts import build_first_question_prompt, build_next_question_prompt


class InterviewService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def iniciar_entrevista(self, user_id: UUID, job_match_id: UUID, tipo: str, seniority: str) -> tuple[EntrevistaModel, str]:
        match = await self.db.scalar(select(JobMatchModel).where(JobMatchModel.id == job_match_id, JobMatchModel.usuario_id == user_id))
        if match is None:
            raise HTTPException(status_code=404, detail="Job Match no encontrado")
        result = await generate_json_response("Genera una pregunta de entrevista en JSON con la clave respuesta.", build_first_question_prompt(match.nombre, tipo))
        first_message = result.get("respuesta") or result.get("question") or "Háblame de tu experiencia más relevante para este puesto."
        interview = EntrevistaModel(usuario_id=user_id, job_match_id=job_match_id, tipo=tipo, seniority_inferido=seniority)
        self.db.add(interview)
        await self.db.flush()
        self.db.add(MensajeModel(entrevista_id=interview.id, rol="asistente", contenido=first_message))
        await self.db.commit()
        await self.db.refresh(interview)
        return interview, first_message

    async def registrar_interaccion(self, user_id: UUID, entrevista_id: UUID, contenido: str) -> str:
        interview = await self.db.scalar(select(EntrevistaModel).options(selectinload(EntrevistaModel.job_match)).where(EntrevistaModel.id == entrevista_id, EntrevistaModel.usuario_id == user_id))
        if interview is None or interview.estado != "activa":
            raise HTTPException(status_code=404, detail="Entrevista activa no encontrada")
        result = await self.db.execute(select(MensajeModel).where(MensajeModel.entrevista_id == entrevista_id).order_by(MensajeModel.created_at))
        history = list(result.scalars())
        history_text = "\n".join(f"{message.rol}: {message.contenido}" for message in history)
        prompt = build_next_question_prompt(interview.job_match.nombre, interview.tipo, history_text + f"\nusuario: {contenido}")
        response = await generate_json_response("Mantén coherencia con la conversación y responde en JSON con la clave respuesta.", prompt)
        answer = response.get("respuesta") or response.get("feedback") or "Gracias por tu respuesta. ¿Puedes profundizar en el resultado obtenido?"
        self.db.add(MensajeModel(entrevista_id=entrevista_id, rol="usuario", contenido=contenido))
        self.db.add(MensajeModel(entrevista_id=entrevista_id, rol="asistente", contenido=answer))
        await self.db.commit()
        return answer

    async def finalizar_entrevista(self, user_id: UUID, entrevista_id: UUID) -> None:
        interview = await self.db.scalar(select(EntrevistaModel).where(EntrevistaModel.id == entrevista_id, EntrevistaModel.usuario_id == user_id))
        if interview is None:
            raise HTTPException(status_code=404, detail="Entrevista no encontrada")
        interview.estado = "finalizada"
        await self.db.commit()
