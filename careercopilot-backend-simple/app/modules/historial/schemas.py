from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class HistoryMatchOut(BaseModel):
    id: UUID
    nombre: str
    scoreCompatibilidad: int
    fecha: datetime


class HistoryMatchDetail(HistoryMatchOut):
    cumple: list
    noCumple: list
    ofertaTexto: str