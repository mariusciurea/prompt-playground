"""Request and response schemas for authentication."""

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import Field, StringConstraints

from app.data_models.common import Email, Schema
from app.db_models import Role, User
from app.domain.passwords import MAX_PASSWORD_LENGTH, MIN_PASSWORD_LENGTH

NewPassword = Annotated[
    str,
    StringConstraints(
        min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH, strip_whitespace=False
    ),
]
CurrentPassword = Annotated[
    str, StringConstraints(min_length=1, max_length=MAX_PASSWORD_LENGTH, strip_whitespace=False)
]
TurnstileToken = Annotated[str | None, Field(default=None, max_length=4096)]
OpaqueToken = Annotated[str, StringConstraints(min_length=20, max_length=128)]
TotpCode = Annotated[str, StringConstraints(pattern=r"^\d{6}$")]


class RegisterIn(Schema):
    """Create an account."""

    email: Email
    password: NewPassword
    turnstile_token: TurnstileToken


class LoginIn(Schema):
    """Sign in; `totp_code` is required for accounts with two-factor enabled."""

    email: Email
    password: CurrentPassword
    turnstile_token: TurnstileToken
    totp_code: TotpCode | None = None


class EmailIn(Schema):
    """An e-mail-triggered action, such as a password reset request."""

    email: Email
    turnstile_token: TurnstileToken


class TokenIn(Schema):
    """A token received by e-mail."""

    token: OpaqueToken


class ResetPasswordIn(Schema):
    """Choose a new password with a reset token."""

    token: OpaqueToken
    new_password: NewPassword


class TotpCodeIn(Schema):
    """A 6-digit authenticator code."""

    code: TotpCode


class TotpSetupOut(Schema):
    """Secret and provisioning URI for an authenticator app."""

    secret: str
    otpauth_uri: str


class CsrfOut(Schema):
    """The CSRF token to echo in the X-CSRF-Token header."""

    csrf_token: str


class UserOut(Schema):
    """Public view of an account."""

    id: uuid.UUID
    email: str
    role: Role
    email_verified: bool
    totp_enabled: bool
    created_at: datetime

    @classmethod
    def from_user(cls, user: User) -> "UserOut":
        """Build the public view of a user."""
        return cls(
            id=user.id,
            email=user.email,
            role=user.role,
            email_verified=user.email_verified_at is not None,
            totp_enabled=user.totp_enabled_at is not None,
            created_at=user.created_at,
        )


class DeleteAccountIn(Schema):
    """Confirm account deletion with the current password."""

    password: CurrentPassword
