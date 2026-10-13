from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utcnow() -> datetime:
    """Naive UTC datetime — хранится в БД без таймзоны."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(unique=True, index=True, nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Europe/Moscow")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)


class Pair(Base):
    __tablename__ = "pairs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    source: Mapped[str] = mapped_column(
        String(8), nullable=False, default="USER", server_default="USER"
    )  # USER | VERB
    verb_base: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    is_orphaned: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    english: Mapped[str] = mapped_column(String(500), nullable=False)
    russian: Mapped[str] = mapped_column(String(500), nullable=False)
    normalized_english: Mapped[str] = mapped_column(String(500), nullable=False)
    normalized_russian: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    cards: Mapped[list["Card"]] = relationship(
        back_populates="pair", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (
        Index("ix_pairs_user_deleted", "user_id", "deleted_at"),
        Index("ix_pairs_user_source_deleted", "user_id", "source", "deleted_at"),
    )


class Card(Base):
    __tablename__ = "cards"

    id: Mapped[int] = mapped_column(primary_key=True)
    pair_id: Mapped[int] = mapped_column(ForeignKey("pairs.id"), nullable=False, index=True)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)  # EN_RU | RU_EN
    state: Mapped[str] = mapped_column(String(16), nullable=False, default="NEW")
    due_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    pair: Mapped[Pair] = relationship(back_populates="cards")

    __table_args__ = (
        UniqueConstraint("pair_id", "direction", name="ux_card_pair_direction"),
        Index("ix_cards_state_due", "state", "due_at"),
    )


class StudySession(Base):
    __tablename__ = "study_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    session_type: Mapped[str] = mapped_column(
        String(8), nullable=False, default="USER", server_default="USER"
    )  # USER | VERB
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE")
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    cards: Mapped[list["SessionCard"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="SessionCard.position",
    )

    __table_args__ = (
        Index("ix_sessions_user_status", "user_id", "status"),
        Index("ix_sessions_user_status_type", "user_id", "status", "session_type"),
    )


class SessionCard(Base):
    __tablename__ = "session_cards"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("study_sessions.id"), nullable=False, index=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id"), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    review_type: Mapped[str] = mapped_column(String(16), nullable=False)  # REQUIRED | ARCHIVE
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="PENDING")  # PENDING | ANSWERED

    session: Mapped[StudySession] = relationship(back_populates="cards")
    card: Mapped[Card] = relationship()

    __table_args__ = (
        UniqueConstraint("session_id", "card_id", name="ux_session_card"),
        Index("ix_session_card_position", "session_id", "position"),
    )


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id"), nullable=False)
    session_id: Mapped[Optional[int]] = mapped_column(ForeignKey("study_sessions.id"), nullable=True)
    shown_value: Mapped[str] = mapped_column(Text, nullable=False)
    expected_answer: Mapped[str] = mapped_column(Text, nullable=False)
    user_answer: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    state_before: Mapped[str] = mapped_column(String(16), nullable=False)
    state_after: Mapped[str] = mapped_column(String(16), nullable=False)
    review_type: Mapped[str] = mapped_column(String(16), nullable=False)  # REQUIRED | ARCHIVE | EARLY
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_reviews_user_created", "user_id", "created_at"),
        Index("ix_reviews_card_created", "card_id", "created_at"),
    )
    