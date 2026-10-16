"""Scheduled clean-up: drop stale data so the database respects the retention policy.

Run as a Railway cron: `python -m app.tasks.retention`.
"""

import asyncio
import logging
from datetime import timedelta
from typing import Any, cast

from sqlalchemy import CursorResult, delete, not_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.logging import configure_logging
from app.core.settings import Settings, get_settings
from app.database.base import utcnow
from app.database.session import create_engine, create_session_factory
from app.db_models import Cohort, CohortMember, PromptHistory, User

logger = logging.getLogger(__name__)

Factory = async_sessionmaker[AsyncSession]


async def purge_unverified_accounts(factory: Factory, settings: Settings) -> int:
    """Delete accounts that never confirmed their e-mail within the allowed window."""
    cutoff = utcnow() - timedelta(hours=settings.unverified_account_ttl_hours)
    async with factory() as session:
        result = await session.execute(
            delete(User).where(User.email_verified_at.is_(None), User.created_at < cutoff)
        )
        await session.commit()
        return cast(CursorResult[Any], result).rowcount


async def purge_expired_history(factory: Factory, settings: Settings) -> int:
    """Delete history for users whose newest cohort ended more than the retention window ago."""
    cutoff = utcnow() - timedelta(days=settings.history_retention_days)
    async with factory() as session:
        # Users still in a cohort that ended recently (or is ongoing) keep their history.
        active_emails = (
            select(CohortMember.email)
            .join(Cohort, Cohort.id == CohortMember.cohort_id)
            .where(Cohort.ends_at > cutoff)
        )
        keep_user_ids = select(User.id).where(User.email.in_(active_emails))
        result = await session.execute(
            delete(PromptHistory).where(not_(PromptHistory.user_id.in_(keep_user_ids)))
        )
        await session.commit()
        return cast(CursorResult[Any], result).rowcount


async def run() -> None:
    """Execute every retention task once."""
    settings = get_settings()
    engine = create_engine(settings.database_url)
    try:
        factory = create_session_factory(engine)
        accounts = await purge_unverified_accounts(factory, settings)
        history = await purge_expired_history(factory, settings)
        logger.info("Retention: removed %d unverified accounts, %d history rows", accounts, history)
    finally:
        await engine.dispose()


def main() -> None:
    """Configure logging and run the retention tasks."""
    settings = get_settings()
    configure_logging(settings.log_level, json_format=settings.log_json)
    asyncio.run(run())


if __name__ == "__main__":
    main()
