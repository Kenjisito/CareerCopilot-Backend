from __future__ import annotations
"""
Extracción de texto de CVs en PDF o DOCX. Función aislada del endpoint
HTTP para que se pueda testear o reemplazar sin tocar el router.
"""
import io
import logging

import pdfplumber
from docx import Document
from docx.document import Document as DocumentType
from docx.table import Table
from docx.text.paragraph import Paragraph
from fastapi import HTTPException

from app.shared.errors import bad_request
from app.shared.text import normalize_whitespace

logger = logging.getLogger(__name__)
MIN_TEXT_CHARS = 30


def _extract_pdf(file_bytes: bytes) -> str:
    parts: list[str] = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            # x_tolerance bajo evita que palabras separadas por poco espacio se peguen.
            page_text = page.extract_text(x_tolerance=1.5, y_tolerance=3)
            if page_text:
                parts.append(page_text)
    return "\n".join(parts)


def _iter_block_text(container) -> list[str]:
    """Párrafos y tablas en el orden en que aparecen en el documento."""
    lines: list[str] = []
    body = container.element.body if isinstance(container, DocumentType) else container._element
    for child in body.iterchildren():
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "p":
            text = Paragraph(child, container).text
            if text.strip():
                lines.append(text)
        elif tag == "tbl":
            for row in Table(child, container).rows:
                seen: set[str] = set()
                cells: list[str] = []
                for cell in row.cells:
                    cell_text = cell.text.strip()
                    # Las celdas combinadas se repiten en python-docx.
                    if cell_text and cell_text not in seen:
                        seen.add(cell_text)
                        cells.append(cell_text)
                if cells:
                    lines.append(" | ".join(cells))
    return lines


def _extract_docx(file_bytes: bytes) -> str:
    document = Document(io.BytesIO(file_bytes))
    lines: list[str] = []
    # Encabezados (muchos CV ponen ahí nombre y contacto).
    for section in document.sections:
        for paragraph in section.header.paragraphs:
            if paragraph.text.strip():
                lines.append(paragraph.text)
    lines.extend(_iter_block_text(document))
    for section in document.sections:
        for paragraph in section.footer.paragraphs:
            if paragraph.text.strip():
                lines.append(paragraph.text)
    # Elimina líneas repetidas consecutivas (encabezados iguales en cada sección).
    deduped = [line for i, line in enumerate(lines) if i == 0 or line != lines[i - 1]]
    return "\n".join(deduped)


def extract_text(file_bytes: bytes, filename: str) -> str:
    lower_name = filename.lower()

    try:
        if lower_name.endswith(".pdf"):
            text = _extract_pdf(file_bytes)
        elif lower_name.endswith(".docx"):
            text = _extract_docx(file_bytes)
        else:
            raise bad_request("Formato no soportado. Sube un archivo PDF o DOCX.")
    except HTTPException:
        raise
    except Exception:
        logger.info("No se pudo leer el archivo %s", filename, exc_info=True)
        raise bad_request("No se pudo leer el archivo. Verifica que no esté dañado y vuelve a subirlo.")

    text = normalize_whitespace(text)
    if len(text) < MIN_TEXT_CHARS:
        raise bad_request(
            "No se pudo extraer texto legible del archivo. Si es un PDF escaneado (imagen), "
            "expórtalo de nuevo desde Word o Google Docs como PDF con texto."
        )
    return text
