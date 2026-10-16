"""User accounts, roles, and authentication tokens."""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import ForeignKey, Index, String, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, CreatedAt, UUIDPrimaryKey, str_enum


class Role(StrEnum):
    """Platform roles, from least to most privileged."""

    STUDENT = "student"
    INSTRUCTOR = "instructor"
    ADMIN = "admin"


class EmailTokenPurpose(StrEnum):
    """What a single-use e-mail token is for."""

    VERIFY_EMAIL = "verify_email"
    RESET_PASSWORD = "reset_password"  # noqa: S105


class User(UUIDPrimaryKey, CreatedAt, Base):
    """A registered account; e-mails are stored lower-cased."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(str_enum(Role), default=Role.STUDENT)
    is_active: Mapped[bool] = mapped_column(default=True)
    email_verified_at: Mapped[datetime | None]
    totp_secret_encrypted: Mapped[str | None] = mapped_column(String(255))
    totp_enabled_at: Mapped[datetime | None]
    failed_login_count: Mapped[int] = mapped_column(default=0)
    locked_until: Mapped[datetime | None]
    last_login_at: Mapped[datetime | None]

    @property
    def is_staff(self) -> bool:
        """Admins and instructors."""
        return self.role in (Role.ADMIN, Role.INSTRUCTOR)


class RefreshToken(UUIDPrimaryKey, CreatedAt, Base):
    """A hashed, rotating refresh token; tokens from one login share a family."""

    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    family_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime]
    used_at: Mapped[datetime | None]
    revoked_at: Mapped[datetime | None]


class EmailToken(UUIDPrimaryKey, CreatedAt, Base):
    """A hashed single-use token sent by e-mail (verification or password reset)."""

    __tablename__ = "email_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    purpose: Mapped[EmailTokenPurpose] = mapped_column(str_enum(EmailTokenPurpose))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    # Verification tokens carry the password chosen at that registration, so whoever
    # controls the inbox decides which password the account ends up with.
    password_hash: Mapped[str | None] = mapped_column(String(255))
    expires_at: Mapped[datetime]
    used_at: Mapped[datetime | None]


Index(
    "ix_users_unverified_created",
    User.created_at,
    postgresql_where=text("email_verified_at IS NULL"),
)
