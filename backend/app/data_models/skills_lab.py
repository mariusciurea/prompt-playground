"""Schemas for the Skills Lab."""

import uuid
from datetime import datetime
from typing import Annotated, Any

from pydantic import Field, StringConstraints

from app.data_models.common import Schema

MAX_SKILL_BODY = 8000
SkillName = Annotated[str, StringConstraints(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$", max_length=64)]


class CatalogSkillOut(Schema):
    """A skill as offered for install (its true nature is not revealed up front)."""

    name: str
    description: str


class CustomSkillIn(Schema):
    """Create or update a private sandbox skill."""

    name: SkillName
    description: Annotated[str, StringConstraints(min_length=1, max_length=200)]
    body: Annotated[str, StringConstraints(min_length=1, max_length=MAX_SKILL_BODY)]


class CustomSkillOut(Schema):
    """A user's private skill."""

    id: uuid.UUID
    name: str
    description: str
    body: str
    created_at: datetime


class ScanIn(Schema):
    """Scan a catalog skill (by name) or raw text."""

    skill_name: str | None = None
    text: Annotated[str | None, StringConstraints(max_length=MAX_SKILL_BODY + 500)] = None


class FindingOut(Schema):
    """One scanner finding."""

    kind: str
    severity: str
    message: str
    excerpt: str


class ScanOut(Schema):
    """Scanner result plus the human/model views for the Inspect panel."""

    suspicious: bool
    max_severity: str
    findings: list[FindingOut]
    as_human_reads: str
    as_model_reads: str


class DefensesIn(Schema):
    """Which defences to enable for a session."""

    scanner: bool = False
    tool_allowlist: bool = False
    egress_allowlist: bool = False
    human_approval: bool = False


class StartLabIn(Schema):
    """Install skills and open a lab session."""

    catalog_skills: list[SkillName] = Field(default_factory=list)
    custom_skill_ids: list[uuid.UUID] = Field(default_factory=list)
    defenses: DefensesIn = Field(default_factory=DefensesIn)


class StartLabOut(Schema):
    """A new lab session."""

    session_id: str
    installed: list[str]
    blocked_by_scanner: list[str]


class LabStateOut(Schema):
    """The observable state of a lab session for the UI panels."""

    workspace: dict[str, str]
    attacker_log: list[dict[str, Any]]
    outbox: list[dict[str, Any]]
    blocked_actions: list[dict[str, Any]]


class DebriefOut(Schema):
    """The 'what just happened' explanation after a run."""

    attacked: bool
    exfiltrated: bool
    steps: list[str]
    technique: str
    stopped_by: list[str]
    learn_slug: str
