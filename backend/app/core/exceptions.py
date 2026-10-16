"""Domain exceptions and the handlers that turn them into JSON error responses."""

import logging
from typing import cast

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base error whose message is safe to show to users."""

    status_code = 400
    code = "bad_request"

    def __init__(self, message: str, *, headers: dict[str, str] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.headers = headers


class AuthenticationError(AppError):
    """The request is not authenticated."""

    status_code = 401
    code = "not_authenticated"


class PermissionDeniedError(AppError):
    """The user is authenticated but not allowed to do this."""

    status_code = 403
    code = "forbidden"


class NoAccessError(PermissionDeniedError):
    """The user has no active course access."""

    code = "no_access"


class NotFoundError(AppError):
    """The resource does not exist (or is not visible to the user)."""

    status_code = 404
    code = "not_found"


class ConflictError(AppError):
    """The request conflicts with the current state."""

    status_code = 409
    code = "conflict"


class RateLimitedError(AppError):
    """Too many requests in the current window."""

    status_code = 429
    code = "rate_limited"

    def __init__(self, retry_after: int) -> None:
        super().__init__(
            "Too many requests. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )


class QuotaExceededError(AppError):
    """The daily prompt quota is used up."""

    status_code = 429
    code = "quota_exceeded"


class ServiceUnavailableError(AppError):
    """A dependency (e.g. the LLM) is unavailable."""

    status_code = 503
    code = "service_unavailable"


def _error_body(code: str, message: str) -> dict[str, dict[str, str]]:
    return {"error": {"code": code, "message": message}}


async def _app_error_handler(_: Request, exc: Exception) -> JSONResponse:
    exc = cast(AppError, exc)
    return JSONResponse(
        _error_body(exc.code, exc.message), status_code=exc.status_code, headers=exc.headers
    )


async def _unhandled_error_handler(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error", exc_info=exc)
    return JSONResponse(_error_body("internal_error", "Something went wrong."), status_code=500)


def register_exception_handlers(app: FastAPI) -> None:
    """Map domain errors and unexpected exceptions to JSON responses."""
    app.add_exception_handler(AppError, _app_error_handler)
    app.add_exception_handler(Exception, _unhandled_error_handler)
