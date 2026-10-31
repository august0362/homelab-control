# HomeLab Control

Private web app to monitor and control a Dell Linux Mint server from an ASUS laptop, phones and tablets over Tailscale. Development runs on the ASUS (Windows); deployment to the Dell comes in M6.

**Status:** M1 (project bootstrap) approved; M2 (real metrics, realtime charts, offline/stale) implemented, awaiting approval; M2.5 (auth) next. Milestones and decisions are in [docs/](docs/); start with [docs/PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md).

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
| Lint + tests + build | `powershell -ExecutionPolicy Bypass -File scripts\test.ps1` |
| Production build | `powershell -ExecutionPolicy Bypass -File scripts\build.ps1` |

Manual equivalents:

```powershell
cd backend;  .\.venv\Scripts\python -m app --reload   # API on 127.0.0.1:8000
cd frontend; npm run dev                               # UI on 127.0.0.1:5173, proxies /api
```

## URLs

- UI (dev): http://localhost:5173
- API health: http://127.0.0.1:8000/api/health
- System info: http://127.0.0.1:8000/api/system
- Live metrics: http://127.0.0.1:8000/api/metrics
- API docs (role `dev` only): http://127.0.0.1:8000/api/docs
- After `build.ps1`, the backend also serves the UI at http://127.0.0.1:8000

## Configuration

Copy `backend/.env.example` to `backend/.env` (setup does this). Never commit `.env`.

| Variable | Default | Meaning |
|---|---|---|
| `HOST` / `PORT` | `127.0.0.1` / `8000` | Bind address; keep loopback (remote access goes through Tailscale Serve) |
| `DEVICE_ID` | empty | Empty = UUID generated once in `STATE_DIR/device_id` |
| `DEVICE_LABEL` | hostname | Shown as "Monitoring &lt;label&gt;" |
| `MACHINE_ROLE` | `dev` | `dev` or `production` |
| `FRONTEND_DIST` | `../frontend/dist` | Built UI served on the same origin when it has `index.html` |
| `STATE_DIR` | `.state` | Local state (gitignored) |
| `LOG_LEVEL` | `info` | Uvicorn log level |

Frontend: `frontend/.env` may set `VITE_API_PROXY_TARGET` (dev proxy target, default `http://127.0.0.1:8000`).

## API (M1–M2, read-only)

- `GET /api/health` → `{status, timestamp, version}`
- `GET /api/system` → `{timestamp, device, os, hardware, app, capabilities}`
- `GET /api/metrics` → `{timestamp, device, cpu, memory, swap, disk, network, uptime_seconds, sensors{temperature, fans, battery, ac}}`. Each group is `{status, data, message}` with `status` = `ok | unsupported | unavailable | error`; `data` is `null` unless `ok` (no fake zeros). Network is bytes/s from counter deltas. The UI polls every 2 s and keeps 10 min in browser memory.
- Errors are always `{code, message}`.

## Security rules

GET-only API, no shell execution from web input, bound to 127.0.0.1, no public ports, no secrets in git. Details: [docs/CONTEXT.md](docs/CONTEXT.md).
