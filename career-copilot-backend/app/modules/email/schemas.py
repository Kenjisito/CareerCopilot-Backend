from __future__ import annotations
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class EmailGeneratePayload(BaseModel):
    jobMatchId: UUID
    recipientName: str | None = None
    tone: str = "professional"


class EmailUpdatePayload(BaseModel):
    subject: str | None = None
    body: str | None = None


class EmailOut(BaseModel):
    id: UUID
    subject: str
    body: str
    jobMatchId: UUID | None
    tone: str
    createdAt: datetime
