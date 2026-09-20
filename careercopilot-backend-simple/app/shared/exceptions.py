"""Alias de excepciones HTTP para mantener un nombre de modulo estable."""
from app.shared.errors import bad_request, conflict, not_found, unauthorized, upstream_ai_error

__all__ = ["bad_request", "conflict", "not_found", "unauthorized", "upstream_ai_error"]