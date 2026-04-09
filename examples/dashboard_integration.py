"""
Dashboard integration example.

Shows the full sync loop between the Aegis SDK and the dashboard:

  1. The dashboard stores policies in PostgreSQL (managed via the Policies UI).
  2. DashboardPolicyStore fetches the *active* policy for this agent at startup
     (and re-fetches it on every cache-miss, so live edits are picked up
     automatically within the configured TTL).
  3. AegisDashboardSink posts every audit record back to the dashboard so the
     Audit, Metrics and Escalations pages stay up to date.

Prerequisites
-------------
- Dashboard running: docker compose up (see aegis-dashboard/docker-compose.yml)
- A customer + API key seeded: python aegis-dashboard/backend/init_db.py
- A policy created for this agent via the Policies page (or via the API).
"""

import aegis


def issue_refund(order_id: str, amount_usd: float) -> dict:
    """Issue a refund."""
    return {"refund_id": "ref_123", "amount": amount_usd, "order_id": order_id}


def update_crm(customer_id: str, notes: str) -> dict:
    """Update CRM."""
    return {"success": True, "customer_id": customer_id}


DASHBOARD_URL = "http://localhost:8000"
API_KEY       = "ak_demo_key_123"   # replace with your real key from init_db
CUSTOMER_ID   = "acme-corp"
AGENT_ID      = "billing-agent"


def main():
    print("=== Aegis Dashboard Integration Example ===\n")

    # ── 1. Policy source: dashboard (PostgreSQL) ──────────────────────────────
    #
    # DashboardPolicyStore fetches the active policy for this agent from the
    # REST API.  Wrap it in a PolicyLoader with a 60-second TTL cache so that
    # every deploy / rollback in the dashboard is reflected within a minute
    # without restarting the agent process.
    #
    policy_store = aegis.DashboardPolicyStore(
        base_url=DASHBOARD_URL,
        api_key=API_KEY,
        agent_id=AGENT_ID,
    )
    policy_loader = aegis.PolicyLoader(store=policy_store, cache_ttl=60)
    active_policy = policy_loader.load(CUSTOMER_ID)

    print(f"Loaded policy v{active_policy.get('version', '?')} for {AGENT_ID}\n")

    # ── 2. Audit sink: dashboard (PostgreSQL) ─────────────────────────────────
    #
    # AegisDashboardSink batches audit records and POSTs them to
    # /api/v1/ingest/audit.  The dashboard Audit, Metrics, and Escalations
    # pages are fed entirely from these records.
    #
    dashboard_sink = aegis.AegisDashboardSink(
        api_key=API_KEY,
        base_url=DASHBOARD_URL,
        async_mode=True,
        batch_size=10,
        batch_timeout_ms=1000,
    )

    # Optional: also keep a local backup on disk.
    file_sink = aegis.FileSink(path="./audit/backup.jsonl")

    # ── 3. Wrap tools ─────────────────────────────────────────────────────────
    tools = aegis.wrap(
        tools=[issue_refund, update_crm],
        policy=active_policy,           # dict loaded from dashboard
        agent_id=AGENT_ID,
        customer_id=CUSTOMER_ID,
        audit_sink=[dashboard_sink, file_sink],
        on_deny="raise",
    )
    wrapped_refund, wrapped_crm = tools

    # ── 4. Run some calls ─────────────────────────────────────────────────────
    print("1. Small refund ($100) — expect: allowed")
    try:
        print(f"   OK  {wrapped_refund(order_id='ord_123', amount_usd=100)}\n")
    except aegis.AegisViolationError as e:
        print(f"   DENIED  {e}\n")

    print("2. CRM update — expect: allowed")
    try:
        print(f"   OK  {wrapped_crm(customer_id='cust_456', notes='Customer satisfied')}\n")
    except aegis.AegisViolationError as e:
        print(f"   DENIED  {e}\n")

    print("3. Large refund ($5 000) — expect: denied")
    try:
        print(f"   OK  {wrapped_refund(order_id='ord_789', amount_usd=5000)}\n")
    except aegis.AegisViolationError as e:
        print(f"   DENIED  {e}\n")

    # ── 5. Flush ──────────────────────────────────────────────────────────────
    print("Flushing audit records to dashboard…")
    dashboard_sink.flush()
    file_sink.close()

    print("\nDone! Open the dashboard to see live data:")
    print(f"  Audit    → {DASHBOARD_URL}  (Audit tab)")
    print(f"  Metrics  → {DASHBOARD_URL}  (Home tab)")
    print(f"  Policies → {DASHBOARD_URL}  (Policies tab — edit & redeploy live)")


if __name__ == "__main__":
    main()
