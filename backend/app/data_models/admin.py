"""Request and response schemas for the admin and instructor panel."""

import uuid
from datetime import date, datetime
from typing import Annotated, Any, Self

from pydantic import Field, StringConstraints, model_validator

from app.data_models.common import Email, Schema
from app.db_models import AccessRequestStatus, Role

CohortName = Annotated[str, StringConstraints(min_length=1, max_length=120)]


class CohortIn(Schema):
    """Create a cohort."""

    name: CohortName
    starts_at: datetime
    ends_at: datetime
    owner_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def _check_dates(self) -> Self:
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        return self


class CohortUpdate(Schema):
    """Change a cohort; omitted fields stay the same."""

    name: CohortName | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    owner_id: uuid.UUID | None = None
    clear_owner: bool = False


class CohortOut(Schema):
    """A cohort with its member count."""

    id: uuid.UUID
    name: str
    starts_at: datetime
    ends_at: datetime
    owner_id: uuid.UUID | None
    owner_email: str | None
    member_count: int
    is_active: bool


class MemberOut(Schema):
    """A pre-approved address in a cohort."""

    email: str
    registered: bool
    invited_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime


class AddMembersIn(Schema):
    """Add addresses to a cohort (validated again on the server)."""

    emails: Annotated[list[Email], Field(min_length=1, max_length=2000)]
    send_invitations: bool = True


class AddMembersOut(Schema):
    """What happened to each address."""

    added: list[str]
    restored: list[str]
    already_members: list[str]


class PasteIn(Schema):
    """Free-form text with addresses separated by lines, commas, or spaces."""

    text: Annotated[str, StringConstraints(max_length=200_000)]


class InvalidEntryOut(Schema):
    """A rejected import value."""

    row: int
    value: str
    reason: str


class ImportPreviewOut(Schema):
    """Dry-run result of an import; nothing is saved."""

    valid: list[str]
    new: list[str]
    already_members: list[str]
    duplicates: list[str]
    invalid: list[InvalidEntryOut]


class AccessRequestIn(Schema):
    """A user's request for course access."""

    message: Annotated[str, StringConstraints(max_length=500)] = ""


class AccessRequestOut(Schema):
    """An access request as seen by staff."""

    id: uuid.UUID
    user_email: str
    message: str
    status: AccessRequestStatus
    created_at: datetime
    reviewed_at: datetime | None
    cohort_name: str | None


class MyAccessRequestOut(Schema):
    """The signed-in user's latest request."""

    status: AccessRequestStatus
    created_at: datetime
    reviewed_at: datetime | None


class ReviewIn(Schema):
    """Approve (into a cohort) or reject an access request."""

    approve: bool
    cohort_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def _cohort_required_for_approval(self) -> Self:
        if self.approve and self.cohort_id is None:
            raise ValueError("cohort_id is required to approve a request")
        return self


class AdminUserOut(Schema):
    """A user as seen by staff."""

    id: uuid.UUID
    email: str
    role: Role
    is_active: bool
    email_verified: bool
    totp_enabled: bool
    created_at: datetime
    last_login_at: datetime | None
    prompts_today: int


class UserUpdateIn(Schema):
    """Change a user's role or status (admins only)."""

    role: Role | None = None
    is_active: bool | None = None


class DailyCount(Schema):
    """Prompts on one day."""

    day: date
    count: int


class StatsOut(Schema):
    """Usage overview, optionally limited to one cohort."""

    users: int
    users_with_access: int
    prompts_today: int
    prompts_by_day: list[DailyCount]
    prompts_by_feature: dict[str, int]
    engage_solved_by_level: dict[int, int]


class AuditOut(Schema):
    """An audit log entry."""

    id: uuid.UUID
    actor_email: str | None
    action: str
    target: str | None
    details: dict[str, Any]
    ip: str | None
    created_at: datetime
