"""Declarative base and shared column helpers for ORM models."""

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, MetaData, Uuid, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def utcnow() -> datetime:
    """Return the current time as an aware UTC datetime."""
    return datetime.now(UTC)


def str_enum(cls: type[StrEnum]) -> Enum:
    """Store a StrEnum as its values in a VARCHAR column (no native PG enum to migrate)."""
    return Enum(cls, native_enum=False, length=32, values_callable=lambda e: [m.value for m in e])


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    type_annotation_map = {datetime: DateTime(timezone=True)}


class UUIDPrimaryKey:
    """Mixin adding a random UUID primary key (no guessable sequential IDs)."""

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)


class CreatedAt:
    """Mixin adding a server-side creation timestamp."""

    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), default=utcnow)
