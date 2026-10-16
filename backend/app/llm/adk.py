"""Shared ADK model and session-service construction for the agents."""

from google.adk.models import Gemini
from google.adk.sessions import BaseSessionService, DatabaseSessionService, InMemorySessionService
from google.genai import Client

from app.core.settings import Settings


def build_agent_model(settings: Settings) -> Gemini | None:
    """Build the ADK Gemini model, reusing the configured API key; None if unset."""
    if settings.gemini_api_key is None:
        return None
    client = Client(api_key=settings.gemini_api_key.get_secret_value())
    return Gemini(model=settings.agent_model_id, client=client)


def build_session_service(settings: Settings) -> BaseSessionService:
    """Persist agent conversations in Postgres in production, in memory for tests/dev."""
    if settings.redis_url is None and not settings.is_production:
        return InMemorySessionService()
    # ADK manages its own tables (sessions/events); a sync psycopg URL keeps it off asyncpg.
    sync_url = settings.database_url.replace("+asyncpg", "+psycopg")
    return DatabaseSessionService(db_url=sync_url)
