# Aegis SDK

**Policy Enforcement and Observability for Agent Builders**

Aegis is a Python SDK that agent builders and MCP server authors embed into their products. It wraps tool calls, evaluates them against customer-configurable policies, and produces structured audit records of every action.

## Features

- **🛡️ Infrastructure-enforced policy controls** - Enforcement at the tool call layer, not prompt layer
- **📋 Customer-configurable policies** - YAML-based policies customers can modify without touching code
- **📊 Policy-aware audit trail** - Structured, immutable records of every tool call evaluation
- **🔌 Framework-agnostic** - Works with LangChain, CrewAI, MCP servers, or raw function calls
- **🚨 Human-in-the-loop escalation** - High-risk actions pause for human approval
- **⚡ High performance** - Sub-2ms policy evaluation for simple rules

## Installation

```bash
pip install aegis-sdk

# With optional dependencies
pip install aegis-sdk[langchain]  # LangChain integration
pip install aegis-sdk[mcp]        # MCP server integration
pip install aegis-sdk[s3]         # S3 policy storage
pip install aegis-sdk[gcs]        # GCS policy storage
```

## Quick Start

### 1. Define your tools

```python
def issue_refund(order_id: str, amount_usd: float) -> dict:
    """Issue a refund for the given order."""
    # Your implementation here
    return {"refund_id": "ref_123", "amount": amount_usd}

def update_crm(customer_id: str, notes: str) -> dict:
    """Update CRM with customer notes."""
    # Your implementation here
    return {"success": True}
```

### 2. Create a policy file

```yaml
# policies/acme-corp.yaml
version: 1
customer_id: acme-corp

rules:
  - tool: issue_refund
    allow:
      - amount_usd: { lte: 200 }
    escalate:
      - amount_usd: { gt: 200, lte: 2000 }
    deny:
      - amount_usd: { gt: 2000 }

  - tool: update_crm
    allow: always

defaults:
  unmatched_tool: deny
  unmatched_param: escalate
```

### 3. Wrap your tools

```python
import aegis

# Wrap tools with policy enforcement
tools = aegis.wrap(
    tools=[issue_refund, update_crm],
    policy="./policies/acme-corp.yaml",
    agent_id="billing-agent",
    customer_id="acme-corp",
    audit_sink=aegis.FileSink(path="./audit/billing-agent.jsonl"),
)

# Use wrapped tools - they have identical interfaces
wrapped_refund, wrapped_crm = tools

# Small refund - allowed
result = wrapped_refund(order_id="ord_123", amount_usd=100)

# Large refund - denied
try:
    result = wrapped_refund(order_id="ord_456", amount_usd=5000)
except aegis.AegisViolationError as e:
    print(f"Policy violation: {e}")
```

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

## Examples

See the `examples/` directory for complete working examples:

- `basic_usage.py` - Simple tool wrapping
- `langchain_example.py` - LangChain integration
- `multi_tenant.py` - Multi-customer policy loading

## License

MIT

## Contributing

Contributions welcome! Please open an issue or PR.

## Support

- Documentation: https://docs.aegis.dev
- Issues: https://github.com/aegis/aegis-sdk/issues
