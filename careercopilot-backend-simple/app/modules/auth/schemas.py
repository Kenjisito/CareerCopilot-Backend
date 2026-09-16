"""
Estos esquemas replican exactamente frontend/types/user.ts — campo por
campo — porque ese archivo ya es el contrato real, aunque hoy nada lo
llame todavía (login/register están mockeados con setTimeout).
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class LoginPayload(BaseModel):
    email: EmailStr
    password: Optional[str] = None


class RegisterPayload(BaseModel):
    fullName: str
    email: EmailStr
    password: Optional[str] = None


class UserOut(BaseModel):
    id: str
    email: str
    fullName: str
    avatarUrl: Optional[str] = None
    role: Optional[str] = None
    createdAt: datetime

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    token: str
    user: UserOut
