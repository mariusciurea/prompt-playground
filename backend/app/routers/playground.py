"""Playground: run a system + user prompt and stream the answer."""

from fastapi import APIRouter, Response

from app.auth.dependencies import AccessUser
from app.content.playground_examples import PLAYGROUND_EXAMPLES
from app.core.exceptions import AppError
from app.core.state import StateDep
from app.data_models.prompting import ExampleOut, PlaygroundIn
from app.database.session import SessionDep
from app.db_models import Feature
from app.domain import prompting
from app.llm.gemini import PromptRequest

router = APIRouter(prefix="/playground", tags=["playground"])


class PromptTooLongError(AppError):
    """A prompt field exceeds the configured limit."""

    code = "prompt_too_long"


@router.get("/examples")
async def examples(_: AccessUser) -> list[ExampleOut]:
    """Return the ready-made example prompts."""
    return [ExampleOut.model_validate(example) for example in PLAYGROUND_EXAMPLES]


@router.post("/run")
async def run(
    data: PlaygroundIn, user: AccessUser, session: SessionDep, state: StateDep
) -> Response:
    """Stream a model answer for the given prompts (one prompt of quota)."""
    limit = state.settings.max_prompt_length
    if len(data.system_prompt) > limit or len(data.user_prompt) > limit:
        raise PromptTooLongError(f"Prompts must be at most {limit} characters.")

    ticket = await prompting.open_ticket(session, state, user, available=state.llm is not None)
    prompt = PromptRequest(
        user_prompt=data.user_prompt,
        system_prompt=data.system_prompt,
        temperature=data.temperature,
    )
    request = {
        "system_prompt": data.system_prompt,
        "user_prompt": data.user_prompt,
        "temperature": data.temperature,
    }
    events = prompting.run_llm_stream(state, ticket, Feature.PLAYGROUND, prompt, request)
    return prompting.stream_response(state, ticket, events)
