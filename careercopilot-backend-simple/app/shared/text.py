from __future__ import annotations
"""Utilidades de texto compartidas."""
import re

_TRUNCATION_NOTE = "\n[…texto recortado por longitud]"


def clip(text: str, limit: int) -> str:
    """Recorta `text` a `limit` caracteres sin cortar palabras.

    Se usa antes de enviar textos a la IA: el plan gratuito de Groq limita
    tokens por minuto, y un CV u oferta muy largos agotarían la cuota."""
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    space = cut.rfind(" ")
    if space > limit * 0.8:
        cut = cut[:space]
    return cut.rstrip() + _TRUNCATION_NOTE


def normalize_whitespace(text: str) -> str:
    """Colapsa espacios y deja como máximo una línea en blanco seguida."""
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\xa0", " ")
    text = re.sub(r"[ \t\f\v]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
