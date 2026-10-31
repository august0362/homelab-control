from __future__ import annotations

from collections import namedtuple
from dataclasses import replace
from types import SimpleNamespace

import psutil
import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import create_app
from app.services.metrics import MetricsCollector
from app.services.platform_adapter import (
    BATTERY_FAULT,
    LinuxAdapter,
    PlatformAdapter,
    WindowsAdapter,
)

METRIC_STATUSES = {"ok", "unsupported", "unavailable", "error"}


def nic(rx: int, tx: int) -> SimpleNamespace:
    return SimpleNamespace(bytes_recv=rx, bytes_sent=tx)


def battery(percent=80.0, secsleft=3600, plugged=False) -> SimpleNamespace:
    return SimpleNamespace(percent=percent, secsleft=secsleft, power_plugged=plugged)


class FakeClock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def counters(monkeypatch):
    """Network counters the test controls: {nic: (rx, tx)}."""
    state: dict[str, tuple[int, int]] = {}
    monkeypatch.setattr(
        psutil,
        "net_io_counters",
        lambda pernic=False: {name: nic(*v) for name, v in state.items()},
    )
    return state


@pytest.fixture
def collector(counters):
    clock = FakeClock()
    col = MetricsCollector(PlatformAdapter(), clock=clock)
    col.clock = clock  # handle for tests
    return col


def test_metrics_endpoint_shape(tmp_path):
    cfg = replace(
        settings, state_dir=tmp_path / "state", device_id=None, frontend_dist=None
    )
    body = TestClient(create_app(cfg)).get("/api/metrics").json()
    assert set(body) == {
        "timestamp",
        "device",
        "cpu",
        "memory",
        "swap",
        "disk",
        "network",
        "uptime_seconds",
        "sensors",
    }
    assert set(body["device"]) == {"id", "label", "role", "platform", "device_type"}
    assert set(body["sensors"]) == {"temperature", "fans", "battery", "ac"}
    groups = [body[k] for k in ("cpu", "memory", "swap", "disk", "network")]
    for group in groups + list(body["sensors"].values()):
        assert set(group) == {"status", "data", "message"}
        assert group["status"] in METRIC_STATUSES
        assert (group["data"] is None) == (group["status"] != "ok")


def test_network_rate(collector, counters):
    counters.update({"eth0": (1000, 500), "lo": (10**9, 10**9)})
    first = collector.network()
    assert first["status"] == "unavailable" and first["data"] is None

    counters.update({"eth0": (5000, 1500), "lo": (2 * 10**9, 2 * 10**9)})
    collector.clock.now += 2
    second = collector.network()
    assert second["status"] == "ok"
    # Loopback traffic is excluded.
    assert second["data"] == {"rx_bytes_per_sec": 2000, "tx_bytes_per_sec": 500}


def test_network_counter_reset_is_null(collector, counters):
    counters["eth0"] = (10_000, 10_000)
    collector.network()
    counters["eth0"] = (100, 100)
    collector.clock.now += 2
    reset = collector.network()
    assert reset["status"] == "unavailable" and reset["data"] is None
    # The next sample after a reset is a normal rate again.
    counters["eth0"] = (300, 100)
    collector.clock.now += 2
    assert collector.network()["data"] == {
        "rx_bytes_per_sec": 100,
        "tx_bytes_per_sec": 0,
    }


def test_network_interface_change_and_zero_elapsed(collector, counters):
    counters["eth0"] = (1000, 1000)
    collector.network()
    counters["wlan0"] = (50, 50)
    collector.clock.now += 2
    assert collector.network()["data"] is None
    assert collector.network()["status"] == "unavailable"  # same instant


def test_failing_collector_does_not_break_payload(collector, counters, monkeypatch):
    def boom():
        raise OSError("no access")

    monkeypatch.setattr(psutil, "virtual_memory", boom)
    payload = collector.collect()
    assert payload["memory"]["status"] == "error"
    assert payload["memory"]["data"] is None
    assert "no access" in payload["memory"]["message"]
    assert payload["disk"]["status"] == "ok"


def test_no_swap_is_unavailable(collector, monkeypatch):
    monkeypatch.setattr(
        psutil,
        "swap_memory",
        lambda: SimpleNamespace(total=0, used=0, free=0, percent=0),
    )
    assert collector.swap()["status"] == "unavailable"


