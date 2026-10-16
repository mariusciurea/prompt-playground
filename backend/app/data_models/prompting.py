"""Schemas for the LLM features: Playground, Engage, agents, history."""

import uuid
from datetime import datetime
from typing import Annotated, Any

from pydantic import Field, StringConstraints

from app.data_models.common import Schema
from app.db_models import Feature


class PlaygroundIn(Schema):
    """A Playground run request."""

    system_prompt: Annotated[str, StringConstraints(max_length=20_000)] = ""
    user_prompt: Annotated[str, StringConstraints(min_length=1, max_length=20_000)]
    temperature: Annotated[float, Field(ge=0.0, le=2.0)] = 1.0


class ExampleOut(Schema):
    """A ready-made Playground example."""

    id: str
    label: str
    system_prompt: str
    user_prompt: str


class EngageLevelOut(Schema):
    """Public view of an Engage level (never the password or system prompt)."""

    number: int
    title: str
    solved: bool
    lesson: str | None


class EngageMessageIn(Schema):
    """A message to an Engage level's hidden assistant."""

    level: Annotated[int, Field(ge=1, le=99)]
    message: Annotated[str, StringConstraints(min_length=1, max_length=20_000)]


class EngageGuessIn(Schema):
    """A password guess for a level."""

    level: Annotated[int, Field(ge=1, le=99)]
    guess: Annotated[str, StringConstraints(min_length=1, max_length=200)]


class EngageGuessOut(Schema):
    """The result of a guess."""

    correct: bool
    lesson: str | None


class ChatStartOut(Schema):
    """A newly created agent conversation."""

    session_id: str


class AgentMessageIn(Schema):
    """A message to an agent conversation."""

    session_id: Annotated[str, StringConstraints(min_length=1, max_length=128)]
    message: Annotated[str, StringConstraints(min_length=1, max_length=20_000)]


class HistoryItemOut(Schema):
    """One stored exchange."""

    id: uuid.UUID
    feature: Feature
    request: dict[str, Any]
    response: str
    details: dict[str, Any]
    created_at: datetime
