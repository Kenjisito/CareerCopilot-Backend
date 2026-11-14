from __future__ import annotations
from typing import Any

from pydantic import BaseModel, Field, HttpUrl, field_validator

MAX_OFFER_CHARS = 30000


class JobMatchPayload(BaseModel):
    nombre: str = Field(min_length=1, max_length=255)
    ofertaTexto: str = Field(min_length=20, max_length=MAX_OFFER_CHARS)

    @field_validator("nombre", "ofertaTexto")
    @classmethod
    def _strip(cls, value: str) -> str:
        return value.strip()


class JobMatchResult(BaseModel):
    id: str
    scoreCompatibilidad: int
    cumple: list[str]
    noCumple: list[str]
    resumen: str
    recomendaciones: list[str] = []


class JobExtractPayload(BaseModel):
    url: HttpUrl


class JobExtractResult(BaseModel):
    nombre: str
    empresa: str | None = None
    ofertaTexto: str
    fuente: str  # "datos-estructurados" | "ia"
    url: str


# --- Respuestas de la IA ------------------------------------------------------

def _str_list(value: Any, limit: int) -> list[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        if isinstance(item, dict):
            item = next((v for v in item.values() if isinstance(v, str)), "")
        text = str(item).strip(" -•\t\n")
        if text and text not in out:
            out.append(text)
    return out[:limit]


class JobMatchAnalysis(BaseModel):
    score_compatibilidad: int = Field(ge=0, le=100)
    cumple: list[str] = []
    no_cumple: list[str] = []
    resumen: str = Field(min_length=1)
    recomendaciones: list[str] = []

    @field_validator("score_compatibilidad", mode="before")
    @classmethod
    def _score(cls, value: Any) -> int:
        if isinstance(value, str):
            value = "".join(ch for ch in value if ch.isdigit() or ch == ".") or "0"
        return max(0, min(100, int(round(float(value)))))

    @field_validator("cumple", "no_cumple", mode="before")
    @classmethod
    def _requirements(cls, value: Any) -> list[str]:
        return _str_list(value, 15)

    @field_validator("recomendaciones", mode="before")
    @classmethod
    def _recs(cls, value: Any) -> list[str]:
        return _str_list(value, 6)


class JobOfferExtraction(BaseModel):
    es_oferta: bool
    nombre: str = ""
    empresa: str | None = None
    oferta_texto: str = ""
