"""
Dashboard integration example.

Shows how to use AegisDashboardSink to send audit records to the dashboard.
"""

import aegis


def issue_refund(order_id: str, amount_usd: float) -> dict:
    """Issue a refund."""
    return {"refund_id": "ref_123", "amount": amount_usd, "order_id": order_id}


def update_crm(customer_id: str, notes: str) -> dict:
    """Update CRM."""
    return {"success": True, "customer_id": customer_id}


def main():
    print("=== Aegis Dashboard Integration Example ===\n")

    # Configure dashboard sink
    # In production, use your actual dashboard URL and API key
    dashboard_sink = aegis.AegisDashboardSink(
        api_key="ak_demo_key_123",  # Replace with real API key
        base_url="http://localhost:8000",  # Dashboard API URL
        async_mode=True,  # Batch and send in background
        batch_size=10,  # Send after 10 records
        batch_timeout_ms=1000,  # Or after 1 second
    )

    # Can also combine with file sink for local backup
    file_sink = aegis.FileSink(path="./audit/backup.jsonl")

    # Wrap tools with both sinks
    tools = aegis.wrap(
        tools=[issue_refund, update_crm],
        policy="./policies/example-billing.yaml",
        agent_id="billing-agent",
        customer_id="acme-corp",
        audit_sink=[dashboard_sink, file_sink],  # Multiple sinks
        on_deny="raise",
    )

    wrapped_refund, wrapped_crm = tools

    print("Testing tool calls - audit records will be sent to dashboard...\n")

    # Test 1: Small refund (allowed)
    print("1. Small refund ($100):")
    try:
        result = wrapped_refund(order_id="ord_123", amount_usd=100)
        print(f"   [OK] {result}\n")
    except aegis.AegisViolationError as e:
        print(f"   [DENIED] {e}\n")

    # Test 2: CRM update (allowed)
    print("2. CRM update:")
    try:
        result = wrapped_crm(customer_id="cust_456", notes="Customer satisfied")
        print(f"   [OK] {result}\n")
    except aegis.AegisViolationError as e:
        print(f"   [DENIED] {e}\n")

    # Test 3: Large refund (denied)
    print("3. Large refund ($5000):")
    try:
        result = wrapped_refund(order_id="ord_789", amount_usd=5000)
        print(f"   [OK] {result}\n")
    except aegis.AegisViolationError as e:
        print(f"   [DENIED] {e}\n")

    # Flush any remaining buffered records
    print("Flushing audit records to dashboard...")
    dashboard_sink.flush()
    file_sink.close()

    print("\n[OK] Complete! Check the dashboard at http://localhost:8000/docs")
    print("     View audit records at: GET /api/v1/audit?customer_id=acme-corp")


if __name__ == "__main__":
    main()
