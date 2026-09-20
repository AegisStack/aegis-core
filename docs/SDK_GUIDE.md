# Aegis SDK Developer Guide

Policy enforcement framework for AI agent tool calls.

## Installation

```bash
pip install aegis-sdk
```

Or from source:
```bash
git clone https://github.com/yourorg/aegis-core.git
cd aegis-core
pip install -e .
```

## 5-Minute Quick Start

### 1. Create Your First Policy

`policy.yaml`:
```yaml
version: 1
rules:
  - tool: "send_email"
    escalate: always
  - tool: "read_file"
    allow: always

defaults:
  unmatched_tool: deny
  unmatched_param: deny
```

### 2. Wrap Your Tools

```python
import aegis

# Define tool
def send_email(to: str, subject: str, body: str):
    # Your email sending logic
    return f"Email sent to {to}"

# Wrap it
(safe_send_email,) = aegis.wrap(
    tools=[send_email],
    policy="policy.yaml",
    agent_id="my-agent",
)

# Use it - will escalate for human approval
safe_send_email(to="user@example.com", subject="Hi", body="Hello")
```

That's it! Your tool is now policy-enforced.

## Core Concepts

### Policy Actions

- **allow** - Execute immediately
- **deny** - Block execution
- **escalate** - Pause for human approval

### Condition Operators

Match tool parameters:

| Operator | Description | Example |
|----------|-------------|---------|
| `eq` | Equals | `value: "production"` |
| `neq` | Not equals | `value: "dev"` |
| `lt` | Less than | `value: 100` |
| `lte` | Less than or equal | `value: 100` |
| `gt` | Greater than | `value: 0` |
| `gte` | Greater than or equal | `value: 0` |
| `in` | In list | `value: ["read", "write"]` |
| `not_in` | Not in list | `value: ["delete", "drop"]` |
| `regex` | Regex match | `value: "^/safe/.*"` |

### Policy Structure

```yaml
version: 1                   # Policy version (any int/string; hashed for policy_version)

rules:
  - tool: "tool_name"        # Tool function name
    allow: always            # OR a list of condition dicts, e.g.:
    #  - param_name: { eq: "expected_value" }
    escalate: [...]          # same shape as allow
    deny: [...]              # same shape as allow

defaults:
  unmatched_tool: deny       # applied when no rule matches the tool name
  unmatched_param: deny      # applied when a rule matches but no allow condition does
```

