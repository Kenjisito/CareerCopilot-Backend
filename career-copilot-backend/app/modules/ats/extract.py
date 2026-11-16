from __future__ import annotations
"""
Extracción de texto de CVs en PDF o DOCX. Función aislada del endpoint
HTTP para que se pueda testear o reemplazar sin tocar el router.
"""
import io
import logging
import re

import pdfplumber
from docx import Document
from docx.document import Document as DocumentType
from docx.table import Table
from docx.text.paragraph import Paragraph
from fastapi import HTTPException

from app.modules.ats.ocr import extract_text_with_ocr
from app.shared.errors import bad_request
from app.shared.text import normalize_whitespace

logger = logging.getLogger(__name__)
MIN_TEXT_CHARS = 30


def _extract_pdf(file_bytes: bytes) -> str:
    parts: list[str] = []
    pages_needing_ocr: list[int] = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page_number, page in enumerate(pdf.pages):
            # PDFs multicolumna pueden quedar mejor en orden de flujo o geométrico;
            # conservamos la extracción que recupera más palabras.
            positioned = page.extract_text(x_tolerance=1.5, y_tolerance=3) or ""
            flow = page.extract_text(x_tolerance=1.5, y_tolerance=3, use_text_flow=True) or ""
            page_text = max(
                (positioned, flow),
                key=lambda value: len(re.findall(r"\w+", value)),
            )
            parts.append(page_text)
            if len(page_text.strip()) < MIN_TEXT_CHARS:
                pages_needing_ocr.append(page_number)
    if pages_needing_ocr:
        ocr_pages = extract_text_with_ocr(file_bytes, "PDF", pages_needing_ocr)
        for page_number, page_text in ocr_pages.items():
            if len(page_text.strip()) > len(parts[page_number].strip()):
                parts[page_number] = page_text
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
        lines.extend(_iter_block_text(section.header))
    lines.extend(_iter_block_text(document))
    for section in document.sections:
        lines.extend(_iter_block_text(section.footer))
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
            "verifica que tenga buena resolución y texto nítido."
        )
    return text
