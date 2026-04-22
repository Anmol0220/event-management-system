from __future__ import annotations

from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.models.category import Category
from app.models.enums import CartStatus, ProductStatus, VendorStatus
from app.models.product import Product
from app.models.request import Request
from app.models.user import User
from app.models.vendor import Vendor
from app.schemas.platform import AddCartItemRequest, ItemRequestCreateRequest, UpdateCartItemRequest


def browse_products(
    db: Session,
    *,
    search: str | None = None,
    category_id: int | None = None,
    vendor_id: int | None = None,
):
    statement = (
        select(Product)
        .join(Product.vendor)
        .join(Product.category)
        .options(selectinload(Product.vendor), selectinload(Product.category))
        .where(
            Product.status == ProductStatus.APPROVED,
            Vendor.status == VendorStatus.APPROVED,
            Category.is_active.is_(True),
        )
        .order_by(Product.created_at.desc())
    )

    if search:
        search_pattern = f"%{search.strip()}%"
        statement = statement.where(Product.name.ilike(search_pattern))
    if category_id is not None:
        statement = statement.where(Product.category_id == category_id)
    if vendor_id is not None:
        statement = statement.where(Product.vendor_id == vendor_id)

    return list(db.execute(statement).scalars().all())


def get_active_cart(db: Session, *, user_id: int) -> Cart:
    statement = (
        select(Cart)
        .options(
            selectinload(Cart.items).selectinload(CartItem.product),
        )
        .where(Cart.user_id == user_id, Cart.status == CartStatus.ACTIVE)
        .order_by(Cart.created_at.desc())
    )
    cart = db.execute(statement).scalars().first()
    if cart is not None:
        return cart

    cart = Cart(
        user_id=user_id,
        status=CartStatus.ACTIVE,
        subtotal_amount=Decimal("0.00"),
        total_amount=Decimal("0.00"),
    )
    db.add(cart)
    db.commit()
    return _reload_cart(db, cart.id)


def add_item_to_cart(db: Session, *, user: User, payload: AddCartItemRequest) -> Cart:
    cart = get_active_cart(db, user_id=user.id)
    product = db.get(Product, payload.product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
    if product.status != ProductStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only approved products can be added to the cart.",
        )

    vendor = db.get(Vendor, product.vendor_id)
    if vendor is None or vendor.status != VendorStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This vendor is not currently available for orders.",
        )
    _ensure_single_vendor_cart(cart, product.vendor_id)

    statement = select(CartItem).where(
        CartItem.cart_id == cart.id,
        CartItem.product_id == product.id,
    )
    cart_item = db.execute(statement).scalar_one_or_none()
    new_quantity = payload.quantity if cart_item is None else cart_item.quantity + payload.quantity

    if product.inventory_count < new_quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Requested quantity exceeds available inventory.",
        )

    if cart_item is None:
        cart_item = CartItem(
            cart_id=cart.id,
            product_id=product.id,
            quantity=payload.quantity,
            unit_price=product.unit_price,
            line_total=product.unit_price * payload.quantity,
        )
        db.add(cart_item)
    else:
        cart_item.quantity = new_quantity
        cart_item.unit_price = product.unit_price
        cart_item.line_total = product.unit_price * new_quantity
        db.add(cart_item)

    db.flush()
    cart = _reload_cart(db, cart.id)
    _recalculate_cart_totals(cart)
    db.add(cart)
    db.commit()
    return _reload_cart(db, cart.id)


def update_cart_item_quantity(
    db: Session,
    *,
    user: User,
    cart_item_id: int,
    payload: UpdateCartItemRequest,
) -> Cart:
    cart = get_active_cart(db, user_id=user.id)
    statement = select(CartItem).where(
        CartItem.id == cart_item_id,
        CartItem.cart_id == cart.id,
    )
    cart_item = db.execute(statement).scalar_one_or_none()
    if cart_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found.")

    product = db.get(Product, cart_item.product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This product is no longer available.",
        )
    if product.inventory_count < payload.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Requested quantity exceeds available inventory.",
        )

    cart_item.quantity = payload.quantity
    cart_item.unit_price = product.unit_price
    cart_item.line_total = product.unit_price * payload.quantity
    db.add(cart_item)
    db.flush()

    cart = _reload_cart(db, cart.id)
    _recalculate_cart_totals(cart)
    db.add(cart)
    db.commit()
    return _reload_cart(db, cart.id)


