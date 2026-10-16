"""Database engine and session management.

Provide the SQLAlchemy async engine, the session factory, and a FastAPI
dependency that yields a session per request.
"""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def create_engine(database_url: str) -> AsyncEngine:
    """Create the async engine with sane pool settings."""
    return create_async_engine(database_url, pool_pre_ping=True, pool_size=5, max_overflow=10)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create the session factory bound to an engine."""
    return async_sessionmaker(engine, expire_on_commit=False)


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Yield a session for one request; roll back if the handler fails."""
    factory: async_sessionmaker[AsyncSession] = request.app.state.app_state.session_factory
    async with factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


SessionDep = Annotated[AsyncSession, Depends(get_session)]
