# HomeLab Control

Private web app to monitor and control a Dell Linux Mint server from an ASUS laptop, phones and tablets over Tailscale. Development runs on the ASUS (Windows); deployment to the Dell comes in M6.

**Status:** M1 (project bootstrap) approved; M2 (real metrics, realtime charts, offline/stale) approved; M2.5 (owner login + device rename) approved; M3 (Remote Desktop) part A done on the ASUS, part B (Dell setup) next. Milestones and decisions are in [docs/](docs/); start with [docs/PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md).

## Structure

```
backend/    FastAPI + psutil (Python 3.12+), tests in backend/tests
frontend/   React + TypeScript + Vite
scripts/    PowerShell helpers for Windows dev
deploy/     Linux deployment files (M6)
docs/       Spec, architecture, milestones, decisions
```

## Requirements

Python 3.12+ (the Dell runs 3.12), Node 20+, Git. Nothing is installed globally: the backend uses `backend/.venv` and the frontend uses its local `node_modules`.

## Commands (PowerShell, from the repo root)

| Task | Command |
|---|---|
| Setup (once, re-runnable) | `powershell -ExecutionPolicy Bypass -File scripts\setup.ps1` |
| Start dev (double-click) | `start.bat`: opens 2 windows + the UI in the browser |
| Stop dev (double-click) | `stop.bat`: stops ports 8000/5173 and closes those windows |
| Dev (opens 2 windows) | `powershell -ExecutionPolicy Bypass -File scripts\dev.ps1` |
| Set the owner password (once; again to change it) | `powershell -ExecutionPolicy Bypass -File scripts\set-password.ps1`, then restart the backend |
| Lint + tests + build | `powershell -ExecutionPolicy Bypass -File scripts\test.ps1` |
| Production build | `powershell -ExecutionPolicy Bypass -File scripts\build.ps1` |

Manual equivalents:

```powershell
cd backend;  .\.venv\Scripts\python -m app --reload   # API on 127.0.0.1:8000
cd frontend; npm run dev                               # UI on 127.0.0.1:5173, proxies /api
```

**Password:** not needed for dev on the ASUS (D-25). On the Dell (M6, `MACHINE_ROLE=production`) nobody can sign in until the owner runs `set-password.ps1` once; each device then stays signed in for a year. It asks twice (hidden, at least 10 characters) and writes only a scrypt hash to `backend/.env`. Running it again changes the password and signs every device out.

## URLs

- UI (dev): http://localhost:5173
- API health: http://127.0.0.1:8000/api/health
- System info / live metrics: `/api/system`, `/api/metrics` (need a signed-in session; open them in the browser after logging in)
- API docs (role `dev` only): http://127.0.0.1:8000/api/docs
- After `build.ps1`, the backend also serves the UI at http://127.0.0.1:8000

## Configuration

Copy `backend/.env.example` to `backend/.env` (setup does this). Never commit `.env`.

| Variable | Default | Meaning |
|---|---|---|
| `HOST` / `PORT` | `127.0.0.1` / `8000` | Bind address; keep loopback (remote access goes through Tailscale Serve) |
| `DEVICE_ID` | empty | Empty = UUID generated once in `STATE_DIR/device_id` |
| `DEVICE_LABEL` | hostname | Default "Monitoring &lt;label&gt;"; a name set on the Dashboard wins (`STATE_DIR/device.json`) |
| `MACHINE_ROLE` | `dev` | `dev` or `production` |
| `FRONTEND_DIST` | `../frontend/dist` | Built UI served on the same origin when it has `index.html` |
| `STATE_DIR` | `.state` | Local state (gitignored) |
| `LOG_LEVEL` | `info` | Uvicorn log level |
| `OWNER_PASSWORD_HASH` | empty | scrypt hash written by `set-password.ps1`. Empty = nobody can log in (dev on this machine needs no login anyway) |
| `ALLOWED_ORIGINS` | empty | Extra origins allowed to send writes, comma-separated (e.g. the Tailscale Serve URL in M6) |
| `DESKTOP_VNC` | empty | VNC target for Remote Desktop: `unix:/run/user/<uid>/hlc-vnc.sock` (Dell) or `tcp:127.0.0.1:<port>` (SSH tunnel). Empty = not configured; non-loopback hosts are refused |
| `DESKTOP_UNIT` | empty | systemd `--user` unit the UI starts/stops (e.g. `hlc-desktop.service`). Empty = start/stop happens on the server |
| `DESKTOP_LABEL` | device label | Whose desktop it is, shown on the page (`Dell` while staging from the ASUS) |

