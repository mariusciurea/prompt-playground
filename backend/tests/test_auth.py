import hashlib
from datetime import timedelta

import pyotp
from pydantic import SecretStr
from sqlalchemy import select, update

from app.core.settings import Settings
from app.db_models import RefreshToken, User
from app.domain.auth import create_admin
from tests.conftest import TEST_PASSWORD


async def test_health_and_security_headers(client):
    response = await client.get("/api/health")
    assert response.json() == {"status": "ok"}
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-request-id"]
    assert (await client.get("/api/health/ready")).status_code == 200


async def test_unsafe_request_without_csrf_header_is_rejected(app):
    import httpx

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as raw:
        await raw.get("/api/auth/csrf")
        response = await raw.post("/api/auth/login", json={"email": "a@b.co", "password": "x"})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "csrf_failed"


async def test_full_account_lifecycle(client, login, emails):
    await login(client, "Student@Example.com")
    me = (await client.get("/api/me")).json()
    assert me["user"]["email"] == "student@example.com"
    assert me["user"]["role"] == "student"
    assert me["access"] == {"has_access": False, "cohorts": [], "pending_request": False}
    assert me["quota"]["limit"] == 70
    assert me["quota"]["used"] == 0

    old_refresh = client.cookies.get("refresh_token")
    assert (await client.post("/api/auth/refresh")).status_code == 200
    assert client.cookies.get("refresh_token") != old_refresh

    assert (await client.post("/api/auth/logout")).status_code == 204
    assert (await client.get("/api/me")).status_code == 401


async def test_register_does_not_reveal_existing_accounts(client, register_and_verify, emails):
    await register_and_verify(client, "taken@example.com")
    response = await client.post(
        "/api/auth/register", json={"email": "taken@example.com", "password": "another strong pass"}
    )
    assert response.status_code == 202
    assert emails.sent[-1].subject == "You already have an AI Playground account"


async def test_login_errors(client, register_and_verify):
    response = await client.post(
        "/api/auth/register", json={"email": "new@example.com", "password": TEST_PASSWORD}
    )
    assert response.status_code == 202
    unverified = await client.post(
        "/api/auth/login", json={"email": "new@example.com", "password": TEST_PASSWORD}
    )
    assert unverified.json()["error"]["code"] == "email_not_verified"

    await register_and_verify(client, "user@example.com")
    wrong = await client.post(
        "/api/auth/login", json={"email": "user@example.com", "password": "wrong password!"}
    )
    unknown = await client.post(
        "/api/auth/login", json={"email": "nobody@example.com", "password": "wrong password!"}
    )
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


async def test_verification_binds_the_password_chosen_by_the_inbox_owner(make_client, emails):
    async with make_client() as attacker, make_client() as victim:
        await attacker.post(
            "/api/auth/register",
            json={"email": "victim@example.com", "password": "attacker password 1"},
        )
        await victim.post(
            "/api/auth/register",
            json={"email": "victim@example.com", "password": "the real owner chose this"},
        )
        victim_token = emails.last_token("victim@example.com")
        await victim.post("/api/auth/verify-email", json={"token": victim_token})

        as_attacker = await attacker.post(
            "/api/auth/login",
            json={"email": "victim@example.com", "password": "attacker password 1"},
        )
        as_victim = await victim.post(
            "/api/auth/login",
            json={"email": "victim@example.com", "password": "the real owner chose this"},
        )
    assert as_attacker.status_code == 401
    assert as_victim.status_code == 200


async def test_repeated_failures_are_throttled(client, register_and_verify):
    await register_and_verify(client, "user@example.com")
    for _ in range(5):
        await client.post(
            "/api/auth/login", json={"email": "user@example.com", "password": "wrong password!"}
        )
    response = await client.post(
        "/api/auth/login", json={"email": "user@example.com", "password": TEST_PASSWORD}
    )
    assert response.status_code == 429
    assert int(response.headers["retry-after"]) > 0


async def test_refresh_token_reuse_revokes_the_session(client, login, session):
    await login(client, "user@example.com")
    stolen = client.cookies.get("refresh_token")
    assert (await client.post("/api/auth/refresh")).status_code == 200

    # Within the grace window a parallel tab gets a retryable conflict.
    client.cookies.set("refresh_token", stolen, path="/api/auth")
    assert (await client.post("/api/auth/refresh")).status_code == 409

    # Later reuse is treated as theft: the whole family is revoked.
    await session.execute(
        update(RefreshToken).values(used_at=RefreshToken.used_at - timedelta(minutes=5))
    )
    await session.commit()
    assert (await client.post("/api/auth/refresh")).status_code == 401
    tokens = (await session.scalars(select(RefreshToken))).all()
    assert all(t.revoked_at is not None for t in tokens)


