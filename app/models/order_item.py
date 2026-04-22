from __future__ import annotations

from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class OrderItem(TimestampMixin, Base):
    __tablename__ = "order_items"
    __table_args__ = (CheckConstraint("quantity > 0", name="quantity_positive"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    vendor_id: Mapped[int | None] = mapped_column(
        ForeignKey("vendors.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    vendor_business_name: Mapped[str] = mapped_column(String(255), nullable=False)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    product_sku: Mapped[str | None] = mapped_column(String(80), nullable=True)
    quantity: Mapped[int] = mapped_column(nullable=False, default=1)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    order: Mapped[Order] = relationship("Order", back_populates="items")
    product: Mapped[Product | None] = relationship("Product", back_populates="order_items")
