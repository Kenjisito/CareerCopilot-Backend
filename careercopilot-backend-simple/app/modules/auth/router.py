from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.auth import service
from app.modules.auth.schemas import AuthResponse, LoginPayload, RegisterPayload

# Nota: el frontend todavía NO llama a estas rutas (login/register están
# mockeados en el código actual). Se dejan listas con el contrato exacto
# de frontend/types/user.ts para que conectar el frontend real sea solo
# reemplazar el setTimeout por un fetch a estos dos endpoints.
router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=AuthResponse, status_code=201)
def register(payload: RegisterPayload, db: Session = Depends(get_db)):
    token, user = service.register(db, payload)
    return AuthResponse(token=token, user=user)


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginPayload, db: Session = Depends(get_db)):
    token, user = service.login(db, payload)
    return AuthResponse(token=token, user=user)
