"""Application entrypoint.

Create the FastAPI application instance, register routers, and configure
startup and shutdown behavior. Run with `uvicorn app.services:create_app --factory`.
"""

from fastapi import APIRouter, FastAPI

from app.core.exceptions import register_exception_handlers
from app.core.lifespan import build_lifespan
from app.core.logging import configure_logging
from app.core.middleware import CSRFMiddleware, RequestIdMiddleware, SecurityHeadersMiddleware
from app.core.settings import Settings, get_settings
from app.routers import (
    access_requests,
    admin,
    auth,
    demos,
    engage,
    health,
    history,
    learn,
    playground,
    reservation,
    skills_lab,
    users,
)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the application."""
    settings = settings or get_settings()
    configure_logging(settings.log_level, json_format=settings.log_json)

    docs = not settings.is_production
    app = FastAPI(
        title=settings.app_name,
        lifespan=build_lifespan(settings),
        docs_url="/api/docs" if docs else None,
        openapi_url="/api/openapi.json" if docs else None,
        redoc_url=None,
    )
    register_exception_handlers(app)

    # Added last runs first: request ID → security headers → CSRF → routes.
    app.add_middleware(CSRFMiddleware)
    app.add_middleware(SecurityHeadersMiddleware, hsts=settings.is_production)
    app.add_middleware(RequestIdMiddleware)

    api = APIRouter(prefix="/api")
    for module in (
        health,
        auth,
        users,
        access_requests,
        admin,
        playground,
        engage,
        reservation,
        skills_lab,
        history,
        demos,
        learn,
    ):
        api.include_router(module.router)
    app.include_router(api)
    return app
