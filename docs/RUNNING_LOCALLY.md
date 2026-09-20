# Running Aegis Locally

This guide covers running both parts of Aegis on your machine:

1. The **Aegis SDK** (the `aegis/` Python package).
2. The **Aegis Dashboard** (FastAPI backend + Next.js frontend under `aegis-dashboard/`).

You can run the SDK on its own. The dashboard is optional and only needed if you
want the web UI for monitoring audit records and escalations.

## Prerequisites

| Tool | Version | Needed for |
|------|---------|------------|
| Python | 3.9+ (3.10+ recommended) | SDK and backend |
| Docker + Docker Compose | recent | Dashboard database and backend |
| Node.js + npm | 18+ | Dashboard frontend |

## Port Reference

The dashboard uses these ports by default (defined in
[`aegis-dashboard/docker-compose.yml`](../aegis-dashboard/docker-compose.yml) and
the frontend `package.json`):

| Service | URL | Notes |
|---------|-----|-------|
| Frontend | http://localhost:3003 | `next dev -p 3003` |
| Backend API | http://localhost:8000 | FastAPI |
| API docs (Swagger) | http://localhost:8000/docs | |
| WebSocket | ws://localhost:8000/ws/live | Live feed |
| PostgreSQL | localhost:5433 | Mapped to container port 5432 |
| Redis | localhost:6379 | |

> **Note on the Postgres port:** Docker maps the container's `5432` to host
> port **5433**. When you connect from your host (e.g. running the backend
> outside Docker), use `5433`. Code running *inside* the Docker network uses
> `5432`.

---

## Part 1 — The SDK

### Install

From the repository root:

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -e ".[dev]"
```

### Verify

```bash
python -c "from aegis import wrap; print('Aegis SDK OK')"
```

### Run the tests

```bash
pytest
```

### Try an example

```bash
python examples/basic_usage.py
```

See [SDK_GUIDE.md](SDK_GUIDE.md) for the full API reference.

---

## Part 2 — The Dashboard

The dashboard has three moving pieces: a PostgreSQL/TimescaleDB database, the
FastAPI backend, and the Next.js frontend.

### Step 1 — Start the backing services

From `aegis-dashboard/`, start PostgreSQL, Redis, and the backend with Docker:

```bash
cd aegis-dashboard
docker-compose up -d --build
```

Wait 30–60 seconds for the services to become healthy, then check:

```bash
docker-compose ps
```

All services should show `Up` (Postgres and Redis show `Up (healthy)`).

> The backend container's start command runs `alembic upgrade head` before
> starting the server, so schema migrations are applied automatically here.
> They are **not** run automatically if you start the backend outside
> Docker (see [Running the Backend Without Docker](#running-the-backend-without-docker)).

### Step 2 — Initialize the database

Seed tables, a demo customer, and demo users:

```bash
cd backend
pip install -r requirements.txt
python init_db.py
```

This prints the seeded accounts and API keys. The default demo login is:

- Admin: `admin@test.com` / `admin123`
- Operator: `operator@test.com` / `operator123`
- Viewer: `viewer@test.com` / `viewer123`

Demo API key for ingesting audit records: `test_api_key_12345`.

### Step 3 — Start the frontend

In a new terminal:

```bash
cd aegis-dashboard/frontend
cp .env.local.example .env.local     # adjust if your backend runs elsewhere
npm install
npm run dev
```

### Step 4 — Open the dashboard

Visit **http://localhost:3003** and log in with the demo credentials above.

---

## Running the Backend Without Docker

If you prefer to run the backend directly (still using Docker only for Postgres
and Redis):

```bash
cd aegis-dashboard
docker-compose up -d postgres redis   # data stores only

cd backend
cp .env.example .env                   # DATABASE_URL uses host port 5433
pip install -r requirements.txt
alembic upgrade head                   # apply schema migrations
python init_db.py                      # seed demo data
uvicorn app.main:app --reload --port 8000
```

---

## Common Tasks

### View logs

```bash
cd aegis-dashboard
docker-compose logs -f            # all services
docker-compose logs -f backend   # one service
```

### Reset the database (clean slate)

```bash
cd aegis-dashboard
docker-compose down -v            # removes volumes
docker-compose up -d
cd backend && python init_db.py
```

### Stop everything

```bash
cd aegis-dashboard
docker-compose down
```

Stop the frontend with `Ctrl+C` in its terminal.

### Connect to Postgres

```bash
docker exec -it aegis-postgres psql -U aegis -d aegis_dashboard
```

---

## Running the Test Suites

```bash
# SDK (from repo root)
pytest

# Frontend
cd aegis-dashboard/frontend && npm test

# Backend (needs the database running)
cd aegis-dashboard
docker-compose up -d postgres redis
cd backend && pytest
```

---

## Troubleshooting

**Port already in use.** Find and stop the conflicting process, or change the
port mapping in `docker-compose.yml` (backend/db) or the `dev` script in the
frontend `package.json`.

- Linux/macOS: `lsof -i :8000`
- Windows: `netstat -ano | findstr :8000` then `taskkill /PID <pid> /F`

**Cannot connect to the database from the host.** Make sure you are using host
port **5433**, not 5432. Check the container is healthy with
`docker-compose ps`.

**`ModuleNotFoundError: No module named 'app'`.** Run backend commands from the
`aegis-dashboard/backend/` directory with dependencies installed
(`pip install -r requirements.txt`).

**Login fails.** Re-run `python init_db.py` to (re)seed the demo accounts.

**Frontend build errors.** Remove `node_modules` and reinstall:

```bash
cd aegis-dashboard/frontend
rm -rf node_modules package-lock.json
npm install
```

**CORS errors in the browser console.** Ensure the backend's `CORS_ORIGINS`
includes `http://localhost:3003` (the frontend dev port).
