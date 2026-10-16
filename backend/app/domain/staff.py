"""Staff operations: cohorts, members, invitations, access requests, and user management.

Admins may act on everything; instructors only on cohorts they own. Every change is
audited and drops the access cache.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.core.settings import Settings
from app.core.store import Store
from app.crud import audit, tokens
from app.crud import cohorts as cohorts_crud
from app.database.base import utcnow
from app.db_models import AccessRequest, AccessRequestStatus, Cohort, Role, User
from app.domain import email as emails
from app.domain.access import invalidate_access_cache


@dataclass(frozen=True, slots=True)
class Actor:
    """The staff member performing an action, and from where."""

    user: User
    ip: str

    @property
    def is_admin(self) -> bool:
        """Whether the actor is an admin."""
        return self.user.role is Role.ADMIN


@dataclass(frozen=True, slots=True)
class MembersAdded:
    """Outcome of adding addresses to a cohort, plus the e-mails to send."""

    added: list[str]
    restored: list[str]
    already_members: list[str]
    messages: list[emails.EmailMessage]


def _audit(
    session: AsyncSession, actor: Actor, action: str, target: str, **details: object
) -> None:
    audit.record(
        session, actor_id=actor.user.id, action=action, target=target, details=details, ip=actor.ip
    )


def _require_admin(actor: Actor) -> None:
    if not actor.is_admin:
        raise PermissionDeniedError("Admins only.")


async def get_managed_cohort(session: AsyncSession, actor: Actor, cohort_id: uuid.UUID) -> Cohort:
    """Return a cohort the actor may manage; others look like they do not exist."""
    cohort = await cohorts_crud.get(session, cohort_id)
    if cohort is None or not (actor.is_admin or cohort.owner_id == actor.user.id):
        raise NotFoundError("Cohort not found.")
    return cohort


async def _check_owner(session: AsyncSession, owner_id: uuid.UUID | None) -> None:
    if owner_id is None:
        return
    owner = await session.get(User, owner_id)
    if owner is None or owner.role is not Role.INSTRUCTOR:
        raise ConflictError("The owner must be an instructor.")


async def _commit_unique(session: AsyncSession, message: str) -> None:
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError(message) from exc


async def create_cohort(
    session: AsyncSession,
    store: Store,
    actor: Actor,
    *,
    name: str,
    starts_at: datetime,
    ends_at: datetime,
    owner_id: uuid.UUID | None,
) -> Cohort:
    """Create a cohort (admins only)."""
    _require_admin(actor)
    await _check_owner(session, owner_id)
    cohort = await cohorts_crud.create(
        session, name=name, starts_at=starts_at, ends_at=ends_at, owner_id=owner_id
    )
    _audit(session, actor, "cohort.create", name, starts_at=str(starts_at), ends_at=str(ends_at))
    await _commit_unique(session, "A cohort with this name already exists.")
    await invalidate_access_cache(store)
    return cohort


async def update_cohort(
    session: AsyncSession,
    store: Store,
    actor: Actor,
    cohort: Cohort,
    *,
    name: str | None,
    starts_at: datetime | None,
    ends_at: datetime | None,
    owner_id: uuid.UUID | None,
    clear_owner: bool,
) -> Cohort:
    """Rename, reschedule, or reassign a cohort (admins only)."""
    _require_admin(actor)
    changes: dict[str, object] = {}
    if name is not None:
        changes["name"] = name
    if starts_at is not None:
        changes["starts_at"] = starts_at
    if ends_at is not None:
        changes["ends_at"] = ends_at
    if clear_owner:
        changes["owner_id"] = None
    elif owner_id is not None:
        await _check_owner(session, owner_id)
        changes["owner_id"] = owner_id
    if (ends_at or cohort.ends_at) <= (starts_at or cohort.starts_at):
        raise ConflictError("The end must be after the start.")
    for key, value in changes.items():
        setattr(cohort, key, value)
    _audit(session, actor, "cohort.update", cohort.name, **{k: str(v) for k, v in changes.items()})
    await _commit_unique(session, "A cohort with this name already exists.")
    await invalidate_access_cache(store)
    return cohort


async def delete_cohort(session: AsyncSession, store: Store, actor: Actor, cohort: Cohort) -> None:
    """Delete a cohort and its memberships (admins only)."""
    _require_admin(actor)
    _audit(session, actor, "cohort.delete", cohort.name)
    await session.delete(cohort)
    await session.commit()
    await invalidate_access_cache(store)


async def add_members(
    session: AsyncSession,
    store: Store,
    settings: Settings,
    actor: Actor,
    cohort: Cohort,
    addresses: list[str],
    *,
    send_invitations: bool,
) -> MembersAdded:
    """Pre-approve addresses for a cohort; revoked ones are restored."""
    unique = list(dict.fromkeys(addresses))
    existing = await cohorts_crud.members_by_email(session, cohort.id, unique)
    added, restored, already = [], [], []
    now = utcnow()
    for address in unique:
        member = existing.get(address)
        if member is None:
            member = cohorts_crud.add_member(session, cohort.id, address, actor.user.id)
            added.append(address)
        elif member.revoked_at is not None:
            member.revoked_at = None
            restored.append(address)
        else:
            already.append(address)
            continue
        if send_invitations:
            member.invited_at = now

    messages: list[emails.EmailMessage] = []
    if send_invitations and (added or restored):
        verified = await cohorts_crud.verified_emails(session, added + restored)
        base = settings.public_base_url.rstrip("/")
        for address in added + restored:
            if address in verified:
                messages.append(emails.access_granted_email(address, cohort.name, f"{base}/"))
            else:
                link = f"{base}/register#email={address}"
                messages.append(emails.invitation_email(address, cohort.name, link))

    _audit(
        session,
        actor,
        "cohort.members.add",
        cohort.name,
        added=len(added),
        restored=len(restored),
        invitations=send_invitations,
    )
    await session.commit()
    await invalidate_access_cache(store)
    return MembersAdded(added, restored, already, messages)


async def revoke_member(
    session: AsyncSession, store: Store, actor: Actor, cohort: Cohort, address: str
) -> None:
    """Withdraw an address's access through this cohort."""
    member = await cohorts_crud.get_member(session, cohort.id, address)
    if member is None:
        raise NotFoundError("Member not found.")
    if member.revoked_at is None:
        member.revoked_at = utcnow()
        _audit(session, actor, "cohort.members.revoke", address, cohort=cohort.name)
        await session.commit()
        await invalidate_access_cache(store)


