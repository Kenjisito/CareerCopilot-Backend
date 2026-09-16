INTERVIEW_QUESTION_SYSTEM_PROMPT = """Eres un entrevistador técnico que genera UNA pregunta de entrevista.
Devuelve EXCLUSIVAMENTE un objeto JSON con este formato exacto:
{
  "category": "technical" | "behavioral" | "situational",
  "question": string,
  "contextOrTips": string | null
}
Si la categoría solicitada es "mixed", elige la categoría más apropiada para esta pregunta puntual.
No agregues texto fuera del objeto JSON."""


def build_first_question_prompt(job_title: str, category: str) -> str:
    return (
        f"Cargo: {job_title}\n"
        f"Categoría de entrevista solicitada: {category}\n"
        f"Genera la primera pregunta de la entrevista."
    )


def build_next_question_prompt(job_title: str, category: str, history: str) -> str:
    return (
        f"Cargo: {job_title}\n"
        f"Categoría de entrevista solicitada: {category}\n"
        f"Preguntas y respuestas anteriores en esta sesión:\n{history}\n\n"
        f"Genera la siguiente pregunta, evitando repetir temas ya cubiertos."
    )


FEEDBACK_SYSTEM_PROMPT = """Eres un entrevistador técnico senior evaluando la respuesta de un candidato
con la metodología STAR (Situación, Tarea, Acción, Resultado).
Devuelve EXCLUSIVAMENTE un objeto JSON con este formato exacto:
{
  "score": number (0-100),
  "strengths": string[],
  "areasForImprovement": string[],
  "suggestedAnswer": string
}
Reglas:
- Evalúa solo lo que el candidato realmente dijo, sin inventar contexto.
- "suggestedAnswer" es un ejemplo breve de cómo mejorar la respuesta, no una respuesta genérica.
- No agregues texto fuera del objeto JSON."""


def build_feedback_prompt(question: str, answer: str) -> str:
    return f"Pregunta: {question}\n\nRespuesta del candidato: {answer}"
