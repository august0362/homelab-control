"""Remote desktop (FR-02, D-26): status, start/stop, and the WebSocket <-> VNC bridge.

The session is checked when the WebSocket opens; an open viewer keeps running until
it disconnects or the desktop is stopped (known limitation, fine for one owner).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import anyio
from fastapi import APIRouter, Request, WebSocket
from starlette.websockets import WebSocketDisconnect, WebSocketState

from app.api.errors import ApiError
from app.api.guard import denial
from app.services.desktop import Desktop, DesktopError
from app.services.device import device_label

log = logging.getLogger(__name__)
router = APIRouter(prefix="/desktop")

WS_PATH = "/api/desktop/ws"
MAX_FRAME = 1 << 20  # browser -> VNC messages are keys, pointer, clipboard: tiny
READ_CHUNK = 1 << 16
POLICY_VIOLATION = 1008  # WebSocket close codes
TOO_BIG = 1009
UNAVAILABLE = 1011


@router.get("/status")
def status(request: Request) -> dict[str, Any]:
    desktop: Desktop = request.app.state.desktop
    cfg = request.app.state.settings
    state, message = desktop.status()
    return {
        "status": state,
        "message": message,
        "label": cfg.desktop_label or device_label(cfg)[0],
        "can_control": desktop.can_control,
        "viewers": desktop.viewers,
        "connection_url": WS_PATH if state == "running" else None,
    }


def _managed(request: Request) -> Desktop:
    desktop: Desktop = request.app.state.desktop
    if not desktop.target:
        raise ApiError(503, "desktop_not_configured", desktop.problem)
    if not desktop.unit:
        raise ApiError(
            409,
            "desktop_unmanaged",
            "Start/stop is not managed here (DESKTOP_UNIT not set). "
            "Use systemctl --user on the server.",
        )
    return desktop


@router.post("/start", status_code=204)
async def start(request: Request) -> None:
    desktop = _managed(request)
    try:
        await asyncio.to_thread(desktop.start)
    except DesktopError as exc:
        raise ApiError(500, exc.code, exc.message) from None


@router.post("/stop", status_code=204)
async def stop(request: Request) -> None:
    desktop = _managed(request)
    try:
        await asyncio.to_thread(desktop.stop)
    except DesktopError as exc:
        raise ApiError(500, exc.code, exc.message) from None
    finally:
        desktop.close_viewers()


@router.websocket("/ws")
async def bridge(ws: WebSocket) -> None:
    if denial(ws, check_origin=True):
        await ws.close(POLICY_VIOLATION)  # before accept: the browser sees a refusal
        return
    desktop: Desktop = ws.app.state.desktop
    offered = ws.scope.get("subprotocols") or []
    await ws.accept(subprotocol="binary" if "binary" in offered else None)
    if not desktop.target:
        await ws.close(UNAVAILABLE, "Desktop not configured.")
        return
    try:
        reader, writer = await desktop.open()
    except (OSError, TimeoutError):
        await ws.close(UNAVAILABLE, "Desktop is not running.")
        return

    async def browser_to_vnc() -> None:
        while True:
            msg = await ws.receive()
            if msg["type"] == "websocket.disconnect":
                return
            data = msg.get("bytes")
            if data is None:  # RFB is binary; ignore stray text frames
                continue
            if len(data) > MAX_FRAME:
                await ws.close(TOO_BIG)
                return
            writer.write(data)
            await writer.drain()

    async def vnc_to_browser() -> None:
        while chunk := await reader.read(READ_CHUNK):
            await ws.send_bytes(chunk)

    with desktop.viewer() as stopped:
        log.info("desktop viewer connected (%d open)", desktop.viewers)
        # anyio, not asyncio.wait: Starlette cancels through anyio scopes, and a task
        # group ends cleanly when either side (or a desktop stop) finishes first.
        async with anyio.create_task_group() as tg:

            async def until_done(pump) -> None:
                try:
                    await pump()
                except (OSError, RuntimeError, WebSocketDisconnect):
                    pass  # the other side went away
                tg.cancel_scope.cancel()

            tg.start_soon(until_done, browser_to_vnc)
            tg.start_soon(until_done, vnc_to_browser)
            tg.start_soon(until_done, stopped.wait)
        writer.close()
        if ws.client_state == ws.application_state == WebSocketState.CONNECTED:
            try:
                await ws.close()
            except (OSError, RuntimeError):  # the browser went away meanwhile
                pass
    log.info("desktop viewer disconnected (%d open)", desktop.viewers)
