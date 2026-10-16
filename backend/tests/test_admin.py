from datetime import timedelta

import pyotp
import pytest
from sqlalchemy import select

from app.auth import totp
from app.database.base import utcnow
from app.db_models import AuditLog, Role, User
from app.domain.auth import create_admin
from tests.conftest import TEST_PASSWORD

TOTP_SECRET = pyotp.random_base32()


@pytest.fixture
def staff_login(session, settings, make_client):
    """Create a staff account with 2FA enrolled and return a signed-in client."""

    async def run(email: str, role: Role = Role.ADMIN, *, with_totp: bool = True):
        user = await create_admin(session, email, TEST_PASSWORD)
        user.role = role
        if with_totp:
            user.totp_secret_encrypted = totp.encrypt_secret(TOTP_SECRET, settings)
            user.totp_enabled_at = utcnow()
        await session.commit()
        client = make_client()
        body = {"email": email, "password": TEST_PASSWORD}
        if with_totp:
            body["totp_code"] = pyotp.TOTP(TOTP_SECRET).now()
        response = await client.post("/api/auth/login", json=body)
        assert response.status_code == 200, response.text
        return client

    return run


async def _create_cohort(admin, name="Oct 2026", *, days_ago=1, days_left=30, owner_id=None):
    now = utcnow()
    response = await admin.post(
        "/api/admin/cohorts",
        json={
            "name": name,
            "starts_at": (now - timedelta(days=days_ago)).isoformat(),
            "ends_at": (now + timedelta(days=days_left)).isoformat(),
            "owner_id": owner_id,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _has_access(client) -> bool:
    return (await client.get("/api/me")).json()["access"]["has_access"]


async def test_membership_grants_and_revocation_removes_access(client, login, staff_login):
    admin = await staff_login("admin@example.com")
    await login(client, "student@example.com")
    assert not await _has_access(client)

    cohort = await _create_cohort(admin)
    response = await admin.post(
        f"/api/admin/cohorts/{cohort['id']}/members",
        json={"emails": ["Student@Example.com"], "send_invitations": False},
    )
    assert response.json() == {
        "added": ["student@example.com"],
        "restored": [],
        "already_members": [],
    }
    assert await _has_access(client)

    response = await admin.delete(f"/api/admin/cohorts/{cohort['id']}/members/student@example.com")
    assert response.status_code == 204
    assert not await _has_access(client)


async def test_pre_approved_address_gets_invitation_and_access(client, login, staff_login, emails):
    admin = await staff_login("admin@example.com")
    cohort = await _create_cohort(admin)
    await admin.post(
        f"/api/admin/cohorts/{cohort['id']}/members",
        json={"emails": ["future@example.com"], "send_invitations": True},
    )
    invitation = emails.sent[-1]
    assert invitation.to == "future@example.com"
    assert invitation.link == "http://app.test/register#email=future@example.com"

    await login(client, "future@example.com")
    assert await _has_access(client)


async def test_expired_and_future_cohorts_grant_nothing(client, login, staff_login):
    admin = await staff_login("admin@example.com")
    await login(client, "student@example.com")
    for name, days_ago, days_left in (("past", 60, -30), ("future", -5, 30)):
        cohort = await _create_cohort(admin, name, days_ago=days_ago, days_left=days_left)
        await admin.post(
            f"/api/admin/cohorts/{cohort['id']}/members",
            json={"emails": ["student@example.com"], "send_invitations": False},
        )
    assert not await _has_access(client)


async def test_access_request_flow(client, login, staff_login, emails):
    admin = await staff_login("admin@example.com")
    cohort = await _create_cohort(admin)
    await login(client, "student@example.com")

    first = await client.post("/api/access-requests", json={"message": "Tuesday group"})
    assert first.status_code == 201
    second = await client.post("/api/access-requests", json={"message": "again"})
    assert second.status_code == 409
    assert (await client.get("/api/me")).json()["access"]["pending_request"] is True

    pending = (await admin.get("/api/admin/access-requests")).json()
    assert pending["total"] == 1
    request = pending["items"][0]
    assert request["user_email"] == "student@example.com"
    response = await admin.post(
        f"/api/admin/access-requests/{request['id']}/review",
        json={"approve": True, "cohort_id": cohort["id"]},
    )
    assert response.status_code == 200
    assert emails.sent[-1].subject == "Your AI Playground access is active"
    assert await _has_access(client)
    assert (await client.get("/api/access-requests/mine")).json()["status"] == "approved"
    assert (await client.post("/api/access-requests", json={})).status_code == 409


async def test_instructor_only_manages_own_cohorts(staff_login, session):
    admin = await staff_login("admin@example.com")
    instructor = await staff_login("teacher@example.com", Role.INSTRUCTOR)
    teacher = await session.scalar(select(User).where(User.email == "teacher@example.com"))
    own = await _create_cohort(admin, "Mine", owner_id=str(teacher.id))
    other = await _create_cohort(admin, "Other")

    assert [c["name"] for c in (await instructor.get("/api/admin/cohorts")).json()] == ["Mine"]
    assert (await instructor.get(f"/api/admin/cohorts/{other['id']}/members")).status_code == 404
    added = await instructor.post(
        f"/api/admin/cohorts/{own['id']}/members",
        json={"emails": ["kid@example.com"], "send_invitations": False},
    )
    assert added.status_code == 200
    assert (await instructor.post("/api/admin/cohorts", json={})).status_code in (403, 422)
    created = await instructor.post(
        "/api/admin/cohorts",
        json={"name": "x", "starts_at": utcnow().isoformat(), "ends_at": "2099-01-01T00:00:00Z"},
    )
    assert created.status_code == 403
    assert (await instructor.get("/api/admin/audit")).status_code == 403


async def test_staff_routes_require_two_factor_and_staff_role(client, login, staff_login):
    no_totp = await staff_login("admin@example.com", with_totp=False)
    response = await no_totp.get("/api/admin/cohorts")
    assert response.json()["error"]["code"] == "totp_setup_required"

    await login(client, "student@example.com")
    assert (await client.get("/api/admin/cohorts")).status_code == 403


async def test_import_preview_is_a_dry_run(staff_login):
    admin = await staff_login("admin@example.com")
    cohort = await _create_cohort(admin)
    await admin.post(
        f"/api/admin/cohorts/{cohort['id']}/members",
        json={"emails": ["old@example.com"], "send_invitations": False},
    )
    csv = b"email\nold@example.com\nnew@example.com\nbroken\nnew@example.com\n"
    response = await admin.post(
        f"/api/admin/cohorts/{cohort['id']}/import/preview",
        files={"file": ("list.csv", csv, "text/csv")},
    )
    preview = response.json()
    assert preview["new"] == ["new@example.com"]
    assert preview["already_members"] == ["old@example.com"]
    assert preview["duplicates"] == ["new@example.com"]
    assert len(preview["invalid"]) == 1

    members = (await admin.get(f"/api/admin/cohorts/{cohort['id']}/members")).json()
    assert members["total"] == 1

    text = await admin.post(
        f"/api/admin/cohorts/{cohort['id']}/import/preview-text", json={"text": "a@b.com c@d.com"}
    )
    assert text.json()["new"] == ["a@b.com", "c@d.com"]


async def test_disabling_a_user_ends_their_session(client, login, staff_login, session):
    admin = await staff_login("admin@example.com")
    await login(client, "student@example.com")
    student = await session.scalar(select(User).where(User.email == "student@example.com"))

    response = await admin.patch(f"/api/admin/users/{student.id}", json={"is_active": False})
    assert response.json()["is_active"] is False
    assert (await client.get("/api/me")).status_code == 401
    assert (await client.post("/api/auth/refresh")).status_code == 401

    actions = (await session.scalars(select(AuditLog.action))).all()
    assert "user.disable" in actions


async def test_user_list_and_stats(client, login, staff_login):
    admin = await staff_login("admin@example.com")
    await login(client, "student@example.com")
    users = (await admin.get("/api/admin/users", params={"search": "student"})).json()
    assert [u["email"] for u in users["items"]] == ["student@example.com"]
    assert (await admin.get("/api/admin/users", params={"limit": 1000})).status_code == 422

    stats = (await admin.get("/api/admin/stats")).json()
    assert stats["users"] == 2
    assert stats["prompts_today"] == 0
