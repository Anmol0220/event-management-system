from __future__ import annotations

import re
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.product import Product
from app.models.product_status_history import ProductStatusHistory


def load_product_with_details(db: Session, product_id: int) -> Product | None:
    statement = (
        select(Product)
        .options(
            selectinload(Product.vendor),
            selectinload(Product.category),
        )
        .where(Product.id == product_id)
    )
    return db.execute(statement).scalar_one_or_none()


def build_unique_product_slug(
    db: Session,
    *,
    name: str,
    requested_slug: str | None = None,
    exclude_product_id: int | None = None,
) -> str:
    base_slug = slugify(requested_slug or name)
    candidate = base_slug
    suffix = 2

    while _product_slug_exists(db, candidate, exclude_product_id):
        candidate = f"{base_slug}-{suffix}"
        suffix += 1

    return candidate


def build_unique_product_sku(
    db: Session,
    *,
    requested_sku: str | None = None,
    exclude_product_id: int | None = None,
) -> str:
    if requested_sku:
        normalized_sku = requested_sku.strip().upper()
        if _product_sku_exists(db, normalized_sku, exclude_product_id):
            raise ValueError("A product with this SKU already exists.")
        return normalized_sku

    while True:
        generated = f"PRD-{uuid4().hex[:10].upper()}"
        if not _product_sku_exists(db, generated, exclude_product_id):
            return generated


def append_product_status_history(
    db: Session,
    *,
    product_id: int,
    old_status,
    new_status,
    changed_by_user_id: int | None,
    notes: str | None = None,
) -> ProductStatusHistory:
    history_entry = ProductStatusHistory(
        product_id=product_id,
        old_status=old_status,
        new_status=new_status,
        changed_by_user_id=changed_by_user_id,
        notes=notes,
    )
    db.add(history_entry)
    db.flush()
    return history_entry


def slugify(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return normalized or "product"


def _product_slug_exists(db: Session, slug: str, exclude_product_id: int | None) -> bool:
    statement = select(Product.id).where(Product.slug == slug)
    if exclude_product_id is not None:
        statement = statement.where(Product.id != exclude_product_id)
    return db.execute(statement).scalar_one_or_none() is not None


def _product_sku_exists(db: Session, sku: str, exclude_product_id: int | None) -> bool:
    statement = select(Product.id).where(Product.sku == sku)
    if exclude_product_id is not None:
        statement = statement.where(Product.id != exclude_product_id)
    return db.execute(statement).scalar_one_or_none() is not None
