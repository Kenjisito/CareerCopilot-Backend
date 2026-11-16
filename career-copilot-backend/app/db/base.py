from __future__ import annotations
"""Base declarativa publica para modelos SQLAlchemy."""
from app.db.session import Base

from app.db import models  # noqa: F401,E402

__all__ = ["Base"]