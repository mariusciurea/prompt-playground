"""Process-wide application state and the FastAPI dependencies that expose it."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated

import httpx
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.rate_limit import RateLimiter
from app.core.settings import Settings
from app.core.store import Store

if TYPE_CHECKING:
    from app.agents.runtime import AgentRunner
    from app.domain.email import EmailSender
    from app.llm.gemini import LLMService


@dataclass
class AppState:
    """Long-lived resources created at startup and closed at shutdown."""

    settings: Settings
    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]
    store: Store
    rate_limiter: RateLimiter
    http: httpx.AsyncClient
    email: "EmailSender"
    llm: "LLMService | None"
    reservation_agent: "AgentRunner | None"
    skills_lab_agent: "AgentRunner | None"


def get_state(request: Request) -> AppState:
    """Return the application state."""
    state: AppState = request.app.state.app_state
    return state


def get_settings_dep(state: Annotated[AppState, Depends(get_state)]) -> Settings:
    """Return the settings."""
    return state.settings


def get_client_ip(
    request: Request, settings: Annotated[Settings, Depends(get_settings_dep)]
) -> str:
    """Return the client IP, preferring the configured trusted proxy header."""
    if settings.client_ip_header:
        forwarded = request.headers.get(settings.client_ip_header)
        if forwarded:
            return forwarded.strip()
    return request.client.host if request.client else "unknown"


StateDep = Annotated[AppState, Depends(get_state)]
SettingsDep = Annotated[Settings, Depends(get_settings_dep)]
ClientIpDep = Annotated[str, Depends(get_client_ip)]
