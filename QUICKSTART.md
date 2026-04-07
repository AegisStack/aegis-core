# Aegis Quickstart Guide

## Table of Contents
1. [Running the Dashboard Locally](#running-the-dashboard-locally)
2. [Using the Aegis SDK](#using-the-aegis-sdk)
3. [Troubleshooting](#troubleshooting)

---

## Running the Dashboard Locally

### Prerequisites
- Docker & Docker Compose
- Node.js 18+ and npm
- Python 3.10+

### Step 1: Start Backend Services

```bash
cd aegis-dashboard
docker-compose up -d
```

This starts:
- PostgreSQL 15 with TimescaleDB (port 5432)
- Backend API (port 8000)
- Frontend (port 3000)

### Step 2: Initialize the Database

```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
```

### Step 3: Create Test Users

```bash
python -c "
from app.core.auth import get_password_hash
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models.database import User, Customer

async def create_users():
    engine = create_async_engine('postgresql+asyncpg://aegis:aegis_password@localhost/aegis_db')
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Create customer
        customer = Customer(
            customer_id='customer_1',
            name='Test Company',
            api_key='test_api_key_123'
        )
        session.add(customer)
        await session.flush()
        
        # Create admin user
        admin = User(
            email='admin@test.com',
            full_name='Admin User',
            hashed_password=get_password_hash('admin123'),
            customer_id='customer_1',
            role='admin',
            is_active=True,
            is_verified=True
        )
        session.add(admin)
        await session.commit()
        print('✅ Created admin@test.com / admin123')

asyncio.run(create_users())
"
```

### Step 4: Access the Dashboard

Open http://localhost:3000 and log in:
- Email: `admin@test.com`
- Password: `admin123`

### Available Endpoints

- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **WebSocket:** ws://localhost:8000/ws

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
version: 1.0
default_action: deny
rules:
  - tool: "execute_code"
    action: escalate
    conditions:
      - field: "language"
        operator: "in"
        value: ["python", "javascript"]
  
  - tool: "read_file"
    action: allow
    conditions:
      - field: "path"
        operator: "regex"
        value: "^/home/user/documents/.*"
  
  - tool: "delete_file"
    action: deny
```

#### 2. Initialize Aegis

```python
from aegis import PolicyEngine, wrap_tool

# Load policy
engine = PolicyEngine.from_yaml("my_policy.yaml")

# Define your tool functions
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
# Wrap individual functions
safe_execute = wrap_tool(execute_code, engine, on_deny="raise")
safe_read = wrap_tool(read_file, engine, on_deny="raise")
safe_delete = wrap_tool(delete_file, engine, on_deny="raise")

# Use wrapped functions
try:
    result = safe_execute(language="python", code="print('hello')")
    # This escalates - waits for human approval
except PermissionError as e:
    print(f"Denied: {e}")
```

#### 4. Batch Wrapping

```python
tools = {
    "execute_code": execute_code,
    "read_file": read_file,
    "delete_file": delete_file
}

wrapped = wrap_tool(tools, engine, on_deny="raise")

# Use wrapped tools
wrapped["read_file"](path="/home/user/documents/report.txt")  # ✅ Allowed
wrapped["delete_file"](path="/tmp/file.txt")  # ❌ Denied
```

### SDK Configuration Options

#### On Deny Behavior

```python
# Raise exception (default)
wrap_tool(func, engine, on_deny="raise")

# Return error dict
wrap_tool(func, engine, on_deny="return_error")

# Silent failure (returns None)
wrap_tool(func, engine, on_deny="silent")
```

#### Audit Configuration

```python
from aegis.audit import FileSink, AuditWriter

# Configure audit writer
audit_writer = AuditWriter()
audit_writer.add_sink(FileSink("audit.jsonl"))

# Pass to wrapper
wrap_tool(func, engine, audit_writer=audit_writer)
```

### Advanced: Escalation Handling

```python
from aegis import PolicyEngine, wrap_tool, EscalationManager

engine = PolicyEngine.from_yaml("policy.yaml")
escalation_mgr = EscalationManager()

# Wrap with escalation support
safe_tool = wrap_tool(
    my_function,
    engine,
    escalation_manager=escalation_mgr,
    on_deny="raise"
)

# In another thread/process, resolve escalations
pending = escalation_mgr.list_pending()
for esc in pending:
    print(f"Escalation {esc.escalation_id}: {esc.tool_name}({esc.arguments})")
    # Human reviews and approves
    escalation_mgr.resolve(esc.escalation_id, "approved", "Looks safe")
```

### Integration with Dashboard

Send audit records to the dashboard:

```python
import requests
from aegis.events import ObservabilityEvent

def send_to_dashboard(event: ObservabilityEvent):
    """Send audit event to Aegis Dashboard."""
    requests.post(
        "http://localhost:8000/api/v1/ingest/audit",
        headers={"X-API-Key": "test_api_key_123"},
        json=event.to_dict()
    )

# Use with custom sink
class DashboardSink:
    def write(self, record):
        send_to_dashboard(record.event)

from aegis.audit import AuditWriter
writer = AuditWriter()
writer.add_sink(DashboardSink())

wrap_tool(func, engine, audit_writer=writer)
```

### Example: Complete Integration

```python
from aegis import PolicyEngine, wrap_tool
from aegis.audit import AuditWriter, FileSink
import requests

# Setup
engine = PolicyEngine.from_yaml("policy.yaml")
audit_writer = AuditWriter()
audit_writer.add_sink(FileSink("local_audit.jsonl"))

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
    "access_database": access_database
}

safe_tools = wrap_tool(
    tools,
    engine,
    audit_writer=audit_writer,
    on_deny="raise"
)

# Use in your agent
try:
    result = safe_tools["execute_command"](command="ls -la")
    print(result)
except PermissionError:
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
# Ensure escalation manager is shared across tool wrappers
from aegis import EscalationManager

mgr = EscalationManager()  # Create once
wrap_tool(func1, engine, escalation_manager=mgr)
wrap_tool(func2, engine, escalation_manager=mgr)  # Same instance
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

- Read the [full technical specification](aegis-techspec.docx.txt)
- Review [policy examples](policies/)
- Check [example integrations](examples/)
- See [dashboard summary](DASHBOARD_SUMMARY.md)
- View [test results](TEST_RESULTS.md)
