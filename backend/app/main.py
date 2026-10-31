"""FastAPI app: /api routes, then the built frontend on the same origin."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api import api_router
from app.api.errors import register_error_handlers
from app.config import APP_NAME, APP_VERSION, Settings, settings
from app.services.metrics import MetricsCollector
from app.services.platform_adapter import get_adapter


def create_app(cfg: Settings = settings) -> FastAPI:
    dev = cfg.machine_role == "dev"
    app = FastAPI(
        title=APP_NAME,
        version=APP_VERSION,
        docs_url="/api/docs" if dev else None,
        redoc_url=None,
        openapi_url="/api/openapi.json" if dev else None,
    )
    app.state.settings = cfg
    app.state.adapter = get_adapter()
    app.state.metrics = MetricsCollector(app.state.adapter)

    register_error_handlers(app)
    app.include_router(api_router)

    # Mounted last so /api/* always wins; unknown /api paths still get the JSON 404.
    dist = cfg.frontend_dist
    if dist and (dist / "index.html").is_file():
        app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")
    return app


app = create_app()
