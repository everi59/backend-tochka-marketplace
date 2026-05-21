import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import String, Text, Integer, Float, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List
from app.infrastructure.database.models.base import Base


class OrderStatus(str, PyEnum):
    """Статусы заказа"""
    CREATED = "CREATED"
    PAID = "PAID"
    PROCESSING = "PROCESSING"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"


class Order(Base):
    """Заказ пользователя"""
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )
    status: Mapped[OrderStatus] = mapped_column(
        SQLEnum(OrderStatus),
        default=OrderStatus.CREATED,
        nullable=False
    )
    total_amount: Mapped[float] = mapped_column(Float, nullable=False)
    delivery_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    delivery_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    delivery_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
    paid_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    shipped_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    items: Mapped[List["OrderItem"]] = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan"
    )


class OrderItem(Base):
    """Позиция заказа"""
    __tablename__ = "order_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    sku_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("skus.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)  # Цена на момент заказа
    total: Mapped[float] = mapped_column(Float, nullable=False)  # quantity * price
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    order: Mapped["Order"] = relationship(
        "Order",
        back_populates="items"
    )
    sku: Mapped["Sku"] = relationship(
        "Sku",
        back_populates="order_items"
    )