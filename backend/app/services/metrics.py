"""Live metrics (FR-01). Cross-platform via psutil; OS details come from the adapter.

Every group is a Metric (status.py) so a broken or missing sensor shows up as
null + reason, never as a believable 0.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any

import psutil

from app.services.platform_adapter import PlatformAdapter
from app.services.status import Metric, ok, safe, unavailable


def _is_loopback(nic: str) -> bool:
    # "lo" on Linux, "Loopback Pseudo-Interface 1" on Windows.
    return nic == "lo" or nic.lower().startswith("loopback")


def _busy_percent(before: Any, after: Any) -> float | None:
    """CPU busy % between two cpu_times() samples, the same formula psutil uses."""

    def split(t: Any) -> tuple[float, float]:
        fields = t._asdict()
        # guest time is already counted in user on Linux.
        total = sum(v for k, v in fields.items() if k not in {"guest", "guest_nice"})
        return total, fields["idle"] + fields.get("iowait", 0.0)

    (total1, idle1), (total2, idle2) = split(before), split(after)
    if total2 - total1 <= 0:
        return None
    busy = 100 * (1 - (idle2 - idle1) / (total2 - total1))
    return round(min(100.0, max(0.0, busy)), 1)


class MetricsCollector:
    """One per app: keeps the previous network sample to turn counters into rates.

    Several viewers (ASUS, phone, tablet) poll at once; calls closer together than
    MIN_INTERVAL share one snapshot so CPU % and rates are never measured over ~0 ms.
    """

    MIN_INTERVAL = 0.5  # seconds

    def __init__(
        self, adapter: PlatformAdapter, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self.adapter = adapter
        self._clock = clock
        self._lock = threading.Lock()
        self._last: tuple[float, dict[str, Any]] | None = None
        self._net_prev: tuple[float, frozenset[str], int, int] | None = None
        # Not psutil.cpu_percent(): it keeps its last sample per thread, and requests
        # run on a thread pool, so a fresh thread would report 0.0.
        self._cpu_prev = (psutil.cpu_times(), psutil.cpu_times(percpu=True))

    def collect(self) -> dict[str, Any]:
        adapter = self.adapter
        with self._lock:
            now = self._clock()
            if self._last and now - self._last[0] < self.MIN_INTERVAL:
                return self._last[1]
            snapshot = {
                "cpu": safe(self.cpu),
                "memory": safe(self.memory),
                "swap": safe(self.swap),
                "disk": safe(self.disk),
                "network": safe(self.network),
                "uptime_seconds": safe(self.uptime)["data"],
                "sensors": {
                    "temperature": safe(adapter.temperatures),
                    "fans": safe(adapter.fans),
                    "battery": safe(adapter.battery),
                    "ac": safe(adapter.ac_power),
                },
            }
            self._last = (now, snapshot)
            return snapshot

    def cpu(self) -> Metric:
        (prev_total, prev_cores) = self._cpu_prev
        total, cores = self._cpu_prev = (
            psutil.cpu_times(),
            psutil.cpu_times(percpu=True),
        )
        usage = _busy_percent(prev_total, total)
        if usage is None:
            return unavailable("No CPU time passed since the previous sample.")
        return ok(
            {
                "usage_percent": usage,
                "per_core": [_busy_percent(a, b) for a, b in zip(prev_cores, cores)],
                "logical": psutil.cpu_count(),
                "load_average": self.adapter.load_average(),
            }
        )

    def memory(self) -> Metric:
        mem = psutil.virtual_memory()
        return ok(
            {
                "total_bytes": mem.total,
                "used_bytes": mem.used,
                "available_bytes": mem.available,
                "percent": mem.percent,
            }
        )

    def swap(self) -> Metric:
        sw = psutil.swap_memory()
        if not sw.total:
            return unavailable("No swap configured.")
        return ok(
            {
                "total_bytes": sw.total,
                "used_bytes": sw.used,
                "free_bytes": sw.free,
                "percent": sw.percent,
            }
        )

    def disk(self) -> Metric:
        path = self.adapter.root_disk()
        du = psutil.disk_usage(path)
        return ok(
            {
                "path": path,
                "total_bytes": du.total,
                "used_bytes": du.used,
                "free_bytes": du.free,
                "percent": du.percent,
            }
        )

    def network(self) -> Metric:
        nics = {
            name: c
            for name, c in psutil.net_io_counters(pernic=True).items()
            if not _is_loopback(name)
        }
        now = self._clock()
        names = frozenset(nics)
        rx = sum(c.bytes_recv for c in nics.values())
        tx = sum(c.bytes_sent for c in nics.values())
        prev, self._net_prev = self._net_prev, (now, names, rx, tx)
        if prev is None:
            return unavailable("Collecting the first sample.")
        prev_time, prev_names, prev_rx, prev_tx = prev
        elapsed = now - prev_time
        if elapsed <= 0:
            return unavailable("No time passed since the previous sample.")
        if names != prev_names:
            return unavailable("Network interfaces changed; rate resets.")
        if rx < prev_rx or tx < prev_tx:
            return unavailable("Network counters reset; rate resets.")
        return ok(
            {
                "rx_bytes_per_sec": round((rx - prev_rx) / elapsed),
                "tx_bytes_per_sec": round((tx - prev_tx) / elapsed),
            }
        )

    def uptime(self) -> Metric:
        return ok(int(time.time() - psutil.boot_time()))
