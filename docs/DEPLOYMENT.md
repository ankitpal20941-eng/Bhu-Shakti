# Deployment

## 1. Topology

```
client ──TLS──► reverse proxy (nginx/Caddy)
                   ├── /            → frontend/dist (static, SPA fallback)
                   └── /api, /docs  → uvicorn 127.0.0.1:8000 (single worker)
                                          ├── PostgreSQL + PostGIS (recommended)
                                          └── backend/storage (report media)
```

The in-process scheduler recalculates risk and ingests weather on an interval. It must run in
exactly one process: keep `--workers 1`, or move the scheduler into a separate process before
scaling the API horizontally.

## 2. Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `BHUSHAKTI_ENV` | `demo` | `production` disables demo mode and seeded-account behaviour |
| `BHUSHAKTI_DEMO_MODE` | follows env | Explicit demo flag; forced off in production |
| `BHUSHAKTI_SECRET_KEY` | generated dev secret | HMAC signing key for session tokens — **set in production** |
| `BHUSHAKTI_SESSION_TTL_MIN` | `720` | Session lifetime (minutes) |
| `BHUSHAKTI_DATABASE_URL` | `sqlite:///backend/data/bhushakti.db` | SQLAlchemy URL, e.g. `postgresql+psycopg://…` |
| `BHUSHAKTI_STORAGE_DIR` | `backend/storage` | Upload directory (set by code default) |
| `BHUSHAKTI_CORS_ORIGINS` | localhost dev origins | Comma-separated console origins |
| `BHUSHAKTI_WEATHER_MODE` | `simulated` in demo, `live` otherwise | `auto\|live\|simulated` |
| `BHUSHAKTI_DEMO_RAINFALL` | `replay` | `replay\|live` demo rainfall behaviour |
| `BHUSHAKTI_OPEN_METEO_BASE` | `https://api.open-meteo.com/v1` | Weather/DEM endpoint |
| `BHUSHAKTI_INGESTION_ENABLED` | `true` | Master switch for outbound calls |
| `BHUSHAKTI_INGESTION_ON_STARTUP` | `true` | Fetch on boot |
| `BHUSHAKTI_INGESTION_TIMEOUT_S` | `25` | HTTP timeout |
| `BHUSHAKTI_SEED_DEMO` | follows demo mode | Seed demonstration dataset |
| `BHUSHAKTI_MAX_UPLOAD_BYTES` | `10485760` | Per-file upload cap |
| `BHUSHAKTI_MAX_UPLOADS_PER_REPORT` | `3` | Files per report |
| `BHUSHAKTI_ALERT_MIN_DURATION_MIN` | `30` | Policy default |
| `BHUSHAKTI_ALERT_HYSTERESIS_POINTS` | `5` | Policy default |
| `BHUSHAKTI_RATE_LOGIN` | `10` | Logins per minute per IP |
| `BHUSHAKTI_RATE_WRITE` | `60` | Writes per minute |
| `BHUSHAKTI_MODEL_VERSION` | `suscept-v0.1+trigger-v0.1` | Active engine version label |
| `BHUSHAKTI_LOG_LEVEL` | `INFO` | Logging level |

Frontend build-time variable: `VITE_API_BASE` (leave empty for same-origin `/api`),
`VITE_PROXY_TARGET` for the dev/preview proxy.

## 3. Backend

```bash
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
export BHUSHAKTI_ENV=production
export BHUSHAKTI_SECRET_KEY="$(python -c 'import secrets;print(secrets.token_urlsafe(48))')"
export BHUSHAKTI_DATABASE_URL="postgresql+psycopg://bhushakti:***@db:5432/bhushakti"
python -c "from app.db import run_migrations; run_migrations()"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

Systemd unit (sketch):

```ini
[Unit]
Description=BHUSHAKTI AI API
After=network-online.target

[Service]
User=bhushakti
WorkingDirectory=/opt/bhushakti/backend
EnvironmentFile=/etc/bhushakti/api.env
ExecStart=/opt/bhushakti/backend/.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
Restart=on-failure
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=/opt/bhushakti/backend/storage /opt/bhushakti/backend/data

[Install]
WantedBy=multi-user.target
```

## 4. Frontend

```bash
cd frontend
npm ci
npm run build          # tsc -b && vite build → frontend/dist
```

Serve `dist` as an SPA (fallback to `index.html` for client routes) and proxy `/api` to the
backend. Example nginx:

```nginx
server {
  listen 443 ssl http2;
  server_name bhushakti.example.gov.in;

  root /opt/bhushakti/frontend/dist;
  index index.html;

  location /api/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_read_timeout 65s;          # SSE needs a long read timeout
    proxy_buffering off;             # keep /api/v1/stream unbuffered
  }

  location / {
    try_files $uri $uri/ /index.html;
  }
}
```

## 5. Database

- Development: SQLite is created automatically; migrations run on startup.
- Production: PostgreSQL 16 + PostGIS. Install `psycopg[binary]`, set the URL, run the migration
  runner once before starting the service.
- Convert GeoJSON columns to native geometry when you need spatial indexes; see
  `DATABASE_SCHEMA.md` §9.
- Back up nightly (`pg_dump`) and back up `backend/storage` separately; media is not in the
  database.

## 6. Operations

| Task | How |
| --- | --- |
| Health | `GET /api/v1/health` (DB check, version, environment) |
| System state | `GET /api/v1/admin/system-health` |
| Source freshness | `GET /api/v1/admin/data-sources` |
| Manual ingestion | `POST /api/v1/admin/data-sources/{id}/ingest` (implemented adapters only) |
| Recalculate | `POST /api/v1/risk/recalculate` |
| Logs | stdout (uvicorn), plus `audit_logs` for privileged actions |
| Backups | PostgreSQL dump + storage directory |
| Secret rotation | Change `BHUSHAKTI_SECRET_KEY` and restart; all sessions are invalidated |

## 7. Deployment of this prototype

What was actually run for this delivery:

1. `cd backend && python -m pytest tests -q` → **41 passed**.
2. `cd frontend && npm run build` → TypeScript + Vite build succeeded.
3. API started with `uvicorn app.main:app --port 8001` (port 8000 was occupied by an unrelated
   service on the development machine).
4. Frontend started with `VITE_PROXY_TARGET=http://127.0.0.1:8001 npm run dev` on
   `http://127.0.0.1:5173`.
5. All routers, the public endpoints, the CSV export and login were smoke-tested through the vite
   proxy (HTTP 200); the preview was registered in the workspace.

Not done: container images, cloud infrastructure, HTTPS certificates, Postgres migration
rehearsal, load testing, and multi-node scheduling. Those are deployment tasks for the target
environment, not claims of this build.
