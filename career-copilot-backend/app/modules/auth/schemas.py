from __future__ import annotations
from datetime import datetime
from uuid import UUID

from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class ProfileUpdate(BaseModel):
    nombre_completo: str = Field(min_length=2, max_length=200)

    @field_validator("nombre_completo")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("El nombre debe tener al menos 2 caracteres.")
        return v


class PlanUpdate(BaseModel):
    email: EmailStr
    plan: Literal["free", "premium"]


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: EmailStr
    nombre_completo: str | None = None
    plan: str
    organization_id: UUID | None = None
    created_at: datetime
