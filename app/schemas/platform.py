from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import (
    CartStatus,
    MembershipStatus,
    MembershipTier,
    OrderStatus,
    PaymentStatus,
    ProductStatus,
    RequestStatus,
    Role,
    VendorStatus,
)
from app.utils.sanitization import sanitize_multiline_text, sanitize_single_line_text


class CategorySummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    description: str | None
    is_active: bool


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    role: Role
    is_active: bool
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime


class VendorMiniResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    business_name: str
    status: VendorStatus


class VendorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    business_name: str
    contact_phone: str | None
    description: str | None
    status: VendorStatus
    created_at: datetime
    updated_at: datetime
    user: UserResponse
    category: CategorySummaryResponse | None


class ProductMiniResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    sku: str
    unit_price: Decimal
    image_url: str | None
    status: ProductStatus


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    sku: str
    description: str | None
    unit_price: Decimal
    inventory_count: int
    image_url: str | None
    status: ProductStatus
    created_at: datetime
    updated_at: datetime
    vendor: VendorMiniResponse
    category: CategorySummaryResponse


class UserAdminUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    role: Role | None = None
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, value: str | None) -> str | None:
        return sanitize_single_line_text(value)


class VendorAdminUpdateRequest(BaseModel):
    business_name: str | None = Field(default=None, min_length=2, max_length=255)
    contact_phone: str | None = Field(default=None, max_length=30)
    description: str | None = Field(default=None, max_length=2000)
    category_id: int | None = Field(default=None, gt=0)
    status: VendorStatus | None = None

    @field_validator("business_name", "contact_phone")
    @classmethod
    def sanitize_single_line_fields(cls, value: str | None) -> str | None:
        return sanitize_single_line_text(value)

    @field_validator("description")
    @classmethod
    def sanitize_description(cls, value: str | None) -> str | None:
        return sanitize_multiline_text(value)


class MembershipCreateRequest(BaseModel):
    user_id: int = Field(..., gt=0)
    tier: MembershipTier
    status: MembershipStatus = MembershipStatus.ACTIVE
    price: Decimal = Field(..., ge=0)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    auto_renew: bool = False


class MembershipUpdateRequest(BaseModel):
    tier: MembershipTier | None = None
    status: MembershipStatus | None = None
    price: Decimal | None = Field(default=None, ge=0)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    auto_renew: bool | None = None


class MembershipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tier: MembershipTier
    status: MembershipStatus
    price: Decimal
    starts_at: datetime | None
    ends_at: datetime | None
    auto_renew: bool
    created_at: datetime
    updated_at: datetime
    user: UserResponse


class AdminProductStatusUpdateRequest(BaseModel):
    status: ProductStatus
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("notes")
    @classmethod
    def sanitize_notes(cls, value: str | None) -> str | None:
        return sanitize_multiline_text(value)


class VendorProductCreateRequest(BaseModel):
    category_id: int = Field(..., gt=0)
    name: str = Field(..., min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    unit_price: Decimal = Field(..., ge=0)
    inventory_count: int = Field(default=0, ge=0)
    image_url: str | None = Field(default=None, max_length=500)
    slug: str | None = Field(default=None, max_length=280)
    sku: str | None = Field(default=None, max_length=80)
    status: ProductStatus | None = None

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, value: str) -> str:
        sanitized = sanitize_single_line_text(value)
        if sanitized is None:
            raise ValueError("Product name is required.")
        return sanitized

    @field_validator("description")
    @classmethod
    def sanitize_description(cls, value: str | None) -> str | None:
        return sanitize_multiline_text(value)

    @field_validator("image_url", "slug", "sku")
    @classmethod
    def sanitize_optional_single_line_fields(cls, value: str | None) -> str | None:
        return sanitize_single_line_text(value)


class VendorProductUpdateRequest(BaseModel):
    category_id: int | None = Field(default=None, gt=0)
    name: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    unit_price: Decimal | None = Field(default=None, ge=0)
    inventory_count: int | None = Field(default=None, ge=0)
    image_url: str | None = Field(default=None, max_length=500)
    slug: str | None = Field(default=None, max_length=280)
    sku: str | None = Field(default=None, max_length=80)
    status: ProductStatus | None = None

    @field_validator("name", "image_url", "slug", "sku")
    @classmethod
    def sanitize_optional_single_line_fields(cls, value: str | None) -> str | None:
        return sanitize_single_line_text(value)

    @field_validator("description")
    @classmethod
    def sanitize_description(cls, value: str | None) -> str | None:
        return sanitize_multiline_text(value)


class CartItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    quantity: int
    unit_price: Decimal
    line_total: Decimal
    product: ProductMiniResponse


class CartResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: CartStatus
    subtotal_amount: Decimal
    total_amount: Decimal
    checked_out_at: datetime | None
    created_at: datetime
    updated_at: datetime
    items: list[CartItemResponse]


class AddCartItemRequest(BaseModel):
    product_id: int = Field(..., gt=0)
    quantity: int = Field(default=1, gt=0)


class UpdateCartItemRequest(BaseModel):
    quantity: int = Field(..., gt=0)


class CheckoutRequest(BaseModel):
    delivery_address: str = Field(..., min_length=10, max_length=4000)
    notes: str | None = Field(default=None, max_length=2000)
    payment_method: str = Field(default="simulation", min_length=3, max_length=50)

    @field_validator("delivery_address")
    @classmethod
    def sanitize_delivery_address(cls, value: str) -> str:
        sanitized = sanitize_multiline_text(value)
        if sanitized is None:
            raise ValueError("Delivery address is required.")
        return sanitized

    @field_validator("notes")
    @classmethod
    def sanitize_notes(cls, value: str | None) -> str | None:
        return sanitize_multiline_text(value)

    @field_validator("payment_method")
    @classmethod
    def sanitize_payment_method(cls, value: str) -> str:
        sanitized = sanitize_single_line_text(value)
        if sanitized is None:
            raise ValueError("Payment method is required.")
        return sanitized.lower()


class PaymentSimulationRequest(BaseModel):
    succeed: bool = True
    provider_message: str | None = Field(default=None, max_length=1000)

    @field_validator("provider_message")
    @classmethod
    def sanitize_provider_message(cls, value: str | None) -> str | None:
        return sanitize_multiline_text(value)


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    amount: Decimal
    payment_method: str
    status: PaymentStatus
    transaction_reference: str | None
    provider_response: str | None
    processed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class OrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int | None
    vendor_id: int | None
    vendor_business_name: str
    product_name: str
    product_sku: str | None
    quantity: int
    unit_price: Decimal
    line_total: Decimal
    created_at: datetime
    updated_at: datetime


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_number: str
    status: OrderStatus
    subtotal_amount: Decimal
    delivery_fee: Decimal
    total_amount: Decimal
    delivery_address: str | None
    notes: str | None
    received_at: datetime
    ready_at: datetime | None
    out_for_delivery_at: datetime | None
    delivered_at: datetime | None
    created_at: datetime
    updated_at: datetime
    user: UserResponse
    items: list[OrderItemResponse]
    payment: PaymentResponse | None


class OrderStatusUpdateRequest(BaseModel):
    status: OrderStatus
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("notes")
    @classmethod
    def sanitize_notes(cls, value: str | None) -> str | None:
        return sanitize_multiline_text(value)


class ItemRequestCreateRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    quantity: int = Field(default=1, gt=0)
    desired_event_date: date | None = None
    budget_amount: Decimal | None = Field(default=None, ge=0)
    vendor_id: int | None = Field(default=None, gt=0)
    product_id: int | None = Field(default=None, gt=0)
    category_id: int | None = Field(default=None, gt=0)

    @field_validator("title")
    @classmethod
    def sanitize_title(cls, value: str) -> str:
        sanitized = sanitize_single_line_text(value)
        if sanitized is None:
            raise ValueError("Request title is required.")
        return sanitized

    @field_validator("description")
    @classmethod
    def sanitize_description(cls, value: str | None) -> str | None:
        return sanitize_multiline_text(value)

    @model_validator(mode="after")
    def validate_targets(self) -> "ItemRequestCreateRequest":
        if not any([self.vendor_id, self.product_id, self.category_id]):
            raise ValueError("At least one of vendor_id, product_id, or category_id is required.")
        return self


class ItemRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    quantity: int
    desired_event_date: date | None
    budget_amount: Decimal | None
    status: RequestStatus
    admin_notes: str | None
    created_at: datetime
    updated_at: datetime
    user: UserResponse
    vendor: VendorMiniResponse | None
    product: ProductMiniResponse | None
    category: CategorySummaryResponse | None
