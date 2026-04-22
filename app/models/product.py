from __future__ import annotations

from decimal import Decimal

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ProductStatus
from app.models.mixins import TimestampMixin


class Product(TimestampMixin, Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("unit_price >= 0", name="unit_price_non_negative"),
        CheckConstraint("inventory_count >= 0", name="inventory_count_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    vendor_id: Mapped[int] = mapped_column(
        ForeignKey("vendors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(280), nullable=False, unique=True, index=True)
    sku: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    inventory_count: Mapped[int] = mapped_column(nullable=False, default=0)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[ProductStatus] = mapped_column(
        Enum(ProductStatus, name="product_status_enum", native_enum=False),
        nullable=False,
        default=ProductStatus.DRAFT,
    )

    vendor: Mapped[Vendor] = relationship("Vendor", back_populates="products")
    category: Mapped[Category] = relationship("Category", back_populates="products")
    cart_items: Mapped[list[CartItem]] = relationship("CartItem", back_populates="product")
    order_items: Mapped[list[OrderItem]] = relationship("OrderItem", back_populates="product")
    requests: Mapped[list[Request]] = relationship("Request", back_populates="product")
    status_history: Mapped[list[ProductStatusHistory]] = relationship(
        "ProductStatusHistory",
        back_populates="product",
        cascade="all, delete-orphan",
    )
