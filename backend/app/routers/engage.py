"""Engage: a prompt-injection game. Passwords and system prompts stay on the server."""

from fastapi import APIRouter, Response

from app.auth.dependencies import AccessUser
from app.content.engage_levels import ENGAGE_LEVELS, EngageLevel
from app.core.exceptions import NotFoundError
from app.core.state import StateDep
from app.crud import activity
from app.data_models.prompting import (
    EngageGuessIn,
    EngageGuessOut,
    EngageLevelOut,
    EngageMessageIn,
)
from app.database.session import SessionDep
from app.db_models import Feature
from app.domain import prompting
from app.llm.gemini import PromptRequest

router = APIRouter(prefix="/engage", tags=["engage"])


def _level(number: int) -> EngageLevel:
    if not 1 <= number <= len(ENGAGE_LEVELS):
        raise NotFoundError("No such level.")
    return ENGAGE_LEVELS[number - 1]


@router.get("/levels")
async def levels(user: AccessUser, session: SessionDep) -> list[EngageLevelOut]:
    """List levels with the user's progress; the lesson shows only once solved."""
    solved = await activity.solved_levels(session, user.id)
    return [
        EngageLevelOut(
            number=index,
            title=level.title,
            solved=index in solved,
            lesson=level.lesson if index in solved else None,
        )
        for index, level in enumerate(ENGAGE_LEVELS, start=1)
    ]


@router.post("/message")
async def message(
    data: EngageMessageIn, user: AccessUser, session: SessionDep, state: StateDep
) -> Response:
    """Send a message to a level's hidden assistant and stream the reply."""
    level = _level(data.level)
    ticket = await prompting.open_ticket(session, state, user, available=state.llm is not None)
    prompt = PromptRequest(user_prompt=data.message, system_prompt=level.system_prompt)
    request = {"level": data.level, "message": data.message}
    events = prompting.run_llm_stream(state, ticket, Feature.ENGAGE, prompt, request)
    return prompting.stream_response(state, ticket, events)


@router.post("/guess")
async def guess(data: EngageGuessIn, user: AccessUser, session: SessionDep) -> EngageGuessOut:
    """Check a password guess; record the level as solved when correct."""
    level = _level(data.level)
    if not level.is_correct(data.guess):
        return EngageGuessOut(correct=False, lesson=None)
    await activity.mark_solved(session, user.id, data.level)
    return EngageGuessOut(correct=True, lesson=level.lesson)
