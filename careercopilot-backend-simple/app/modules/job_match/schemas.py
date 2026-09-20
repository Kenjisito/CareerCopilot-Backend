from pydantic import BaseModel, Field


class JobMatchPayload(BaseModel):
    nombre: str = Field(min_length=1)
    ofertaTexto: str = Field(min_length=20)


class JobMatchResult(BaseModel):
    id: str
    scoreCompatibilidad: int
    cumple: list[str]
    noCumple: list[str]
    resumen: str


class JobMatchAnalysis(BaseModel):
    score_compatibilidad: int = Field(ge=0, le=100)
    cumple: list[str]
    no_cumple: list[str]
    resumen: str
