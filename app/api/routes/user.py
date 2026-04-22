from fastapi import APIRouter, Depends, Query

from app.core.csrf import enforce_csrf_protection
from app.core.dependencies import DBSession, EndUser
from app.schemas.platform import (
    AddCartItemRequest,
    CartResponse,
    CheckoutRequest,
    ItemRequestCreateRequest,
    ItemRequestResponse,
    OrderResponse,
    PaymentSimulationRequest,
    ProductResponse,
    UpdateCartItemRequest,
)
from app.services import orders as order_service
from app.services import user as user_service


router = APIRouter(
    prefix="/api/user",
    tags=["user"],
    dependencies=[Depends(enforce_csrf_protection)],
)


@router.get("/products", response_model=list[ProductResponse])
def browse_products(
    _: EndUser,
    db: DBSession,
    search: str | None = Query(default=None, max_length=255),
    category_id: int | None = Query(default=None, gt=0),
    vendor_id: int | None = Query(default=None, gt=0),
) -> list[ProductResponse]:
    products = user_service.browse_products(
        db,
        search=search,
        category_id=category_id,
        vendor_id=vendor_id,
    )
    return [ProductResponse.model_validate(product) for product in products]


@router.get("/cart", response_model=CartResponse)
def get_cart(user: EndUser, db: DBSession) -> CartResponse:
    cart = user_service.get_active_cart(db, user_id=user.id)
    return CartResponse.model_validate(cart)


@router.post("/cart/items", response_model=CartResponse)
def add_to_cart(
    payload: AddCartItemRequest,
    user: EndUser,
    db: DBSession,
) -> CartResponse:
    cart = user_service.add_item_to_cart(db, user=user, payload=payload)
    return CartResponse.model_validate(cart)


@router.patch("/cart/items/{cart_item_id}", response_model=CartResponse)
def update_cart_item(
    cart_item_id: int,
    payload: UpdateCartItemRequest,
    user: EndUser,
    db: DBSession,
) -> CartResponse:
    cart = user_service.update_cart_item_quantity(
        db,
        user=user,
        cart_item_id=cart_item_id,
        payload=payload,
    )
    return CartResponse.model_validate(cart)


@router.delete("/cart/items/{cart_item_id}", response_model=CartResponse)
def remove_cart_item(
    cart_item_id: int,
    user: EndUser,
    db: DBSession,
) -> CartResponse:
    cart = user_service.remove_cart_item(db, user=user, cart_item_id=cart_item_id)
    return CartResponse.model_validate(cart)


@router.post("/checkout", response_model=OrderResponse)
def checkout(
    payload: CheckoutRequest,
    user: EndUser,
    db: DBSession,
) -> OrderResponse:
    order = order_service.checkout_cart(db, user=user, payload=payload)
    return OrderResponse.model_validate(order)


@router.get("/orders", response_model=list[OrderResponse])
def list_orders(user: EndUser, db: DBSession) -> list[OrderResponse]:
    orders = order_service.list_user_orders(db, user_id=user.id)
    return [OrderResponse.model_validate(order) for order in orders]


@router.get("/orders/{order_id}", response_model=OrderResponse)
def get_order(order_id: int, user: EndUser, db: DBSession) -> OrderResponse:
    order = order_service.get_user_order(db, user_id=user.id, order_id=order_id)
    return OrderResponse.model_validate(order)


@router.post("/orders/{order_id}/pay", response_model=OrderResponse)
def simulate_payment(
    order_id: int,
    payload: PaymentSimulationRequest,
    user: EndUser,
    db: DBSession,
) -> OrderResponse:
    order = order_service.simulate_payment(db, user=user, order_id=order_id, payload=payload)
    return OrderResponse.model_validate(order)


@router.get("/requests", response_model=list[ItemRequestResponse])
def list_requests(user: EndUser, db: DBSession) -> list[ItemRequestResponse]:
    requests = user_service.list_user_requests(db, user_id=user.id)
    return [ItemRequestResponse.model_validate(item_request) for item_request in requests]


@router.post("/requests", response_model=ItemRequestResponse)
def create_request(
    payload: ItemRequestCreateRequest,
    user: EndUser,
    db: DBSession,
) -> ItemRequestResponse:
    item_request = user_service.create_user_request(db, user=user, payload=payload)
    return ItemRequestResponse.model_validate(item_request)
