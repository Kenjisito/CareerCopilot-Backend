from uuid import UUID

from pydantic import BaseModel, Field


class InterviewStartPayload(BaseModel):
    jobMatchId: UUID | None = None
    tipo: str = "mixta"
    seniority: str = "Senior"


class MessagePayload(BaseModel):
    contenido: str = Field(min_length=1, max_length=10000)


class InterviewStartResponse(BaseModel):
    entrevistaId: UUID
    respuesta: str


class MessageResponse(BaseModel):
    respuesta: str
