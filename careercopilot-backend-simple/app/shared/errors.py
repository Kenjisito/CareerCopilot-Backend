"""
El apiClient del frontend (lib/api-client.ts) espera, cuando la respuesta
no es ok:
    errorData.detail || errorData.message || `API Error: ${status}`
FastAPI ya devuelve {"detail": "..."} por defecto en sus HTTPException,
así que basta con usar HTTPException normalmente en los routers — no se
necesita un formato de error custom. Este archivo centraliza mensajes
reutilizables para no repetir strings sueltos en cada módulo.
"""
from fastapi import HTTPException, status


def not_found(detail: str = "Recurso no encontrado") -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def unauthorized(detail: str = "Credenciales inválidas") -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


def conflict(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


def upstream_ai_error(detail: str = "El servicio de IA no está disponible, intenta de nuevo") -> HTTPException:
    return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)
