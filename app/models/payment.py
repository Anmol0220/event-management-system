from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import PaymentStatus
from app.models.mixins import TimestampMixin


class Payment(TimestampMixin, Base):
    __tablename__ = "payments"
    __table_args__ = (CheckConstraint("amount >= 0", name="amount_non_negative"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    payment_method: Mapped[str] = mapped_column(String(50), nullable=False, default="simulation")
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status_enum", native_enum=False),
        nullable=False,
        default=PaymentStatus.PENDING,
    )
    transaction_reference: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
        unique=True,
        index=True,
    )
    provider_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    order: Mapped[Order] = relationship("Order", back_populates="payment")
