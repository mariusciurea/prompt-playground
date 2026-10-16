"""Run Google ADK agents and translate their events into a small, typed stream."""

import logging
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Protocol

from google.adk.agents import Agent
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.runners import Runner
from google.adk.sessions import BaseSessionService
from google.genai import types

from app.llm.gemini import LLMError

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ToolCallRecord:
    """A tool invocation and, once available, its result."""

    id: str
    name: str
    args: dict[str, Any]
    result: Any = None


@dataclass(frozen=True, slots=True)
class TextDelta:
    """A piece of the answer as it streams in."""

    text: str


@dataclass(frozen=True, slots=True)
class ToolCalled:
    """The agent asked for a tool."""

    call: ToolCallRecord


@dataclass(frozen=True, slots=True)
class ToolReturned:
    """A tool finished and returned a result."""

    call: ToolCallRecord


@dataclass(frozen=True, slots=True)
class Finished:
    """The agent's final answer and every tool it used."""

    text: str
    tool_calls: list[ToolCallRecord] = field(default_factory=list)


AgentEvent = TextDelta | ToolCalled | ToolReturned | Finished


class AgentRunner(Protocol):
    """What the routers need from an agent (lets tests swap in fakes)."""

    async def create_session(self, user_id: str, state: dict[str, Any] | None = None) -> str:
        """Start a conversation and return its ID."""
        ...

    async def owns_session(self, user_id: str, session_id: str) -> bool:
        """Whether the conversation exists and belongs to the user."""
        ...

    async def session_state(self, user_id: str, session_id: str) -> dict[str, Any]:
        """Return the conversation's current state."""
        ...

    def run(
        self,
        user_id: str,
        session_id: str,
        text: str,
        state_delta: dict[str, Any] | None = None,
    ) -> AsyncIterator[AgentEvent]:
        """Send a message and stream the agent's events."""
        ...


class AdkAgentRunner:
    """AgentRunner backed by an ADK Runner and a shared session service."""

    def __init__(self, agent: Agent, app_name: str, sessions: BaseSessionService) -> None:
        self._app_name = app_name
        self._sessions = sessions
        self._runner = Runner(app_name=app_name, agent=agent, session_service=sessions)

    async def create_session(self, user_id: str, state: dict[str, Any] | None = None) -> str:
        session = await self._sessions.create_session(
            app_name=self._app_name, user_id=user_id, state=state or {}
        )
        return session.id

    async def owns_session(self, user_id: str, session_id: str) -> bool:
        session = await self._sessions.get_session(
            app_name=self._app_name, user_id=user_id, session_id=session_id
        )
        return session is not None

    async def session_state(self, user_id: str, session_id: str) -> dict[str, Any]:
        session = await self._sessions.get_session(
            app_name=self._app_name, user_id=user_id, session_id=session_id
        )
        return dict(session.state) if session is not None else {}

    async def run(
        self,
        user_id: str,
        session_id: str,
        text: str,
        state_delta: dict[str, Any] | None = None,
    ) -> AsyncIterator[AgentEvent]:
        message = types.Content(role="user", parts=[types.Part(text=text)])
        calls: dict[str, ToolCallRecord] = {}
        streamed: list[str] = []
        final: list[str] = []
        try:
            async for event in self._runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=message,
                state_delta=state_delta,
                run_config=RunConfig(streaming_mode=StreamingMode.SSE),
            ):
                for call in event.get_function_calls():
                    record = ToolCallRecord(
                        id=call.id or uuid.uuid4().hex,
                        name=call.name or "",
                        args=dict(call.args or {}),
                    )
                    calls[record.id] = record
                    yield ToolCalled(record)
                for response in event.get_function_responses():
                    match = calls.get(response.id or "") or next(
                        (c for c in calls.values() if c.name == response.name and c.result is None),
                        None,
                    )
                    if match is not None:
                        match.result = response.response
                        yield ToolReturned(match)
                if not event.content or not event.content.parts:
                    continue
                texts = [p.text for p in event.content.parts if p.text and not p.thought]
                if event.partial:
                    streamed.extend(texts)
                    for piece in texts:
                        yield TextDelta(piece)
                elif event.is_final_response():
                    final.extend(texts)
        except Exception as exc:
            logger.exception("Agent run failed")
            raise LLMError("The agent is unavailable right now. Please try again.") from exc

        answer = "\n".join(final) or "".join(streamed)
        if final and not streamed:
            yield TextDelta(answer)
        yield Finished(text=answer or "No response.", tool_calls=list(calls.values()))
