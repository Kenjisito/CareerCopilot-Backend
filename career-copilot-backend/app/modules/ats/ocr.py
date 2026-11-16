from __future__ import annotations
"""OCR acotado para páginas de PDF que no contienen texto seleccionable."""

import logging

import pypdfium2 as pdfium
import pytesseract
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)
OCR_DPI = 300
MAX_OCR_PAGES = 20


def extract_text_with_ocr(file_bytes: bytes, filename: str, page_numbers: list[int]) -> dict[int, str]:
    if len(page_numbers) > MAX_OCR_PAGES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"El PDF requiere OCR en más de {MAX_OCR_PAGES} páginas. Divide el documento e inténtalo de nuevo.",
        )

    document = pdfium.PdfDocument(file_bytes)
    extracted: dict[int, str] = {}
    try:
        for page_number in page_numbers:
            page = document[page_number]
            bitmap = page.render(scale=OCR_DPI / 72)
            image = bitmap.to_pil()
            try:
                extracted[page_number] = pytesseract.image_to_string(
                    image,
                    lang="spa+eng",
                    config="--psm 3",
                )
            except pytesseract.TesseractNotFoundError as exc:
                logger.exception("Tesseract no está disponible para procesar %s", filename)
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="El servicio de OCR no está disponible. Inténtalo más tarde.",
                ) from exc
            except pytesseract.TesseractError as exc:
                logger.exception("Tesseract no pudo procesar %s", filename)
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="No se pudo iniciar el OCR para este PDF. Inténtalo más tarde.",
                ) from exc
            finally:
                image.close()
                bitmap.close()
                page.close()
    finally:
        document.close()
    return extracted