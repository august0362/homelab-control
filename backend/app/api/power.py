"""Server power (D-27): light sleep / wake up, clean up, restart."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.api.errors import ApiError
from app.services.device import server_label
from app.services.power import Power, PowerError

router = APIRouter(prefix="/power")

UNAVAILABLE = (
    "Power controls act on the Linux server. On the ASUS, set REMOTE_SSH (see README)."
)


class RebootIn(BaseModel):
    confirm: str = ""  # must be "reboot": no accidental one-click restart


def _power(request: Request, *, need_server: bool = True) -> Power:
    power: Power = request.app.state.power
    if need_server and not power.runner.available:
        raise ApiError(409, "power_unavailable", UNAVAILABLE)
    return power


def _run(action) -> Any:
    try:
        return action()
    except PowerError as exc:
        raise ApiError(exc.status, exc.code, exc.message) from None


@router.get("")
def status(request: Request) -> dict[str, Any]:
    power = _power(request, need_server=False)
    cfg = request.app.state.settings
    body: dict[str, Any] = {
        "available": power.runner.available,
        "reachable": False,
        "label": server_label(cfg)[0],
        "sleeping_since": power.sleeping_since(),
        "tasks": [],
        "message": None if power.runner.available else UNAVAILABLE,
    }
    if power.runner.available:
        try:
            body["tasks"] = [
                {"unit": t.unit, "scope": t.scope, "active": t.active}
                for t in power.tasks()
            ]
            body["reachable"] = True
        except PowerError as exc:
            body["message"] = exc.message
    return body


@router.post("/sleep")
def sleep(request: Request) -> dict[str, int]:
    return {"stopped": _run(_power(request).sleep)}


@router.post("/wake")
def wake(request: Request) -> dict[str, int]:
    return {"started": _run(_power(request).wake)}


@router.post("/cleanup")
def cleanup(request: Request) -> dict[str, int]:
    return {"stopped": _run(_power(request).cleanup)}


@router.post("/reboot", status_code=204)
def reboot(body: RebootIn, request: Request) -> None:
    if body.confirm != "reboot":
        raise ApiError(422, "confirm_required", 'Send {"confirm": "reboot"}.')
    _run(_power(request).reboot)
