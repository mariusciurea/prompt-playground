"""Account lifecycle: registration, verification, sign-in, token rotation, password reset."""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

import httpx
from disposable_email_domains import blocklist as disposable_domains
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import jwt, totp
from app.auth.security import generate_token, hash_password, hash_token, verify_password
from app.core.exceptions import (
    AppError,
    AuthenticationError,
    ConflictError,
    PermissionDeniedError,
    RateLimitedError,
)
from app.core.settings import Settings
from app.core.store import Store
from app.crud import tokens, users
from app.database.base import utcnow
from app.db_models import EmailTokenPurpose, Role, User
from app.domain import email as emails
from app.domain.passwords import check_password

logger = logging.getLogger(__name__)

VERIFY_TOKEN_TTL = timedelta(hours=24)
RESET_TOKEN_TTL = timedelta(minutes=30)
REFRESH_REUSE_GRACE = timedelta(seconds=30)
FREE_LOGIN_FAILURES = 5
LOCK_BASE = timedelta(seconds=30)
LOCK_MAX = timedelta(minutes=15)

_INVALID_CREDENTIALS = "Invalid e-mail or password."
_INVALID_LINK = "This link is invalid or has expired."


class EmailNotVerifiedError(PermissionDeniedError):
    """The account exists but its e-mail is not confirmed."""

    code = "email_not_verified"


class TotpRequiredError(AuthenticationError):
    """The account needs a two-factor code to sign in."""

    code = "totp_required"


class DisposableEmailError(AppError):
    """The address belongs to a throwaway e-mail provider."""

    code = "disposable_email"


class InvalidTokenError(AppError):
    """An e-mailed link is invalid, used, or expired."""

    code = "invalid_token"


class StaleRefreshError(ConflictError):
    """A refresh token was just rotated by a parallel request; retry with the new cookies."""

    code = "refresh_stale"


@dataclass(frozen=True, slots=True)
class IssuedTokens:
    """A fresh access token and its rotating refresh token."""

    access: str
    refresh: str


def _link(settings: Settings, path: str, token: str | None = None) -> str:
    # Tokens travel in the URL fragment so they never reach server or proxy logs.
    base = settings.public_base_url.rstrip("/")
    return f"{base}{path}#token={token}" if token else f"{base}{path}"


async def register(
    session: AsyncSession, *, email: str, password: str, settings: Settings, http: httpx.AsyncClient
) -> emails.EmailMessage | None:
    """Create an unverified account and return the e-mail to send.

    The response to the caller never reveals whether the address was taken;
    the e-mail tells the inbox owner instead.
    """
    if email.rsplit("@", 1)[-1] in disposable_domains:
        raise DisposableEmailError("Please use a permanent e-mail address.")
    await check_password(password, email, http)
    password_hash = await hash_password(password)

    user = await users.get_by_email(session, email)
    if user is not None and user.email_verified_at is not None:
        return emails.account_exists_email(
            email, _link(settings, "/login"), _link(settings, "/forgot-password")
        )
    try:
        if user is None:
            user = await users.create(session, email=email, password_hash=password_hash)
        token = generate_token()
        await tokens.add_email_token(
            session,
            user_id=user.id,
            purpose=EmailTokenPurpose.VERIFY_EMAIL,
            token_hash=hash_token(token),
            expires_at=utcnow() + VERIFY_TOKEN_TTL,
            password_hash=password_hash,
        )
        await session.commit()
    except IntegrityError:  # a parallel registration for the same address won the race
        await session.rollback()
        return None
    return emails.verification_email(email, _link(settings, "/verify-email", token))


async def verify_email(session: AsyncSession, token: str) -> User:
    """Confirm an address; the password chosen with this token becomes the account's."""
    row = await tokens.consume_email_token(
        session, hash_token(token), EmailTokenPurpose.VERIFY_EMAIL
    )
    user = await users.get_by_id(session, row.user_id) if row else None
    if row is None or user is None:
        raise InvalidTokenError(_INVALID_LINK)
    if user.email_verified_at is None:
        user.email_verified_at = utcnow()
        if row.password_hash:
            user.password_hash = row.password_hash
        await tokens.invalidate_email_tokens(session, user.id, EmailTokenPurpose.VERIFY_EMAIL)
    await session.commit()
    return user


