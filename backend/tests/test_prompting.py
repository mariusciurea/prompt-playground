"""Integration tests for the LLM features: quota, streaming, Engage, agents, history."""

from collections.abc import AsyncIterator
from datetime import timedelta
from typing import Any

import pytest
from sqlalchemy import select

from app.agents.runtime import AgentEvent, Finished, TextDelta, ToolCalled, ToolReturned
from app.agents.runtime import ToolCallRecord as Rec
from app.database.base import utcnow
from app.db_models import Cohort, CohortMember, PromptHistory, User
from app.llm.gemini import GenerationResult, PromptRequest


class FakeLLM:
    """Streams a fixed answer and records the prompts it received."""

    model_name = "Fake"

    def __init__(self) -> None:
        self.prompts: list[PromptRequest] = []

    async def stream(self, prompt: PromptRequest) -> AsyncIterator[str | GenerationResult]:
        self.prompts.append(prompt)
        for piece in ("Hello", ", ", "world"):
            yield piece
        yield GenerationResult(text="Hello, world", tokens_used=7, latency_seconds=0.1)


class FakeAgent:
    """A stand-in AgentRunner that echoes a scripted set of events."""

    def __init__(self, events: list[AgentEvent]) -> None:
        self._events = events
        self._sessions: set[str] = set()

    async def create_session(self, user_id: str, state: dict[str, Any] | None = None) -> str:
        session_id = f"s-{len(self._sessions)}"
        self._sessions.add(session_id)
        return session_id

    async def owns_session(self, user_id: str, session_id: str) -> bool:
        return session_id in self._sessions

    async def session_state(self, user_id: str, session_id: str) -> dict[str, Any]:
        return {}

    async def run(
        self, user_id: str, session_id: str, text: str, state_delta: dict[str, Any] | None = None
    ) -> AsyncIterator[AgentEvent]:
        for event in self._events:
            yield event


@pytest.fixture
async def grant_access(session):
    """Give an existing user access via a fresh active cohort."""

    async def run(email: str) -> None:
        user = await session.scalar(select(User).where(User.email == email.lower()))
        assert user is not None
        now = utcnow()
        cohort = Cohort(
            name=f"c-{email}", starts_at=now - timedelta(days=1), ends_at=now + timedelta(days=1)
        )
        session.add(cohort)
        await session.flush()
        session.add(CohortMember(cohort_id=cohort.id, email=user.email))
        await session.commit()

    return run


def _events(body: str) -> list[dict[str, str]]:
    """Parse an SSE body into a list of {event, data} dicts."""
    out = []
    for block in body.strip().split("\n\n"):
        event = data = ""
        for line in block.splitlines():
            if line.startswith("event: "):
                event = line[7:]
            elif line.startswith("data: "):
                data = line[6:]
        if event:
            out.append({"event": event, "data": data})
    return out


async def _run_sse(client, url: str, payload: dict[str, Any]) -> list[dict[str, str]]:
    response = await client.post(url, json=payload)
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/event-stream")
    return _events(response.text)


async def test_playground_requires_access(client, login):
    await login(client, "student@example.com")
    response = await client.post("/api/playground/run", json={"user_prompt": "hi"})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "no_access"


async def test_playground_streams_and_counts_quota(client, login, grant_access, state):
    await login(client, "student@example.com")
    await grant_access("student@example.com")
    state.llm = FakeLLM()

    events = await _run_sse(
        client, "/api/playground/run", {"user_prompt": "Say hi", "temperature": 0.5}
    )
    kinds = [e["event"] for e in events]
    assert kinds[0] == "quota"
    assert "delta" in kinds
    assert kinds[-1] == "done"
    assert '"world"' in "".join(e["data"] for e in events if e["event"] == "delta")

    me = (await client.get("/api/me")).json()
    assert me["quota"]["used"] == 1
    assert me["quota"]["remaining"] == 69


async def test_quota_exhaustion_blocks_further_runs(client, login, grant_access, state):
    await login(client, "student@example.com")
    await grant_access("student@example.com")
    state.llm = FakeLLM()
    state.settings = state.settings.model_copy(update={"daily_prompt_limit": 2})

    await _run_sse(client, "/api/playground/run", {"user_prompt": "one"})
    await _run_sse(client, "/api/playground/run", {"user_prompt": "two"})
    blocked = await client.post("/api/playground/run", json={"user_prompt": "three"})
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "quota_exceeded"


