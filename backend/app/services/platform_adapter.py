"""Small per-OS adapter for the few things psutil does not unify.

Everything cross-platform lives in metrics.py; only OS-specific details go here.
"""

from __future__ import annotations

import os
import platform
import sys
from pathlib import Path
from typing import Any, ClassVar

import psutil

from app.services.status import Metric, error, ok, safe, unavailable, unsupported

BATTERY_FAULT = "Battery reports a fault (e.g. Communication Error)."


def _secs_left(value: int) -> int | None:
    # psutil uses negative sentinels for "unknown" and "unlimited" (on AC).
    return value if value >= 0 else None


class PlatformAdapter:
    name = "generic"

    def root_disk(self) -> str:
        return "/"

    def os_details(self) -> dict[str, Any]:
        return {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "pretty_name": f"{platform.system()} {platform.release()}",
        }

    def cpu_model(self) -> str | None:
        return platform.processor() or None

    def sensor_support(self) -> dict[str, bool]:
        return {
            "temperature": hasattr(psutil, "sensors_temperatures"),
            "fans": hasattr(psutil, "sensors_fans"),
            # A faulty battery still counts: the device has one, the reading is bad.
            "battery": safe(self.battery)["status"] in {"ok", "error"},
        }

    def load_average(self) -> list[float] | None:
        if hasattr(os, "getloadavg"):
            return [round(x, 2) for x in os.getloadavg()]
        return None

    def temperatures(self) -> Metric:
        reader = getattr(psutil, "sensors_temperatures", None)
        if reader is None:
            return unsupported("psutil cannot read temperatures on this OS.")
        readings = [
            {
                "sensor": sensor,
                "label": entry.label or sensor,
                "current": entry.current,
                "high": entry.high,
                "critical": entry.critical,
            }
            for sensor, entries in reader().items()
            for entry in entries
        ]
        if not readings:
            return unavailable(
                "No temperature sensor found (try installing lm-sensors)."
            )
        return ok(readings)

    def fans(self) -> Metric:
        reader = getattr(psutil, "sensors_fans", None)
        if reader is None:
            return unsupported("psutil cannot read fan speed on this OS.")
        readings = [
            {"sensor": sensor, "label": entry.label or sensor, "rpm": entry.current}
            for sensor, entries in reader().items()
            for entry in entries
        ]
        if not readings:
            return unavailable("No fan sensor exposed by the system.")
        return ok(readings)

    def battery(self) -> Metric:
        reader = getattr(psutil, "sensors_battery", None)
        if reader is None:
            return unsupported("psutil cannot read the battery on this OS.")
        bat = reader()
        if bat is None:
            return unavailable("No battery detected.")
        return ok(
            {"percent": round(bat.percent, 1), "secs_left": _secs_left(bat.secsleft)}
        )

    def ac_power(self) -> Metric:
        reader = getattr(psutil, "sensors_battery", None)
        bat = reader() if reader else None
        if bat is None or bat.power_plugged is None:
            return unavailable("AC state is only reported together with a battery.")
        return ok({"online": bool(bat.power_plugged)})

    def skip_partition(self, part: Any) -> bool:
        return False


class WindowsAdapter(PlatformAdapter):
    name = "windows"

    def root_disk(self) -> str:
        return os.environ.get("SystemDrive", "C:") + "\\"

    def os_details(self) -> dict[str, Any]:
        release, version, _csd, _ptype = platform.win32_ver()
        edition = (
            platform.win32_edition() if hasattr(platform, "win32_edition") else None
        )
        pretty = " ".join(p for p in ["Windows", release, edition] if p)
        return {
            "system": "Windows",
            "release": release,
            "version": version,
            "pretty_name": pretty,
        }

    def sensor_support(self) -> dict[str, bool]:
        return {**super().sensor_support(), "temperature": False, "fans": False}

    def load_average(self) -> list[float] | None:
        # psutil emulates loadavg on Windows with a background thread; not worth it.
        return None

    def temperatures(self) -> Metric:
        return unsupported("Windows does not expose CPU temperature to psutil.")

    def fans(self) -> Metric:
        return unsupported("Windows does not expose fan speed to psutil.")

    def skip_partition(self, part: Any) -> bool:
        # Empty CD-ROM drives raise on disk_usage.
        return "cdrom" in part.opts or part.fstype == ""


class LinuxAdapter(PlatformAdapter):
    name = "linux"

    _virtual_fs: ClassVar[set[str]] = {
        "squashfs",
        "tmpfs",
        "devtmpfs",
        "overlay",
        "proc",
        "sysfs",
        "ramfs",
    }
    power_supply_dir: ClassVar[Path] = Path("/sys/class/power_supply")

    def os_details(self) -> dict[str, Any]:
        details = super().os_details()
        try:
            release = platform.freedesktop_os_release()
            details["pretty_name"] = release.get("PRETTY_NAME", details["pretty_name"])
            details["distro_id"] = release.get("ID")
            details["distro_version"] = release.get("VERSION_ID")
        except OSError:
            pass
        return details

    def cpu_model(self) -> str | None:
        try:
            for line in Path("/proc/cpuinfo").read_text().splitlines():
                if line.startswith("model name"):
                    return line.split(":", 1)[1].strip()
        except OSError:
            pass
        return super().cpu_model()

    def skip_partition(self, part: Any) -> bool:
        return part.fstype in self._virtual_fs or part.mountpoint.startswith("/snap")

    def _power_supplies(self, kind: str) -> list[dict[str, str | None]]:
        """sysfs entries of one type; a file that exists but cannot be read is None."""
        if not self.power_supply_dir.is_dir():
            return []
        found = []
        for entry in sorted(self.power_supply_dir.iterdir()):
            info: dict[str, str | None] = {}
            for key in ("type", "scope", "present", "status", "capacity", "online"):
                path = entry / key
                if path.exists():
                    try:
                        info[key] = path.read_text().strip()
                    except OSError:  # driver error, e.g. EIO on a dead battery
                        info[key] = None
            if info.get("type") == kind and info.get("scope") != "Device":
                found.append(info)
        return found

    def battery(self) -> Metric:
        # The Dell's dead battery shows up as 0% / Unknown (CONTEXT §6.7):
        # report a fault instead of a believable 0%.
        batteries = [
            b for b in self._power_supplies("Battery") if b.get("present") != "0"
        ]
        for bat in batteries:
            capacity, status = bat.get("capacity", ""), bat.get("status", "")
            if capacity is None or status is None:
                return error(BATTERY_FAULT)
            if capacity == "0" and status != "Discharging":
                return error(BATTERY_FAULT)
        result = super().battery()
        if result["status"] != "ok" and batteries:
            return error(BATTERY_FAULT)
        return result

    def ac_power(self) -> Metric:
        mains = self._power_supplies("Mains")
        if not mains:
            return unavailable("No AC adapter in /sys/class/power_supply.")
        states = [m.get("online") for m in mains]
        if all(s is None for s in states):
            return error("AC adapter state cannot be read.")
        return ok({"online": "1" in states})


def get_adapter() -> PlatformAdapter:
    if sys.platform.startswith("win"):
        return WindowsAdapter()
    if sys.platform.startswith("linux"):
        return LinuxAdapter()
    return PlatformAdapter()
