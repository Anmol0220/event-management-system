from __future__ import annotations

import secrets

from fastapi import HTTPException, Request, Response, status


CSRF_SESSION_KEY = "_csrf_token"
CSRF_FORM_FIELD = "csrf_token"
CSRF_HEADER_NAME = "x-csrf-token"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}


def get_or_create_csrf_token(request: Request) -> str:
    token = request.session.get(CSRF_SESSION_KEY)
    if isinstance(token, str) and token:
        return token

    token = secrets.token_urlsafe(32)
    request.session[CSRF_SESSION_KEY] = token
    return token


async def enforce_csrf_protection(request: Request, response: Response) -> None:
    token = get_or_create_csrf_token(request)
    response.headers["X-CSRF-Token"] = token

    if request.method.upper() in SAFE_METHODS:
        return

    provided_token = request.headers.get(CSRF_HEADER_NAME, "").strip()
    if not provided_token:
        content_type = request.headers.get("content-type", "")
        if content_type.startswith("application/x-www-form-urlencoded") or content_type.startswith("multipart/form-data"):
            form = await request.form()
            provided_token = str(form.get(CSRF_FORM_FIELD, "")).strip()

    if not provided_token or not secrets.compare_digest(provided_token, token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token missing or invalid.",
        )