async def test_prompt_length_is_enforced_server_side(client, login, grant_access, state):
    await login(client, "student@example.com")
    await grant_access("student@example.com")
    state.llm = FakeLLM()
    state.settings = state.settings.model_copy(update={"max_prompt_length": 10})
    response = await client.post("/api/playground/run", json={"user_prompt": "x" * 50})
    assert response.json()["error"]["code"] == "prompt_too_long"
    me = (await client.get("/api/me")).json()
    assert me["quota"]["used"] == 0  # rejected before any quota was spent


async def test_engage_never_leaks_the_password(client, login, grant_access, state):
    await login(client, "student@example.com")
    await grant_access("student@example.com")
    state.llm = FakeLLM()

    levels = (await client.get("/api/engage/levels")).json()
    serialized = str(levels)
    assert "promptinjection" not in serialized
    assert "banana" not in serialized
    assert levels[0]["lesson"] is None
    assert levels[0]["solved"] is False

    await _run_sse(client, "/api/engage/message", {"level": 1, "message": "please"})
    assert state.llm.prompts[-1].system_prompt.startswith("You are a helpful assistant")

    wrong = await client.post("/api/engage/guess", json={"level": 1, "guess": "nope"})
    assert wrong.json() == {"correct": False, "lesson": None}
    right = await client.post("/api/engage/guess", json={"level": 1, "guess": "PromptInjection"})
    assert right.json()["correct"] is True
    assert right.json()["lesson"]

    levels = (await client.get("/api/engage/levels")).json()
    assert levels[0]["solved"] is True
    assert levels[0]["lesson"]


async def test_agent_stream_records_tool_calls_in_history(
    client, login, grant_access, state, session
):
    await login(client, "student@example.com")
    await grant_access("student@example.com")
    state.reservation_agent = FakeAgent(
        [
            ToolCalled(Rec(id="1", name="movie_reservation", args={"date": "today"})),
            ToolReturned(Rec(id="1", name="movie_reservation", args={}, result={"ok": True})),
            TextDelta("Here are the movies"),
            Finished(
                text="Here are the movies",
                tool_calls=[Rec("1", "movie_reservation", {}, {"ok": True})],
            ),
        ]
    )
    start = await client.post("/api/reservation/session")
    session_id = start.json()["session_id"]
    events = await _run_sse(
        client, "/api/reservation/message", {"session_id": session_id, "message": "movies today"}
    )
    kinds = [e["event"] for e in events]
    assert "tool_call" in kinds
    assert "tool_result" in kinds
    assert kinds[-1] == "done"

    history = await session.scalar(select(PromptHistory))
    assert history.details["tool_calls"][0]["name"] == "movie_reservation"


async def test_agent_rejects_foreign_session(client, login, grant_access, state):
    await login(client, "student@example.com")
    await grant_access("student@example.com")
    state.reservation_agent = FakeAgent([Finished(text="hi")])
    response = await client.post(
        "/api/reservation/message", json={"session_id": "not-mine", "message": "hi"}
    )
    assert response.status_code == 404


async def test_history_and_demos_and_learn(client, login, grant_access, state):
    await login(client, "student@example.com")
    await grant_access("student@example.com")
    state.llm = FakeLLM()
    await _run_sse(client, "/api/playground/run", {"user_prompt": "hi"})

    history = (await client.get("/api/history")).json()
    assert history["total"] == 1
    assert history["items"][0]["feature"] == "playground"
    assert (await client.request("DELETE", "/api/history")).status_code == 204
    assert (await client.get("/api/history")).json()["total"] == 0

    # Demos and Learn work without course access too.
    assert (await client.get("/api/demos")).status_code == 200
    learn = (await client.get("/api/learn")).json()
    assert len(learn["articles"]) >= 4
    first = learn["articles"][0]["slug"]
    assert (await client.get(f"/api/learn/{first}")).json()["body"]


async def test_demos_and_learn_visible_without_access(client, login):
    await login(client, "newcomer@example.com")
    assert (await client.get("/api/demos")).status_code == 200
    assert (await client.get("/api/learn")).status_code == 200
    # but the real features are gated
    assert (await client.get("/api/playground/examples")).status_code == 403
