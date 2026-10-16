"""Data access operations for refresh tokens and single-use e-mail tokens."""

import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base import utcnow
from app.db_models import EmailToken, EmailTokenPurpose, RefreshToken


async def add_refresh_token(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    family_id: uuid.UUID,
    token_hash: str,
    expires_at: datetime,
) -> RefreshToken:
    """Store a new refresh token."""
    token = RefreshToken(
        user_id=user_id, family_id=family_id, token_hash=token_hash, expires_at=expires_at
    )
    session.add(token)
    await session.flush()
    return token


async def get_refresh_token(session: AsyncSession, token_hash: str) -> RefreshToken | None:
    """Return a refresh token by hash, locking the row for rotation."""
    return await session.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash).with_for_update()
    )


async def revoke_family(session: AsyncSession, family_id: uuid.UUID) -> None:
    """Revoke every token of one login session."""
    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )


async def revoke_all_for_user(session: AsyncSession, user_id: uuid.UUID) -> None:
    """Revoke every refresh token of a user (sign out everywhere)."""
    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )


async def add_email_token(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    purpose: EmailTokenPurpose,
    token_hash: str,
    expires_at: datetime,
    password_hash: str | None = None,
) -> EmailToken:
    """Store a new single-use e-mail token."""
    token = EmailToken(
        user_id=user_id,
        purpose=purpose,
        token_hash=token_hash,
        expires_at=expires_at,
        password_hash=password_hash,
    )
    session.add(token)
    await session.flush()
    return token


async def consume_email_token(
    session: AsyncSession, token_hash: str, purpose: EmailTokenPurpose
) -> EmailToken | None:
    """Mark a valid, unused, unexpired token as used and return it."""
    now = utcnow()
    token = await session.scalar(
        select(EmailToken)
        .where(
            EmailToken.token_hash == token_hash,
            EmailToken.purpose == purpose,
            EmailToken.used_at.is_(None),
            EmailToken.expires_at > now,
        )
        .with_for_update()
    )
    if token is not None:
        token.used_at = now
    return token


async def invalidate_email_tokens(
    session: AsyncSession, user_id: uuid.UUID, purpose: EmailTokenPurpose
) -> None:
    """Mark all unused tokens of a purpose as used."""
    await session.execute(
        update(EmailToken)
        .where(
            EmailToken.user_id == user_id,
            EmailToken.purpose == purpose,
            EmailToken.used_at.is_(None),
        )
        .values(used_at=utcnow())
    )
