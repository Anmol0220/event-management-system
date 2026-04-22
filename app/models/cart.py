from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import CartStatus
from app.models.mixins import TimestampMixin


class Cart(TimestampMixin, Base):
    __tablename__ = "carts"
    __table_args__ = (
        CheckConstraint("subtotal_amount >= 0", name="subtotal_non_negative"),
        CheckConstraint("total_amount >= 0", name="total_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[CartStatus] = mapped_column(
        Enum(CartStatus, name="cart_status_enum", native_enum=False),
        nullable=False,
        default=CartStatus.ACTIVE,
    )
    subtotal_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    checked_out_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship("User", back_populates="carts")
    items: Mapped[list[CartItem]] = relationship(
        "CartItem",
        back_populates="cart",
        cascade="all, delete-orphan",
    )
    order: Mapped[Order | None] = relationship("Order", back_populates="cart", uselist=False)
