from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.category import Category
from app.models.enums import ProductStatus, VendorStatus
from app.models.product import Product
from app.models.request import Request
from app.models.user import User
from app.models.vendor import Vendor
from app.schemas.platform import VendorProductCreateRequest, VendorProductUpdateRequest
from app.services.products import (
    append_product_status_history,
    build_unique_product_sku,
    build_unique_product_slug,
    load_product_with_details,
)


def list_vendor_products(db: Session, *, vendor_user: User):
    vendor = _require_vendor_profile(vendor_user)
    statement = (
        select(Product)
        .options(selectinload(Product.vendor), selectinload(Product.category))
        .where(Product.vendor_id == vendor.id)
        .order_by(Product.created_at.desc())
    )
    return list(db.execute(statement).scalars().all())


def create_vendor_product(db: Session, *, vendor_user: User, payload: VendorProductCreateRequest) -> Product:
    vendor = _require_vendor_profile(vendor_user)
    _ensure_vendor_approved(vendor)
    category = _get_active_category(db, payload.category_id)
    target_status = _normalize_vendor_product_status(payload.status)

    product = Product(
        vendor_id=vendor.id,
        category_id=category.id,
        name=payload.name.strip(),
        slug=build_unique_product_slug(db, name=payload.name, requested_slug=payload.slug),
        sku=build_unique_product_sku(db, requested_sku=payload.sku),
        description=payload.description,
        unit_price=payload.unit_price,
        inventory_count=payload.inventory_count,
        image_url=payload.image_url,
        status=target_status,
    )
    db.add(product)
    db.flush()

    append_product_status_history(
        db,
        product_id=product.id,
        old_status=ProductStatus.DRAFT,
        new_status=target_status,
        changed_by_user_id=vendor_user.id,
        notes="Product created by vendor.",
    )
    db.commit()
    return load_product_with_details(db, product.id) or product


def update_vendor_product(
    db: Session,
    *,
    vendor_user: User,
    product_id: int,
    payload: VendorProductUpdateRequest,
) -> Product:
    vendor = _require_vendor_profile(vendor_user)
    _ensure_vendor_approved(vendor)

    statement = (
        select(Product)
        .options(selectinload(Product.vendor), selectinload(Product.category))
        .where(Product.id == product_id, Product.vendor_id == vendor.id)
    )
    product = db.execute(statement).scalar_one_or_none()
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found for this vendor.",
        )

    if payload.category_id is not None:
        category = _get_active_category(db, payload.category_id)
        product.category_id = category.id

    name_changed = False
    if payload.name is not None:
        product.name = payload.name.strip()
        name_changed = True
    if payload.description is not None:
        product.description = payload.description
    if payload.unit_price is not None:
        product.unit_price = payload.unit_price
    if payload.inventory_count is not None:
        product.inventory_count = payload.inventory_count
    if payload.image_url is not None:
        product.image_url = payload.image_url
    if payload.sku is not None:
        product.sku = build_unique_product_sku(
            db,
            requested_sku=payload.sku,
            exclude_product_id=product.id,
        )
    if payload.slug is not None or name_changed:
        product.slug = build_unique_product_slug(
            db,
            name=product.name,
            requested_slug=payload.slug,
            exclude_product_id=product.id,
        )

    old_status = product.status
    if payload.status is not None:
        product.status = _normalize_vendor_product_status(payload.status)
    elif old_status == ProductStatus.APPROVED:
        product.status = ProductStatus.PENDING_APPROVAL

    db.add(product)
    db.flush()

    if product.status != old_status:
        append_product_status_history(
            db,
            product_id=product.id,
            old_status=old_status,
            new_status=product.status,
            changed_by_user_id=vendor_user.id,
            notes="Product updated by vendor.",
        )

    db.commit()
    return load_product_with_details(db, product.id) or product


def list_vendor_requests(db: Session, *, vendor_user: User):
    vendor = _require_vendor_profile(vendor_user)
    statement = (
        select(Request)
        .options(
            selectinload(Request.user),
            selectinload(Request.vendor),
            selectinload(Request.product),
            selectinload(Request.category),
        )
        .where(
            or_(
                Request.vendor_id == vendor.id,
                Request.product.has(Product.vendor_id == vendor.id),
            )
        )
        .order_by(Request.created_at.desc())
    )
    return list(db.execute(statement).scalars().all())


def _require_vendor_profile(vendor_user: User) -> Vendor:
    vendor = vendor_user.vendor_profile
    if vendor is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account does not have a vendor profile.",
        )
    return vendor


def _ensure_vendor_approved(vendor: Vendor) -> None:
    if vendor.status != VendorStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vendor approval is required before managing products.",
        )


def _get_active_category(db: Session, category_id: int) -> Category:
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found.")
    if not category.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive categories cannot be assigned to products.",
        )
    return category


def _normalize_vendor_product_status(status_value: ProductStatus | None) -> ProductStatus:
    if status_value is None:
        return ProductStatus.PENDING_APPROVAL
    if status_value not in {ProductStatus.DRAFT, ProductStatus.PENDING_APPROVAL}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vendors may only set product status to draft or pending approval.",
        )
    return status_value
