from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.category import Category
from app.models.membership import Membership
from app.models.product import Product
from app.models.user import User
from app.models.vendor import Vendor
from app.schemas.platform import (
    AdminProductStatusUpdateRequest,
    MembershipCreateRequest,
    MembershipUpdateRequest,
    UserAdminUpdateRequest,
    VendorAdminUpdateRequest,
)
from app.services.products import append_product_status_history, load_product_with_details


def list_users(db: Session):
    statement = select(User).order_by(User.created_at.desc())
    return list(db.execute(statement).scalars().all())


def update_user(db: Session, *, user_id: int, payload: UserAdminUpdateRequest) -> User:
    statement = (
        select(User)
        .options(selectinload(User.vendor_profile))
        .where(User.id == user_id)
    )
    user = db.execute(statement).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    if payload.name is not None:
        user.name = payload.name.strip()

    if payload.role is not None and payload.role != user.role:
        if payload.role.value == "vendor" and user.vendor_profile is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot assign vendor role without a vendor profile.",
            )
        if user.role.value == "vendor" and payload.role.value != "vendor" and user.vendor_profile is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vendor users must be updated through vendor management before changing role.",
            )
        user.role = payload.role

    if payload.is_active is not None:
        user.is_active = payload.is_active

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def list_vendors(db: Session):
    statement = (
        select(Vendor)
        .options(selectinload(Vendor.user), selectinload(Vendor.category))
        .order_by(Vendor.created_at.desc())
    )
    return list(db.execute(statement).scalars().all())


def update_vendor(db: Session, *, vendor_id: int, payload: VendorAdminUpdateRequest) -> Vendor:
    statement = (
        select(Vendor)
        .options(selectinload(Vendor.user), selectinload(Vendor.category))
        .where(Vendor.id == vendor_id)
    )
    vendor = db.execute(statement).scalar_one_or_none()
    if vendor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found.")

    if payload.category_id is not None:
        category = db.get(Category, payload.category_id)
        if category is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found.")
        vendor.category_id = category.id

    if payload.business_name is not None:
        vendor.business_name = payload.business_name.strip()
    if payload.contact_phone is not None:
        vendor.contact_phone = payload.contact_phone.strip() or None
    if payload.description is not None:
        vendor.description = payload.description.strip() or None
    if payload.status is not None:
        vendor.status = payload.status

    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    return _reload_vendor(db, vendor.id)


def list_memberships(db: Session):
    statement = (
        select(Membership)
        .options(selectinload(Membership.user))
        .order_by(Membership.created_at.desc())
    )
    return list(db.execute(statement).scalars().all())


def create_membership(db: Session, *, payload: MembershipCreateRequest) -> Membership:
    user = db.get(User, payload.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    membership = Membership(
        user_id=payload.user_id,
        tier=payload.tier,
        status=payload.status,
        price=payload.price,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        auto_renew=payload.auto_renew,
    )
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return _reload_membership(db, membership.id)


def update_membership(db: Session, *, membership_id: int, payload: MembershipUpdateRequest) -> Membership:
    membership = db.get(Membership, membership_id)
    if membership is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membership not found.")

    if payload.tier is not None:
        membership.tier = payload.tier
    if payload.status is not None:
        membership.status = payload.status
    if payload.price is not None:
        membership.price = payload.price
    if payload.starts_at is not None:
        membership.starts_at = payload.starts_at
    if payload.ends_at is not None:
        membership.ends_at = payload.ends_at
    if payload.auto_renew is not None:
        membership.auto_renew = payload.auto_renew

    db.add(membership)
    db.commit()
    db.refresh(membership)
    return _reload_membership(db, membership.id)


def update_product_status(
    db: Session,
    *,
    product_id: int,
    actor_user_id: int,
    payload: AdminProductStatusUpdateRequest,
) -> Product:
    product = load_product_with_details(db, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")

    if product.status == payload.status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product already has this status.",
        )

    old_status = product.status
    product.status = payload.status
    db.add(product)
    append_product_status_history(
        db,
        product_id=product.id,
        old_status=old_status,
        new_status=payload.status,
        changed_by_user_id=actor_user_id,
        notes=payload.notes,
    )
    db.commit()
    return load_product_with_details(db, product.id) or product


def _reload_vendor(db: Session, vendor_id: int) -> Vendor:
    statement = (
        select(Vendor)
        .options(selectinload(Vendor.user), selectinload(Vendor.category))
        .where(Vendor.id == vendor_id)
    )
    vendor = db.execute(statement).scalar_one_or_none()
    if vendor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found.")
    return vendor


def _reload_membership(db: Session, membership_id: int) -> Membership:
    statement = (
        select(Membership)
        .options(selectinload(Membership.user))
        .where(Membership.id == membership_id)
    )
    membership = db.execute(statement).scalar_one_or_none()
    if membership is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membership not found.")
    return membership
