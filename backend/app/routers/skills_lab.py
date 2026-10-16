"""Skills Lab: install skills, scan them, run the assistant, and debrief the attack."""

import uuid

from fastapi import APIRouter, Response, status

from app.agents.skills_lab.catalog import CATALOG, get_skill
from app.agents.skills_lab.defenses import BLOCKED_KEY, DefenseConfig
from app.agents.skills_lab.scanner import normalize_whitespace_report, scan_skill
from app.agents.skills_lab.workspace import ATTACKER_LOG_KEY, OUTBOX_KEY, WORKSPACE_KEY
from app.auth.dependencies import AccessUser
from app.core.exceptions import ConflictError, NotFoundError, ServiceUnavailableError
from app.core.state import StateDep
from app.crud import activity
from app.data_models.prompting import AgentMessageIn
from app.data_models.skills_lab import (
    CatalogSkillOut,
    CustomSkillIn,
    CustomSkillOut,
    DebriefOut,
    FindingOut,
    LabStateOut,
    ScanIn,
    ScanOut,
    StartLabIn,
    StartLabOut,
)
from app.database.session import SessionDep
from app.db_models import CustomSkill, Feature
from app.domain import prompting, skills_lab
from app.domain.skills_lab import debrief_from_state

router = APIRouter(prefix="/skills-lab", tags=["skills lab"])

MAX_CUSTOM_SKILLS = 10


@router.get("/catalog")
async def catalog(_: AccessUser) -> list[CatalogSkillOut]:
    """List the installable catalog skills (as a user would first see them)."""
    return [CatalogSkillOut(name=s.name, description=s.description) for s in CATALOG]


@router.post("/scan")
async def scan(data: ScanIn, user: AccessUser, session: SessionDep) -> ScanOut:
    """Scan a catalog skill or raw text for hidden or suspicious content."""
    if data.skill_name is not None:
        skill = get_skill(data.skill_name)
        if skill is None:
            raise NotFoundError("No such catalog skill.")
        text = skill.full_text
    elif data.text is not None:
        text = data.text
    else:
        raise ConflictError("Provide a skill name or text to scan.")
    result = scan_skill(text)
    views = normalize_whitespace_report(text)
    return ScanOut(
        suspicious=result.is_suspicious,
        max_severity=result.max_severity.value,
        findings=[
            FindingOut(kind=f.kind, severity=f.severity.value, message=f.message, excerpt=f.excerpt)
            for f in result.findings
        ],
        as_human_reads=views["as_human_reads"],
        as_model_reads=views["as_model_reads"],
    )


@router.get("/custom")
async def list_custom(user: AccessUser, session: SessionDep) -> list[CustomSkillOut]:
    """List the user's private sandbox skills."""
    skills = await activity.list_custom_skills(session, user.id)
    return [CustomSkillOut.model_validate(skill) for skill in skills]


@router.post("/custom", status_code=status.HTTP_201_CREATED)
async def create_custom(
    data: CustomSkillIn, user: AccessUser, session: SessionDep
) -> CustomSkillOut:
    """Create a private sandbox skill (bounded in size and count)."""
    if await activity.count_custom_skills(session, user.id) >= MAX_CUSTOM_SKILLS:
        raise ConflictError(f"You can keep at most {MAX_CUSTOM_SKILLS} skills.")
    skill = CustomSkill(
        user_id=user.id, name=data.name, description=data.description, body=data.body
    )
    session.add(skill)
    try:
        await session.commit()
    except Exception as exc:  # unique (user_id, name)
        await session.rollback()
        raise ConflictError("You already have a skill with that name.") from exc
    return CustomSkillOut.model_validate(skill)


@router.delete("/custom/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_custom(skill_id: uuid.UUID, user: AccessUser, session: SessionDep) -> None:
    """Delete one of the user's private skills."""
    skill = await activity.get_custom_skill(session, user.id, skill_id)
    if skill is None:
        raise NotFoundError("Skill not found.")
    await session.delete(skill)
    await session.commit()


@router.post("/session")
async def start(
    data: StartLabIn, user: AccessUser, session: SessionDep, state: StateDep
) -> StartLabOut:
    """Install the chosen skills into a fresh workspace and open a session."""
    if state.skills_lab_agent is None:
        raise ServiceUnavailableError("The agent is not configured on this server.")
    lab = await skills_lab.build_session_state(
        session,
        user,
        catalog_names=data.catalog_skills,
        custom_ids=data.custom_skill_ids,
        defenses=DefenseConfig(**data.defenses.model_dump()),
    )
    session_id = await state.skills_lab_agent.create_session(str(user.id), lab.state)
    return StartLabOut(
        session_id=session_id, installed=lab.installed, blocked_by_scanner=lab.blocked_by_scanner
    )


@router.post("/message")
async def message(
    data: AgentMessageIn, user: AccessUser, session: SessionDep, state: StateDep
) -> Response:
    """Send a message to the Workspace Assistant and stream its reply and tool calls."""
    runner = state.skills_lab_agent
    if runner is None or not await runner.owns_session(str(user.id), data.session_id):
        raise NotFoundError("Lab session not found. Start a new one.")
    ticket = await prompting.open_ticket(session, state, user, available=True)
    events = prompting.run_agent_stream(
        state, ticket, runner, Feature.SKILLS_LAB, session_id=data.session_id, message=data.message
    )
    return prompting.stream_response(state, ticket, events)


@router.get("/session/{session_id}")
async def lab_state(session_id: str, user: AccessUser, state: StateDep) -> LabStateOut:
    """Return the workspace, the attacker's capture log, the outbox, and blocked actions."""
    runner = state.skills_lab_agent
    if runner is None or not await runner.owns_session(str(user.id), session_id):
        raise NotFoundError("Lab session not found.")
    snapshot = await runner.session_state(str(user.id), session_id)
    return LabStateOut(
        workspace=snapshot.get(WORKSPACE_KEY) or {},
        attacker_log=snapshot.get(ATTACKER_LOG_KEY) or [],
        outbox=snapshot.get(OUTBOX_KEY) or [],
        blocked_actions=snapshot.get(BLOCKED_KEY) or [],
    )


@router.get("/session/{session_id}/debrief")
async def debrief(session_id: str, user: AccessUser, state: StateDep) -> DebriefOut:
    """Explain what the loaded skill did, whether it succeeded, and what would stop it."""
    runner = state.skills_lab_agent
    if runner is None or not await runner.owns_session(str(user.id), session_id):
        raise NotFoundError("Lab session not found.")
    snapshot = await runner.session_state(str(user.id), session_id)
    result = debrief_from_state(snapshot)
    return DebriefOut(
        attacked=result.attacked,
        exfiltrated=result.exfiltrated,
        steps=result.steps,
        technique=result.technique,
        stopped_by=result.stopped_by,
        learn_slug=result.learn_slug,
    )
