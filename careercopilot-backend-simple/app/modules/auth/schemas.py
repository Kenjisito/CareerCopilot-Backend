from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: EmailStr
    nombre_completo: str | None = None
    plan: str
    organization_id: UUID | None = None
    created_at: datetime