def remove_cart_item(db: Session, *, user: User, cart_item_id: int) -> Cart:
    cart = get_active_cart(db, user_id=user.id)
    statement = select(CartItem).where(
        CartItem.id == cart_item_id,
        CartItem.cart_id == cart.id,
    )
    cart_item = db.execute(statement).scalar_one_or_none()
    if cart_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found.")

    db.delete(cart_item)
    db.flush()

    cart = _reload_cart(db, cart.id)
    _recalculate_cart_totals(cart)
    db.add(cart)
    db.commit()
    return _reload_cart(db, cart.id)


def list_user_requests(db: Session, *, user_id: int):
    statement = (
        select(Request)
        .options(
            selectinload(Request.user),
            selectinload(Request.vendor),
            selectinload(Request.product),
            selectinload(Request.category),
        )
        .where(Request.user_id == user_id)
        .order_by(Request.created_at.desc())
    )
    return list(db.execute(statement).scalars().all())


def create_user_request(db: Session, *, user: User, payload: ItemRequestCreateRequest) -> Request:
    product = None
    vendor = None
    category = None

    if payload.product_id is not None:
        product = db.get(Product, payload.product_id)
        if product is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
        vendor = db.get(Vendor, product.vendor_id)
        category = db.get(Category, product.category_id)

    if payload.vendor_id is not None:
        requested_vendor = db.get(Vendor, payload.vendor_id)
        if requested_vendor is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found.")
        if vendor is not None and vendor.id != requested_vendor.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Provided vendor_id does not match the selected product.",
            )
        vendor = requested_vendor

    if payload.category_id is not None:
        requested_category = db.get(Category, payload.category_id)
        if requested_category is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found.")
        if category is not None and category.id != requested_category.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Provided category_id does not match the selected product.",
            )
        category = requested_category

    item_request = Request(
        user_id=user.id,
        vendor_id=vendor.id if vendor is not None else None,
        product_id=product.id if product is not None else None,
        category_id=category.id if category is not None else None,
        title=payload.title.strip(),
        description=payload.description,
        quantity=payload.quantity,
        desired_event_date=payload.desired_event_date,
        budget_amount=payload.budget_amount,
    )
    db.add(item_request)
    db.commit()
    return _reload_request(db, item_request.id)


def _recalculate_cart_totals(cart: Cart) -> None:
    subtotal = sum((item.line_total for item in cart.items), Decimal("0.00"))
    cart.subtotal_amount = subtotal
    cart.total_amount = subtotal


def _ensure_single_vendor_cart(cart: Cart, target_vendor_id: int) -> None:
    existing_vendor_ids = {
        item.product.vendor_id
        for item in cart.items
        if item.product is not None and item.product.vendor_id != target_vendor_id
    }
    if existing_vendor_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A cart can only contain products from one vendor at a time.",
        )


def _reload_cart(db: Session, cart_id: int) -> Cart:
    statement = (
        select(Cart)
        .options(selectinload(Cart.items).selectinload(CartItem.product))
        .where(Cart.id == cart_id)
    )
    cart = db.execute(statement).scalar_one_or_none()
    if cart is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found.")
    return cart


def _reload_request(db: Session, request_id: int) -> Request:
    statement = (
        select(Request)
        .options(
            selectinload(Request.user),
            selectinload(Request.vendor),
            selectinload(Request.product),
            selectinload(Request.category),
        )
        .where(Request.id == request_id)
    )
    item_request = db.execute(statement).scalar_one_or_none()
    if item_request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found.")
    return item_request
