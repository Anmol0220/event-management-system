from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import Role
from app.models.mixins import TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Role] = mapped_column(
        Enum(Role, name="role_enum", native_enum=False),
        nullable=False,
        default=Role.USER,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    vendor_profile: Mapped[Vendor | None] = relationship(
        "Vendor",
        back_populates="user",
        uselist=False,
    )
    carts: Mapped[list[Cart]] = relationship("Cart", back_populates="user")
    orders: Mapped[list[Order]] = relationship("Order", back_populates="user")
    memberships: Mapped[list[Membership]] = relationship("Membership", back_populates="user")
    requests: Mapped[list[Request]] = relationship("Request", back_populates="user")
    product_status_changes: Mapped[list[ProductStatusHistory]] = relationship(
        "ProductStatusHistory",
        back_populates="changed_by",
    )