async def login(
    session: AsyncSession,
    *,
    email: str,
    password: str,
    totp_code: str | None,
    settings: Settings,
    store: Store,
) -> tuple[User, IssuedTokens]:
    """Check credentials (and 2FA) and start a new session."""
    user = await users.get_by_email(session, email)
    now = utcnow()
    if user is not None and user.locked_until and user.locked_until > now:
        raise RateLimitedError(retry_after=int((user.locked_until - now).total_seconds()) + 1)

    valid, new_hash = await verify_password(password, user.password_hash if user else None)
    if user is None:
        raise AuthenticationError(_INVALID_CREDENTIALS)
    if not valid:
        await _record_failure(session, user)
        raise AuthenticationError(_INVALID_CREDENTIALS)
    if not user.is_active:
        raise PermissionDeniedError("This account is disabled.")
    if user.email_verified_at is None:
        raise EmailNotVerifiedError("Please confirm your e-mail address first.")
    if user.totp_enabled_at is not None:
        if not totp_code:
            raise TotpRequiredError("Enter the code from your authenticator app.")
        secret = totp.decrypt_secret(user.totp_secret_encrypted or "", settings)
        if not await totp.verify_code(secret, totp_code, replay_key=str(user.id), store=store):
            await _record_failure(session, user)
            raise AuthenticationError("Invalid authentication code.")

    if new_hash:
        user.password_hash = new_hash
    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = now
    issued = await _issue_tokens(session, user, settings)
    await session.commit()
    return user, issued


async def _record_failure(session: AsyncSession, user: User) -> None:
    user.failed_login_count += 1
    extra = user.failed_login_count - FREE_LOGIN_FAILURES
    if extra >= 0:
        user.locked_until = utcnow() + min(LOCK_BASE * (2**extra), LOCK_MAX)
    await session.commit()


async def _issue_tokens(
    session: AsyncSession,
    user: User,
    settings: Settings,
    *,
    family_id: uuid.UUID | None = None,
    expires_at: datetime | None = None,
) -> IssuedTokens:
    refresh = generate_token()
    await tokens.add_refresh_token(
        session,
        user_id=user.id,
        family_id=family_id or uuid.uuid4(),
        token_hash=hash_token(refresh),
        expires_at=expires_at or utcnow() + timedelta(days=settings.refresh_token_expire_days),
    )
    return IssuedTokens(access=jwt.create_access_token(user.id, settings), refresh=refresh)


async def refresh(
    session: AsyncSession, raw_token: str, settings: Settings
) -> tuple[User, IssuedTokens]:
    """Rotate a refresh token; reusing an old token revokes the whole session."""
    row = await tokens.get_refresh_token(session, hash_token(raw_token))
    now = utcnow()
    if row is None or row.revoked_at is not None or row.expires_at <= now:
        raise AuthenticationError("Session expired. Please sign in again.")
    if row.used_at is not None:
        if now - row.used_at <= REFRESH_REUSE_GRACE:
            raise StaleRefreshError("Session was just refreshed.")
        logger.warning("Refresh token reuse detected for user %s", row.user_id)
        await tokens.revoke_family(session, row.family_id)
        await session.commit()
        raise AuthenticationError("Session expired. Please sign in again.")

    user = await users.get_by_id(session, row.user_id)
    if user is None or not user.is_active:
        raise AuthenticationError("Session expired. Please sign in again.")
    row.used_at = now
    # The new token inherits the expiry, so a session lasts at most one refresh lifetime.
    issued = await _issue_tokens(
        session, user, settings, family_id=row.family_id, expires_at=row.expires_at
    )
    await session.commit()
    return user, issued


async def logout(session: AsyncSession, raw_token: str | None) -> None:
    """End the session the refresh token belongs to."""
    if not raw_token:
        return
    row = await tokens.get_refresh_token(session, hash_token(raw_token))
    if row is not None:
        await tokens.revoke_family(session, row.family_id)
        await session.commit()


