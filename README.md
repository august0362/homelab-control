# HomeLab Control

Private web app to monitor and control a Dell Linux Mint server from an ASUS laptop, phones and tablets over Tailscale. Development runs on the ASUS (Windows); deployment to the Dell comes in M6.

**Status:** M1 (project bootstrap) approved; M2 (real metrics, realtime charts, offline/stale) approved; M2.5 (owner login + device rename) approved; M3 (Remote Desktop) done (part A on the ASUS, part B verified on the real Dell), waiting for owner approval. Milestones and decisions are in [docs/](docs/); start with [docs/PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md).

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
| `DESKTOP_LABEL` | device label | The server's name on the Remote Desktop page and the Power card (`Dell` while staging from the ASUS) |
| `REMOTE_SSH` | empty | Staging (D-28): an SSH `Host` alias for the Dell; desktop start/stop and power commands run over SSH, and `start.bat` opens the desktop tunnel. Empty on the Dell itself |

Frontend: `frontend/.env` may set `VITE_API_PROXY_TARGET` (dev proxy target, default `http://127.0.0.1:8000`).

## API

Everything under `/api` except `/api/health` and `/api/auth/*` needs the session cookie (`401 unauthorized` otherwise), except in dev on this machine: with `MACHINE_ROLE=dev`, a loopback `HOST` and a loopback URL (`127.0.0.1`/`localhost`), no login is needed (D-25). Writes (POST/PUT/PATCH/DELETE) also need an `Origin` matching the host (or `ALLOWED_ORIGINS`) and `Content-Type: application/json`, else `403 forbidden_origin`.

- `GET /api/health` → `{status, timestamp, version}` (public)
- `POST /api/auth/login {password}` → `204` + `hlc_session` cookie (HttpOnly, SameSite=Strict, 1 year; Secure in production) · `401 invalid_credentials` · `429 too_many_attempts` (5 misses → 60 s) · `503 auth_not_configured`
- `POST /api/auth/logout` → `204`, clears the cookie
- `GET /api/auth/session` → `{authenticated, login_required, configured, expires_at}` (public)
- `PATCH /api/server {label: string | null}` → `{label, label_source}`: the server's name on Remote Desktop and Power (staging: stored in `STATE_DIR/server.json`, default `DESKTOP_LABEL`; on the server itself it renames the device).
- `PATCH /api/device {label: string | null}` → the device object. 1–40 characters, no control characters (`422 invalid_label`); `null` = back to `DEVICE_LABEL` / hostname. `device.label_source` is `custom | env | hostname`.
- `GET /api/system` → `{timestamp, device, os, hardware, app, capabilities}`
- `GET /api/metrics` → `{timestamp, device, cpu, memory, swap, disk, network, uptime_seconds, sensors{temperature, fans, battery, ac}}`. Each group is `{status, data, message}` with `status` = `ok | unsupported | unavailable | error`; `data` is `null` unless `ok` (no fake zeros). Network is bytes/s from counter deltas. The UI polls every 2 s and keeps 10 min in browser memory.
- `GET /api/desktop/status` → `{status, message, label, can_control, viewers, connection_url}`; `status` = `not_configured | stopped | starting | running | error`. `running` means the VNC server answered with its RFB banner; `connection_url` is `/api/desktop/ws` only then. No VNC credentials are ever returned.
- `POST /api/desktop/start` · `POST /api/desktop/stop` → `204`; run `systemctl --user start|stop $DESKTOP_UNIT` (fixed argv). `503 desktop_not_configured` without `DESKTOP_VNC`, `409 desktop_unmanaged` without `DESKTOP_UNIT`, `500 desktop_start_failed|desktop_stop_failed` (details stay in `journalctl --user` on the server). Stop also closes open viewers.
- `WS /api/desktop/ws` → raw RFB bytes between noVNC and the VNC server (subprotocol `binary`). Needs a matching `Origin` and a session (or D-25), checked once when it opens; refused with close code 1008 otherwise.
- `GET /api/power` → `{available, reachable, label, sleeping_since, tasks[{unit, scope, active}], message}` (D-27). Only optional tasks are listed; ssh, Tailscale, the network and this app are never touched.
- `POST /api/power/sleep` → `{stopped}`: light sleep, stops the optional tasks that run and remembers them · `POST /api/power/wake` → `{started}`: starts exactly those again · `POST /api/power/cleanup` → `{stopped}`: stops every optional task, remembers nothing · `POST /api/power/reboot {confirm: "reboot"}` → `204`. No shut down (nothing could switch the Dell back on). `409 power_unavailable` on the Windows dev machine without `REMOTE_SSH`, `403 power_not_permitted` until `deploy/linux/power-setup.sh` ran, `502 server_unreachable` when SSH fails.
- Errors are always `{code, message}`.

## Remote desktop (staging)

The desktop is a separate XFCE session on the Dell (TigerVNC Xvnc, 1280x720, started on demand). Xvnc listens **only on a Unix socket** (`/run/user/<uid>/hlc-vnc.sock`, mode 0600): there is no VNC TCP port and no websockify. The backend bridges the browser's WebSocket to that socket after checking the session and `Origin` (D-26). Dell setup, rescue and undo: [deploy/linux/README.md](deploy/linux/README.md).

Before the full deploy (M6), the ASUS drives the Dell over SSH (D-28). Once, in ASUS `backend/.env`:

```
REMOTE_SSH=<ssh alias of the Dell>
DESKTOP_VNC=tcp:127.0.0.1:5901
DESKTOP_UNIT=hlc-desktop.service
DESKTOP_LABEL=Dell
```

Then every day: `start.bat` (it also opens the tunnel `127.0.0.1:5901 → /run/user/<uid>/hlc-vnc.sock`) → Remote Desktop → **Start** → **Connect**. **Stop** turns the Dell's desktop off again; `stop.bat` closes the tunnel too. The desktop never starts by itself (ADR-008).

While the tunnel is open, any program on the ASUS can reach the Dell's desktop through 127.0.0.1:5901 (accepted: only the owner uses the ASUS, D-25). **Pop out** opens the desktop in a window of its own (only the screen and its keys; move it to another monitor); its **Return to page** button closes it and shows the desktop in the page again. Untick **Docked in page** to lift the desktop out into a floating panel that stays over every page (drag its title bar, resize from the corner; position and size are remembered per browser); tick it again to put the desktop back in the page. **Focus mode:** click the screen and the keyboard belongs to the desktop (orange outline); click anywhere outside it to give the keyboard back, click it again to return. In **Fullscreen**, Edge/Chrome also pass Alt+Tab, the Windows key and Ctrl+W to the desktop (hold Esc to leave fullscreen). The server's name has a pencil next to it. **Slow picture:** the Dell's Wi-Fi card (Broadcom BCM4313) uploads only ~20–120 KB/s, which is what makes the screen blurry and laggy; the session uses no compositor effects and a plain background, noVNC compresses harder, and a LAN cable fixes it for good. Phones: the toolbar has Ctrl+Alt+Del, Esc, Tab and a Keyboard button that opens the on-screen keyboard (best effort; typed text and Backspace/Enter are sent, other special keys are not).
## Security rules

Owner login on every API call except health, CSRF checks on writes, the only write routes are login/logout, rename, desktop start/stop and power (light sleep, wake, clean up, confirmed restart; no shut down), no shell execution from web input, bound to 127.0.0.1, no public ports, no secrets in git. Details: [docs/CONTEXT.md](docs/CONTEXT.md).
