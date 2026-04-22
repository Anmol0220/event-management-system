from fastapi import APIRouter, Depends

from app.core.csrf import enforce_csrf_protection
from app.core.dependencies import AdminUser, DBSession
from app.schemas.platform import (
    AdminProductStatusUpdateRequest,
    MembershipCreateRequest,
    MembershipResponse,
    MembershipUpdateRequest,
    OrderResponse,
    OrderStatusUpdateRequest,
    ProductResponse,
    UserAdminUpdateRequest,
    UserResponse,
    VendorAdminUpdateRequest,
    VendorResponse,
)
from app.services import admin as admin_service
from app.services import orders as order_service


router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    dependencies=[Depends(enforce_csrf_protection)],
)


@router.get("/users", response_model=list[UserResponse])
def list_users(_: AdminUser, db: DBSession) -> list[UserResponse]:
    users = admin_service.list_users(db)
    return [UserResponse.model_validate(user) for user in users]


@router.patch("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    payload: UserAdminUpdateRequest,
    _: AdminUser,
    db: DBSession,
) -> UserResponse:
    user = admin_service.update_user(db, user_id=user_id, payload=payload)
    return UserResponse.model_validate(user)


@router.get("/vendors", response_model=list[VendorResponse])
def list_vendors(_: AdminUser, db: DBSession) -> list[VendorResponse]:
    vendors = admin_service.list_vendors(db)
    return [VendorResponse.model_validate(vendor) for vendor in vendors]


@router.patch("/vendors/{vendor_id}", response_model=VendorResponse)
def update_vendor(
    vendor_id: int,
    payload: VendorAdminUpdateRequest,
    _: AdminUser,
    db: DBSession,
) -> VendorResponse:
    vendor = admin_service.update_vendor(db, vendor_id=vendor_id, payload=payload)
    return VendorResponse.model_validate(vendor)


@router.get("/memberships", response_model=list[MembershipResponse])
def list_memberships(_: AdminUser, db: DBSession) -> list[MembershipResponse]:
    memberships = admin_service.list_memberships(db)
    return [MembershipResponse.model_validate(membership) for membership in memberships]


@router.post("/memberships", response_model=MembershipResponse)
def create_membership(
    payload: MembershipCreateRequest,
    _: AdminUser,
    db: DBSession,
) -> MembershipResponse:
    membership = admin_service.create_membership(db, payload=payload)
    return MembershipResponse.model_validate(membership)


@router.patch("/memberships/{membership_id}", response_model=MembershipResponse)
def update_membership(
    membership_id: int,
    payload: MembershipUpdateRequest,
    _: AdminUser,
    db: DBSession,
) -> MembershipResponse:
    membership = admin_service.update_membership(db, membership_id=membership_id, payload=payload)
    return MembershipResponse.model_validate(membership)


@router.patch("/products/{product_id}/status", response_model=ProductResponse)
def update_product_status(
    product_id: int,
    payload: AdminProductStatusUpdateRequest,
    admin_user: AdminUser,
    db: DBSession,
) -> ProductResponse:
    product = admin_service.update_product_status(
        db,
        product_id=product_id,
        actor_user_id=admin_user.id,
        payload=payload,
    )
    return ProductResponse.model_validate(product)


@router.get("/orders", response_model=list[OrderResponse])
def list_orders(_: AdminUser, db: DBSession) -> list[OrderResponse]:
    orders = order_service.list_admin_orders(db)
    return [OrderResponse.model_validate(order) for order in orders]


@router.patch("/orders/{order_id}/status", response_model=OrderResponse)
def update_order_status(
    order_id: int,
    payload: OrderStatusUpdateRequest,
    admin_user: AdminUser,
    db: DBSession,
) -> OrderResponse:
    order = order_service.update_order_status(
        db,
        actor_user=admin_user,
        order_id=order_id,
        payload=payload,
    )
    return OrderResponse.model_validate(order)
