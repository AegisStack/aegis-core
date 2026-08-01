# Starting Aegis Dashboard Locally

Quick reference for running the dashboard on your local machine.

## Prerequisites Checklist

- [ ] Docker Desktop installed and running
- [ ] Node.js 18+ installed
- [ ] Python 3.10+ installed
- [ ] Git repository cloned

## Quick Start (5 minutes)

### 1. Start Backend Services

```bash
cd aegis-dashboard
docker-compose up -d --build
```

This starts:
- PostgreSQL with TimescaleDB (port 5432)
- Redis (port 6379)
- FastAPI backend (port 8000)

**Wait 30-60 seconds** for services to be healthy.

### 2. Check Services Status

```bash
docker-compose ps
```

All services should show "Up" status:
```
NAME                IMAGE                            STATUS
aegis-backend       aegis-dashboard-backend          Up
aegis-postgres      timescale/timescaledb:latest    Up (healthy)
aegis-redis         redis:7-alpine                   Up (healthy)
```

### 3. Initialize Database

```bash
cd backend
pip install -r requirements.txt
python init_db.py
```

This creates:
- Database tables
- Test customer (`test_customer`)
- Three test users (admin, operator, viewer)

### 4. Start Frontend

```bash
cd ../frontend
npm install
npm run dev
```

Frontend starts on http://localhost:3000

### 5. Access Dashboard

Open browser to: **http://localhost:3000**

**Login credentials:**
- Admin: `admin@test.com` / `admin123`
- Operator: `operator@test.com` / `operator123`
- Viewer: `viewer@test.com` / `viewer123`

---

## Service URLs

| Service | URL | Description |
|---------|-----|-------------|
| Frontend | http://localhost:3000 | Dashboard UI |
| Backend API | http://localhost:8000 | REST API |
| API Docs | http://localhost:8000/docs | Swagger UI |
| WebSocket | ws://localhost:8000/ws | Live feed |
| PostgreSQL | localhost:5432 | Database |
| Redis | localhost:6379 | Cache |

---

## API Key for Testing

Use this API key when ingesting audit records:

```
X-API-Key: test_api_key_12345
```

Example curl:
```bash
curl -X POST http://localhost:8000/api/v1/ingest/audit \
  -H "X-API-Key: test_api_key_12345" \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "send_email",
    "action": "escalate",
    "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)'",
    "metadata": {
      "to": "user@example.com",
      "subject": "Test"
    }
  }'
```

---

## Stopping Services

### Stop all services
```bash
cd aegis-dashboard
docker-compose down
```

### Stop and remove data (clean slate)
```bash
docker-compose down -v
```

### Stop frontend
Press `Ctrl+C` in the terminal running `npm run dev`

---

## Troubleshooting

### Docker not running

**Error:** `Cannot connect to Docker daemon`

**Solution:**
1. Start Docker Desktop
2. Wait for it to fully start (look for green icon)
3. Retry `docker-compose up -d`

### Port already in use

**Error:** `Bind for 0.0.0.0:8000 failed: port is already allocated`

**Solutions:**

**Option 1:** Stop the conflicting service
```bash
# Find process using port
netstat -ano | findstr :8000
# Kill process (replace PID with actual number)
taskkill /PID <PID> /F
```

**Option 2:** Change ports in `docker-compose.yml`
```yaml
services:
  backend:
    ports:
      - "8001:8000"  # Use 8001 instead
```

### Database connection failed

**Error:** `Connection refused` or `Cannot connect to database`

**Solution:**
```bash
# Check if PostgreSQL is healthy
docker-compose ps postgres

# View logs
docker-compose logs postgres

# Restart database
docker-compose restart postgres

# Wait 10 seconds, then retry
```

### Frontend build errors

**Error:** `Module not found` or `Cannot find module`

**Solution:**
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### Backend import errors

**Error:** `ModuleNotFoundError: No module named 'app'`

**Solution:**
```bash
cd backend
pip install -r requirements.txt
# If using venv:
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Can't log in to dashboard

**Symptoms:** Invalid credentials error

**Solution:**
```bash
cd backend
python init_db.py  # Re-run initialization
```

### WebSocket not connecting

**Symptoms:** "Live Feed" not updating

**Check:**
1. Backend is running: `curl http://localhost:8000/health`
2. Check browser console for errors
3. Verify WebSocket URL in frontend code uses `ws://` not `wss://`

---

## Development Mode

### Watch mode for backend
```bash
# Backend auto-reloads on file changes (already enabled in docker-compose)
docker-compose logs -f backend
```

### Watch mode for frontend
```bash
# Frontend already has hot reload with `npm run dev`
cd frontend
npm run dev
```

### View all logs
```bash
docker-compose logs -f
```

### Restart a single service
```bash
docker-compose restart backend
docker-compose restart postgres
```

---

## Database Management

### Connect to PostgreSQL
```bash
docker exec -it aegis-postgres psql -U aegis -d aegis_dashboard
```

### Common SQL queries
```sql
-- List all tables
\dt

-- Count audit records
SELECT COUNT(*) FROM audit_records;

-- List users
SELECT email, role, is_active FROM users;

-- List customers
SELECT customer_id, name FROM customers;

-- Exit
\q
```

### Reset database
```bash
docker-compose down -v  # Removes volumes
docker-compose up -d
cd backend && python init_db.py
```

---

## Production Deployment

For production, update:

1. **docker-compose.yml:**
   - Change `SECRET_KEY` to random value
   - Set `DEBUG=false`
   - Update `CORS_ORIGINS`
   - Use strong PostgreSQL password

2. **Environment variables:**
   ```bash
   export SECRET_KEY=$(openssl rand -hex 32)
   export DATABASE_URL=postgresql+asyncpg://user:pass@host/db
   ```

3. **Frontend build:**
   ```bash
   cd frontend
   npm run build
   npm start  # Production server
   ```

See `QUICKSTART.md` for detailed production setup.

---

## Next Steps

- Read [SDK_GUIDE.md](../docs/SDK_GUIDE.md) to integrate the Aegis SDK
- Run tests: `pytest tests/ -v`
- Explore API docs: http://localhost:8000/docs
