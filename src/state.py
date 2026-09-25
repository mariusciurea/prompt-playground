"""Typed access to Streamlit session state and shared service instances."""

from dataclasses import dataclass, field

import streamlit as st

from src.agent.agent import ReservationAgentService, ToolCall
from src.config import get_settings
from src.models import ModelResponse
from src.services import AIService, create_ai_service


@dataclass
class PlaygroundState:
    responses: list[ModelResponse] = field(default_factory=list)


@dataclass
class EngageState:
    level: int = 1
    responses: dict[int, list[ModelResponse]] = field(default_factory=dict)
    solved: set[int] = field(default_factory=set)
    # (streamlit alert kind, message) shown once after a password check.
    feedback: tuple[str, str] | None = None


@dataclass
class ChatMessage:
    role: str
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)


@dataclass
class ReservationState:
    messages: list[ChatMessage] = field(default_factory=list)


def _session_object[T](key: str, factory: type[T]) -> T:
    if key not in st.session_state:
        st.session_state[key] = factory()
    return st.session_state[key]


def playground_state() -> PlaygroundState:
    return _session_object("_playground_state", PlaygroundState)


def engage_state() -> EngageState:
    return _session_object("_engage_state", EngageState)


def reservation_state() -> ReservationState:
    return _session_object("_reservation_state", ReservationState)


@st.cache_resource(show_spinner=False)
def _cached_ai_service() -> AIService:
    return create_ai_service(get_settings())


def get_ai_service() -> tuple[AIService | None, str | None]:
    """Return ``(service, None)`` or ``(None, user-facing error)`` if misconfigured."""
    try:
        return _cached_ai_service(), None
    except ValueError as exc:
        return None, str(exc)


def get_reservation_agent() -> tuple[ReservationAgentService | None, str | None]:
    """Return this session's agent, creating it on first use."""
    if "_reservation_agent" not in st.session_state:
        try:
            st.session_state["_reservation_agent"] = ReservationAgentService(get_settings())
        except ValueError as exc:
            return None, str(exc)
    return st.session_state["_reservation_agent"], None
