from fastapi import APIRouter, Depends

from app.core.csrf import enforce_csrf_protection
from app.core.dependencies import DBSession, VendorUser
from app.schemas.platform import (
    ItemRequestResponse,
    OrderResponse,
    OrderStatusUpdateRequest,
    ProductResponse,
    VendorProductCreateRequest,
    VendorProductUpdateRequest,
)
from app.services import orders as order_service
from app.services import vendor as vendor_service


router = APIRouter(
    prefix="/api/vendor",
    tags=["vendor"],
    dependencies=[Depends(enforce_csrf_protection)],
)


@router.get("/products", response_model=list[ProductResponse])
def list_products(vendor_user: VendorUser, db: DBSession) -> list[ProductResponse]:
    products = vendor_service.list_vendor_products(db, vendor_user=vendor_user)
    return [ProductResponse.model_validate(product) for product in products]


@router.post("/products", response_model=ProductResponse)
def create_product(
    payload: VendorProductCreateRequest,
    vendor_user: VendorUser,
    db: DBSession,
) -> ProductResponse:
    product = vendor_service.create_vendor_product(db, vendor_user=vendor_user, payload=payload)
    return ProductResponse.model_validate(product)


@router.patch("/products/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    payload: VendorProductUpdateRequest,
    vendor_user: VendorUser,
    db: DBSession,
) -> ProductResponse:
    product = vendor_service.update_vendor_product(
        db,
        vendor_user=vendor_user,
        product_id=product_id,
        payload=payload,
    )
    return ProductResponse.model_validate(product)


@router.get("/requests", response_model=list[ItemRequestResponse])
def list_requests(vendor_user: VendorUser, db: DBSession) -> list[ItemRequestResponse]:
    requests = vendor_service.list_vendor_requests(db, vendor_user=vendor_user)
    return [ItemRequestResponse.model_validate(item_request) for item_request in requests]


@router.get("/orders", response_model=list[OrderResponse])
def list_orders(vendor_user: VendorUser, db: DBSession) -> list[OrderResponse]:
    orders = order_service.list_vendor_orders(db, vendor_user=vendor_user)
    return [OrderResponse.model_validate(order) for order in orders]


@router.patch("/orders/{order_id}/status", response_model=OrderResponse)
def update_order_status(
    order_id: int,
    payload: OrderStatusUpdateRequest,
    vendor_user: VendorUser,
    db: DBSession,
) -> OrderResponse:
    order = order_service.update_order_status(
        db,
        actor_user=vendor_user,
        order_id=order_id,
        payload=payload,
    )
    return OrderResponse.model_validate(order)
