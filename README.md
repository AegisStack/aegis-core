# Aegis SDK

**Policy Enforcement and Observability for AI Agent Tool Calls**

Aegis is a Python SDK and dashboard platform that enables infrastructure-level policy enforcement for AI agent tool calls. It wraps functions, evaluates them against YAML-based policies, and produces structured audit records for every action.

## Features

- **🛡️ Infrastructure-enforced policy controls** - Enforcement at the tool call layer, not prompt layer
- **📋 Customer-configurable policies** - YAML-based policies with 8 condition operators
- **📊 Real-time observability dashboard** - Web UI for monitoring, alerts, and audit trails
- **🔌 Framework-agnostic** - Works with any Python function or AI framework
- **🚨 Human-in-the-loop escalation** - High-risk actions pause for human approval
- **⚡ High performance** - Batched async ingestion, TimescaleDB time-series storage

## Quick Links

- **[🚀 Quickstart Guide](QUICKSTART.md)** - Run the dashboard locally, set up database
- **[📚 SDK Developer Guide](SDK_GUIDE.md)** - Complete API reference, patterns, integrations
- **[📋 Dashboard Summary](DASHBOARD_SUMMARY.md)** - Architecture, features, deployment
- **[🧪 Test Results](TEST_RESULTS.md)** - 68 tests passing (44 SDK + 24 frontend)

## Installation

**SDK Only:**
```bash
cd aegis-core
pip install -e .
```

**Full Platform (Dashboard + SDK):**
```bash
cd aegis-dashboard
docker-compose up -d
```

See [QUICKSTART.md](QUICKSTART.md) for detailed setup instructions.

## Quick Start

### 1. Create a Policy

`policy.yaml`:
```yaml
version: 1.0
default_action: deny

rules:
  - tool: "send_email"
    action: escalate
    
  - tool: "read_file"
    action: allow
    conditions:
      - field: "path"
        operator: "regex"
        value: "^/safe/.*"
  
  - tool: "delete_file"
    action: deny
```

### 2. Wrap Your Tools

```python
from aegis import PolicyEngine, wrap_tool

# Load policy
engine = PolicyEngine.from_yaml("policy.yaml")

# Your tool functions
def send_email(to: str, subject: str, body: str):
    # Send email logic
    return f"Email sent to {to}"

def read_file(path: str):
    with open(path) as f:
        return f.read()

def delete_file(path: str):
    import os
    os.remove(path)
    return f"Deleted {path}"

# Wrap with policy enforcement
wrapped = wrap_tool({
    "send_email": send_email,
    "read_file": read_file,
    "delete_file": delete_file
}, engine, on_deny="raise")

# Use wrapped tools
wrapped["read_file"](path="/safe/file.txt")  # ✅ Allowed
wrapped["send_email"](to="user@example.com", subject="Hi", body="Hello")  # ⏸️ Escalates
wrapped["delete_file"](path="/important.txt")  # ❌ Denied
```

### 3. View in Dashboard

Send audit records to the dashboard for monitoring:

```python
import requests

def send_to_dashboard(event):
    requests.post(
        "http://localhost:8000/api/v1/ingest/audit",
        headers={"X-API-Key": "your_api_key"},
        json=event.to_dict()
    )
```

Dashboard provides:
- Real-time tool call monitoring
- Policy editor with YAML validation
- Audit trail with filtering
- Alert management
- WebSocket live feed

## Policy Language

### Condition Operators

| Operator | Meaning | Example |
|----------|---------|---------|
| `eq` / `neq` | Equality | `status: { eq: draft }` |
| `lt` / `lte` | Less than | `amount: { lte: 500 }` |
| `gt` / `gte` | Greater than | `amount: { gt: 100 }` |
| `in` / `not_in` | List membership | `domain: { in: [acme.com] }` |
| `regex` | Regex match | `path: { regex: ^/tmp/ }` |
| `always` | Unconditional | `allow: always` |

### Evaluation Order

1. Check if tool is in policy (apply `defaults.unmatched_tool` if not)
2. Evaluate `deny` conditions (first match blocks immediately)
3. Evaluate `escalate` conditions (first match pauses for human approval)
4. Evaluate `allow` conditions (first match permits execution)
5. If no allow matches, apply `defaults.unmatched_param`

## Framework Integrations

### LangChain

```python
from langchain.tools import Tool
import aegis

raw_tools = [
    Tool(name='issue_refund', func=issue_refund, description='...'),
    Tool(name='update_crm', func=update_crm, description='...'),
]

tools = aegis.wrap_langchain_tools(
    tools=raw_tools,
    policy='./policies/acme-corp.yaml',
    agent_id='billing-agent',
    customer_id='acme-corp'
)
```

### MCP Server

```python
from mcp.server import Server
import aegis

server = Server('billing-agent')

@server.call_tool()
@aegis.mcp_enforce(
    policy=lambda ctx: aegis.load_customer_policy(ctx.customer_id),
    agent_id='billing-agent'
)
async def handle_tool_call(name: str, arguments: dict):
    if name == 'issue_refund':
        return await issue_refund(**arguments)
```

### Raw OpenAI Function Calling

