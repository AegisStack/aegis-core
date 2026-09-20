# Aegis

**Policy enforcement and observability for AI agent tool calls.**

Aegis is a Python SDK and dashboard platform that provides infrastructure-level
policy enforcement for AI agent tool calls. It wraps tool functions, evaluates
each call against YAML-based policies, and produces a structured audit record
for every action — allowed, denied, or escalated for human approval.

## Features

- **Infrastructure-enforced controls** — enforcement happens at the tool-call layer, not the prompt layer.
- **Configurable policies** — YAML-based rules with 8 condition operators.
- **Real-time observability** — web dashboard for monitoring, alerts, and audit trails.
- **Framework-agnostic** — works with any Python function, LangChain, MCP, or raw OpenAI function calling.
- **Human-in-the-loop escalation** — high-risk actions pause for human approval.
- **High performance** — batched async ingestion with TimescaleDB time-series storage.

## Repository Layout

```
aegis-core/
├── aegis/                  # Python SDK
│   ├── audit/              # Audit records, schema, writer
│   ├── core/               # Policy engine, loader, wrapper, escalation
│   ├── integrations/       # LangChain and MCP adapters
│   ├── obs/                # Observability events
│   └── sinks/              # File, webhook, and dashboard sinks
├── tests/                  # SDK test suite
├── examples/               # Runnable usage examples
│   └── policies/           # Example policy files used by the examples
├── aegis-dashboard/        # Full-stack observability dashboard
│   ├── backend/            # FastAPI + SQLAlchemy + TimescaleDB
│   └── frontend/           # Next.js + React + Tailwind
└── docs/                   # Guides and reference
    ├── RUNNING_LOCALLY.md   # Local setup for SDK + dashboard
    ├── QUICKSTART.md        # Quick SDK + dashboard walkthrough
    ├── SDK_GUIDE.md         # Full SDK developer reference
    ├── RELEASING.md         # Release process
    └── internal/            # Internal notes and specs
```

## Documentation

- [Running Locally](docs/RUNNING_LOCALLY.md) — get the SDK and dashboard running on your machine.
- [Quickstart](docs/QUICKSTART.md) — a fast walkthrough of the SDK and dashboard.
- [SDK Developer Guide](docs/SDK_GUIDE.md) — complete API reference, patterns, and integrations.
- [Contributing](CONTRIBUTING.md) — how to set up a dev environment and submit changes.
- [Releasing](docs/RELEASING.md) — how releases are cut and published.

## Installation

**SDK only:**

```bash
pip install -e .
```

**Full platform (SDK + dashboard):** see [Running Locally](docs/RUNNING_LOCALLY.md).

## Quick Start

### 1. Create a policy

`policy.yaml`:

```yaml
version: 1
rules:
  - tool: "send_email"
    escalate: always

  - tool: "read_file"
    allow:
      - path: { regex: "^/safe/.*" }

  - tool: "delete_file"
    deny: always

defaults:
  unmatched_tool: deny
  unmatched_param: deny  # non-matching read_file paths are denied by this default
```

### 2. Wrap your tools

```python
import aegis

def send_email(to: str, subject: str, body: str):
    return f"Email sent to {to}"

def read_file(path: str):
    with open(path) as f:
        return f.read()

def delete_file(path: str):
    import os
    os.remove(path)
    return f"Deleted {path}"

wrapped_send, wrapped_read, wrapped_delete = aegis.wrap(
    tools=[send_email, read_file, delete_file],
    policy="policy.yaml",
    agent_id="my-agent",
    on_deny="raise",
)

wrapped_read(path="/safe/file.txt")                     # Allowed
wrapped_send(to="user@example.com", subject="Hi", body="Hello")  # Escalates
wrapped_delete(path="/important.txt")                    # Denied
```

