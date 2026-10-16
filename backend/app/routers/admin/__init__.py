"""Staff endpoints (admins and instructors) under /api/admin."""

from fastapi import APIRouter

from app.routers.admin import audit, cohorts, requests, stats, users

router = APIRouter(prefix="/admin", tags=["admin"])
for module in (cohorts, requests, users, stats, audit):
    router.include_router(module.router)
