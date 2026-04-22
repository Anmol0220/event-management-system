from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ProductStatus


class ProductStatusHistory(Base):
    __tablename__ = "product_status_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    changed_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    old_status: Mapped[ProductStatus] = mapped_column(
        Enum(ProductStatus, name="product_status_enum", native_enum=False),
        nullable=False,
    )
    new_status: Mapped[ProductStatus] = mapped_column(
        Enum(ProductStatus, name="product_status_enum", native_enum=False),
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    product: Mapped[Product] = relationship("Product", back_populates="status_history")
    changed_by: Mapped[User | None] = relationship("User", back_populates="product_status_changes")
