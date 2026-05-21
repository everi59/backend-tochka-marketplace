import uuid
from datetime import datetime
from sqlalchemy import String, Text, Integer, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List
from app.infrastructure.database.models.base import Base


class Banner(Base):
    """Баннер на главной странице"""
    __tablename__ = "banners"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    subtitle: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    image_url: Mapped[str] = mapped_column(String(512), nullable=False)
    link_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    events: Mapped[List["BannerEvent"]] = relationship(
        "BannerEvent",
        back_populates="banner",
        cascade="all, delete-orphan"
    )


class BannerEvent(Base):
    """Событие аналитики баннера (показы, клики)"""
    __tablename__ = "banner_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    banner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("banners.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )  # 'impression', 'click'
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True
    )
    session_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, index=True)

    banner: Mapped["Banner"] = relationship(
        "Banner",
        back_populates="events"
    )