async def create_access_request(session: AsyncSession, user: User, message: str) -> AccessRequest:
    """File a request for access; only one may be pending at a time."""
    request = AccessRequest(user_id=user.id, message=message)
    session.add(request)
    await _commit_unique(session, "You already have a pending request.")
    return request


async def review_access_request(
    session: AsyncSession,
    store: Store,
    settings: Settings,
    actor: Actor,
    request_id: uuid.UUID,
    *,
    approve: bool,
    cohort_id: uuid.UUID | None,
) -> emails.EmailMessage | None:
    """Approve a pending request into a cohort, or reject it."""
    request = await session.get(AccessRequest, request_id, with_for_update=True)
    if request is None:
        raise NotFoundError("Request not found.")
    if request.status is not AccessRequestStatus.PENDING:
        raise ConflictError("This request was already reviewed.")
    user = await session.get(User, request.user_id)
    if user is None:
        raise NotFoundError("Request not found.")

    request.reviewed_by = actor.user.id
    request.reviewed_at = utcnow()
    message = None
    if approve:
        if cohort_id is None:
            raise ConflictError("Choose a cohort to approve the request.")
        cohort = await get_managed_cohort(session, actor, cohort_id)
        member = await cohorts_crud.get_member(session, cohort.id, user.email)
        if member is None:
            cohorts_crud.add_member(session, cohort.id, user.email, actor.user.id)
        else:
            member.revoked_at = None
        request.status = AccessRequestStatus.APPROVED
        request.cohort_id = cohort.id
        message = emails.access_granted_email(
            user.email, cohort.name, settings.public_base_url.rstrip("/") + "/"
        )
    else:
        request.status = AccessRequestStatus.REJECTED
    _audit(session, actor, f"access_request.{request.status.value}", user.email)
    await session.commit()
    await invalidate_access_cache(store)
    return message


async def update_user(
    session: AsyncSession,
    store: Store,
    actor: Actor,
    user_id: uuid.UUID,
    *,
    role: Role | None,
    is_active: bool | None,
) -> User:
    """Change a user's role or disable the account (admins only, never themselves)."""
    _require_admin(actor)
    user = await session.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found.")
    if user.id == actor.user.id:
        raise ConflictError("You cannot change your own account here.")
    if role is not None and role is not user.role:
        _audit(session, actor, "user.role", user.email, old=user.role.value, new=role.value)
        user.role = role
    if is_active is not None and is_active != user.is_active:
        user.is_active = is_active
        if not is_active:
            await tokens.revoke_all_for_user(session, user.id)
        _audit(session, actor, "user.active" if is_active else "user.disable", user.email)
    await session.commit()
    await invalidate_access_cache(store)
    return user


async def reset_two_factor(session: AsyncSession, actor: Actor, user_id: uuid.UUID) -> None:
    """Clear a user's 2FA so they can enroll again (admins only)."""
    _require_admin(actor)
    user = await session.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found.")
    user.totp_secret_encrypted = None
    user.totp_enabled_at = None
    await tokens.revoke_all_for_user(session, user.id)
    _audit(session, actor, "user.totp_reset", user.email)
    await session.commit()


async def delete_user(session: AsyncSession, actor: Actor, user_id: uuid.UUID) -> None:
    """Delete a non-admin account and its data (admins only)."""
    _require_admin(actor)
    user = await session.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found.")
    if user.role is Role.ADMIN:
        raise ConflictError("Admin accounts cannot be deleted here.")
    _audit(session, actor, "user.delete", user.email)
    await session.delete(user)
    await session.commit()
