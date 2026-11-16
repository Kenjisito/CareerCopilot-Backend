from __future__ import annotations

import re
import unicodedata

SECTION_TEMPLATES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("contact", "CONTACTO", (
        "contacto", "datos de contacto", "informacion de contacto", "informacion personal",
        "datos personales", "contact information", "contact details", "personal details",
        "personal information", "contact info",
    )),
    ("summary", "PERFIL Y RESUMEN", (
        "perfil", "perfil profesional", "resumen", "resumen profesional", "extracto profesional",
        "perfil academico", "perfil laboral", "sobre mi", "acerca de mi", "objetivo profesional",
        "objetivo laboral", "objetivo", "presentacion", "declaracion profesional",
        "perfil ejecutivo", "perfil personal",
        "professional summary", "professional profile", "career summary", "career profile",
        "academic profile", "academic summary", "executive summary", "professional statement",
        "personal statement", "profile", "summary", "about me", "objective", "career objective",
    )),
    ("experience", "EXPERIENCIA LABORAL", (
        "experiencia", "experiencia laboral", "experiencia profesional", "experiencia relevante",
        "experiencia academica", "experiencia docente", "experiencia en docencia",
        "experiencia investigativa", "experiencia en investigacion", "experiencia de investigacion",
        "experiencia en practicas", "experiencia freelance", "historial laboral",
        "historial de empleo", "trayectoria", "trayectoria profesional", "empleos",
        "experiencia de trabajo", "experiencia de empleo", "practicas profesionales",
        "experiencia en la industria", "experiencia en el sector", "historial profesional",
        "pasantias", "docencia", "work experience", "professional experience",
        "academic experience", "teaching experience", "research experience",
        "industry experience", "internship experience", "freelance experience",
        "consulting experience", "relevant experience", "employment experience",
        "employment history", "employment record", "work history", "career history", "internships",
        "employment", "experience",
    )),
    ("education", "EDUCACION Y FORMACION", (
        "educacion", "formacion", "formacion academica", "educacion y formacion",
        "estudios", "estudios academicos", "historial educativo", "antecedentes academicos",
        "educacion superior", "academic background", "academic history", "education",
        "educational background", "education and training", "academic qualifications",
        "educational history", "academic credentials",
    )),
    ("skills", "HABILIDADES Y COMPETENCIAS", (
        "habilidad", "habilidades", "habilidades tecnicas", "competencia", "competencias",
        "competencias clave", "aptitud", "aptitudes", "conocimiento", "conocimientos",
        "conocimientos tecnicos", "tecnologias", "herramientas",
        "fortalezas", "capacidades", "areas de conocimiento", "stack", "stack tecnologico",
        "habilidades y competencias", "skills", "skill", "skill set", "skillset", "abilities",
        "technical skills", "soft skills",
        "hard skills", "interpersonal skills", "computer skills", "key skills", "core skills",
        "core competencies", "core competency", "professional competencies", "competencies", "competency",
        "competence", "professional skills", "technical competencies", "areas of expertise", "core qualifications",
        "proficiencies", "strengths", "tools and technologies", "knowledge and skills",
    )),
    ("certifications", "CERTIFICACIONES Y CURSOS", (
        "certificacion", "certificaciones", "certificado", "certificados", "cursos",
        "cursos y certificaciones", "certificaciones y cursos", "licencias", "credenciales",
        "formacion complementaria", "capacitaciones", "talleres", "seminarios",
        "certification", "certifications", "certificate", "certificates", "licenses",
        "credentials", "courses", "coursework", "workshops", "seminars",
        "professional development", "professional training", "continuing education",
    )),
    ("projects", "PROYECTOS", (
        "proyectos", "proyectos destacados", "proyectos relevantes", "proyectos personales",
        "portafolio", "portfolio", "projects", "selected projects", "personal projects",
    )),
    ("languages", "IDIOMAS", (
        "idiomas", "lenguas", "idiomas y nivel", "language", "languages", "language skills",
        "language proficiency",
    )),
    ("achievements", "LOGROS Y RECONOCIMIENTOS", (
        "logro", "logros", "logros destacados", "reconocimientos", "premios", "distinciones",
        "reconocimientos academicos", "honor", "honores", "achievement", "achievements",
        "accomplishment", "accomplishments", "awards", "honors and awards",
        "career achievements", "key accomplishments",
    )),
    ("volunteering", "VOLUNTARIADO", (
        "voluntariado", "experiencia voluntaria", "volunteer experience", "volunteer work", "volunteering",
    )),
    ("publications", "PUBLICACIONES", (
        "publicaciones", "investigaciones", "articulos", "articulos publicados",
        "publications", "papers", "research papers", "research and publications",
    )),
    ("interests", "INTERESES", (
        "intereses", "intereses personales", "hobbies", "interests", "interests and hobbies",
    )),
    ("references", "REFERENCIAS", (
        "referencias", "referencias laborales", "references", "professional references",
    )),
    ("other", "OTRA INFORMACION", (
        "otra informacion", "informacion adicional", "datos adicionales", "otros",
        "miscellaneous", "other information", "additional information", "additional details",
    )),
)

