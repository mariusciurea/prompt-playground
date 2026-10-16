"""Transactional e-mail: message templates and delivery via Resend, SMTP, or the console."""

import asyncio
import html
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

import httpx

from app.core.settings import Settings

logger = logging.getLogger(__name__)

_RESEND_URL = "https://api.resend.com/emails"


@dataclass(frozen=True, slots=True)
class EmailMessage:
    """A plain-text e-mail with a single call-to-action link."""

    to: str
    subject: str
    body: str
    link: str | None = None
    link_label: str | None = None

    def as_text(self) -> str:
        """Render the plain-text part."""
        return f"{self.body}\n\n{self.link}\n" if self.link else f"{self.body}\n"

    def as_html(self) -> str:
        """Render a minimal HTML part with every value escaped."""
        paragraphs = "".join(f"<p>{html.escape(p)}</p>" for p in self.body.split("\n\n"))
        button = (
            f'<p><a href="{html.escape(self.link, quote=True)}">'
            f"{html.escape(self.link_label or self.link)}</a></p>"
            if self.link
            else ""
        )
        return f'<div style="font-family:sans-serif;max-width:560px">{paragraphs}{button}</div>'


class EmailSender(Protocol):
    """Delivers e-mail messages."""

    async def send(self, message: EmailMessage) -> None:
        """Send one message."""
        ...


class ConsoleEmailSender:
    """Development sender that logs messages instead of delivering them."""

    async def send(self, message: EmailMessage) -> None:
        logger.info("E-mail to %s | %s\n%s", message.to, message.subject, message.as_text())


class ResendEmailSender:
    """Sender backed by the Resend HTTP API."""

    throttle_seconds = 0.6  # stay under Resend's default limit of 2 requests per second

    def __init__(self, http: httpx.AsyncClient, api_key: str, sender: str) -> None:
        self._http = http
        self._api_key = api_key
        self._sender = sender

    async def send(self, message: EmailMessage) -> None:
        response = await self._http.post(
            _RESEND_URL,
            headers={"Authorization": f"Bearer {self._api_key}"},
            json={
                "from": self._sender,
                "to": [message.to],
                "subject": message.subject,
                "text": message.as_text(),
                "html": message.as_html(),
            },
            timeout=10.0,
        )
        response.raise_for_status()


class SmtpEmailSender:
    """Sender for any SMTP server (e.g. Gmail with an app password); needs no domain."""

    throttle_seconds = 1.0  # Gmail is unhappy with bursts

    def __init__(self, settings: Settings) -> None:
        self._host = settings.smtp_host or ""
        self._port = settings.smtp_port
        self._username = settings.smtp_username or ""
        self._password = settings.smtp_password.get_secret_value() if settings.smtp_password else ""
        self._sender = settings.email_from

    async def send(self, message: EmailMessage) -> None:
        from email.message import EmailMessage as MimeMessage

        import aiosmtplib

        mime = MimeMessage()
        mime["From"] = self._sender
        mime["To"] = message.to
        mime["Subject"] = message.subject
        mime.set_content(message.as_text())
        mime.add_alternative(message.as_html(), subtype="html")
        await aiosmtplib.send(
            mime,
            hostname=self._host,
            port=self._port,
            username=self._username,
            password=self._password,
            start_tls=self._port == 587,
            use_tls=self._port == 465,
            timeout=15,
        )


def create_email_sender(settings: Settings, http: httpx.AsyncClient) -> EmailSender:
    """Build the configured sender (AUTO resolves to Resend, then SMTP, then console)."""
    from app.core.settings import EmailBackend

    backend = settings.resolved_email_backend
    if backend is EmailBackend.RESEND and settings.resend_api_key is not None:
        return ResendEmailSender(
            http, settings.resend_api_key.get_secret_value(), settings.email_from
        )
    if backend is EmailBackend.SMTP:
        return SmtpEmailSender(settings)
    return ConsoleEmailSender()


async def deliver(sender: EmailSender, message: EmailMessage) -> None:
    """Send a message from a background task, logging instead of raising on failure."""
    try:
        await sender.send(message)
    except Exception:
        logger.exception("Failed to send '%s' e-mail", message.subject)


async def deliver_many(sender: EmailSender, messages: Sequence[EmailMessage]) -> None:
    """Send several messages in the background, pacing them for the provider's rate limit."""
    delay = getattr(sender, "throttle_seconds", 0.0)
    for index, message in enumerate(messages):
        if index and delay:
            await asyncio.sleep(delay)
        await deliver(sender, message)


def verification_email(to: str, link: str) -> EmailMessage:
    """Ask a new user to confirm their address."""
    return EmailMessage(
        to=to,
        subject="Confirm your AI Playground account",
        body=(
            "Confirm your e-mail address to finish creating your account. "
            "The link is valid for 24 hours.\n\n"
            "If you did not sign up, ignore this e-mail."
        ),
        link=link,
        link_label="Confirm e-mail",
    )


def account_exists_email(to: str, login_link: str, reset_link: str) -> EmailMessage:
    """Tell an existing user that someone tried to register with their address."""
    return EmailMessage(
        to=to,
        subject="You already have an AI Playground account",
        body=(
            "Someone (hopefully you) tried to create an account with this address, "
            "but it already has one. Sign in instead, or reset your password at "
            f"{reset_link} if you forgot it.\n\n"
            "If this was not you, you can ignore this e-mail."
        ),
        link=login_link,
        link_label="Sign in",
    )


def password_reset_email(to: str, link: str) -> EmailMessage:
    """Send a password reset link."""
    return EmailMessage(
        to=to,
        subject="Reset your AI Playground password",
        body=(
            "Use the link below to choose a new password. It is valid for 30 minutes "
            "and can be used once.\n\n"
            "If you did not ask for this, ignore this e-mail; your password stays the same."
        ),
        link=link,
        link_label="Reset password",
    )


def invitation_email(to: str, cohort_name: str, register_link: str) -> EmailMessage:
    """Invite a pre-approved address to join a cohort."""
    return EmailMessage(
        to=to,
        subject=f"You're invited to AI Playground: {cohort_name}",
        body=(
            f"You have been given access to the AI Playground for the course “{cohort_name}”. "
            "Create an account with this e-mail address and your access is activated "
            "automatically."
        ),
        link=register_link,
        link_label="Create your account",
    )


def access_granted_email(to: str, cohort_name: str, app_link: str) -> EmailMessage:
    """Tell a user their access request was approved."""
    return EmailMessage(
        to=to,
        subject="Your AI Playground access is active",
        body=f"Your access for “{cohort_name}” has been approved. Happy prompting!",
        link=app_link,
        link_label="Open the Playground",
    )
