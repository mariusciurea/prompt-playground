"""Cohorts, their pre-approved e-mails, and access requests."""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, UniqueConstraint, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, CreatedAt, UUIDPrimaryKey, str_enum


class AccessRequestStatus(StrEnum):
    """Lifecycle of an access request."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class Cohort(UUIDPrimaryKey, CreatedAt, Base):
    """A course group whose members have access between `starts_at` and `ends_at`."""

    __tablename__ = "cohorts"
    __table_args__ = (CheckConstraint("ends_at > starts_at", name="dates_ordered"),)

    name: Mapped[str] = mapped_column(String(120), unique=True)
    starts_at: Mapped[datetime]
    ends_at: Mapped[datetime]
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), index=True
    )


class CohortMember(UUIDPrimaryKey, CreatedAt, Base):
    """A pre-approved e-mail in a cohort; matched to users by e-mail."""

    __tablename__ = "cohort_members"
    __table_args__ = (UniqueConstraint("cohort_id", "email"),)

    cohort_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("cohorts.id", ondelete="CASCADE"), index=True
    )
    email: Mapped[str] = mapped_column(String(320), index=True)
    added_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
    invited_at: Mapped[datetime | None]
    revoked_at: Mapped[datetime | None]


class AccessRequest(UUIDPrimaryKey, CreatedAt, Base):
    """A user's request to be granted course access."""

    __tablename__ = "access_requests"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    message: Mapped[str] = mapped_column(String(500), default="")
    status: Mapped[AccessRequestStatus] = mapped_column(
        str_enum(AccessRequestStatus),
        default=AccessRequestStatus.PENDING,
    )
    cohort_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("cohorts.id", ondelete="SET NULL")
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
    reviewed_at: Mapped[datetime | None]


Index(
    "uq_access_requests_one_pending",
    AccessRequest.user_id,
    unique=True,
    postgresql_where=text("status = 'pending'"),
)
