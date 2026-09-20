from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import UsuarioModel
from app.db.session import get_db
from app.modules.auth.schemas import UserResponse
from app.modules.auth.service import AuthService
from app.shared.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.get("/me", response_model=UserResponse)
async def get_my_profile(user: UsuarioModel = Depends(get_current_user)):
    return user


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_account(user: UsuarioModel = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await AuthService(db).delete_user_completely(user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
