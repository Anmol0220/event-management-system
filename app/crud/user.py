from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.enums import Role, VendorStatus
from app.models.user import User
from app.models.vendor import Vendor


def get_user_by_email(db: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email)
    return db.execute(statement).scalar_one_or_none()


def get_user_with_vendor_by_id(db: Session, user_id: int) -> User | None:
    statement = (
        select(User)
        .options(selectinload(User.vendor_profile))
        .where(User.id == user_id)
    )
    return db.execute(statement).scalar_one_or_none()


def create_user(
    db: Session,
    *,
    name: str,
    email: str,
    password: str,
    role: Role,
) -> User:
    user = User(
        name=name,
        email=email,
        password=password,
        role=role,
    )
    db.add(user)
    db.flush()
    return user


def create_vendor_profile(
    db: Session,
    *,
    user_id: int,
    business_name: str,
    category_id: int | None = None,
    contact_phone: str | None = None,
    description: str | None = None,
    status: VendorStatus = VendorStatus.PENDING,
) -> Vendor:
    vendor = Vendor(
        user_id=user_id,
        category_id=category_id,
        business_name=business_name,
        contact_phone=contact_phone,
        description=description,
        status=status,
    )
    db.add(vendor)
    db.flush()
    return vendor


def update_last_login(db: Session, user: User) -> User:
    user.last_login_at = datetime.now(timezone.utc)
    db.add(user)
    db.flush()
    return user
