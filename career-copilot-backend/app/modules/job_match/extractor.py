from __future__ import annotations
"""
Extracción de una oferta laboral desde la URL de cualquier portal.

Estrategia (de más a menos confiable):
1. Datos estructurados schema.org `JobPosting` (JSON-LD). Los publican casi
   todos los portales para aparecer en Google Empleos: LinkedIn (vista
   pública), Indeed, Computrabajo, Laborum, GetOnBoard, Bumeran, Trabajando,
   Greenhouse, Lever, Workday, etc. → sin gastar IA.
2. Si no hay JSON-LD: se toma el texto visible de la página y la IA aísla
   la oferta (título, empresa y contenido limpio).

Seguridad (SSRF): solo http/https, puertos estándar, y cada salto de
redirección se valida para que no apunte a IPs privadas, locales o de la
red interna del servidor.
"""
import asyncio
import ipaddress
import json
import logging
import re
import socket
from typing import Any
from urllib.parse import parse_qs, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from fastapi import HTTPException, status

from app.core.ai_router import generate_structured
from app.modules.job_match.prompts import JOB_EXTRACT_SYSTEM_PROMPT, build_job_extract_user_prompt
from app.modules.job_match.schemas import JobExtractResult, JobOfferExtraction
from app.shared.text import clip, normalize_whitespace

logger = logging.getLogger(__name__)

MAX_BYTES = 4 * 1024 * 1024
MAX_REDIRECTS = 5
MIN_OFFER_CHARS = 120
MAX_PAGE_CHARS_FOR_AI = 9000  # ≈ 2.500 tokens + respuesta: cabe en el límite por minuto de Groq
MAX_OFFER_CHARS = 15000
TIMEOUT = httpx.Timeout(15.0, connect=8.0)
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-CL,es;q=0.9,en;q=0.7",
}


def _unprocessable(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)


PASTE_HINT = "Copia el texto de la oferta y pégalo en el campo de requisitos."


# --- Validación de URL --------------------------------------------------------

def normalize_job_url(url: str) -> str:
    """Convierte URLs de búsqueda de LinkedIn (…?currentJobId=123) en la
    vista pública de la oferta, que sí trae los datos estructurados."""
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host.endswith("linkedin.com"):
        job_id = parse_qs(parsed.query).get("currentJobId", [None])[0]
        match = re.search(r"/jobs/view/(?:[^/]*?-)?(\d+)", parsed.path)
        job_id = job_id or (match.group(1) if match else None)
        if job_id and job_id.isdigit():
            return f"https://www.linkedin.com/jobs/view/{job_id}/"
    return url


