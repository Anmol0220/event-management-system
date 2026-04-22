from __future__ import annotations

from typing import Literal

from fastapi import Request


FlashLevel = Literal["success", "info", "warning", "danger"]
FLASH_SESSION_KEY = "_flash_messages"


def flash(request: Request, message: str, level: FlashLevel = "info") -> None:
    entries = list(request.session.get(FLASH_SESSION_KEY, []))
    entries.append({"message": message, "level": level})
    request.session[FLASH_SESSION_KEY] = entries


def pop_flashes(request: Request) -> list[dict[str, str]]:
    raw_entries = request.session.pop(FLASH_SESSION_KEY, [])
    if not isinstance(raw_entries, list):
        return []

    normalized_entries: list[dict[str, str]] = []
    for entry in raw_entries:
        if not isinstance(entry, dict):
            continue
        message = str(entry.get("message", "")).strip()
        level = str(entry.get("level", "info")).strip() or "info"
        if message:
            normalized_entries.append({"message": message, "level": level})
    return normalized_entries
