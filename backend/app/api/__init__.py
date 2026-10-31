"""All HTTP endpoints live under /api. M1/M2 are read-only (GET)."""

from fastapi import APIRouter

from app.api import health, system

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(system.router)
