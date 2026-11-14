from __future__ import annotations
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

InterviewType = Literal["mixta", "tecnica", "conductual"]
Seniority = Literal["Junior", "Semi-Senior", "Senior"]


class InterviewStartPayload(BaseModel):
    jobMatchId: UUID | None = None
    tipo: InterviewType = "mixta"
    seniority: Seniority = "Junior"


class MessagePayload(BaseModel):
    contenido: str = Field(min_length=1, max_length=10000)

    @field_validator("contenido")
    @classmethod
    def _strip(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("La respuesta no puede estar vacía.")
        return value


class InterviewStartResponse(BaseModel):
    entrevistaId: UUID
    respuesta: str
    preguntaActual: int = 1
    totalPreguntas: int


class MessageResponse(BaseModel):
    respuesta: str
    finalizada: bool = False  # True: se respondió la última pregunta → pedir la evaluación
    preguntaActual: int
    totalPreguntas: int


class CompetencyScore(BaseModel):
    nombre: str
    puntaje: int


class QuestionFeedback(BaseModel):
    pregunta: str
    respuesta: str
    puntaje: int
    comentario: str
    sugerencia: str


class InterviewEvaluation(BaseModel):
    entrevistaId: UUID
    puntaje: int
    nivel: str
    resumen: str
    preguntasRespondidas: int
    totalPreguntas: int
    competencias: list[CompetencyScore]
    preguntas: list[QuestionFeedback]
    fortalezas: list[str]
    recomendaciones: list[str]


# --- Respuestas de la IA ------------------------------------------------------

def _score(value: Any) -> int:
    if isinstance(value, str):
        value = "".join(ch for ch in value if ch.isdigit() or ch == ".") or "0"
    try:
        return max(0, min(100, int(round(float(value)))))
    except (TypeError, ValueError):
        return 0


def _str_list(value: Any, limit: int) -> list[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    out = [str(v.get("texto") if isinstance(v, dict) else v).strip(" -•\n") for v in value]
    return [v for v in out if v][:limit]


class InterviewerTurn(BaseModel):
    reaccion: str = ""
    pregunta: str = Field(min_length=2)

    @model_validator(mode="before")
    @classmethod
    def _compat(cls, data: Any) -> Any:
        # Tolera {"mensaje": "..."} (formato anterior o modelos que ignoran el esquema).
        if isinstance(data, dict) and not data.get("pregunta") and isinstance(data.get("mensaje"), str):
            return {**data, "pregunta": data["mensaje"]}
        return data

    @property
    def mensaje(self) -> str:
        """Texto que ve el candidato: reacción y pregunta en párrafos separados."""
        pregunta = " ".join(self.pregunta.split())
        reaccion = self.reaccion.strip()
        return f"{reaccion}\n\n{pregunta}" if reaccion else pregunta


class AIQuestionEval(BaseModel):
    puntaje: int = 0
    comentario: str = ""
    sugerencia: str = ""

    @field_validator("puntaje", mode="before")
    @classmethod
    def _clamp(cls, value: Any) -> int:
        return _score(value)


class AICompetency(BaseModel):
    nombre: str
    puntaje: int = 0

    @field_validator("puntaje", mode="before")
    @classmethod
    def _clamp(cls, value: Any) -> int:
        return _score(value)


class AIEvaluation(BaseModel):
    puntaje_general: int = 0
    resumen: str = Field(min_length=1)
    preguntas: list[AIQuestionEval]
    competencias: list[AICompetency] = []
    fortalezas: list[str] = []
    recomendaciones: list[str] = []

    @field_validator("puntaje_general", mode="before")
    @classmethod
    def _clamp(cls, value: Any) -> int:
        return _score(value)

    @field_validator("fortalezas", mode="before")
    @classmethod
    def _fortalezas(cls, value: Any) -> list[str]:
        return _str_list(value, 5)

    @field_validator("recomendaciones", mode="before")
    @classmethod
    def _recomendaciones(cls, value: Any) -> list[str]:
        return _str_list(value, 6)

    @field_validator("competencias", mode="before")
    @classmethod
    def _competencias(cls, value: Any) -> Any:
        if isinstance(value, dict):  # {"Comunicación": 70, ...}
            return [{"nombre": k, "puntaje": v} for k, v in value.items()]
        return value if isinstance(value, list) else []
