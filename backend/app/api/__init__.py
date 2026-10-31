"""All HTTP endpoints live under /api; guard.py protects every one except health and auth."""

from fastapi import APIRouter

from app.api import auth, desktop, device, health, metrics, system

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(system.router)
api_router.include_router(metrics.router)
api_router.include_router(device.router)
api_router.include_router(desktop.router)
