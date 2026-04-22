from __future__ import annotations

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import VendorStatus
from app.models.mixins import TimestampMixin


class Vendor(TimestampMixin, Base):
    __tablename__ = "vendors"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    business_name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[VendorStatus] = mapped_column(
        Enum(VendorStatus, name="vendor_status_enum", native_enum=False),
        nullable=False,
        default=VendorStatus.PENDING,
    )

    user: Mapped[User] = relationship("User", back_populates="vendor_profile")
    category: Mapped[Category | None] = relationship("Category", back_populates="vendors")
    products: Mapped[list[Product]] = relationship(
        "Product",
        back_populates="vendor",
        cascade="all, delete-orphan",
    )
    requests: Mapped[list[Request]] = relationship("Request", back_populates="vendor")