CV_FIELD_TEMPLATES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("headline", (
        "cargo objetivo", "puesto objetivo", "titulo profesional", "professional title",
        "desired position", "target role",
    )),
    ("professionalSummary", (
        "perfil", "perfil profesional", "perfil academico", "resumen", "objetivo",
        "professional profile", "academic profile", "professional summary", "about me",
    )),
    ("experiences.role", (
        "cargo", "puesto", "posicion", "titulo del puesto", "funcion", "job title",
        "position", "role", "designation",
    )),
    ("experiences.company", (
        "empresa", "empleador", "institucion", "organizacion", "cliente", "company",
        "employer", "organization", "institution", "client",
    )),
    ("experiences.startDate", (
        "fecha de inicio", "desde", "inicio", "start date", "from",
    )),
    ("experiences.endDate", (
        "fecha de termino", "fecha de fin", "hasta", "fin", "end date", "to", "through",
    )),
    ("experiences.isCurrent", (
        "actual", "presente", "hasta la fecha", "current", "present", "ongoing",
    )),
    ("experiences.experienceType", (
        "profesional", "academica", "practica", "pasantia", "voluntariado", "freelance",
        "professional", "academic", "internship", "volunteering",
    )),
    ("experiences.description", (
        "funciones", "responsabilidades", "tareas", "actividades", "duties",
        "responsibilities", "activities", "scope",
    )),
    ("experiences.achievements", (
        "logros", "resultados", "impacto", "metricas", "achievements", "results",
        "accomplishments", "impact", "metrics",
    )),
    ("skills", (
        "habilidades", "competencias", "aptitudes", "capacidades", "fortalezas",
        "conocimientos", "skills", "competencies", "expertise", "strengths",
    )),
)

_NON_WORD_RE = re.compile(r"[^a-z0-9]+")
_PREFIX_RE = re.compile(r"^\s*(?:[#>*•·▪\-–—]+\s*|\d{1,2}\s*[.)\-]\s*)+")


