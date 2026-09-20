# Aegis Quickstart Guide

## Table of Contents
1. [Running the Dashboard Locally](#running-the-dashboard-locally)
2. [Using the Aegis SDK](#using-the-aegis-sdk)
3. [Troubleshooting](#troubleshooting)

---

## Running the Dashboard Locally

This is the short version — see [RUNNING_LOCALLY.md](RUNNING_LOCALLY.md) for full
detail, troubleshooting, and running the backend without Docker.

### Prerequisites
- Docker & Docker Compose
- Node.js 18+ and npm
- Python 3.9+ (3.10+ recommended)

### Step 1: Start Backend Services

```bash
cd aegis-dashboard
docker-compose up -d --build
```

This starts PostgreSQL 15 + TimescaleDB and Redis, and the backend API (port 8000).

### Step 2: Initialize the Database

Seeds tables plus a demo customer and users:

```bash
cd backend
pip install -r requirements.txt
python init_db.py
```

This prints the seeded accounts and API keys, including:
- Admin: `admin@test.com` / `admin123`
- Operator: `operator@test.com` / `operator123`
- Viewer: `viewer@test.com` / `viewer123`

### Step 3: Start the Frontend

```bash
cd aegis-dashboard/frontend
cp .env.local.example .env.local
npm install
npm run dev
```

### Step 4: Access the Dashboard

Open http://localhost:3003 and log in with one of the demo accounts above.

### Available Endpoints

- **Frontend:** http://localhost:3003
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **WebSocket:** ws://localhost:8000/ws/live

---

## Using the Aegis SDK

### Installation

```bash
cd aegis-core
pip install -e .
```

Or install from source:
```bash
pip install git+https://github.com/yourorg/aegis-core.git
```

### Basic Usage

#### 1. Create a Policy File

Create `my_policy.yaml`:

```yaml
version: 1
rules:
  - tool: "execute_code"
    escalate:
      - language: { in: ["python", "javascript"] }

  - tool: "read_file"
    allow:
      - path: { regex: "^/home/user/documents/.*" }

  - tool: "delete_file"
    deny: always

defaults:
  unmatched_tool: deny
  unmatched_param: deny
```

#### 2. Define Your Tools

```python
def execute_code(language: str, code: str):
    """Execute code in the specified language."""
    # Your implementation
    return f"Executed {language} code"

def read_file(path: str):
    """Read a file from disk."""
    with open(path) as f:
        return f.read()

def delete_file(path: str):
    """Delete a file."""
    import os
    os.remove(path)
    return f"Deleted {path}"
```

#### 3. Wrap Your Tools

```python
import aegis

safe_execute, safe_read, safe_delete = aegis.wrap(
    tools=[execute_code, read_file, delete_file],
    policy="my_policy.yaml",
    agent_id="my-agent",
    on_deny="raise",
)

# Use wrapped functions
try:
    result = safe_execute(language="python", code="print('hello')")
    # This escalates - waits for human approval
except aegis.AegisViolationError as e:
    print(f"Denied: {e}")
```

#### 4. Batch Wrapping by Name

If you'd rather look tools up by name (e.g. dispatching OpenAI/Anthropic tool
calls), use `wrap_function_map()` instead:

```python
tools = {
    "execute_code": execute_code,
    "read_file": read_file,
    "delete_file": delete_file,
}

wrapped = aegis.wrap_function_map(tools, policy="my_policy.yaml", agent_id="my-agent")

wrapped["read_file"](path="/home/user/documents/report.txt")  # Allowed
wrapped["delete_file"](path="/tmp/file.txt")  # Denied
```

### SDK Configuration Options

#### On Deny Behavior

```python
# Raise AegisViolationError (default)
aegis.wrap(tools=[func], policy=policy, agent_id="agent", on_deny="raise")

# Return "AEGIS_DENIED: <reason>" instead of raising
aegis.wrap(tools=[func], policy=policy, agent_id="agent", on_deny="return_error")

# Silent failure (returns None)
aegis.wrap(tools=[func], policy=policy, agent_id="agent", on_deny="silent")
```

#### Audit Configuration

```python
from aegis import FileSink

audit_sink = FileSink(path="audit.jsonl")

wrapped = aegis.wrap(
    tools=[func], policy=policy, agent_id="agent", audit_sink=audit_sink,
)
```

### Advanced: Escalation Handling

```python
import aegis

wrapped = aegis.wrap(
    tools=[my_function],
    policy="policy.yaml",
    agent_id="my-agent",
    escalation_webhook="https://hooks.acme.com/escalations",
    escalation_timeout_minutes=30,
    on_escalate="block",  # or "notify_and_proceed"
)
```

Escalations are resolved via the dashboard's Escalations page (or its
`/api/v1/escalations/{id}/resolve` endpoint), not directly against the SDK's
in-process `EscalationManager`.

### Integration with Dashboard

Send audit records to the dashboard using the built-in sink:

```python
import aegis

dashboard_sink = aegis.AegisDashboardSink(
    base_url="http://localhost:8000",
    api_key="test_api_key_12345",
)

wrapped = aegis.wrap(
    tools=[func],
    policy="policy.yaml",
    agent_id="my-agent",
    customer_id="acme-corp",
    audit_sink=dashboard_sink,
)
```

### Example: Complete Integration

```python
import aegis

# Your AI agent tools
def execute_command(command: str):
    import subprocess
    return subprocess.check_output(command, shell=True).decode()

def access_database(query: str):
    # Your database logic
    pass

# Wrap all tools
tools = {
    "execute_command": execute_command,
    "access_database": access_database,
}

safe_tools = aegis.wrap_function_map(
    tools,
    policy="policy.yaml",
    agent_id="my-agent",
    audit_sink=aegis.FileSink(path="local_audit.jsonl"),
)

# Use in your agent
try:
    result = safe_tools["execute_command"](command="ls -la")
    print(result)
except aegis.AegisViolationError:
    print("Command blocked by policy")
```

---

## Troubleshooting

### Dashboard Won't Start

**Database connection failed:**
```bash
# Check if PostgreSQL is running
docker-compose ps

# View logs
docker-compose logs db

# Restart services
docker-compose restart
```

**Port already in use:**
```bash
# Change ports in docker-compose.yml
ports:
  - "3001:3000"  # Frontend
  - "8001:8000"  # Backend
```

### SDK Issues

**Import errors:**
```bash
# Reinstall in development mode
pip install -e .

# Or install dependencies manually
pip install pyyaml dataclasses
```

**Policy not loading:**
```python
# Check YAML syntax
import yaml
with open("policy.yaml") as f:
    policy = yaml.safe_load(f)
    print(policy)  # Should be valid dict
```

**Escalations not working:**
```python
# Wrap all tools that should share escalation/audit config in a single
# aegis.wrap() call rather than one call per tool - each call creates its
# own PolicyEngine/EscalationManager internally.
wrapped = aegis.wrap(
    tools=[func1, func2],
    policy="policy.yaml",
    agent_id="my-agent",
    escalation_webhook="https://hooks.acme.com/escalations",
)
```

### Running Tests

**SDK tests:**
```bash
cd aegis-core
pytest tests/ -v
```

**Frontend tests:**
```bash
cd aegis-dashboard/frontend
npm test
```

**Backend tests (requires database):**
```bash
cd aegis-dashboard
docker-compose up -d db
cd backend
pytest tests/ -v
```

---

## Next Steps

- Review [policy examples](../examples/policies/)
- Check [example integrations](../examples/)
- Read the [SDK Developer Guide](SDK_GUIDE.md)
