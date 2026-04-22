from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import RequestStatus
from app.models.mixins import TimestampMixin


class Request(TimestampMixin, Base):
    __tablename__ = "requests"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint(
            "budget_amount IS NULL OR budget_amount >= 0",
            name="budget_non_negative",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    vendor_id: Mapped[int | None] = mapped_column(
        ForeignKey("vendors.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    quantity: Mapped[int] = mapped_column(nullable=False, default=1)
    desired_event_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    budget_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    status: Mapped[RequestStatus] = mapped_column(
        Enum(RequestStatus, name="request_status_enum", native_enum=False),
        nullable=False,
        default=RequestStatus.PENDING,
    )
    admin_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped[User] = relationship("User", back_populates="requests")
    vendor: Mapped[Vendor | None] = relationship("Vendor", back_populates="requests")
    product: Mapped[Product | None] = relationship("Product", back_populates="requests")
    category: Mapped[Category | None] = relationship("Category", back_populates="requests")
