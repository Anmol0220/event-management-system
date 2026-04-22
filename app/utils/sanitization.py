from __future__ import annotations

import re


CONTROL_CHAR_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
WHITESPACE_PATTERN = re.compile(r"\s+")


def sanitize_single_line_text(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = CONTROL_CHAR_PATTERN.sub("", value)
    normalized = WHITESPACE_PATTERN.sub(" ", normalized).strip()
    return normalized or None


def sanitize_multiline_text(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = CONTROL_CHAR_PATTERN.sub("", value)
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.strip() for line in normalized.split("\n")]
    cleaned_lines: list[str] = []
    previous_blank = False

    for line in lines:
        if not line:
            if previous_blank:
                continue
            previous_blank = True
            cleaned_lines.append("")
            continue
        previous_blank = False
        cleaned_lines.append(WHITESPACE_PATTERN.sub(" ", line))

    cleaned = "\n".join(cleaned_lines).strip()
    return cleaned or None


def validate_password_strength(password: str) -> str:
    if len(password) < 10:
        raise ValueError("Password must be at least 10 characters long.")
    if not any(character.islower() for character in password):
        raise ValueError("Password must include at least one lowercase letter.")
    if not any(character.isupper() for character in password):
        raise ValueError("Password must include at least one uppercase letter.")
    if not any(character.isdigit() for character in password):
        raise ValueError("Password must include at least one number.")
    if not any(not character.isalnum() for character in password):
        raise ValueError("Password must include at least one special character.")
    return password
