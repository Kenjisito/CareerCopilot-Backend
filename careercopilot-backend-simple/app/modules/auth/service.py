from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.db.models import User
from app.modules.auth.schemas import LoginPayload, RegisterPayload, UserOut
from app.shared.errors import conflict, unauthorized


def _to_user_out(user: User) -> UserOut:
    """Traduce el modelo ORM (snake_case) al schema que espera el frontend
    (camelCase, ver frontend/types/user.ts)."""
    return UserOut(
        id=user.id,
        email=user.email,
        fullName=user.full_name,
        avatarUrl=user.avatar_url,
        role=user.role,
        createdAt=user.created_at,
    )


def register(db: Session, payload: RegisterPayload) -> tuple[str, UserOut]:
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise conflict("Ya existe una cuenta con ese correo")

    if not payload.password:
        raise conflict("La contraseña es requerida para registrarse")

    user = User(
        email=payload.email,
        full_name=payload.fullName,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id)
    return token, _to_user_out(user)


def login(db: Session, payload: LoginPayload) -> tuple[str, UserOut]:
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not payload.password or not verify_password(payload.password, user.password_hash):
        raise unauthorized("Correo o contraseña incorrectos")

    token = create_access_token(user.id)
    return token, _to_user_out(user)
