# Aegis Dashboard

Web-based observability dashboard for Aegis SDK - policy enforcement monitoring and management.

## Features

- **Audit Trail Explorer** - Query and filter all policy evaluations
- **Real-time Metrics** - Dashboard with aggregated statistics
- **Policy Management** - CRUD operations with YAML validation and version history
- **Escalation Inbox** - Approve/deny high-risk tool calls
- **Multi-tenant** - Isolated data per customer with API key authentication

## Tech Stack

**Backend:**
- FastAPI (async Python web framework)
- PostgreSQL + TimescaleDB (time-series audit storage)
- Redis (caching and pub/sub)
- SQLAlchemy 2.0 (async ORM)
- Alembic (database migrations)

**Frontend:**
- Next.js 14 with App Router
- shadcn/ui-style components
- Recharts for visualizations

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.10+
- Node.js 18+ (for frontend)

### Local Development

1. **Start services:**

```bash
cd aegis-dashboard
docker-compose up -d
```

This starts:
- PostgreSQL with TimescaleDB (host port 5433, container port 5432)
- Redis on port 6379
- FastAPI backend on port 8000

The frontend dev server runs separately on port 3003; see
[../docs/RUNNING_LOCALLY.md](../docs/RUNNING_LOCALLY.md).

2. **Initialize database:**

Schema is managed by Alembic migrations (see [Database Migrations](#database-migrations)
below); the backend container's start command runs `alembic upgrade head`
automatically before starting the server, so this happens on first run
without a separate step. Then seed demo data with `python init_db.py`.

3. **Access API docs:**

Open http://localhost:8000/docs for interactive Swagger documentation.

### Without Docker

1. **Install backend dependencies:**

```bash
cd backend
pip install -r requirements.txt
```

2. **Configure environment:**

```bash
cp .env.example .env
# Edit .env with your database/redis URLs
```

3. **Apply migrations and start backend:**

```bash
alembic upgrade head
uvicorn app.main:app --reload
```

## API Endpoints

### Ingestion

- `POST /api/v1/ingest/audit` - Ingest audit records from SDK (requires API key)
- `POST /api/v1/ingest/events` - Ingest observability events

### Query

- `GET /api/v1/audit` - Query audit records with filters
- `GET /api/v1/audit/{record_id}` - Get specific audit record
- `GET /api/v1/metrics/summary` - Get dashboard metrics summary

### Policies

- `GET /api/v1/policies` - List policies
- `GET /api/v1/policies/{policy_id}` - Get specific policy
- `POST /api/v1/policies` - Create new policy version
- `POST /api/v1/policies/{policy_id}/activate` - Rollback to previous version

### Escalations

- `GET /api/v1/escalations` - List escalations
- `GET /api/v1/escalations/{escalation_id}` - Get specific escalation
- `POST /api/v1/escalations/{escalation_id}/resolve` - Approve/deny escalation

## Using Dashboard Sink from SDK

```python
import aegis

# Configure dashboard sink
sink = aegis.AegisDashboardSink(
    api_key="ak_your_api_key_here",
    base_url="http://localhost:8000",
    async_mode=True,
    batch_size=10
)

# Wrap tools with dashboard sink
tools = aegis.wrap(
    tools=[issue_refund, update_crm],
    policy="./policies/acme-corp.yaml",
    agent_id="billing-agent",
    customer_id="acme-corp",
    audit_sink=sink
)

# Use tools - audit records automatically sent to dashboard
result = tools[0](order_id="ord_123", amount_usd=100)
```

## Database Schema

### audit_records (TimescaleDB hypertable)

Stores every policy evaluation with full context. Partitioned by timestamp for efficient time-series queries.

**Key indexes:**
- `(customer_id, timestamp)` - Customer-scoped queries
- `(agent_id, timestamp)` - Agent-scoped queries
- `(customer_id, outcome)` - Outcome filtering
- `(customer_id, tool_name)` - Tool filtering

### policies

Stores YAML policies with version history. Only one active policy per (customer_id, agent_id).

### customers

Customer accounts with API keys for SDK authentication.

### escalations

Tracks tool calls requiring human approval with status tracking.

## Development

### Running Tests

```bash
cd backend
pytest
```

### Code Quality

```bash
# Format code
black app tests

# Lint
ruff app tests

# Type check
mypy app
```

## Architecture

```
SDK (Python)
    |
    | POST /api/v1/ingest/audit (with API key)
    v
FastAPI Backend
    |
    |-- Write to PostgreSQL (batched)
    |-- Cache in Redis
    |
    v
TimescaleDB (partitioned by time)

Dashboard UI (Next.js)
    |
    | Query APIs
    v
FastAPI Backend
    |
    |-- Query PostgreSQL
    |-- Aggregate metrics
    |
    v
Return JSON
```

## Production Deployment

### Environment Variables

See `.env.example` for all configuration options.

Critical settings:
- `SECRET_KEY` - Must be random and secure in production
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `CORS_ORIGINS` - Frontend domain(s)

### Database Migrations

```bash
# Generate migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head
```

### Kubernetes Deployment

See `/k8s` directory for manifests (coming soon).

## Monitoring

The backend exposes metrics at `/metrics` (Prometheus format).

Key metrics:
- `aegis_ingestion_records_total` - Total audit records ingested
- `aegis_ingestion_duration_seconds` - Ingestion latency
- `aegis_query_duration_seconds` - Query latency
- `aegis_active_connections` - Active database connections

## License

MIT

## Support

- Running locally: [../docs/RUNNING_LOCALLY.md](../docs/RUNNING_LOCALLY.md)
- Issues: https://github.com/AegisStack/aegis-core/issues
