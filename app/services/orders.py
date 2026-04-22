from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.models.enums import (
    CartStatus,
    MembershipStatus,
    MembershipTier,
    OrderStatus,
    PaymentStatus,
    ProductStatus,
    Role,
    VendorStatus,
)
from app.models.membership import Membership
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.payment import Payment
from app.models.product import Product
from app.models.user import User
from app.models.vendor import Vendor
from app.schemas.platform import CheckoutRequest, OrderStatusUpdateRequest, PaymentSimulationRequest


BASE_DELIVERY_FEE = Decimal("50.00")
PREMIUM_DELIVERY_FEE = Decimal("25.00")
VIP_DELIVERY_FEE = Decimal("0.00")


def checkout_cart(db: Session, *, user: User, payload: CheckoutRequest) -> Order:
    cart = _load_active_cart_for_checkout(db, user_id=user.id)
    if not cart.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your cart is empty and cannot be checked out.",
        )

    _validate_single_vendor_cart(cart)
    _validate_checkout_inventory(db, cart)
    _recalculate_cart_totals(cart)

    active_membership = _get_active_membership(db, user_id=user.id)
    delivery_fee = _resolve_delivery_fee(active_membership)
    order = Order(
        order_number=_generate_order_number(),
        user_id=user.id,
        cart_id=cart.id,
        status=OrderStatus.RECEIVED,
        subtotal_amount=cart.subtotal_amount,
        delivery_fee=delivery_fee,
        total_amount=cart.subtotal_amount + delivery_fee,
        delivery_address=payload.delivery_address.strip(),
        notes=payload.notes.strip() if payload.notes else None,
    )
    db.add(order)
    db.flush()

    for cart_item in cart.items:
        product = db.get(Product, cart_item.product_id)
        if product is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One of the products in the cart is no longer available.",
            )

        vendor = db.get(Vendor, product.vendor_id)
        if vendor is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A vendor for one of the cart items could not be found.",
            )

        product.inventory_count -= cart_item.quantity
        db.add(product)

        order_item = OrderItem(
            order_id=order.id,
            product_id=product.id,
            vendor_id=vendor.id,
            vendor_business_name=vendor.business_name,
            product_name=product.name,
            product_sku=product.sku,
            quantity=cart_item.quantity,
            unit_price=product.unit_price,
            line_total=product.unit_price * cart_item.quantity,
        )
        db.add(order_item)

    payment = Payment(
        order_id=order.id,
        amount=order.total_amount,
        payment_method=payload.payment_method.strip().lower(),
        status=PaymentStatus.PENDING,
    )
    db.add(payment)

    cart.status = CartStatus.CHECKED_OUT
    cart.checked_out_at = _now_utc()
    db.add(cart)

    db.commit()
    return _reload_order(db, order.id)


def simulate_payment(db: Session, *, user: User, order_id: int, payload: PaymentSimulationRequest) -> Order:
    order = _load_order_for_user(db, user_id=user.id, order_id=order_id)
    payment = order.payment
    if payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment record not found for this order.",
        )

    if payment.status == PaymentStatus.PAID:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This order has already been paid.",
        )

    if order.status in {OrderStatus.DELIVERED, OrderStatus.CANCELLED}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment simulation is not allowed for closed orders.",
        )

    payment.status = PaymentStatus.PAID if payload.succeed else PaymentStatus.FAILED
    payment.processed_at = _now_utc()
    payment.transaction_reference = _generate_transaction_reference()
    payment.provider_response = (
        payload.provider_message.strip()
        if payload.provider_message
        else (
            "Simulated payment approved successfully."
            if payload.succeed
            else "Simulated payment was declined."
        )
    )
    db.add(payment)
    db.commit()
    return _reload_order(db, order.id)


def list_user_orders(db: Session, *, user_id: int) -> list[Order]:
    statement = (
        _order_query()
        .where(Order.user_id == user_id)
        .order_by(Order.created_at.desc())
    )
    return list(db.execute(statement).scalars().all())


def get_user_order(db: Session, *, user_id: int, order_id: int) -> Order:
    return _load_order_for_user(db, user_id=user_id, order_id=order_id)


def list_admin_orders(db: Session) -> list[Order]:
    statement = _order_query().order_by(Order.created_at.desc())
    return list(db.execute(statement).scalars().all())


def list_vendor_orders(db: Session, *, vendor_user: User) -> list[Order]:
    vendor = vendor_user.vendor_profile
    if vendor is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account does not have a vendor profile.",
        )

    statement = (
        _order_query()
        .join(Order.items)
        .where(OrderItem.vendor_id == vendor.id)
        .order_by(Order.created_at.desc())
        .distinct()
    )
    return list(db.execute(statement).scalars().all())


