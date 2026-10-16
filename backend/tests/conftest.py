"""Shared pytest fixtures: an embedded Postgres, test settings, the app, and an API client."""

import logging
import re
import tempfile
from collections.abc import AsyncIterator, Callable, Iterator
from pathlib import Path
from typing import Any

import httpx
import pgserver
import pytest
from alembic import command
from alembic.config import Config
from cryptography.fernet import Fernet
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import Environment, Settings
from app.core.state import AppState
from app.database.base import Base
from app.domain.email import EmailMessage
from app.services import create_app

BACKEND_DIR = Path(__file__).resolve().parent.parent
logging.getLogger("pgserver").setLevel(logging.WARNING)
TEST_PASSWORD = "correct horse battery staple"


@pytest.fixture(scope="session")
def database_url() -> Iterator[str]:
    """Start a throwaway Postgres server and migrate it to the latest schema."""
    with tempfile.TemporaryDirectory() as tmp:
        server = pgserver.get_server(Path(tmp) / "pg", cleanup_mode="stop")
        server.psql("CREATE DATABASE test_db;")
        url = server.get_uri("test_db").replace("postgresql://", "postgresql+asyncpg://", 1)
        config = Config(BACKEND_DIR / "alembic.ini")
        config.attributes["database_url"] = url
        config.attributes["configure_logger"] = False
        command.upgrade(config, "head")
        yield url
        server.cleanup()


@pytest.fixture
def settings(database_url: str) -> Settings:
    """Settings isolated from the developer's environment and .env file."""
    return Settings(
        _env_file=None,  # type: ignore[call-arg]
        environment=Environment.TEST,
        database_url=database_url,
        redis_url=None,
        jwt_secret_key="test-secret-key-that-is-long-enough-123",
        totp_encryption_key=Fernet.generate_key().decode(),
        cookie_secure=False,
        turnstile_secret_key=None,
        resend_api_key=None,
        gemini_api_key=None,
        public_base_url="http://app.test",
    )


class RecordingEmailSender:
    """Collects e-mails instead of sending them."""

    def __init__(self) -> None:
        self.sent: list[EmailMessage] = []

    async def send(self, message: EmailMessage) -> None:
        self.sent.append(message)

    def last_token(self, to: str) -> str:
        """Return the token from the most recent link sent to an address."""
        links = [m.link for m in self.sent if m.to == to.lower() and m.link]
        assert links, f"no e-mail with a link was sent to {to}"
        match = re.search(r"#token=(.+)$", links[-1])
        assert match, links[-1]
        return match.group(1)


class ExternalHttp:
    """Programmable stand-in for third-party HTTP APIs (HIBP, Turnstile)."""

    def __init__(self) -> None:
        self.breached_suffixes: set[str] = set()
        self.turnstile_success = True
        self.requests: list[httpx.Request] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.url.host == "api.pwnedpasswords.com":
            body = "\n".join(f"{s}:12" for s in self.breached_suffixes) or "0000:0"
            return httpx.Response(200, text=body)
        if request.url.host == "challenges.cloudflare.com":
            return httpx.Response(200, json={"success": self.turnstile_success})
        return httpx.Response(404)


@pytest.fixture
def external_http() -> ExternalHttp:
    return ExternalHttp()


@pytest.fixture
def emails() -> RecordingEmailSender:
    return RecordingEmailSender()


@pytest.fixture
async def app(
    settings: Settings, emails: RecordingEmailSender, external_http: ExternalHttp
) -> AsyncIterator[FastAPI]:
    """A running app with fake e-mail and external HTTP; tables are emptied afterwards."""
    application = create_app(settings)
    async with application.router.lifespan_context(application):
        state: AppState = application.state.app_state
        await state.http.aclose()
        state.http = httpx.AsyncClient(transport=httpx.MockTransport(external_http.handler))
        state.email = emails
        yield application
        async with state.engine.begin() as conn:
            tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
            await conn.execute(text(f"TRUNCATE {tables} CASCADE"))


@pytest.fixture
def state(app: FastAPI) -> AppState:
    state: AppState = app.state.app_state
    return state


@pytest.fixture
async def session(state: AppState) -> AsyncIterator[AsyncSession]:
    async with state.session_factory() as db_session:
        yield db_session


class ApiClient(httpx.AsyncClient):
    """Test client that fetches and echoes the CSRF token like the web app does."""

    async def request(self, method: str, url: Any, **kwargs: Any) -> httpx.Response:  # type: ignore[override]
        if method.upper() not in {"GET", "HEAD", "OPTIONS"}:
            token = self.cookies.get("csrf_token")
            if token is None:
                token = (await super().request("GET", "/api/auth/csrf")).json()["csrf_token"]
            headers = dict(kwargs.pop("headers", None) or {})
            headers.setdefault("X-CSRF-Token", token)
            kwargs["headers"] = headers
        return await super().request(method, url, **kwargs)


@pytest.fixture
def make_client(app: FastAPI) -> Callable[[], ApiClient]:
    """Factory for independent clients (separate cookie jars)."""

    def factory() -> ApiClient:
        return ApiClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver")

    return factory


@pytest.fixture
async def client(make_client: Callable[[], ApiClient]) -> AsyncIterator[ApiClient]:
    async with make_client() as api_client:
        yield api_client


@pytest.fixture
def register_and_verify(
    emails: RecordingEmailSender,
) -> Callable[..., Any]:
    """Register an account through the API and confirm its e-mail."""

    async def run(client: ApiClient, email: str, password: str = TEST_PASSWORD) -> None:
        response = await client.post(
            "/api/auth/register", json={"email": email, "password": password}
        )
        assert response.status_code == 202, response.text
        response = await client.post(
            "/api/auth/verify-email", json={"token": emails.last_token(email)}
        )
        assert response.status_code == 200, response.text

    return run


@pytest.fixture
def login(register_and_verify: Callable[..., Any]) -> Callable[..., Any]:
    """Register, verify, and sign in; returns the signed-in client."""

    async def run(client: ApiClient, email: str, password: str = TEST_PASSWORD) -> ApiClient:
        await register_and_verify(client, email, password)
        response = await client.post("/api/auth/login", json={"email": email, "password": password})
        assert response.status_code == 200, response.text
        return client

    return run
