"""Per-user activity: daily usage, prompt history, Engage progress, custom skills, audit log."""

import uuid
from datetime import date, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, CreatedAt, UUIDPrimaryKey, str_enum


class Feature(StrEnum):
    """Features that consume prompts."""

    PLAYGROUND = "playground"
    ENGAGE = "engage"
    RESERVATION = "reservation"
    SKILLS_LAB = "skills_lab"


class PromptUsage(Base):
    """How many prompts a user sent on a given (quota-zone) day."""

    __tablename__ = "prompt_usage"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    day: Mapped[date] = mapped_column(primary_key=True)
    count: Mapped[int] = mapped_column(default=0)


class PromptHistory(UUIDPrimaryKey, CreatedAt, Base):
    """One LLM exchange, kept for the user's history and admin statistics."""

    __tablename__ = "prompt_history"
    __table_args__ = (Index("ix_prompt_history_user_created", "user_id", "created_at"),)

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"))
    feature: Mapped[Feature] = mapped_column(str_enum(Feature))
    request: Mapped[dict[str, Any]] = mapped_column(JSONB)
    response: Mapped[str] = mapped_column(Text)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class EngageProgress(Base):
    """A solved Engage level."""

    __tablename__ = "engage_progress"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    level: Mapped[int] = mapped_column(primary_key=True)
    solved_at: Mapped[datetime]


class CustomSkill(UUIDPrimaryKey, CreatedAt, Base):
    """A private skill written by a user in the Skills Lab sandbox."""

    __tablename__ = "custom_skills"
    __table_args__ = (UniqueConstraint("user_id", "name"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime | None]


class AuditLog(UUIDPrimaryKey, CreatedAt, Base):
    """A record of a privileged or security-relevant action."""

    __tablename__ = "audit_log"

    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    action: Mapped[str] = mapped_column(String(64), index=True)
    target: Mapped[str | None] = mapped_column(String(320))
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    ip: Mapped[str | None] = mapped_column(String(45))
