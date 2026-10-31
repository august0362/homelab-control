"""Owner login (D-23): scrypt password hash, stateless signed session cookie, lockout.

The cookie is "<expires_unix>.<hmac>". The HMAC key mixes a secret kept in
STATE_DIR with the password hash, so sessions survive a restart but a new
password signs every device out. Nothing here ever logs a password or token.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import secrets
import threading
import time
from collections.abc import Callable

from app.config import Settings

COOKIE = "hlc_session"
SESSION_TTL = 30 * 24 * 3600  # seconds
MIN_PASSWORD_LENGTH = 10
MAX_FAILURES = 5
LOCKOUT_SECONDS = 60
_SCRYPT_N, _SCRYPT_R, _SCRYPT_P = 2**14, 8, 1  # ~16 MB, ~50 ms per check


def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode(), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P, dklen=32
    )
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, n, r, p, salt, digest = stored.split("$")
        if algo != "scrypt":
            return False
        expected = base64.b64decode(digest, validate=True)
        actual = hashlib.scrypt(
            password.encode(),
            salt=base64.b64decode(salt, validate=True),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected),
        )
    except (ValueError, binascii.Error):  # malformed hash or scrypt params
        return False
    return hmac.compare_digest(actual, expected)


def _session_secret(cfg: Settings) -> bytes:
    """Random secret generated once per install, like device_id."""
    path = cfg.state_dir / "session_secret"
    if path.is_file():
        stored = path.read_text(encoding="ascii").strip()
        if stored:
            return bytes.fromhex(stored)
    secret = secrets.token_bytes(32)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(secret.hex(), encoding="ascii")
    return secret


class Auth:
    """One per app. Login failures are counted globally: there is a single owner, and
    behind Tailscale Serve every request comes from 127.0.0.1 anyway."""

    def __init__(self, cfg: Settings, clock: Callable[[], float] = time.time) -> None:
        self.password_hash = cfg.owner_password_hash
        self.secure_cookie = cfg.machine_role == "production"
        self._clock = clock
        self._key = (
            hmac.new(
                _session_secret(cfg), self.password_hash.encode(), hashlib.sha256
            ).digest()
            if self.password_hash
            else None
        )
        self._lock = threading.Lock()
        self._failures = 0
        self._locked_until = 0.0

    @property
    def configured(self) -> bool:
        return self._key is not None

    def locked_for(self) -> int:
        """Seconds left on the lockout, 0 when logins are allowed."""
        return max(0, int(self._locked_until - self._clock() + 0.999))

    def login(self, password: str) -> bool:
        """Caller checks `configured` and `locked_for()` first."""
        ok = verify_password(password, self.password_hash or "")
        with self._lock:
            if ok:
                self._failures = 0
            else:
                self._failures += 1
                if self._failures >= MAX_FAILURES:
                    self._failures = 0
                    self._locked_until = self._clock() + LOCKOUT_SECONDS
        return ok

    def _sign(self, expires: int) -> str:
        assert self._key is not None
        return hmac.new(self._key, str(expires).encode(), hashlib.sha256).hexdigest()

    def issue(self) -> tuple[str, int]:
        expires = int(self._clock()) + SESSION_TTL
        return f"{expires}.{self._sign(expires)}", expires

    def session_expiry(self, token: str | None) -> int | None:
        """Expiry of a valid session cookie, otherwise None."""
        if not token or not self.configured:
            return None
        expires_raw, _, signature = token.partition(".")
        if not (expires_raw.isascii() and expires_raw.isdigit()):
            return None
        expires = int(expires_raw)
        if expires <= self._clock():
            return None
        expected = self._sign(expires).encode()
        valid = hmac.compare_digest(signature.encode("utf-8", "replace"), expected)
        return expires if valid else None
