from fastapi import APIRouter

from app.api.routes.admin import router as admin_router
from app.api.routes.auth import router as auth_router
from app.api.routes.health import router as health_router
from app.api.routes.pages import router as pages_router
from app.api.routes.user import router as user_router
from app.api.routes.vendor import router as vendor_router


api_router = APIRouter()
api_router.include_router(pages_router)
api_router.include_router(admin_router)
api_router.include_router(auth_router)
api_router.include_router(health_router)
api_router.include_router(user_router)
api_router.include_router(vendor_router)
