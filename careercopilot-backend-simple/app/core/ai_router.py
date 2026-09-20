"""Capa unica para seleccionar el proveedor/modelo de IA."""
from typing import Any

from app.core.config import settings
from app.shared.ai_client import generate_json


async def generate_json_response(system_prompt: str, user_prompt: str, *, premium: bool = False) -> dict[str, Any]:
    """Genera una respuesta usando el modelo configurado para el plan."""
    model = settings.AI_PREMIUM_MODEL if premium else settings.OPENAI_MODEL
    return await generate_json(system_prompt, user_prompt, model=model)