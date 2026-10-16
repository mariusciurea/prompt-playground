"""Guard every LLM call: availability, rate limit, one stream per user, and the daily quota.

All checks run before the response starts, so failures reach the client as normal JSON
errors; once streaming, failures are reported as SSE `error` events.
"""

import json
import logging
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING, Any

from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, ConflictError, ServiceUnavailableError
from app.core.rate_limit import LLM_PER_USER
from app.core.state import AppState

if TYPE_CHECKING:
    from app.agents.runtime import AgentRunner
from app.db_models import Feature, PromptHistory, Role, User
from app.domain import quota
from app.domain.quota import QuotaStatus
from app.llm.gemini import GenerationResult, PromptRequest

logger = logging.getLogger(__name__)

_BUSY_TTL = 180


class BusyError(ConflictError):
    """The user already has an answer being generated."""

    code = "busy"


@dataclass(frozen=True, slots=True)
class PromptTicket:
    """A reserved prompt: who, which quota day, and the lock to release."""

    user_id: uuid.UUID
    day: date
    quota: QuotaStatus
    lock_key: str


async def open_ticket(
    session: AsyncSession, state: AppState, user: User, *, available: bool
) -> PromptTicket:
    """Check that a model call may start now and count it against the quota."""
    if not available:
        raise ServiceUnavailableError("The AI model is not configured on this server.")
    if user.role is not Role.ADMIN:
        await state.rate_limiter.hit(LLM_PER_USER, str(user.id))
    lock_key = f"llm_busy:{user.id}"
    if not await state.store.set_if_absent(lock_key, "1", _BUSY_TTL):
        raise BusyError("Please wait until the current answer is finished.")
    try:
        day, status = await quota.reserve(session, user, state.settings)
    except BaseException:
        await state.store.delete(lock_key)
        raise
    return PromptTicket(user_id=user.id, day=day, quota=status, lock_key=lock_key)


async def close_ticket(state: AppState, ticket: PromptTicket, *, refund: bool) -> None:
    """Release the per-user lock and give the prompt back if the model failed."""
    try:
        if refund:
            async with state.session_factory() as session:
                await quota.refund(session, ticket.user_id, ticket.day)
    finally:
        await state.store.delete(ticket.lock_key)


async def save_history(
    state: AppState,
    user_id: uuid.UUID,
    feature: Feature,
    request: dict[str, Any],
    response: str,
    details: dict[str, Any],
) -> None:
    """Store one exchange in the user's history (own session: streaming outlives the request)."""
    async with state.session_factory() as session:
        session.add(
            PromptHistory(
                user_id=user_id,
                feature=feature,
                request=request,
                response=response,
                details=details,
            )
        )
        await session.commit()


async def run_llm_stream(
    state: AppState,
    ticket: PromptTicket,
    feature: Feature,
    prompt: PromptRequest,
    request: dict[str, Any],
) -> AsyncIterator[bytes]:
    """Stream an LLM answer as SSE `delta` events and save the exchange to history."""
    if state.llm is None:
        raise ServiceUnavailableError("The AI model is not configured on this server.")
    answer = ""
    details: dict[str, Any] = {}
    async for piece in state.llm.stream(prompt):
        if isinstance(piece, GenerationResult):
            answer = piece.text
            details = {"tokens_used": piece.tokens_used, "latency_seconds": piece.latency_seconds}
        else:
            yield sse("delta", {"text": piece})
    await save_history(state, ticket.user_id, feature, request, answer, details)
    yield sse("done", {"tokens_used": details.get("tokens_used")})


def sse(event: str, data: BaseModel | dict[str, Any]) -> bytes:
    """Encode one server-sent event."""
    payload = data.model_dump_json() if isinstance(data, BaseModel) else json.dumps(data)
    return f"event: {event}\ndata: {payload}\n\n".encode()


def stream_response(
    state: AppState, ticket: PromptTicket, events: AsyncIterator[bytes]
) -> StreamingResponse:
    """Stream SSE events, then release the ticket (refunding it if the model failed)."""

    async def body() -> AsyncIterator[bytes]:
        refund = False
        try:
            yield sse("quota", _quota_payload(ticket.quota))
            async for chunk in events:
                yield chunk
        except AppError as exc:
            refund = exc.status_code >= 500
            yield sse("error", {"code": exc.code, "message": exc.message})
        except Exception:
            logger.exception("Streaming failed")
            refund = True
            yield sse("error", {"code": "internal_error", "message": "Something went wrong."})
        finally:
            await close_ticket(state, ticket, refund=refund)

    return StreamingResponse(
        body(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )


async def run_agent_stream(
    state: AppState,
    ticket: PromptTicket,
    runner: "AgentRunner",
    feature: Feature,
    *,
    session_id: str,
    message: str,
    state_delta: dict[str, Any] | None = None,
) -> AsyncIterator[bytes]:
    """Stream an agent's events as SSE and save the exchange, with its tool calls, to history."""
    from app.agents.runtime import Finished, TextDelta, ToolCalled, ToolReturned

    answer = ""
    tool_calls: list[dict[str, Any]] = []
    async for event in runner.run(str(ticket.user_id), session_id, message, state_delta):
        if isinstance(event, TextDelta):
            yield sse("delta", {"text": event.text})
        elif isinstance(event, ToolCalled):
            yield sse(
                "tool_call", {"id": event.call.id, "name": event.call.name, "args": event.call.args}
            )
        elif isinstance(event, ToolReturned):
            yield sse(
                "tool_result",
                {"id": event.call.id, "name": event.call.name, "result": event.call.result},
            )
        elif isinstance(event, Finished):
            answer = event.text
            tool_calls = [
                {"name": c.name, "args": c.args, "result": c.result} for c in event.tool_calls
            ]
    await save_history(
        state, ticket.user_id, feature, {"message": message}, answer, {"tool_calls": tool_calls}
    )
    yield sse("done", {"session_id": session_id})


def _quota_payload(status: QuotaStatus) -> dict[str, Any]:
    return {
        "used": status.used,
        "limit": status.limit,
        "remaining": status.remaining,
        "resets_at": status.resets_at.isoformat(),
    }
