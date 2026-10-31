"""Where server commands run (D-28): on the server itself (the Dell, M6), or over SSH while
the app is staged on the ASUS (REMOTE_SSH = an alias from ~/.ssh/config, key auth only).

Commands are always fixed argv lists (D-15). Over SSH the remote shell joins them, which is
safe only because every token is a literal or a config value checked against a strict pattern.
"""

from __future__ import annotations

import logging
import re
import subprocess
import sys

log = logging.getLogger(__name__)

SSH_OPTIONS = ["-o", "BatchMode=yes", "-o", "ConnectTimeout=5"]
SSH_FAILED = 255  # ssh's own exit code: could not connect or authenticate
# A plain alias: no spaces, nothing ssh could read as an option ("-o...").
_ALIAS = re.compile(r"[A-Za-z0-9][A-Za-z0-9._@-]*")


class Runner:
    def __init__(self, remote: str | None) -> None:
        self.remote = remote if remote and _ALIAS.fullmatch(remote) else None
        if remote and not self.remote:
            log.warning("REMOTE_SSH ignored: not a plain SSH alias.")

    @property
    def available(self) -> bool:
        """Linux server commands can run: over SSH, or locally on Linux. Never on the
        Windows dev machine itself (nothing here may power off the ASUS)."""
        return bool(self.remote) or sys.platform.startswith("linux")

    def run(self, argv: list[str], timeout: float) -> subprocess.CompletedProcess[str]:
        cmd = ["ssh", *SSH_OPTIONS, self.remote, *argv] if self.remote else argv
        return subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, check=False
        )
