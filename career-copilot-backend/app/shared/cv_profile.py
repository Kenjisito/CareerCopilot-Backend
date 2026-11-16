from __future__ import annotations

from typing import Any


def validate_additional_sections(value: Any) -> dict[str, list[str]]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("additionalSections debe ser un objeto por categoría")

    sections: dict[str, list[str]] = {}
    for category, entries in value.items():
        if not isinstance(category, str) or not category.strip() or not isinstance(entries, list):
            raise ValueError("Cada sección adicional debe ser una lista de textos")
        if len(entries) > 100:
            raise ValueError("Una sección no puede contener más de 100 elementos")
        cleaned = []
        for entry in entries:
            if not isinstance(entry, str):
                raise ValueError("Los elementos de las secciones adicionales deben ser texto")
            text = entry.strip()
            if text:
                if len(text) > 3000:
                    raise ValueError("Cada elemento de una sección admite hasta 3000 caracteres")
                cleaned.append(text)
        sections[category.strip()] = cleaned
    return sections
