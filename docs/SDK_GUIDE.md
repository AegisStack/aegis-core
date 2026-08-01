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
version: 1.0
default_action: deny
rules:
  - tool: "send_email"
    action: escalate
  - tool: "read_file"
    action: allow
```

### 2. Wrap Your Tools

```python
from aegis import PolicyEngine, wrap_tool

# Load policy
engine = PolicyEngine.from_yaml("policy.yaml")

# Define tool
def send_email(to: str, subject: str, body: str):
    # Your email sending logic
    return f"Email sent to {to}"

# Wrap it
safe_send_email = wrap_tool(send_email, engine)

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
version: 1.0
default_action: deny  # What to do if no rules match

rules:
  - tool: "tool_name"        # Tool function name
    action: allow            # allow | deny | escalate
    conditions:              # Optional: match parameters
      - field: "param_name"
        operator: "eq"
        value: "expected_value"
```

## Common Patterns

### Pattern 1: Allow Safe Operations

```yaml
version: 1.0
default_action: deny
rules:
  # Read-only operations allowed
  - tool: "read_file"
    action: allow
  - tool: "list_directory"
    action: allow
  
  # Everything else denied by default
```

### Pattern 2: Conditional Approval

```yaml
version: 1.0
default_action: deny
rules:
  # Allow file reads only from safe directories
  - tool: "read_file"
    action: allow
    conditions:
      - field: "path"
        operator: "regex"
        value: "^/home/user/documents/.*"
  
  # Deny reads from other locations (explicit)
  - tool: "read_file"
    action: deny
```

### Pattern 3: Escalate Risky Actions

```yaml
version: 1.0
default_action: allow
rules:
  # Database writes need approval
  - tool: "execute_sql"
    action: escalate
    conditions:
      - field: "query"
        operator: "regex"
        value: ".*(UPDATE|DELETE|DROP).*"
  
  # File deletion needs approval
  - tool: "delete_file"
    action: escalate
  
  # Everything else allowed
```

### Pattern 4: Environment-Based Rules

```yaml
version: 1.0
default_action: deny
rules:
  # Allow deploys to staging
  - tool: "deploy_application"
    action: allow
    conditions:
      - field: "environment"
        operator: "eq"
        value: "staging"
  
  # Escalate production deploys
  - tool: "deploy_application"
    action: escalate
    conditions:
      - field: "environment"
        operator: "eq"
        value: "production"
```

## API Reference

### PolicyEngine

```python
from aegis import PolicyEngine

# Load from YAML file
engine = PolicyEngine.from_yaml("policy.yaml")

# Load from dict
engine = PolicyEngine.from_dict({
    "version": 1.0,
    "default_action": "deny",
    "rules": []
})

# Evaluate a decision
decision = engine.evaluate("tool_name", {"param": "value"})
print(decision.action)  # "allow", "deny", or "escalate"
```

### wrap_tool

```python
from aegis import wrap_tool

# Single function
wrapped = wrap_tool(my_function, engine, on_deny="raise")

# Multiple functions
wrapped_tools = wrap_tool(
    {"tool1": func1, "tool2": func2},
    engine,
    on_deny="raise"
)

# Options:
# on_deny="raise"         - Raise PermissionError (default)
# on_deny="return_error"  - Return {"error": "...", "denied": True}
# on_deny="silent"        - Return None silently
```

### EscalationManager

```python
from aegis import EscalationManager

mgr = EscalationManager()

# Wrap tools with escalation support
wrapped = wrap_tool(func, engine, escalation_manager=mgr)

# List pending escalations
pending = mgr.list_pending()

# Resolve escalation
mgr.resolve(
    escalation_id="esc_123",
    resolution="approved",  # or "rejected"
    reason="Reviewed and approved"
)
```

### AuditWriter

```python
from aegis.audit import AuditWriter, FileSink

# Create writer with file sink
writer = AuditWriter()
writer.add_sink(FileSink("audit.jsonl"))

# Use with wrapped tools
wrapped = wrap_tool(func, engine, audit_writer=writer)

# Every tool call is logged to audit.jsonl
```

## Testing Your Policies

```python
import pytest
from aegis import PolicyEngine

