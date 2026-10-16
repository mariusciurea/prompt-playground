"""Reservation: chat with the cinema agent and watch which tools it calls."""

from fastapi import APIRouter, Response

from app.auth.dependencies import AccessUser
from app.core.exceptions import NotFoundError, ServiceUnavailableError
from app.core.state import StateDep
from app.data_models.prompting import AgentMessageIn, ChatStartOut
from app.database.session import SessionDep
from app.db_models import Feature
from app.domain import prompting

router = APIRouter(prefix="/reservation", tags=["reservation"])


@router.post("/session")
async def start(user: AccessUser, state: StateDep) -> ChatStartOut:
    """Start a new conversation with the reservation agent."""
    if state.reservation_agent is None:
        raise ServiceUnavailableError("The agent is not configured on this server.")
    session_id = await state.reservation_agent.create_session(str(user.id))
    return ChatStartOut(session_id=session_id)


@router.post("/message")
async def message(
    data: AgentMessageIn, user: AccessUser, session: SessionDep, state: StateDep
) -> Response:
    """Send a message to the reservation agent and stream its reply and tool calls."""
    runner = state.reservation_agent
    if runner is None or not await runner.owns_session(str(user.id), data.session_id):
        raise NotFoundError("Conversation not found. Start a new one.")
    ticket = await prompting.open_ticket(session, state, user, available=True)
    events = prompting.run_agent_stream(
        state, ticket, runner, Feature.RESERVATION, session_id=data.session_id, message=data.message
    )
    return prompting.stream_response(state, ticket, events)
