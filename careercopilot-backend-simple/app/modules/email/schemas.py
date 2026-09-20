from uuid import UUID
from pydantic import BaseModel, ConfigDict


class EmailGeneratePayload(BaseModel):
    jobMatchId: UUID
    recipientName: str | None = None
    tone: str = "professional"


class EmailUpdatePayload(BaseModel):
    subject: str | None = None
    body: str | None = None


class EmailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    subject: str
    body: str
