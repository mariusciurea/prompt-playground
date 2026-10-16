"""Cohort, member, and import endpoints."""

import uuid

from fastapi import APIRouter, BackgroundTasks, UploadFile, status

from app.core.state import StateDep
from app.crud import cohorts as cohorts_crud
from app.data_models.admin import (
    AddMembersIn,
    AddMembersOut,
    CohortIn,
    CohortOut,
    CohortUpdate,
    ImportPreviewOut,
    InvalidEntryOut,
    MemberOut,
    PasteIn,
)
from app.data_models.common import Email, Page
from app.database.session import SessionDep
from app.db_models import Cohort
from app.domain import staff
from app.domain.email import deliver_many
from app.domain.imports import MAX_IMPORT_BYTES, ParsedEmails, parse_file, parse_text
from app.routers.admin.deps import ActorDep
from app.routers.helpers import PaginationDep

router = APIRouter(prefix="/cohorts")


def _cohort_out(cohort: Cohort, owner_email: str | None, member_count: int) -> CohortOut:
    return CohortOut(
        id=cohort.id,
        name=cohort.name,
        starts_at=cohort.starts_at,
        ends_at=cohort.ends_at,
        owner_id=cohort.owner_id,
        owner_email=owner_email,
        member_count=member_count,
        is_active=cohorts_crud.is_active(cohort),
    )


@router.get("")
async def list_cohorts(actor: ActorDep, session: SessionDep) -> list[CohortOut]:
    """List cohorts the actor manages."""
    rows = await cohorts_crud.list_with_counts(
        session, owner_id=None if actor.is_admin else actor.user.id
    )
    return [_cohort_out(*row) for row in rows]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_cohort(
    data: CohortIn, actor: ActorDep, session: SessionDep, state: StateDep
) -> CohortOut:
    """Create a cohort (admins only)."""
    cohort = await staff.create_cohort(
        session,
        state.store,
        actor,
        name=data.name,
        starts_at=data.starts_at,
        ends_at=data.ends_at,
        owner_id=data.owner_id,
    )
    (row,) = await cohorts_crud.list_with_counts(session, cohort_id=cohort.id)
    return _cohort_out(*row)


@router.patch("/{cohort_id}")
async def update_cohort(
    cohort_id: uuid.UUID, data: CohortUpdate, actor: ActorDep, session: SessionDep, state: StateDep
) -> CohortOut:
    """Rename, reschedule, or reassign a cohort (admins only)."""
    cohort = await staff.get_managed_cohort(session, actor, cohort_id)
    await staff.update_cohort(session, state.store, actor, cohort, **data.model_dump())
    (row,) = await cohorts_crud.list_with_counts(session, cohort_id=cohort.id)
    return _cohort_out(*row)


@router.delete("/{cohort_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cohort(
    cohort_id: uuid.UUID, actor: ActorDep, session: SessionDep, state: StateDep
) -> None:
    """Delete a cohort and its memberships (admins only)."""
    cohort = await staff.get_managed_cohort(session, actor, cohort_id)
    await staff.delete_cohort(session, state.store, actor, cohort)


@router.get("/{cohort_id}/members")
async def list_members(
    cohort_id: uuid.UUID,
    actor: ActorDep,
    session: SessionDep,
    page: PaginationDep,
    search: str | None = None,
) -> Page[MemberOut]:
    """List the addresses of a cohort."""
    await staff.get_managed_cohort(session, actor, cohort_id)
    rows, total = await cohorts_crud.list_members(
        session, cohort_id, search=search, limit=page.limit, offset=page.offset
    )
    items = [
        MemberOut(
            email=member.email,
            registered=registered,
            invited_at=member.invited_at,
            revoked_at=member.revoked_at,
            created_at=member.created_at,
        )
        for member, registered in rows
    ]
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)


@router.post("/{cohort_id}/members")
async def add_members(
    cohort_id: uuid.UUID,
    data: AddMembersIn,
    background: BackgroundTasks,
    actor: ActorDep,
    session: SessionDep,
    state: StateDep,
) -> AddMembersOut:
    """Pre-approve addresses and optionally e-mail them an invitation."""
    cohort = await staff.get_managed_cohort(session, actor, cohort_id)
    result = await staff.add_members(
        session,
        state.store,
        state.settings,
        actor,
        cohort,
        list(data.emails),
        send_invitations=data.send_invitations,
    )
    if result.messages:
        background.add_task(deliver_many, state.email, result.messages)
    return AddMembersOut(
        added=result.added, restored=result.restored, already_members=result.already_members
    )


@router.delete("/{cohort_id}/members/{email}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_member(
    cohort_id: uuid.UUID, email: Email, actor: ActorDep, session: SessionDep, state: StateDep
) -> None:
    """Withdraw an address's access through this cohort."""
    cohort = await staff.get_managed_cohort(session, actor, cohort_id)
    await staff.revoke_member(session, state.store, actor, cohort, email)


async def _preview(session: SessionDep, cohort: Cohort, parsed: ParsedEmails) -> ImportPreviewOut:
    existing = await cohorts_crud.members_by_email(session, cohort.id, parsed.valid)
    active = {email for email, member in existing.items() if member.revoked_at is None}
    return ImportPreviewOut(
        valid=parsed.valid,
        new=[e for e in parsed.valid if e not in active],
        already_members=[e for e in parsed.valid if e in active],
        duplicates=parsed.duplicates,
        invalid=[
            InvalidEntryOut(row=i.row, value=i.value, reason=i.reason) for i in parsed.invalid
        ],
    )


@router.post("/{cohort_id}/import/preview")
async def preview_import_file(
    cohort_id: uuid.UUID, file: UploadFile, actor: ActorDep, session: SessionDep
) -> ImportPreviewOut:
    """Dry-run an Excel or CSV upload; nothing is saved."""
    cohort = await staff.get_managed_cohort(session, actor, cohort_id)
    content = await file.read(MAX_IMPORT_BYTES + 1)
    return await _preview(session, cohort, parse_file(file.filename or "", content))


@router.post("/{cohort_id}/import/preview-text")
async def preview_import_text(
    cohort_id: uuid.UUID, data: PasteIn, actor: ActorDep, session: SessionDep
) -> ImportPreviewOut:
    """Dry-run pasted addresses; nothing is saved."""
    cohort = await staff.get_managed_cohort(session, actor, cohort_id)
    return await _preview(session, cohort, parse_text(data.text))
