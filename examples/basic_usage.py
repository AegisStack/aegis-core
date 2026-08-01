"""
Basic usage example of Aegis SDK.

Demonstrates wrapping tools with policy enforcement.
"""

import aegis


# Define some tools
def issue_refund(order_id: str, amount_usd: float) -> dict:
    """Issue a refund for an order."""
    print(f"Issuing refund of ${amount_usd} for order {order_id}")
    return {"refund_id": "ref_123", "amount": amount_usd, "order_id": order_id}


def update_crm(customer_id: str, notes: str) -> dict:
    """Update CRM with customer notes."""
    print(f"Updating CRM for customer {customer_id}: {notes}")
    return {"success": True, "customer_id": customer_id}


def deploy(environment: str) -> dict:
    """Deploy to production (dangerous!)."""
    print(f"Deploying to {environment}")
    return {"deployed": True, "environment": environment}


def main():
    # Set up file-based audit sink
    audit_sink = aegis.FileSink(path="./audit/billing-agent.jsonl")

    # Wrap tools with policy enforcement
    tools = aegis.wrap(
        tools=[issue_refund, update_crm, deploy],
        policy="./examples/policies/example-billing.yaml",
        agent_id="billing-agent",
        customer_id="acme-corp",
        audit_sink=audit_sink,
        on_deny="raise",
    )

    wrapped_refund, wrapped_crm, wrapped_deploy = tools

    print("=== Test 1: Small refund (should be allowed) ===")
    try:
        result = wrapped_refund(order_id="ord_123", amount_usd=100)
        print(f"[OK] Success: {result}")
    except aegis.AegisViolationError as e:
        print(f"[DENIED] {e}")

    print("\n=== Test 2: Large refund (should be denied) ===")
    try:
        result = wrapped_refund(order_id="ord_456", amount_usd=5000)
        print(f"[OK] Success: {result}")
    except aegis.AegisViolationError as e:
        print(f"[DENIED] {e}")

    print("\n=== Test 3: CRM update (always allowed) ===")
    try:
        result = wrapped_crm(customer_id="cust_789", notes="Customer requested refund")
        print(f"[OK] Success: {result}")
    except aegis.AegisViolationError as e:
        print(f"[DENIED] {e}")

    print("\n=== Test 4: Deploy (always denied) ===")
    try:
        result = wrapped_deploy(environment="production")
        print(f"[OK] Success: {result}")
    except aegis.AegisViolationError as e:
        print(f"[DENIED] {e}")

    # Close the audit sink
    audit_sink.close()

    print("\n[OK] Audit trail written to ./audit/billing-agent.jsonl")


if __name__ == "__main__":
    main()
