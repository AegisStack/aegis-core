"""
LangChain integration example.

Shows how to wrap LangChain tools with Aegis policy enforcement.
"""

import aegis


def issue_refund(order_id: str, amount_usd: float) -> dict:
    """Issue a refund."""
    return {"refund_id": "ref_123", "amount": amount_usd}


def update_crm(customer_id: str, notes: str) -> dict:
    """Update CRM."""
    return {"success": True}


def main():
    try:
        from langchain.tools import Tool
    except ImportError:
        print("LangChain not installed. Install with: pip install aegis-sdk[langchain]")
        return

    # Create LangChain tools
    raw_tools = [
        Tool(
            name="issue_refund",
            func=issue_refund,
            description="Issue a refund for an order"
        ),
        Tool(
            name="update_crm",
            func=update_crm,
            description="Update CRM with customer notes"
        ),
    ]

    # Wrap with Aegis enforcement
    tools = aegis.wrap_langchain_tools(
        tools=raw_tools,
        policy="./examples/policies/example-billing.yaml",
        agent_id="billing-agent",
        customer_id="acme-corp",
        audit_sink=aegis.FileSink(path="./audit/langchain-agent.jsonl"),
    )

    print("=== LangChain Tools Wrapped with Aegis ===")
    print(f"Number of tools: {len(tools)}")

    # Use the tools
    print("\nTesting small refund (should be allowed):")
    try:
        result = tools[0].func(order_id="ord_123", amount_usd=100)
        print(f"[OK] Success: {result}")
    except aegis.AegisViolationError as e:
        print(f"[DENIED] {e}")

    print("\nTesting large refund (should be denied):")
    try:
        result = tools[0].func(order_id="ord_456", amount_usd=5000)
        print(f"[OK] Success: {result}")
    except aegis.AegisViolationError as e:
        print(f"[DENIED] {e}")


if __name__ == "__main__":
    main()
