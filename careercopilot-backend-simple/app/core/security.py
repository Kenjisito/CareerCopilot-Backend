"""
Seguridad: hashing de contraseñas + JWT propio.

Diseño importante: el frontend actual (login/register) está MOCKEADO —
no llama a ningún backend todavía, solo guarda un token falso en
localStorage. Para que el resto de los módulos (ATS, Job Match,
Entrevista), que SÍ están conectados de verdad, sigan funcionando hoy
mismo sin bloquear por auth, `get_current_user` es "suave": si no hay
token o es inválido, entrega un usuario anónimo en vez de fallar con 401.
Apenas el frontend conecte /auth/login y /auth/register de verdad, el
mismo código empieza a resolver el usuario real sin cambios.
"""
from datetime import datetime, timedelta
from typing import Optional

import jwt
from fastapi import Depends, Header
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import User
from app.db.session import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ANONYMOUS_USER_ID = "anonymous"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRES_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload.get("sub")
    except jwt.PyJWTError:
        return None


def get_current_user_id(
    authorization: str = Header(default=None),
) -> str:
    """Devuelve el user_id del token si es válido, o ANONYMOUS_USER_ID si no
    hay token o es inválido (ver nota de diseño arriba)."""
    if not authorization or not authorization.startswith("Bearer "):
        return ANONYMOUS_USER_ID

    token = authorization.removeprefix("Bearer ").strip()
    user_id = decode_access_token(token)
    return user_id or ANONYMOUS_USER_ID


def get_current_user(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Devuelve el objeto User si el token es válido y el usuario existe,
    o None si es anónimo. Los módulos que necesiten datos del usuario real
    (nombre, email) usan esta dependency; los que solo necesitan un id
    para agrupar datos (ATS, Interview) pueden usar get_current_user_id
    directamente, que nunca es None."""
    if user_id == ANONYMOUS_USER_ID:
        return None
    return db.query(User).filter(User.id == user_id).first()
