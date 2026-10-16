"""Audit log endpoint (admins only)."""

from fastapi import APIRouter

from app.auth.dependencies import AdminUser
from app.crud import audit
from app.data_models.admin import AuditOut
from app.data_models.common import Page
from app.database.session import SessionDep
from app.routers.helpers import PaginationDep

router = APIRouter(prefix="/audit")


@router.get("")
async def list_audit(
    _: AdminUser, session: SessionDep, page: PaginationDep, action: str | None = None
) -> Page[AuditOut]:
    """List audit entries, newest first."""
    rows, total = await audit.list_entries(
        session, action=action, limit=page.limit, offset=page.offset
    )
    items = [
        AuditOut(
            id=entry.id,
            actor_email=email,
            action=entry.action,
            target=entry.target,
            details=entry.details,
            ip=entry.ip,
            created_at=entry.created_at,
        )
        for entry, email in rows
    ]
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)
