from enum import Enum


class Role(str, Enum):
    ADMIN = "admin"
    VENDOR = "vendor"
    USER = "user"


class VendorStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    SUSPENDED = "suspended"


class ProductStatus(str, Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class CartStatus(str, Enum):
    ACTIVE = "active"
    CHECKED_OUT = "checked_out"
    ABANDONED = "abandoned"


class OrderStatus(str, Enum):
    RECEIVED = "received"
    READY = "ready"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


class MembershipTier(str, Enum):
    BASIC = "basic"
    PREMIUM = "premium"
    VIP = "vip"


class MembershipStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class RequestStatus(str, Enum):
    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    FULFILLED = "fulfilled"
    REJECTED = "rejected"
