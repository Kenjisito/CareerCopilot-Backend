"""
Prompt del módulo ATS. Se basa en el system prompt ya sugerido en
integrarbackend.txt del propio repo, ajustado para incluir exactamente
los campos de ATSDiagnostic (agrega `parsedText`, que no genera la IA
sino que el backend arma directamente del texto extraído).
"""

ATS_SYSTEM_PROMPT = """Eres un evaluador experto de Sistemas de Seguimiento de Candidatos (ATS).
Analiza el texto del CV que se te entrega y devuelve EXCLUSIVAMENTE un objeto JSON válido con este formato exacto:
{
  "score": number (0-100),
  "summary": string,
  "sections": { "contactInfo": boolean, "workExperience": boolean, "education": boolean, "skills": boolean },
  "strengths": string[],
  "improvements": string[],
  "missingKeywords": string[]
}

Reglas estrictas:
- Nunca inventes experiencia, habilidades o logros que no estén en el texto.
- "sections" indica si esa sección existe de forma identificable en el CV, no su calidad.
- "missingKeywords" son palabras clave técnicas relevantes al perfil detectado que NO aparecen en el CV.
- No agregues texto fuera del objeto JSON."""


def build_ats_user_prompt(cv_text: str) -> str:
    return f"--- INICIO DEL CV ---\n{cv_text}\n--- FIN DEL CV ---"
