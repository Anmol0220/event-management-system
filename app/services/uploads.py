from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from app.core.config import get_settings


ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
ALLOWED_IMAGE_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
}

APP_DIR = Path(__file__).resolve().parent.parent
PRODUCT_UPLOAD_DIR = APP_DIR / "static" / "uploads" / "products"


async def save_validated_product_image(upload: UploadFile) -> str:
    _ensure_upload_filename(upload)

    suffix = Path(upload.filename or "").suffix.lower()
    if suffix not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPG, JPEG, PNG, GIF, and WEBP images are allowed.",
        )

    if upload.content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported image content type.",
        )

    settings = get_settings()
    content = await upload.read(settings.product_image_max_size_bytes + 1)
    await upload.close()

    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded image is empty.",
        )

    if len(content) > settings.product_image_max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image size must not exceed {settings.product_image_max_size_bytes} bytes.",
        )

    if not _matches_expected_image_signature(content):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file does not match a supported image format.",
        )

    PRODUCT_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    file_name = f"product_{uuid4().hex}{suffix}"
    destination = PRODUCT_UPLOAD_DIR / file_name
    destination.write_bytes(content)
    return f"/static/uploads/products/{file_name}"


def _ensure_upload_filename(upload: UploadFile) -> None:
    if not upload.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must include a filename.",
        )


def _matches_expected_image_signature(content: bytes) -> bool:
    if content.startswith(b"\xff\xd8\xff"):
        return True
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return True
    if content.startswith((b"GIF87a", b"GIF89a")):
        return True
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return True
    return False