async def _assert_public_host(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise _unprocessable("La URL debe empezar con http:// o https://.")
    if parsed.port not in (None, 80, 443):
        raise _unprocessable("La URL usa un puerto no permitido.")
    try:
        infos = await asyncio.get_running_loop().getaddrinfo(parsed.hostname, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise _unprocessable("No encontramos ese sitio. Revisa que la URL esté bien escrita.") from exc
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global:
            raise _unprocessable("Esa URL no apunta a un sitio público.")


async def fetch_html(url: str) -> tuple[str, str]:
    """Descarga la página validando cada redirección. Devuelve (url_final, html)."""
    current = url
    async with httpx.AsyncClient(headers=HEADERS, timeout=TIMEOUT, follow_redirects=False) as client:
        for _ in range(MAX_REDIRECTS + 1):
            await _assert_public_host(current)
            try:
                async with client.stream("GET", current) as response:
                    if response.is_redirect:
                        location = response.headers.get("location")
                        if not location:
                            break
                        current = urljoin(current, location)
                        continue
                    if response.status_code in (401, 403, 999) or "authwall" in str(response.url):
                        raise _unprocessable(f"Ese sitio no permite leer la oferta sin iniciar sesión. {PASTE_HINT}")
                    if response.status_code == 404:
                        raise _unprocessable("La oferta no existe o ya fue cerrada (error 404).")
                    if response.status_code >= 400:
                        raise _unprocessable(f"El sitio respondió con un error ({response.status_code}). {PASTE_HINT}")
                    content_type = response.headers.get("content-type", "")
                    if "html" not in content_type and "text" not in content_type:
                        raise _unprocessable(f"La URL no es una página web (es {content_type or 'otro tipo de archivo'}). {PASTE_HINT}")
                    chunks: list[bytes] = []
                    size = 0
                    async for chunk in response.aiter_bytes():
                        size += len(chunk)
                        if size > MAX_BYTES:
                            break
                        chunks.append(chunk)
                    raw = b"".join(chunks)
                    encoding = response.encoding or "utf-8"
                    return current, raw.decode(encoding, errors="replace")
            except HTTPException:
                raise
            except httpx.TimeoutException as exc:
                raise _unprocessable(f"El sitio tardó demasiado en responder. {PASTE_HINT}") from exc
            except httpx.HTTPError as exc:
                logger.info("No se pudo descargar %s: %s", current, exc)
                raise _unprocessable(f"No pudimos abrir esa página. {PASTE_HINT}") from exc
    raise _unprocessable(f"La página redirige demasiadas veces. {PASTE_HINT}")


# --- Parseo -------------------------------------------------------------------

def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for br in soup.find_all("br"):
        br.replace_with("\n")
    for li in soup.find_all("li"):
        li.insert_before("\n• ")
    for block in soup.find_all(["p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "section", "article", "ul", "ol"]):
        block.insert_after("\n")
    return normalize_whitespace(soup.get_text())


def _iter_jsonld_nodes(data: Any):
    if isinstance(data, list):
        for item in data:
            yield from _iter_jsonld_nodes(item)
    elif isinstance(data, dict):
        yield data
        if "@graph" in data:
            yield from _iter_jsonld_nodes(data["@graph"])


def _is_job_posting(node: dict) -> bool:
    node_type = node.get("@type")
    types = node_type if isinstance(node_type, list) else [node_type]
    return "JobPosting" in types


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return html_to_text(value) if "<" in value else normalize_whitespace(value)
    if isinstance(value, list):
        return "\n".join(filter(None, (_as_text(v) for v in value)))
    if isinstance(value, dict):
        return _as_text(value.get("name") or value.get("description") or value.get("value") or "")
    return str(value)


EMPLOYMENT_TYPES = {
    "FULL_TIME": "Jornada completa",
    "PART_TIME": "Media jornada",
    "CONTRACTOR": "Contrato por proyecto",
    "TEMPORARY": "Temporal",
    "INTERN": "Práctica",
    "VOLUNTEER": "Voluntariado",
    "PER_DIEM": "Por día",
}


def _location(node: dict) -> str:
    locations = node.get("jobLocation")
    locations = locations if isinstance(locations, list) else [locations]
    parts: list[str] = []
    for loc in locations:
        if not isinstance(loc, dict):
            continue
        address = loc.get("address") or {}
        if isinstance(address, dict):
            text = ", ".join(
                str(address[k]) for k in ("addressLocality", "addressRegion", "addressCountry")
                if isinstance(address.get(k), str) and address.get(k)
            )
            if text and text not in parts:
                parts.append(text)
    if str(node.get("jobLocationType", "")).upper() == "TELECOMMUTE":
        parts.append("Remoto")
    return " / ".join(parts)


def extract_job_posting(html: str) -> dict[str, str] | None:
    """Busca un JobPosting schema.org en los <script type="application/ld+json">."""
    soup = BeautifulSoup(html, "html.parser")
    for script in soup.find_all("script", type=re.compile(r"ld\+json", re.I)):
        raw = script.string or script.get_text() or ""
        try:
            data = json.loads(raw.strip())
        except (json.JSONDecodeError, ValueError):
            continue
        for node in _iter_jsonld_nodes(data):
            if not _is_job_posting(node):
                continue
            title = _as_text(node.get("title"))
            org = node.get("hiringOrganization")
            company = _as_text(org.get("name") if isinstance(org, dict) else org) or None
            sections: list[str] = []
            if company:
                sections.append(f"Empresa: {company}")
            location = _location(node)
            if location:
                sections.append(f"Ubicación: {location}")
            raw_types = node.get("employmentType")
            raw_types = raw_types if isinstance(raw_types, list) else [raw_types]
            employment = ", ".join(
                EMPLOYMENT_TYPES.get(str(t).upper(), str(t)) for t in raw_types
                if t and str(t).upper() not in ("OTHER", "")
            )
            if employment:
                sections.append(f"Tipo de empleo: {employment}")
            description = _as_text(node.get("description"))
            if description:
                sections.append(f"\n{description}")
            for key, label in (
                ("responsibilities", "Responsabilidades"),
                ("qualifications", "Requisitos"),
                ("experienceRequirements", "Experiencia requerida"),
                ("educationRequirements", "Educación requerida"),
                ("skills", "Habilidades"),
            ):
                value = _as_text(node.get(key))
                if value and value not in description:
                    sections.append(f"\n{label}:\n{value}")
            text = normalize_whitespace("\n".join(sections))
            if title and len(description) >= MIN_OFFER_CHARS // 2:
                return {"nombre": title, "empresa": company or "", "ofertaTexto": text}
    return None


def visible_text(html: str) -> tuple[str, str]:
    """(título de la página, texto principal visible)."""
    soup = BeautifulSoup(html, "html.parser")
    og_title = soup.find("meta", property="og:title")
    title = (og_title.get("content") if og_title else None) or (soup.title.get_text() if soup.title else "")
    for tag in soup(["script", "style", "noscript", "svg", "nav", "footer", "header", "aside", "form", "iframe", "button"]):
        tag.decompose()
    main = soup.find("main") or soup.find("article") or soup.body or soup
    return normalize_whitespace(title or ""), html_to_text(str(main))


# --- Orquestación -------------------------------------------------------------

async def extract_job_offer(url: str) -> JobExtractResult:
    target = normalize_job_url(url)
    final_url, html = await fetch_html(target)

    posting = extract_job_posting(html)
    if posting:
        return JobExtractResult(
            nombre=posting["nombre"][:255],
            empresa=posting["empresa"] or None,
            ofertaTexto=clip(posting["ofertaTexto"], MAX_OFFER_CHARS),
            fuente="datos-estructurados",
            url=final_url,
        )

    title, text = visible_text(html)
    if len(text) < MIN_OFFER_CHARS:
        raise _unprocessable(
            "No encontramos el texto de la oferta en esa página (puede requerir iniciar sesión "
            f"o cargarse con JavaScript). {PASTE_HINT}"
        )

    extraction = await generate_structured(
        JOB_EXTRACT_SYSTEM_PROMPT,
        build_job_extract_user_prompt(final_url, title, clip(text, MAX_PAGE_CHARS_FOR_AI)),
        JobOfferExtraction,
        temperature=0.1,
        max_tokens=2000,
    )
    offer = normalize_whitespace(extraction.oferta_texto)
    if not extraction.es_oferta or len(offer) < MIN_OFFER_CHARS // 2:
        raise _unprocessable(f"Esa página no parece contener una oferta laboral concreta. {PASTE_HINT}")
    company = (extraction.empresa or "").strip() or None
    header = f"Empresa: {company}\n\n" if company and company.lower() not in offer.lower()[:300] else ""
    return JobExtractResult(
        nombre=(extraction.nombre.strip() or title or "Oferta laboral")[:255],
        empresa=company,
        ofertaTexto=clip(header + offer, MAX_OFFER_CHARS),
        fuente="ia",
        url=final_url,
    )