def update_order_status(
    db: Session,
    *,
    actor_user: User,
    order_id: int,
    payload: OrderStatusUpdateRequest,
) -> Order:
    order = _reload_order(db, order_id)

    if actor_user.role == Role.VENDOR:
        _authorize_vendor_for_order(actor_user, order)
    elif actor_user.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins or vendors can update order status.",
        )

    if order.status == payload.status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order already has this status.",
        )

    allowed_transitions = {
        OrderStatus.RECEIVED: {OrderStatus.READY, OrderStatus.CANCELLED},
        OrderStatus.READY: {OrderStatus.OUT_FOR_DELIVERY, OrderStatus.CANCELLED},
        OrderStatus.OUT_FOR_DELIVERY: {OrderStatus.DELIVERED},
        OrderStatus.DELIVERED: set(),
        OrderStatus.CANCELLED: set(),
    }
    next_statuses = allowed_transitions.get(order.status, set())
    if payload.status not in next_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot move order from {order.status.value} to {payload.status.value}.",
        )

    if payload.status in {
        OrderStatus.READY,
        OrderStatus.OUT_FOR_DELIVERY,
        OrderStatus.DELIVERED,
    }:
        if order.payment is None or order.payment.status != PaymentStatus.PAID:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Order status can only progress after successful payment.",
            )

    order.status = payload.status
    now = _now_utc()
    if payload.status == OrderStatus.READY:
        order.ready_at = now
    elif payload.status == OrderStatus.OUT_FOR_DELIVERY:
        order.out_for_delivery_at = now
    elif payload.status == OrderStatus.DELIVERED:
        order.delivered_at = now
    elif payload.status == OrderStatus.CANCELLED:
        _restore_inventory_for_cancelled_order(db, order)

    if payload.notes:
        order.notes = _append_note(order.notes, payload.notes)

    db.add(order)
    db.commit()
    return _reload_order(db, order.id)


def _load_active_cart_for_checkout(db: Session, *, user_id: int) -> Cart:
    statement = (
        select(Cart)
        .options(selectinload(Cart.items).selectinload(CartItem.product))
        .where(Cart.user_id == user_id, Cart.status == CartStatus.ACTIVE)
        .order_by(Cart.created_at.desc())
    )
    cart = db.execute(statement).scalars().first()
    if cart is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active cart was found for checkout.",
        )
    return cart


def _validate_single_vendor_cart(cart: Cart) -> None:
    vendor_ids = {item.product.vendor_id for item in cart.items if item.product is not None}
    if len(vendor_ids) > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A checkout order can only contain products from one vendor.",
        )


def _validate_checkout_inventory(db: Session, cart: Cart) -> None:
    for item in cart.items:
        product = db.get(Product, item.product_id)
        if product is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One of the products in the cart is no longer available.",
            )
        if product.status != ProductStatus.APPROVED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{product.name} is no longer approved for purchase.",
            )
        vendor = db.get(Vendor, product.vendor_id)
        if vendor is None or vendor.status != VendorStatus.APPROVED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"The vendor for {product.name} is no longer available.",
            )
        if product.inventory_count < item.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient inventory for {product.name}.",
            )
        item.unit_price = product.unit_price
        item.line_total = product.unit_price * item.quantity
        db.add(item)


def _get_active_membership(db: Session, *, user_id: int) -> Membership | None:
    now = _now_utc()
    statement = (
        select(Membership)
        .where(
            Membership.user_id == user_id,
            Membership.status == MembershipStatus.ACTIVE,
            or_(Membership.starts_at.is_(None), Membership.starts_at <= now),
            or_(Membership.ends_at.is_(None), Membership.ends_at >= now),
        )
        .order_by(Membership.created_at.desc())
    )
    return db.execute(statement).scalars().first()


def _resolve_delivery_fee(membership: Membership | None) -> Decimal:
    if membership is None:
        return BASE_DELIVERY_FEE
    if membership.tier == MembershipTier.VIP:
        return VIP_DELIVERY_FEE
    if membership.tier == MembershipTier.PREMIUM:
        return PREMIUM_DELIVERY_FEE
    return BASE_DELIVERY_FEE


def _authorize_vendor_for_order(vendor_user: User, order: Order) -> None:
    vendor = vendor_user.vendor_profile
    if vendor is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account does not have a vendor profile.",
        )

    order_vendor_ids = {item.vendor_id for item in order.items if item.vendor_id is not None}
    if not order_vendor_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This order has no vendor ownership metadata.",
        )

    if vendor.id not in order_vendor_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to manage this order.",
        )

    if len(order_vendor_ids) > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mixed-vendor orders must be managed by an admin.",
        )


def _load_order_for_user(db: Session, *, user_id: int, order_id: int) -> Order:
    statement = _order_query().where(Order.id == order_id, Order.user_id == user_id)
    order = db.execute(statement).scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
    return order


def _reload_order(db: Session, order_id: int) -> Order:
    statement = _order_query().where(Order.id == order_id)
    order = db.execute(statement).scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
    return order


def _order_query():
    return select(Order).options(
        selectinload(Order.user),
        selectinload(Order.items),
        selectinload(Order.payment),
    )


def _recalculate_cart_totals(cart: Cart) -> None:
    subtotal = sum((item.line_total for item in cart.items), Decimal("0.00"))
    cart.subtotal_amount = subtotal
    cart.total_amount = subtotal


def _append_note(existing_notes: str | None, note: str) -> str:
    timestamp = _now_utc().isoformat()
    formatted_note = f"[{timestamp}] {note.strip()}"
    if not existing_notes:
        return formatted_note
    return f"{existing_notes}\n{formatted_note}"


def _restore_inventory_for_cancelled_order(db: Session, order: Order) -> None:
    for item in order.items:
        if item.product_id is None:
            continue
        product = db.get(Product, item.product_id)
        if product is None:
            continue
        product.inventory_count += item.quantity
        db.add(product)


def _generate_order_number() -> str:
    return f"ORD-{uuid4().hex[:12].upper()}"


def _generate_transaction_reference() -> str:
    return f"TXN-{uuid4().hex[:14].upper()}"


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)
