import uuid
from datetime import datetime
from sqlalchemy import String, Text, Integer, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List
from app.infrastructure.database.models.base import Base


class Sku(Base):
    __tablename__ = "skus"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    product: Mapped["Product"] = relationship(
        "Product",
        back_populates="skus"
    )
    images: Mapped[List["SkuImage"]] = relationship(
        "SkuImage",
        back_populates="sku",
        cascade="all, delete-orphan"
    )
    characteristics: Mapped[List["SkuCharacteristic"]] = relationship(
        "SkuCharacteristic",
        back_populates="sku",
        cascade="all, delete-orphan"
    )
    cart_items: Mapped[List["CartItem"]] = relationship(
        "CartItem",
        back_populates="sku",
        cascade="all, delete-orphan"
    )
    order_items: Mapped[List["OrderItem"]] = relationship(
        "OrderItem",
        back_populates="sku",
        cascade="all, delete-orphan"
    )
    invoice_items: Mapped[List["InvoiceItem"]] = relationship(
        "InvoiceItem",
        back_populates="sku",
        cascade="all, delete-orphan"
    )


class SkuImage(Base):
    __tablename__ = "sku_images"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    sku_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("skus.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    url: Mapped[str] = mapped_column(String(512), nullable=False)
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    sku: Mapped["Sku"] = relationship(
        "Sku",
        back_populates="images"
    )


class SkuCharacteristic(Base):
    __tablename__ = "sku_characteristics"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    sku_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("skus.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    sku: Mapped["Sku"] = relationship(
        "Sku",
        back_populates="characteristics"
    )