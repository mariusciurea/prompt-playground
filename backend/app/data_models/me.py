"""Schemas for the signed-in user's own account, access, and quota."""

from datetime import datetime

from app.data_models.auth import CurrentPassword, NewPassword, UserOut
from app.data_models.common import Schema
from app.domain.access import AccessStatus
from app.domain.quota import QuotaStatus


class CohortOut(Schema):
    """A cohort granting access."""

    name: str
    ends_at: datetime


class AccessOut(Schema):
    """Current course access."""

    has_access: bool
    cohorts: list[CohortOut]
    pending_request: bool

    @classmethod
    def build(cls, status: AccessStatus, *, pending_request: bool) -> "AccessOut":
        """Build from the domain status."""
        return cls(
            has_access=status.has_access,
            cohorts=[CohortOut(name=c.name, ends_at=c.ends_at) for c in status.cohorts],
            pending_request=pending_request,
        )


class QuotaOut(Schema):
    """Today's prompt usage; `limit` is null for exempt users."""

    used: int
    limit: int | None
    remaining: int | None
    resets_at: datetime

    @classmethod
    def build(cls, status: QuotaStatus) -> "QuotaOut":
        """Build from the domain status."""
        return cls(
            used=status.used,
            limit=status.limit,
            remaining=status.remaining,
            resets_at=status.resets_at,
        )


class MeOut(Schema):
    """Everything the web app needs to render the shell."""

    user: UserOut
    access: AccessOut
    quota: QuotaOut


class ChangePasswordIn(Schema):
    """Change the password of the signed-in user."""

    current_password: CurrentPassword
    new_password: NewPassword
