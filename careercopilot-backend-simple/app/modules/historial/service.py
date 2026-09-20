from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import JobMatchModel
from app.modules.historial.schemas import HistoryMatchDetail, HistoryMatchOut


def _summary(match: JobMatchModel) -> HistoryMatchOut:
    return HistoryMatchOut(id=match.id, nombre=match.nombre, scoreCompatibilidad=match.score_compatibilidad, fecha=match.fecha)


async def list_matches(db: AsyncSession, user_id: UUID) -> list[HistoryMatchOut]:
    result = await db.execute(select(JobMatchModel).where(JobMatchModel.usuario_id == user_id).order_by(JobMatchModel.fecha.desc()))
    return [_summary(match) for match in result.scalars()]


async def get_match(db: AsyncSession, user_id: UUID, match_id: UUID) -> HistoryMatchDetail:
    match = await db.scalar(select(JobMatchModel).where(JobMatchModel.id == match_id, JobMatchModel.usuario_id == user_id))
    if match is None:
        raise HTTPException(status_code=404, detail="Match no encontrado")
    return HistoryMatchDetail(id=match.id, nombre=match.nombre, scoreCompatibilidad=match.score_compatibilidad, fecha=match.fecha, cumple=match.cumple, noCumple=match.no_cumple, ofertaTexto=match.oferta_texto)


async def delete_match(db: AsyncSession, user_id: UUID, match_id: UUID) -> None:
    result = await db.execute(delete(JobMatchModel).where(JobMatchModel.id == match_id, JobMatchModel.usuario_id == user_id))
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Match no encontrado")
    await db.commit()
