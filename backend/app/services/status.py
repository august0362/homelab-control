"""Uniform wrapper so every metric group says whether its data is real.

status:
  ok          data is a real reading
  unsupported the OS / psutil cannot provide it (data is null)
  unavailable supported, but no such device or reading right now (data is null)
  error       reading failed (data is null, message has the reason)
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any, TypedDict

log = logging.getLogger(__name__)


class Metric(TypedDict):
    status: str
    data: Any
    message: str | None


def ok(data: Any) -> Metric:
    return {"status": "ok", "data": data, "message": None}


def unsupported(message: str) -> Metric:
    return {"status": "unsupported", "data": None, "message": message}


def unavailable(message: str) -> Metric:
    return {"status": "unavailable", "data": None, "message": message}


def error(message: str) -> Metric:
    return {"status": "error", "data": None, "message": message}


def safe(fn: Callable[[], Metric]) -> Metric:
    """Run a collector; one failing metric must not break the whole response."""
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001 - reported to the client as status=error
        log.warning("metric collector %s failed: %s", getattr(fn, "__name__", fn), exc)
        return error(f"{type(exc).__name__}: {exc}")
