from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.models.enums import MembershipStatus, ProductStatus, RequestStatus, VendorStatus
from app.models.membership import Membership
from app.models.order import Order
from app.models.product import Product
from app.models.request import Request
from app.models.user import User
from app.models.vendor import Vendor
from app.services import orders as order_service
from app.services import user as user_service
from app.services import vendor as vendor_service


def get_admin_dashboard_data(db: Session) -> dict[str, object]:
    stats = {
        "users": db.scalar(select(func.count()).select_from(User)) or 0,
        "vendors": db.scalar(select(func.count()).select_from(Vendor)) or 0,
        "pending_products": db.scalar(
            select(func.count()).select_from(Product).where(Product.status == ProductStatus.PENDING_APPROVAL)
        )
        or 0,
        "orders": db.scalar(select(func.count()).select_from(Order)) or 0,
    }

    recent_users = list(
        db.execute(select(User).order_by(User.created_at.desc()).limit(6)).scalars().all()
    )
    vendors = list(
        db.execute(
            select(Vendor)
            .options(selectinload(Vendor.user), selectinload(Vendor.category))
            .order_by(Vendor.created_at.desc())
            .limit(6)
        )
        .scalars()
        .all()
    )
    pending_products = list(
        db.execute(
            select(Product)
            .options(selectinload(Product.vendor), selectinload(Product.category))
            .where(Product.status == ProductStatus.PENDING_APPROVAL)
            .order_by(Product.created_at.desc())
            .limit(6)
        )
        .scalars()
        .all()
    )
    memberships = list(
        db.execute(
            select(Membership)
            .options(selectinload(Membership.user))
            .order_by(Membership.created_at.desc())
            .limit(6)
        )
        .scalars()
        .all()
    )
    recent_orders = order_service.list_admin_orders(db)[:6]

    return {
        "stats": stats,
        "recent_users": recent_users,
        "vendors": vendors,
        "pending_products": pending_products,
        "memberships": memberships,
        "recent_orders": recent_orders,
    }


def get_vendor_dashboard_data(db: Session, vendor_user: User) -> dict[str, object]:
    vendor = vendor_user.vendor_profile
    products = vendor_service.list_vendor_products(db, vendor_user=vendor_user)
    requests = vendor_service.list_vendor_requests(db, vendor_user=vendor_user)
    orders = order_service.list_vendor_orders(db, vendor_user=vendor_user)

    status_counts = {
        "approved": sum(1 for product in products if product.status == ProductStatus.APPROVED),
        "pending": sum(1 for product in products if product.status == ProductStatus.PENDING_APPROVAL),
        "draft": sum(1 for product in products if product.status == ProductStatus.DRAFT),
    }

    return {
        "vendor": vendor,
        "products": products[:8],
        "requests": requests[:8],
        "orders": orders[:8],
        "status_counts": status_counts,
    }


def get_user_dashboard_data(db: Session, user: User) -> dict[str, object]:
    memberships = list(
        db.execute(
            select(Membership)
            .where(Membership.user_id == user.id)
            .order_by(Membership.created_at.desc())
            .limit(3)
        )
        .scalars()
        .all()
    )
    active_membership = next(
        (
            membership
            for membership in memberships
            if membership.status == MembershipStatus.ACTIVE
        ),
        None,
    )
    cart = user_service.get_active_cart(db, user_id=user.id)
    orders = order_service.list_user_orders(db, user_id=user.id)
    requests = user_service.list_user_requests(db, user_id=user.id)

    return {
        "active_membership": active_membership,
        "memberships": memberships,
        "cart": cart,
        "recent_orders": orders[:5],
        "recent_requests": requests[:5],
    }
