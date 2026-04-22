from __future__ import annotations

import logging
from time import perf_counter

from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.auth import SESSION_USER_ID_KEY, SessionPrincipal
from app.db.session import SessionLocal
from app.models.enums import Role
from app.models.user import User


request_logger = logging.getLogger("app.request")


class AuthContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request.state.principal = None
        user_id = request.session.get(SESSION_USER_ID_KEY)

        if user_id is not None:
            try:
                user_id = int(user_id)
            except (TypeError, ValueError):
                request.session.clear()
                user_id = None

        if user_id is not None:
            with SessionLocal() as db:
                statement = select(User.id, User.name, User.email, User.role).where(
                    User.id == user_id,
                    User.is_active.is_(True),
                )
                principal_row = db.execute(statement).one_or_none()

            if principal_row is None:
                request.session.clear()
            else:
                request.state.principal = SessionPrincipal(
                    user_id=principal_row.id,
                    role=principal_row.role,
                    email=principal_row.email,
                    name=principal_row.name,
                )

        return await call_next(request)


class RBACMiddleware(BaseHTTPMiddleware):
    role_rules: tuple[tuple[str, set[Role]], ...] = (
        ("/api/admin", {Role.ADMIN}),
        ("/api/vendor", {Role.ADMIN, Role.VENDOR}),
        ("/api/user", {Role.ADMIN, Role.USER}),
    )

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method == "OPTIONS":
            return await call_next(request)

        allowed_roles = self._resolve_allowed_roles(request.url.path)
        if allowed_roles is None:
            return await call_next(request)

        principal = getattr(request.state, "principal", None)
        if principal is None:
            return JSONResponse(
                status_code=401,
                content={"detail": "Authentication is required to access this resource."},
            )

        if principal.role not in allowed_roles:
            return JSONResponse(
                status_code=403,
                content={"detail": "You do not have permission to access this resource."},
            )

        return await call_next(request)

    def _resolve_allowed_roles(self, path: str) -> set[Role] | None:
        for prefix, roles in self.role_rules:
            if path.startswith(prefix):
                return roles
        return None


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=()",
        )
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path.startswith("/static"):
            return await call_next(request)

        started_at = perf_counter()
        client_host = request.client.host if request.client else "unknown"

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (perf_counter() - started_at) * 1000
            request_logger.exception(
                "Unhandled request error | method=%s path=%s client=%s duration_ms=%.2f",
                request.method,
                request.url.path,
                client_host,
                duration_ms,
            )
            raise

        duration_ms = (perf_counter() - started_at) * 1000
        request_logger.info(
            "Request completed | method=%s path=%s status=%s client=%s duration_ms=%.2f",
            request.method,
            request.url.path,
            response.status_code,
            client_host,
            duration_ms,
        )
        return response