Each of `allow`/`deny`/`escalate` on a rule is either the literal string
`always`, or a list of condition dicts. A condition dict maps parameter names
to a value (or an operator dict, e.g. `{ gt: 100 }`); all keys in one dict
must match (AND), and any dict in the list matching is enough (OR). See
[Evaluation order](../README.md#evaluation-order) for how `deny`/`escalate`/`allow`
are checked in sequence.

**There is no default-allow.** `unmatched_tool` only recognizes the literal
value `"deny"` - any other value (including `"allow"`) is treated as
`"escalate"`, never as an implicit allow. Likewise `unmatched_param` only
recognizes `"escalate"` specially; anything else denies. This is intentional
fail-safe behavior: a typo'd or forgotten default can only make Aegis more
restrictive, never silently permissive.

## Common Patterns

### Pattern 1: Allow Safe Operations

```yaml
version: 1
rules:
  - tool: "read_file"
    allow: always
  - tool: "list_directory"
    allow: always

defaults:
  unmatched_tool: deny  # Everything else denied by default
```

### Pattern 2: Conditional Approval

```yaml
version: 1
rules:
  - tool: "read_file"
    allow:
      - path: { regex: "^/home/user/documents/.*" }
    # Note: deny is checked before allow, so a catch-all deny regex here
    # would always win - reads outside the allowed path are denied by
    # defaults.unmatched_param below instead.

defaults:
  unmatched_tool: deny
  unmatched_param: deny
```

### Pattern 3: Escalate Risky Actions

```yaml
version: 1
rules:
  - tool: "execute_sql"
    escalate:
      - query: { regex: ".*(UPDATE|DELETE|DROP).*" }
    allow: always  # non-matching (e.g. read-only) queries proceed

  - tool: "delete_file"
    escalate: always

  - tool: "read_file"
    allow: always

defaults:
  # Tools not explicitly listed above are denied, not allowed - see the
  # "no default-allow" note above. List every tool the agent may call.
  unmatched_tool: deny
```

### Pattern 4: Environment-Based Rules

```yaml
version: 1
rules:
  - tool: "deploy_application"
    allow:
      - environment: { eq: "staging" }
    escalate:
      - environment: { eq: "production" }

defaults:
  unmatched_tool: deny
```

## API Reference

### PolicyEngine

```python
from aegis import PolicyEngine
import yaml

# PolicyEngine takes an already-parsed policy dict, not a file path
with open("policy.yaml") as f:
    policy_dict = yaml.safe_load(f)

engine = PolicyEngine(policy_dict)

# Evaluate a decision
decision = engine.evaluate("tool_name", {"param": "value"})
print(decision.outcome)  # Outcome.ALLOW, Outcome.DENY, or Outcome.ESCALATE
```

In practice you rarely construct `PolicyEngine` directly — `aegis.wrap()` and
`aegis.wrap_function_map()` accept a policy file path or dict and build the
engine internally.

### wrap / wrap_function_map

```python
import aegis

# List of functions -> list of wrapped functions, same order
wrapped_tools = aegis.wrap(
    tools=[func1, func2],
    policy="policy.yaml",   # file path or a policy dict
    agent_id="my-agent",
    on_deny="raise",
)

# Dict of {name: function} -> dict of {name: wrapped function}
wrapped_map = aegis.wrap_function_map(
    {"tool1": func1, "tool2": func2},
    policy="policy.yaml",
    agent_id="my-agent",
    on_deny="raise",
)

# on_deny="raise"         - Raise AegisViolationError (default)
# on_deny="return_error"  - Return "AEGIS_DENIED: <reason>"
# on_deny="silent"        - Return None silently
```

### EscalationManager

```python
import aegis

wrapped = aegis.wrap(
    tools=[func],
    policy="policy.yaml",
    agent_id="my-agent",
    escalation_webhook="https://hooks.acme.com/escalations",
    escalation_timeout_minutes=30,
    on_escalate="block",  # or "notify_and_proceed"
)
```

`aegis.wrap()` creates and owns the `EscalationManager` internally — pass
`escalation_webhook`/`escalation_timeout_minutes`/`on_escalate` to `wrap()`
rather than constructing `EscalationManager` yourself, unless you're
building a custom integration (see `aegis/core/escalation.py`).

### AuditWriter / Sinks

```python
import aegis

wrapped = aegis.wrap(
    tools=[func],
    policy="policy.yaml",
    agent_id="my-agent",
    audit_sink=aegis.FileSink(path="audit.jsonl"),
    # or a list to fan out to multiple sinks:
    # audit_sink=[aegis.FileSink(path="audit.jsonl"), aegis.WebhookSink(url="...")],
)

# Every tool call is logged to audit.jsonl
```

## Testing Your Policies

```python
from aegis import PolicyEngine, Outcome

def load_engine(path):
    import yaml
    with open(path) as f:
        return PolicyEngine(yaml.safe_load(f))

def test_policy_allows_safe_reads():
    engine = load_engine("policy.yaml")
    decision = engine.evaluate("read_file", {"path": "/safe/file.txt"})
    assert decision.outcome == Outcome.ALLOW

def test_policy_denies_dangerous_deletes():
    engine = load_engine("policy.yaml")
    decision = engine.evaluate("delete_file", {"path": "/important.txt"})
    assert decision.outcome == Outcome.DENY
```

Run tests:
```bash
pytest test_policies.py -v
```

## Integration Examples

### With LangChain

```python
from langchain.tools import Tool
import aegis

def search_database(query: str):
    # Your DB logic
    pass

raw_tools = [Tool(name="search_database", func=search_database, description="...")]

wrapped_tools = aegis.wrap_langchain_tools(
    tools=raw_tools,
    policy="policy.yaml",
    agent_id="my-agent",
)
```

### With OpenAI Function Calling

```python
import aegis

functions = {
    "send_email": send_email_func,
    "read_file": read_file_func,
}

safe_functions = aegis.wrap_function_map(functions, policy="policy.yaml", agent_id="my-agent")

# Execute with policy enforcement
func_name = response.choices[0].message.function_call.name
func_args = json.loads(response.choices[0].message.function_call.arguments)
result = safe_functions[func_name](**func_args)
```

### With Anthropic Claude

```python
import aegis

tools = aegis.wrap_function_map(
    {
        "execute_code": execute_code_func,
        "access_files": access_files_func,
    },
    policy="policy.yaml",
    agent_id="my-agent",
)

for block in response.content:
    if block.type == "tool_use":
        result = tools[block.name](**block.input)
```

### MCP server

```python
from mcp.server import Server
import aegis

server = Server("my-agent")

@server.call_tool()
@aegis.mcp_enforce(policy="policy.yaml", agent_id="my-agent")
async def handle_tool_call(name: str, arguments: dict):
    if name == "issue_refund":
        return await issue_refund(**arguments)
```

## Performance Tips

1. **Load policies once** - Call `aegis.wrap()` once per agent lifecycle, not per tool call.
2. **Batch wrap tools** - Use `wrap_function_map()` for multiple functions.
3. **Use on_deny="silent"** - For less critical operations.

## Best Practices

1. **Start restrictive** - Set `defaults.unmatched_tool: deny`, then allow specific tools.
2. **Test policies** - Write unit tests for critical rules (see [Testing Your Policies](#testing-your-policies)).
3. **Version policies** - Track changes in git.
4. **Audit everything** - Enable audit logging in production.
5. **Review escalations** - Regularly check what's being escalated.
6. **Use regex carefully** - Test patterns thoroughly.
7. **Document intent** - Add comments to YAML explaining why rules exist.

## Troubleshooting

**Policy not loading:**
```python
import yaml
with open("policy.yaml") as f:
    print(yaml.safe_load(f))  # Check syntax
```

**Tool not matching:**
```python
decision = engine.evaluate("tool_name", params)
print(decision.matched_rule, decision.reason)  # Shows which rule/default applied
```

**Function signature lost:**
```python
# Aegis preserves signatures automatically
(wrapped,) = aegis.wrap(tools=[func], policy="policy.yaml", agent_id="my-agent")
print(wrapped.__name__)      # Original name
print(wrapped.__doc__)       # Original docstring
```

## Support

- **Documentation:** https://github.com/yourorg/aegis-core
- **Issues:** https://github.com/yourorg/aegis-core/issues
- **Examples:** `examples/` directory in repo

## License

MIT License - See LICENSE file
