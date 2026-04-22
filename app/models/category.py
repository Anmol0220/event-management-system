from __future__ import annotations

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class Category(TimestampMixin, Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    slug: Mapped[str] = mapped_column(String(140), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    vendors: Mapped[list[Vendor]] = relationship("Vendor", back_populates="category")
    products: Mapped[list[Product]] = relationship("Product", back_populates="category")
    requests: Mapped[list[Request]] = relationship("Request", back_populates="category")
