"""Startup and shutdown: create and close the long-lived resources in AppState."""

from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager

import httpx
from fastapi import FastAPI

from app.agents.runtime import AgentRunner
from app.core.rate_limit import RateLimiter
from app.core.settings import Settings
from app.core.state import AppState
from app.core.store import create_store
from app.database.session import create_engine, create_session_factory
from app.domain.email import create_email_sender
from app.llm.adk import build_agent_model, build_session_service
from app.llm.gemini import create_llm_service


def build_lifespan(
    settings: Settings,
) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    """Return a lifespan handler bound to the given settings."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = create_engine(settings.database_url)
        http = httpx.AsyncClient(headers={"User-Agent": settings.app_name})
        store = create_store(settings.redis_url)
        reservation_agent, skills_lab_agent = _build_agents(settings)
        app.state.app_state = AppState(
            settings=settings,
            engine=engine,
            session_factory=create_session_factory(engine),
            store=store,
            rate_limiter=RateLimiter(store),
            http=http,
            email=create_email_sender(settings, http),
            llm=create_llm_service(settings),
            reservation_agent=reservation_agent,
            skills_lab_agent=skills_lab_agent,
        )
        try:
            yield
        finally:
            await http.aclose()
            await store.close()
            await engine.dispose()

    return lifespan


def _build_agents(settings: Settings) -> tuple[AgentRunner | None, AgentRunner | None]:
    """Build the ADK agent runners, or (None, None) when no API key is configured."""
    from app.agents.reservation.agent import APP_NAME as RES_APP
    from app.agents.reservation.agent import build_reservation_agent
    from app.agents.runtime import AdkAgentRunner
    from app.agents.skills_lab.agent import APP_NAME as LAB_APP
    from app.agents.skills_lab.agent import build_skills_lab_agent

    model = build_agent_model(settings)
    if model is None:
        return None, None
    sessions = build_session_service(settings)
    reservation = AdkAgentRunner(build_reservation_agent(model), RES_APP, sessions)
    skills_lab = AdkAgentRunner(build_skills_lab_agent(model), LAB_APP, sessions)
    return reservation, skills_lab
