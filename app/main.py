from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.api.routes import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.middleware import (
    AuthContextMiddleware,
    RBACMiddleware,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
)


BASE_DIR = Path(__file__).resolve().parent


def create_application() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)

    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        docs_url="/docs" if settings.show_docs else None,
        redoc_url="/redoc" if settings.show_docs else None,
        openapi_url="/openapi.json" if settings.show_docs else None,
    )

    application.add_middleware(SecurityHeadersMiddleware)
    application.add_middleware(RequestLoggingMiddleware)
    application.add_middleware(RBACMiddleware)
    application.add_middleware(AuthContextMiddleware)
    application.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key,
        session_cookie=settings.session_cookie_name,
        max_age=settings.session_max_age,
        same_site=settings.session_same_site,
        https_only=settings.effective_session_https_only,
    )

    application.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
    application.include_router(api_router)

    return application


app = create_application()
