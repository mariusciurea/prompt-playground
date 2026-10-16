"""Shared schema types."""

from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field


def _normalize_email(value: str) -> str:
    return value.strip().lower()


Email = Annotated[EmailStr, Field(max_length=254), AfterValidator(_normalize_email)]
"""A validated, lower-cased e-mail address."""


class Schema(BaseModel):
    """Base schema: forbid unknown fields and strip surrounding whitespace."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, from_attributes=True)


class Page[T](Schema):
    """A page of results."""

    items: list[T]
    total: int
    limit: int
    offset: int


class MessageOut(Schema):
    """A user-facing confirmation message."""

    message: str