def test_policy_allows_safe_reads():
    engine = PolicyEngine.from_yaml("policy.yaml")
    decision = engine.evaluate("read_file", {"path": "/safe/file.txt"})
    assert decision.action == "allow"

def test_policy_denies_dangerous_deletes():
    engine = PolicyEngine.from_yaml("policy.yaml")
    decision = engine.evaluate("delete_file", {"path": "/important.txt"})
    assert decision.action == "deny"
```

Run tests:
```bash
pytest test_policies.py -v
```

## Integration Examples

### With LangChain

```python
from langchain.agents import Tool
from aegis import PolicyEngine, wrap_tool

engine = PolicyEngine.from_yaml("policy.yaml")

def search_database(query: str):
    # Your DB logic
    pass

# Wrap as LangChain tool
safe_search = wrap_tool(search_database, engine)
tool = Tool(
    name="DatabaseSearch",
    func=safe_search,
    description="Search the database"
)
```

### With OpenAI Function Calling

```python
import openai
from aegis import PolicyEngine, wrap_tool

engine = PolicyEngine.from_yaml("policy.yaml")

functions = {
    "send_email": send_email_func,
    "read_file": read_file_func
}

# Wrap all functions
safe_functions = wrap_tool(functions, engine)

# Use with OpenAI
response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[...],
    functions=[...],
    function_call="auto"
)

# Execute with policy enforcement
func_name = response.choices[0].message.function_call.name
func_args = json.loads(response.choices[0].message.function_call.arguments)
result = safe_functions[func_name](**func_args)
```

### With Anthropic Claude

```python
import anthropic
from aegis import PolicyEngine, wrap_tool

engine = PolicyEngine.from_yaml("policy.yaml")
client = anthropic.Anthropic()

tools = wrap_tool({
    "execute_code": execute_code_func,
    "access_files": access_files_func
}, engine)

# Use with tool calls
response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    tools=[...],
    messages=[...]
)

for block in response.content:
    if block.type == "tool_use":
        result = tools[block.name](**block.input)
```

## Performance Tips

1. **Load policies once** - Reuse PolicyEngine instances
2. **Batch wrap tools** - Use dict wrapping for multiple functions
3. **Use on_deny="silent"** - For less critical operations
4. **Async support** - Coming in v0.2.0

## CLI Usage

Validate policies:
```bash
aegis validate policy.yaml
```

Test policy decisions:
```bash
aegis test policy.yaml --tool read_file --params '{"path": "/tmp/file.txt"}'
```

Generate policy template:
```bash
aegis init > policy.yaml
```

## Configuration Files

Create `.aegisrc` in your project:

```yaml
policy_path: "./policies/production.yaml"
audit_path: "./audit/logs"
default_on_deny: "raise"
escalation_timeout: 300  # 5 minutes
```

Load in code:
```python
from aegis import load_config

config = load_config(".aegisrc")
engine = PolicyEngine.from_yaml(config["policy_path"])
```

## Best Practices

1. **Start restrictive** - Use `default_action: deny`, then allow specific tools
2. **Test policies** - Write unit tests for critical rules
3. **Version policies** - Track changes in git
4. **Audit everything** - Enable audit logging in production
5. **Review escalations** - Regularly check what's being escalated
6. **Use regex carefully** - Test patterns thoroughly
7. **Document intent** - Add comments to YAML explaining why rules exist

## Troubleshooting

**Policy not loading:**
```python
import yaml
with open("policy.yaml") as f:
    print(yaml.safe_load(f))  # Check syntax
```

**Tool not matching:**
```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

decision = engine.evaluate("tool_name", params)
# Shows which rules were evaluated
```

**Function signature lost:**
```python
# Aegis preserves signatures automatically
wrapped = wrap_tool(func, engine)
print(wrapped.__name__)      # Original name
print(wrapped.__doc__)       # Original docstring
print(wrapped.__signature__) # Original signature
```

## Support

- **Documentation:** https://github.com/yourorg/aegis-core
- **Issues:** https://github.com/yourorg/aegis-core/issues
- **Examples:** `examples/` directory in repo

## License

MIT License - See LICENSE file
