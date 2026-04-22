from fastapi import APIRouter


router = APIRouter(tags=["system"])


@router.get("/", summary="Application welcome endpoint")
def root() -> dict[str, str]:
    return {"message": "Event Management System API is running."}


@router.get("/health", summary="Application health check")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