async def test_password_reset(client, make_client, login, emails):
    await login(client, "user@example.com")
    async with make_client() as anonymous:
        response = await anonymous.post(
            "/api/auth/forgot-password", json={"email": "user@example.com"}
        )
        assert response.status_code == 202
        token = emails.last_token("user@example.com")
        response = await anonymous.post(
            "/api/auth/reset-password",
            json={"token": token, "new_password": "a brand new password"},
        )
        assert response.status_code == 200
        reused = await anonymous.post(
            "/api/auth/reset-password", json={"token": token, "new_password": "yet another one!!"}
        )
        assert reused.json()["error"]["code"] == "invalid_token"

    assert (await client.post("/api/auth/refresh")).status_code == 401
    response = await client.post(
        "/api/auth/login", json={"email": "user@example.com", "password": "a brand new password"}
    )
    assert response.status_code == 200


async def test_breached_and_disposable_addresses_are_rejected(client, external_http):
    password = "password from a breach"
    digest = hashlib.sha1(password.encode()).hexdigest().upper()  # noqa: S324
    external_http.breached_suffixes.add(digest[5:])
    response = await client.post(
        "/api/auth/register", json={"email": "user@example.com", "password": password}
    )
    assert response.json()["error"]["code"] == "weak_password"
    assert all(digest not in str(r.url) for r in external_http.requests)

    response = await client.post(
        "/api/auth/register", json={"email": "user@mailinator.com", "password": TEST_PASSWORD}
    )
    assert response.json()["error"]["code"] == "disposable_email"


async def test_passwords_keep_surrounding_whitespace(client, login):
    await login(client, "user@example.com", password="  spaced password  ")
    response = await client.post(
        "/api/auth/login", json={"email": "user@example.com", "password": "spaced password"}
    )
    assert response.status_code == 401


async def test_turnstile_is_enforced_when_configured(client, state, external_http):
    state.settings = state.settings.model_copy(update={"turnstile_secret_key": SecretStr("s")})
    body = {"email": "user@example.com", "password": TEST_PASSWORD}
    missing = await client.post("/api/auth/register", json=body)
    assert missing.json()["error"]["code"] == "bot_check_failed"

    external_http.turnstile_success = False
    failed = await client.post("/api/auth/register", json={**body, "turnstile_token": "x"})
    assert failed.status_code == 403

    external_http.turnstile_success = True
    ok = await client.post("/api/auth/register", json={**body, "turnstile_token": "x"})
    assert ok.status_code == 202


async def test_totp_enrollment_and_login(client, session, state):
    await create_admin(session, "admin@example.com", TEST_PASSWORD)
    body = {"email": "admin@example.com", "password": TEST_PASSWORD}
    assert (await client.post("/api/auth/login", json=body)).status_code == 200

    secret = (await client.post("/api/me/totp/setup")).json()["secret"]
    code = pyotp.TOTP(secret).now()
    assert (await client.post("/api/me/totp/enable", json={"code": code})).status_code == 200

    await client.post("/api/auth/logout")
    needs_code = await client.post("/api/auth/login", json=body)
    assert needs_code.json()["error"]["code"] == "totp_required"
    replayed = await client.post("/api/auth/login", json={**body, "totp_code": code})
    assert replayed.status_code == 401  # the code was already used for enrollment

    await state.store.delete(f"totp_used:{(await _user(session, 'admin@example.com')).id}:{code}")
    accepted = await client.post("/api/auth/login", json={**body, "totp_code": code})
    assert accepted.status_code == 200


async def test_delete_account(client, login, session):
    await login(client, "user@example.com")
    response = await client.request("DELETE", "/api/me", json={"password": TEST_PASSWORD})
    assert response.status_code == 204
    assert await _user(session, "user@example.com") is None


async def _user(session, email: str) -> User | None:
    return await session.scalar(select(User).where(User.email == email))


def test_production_requires_hardening_settings(database_url):
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="REDIS_URL"):
        Settings(
            _env_file=None,  # type: ignore[call-arg]
            environment="production",
            database_url=database_url,
            jwt_secret_key="x" * 40,
            totp_encryption_key="k",
        )
