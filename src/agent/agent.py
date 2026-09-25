"""Google ADK agent definition and a synchronous wrapper for Streamlit."""

import asyncio
import concurrent.futures
import logging
import os
from collections.abc import Coroutine
from dataclasses import dataclass, field
from typing import Any

from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner
from google.genai import types

from src.agent.prompt import RESERVATION_AGENT_INSTRUCTION
from src.agent.tools import movie_reservation, read_from_disc, save_to_calendar
from src.config import Settings

logger = logging.getLogger(__name__)

APP_NAME = "reservation_app"
USER_ID = "streamlit_user"


class AgentError(RuntimeError):
    """Raised when the agent cannot produce a reply; message is user-safe."""


@dataclass
class ToolCall:
    """A tool invocation made by the agent while answering."""

    name: str
    args: dict[str, Any]
    result: Any = None


@dataclass
class AgentReply:
    """The agent's final answer plus the tools it used to get there."""

    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)


def build_agent(settings: Settings) -> Agent:
    """Create the reservation agent."""
    return Agent(
        name="reservation_agent",
        model=settings.agent_model_id,
        description="A cinema reservation assistant that can book movies and read stored data.",
        instruction=RESERVATION_AGENT_INSTRUCTION,
        tools=[movie_reservation, save_to_calendar, read_from_disc],
    )


def _run_coroutine[T](coro: Coroutine[Any, Any, T]) -> T:
    """Run a coroutine to completion, even if an event loop is already running."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


class ReservationAgentService:
    """Wraps the ADK runner so a Streamlit view can chat with the agent."""

    def __init__(self, settings: Settings) -> None:
        # ADK's google-genai client reads the key from the process environment,
        # while pydantic-settings only loads .env into the Settings object.
        os.environ.setdefault("GEMINI_API_KEY", settings.require_api_key())
        self._runner = InMemoryRunner(agent=build_agent(settings), app_name=APP_NAME)
        self._session_id: str | None = None

    def _ensure_session(self) -> str:
        if self._session_id is None:
            session = _run_coroutine(
                self._runner.session_service.create_session(app_name=APP_NAME, user_id=USER_ID)
            )
            self._session_id = session.id
        return self._session_id

    def send_message(self, text: str) -> AgentReply:
        """Send a user message and return the agent's reply."""
        message = types.Content(role="user", parts=[types.Part(text=text)])
        final_texts: list[str] = []
        other_texts: list[str] = []
        tool_calls: list[ToolCall] = []

        try:
            events = self._runner.run(
                user_id=USER_ID,
                session_id=self._ensure_session(),
                new_message=message,
            )
            for event in events:
                for call in event.get_function_calls():
                    tool_calls.append(ToolCall(call.name, dict(call.args or {})))
                for response in event.get_function_responses():
                    pending = next(
                        (c for c in tool_calls if c.name == response.name and c.result is None),
                        None,
                    )
                    if pending:
                        pending.result = response.response

                if event.partial or not event.content or not event.content.parts:
                    continue
                texts = [part.text for part in event.content.parts if part.text]
                (final_texts if event.is_final_response() else other_texts).extend(texts)
        except Exception as exc:
            logger.exception("Reservation agent failed")
            raise AgentError(f"The reservation agent failed: {exc}") from exc

        reply = "\n".join(final_texts or other_texts)
        return AgentReply(text=reply or "No response.", tool_calls=tool_calls)

    def reset_session(self) -> None:
        """Forget the conversation; the next message starts a fresh session."""
        self._session_id = None
