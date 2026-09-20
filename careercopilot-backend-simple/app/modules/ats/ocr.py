"""Punto de extension para OCR de PDFs escaneados."""
from app.shared.errors import bad_request


def extract_text_with_ocr(file_bytes: bytes, filename: str) -> str:
    """Indica que OCR debe configurarse cuando el parser no encuentra texto."""
    raise bad_request("El archivo no contiene texto extraible; configura OCR para PDFs escaneados.")