async def forgot_password(
    session: AsyncSession, email: str, settings: Settings
) -> emails.EmailMessage | None:
    """Return a reset e-mail for verified, active accounts; nothing otherwise."""
    user = await users.get_by_email(session, email)
    if user is None or user.email_verified_at is None or not user.is_active:
        return None
    await tokens.invalidate_email_tokens(session, user.id, EmailTokenPurpose.RESET_PASSWORD)
    token = generate_token()
    await tokens.add_email_token(
        session,
        user_id=user.id,
        purpose=EmailTokenPurpose.RESET_PASSWORD,
        token_hash=hash_token(token),
        expires_at=utcnow() + RESET_TOKEN_TTL,
    )
    await session.commit()
    return emails.password_reset_email(email, _link(settings, "/reset-password", token))


async def reset_password(
    session: AsyncSession, token: str, new_password: str, http: httpx.AsyncClient
) -> None:
    """Set a new password from a reset link and sign out every session."""
    row = await tokens.consume_email_token(
        session, hash_token(token), EmailTokenPurpose.RESET_PASSWORD
    )
    user = await users.get_by_id(session, row.user_id) if row else None
    if row is None or user is None:
        raise InvalidTokenError(_INVALID_LINK)
    await check_password(new_password, user.email, http)
    await _set_password(session, user, new_password)
    await session.commit()


async def change_password(
    session: AsyncSession, user: User, current: str, new: str, http: httpx.AsyncClient
) -> None:
    """Change the password of a signed-in user and sign out every session."""
    valid, _ = await verify_password(current, user.password_hash)
    if not valid:
        raise AuthenticationError("Current password is incorrect.")
    await check_password(new, user.email, http)
    await _set_password(session, user, new)
    await session.commit()


async def _set_password(session: AsyncSession, user: User, password: str) -> None:
    user.password_hash = await hash_password(password)
    user.failed_login_count = 0
    user.locked_until = None
    await tokens.revoke_all_for_user(session, user.id)
    await tokens.invalidate_email_tokens(session, user.id, EmailTokenPurpose.RESET_PASSWORD)


async def delete_account(session: AsyncSession, user: User, password: str) -> None:
    """Delete a user and all their data after re-checking the password."""
    valid, _ = await verify_password(password, user.password_hash)
    if not valid:
        raise AuthenticationError("Password is incorrect.")
    if user.role is Role.ADMIN:
        raise PermissionDeniedError("Admin accounts cannot delete themselves.")
    await session.delete(user)
    await session.commit()


async def start_totp_setup(
    session: AsyncSession, user: User, settings: Settings
) -> tuple[str, str]:
    """Generate a pending TOTP secret; return (secret, otpauth URI)."""
    if user.totp_enabled_at is not None:
        raise ConflictError("Two-factor authentication is already enabled.")
    secret = totp.generate_secret()
    user.totp_secret_encrypted = totp.encrypt_secret(secret, settings)
    await session.commit()
    return secret, totp.provisioning_uri(secret, user.email, settings.app_name)


async def enable_totp(
    session: AsyncSession, user: User, code: str, settings: Settings, store: Store
) -> None:
    """Activate two-factor authentication after the user proves the code works."""
    if user.totp_enabled_at is not None:
        raise ConflictError("Two-factor authentication is already enabled.")
    if user.totp_secret_encrypted is None:
        raise ConflictError("Start the setup first.")
    secret = totp.decrypt_secret(user.totp_secret_encrypted, settings)
    if not await totp.verify_code(secret, code, replay_key=str(user.id), store=store):
        raise AppError("Invalid authentication code.")
    user.totp_enabled_at = utcnow()
    await session.commit()


async def create_admin(session: AsyncSession, email: str, password: str) -> User:
    """Create (or promote) a verified admin account."""
    user = await users.get_by_email(session, email)
    password_hash = await hash_password(password)
    if user is None:
        user = await users.create(
            session, email=email, password_hash=password_hash, role=Role.ADMIN
        )
    else:
        user.role = Role.ADMIN
        user.password_hash = password_hash
    user.email_verified_at = user.email_verified_at or utcnow()
    user.is_active = True
    await session.commit()
    return user
