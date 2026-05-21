import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import String, Text, ForeignKey, Boolean, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional
from app.infrastructure.database.models.base import Base


class ModerationStatus(str, PyEnum):
    """Статусы модерации"""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    DECLINED = "DECLINED"


class ModerationQueue(Base):
    """Очередь модерации товаров"""
    __tablename__ = "moderation_queue"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    status: Mapped[ModerationStatus] = mapped_column(
        SQLEnum(ModerationStatus),
        default=ModerationStatus.PENDING,
        nullable=False
    )
    moderator_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    product: Mapped["Product"] = relationship(
        "Product",
        back_populates="moderation_queue"
    )
    decisions: Mapped[List["ModerationDecision"]] = relationship(
        "ModerationDecision",
        back_populates="queue",
        cascade="all, delete-orphan"
    )


class ModerationDecision(Base):
    """Решение модератора"""
    __tablename__ = "moderation_decisions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    queue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("moderation_queue.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    decision: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )  # 'approve', 'decline'
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    blocking_reason_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_blocking_reasons.id"),
        nullable=True
    )
    moderator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    queue: Mapped["ModerationQueue"] = relationship(
        "ModerationQueue",
        back_populates="decisions"
    )
    blocking_reason: Mapped[Optional["ProductBlockingReason"]] = relationship(
        "ProductBlockingReason",
        back_populates="decisions"
    )


class ProductBlockingReason(Base):
    """Причины блокировки товаров"""
    __tablename__ = "product_blocking_reasons"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    decisions: Mapped[List["ModerationDecision"]] = relationship(
        "ModerationDecision",
        back_populates="blocking_reason"
    )