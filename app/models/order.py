from __future__ import annotations

from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import OrderStatus
from app.models.mixins import TimestampMixin


class Order(TimestampMixin, Base):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint("subtotal_amount >= 0", name="subtotal_non_negative"),
        CheckConstraint("delivery_fee >= 0", name="delivery_fee_non_negative"),
        CheckConstraint("total_amount >= 0", name="total_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    order_number: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    cart_id: Mapped[int | None] = mapped_column(
        ForeignKey("carts.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
        index=True,
    )
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="order_status_enum", native_enum=False),
        nullable=False,
        default=OrderStatus.RECEIVED,
    )
    subtotal_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    delivery_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    delivery_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    out_for_delivery_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship("User", back_populates="orders")
    cart: Mapped[Cart | None] = relationship("Cart", back_populates="order")
    items: Mapped[list[OrderItem]] = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
    )
    payment: Mapped[Payment | None] = relationship(
        "Payment",
        back_populates="order",
        uselist=False,
        cascade="all, delete-orphan",
    )
