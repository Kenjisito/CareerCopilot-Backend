from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import UsuarioModel
from app.db.session import get_db
from app.modules.email.schemas import EmailGeneratePayload, EmailOut, EmailUpdatePayload
from app.modules.email.service import create_email, update_email
from app.shared.dependencies import get_current_user

router = APIRouter(prefix="/email", tags=["Email"])


@router.post("/generate", response_model=EmailOut, status_code=201)
async def generate(payload: EmailGeneratePayload, user: UsuarioModel = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await create_email(db, user.id, payload)


@router.put("/{email_id}", response_model=EmailOut)
async def update(email_id: UUID, payload: EmailUpdatePayload, user: UsuarioModel = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await update_email(db, user.id, email_id, payload)