def test_windows_without_battery(monkeypatch):
    monkeypatch.setattr(psutil, "sensors_battery", lambda: None, raising=False)
    adapter = WindowsAdapter()
    assert adapter.battery()["status"] == "unavailable"
    assert adapter.ac_power()["status"] == "unavailable"
    assert adapter.sensor_support()["battery"] is False


def test_windows_battery_unknown_time_is_null(monkeypatch):
    monkeypatch.setattr(
        psutil,
        "sensors_battery",
        lambda: battery(secsleft=-2, plugged=True),
        raising=False,
    )
    adapter = WindowsAdapter()
    assert adapter.battery()["data"] == {"percent": 80.0, "secs_left": None}
    assert adapter.ac_power()["data"] == {"online": True}


def write_supply(root, name, **files):
    entry = root / name
    entry.mkdir(parents=True)
    for key, value in files.items():
        (entry / key).write_text(f"{value}\n")


@pytest.fixture
def sysfs(tmp_path, monkeypatch):
    monkeypatch.setattr(LinuxAdapter, "power_supply_dir", tmp_path)
    return tmp_path


def test_linux_faulty_battery_is_error(sysfs, monkeypatch):
    # The Dell case: 0% / Unknown while the AC adapter is online.
    write_supply(sysfs, "BAT0", type="Battery", present=1, status="Unknown", capacity=0)
    write_supply(sysfs, "AC", type="Mains", online=1)
    monkeypatch.setattr(
        psutil,
        "sensors_battery",
        lambda: battery(percent=0.0, plugged=True),
        raising=False,
    )
    adapter = LinuxAdapter()
    bat = adapter.battery()
    assert bat == {"status": "error", "data": None, "message": BATTERY_FAULT}
    assert adapter.ac_power()["data"] == {"online": True}
    assert adapter.sensor_support()["battery"] is True


def test_linux_battery_missing_from_psutil_is_error(sysfs, monkeypatch):
    write_supply(sysfs, "BAT0", type="Battery", present=1, status="Unknown")
    monkeypatch.setattr(psutil, "sensors_battery", lambda: None, raising=False)
    assert LinuxAdapter().battery()["status"] == "error"


def test_linux_healthy_battery_and_peripherals(sysfs, monkeypatch):
    write_supply(
        sysfs, "BAT0", type="Battery", present=1, status="Discharging", capacity=64
    )
    # A wireless mouse battery must not be mistaken for the laptop battery.
    write_supply(
        sysfs, "hid-mouse", type="Battery", scope="Device", status="Unknown", capacity=0
    )
    monkeypatch.setattr(
        psutil, "sensors_battery", lambda: battery(percent=64.0), raising=False
    )
    adapter = LinuxAdapter()
    assert adapter.battery()["data"] == {"percent": 64.0, "secs_left": 3600}
    assert adapter.ac_power()["status"] == "unavailable"  # no Mains entry


def test_linux_without_battery(sysfs, monkeypatch):
    monkeypatch.setattr(psutil, "sensors_battery", lambda: None, raising=False)
    assert LinuxAdapter().battery()["status"] == "unavailable"


def test_close_calls_share_one_snapshot(collector, counters):
    # Two viewers polling a few ms apart must not get CPU % over a ~0 ms window.
    counters["eth0"] = (0, 0)
    first = collector.collect()
    collector.clock.now += 0.1
    assert collector.collect() is first
    collector.clock.now += 1
    assert collector.collect() is not first


def test_cpu_percent_from_time_deltas(collector, monkeypatch):
    # Computed by the collector itself, so the thread serving the request is irrelevant.
    times = namedtuple("scputimes", "user system idle iowait")
    samples = iter([times(30, 10, 50, 10), times(40, 20, 60, 10)])
    current = {}

    def cpu_times(percpu=False):
        if not percpu:
            current["t"] = next(samples)
        return [current["t"]] if percpu else current["t"]

    monkeypatch.setattr(psutil, "cpu_times", cpu_times)
    collector._cpu_prev = (cpu_times(), cpu_times(percpu=True))
    data = collector.cpu()["data"]
    assert data["usage_percent"] == 66.7  # 20 busy of 30 elapsed; iowait counts as idle
    assert data["per_core"] == [66.7]
    # No time passed: unavailable, not a believable 0%.
    collector._cpu_prev = (current["t"], [current["t"]])
    monkeypatch.setattr(
        psutil,
        "cpu_times",
        lambda percpu=False: [current["t"]] if percpu else current["t"],
    )
    assert collector.cpu()["status"] == "unavailable"
