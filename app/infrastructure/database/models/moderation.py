import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import String, Text, ForeignKey, Boolean, Enum as SQLEnum, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional
from app.infrastructure.database.models.base import Base


class ModerationStatus(str, PyEnum):
    PENDING = "PENDING"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    BLOCKED = "BLOCKED"
    HARD_BLOCKED = "HARD_BLOCKED"


class ModerationQueue(Base):
    __tablename__ = "moderation_queue"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    product_id: Mapped[str] = mapped_column(
        String(36), nullable=False, unique=True, index=True
    )
    seller_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="PENDING", nullable=False, index=True
    )
    queue_priority: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    json_before: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    json_after: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    blocking_reason_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    moderator_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    moderator_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    field_reports: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    date_created: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    date_updated: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )
    date_moderation: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    blocking_history: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)


class ModerationDecision(Base):
    __tablename__ = "moderation_decisions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    queue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("moderation_queue.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    blocking_reason_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_blocking_reasons.id"), nullable=True
    )
    moderator_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    queue: Mapped["ModerationQueue"] = relationship("ModerationQueue", back_populates="decisions")
    blocking_reason: Mapped[Optional["ProductBlockingReason"]] = relationship(
        "ProductBlockingReason", back_populates="decisions"
    )


class ProductBlockingReason(Base):
    __tablename__ = "product_blocking_reasons"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    decisions: Mapped[List["ModerationDecision"]] = relationship(
        "ModerationDecision", back_populates="blocking_reason"
    )
