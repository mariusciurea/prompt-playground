"""Data access operations for users."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db_models import Role, User


async def get_by_id(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    """Return a user by ID."""
    return await session.get(User, user_id)


async def get_by_email(session: AsyncSession, email: str) -> User | None:
    """Return a user by (normalized) e-mail."""
    return await session.scalar(select(User).where(User.email == email))


async def create(
    session: AsyncSession, *, email: str, password_hash: str, role: Role = Role.STUDENT
) -> User:
    """Add a new, unverified user to the session."""
    user = User(email=email, password_hash=password_hash, role=role)
    session.add(user)
    await session.flush()
    return user
