from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import MembershipStatus, MembershipTier
from app.models.mixins import TimestampMixin


class Membership(TimestampMixin, Base):
    __tablename__ = "memberships"
    __table_args__ = (CheckConstraint("price >= 0", name="price_non_negative"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tier: Mapped[MembershipTier] = mapped_column(
        Enum(MembershipTier, name="membership_tier_enum", native_enum=False),
        nullable=False,
        default=MembershipTier.BASIC,
    )
    status: Mapped[MembershipStatus] = mapped_column(
        Enum(MembershipStatus, name="membership_status_enum", native_enum=False),
        nullable=False,
        default=MembershipStatus.PENDING,
    )
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    auto_renew: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    user: Mapped[User] = relationship("User", back_populates="memberships")