```python
import aegis

function_map = {
    'issue_refund': issue_refund,
    'update_crm': update_crm,
}

wrapped = aegis.wrap_function_map(
    function_map,
    policy='./policies/acme-corp.yaml',
    agent_id='billing-agent',
    customer_id='acme-corp'
)

# After model response
result = wrapped[tool_call.function.name](**arguments)
```

## Multi-Tenant Deployments

```python
import aegis

# Register policy store
aegis.register_policy_store(
    backend='s3',
    bucket='aegis-policies',
    cache_ttl=60
)

# Load customer-specific policy at request time
tools = aegis.wrap(
    tools=raw_tools,
    policy=aegis.load_customer_policy(session.customer_id),
    agent_id='billing-agent',
    customer_id=session.customer_id
)
```

## Audit Trail

Every tool call produces a structured audit record:

```json
{
  "record_id": "uuid-v4",
  "timestamp": "2024-11-15T14:32:01.234Z",
  "customer_id": "acme-corp",
  "agent_id": "billing-agent",
  "tool_name": "issue_refund",
  "params": {"order_id": "ord_789", "amount_usd": 340.00},
  "outcome": "allow",
  "matched_rule": "issue_refund.allow[0]",
  "reason": "Amount within limit",
  "execution_result": {"refund_id": "ref_456"},
  "latency_ms": 4
}
```

### Audit Sinks

```python
from aegis.sinks import FileSink, WebhookSink

# File sink - newline-delimited JSON
sink = FileSink(path='./audit/agent.jsonl', rotate='daily')

# Webhook sink - POST to your SIEM
sink = WebhookSink(
    url='https://ingest.acme.com/aegis',
    headers={'Authorization': 'Bearer TOKEN'},
    async_mode=True
)

# Multiple sinks
tools = aegis.wrap(
    tools=raw_tools,
    policy=policy,
    agent_id='agent',
    audit_sink=[file_sink, webhook_sink]
)
```

## Escalation Flow

When a tool call matches an `escalate` condition:

1. Aegis writes audit record with `outcome: "escalate"`
2. Fires webhook notification to configured URL
3. Blocks execution (default) or continues (`on_escalate="notify_and_proceed"`)
4. Human approves/denies via resolution API
5. Aegis updates audit record with resolution details

```python
tools = aegis.wrap(
    tools=raw_tools,
    policy=policy,
    agent_id='billing-agent',
    escalation_webhook='https://hooks.acme.com/escalations',
    escalation_timeout_minutes=30,
    on_escalate='block'  # or 'notify_and_proceed'
)
```

## Error Handling

### on_deny Behaviors

| Setting | Behavior | When to use |
|---------|----------|-------------|
| `raise` (default) | Raises `AegisViolationError` | Production - fails loudly |
| `return_error` | Returns `"AEGIS_DENIED: <reason>"` | Agent should adapt and retry |
| `silent` | Returns `None` | Debugging only |

```python
tools = aegis.wrap(
    tools=raw_tools,
    policy=policy,
    agent_id='agent',
    on_deny='return_error'  # Agent can read error and try alternative
)
```

## Performance

| Operation | Target | Notes |
|-----------|--------|-------|
| Simple evaluation | < 2ms | Single rule match |
| Complex policy (20+ rules) | < 10ms | Full tree traversal |
| Policy load (disk, cached) | < 50ms | After first load |
| Policy load (S3, cached) | < 200ms | Configurable TTL |

## Development

```bash
# Clone repository
git clone https://github.com/aegis/aegis-sdk
cd aegis-sdk

# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=aegis --cov-report=html

# Format code
black aegis tests

# Type check
mypy aegis
```

## Project Structure

```
aegis-core/
├── aegis/                   # SDK source code
│   ├── __init__.py
│   ├── audit.py            # Audit logging
│   ├── escalation.py       # Escalation management
│   ├── events.py           # Event data models
│   ├── policy_engine.py    # Policy evaluation
│   └── wrapper.py          # Tool wrapping
├── tests/                   # SDK tests (44 tests)
├── examples/                # Usage examples
├── policies/                # Example policies
├── aegis-dashboard/         # Full-stack dashboard
│   ├── backend/            # FastAPI + SQLAlchemy
│   │   ├── app/
│   │   ├── alembic/
│   │   └── tests/          # Backend tests (13 tests)
│   ├── frontend/           # Next.js + React
│   │   ├── src/
│   │   └── tests/          # Frontend tests (24 tests)
│   └── docker-compose.yml
└── docs/
    ├── QUICKSTART.md       # Local setup guide
    ├── SDK_GUIDE.md        # Developer reference
    ├── DASHBOARD_SUMMARY.md
    └── TEST_RESULTS.md
```

## Examples

See `examples/` for complete working examples:
- `basic_example.py` - Simple policy enforcement
- `multi_tool_example.py` - Multiple tools with conditions
- `escalation_example.py` - Human-in-the-loop workflow

## License

MIT

## Contributing

Contributions welcome! Please open an issue or PR.

## Support

- Issues: https://github.com/yourorg/aegis-core/issues
- Documentation: [QUICKSTART.md](QUICKSTART.md), [SDK_GUIDE.md](SDK_GUIDE.md)
