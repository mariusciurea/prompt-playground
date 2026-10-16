"""Liveness and readiness probes."""

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.state import StateDep

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def live() -> dict[str, str]:
    """Report that the process is up."""
    return {"status": "ok"}


@router.get("/ready")
async def ready(state: StateDep) -> JSONResponse:
    """Report whether the database and the store are reachable."""
    try:
        async with state.engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        store_ok = await state.store.ping()
    except Exception:
        logger.exception("Readiness check failed")
        store_ok = False
    else:
        if store_ok:
            return JSONResponse({"status": "ready"})
    return JSONResponse({"status": "unavailable"}, status_code=503)