def normalize_heading(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii").lower()
    value = value.replace("&", " and ")
    return " ".join(_NON_WORD_RE.sub(" ", value).split())


_ALIAS_TO_CATEGORY = {
    normalize_heading(alias): category
    for category, _label, aliases in SECTION_TEMPLATES
    for alias in aliases
}
_TRAILING_QUALIFIER_RE = re.compile(r"\s*\([^)]*\)\s*$")


def build_field_mapping_guide() -> str:
    return "\n".join(
        f"- {field}: {', '.join(aliases)}."
        for field, aliases in CV_FIELD_TEMPLATES
    )


def _match_heading_candidate(value: str) -> str | None:
    normalized = normalize_heading(_PREFIX_RE.sub("", value).strip(" :;.!"))
    category = _ALIAS_TO_CATEGORY.get(normalized)
    if category:
        return category
    return _ALIAS_TO_CATEGORY.get(_TRAILING_QUALIFIER_RE.sub("", normalized).strip())


def _looks_like_unclassified_heading(line: str) -> bool:
    candidate = _PREFIX_RE.sub("", line.strip()).strip()
    if not candidate or len(candidate) > 80 or re.search(r"\d{4}", candidate):
        return False
    if candidate.endswith(":") and len(candidate.split()) <= 8:
        return True
    return (
        line.lstrip().startswith("#")
        or (
            candidate.isupper()
            and len(candidate.split()) <= 8
            and not any(separator in candidate for separator in ("|", ";", ","))
        )
    )


def identify_heading(line: str) -> tuple[str, str] | None:
    """Return canonical category and any same-line content after a recognized heading."""
    candidate = _PREFIX_RE.sub("", line.strip()).strip()
    if not candidate:
        return None

    category = _match_heading_candidate(candidate)
    if category:
        return category, ""

    for separator in (":", "|", "—", "–", " - ", "\t", " / "):
        if separator not in candidate:
            continue
        parts = candidate.split(separator, 1)
        category = _match_heading_candidate(parts[0])
        if category:
            return category, parts[1].strip()

    normalized_line = normalize_heading(candidate)
    if len(normalized_line.split()) <= 16:
        original_words = list(re.finditer(r"[^\W_]+", candidate, re.UNICODE))
        for alias, category in sorted(_ALIAS_TO_CATEGORY.items(), key=lambda item: len(item[0]), reverse=True):
            if not normalized_line.startswith(f"{alias} "):
                continue
            alias_word_count = len(alias.split())
            if alias_word_count >= len(original_words):
                continue
            remainder = candidate[original_words[alias_word_count].start():].strip(" :|—–-\t")
            return category, remainder

    if _looks_like_unclassified_heading(line):
        return "other", ""
    return None


def detect_section_categories(text: str) -> set[str]:
    categories = set()
    for line in text.splitlines():
        heading = identify_heading(line)
        if heading:
            categories.add(heading[0])
    return categories


def organize_cv_sections(text: str) -> str:
    """Group recognized headings under canonical labels without dropping source lines."""
    labels = {category: label for category, label, _aliases in SECTION_TEMPLATES}
    sections: dict[str, list[str]] = {"general": []}
    current = "general"

    for line in text.splitlines():
        match = identify_heading(line)
        if match:
            current, remainder = match
            sections.setdefault(current, [])
            original_heading = line.strip()
            if remainder:
                original_heading = original_heading.rsplit(remainder, 1)[0].rstrip(" :|—–-\t")
            sections[current].append(f"### {original_heading}")
            if remainder:
                sections[current].append(remainder)
        elif line.strip():
            sections.setdefault(current, []).append(line.strip())

    ordered_categories = ["general", *(category for category, _label, _aliases in SECTION_TEMPLATES)]
    blocks = []
    for category in ordered_categories:
        content = sections.get(category)
        if not content:
            continue
        label = "INFORMACION GENERAL" if category == "general" else labels[category]
        blocks.append(f"## {label}\n" + "\n".join(content))
    return "\n\n".join(blocks)


def split_text_chunks(text: str, max_chars: int) -> list[str]:
    """Split long text at line and word boundaries without discarding content."""
    if max_chars < 1:
        raise ValueError("max_chars debe ser mayor que cero")
    chunks: list[str] = []
    current = ""
    section_heading = ""
    for line in text.splitlines():
        line = line.rstrip()
        if not line:
            continue
        if line.startswith("## "):
            section_heading = line
            if current and len(current) + len(line) + 1 > max_chars:
                chunks.append(current)
                current = ""
            current = f"{current}\n{line}".strip()
            continue

        prefix = f"{section_heading}\n" if section_heading else ""
        if current and len(current) + len(line) + 1 <= max_chars:
            current = f"{current}\n{line}"
            continue
        if current:
            chunks.append(current)
            current = ""
        available_chars = max_chars - len(prefix)
        if len(line) <= available_chars:
            current = prefix + line
            continue

        parts = line.split()
        segment = ""
        for part in parts:
            if len(part) > available_chars:
                raise ValueError("Una palabra supera el tamaño máximo del bloque.")
            if segment and len(segment) + len(part) + 1 > available_chars:
                chunks.append(prefix + segment)
                segment = ""
            segment = f"{segment} {part}".strip()
        if segment:
            chunks.append(prefix + segment)
    if current:
        chunks.append(current)
    return chunks
