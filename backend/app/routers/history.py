"""The signed-in user's prompt history."""

from fastapi import APIRouter, status

from app.auth.dependencies import AccessUser
from app.crud import activity
from app.data_models.common import Page
from app.data_models.prompting import HistoryItemOut
from app.database.session import SessionDep
from app.db_models import Feature
from app.routers.helpers import PaginationDep

router = APIRouter(prefix="/history", tags=["history"])


@router.get("")
async def list_history(
    user: AccessUser, session: SessionDep, page: PaginationDep, feature: Feature | None = None
) -> Page[HistoryItemOut]:
    """Return the user's saved exchanges, newest first."""
    rows, total = await activity.list_history(
        session, user.id, feature=feature, limit=page.limit, offset=page.offset
    )
    return Page(
        items=[HistoryItemOut.model_validate(row) for row in rows],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def clear_history(user: AccessUser, session: SessionDep) -> None:
    """Delete all of the user's history."""
    await activity.clear_history(session, user.id)
