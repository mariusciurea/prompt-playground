"""Orchestrate the Skills Lab: install skills (optionally gated by the scanner) and debrief runs."""

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.skills_lab.catalog import CATALOG, HideTechnique, get_skill
from app.agents.skills_lab.debrief import Debrief, build_debrief
from app.agents.skills_lab.defenses import DEFENSES_KEY, DefenseConfig
from app.agents.skills_lab.scanner import scan_skill
from app.agents.skills_lab.workspace import new_workspace_state
from app.core.exceptions import NotFoundError
from app.crud import activity
from app.db_models import User

_CUSTOM_ALLOWED_TOOLS = ("list_files", "read_file")


@dataclass(frozen=True, slots=True)
class ResolvedSkill:
    """A skill ready to install into a session."""

    name: str
    description: str
    body: str
    allowed_tools: tuple[str, ...]
    malicious: bool
    technique: HideTechnique


async def _resolve(
    session: AsyncSession, user: User, catalog_names: list[str], custom_ids: list[uuid.UUID]
) -> list[ResolvedSkill]:
    resolved: list[ResolvedSkill] = []
    for name in catalog_names:
        skill = get_skill(name)
        if skill is None:
            raise NotFoundError(f"No catalog skill named '{name}'.")
        resolved.append(
            ResolvedSkill(
                skill.name,
                skill.description,
                skill.body,
                skill.allowed_tools,
                skill.malicious,
                skill.technique,
            )
        )
    for skill_id in custom_ids:
        custom = await activity.get_custom_skill(session, user.id, skill_id)
        if custom is None:
            raise NotFoundError("Custom skill not found.")
        # A user's own skill is "malicious" for debrief purposes if the scanner flags it.
        header = f"---\nname: {custom.name}\n---\n\n"
        suspicious = scan_skill(header + custom.body).is_suspicious
        resolved.append(
            ResolvedSkill(
                name=custom.name,
                description=custom.description,
                body=custom.body,
                allowed_tools=_CUSTOM_ALLOWED_TOOLS,
                malicious=suspicious,
                technique=HideTechnique.NONE,
            )
        )
    return resolved


@dataclass(frozen=True, slots=True)
class LabSession:
    """The initial state and bookkeeping for a new lab session."""

    state: dict[str, Any]
    installed: list[str]
    blocked_by_scanner: list[str]


async def build_session_state(
    session: AsyncSession,
    user: User,
    *,
    catalog_names: list[str],
    custom_ids: list[uuid.UUID],
    defenses: DefenseConfig,
) -> LabSession:
    """Resolve the chosen skills into session state, gating installs when the scanner is on."""
    resolved = await _resolve(session, user, catalog_names, custom_ids)
    available: dict[str, Any] = {}
    techniques: dict[str, str] = {}
    installed: list[str] = []
    blocked: list[str] = []
    for skill in resolved:
        if defenses.scanner and scan_skill(_full_text(skill)).is_suspicious:
            blocked.append(skill.name)
            continue
        available[skill.name] = {
            "description": skill.description,
            "body": skill.body,
            "allowed_tools": list(skill.allowed_tools),
        }
        techniques[skill.name] = skill.technique.value if skill.malicious else ""
        installed.append(skill.name)

    state = new_workspace_state()
    state["available_skills"] = available
    state["skill_techniques"] = techniques
    state[DEFENSES_KEY] = defenses.to_state()
    return LabSession(state=state, installed=installed, blocked_by_scanner=blocked)


def _full_text(skill: ResolvedSkill) -> str:
    front = f"---\nname: {skill.name}\n---\n\n"
    return front + skill.body


def debrief_from_state(state: dict[str, Any]) -> Debrief:
    """Build the debrief from a finished run's session state."""
    loaded = state.get("loaded_skill")
    techniques: dict[str, str] = state.get("skill_techniques") or {}
    technique_value = techniques.get(loaded or "", "")
    malicious = bool(technique_value)
    technique = HideTechnique(technique_value) if technique_value else HideTechnique.NONE
    return build_debrief(
        malicious=malicious,
        technique=technique,
        attacker_log=state.get("attacker_log") or [],
        outbox=state.get("outbox") or [],
        blocked=state.get("blocked_actions") or [],
        skill_loaded=loaded is not None,
    )


def catalog_names() -> list[str]:
    """Names of the built-in catalog skills."""
    return [skill.name for skill in CATALOG]
