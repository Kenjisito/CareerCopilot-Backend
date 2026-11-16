from __future__ import annotations

from typing import Any


def response_rows(response: Any) -> list[dict[str, Any]]:
    data = response.data or []
    if isinstance(data, dict):
        return [data]
    return list(data)


def first_row(response: Any) -> dict[str, Any] | None:
    rows = response_rows(response)
    return rows[0] if rows else None