Prefer a dict of `{name: function}` (e.g. for OpenAI-style function calling)? Use
`aegis.wrap_function_map()` instead — see [Raw OpenAI function calling](#raw-openai-function-calling) below.

### 3. View in the dashboard

Send audit records to the dashboard for monitoring:

```python
import requests

def send_to_dashboard(event):
    requests.post(
        "http://localhost:8000/api/v1/ingest/audit",
        headers={"X-API-Key": "your_api_key"},
        json=event.to_dict(),
    )
```

The dashboard provides real-time tool-call monitoring, a policy editor with YAML
validation, a filterable audit trail, escalation management, and a WebSocket live feed.

## Policy Language

### Condition operators

| Operator | Meaning | Example |
|----------|---------|---------|
| `eq` / `neq` | Equality | `status: { eq: draft }` |
| `lt` / `lte` | Less than | `amount: { lte: 500 }` |
| `gt` / `gte` | Greater than | `amount: { gt: 100 }` |
| `in` / `not_in` | List membership | `domain: { in: [acme.com] }` |
| `regex` | Regex match | `path: { regex: ^/tmp/ }` |
| `always` | Unconditional | `allow: always` |

### Evaluation order

1. Check if the tool is in the policy (apply `defaults.unmatched_tool` if not).
2. Evaluate `deny` conditions (first match blocks immediately).
3. Evaluate `escalate` conditions (first match pauses for human approval).
4. Evaluate `allow` conditions (first match permits execution).
5. If no allow matches, apply `defaults.unmatched_param`.

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
    customer_id='acme-corp',
)
```

### MCP server

```python
from mcp.server import Server
import aegis

server = Server('billing-agent')

@server.call_tool()
@aegis.mcp_enforce(
    policy=lambda ctx: aegis.load_customer_policy(ctx.customer_id),
    agent_id='billing-agent',
)
async def handle_tool_call(name: str, arguments: dict):
    if name == 'issue_refund':
        return await issue_refund(**arguments)
```

### Raw OpenAI function calling

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
    customer_id='acme-corp',
)

result = wrapped[tool_call.function.name](**arguments)
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

### Audit sinks

```python
from aegis.sinks import FileSink, WebhookSink

file_sink = FileSink(path='./audit/agent.jsonl', rotate='daily')

webhook_sink = WebhookSink(
    url='https://ingest.acme.com/aegis',
    headers={'Authorization': 'Bearer TOKEN'},
    async_mode=True,
)

tools = aegis.wrap(
    tools=raw_tools,
    policy=policy,
    agent_id='agent',
    audit_sink=[file_sink, webhook_sink],
)
```

## Escalation Flow

When a tool call matches an `escalate` condition, Aegis:

1. Writes an audit record with `outcome: "escalate"`.
2. Fires a webhook notification to the configured URL.
3. Blocks execution (default) or continues (`on_escalate="notify_and_proceed"`).
4. Waits for a human to approve or deny via the resolution API.
5. Updates the audit record with the resolution details.

```python
tools = aegis.wrap(
    tools=raw_tools,
    policy=policy,
    agent_id='billing-agent',
    escalation_webhook='https://hooks.acme.com/escalations',
    escalation_timeout_minutes=30,
    on_escalate='block',  # or 'notify_and_proceed'
)
```

## Error Handling

### `on_deny` behaviors

| Setting | Behavior | When to use |
|---------|----------|-------------|
| `raise` (default) | Raises `AegisViolationError` | Production — fails loudly |
| `return_error` | Returns `"AEGIS_DENIED: <reason>"` | Agent should adapt and retry |
| `silent` | Returns `None` | Debugging only |

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=aegis --cov-report=html

# Format and lint
black aegis tests
ruff check aegis tests

# Type check
mypy aegis
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full contributor workflow and
[docs/RUNNING_LOCALLY.md](docs/RUNNING_LOCALLY.md) for running the dashboard.

## Examples

See [examples/](examples/) for complete working examples:

- `basic_usage.py` — simple policy enforcement.
- `multi_tenant.py` — per-customer policies.
- `langchain_example.py` — LangChain integration.
- `dashboard_integration.py` — sending audit records to the dashboard.

## Contributing

Contributions are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) before
opening an issue or pull request.
