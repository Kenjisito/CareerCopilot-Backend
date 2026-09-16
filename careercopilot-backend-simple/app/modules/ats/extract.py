"""
Extracción de texto de CVs en PDF o DOCX. Función aislada del endpoint
HTTP (mismo principio de desacople usado en el resto del proyecto) para
que se pueda testear o reemplazar sin tocar el router.
"""
import io

import pdfplumber
from docx import Document

from app.shared.errors import bad_request


def extract_text(file_bytes: bytes, filename: str) -> str:
    lower_name = filename.lower()

    if lower_name.endswith(".pdf"):
        text_parts: list[str] = []
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        text = "\n".join(text_parts)

    elif lower_name.endswith(".docx"):
        document = Document(io.BytesIO(file_bytes))
        text = "\n".join(p.text for p in document.paragraphs)

    else:
        raise bad_request("Formato no soportado. Sube un archivo PDF o DOCX.")

    text = text.strip()
    if len(text) < 30:
        raise bad_request(
            "No se pudo extraer texto legible del archivo. Revisa que no sea un PDF escaneado como imagen."
        )
    return text
