"""Read-only demos for users without course access."""

from fastapi import APIRouter

from app.auth.dependencies import CurrentUser
from app.content.demos import DEMOS
from app.data_models.common import Schema


class DemoOut(Schema):
    """A canned demo."""

    id: str
    feature: str
    title: str
    prompt: str
    response: str


router = APIRouter(prefix="/demos", tags=["demos"])


@router.get("")
async def list_demos(_: CurrentUser) -> list[DemoOut]:
    """List the pre-generated demos."""
    return [DemoOut.model_validate(demo) for demo in DEMOS]