Frontend: `frontend/.env` may set `VITE_API_PROXY_TARGET` (dev proxy target, default `http://127.0.0.1:8000`).

## API

Everything under `/api` except `/api/health` and `/api/auth/*` needs the session cookie (`401 unauthorized` otherwise), except in dev on this machine: with `MACHINE_ROLE=dev`, a loopback `HOST` and a loopback URL (`127.0.0.1`/`localhost`), no login is needed (D-25). Writes (POST/PUT/PATCH/DELETE) also need an `Origin` matching the host (or `ALLOWED_ORIGINS`) and `Content-Type: application/json`, else `403 forbidden_origin`.

- `GET /api/health` → `{status, timestamp, version}` (public)
- `POST /api/auth/login {password}` → `204` + `hlc_session` cookie (HttpOnly, SameSite=Strict, 1 year; Secure in production) · `401 invalid_credentials` · `429 too_many_attempts` (5 misses → 60 s) · `503 auth_not_configured`
- `POST /api/auth/logout` → `204`, clears the cookie
- `GET /api/auth/session` → `{authenticated, login_required, configured, expires_at}` (public)
- `PATCH /api/device {label: string | null}` → the device object. 1–40 characters, no control characters (`422 invalid_label`); `null` = back to `DEVICE_LABEL` / hostname. `device.label_source` is `custom | env | hostname`.
- `GET /api/system` → `{timestamp, device, os, hardware, app, capabilities}`
- `GET /api/metrics` → `{timestamp, device, cpu, memory, swap, disk, network, uptime_seconds, sensors{temperature, fans, battery, ac}}`. Each group is `{status, data, message}` with `status` = `ok | unsupported | unavailable | error`; `data` is `null` unless `ok` (no fake zeros). Network is bytes/s from counter deltas. The UI polls every 2 s and keeps 10 min in browser memory.
- `GET /api/desktop/status` → `{status, message, label, can_control, viewers, connection_url}`; `status` = `not_configured | stopped | starting | running | error`. `running` means the VNC server answered with its RFB banner; `connection_url` is `/api/desktop/ws` only then. No VNC credentials are ever returned.
- `POST /api/desktop/start` · `POST /api/desktop/stop` → `204`; run `systemctl --user start|stop $DESKTOP_UNIT` (fixed argv). `503 desktop_not_configured` without `DESKTOP_VNC`, `409 desktop_unmanaged` without `DESKTOP_UNIT`, `500 desktop_start_failed|desktop_stop_failed` (details stay in `journalctl --user` on the server). Stop also closes open viewers.
- `WS /api/desktop/ws` → raw RFB bytes between noVNC and the VNC server (subprotocol `binary`). Needs a matching `Origin` and a session (or D-25), checked once when it opens; refused with close code 1008 otherwise.
- Errors are always `{code, message}`.

## Remote desktop (staging)

The desktop is a separate XFCE session on the Dell (TigerVNC Xvnc, 1280x720, started on demand). Xvnc listens **only on a Unix socket** (`/run/user/<uid>/hlc-vnc.sock`, mode 0600): there is no VNC TCP port and no websockify. The backend bridges the browser's WebSocket to that socket after checking the session and `Origin` (D-26). Dell setup lives in `deploy/linux/` (M3 part B).

Before the full deploy (M6), the ASUS can show the Dell's desktop:

1. Dell, over SSH: `systemctl --user start hlc-desktop`
2. ASUS, keep open: `ssh -N -L 127.0.0.1:5901:/run/user/<uid>/hlc-vnc.sock <user>@<dell>` (OpenSSH forwards a local loopback port to the remote socket)
3. ASUS `backend/.env`: `DESKTOP_VNC=tcp:127.0.0.1:5901`, `DESKTOP_LABEL=Dell`, `DESKTOP_UNIT` empty; restart the backend, open Remote Desktop, press Connect.
4. When done: `systemctl --user stop hlc-desktop` on the Dell, close the tunnel.

While the tunnel is open, any program on the ASUS can reach the Dell's desktop through 127.0.0.1:5901 (accepted: only the owner uses the ASUS, D-25). Phones: the toolbar has Ctrl+Alt+Del, Esc, Tab and a Keyboard button that opens the on-screen keyboard (best effort; typed text and Backspace/Enter are sent, other special keys are not).
## Security rules

Owner login on every API call except health, CSRF checks on writes, the only write routes are login/logout, rename and desktop start/stop, no shell execution from web input, bound to 127.0.0.1, no public ports, no secrets in git. Details: [docs/CONTEXT.md](docs/CONTEXT.md).
