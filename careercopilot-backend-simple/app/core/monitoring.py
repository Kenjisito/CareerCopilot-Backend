"""Logging centralizado y punto de integracion opcional con Sentry."""
import logging

from app.core.config import settings


def configure_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


logger = logging.getLogger("careercopilot")


def capture_exception(error: Exception) -> None:
    """Registra el error; Sentry puede conectarse sin hacerlo obligatorio."""
    logger.exception("Unhandled application error", exc_info=error)