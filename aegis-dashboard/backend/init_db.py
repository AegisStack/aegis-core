"""
Seed the Aegis Dashboard database with realistic demo data.

Creates customers, users, policies (with version history), audit records,
and escalations (pending, approved, denied, expired) — all properly linked.

Usage
-----
From outside the container (DB exposed on 5433):
    cd aegis-dashboard/backend
    python init_db.py

From inside the backend container (uses internal DB URL):
    docker exec -it aegis-backend python init_db.py

The script is idempotent: it skips anything that already exists.
"""

import asyncio
import hashlib
import os
import random
import sys
import uuid
from datetime import datetime, timedelta

if sys.platform == "win32":
    os.system("chcp 65001 > nul")
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, ".")

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.audit import AuditRecord
from app.models.escalation import Escalation
from app.models.policy import Customer, Policy
from app.models.user import User
from app.services.auth import get_password_hash

# ── helpers ──────────────────────────────────────────────────────────────────

def _hash(yaml_text: str) -> str:
    return hashlib.sha256(yaml_text.encode()).hexdigest()


def _ago(**kwargs) -> datetime:
    return datetime.utcnow() - timedelta(**kwargs)


def _from_now(**kwargs) -> datetime:
    return datetime.utcnow() + timedelta(**kwargs)


# ── policy YAML templates ─────────────────────────────────────────────────────

POLICIES: dict[str, list[dict]] = {
    # list of {agent_id, versions: [{yaml, description}]}
    "acme-corp": [
        {
            "agent_id": "billing-agent",
            "versions": [
                {
                    "description": "Initial billing policy",
                    "yaml": """\
version: 1
agent_role: billing-agent
customer_id: acme-corp
policy_owner: sarah@acme.com

rules:
  - tool: issue_refund
    allow:
      - amount_usd: { lte: 100 }
    escalate:
      - amount_usd: { gt: 100, lte: 500 }
    deny:
      - amount_usd: { gt: 500 }

  - tool: send_email
    allow:
      - recipient_domain: { in: [acme.com] }
    deny:
      - recipient_domain: { not_in: [acme.com] }

defaults:
  unmatched_tool: deny
  unmatched_param: escalate
""",
                },
                {
                    "description": "Raise refund ceiling to $200, add trusted vendor domain",
                    "yaml": """\
version: 2
agent_role: billing-agent
customer_id: acme-corp
policy_owner: sarah@acme.com

rules:
  - tool: issue_refund
    allow:
      - amount_usd: { lte: 200 }
    escalate:
      - amount_usd: { gt: 200, lte: 2000 }
    deny:
      - amount_usd: { gt: 2000 }

  - tool: send_email
    allow:
      - recipient_domain: { in: [acme.com, trusted-vendor.com] }
    deny:
      - recipient_domain: { not_in: [acme.com, trusted-vendor.com] }

  - tool: update_crm
    allow: always

  - tool: deploy
    deny: always

defaults:
  unmatched_tool: deny
  unmatched_param: escalate

notifications:
  escalation_webhook: https://hooks.acme.com/aegis-escalations
  escalation_timeout_minutes: 30
""",
                },
            ],
        },
        {
            "agent_id": "support-agent",
            "versions": [
                {
                    "description": "Support agent initial policy",
                    "yaml": """\
version: 1
agent_role: support-agent
customer_id: acme-corp

rules:
  - tool: read_ticket
    allow: always

  - tool: close_ticket
    allow:
      - status: { in: [resolved, duplicate] }
    escalate:
      - status: { in: [pending] }

  - tool: delete_ticket
    deny: always

  - tool: send_email
    allow:
      - recipient_domain: { in: [acme.com] }
    deny:
      - recipient_domain: { not_in: [acme.com] }

defaults:
  unmatched_tool: escalate
  unmatched_param: deny
""",
                },
            ],
        },
        {
            "agent_id": "analytics-agent",
            "versions": [
                {
                    "description": "Read-only analytics policy",
                    "yaml": """\
version: 1
agent_role: analytics-agent
customer_id: acme-corp

rules:
  - tool: query_database
    allow:
      - query_type: { in: [SELECT] }
    deny:
      - query_type: { in: [INSERT, UPDATE, DELETE, DROP] }

  - tool: export_report
    allow:
      - format: { in: [csv, pdf, json] }
      - destination: { in: [internal] }
    escalate:
      - destination: { in: [external] }

  - tool: access_s3
    allow:
      - bucket: { in: [acme-reports, acme-logs] }
    deny:
      - bucket: { not_in: [acme-reports, acme-logs] }

defaults:
  unmatched_tool: deny
  unmatched_param: deny
""",
                },
            ],
        },
    ],
    "beta-corp": [
        {
            "agent_id": "ops-agent",
            "versions": [
                {
                    "description": "Ops agent policy v1",
                    "yaml": """\
version: 1
agent_role: ops-agent
customer_id: beta-corp

rules:
  - tool: restart_service
    allow:
      - environment: { in: [staging] }
    escalate:
      - environment: { in: [production] }

  - tool: execute_code
    deny: always

  - tool: read_file
    allow: always

  - tool: write_file
    escalate:
      - path: { startswith: /etc }
    allow:
      - path: { startswith: /tmp }

defaults:
  unmatched_tool: escalate
  unmatched_param: deny
""",
                },
            ],
        },
    ],
    "test_customer": [
        {
            "agent_id": "billing-agent",
            "versions": [
                {
                    "description": "Test billing policy",
                    "yaml": """\
version: 1
agent_role: billing-agent
customer_id: test_customer

rules:
  - tool: issue_refund
    allow:
      - amount_usd: { lte: 50 }
    deny:
      - amount_usd: { gt: 50 }

defaults:
  unmatched_tool: deny
  unmatched_param: deny
""",
                },
            ],
        },
    ],
}

# ── audit + escalation data tables ───────────────────────────────────────────

RULES_DENY = [
    "no_pii_in_email", "rate_limit_exceeded", "privileged_action",
    "outside_business_hours", "missing_approval", "data_exfiltration_risk",
    "amount_exceeds_limit", "restricted_bucket", "dangerous_query_type",
]

# Realistic agent -> (tool, outcome_weights, sample_params) mappings
AGENT_TOOLS: dict[str, list[dict]] = {
    "billing-agent": [
        {"tool": "issue_refund",  "weights": [75, 15, 10],
         "allow_params":   {"amount_usd": 50,   "customer_id": "cust_001"},
         "deny_params":    {"amount_usd": 750,  "customer_id": "cust_002"},
         "esc_params":     {"amount_usd": 350,  "customer_id": "cust_003"},
         "deny_rule": "amount_exceeds_limit", "esc_rule": "high_value_transaction"},
        {"tool": "send_email",    "weights": [80, 20,  0],
         "allow_params":   {"recipient": "user@acme.com",     "subject": "Invoice"},
         "deny_params":    {"recipient": "user@external.com", "subject": "Invoice"},
         "esc_params":     {},
         "deny_rule": "no_pii_in_email", "esc_rule": "external_email_recipient"},
        {"tool": "update_crm",    "weights": [90, 10,  0],
         "allow_params":   {"record_id": "CRM-123", "field": "phone"},
         "deny_params":    {"record_id": "CRM-999", "field": "salary"},
         "esc_params":     {},
         "deny_rule": "privileged_action", "esc_rule": "high_value_transaction"},
    ],
    "support-agent": [
        {"tool": "close_ticket",  "weights": [65, 15, 20],
         "allow_params":   {"ticket_id": "TKT-100", "status": "resolved"},
         "deny_params":    {"ticket_id": "TKT-200", "status": "deleted"},
         "esc_params":     {"ticket_id": "TKT-300", "status": "pending"},
         "deny_rule": "privileged_action", "esc_rule": "pending_ticket_close"},
        {"tool": "send_email",    "weights": [85, 15,  0],
         "allow_params":   {"recipient": "agent@acme.com",   "subject": "Update"},
         "deny_params":    {"recipient": "user@outlook.com", "subject": "Update"},
         "esc_params":     {},
         "deny_rule": "no_pii_in_email", "esc_rule": "external_email_recipient"},
        {"tool": "read_ticket",   "weights": [99,  1,  0],
         "allow_params":   {"ticket_id": "TKT-400"},
         "deny_params":    {"ticket_id": "TKT-401"},
         "esc_params":     {},
         "deny_rule": "rate_limit_exceeded", "esc_rule": "pending_ticket_close"},
        {"tool": "delete_ticket", "weights": [ 0, 100, 0],
         "allow_params":   {},
         "deny_params":    {"ticket_id": "TKT-500"},
         "esc_params":     {},
         "deny_rule": "privileged_action", "esc_rule": "pending_ticket_close"},
    ],
    "analytics-agent": [
        {"tool": "query_database","weights": [70, 25,  5],
         "allow_params":   {"query_type": "SELECT", "table": "orders"},
         "deny_params":    {"query_type": "DROP",   "table": "users"},
         "esc_params":     {"query_type": "SELECT", "table": "pii_data"},
         "deny_rule": "dangerous_query_type", "esc_rule": "data_exfiltration_risk"},
        {"tool": "export_report", "weights": [60, 10, 30],
         "allow_params":   {"format": "csv", "destination": "internal", "rows": 1000},
         "deny_params":    {"format": "csv", "destination": "external", "rows": 1000000},
         "esc_params":     {"format": "csv", "destination": "external", "rows": 50000},
         "deny_rule": "data_exfiltration_risk", "esc_rule": "external_destination"},
        {"tool": "access_s3",    "weights": [75, 25,  0],
         "allow_params":   {"bucket": "acme-reports", "key": "q3.csv"},
         "deny_params":    {"bucket": "acme-billing",  "key": "payroll.csv"},
         "esc_params":     {},
         "deny_rule": "restricted_bucket", "esc_rule": "data_exfiltration_risk"},
    ],
    "ops-agent": [
        {"tool": "restart_service","weights": [50, 10, 40],
         "allow_params":   {"service": "nginx",            "environment": "staging"},
         "deny_params":    {"service": "payment-processor","environment": "staging"},
         "esc_params":     {"service": "payment-processor","environment": "production"},
         "deny_rule": "missing_approval", "esc_rule": "production_environment"},
        {"tool": "read_file",    "weights": [99,  1,  0],
         "allow_params":   {"path": "/var/log/nginx.log"},
         "deny_params":    {"path": "/etc/shadow"},
         "esc_params":     {},
         "deny_rule": "privileged_action", "esc_rule": "production_environment"},
        {"tool": "write_file",   "weights": [60, 10, 30],
         "allow_params":   {"path": "/tmp/output.txt", "size_bytes": 512},
         "deny_params":    {"path": "/etc/cron.d/job", "size_bytes": 128},
         "esc_params":     {"path": "/etc/nginx/nginx.conf", "size_bytes": 4096},
         "deny_rule": "privileged_action", "esc_rule": "production_environment"},
        {"tool": "execute_code", "weights": [ 0, 100, 0],
         "allow_params":   {},
         "deny_params":    {"script": "rm -rf /tmp/*"},
         "esc_params":     {},
         "deny_rule": "privileged_action", "esc_rule": "production_environment"},
    ],
}

AGENTS = list(AGENT_TOOLS.keys())


# ── seed functions ────────────────────────────────────────────────────────────

async def seed_customer(session: AsyncSession, cfg: dict):
    existing = await session.execute(
        select(Customer).where(Customer.customer_id == cfg["customer_id"])
    )
    if existing.scalar_one_or_none():
        print(f"  ⚠️  {cfg['customer_id']} already exists — skipping")
        return

    session.add(Customer(
        customer_id=cfg["customer_id"],
        name=cfg["name"],
        api_key=cfg["api_key"],
    ))
    await session.flush()

    for email, full_name, role, password in cfg["users"]:
        session.add(User(
            email=email,
            full_name=full_name,
            hashed_password=get_password_hash(password),
            customer_id=cfg["customer_id"],
            role=role,
            is_active=True,
            is_verified=True,
        ))

    print(f"  ✅  {cfg['customer_id']} — {len(cfg['users'])} users")


async def seed_policies(session: AsyncSession, customer_id: str):
    agent_configs = POLICIES.get(customer_id, [])
    total = 0
    for agent_cfg in agent_configs:
        agent_id = agent_cfg["agent_id"]
        versions = agent_cfg["versions"]
        for i, v in enumerate(versions):
            is_active = (i == len(versions) - 1)  # only the last version is active
            session.add(Policy(
                customer_id=customer_id,
                agent_id=agent_id,
                policy_yaml=v["yaml"],
                policy_hash=_hash(v["yaml"]),
                version=i + 1,
                is_active=is_active,
                created_at=_ago(days=30 - i * 7),   # older versions further back
                created_by=f"admin@{customer_id}",
                description=v["description"],
            ))
            total += 1
    print(f"  ✅  {customer_id} — {total} policy versions across {len(agent_configs)} agents")


async def seed_audit_and_escalations(session: AsyncSession, customer_id: str, n_regular: int):
    """
    Seeds:
    - n_regular audit records with realistic agent/tool/outcome distributions.
      ~40% in the last 2 hours (for time-series charts), ~60% spread over last 7 days.
    - Escalation records distributed across statuses.
    """
    # ── regular records ───────────────────────────────────────────────────────
    # Weight timestamps: recent records are more likely so time-series charts have data
    def _random_ts() -> datetime:
        # 40% chance of being in the last 2 hours, 60% in the last 7 days
        if random.random() < 0.40:
            return _ago(hours=random.uniform(0, 2))
        return _ago(hours=random.uniform(2, 24 * 7))

    for _ in range(n_regular):
        agent_id = random.choice(AGENTS)
        tool_cfg = random.choice(AGENT_TOOLS[agent_id])
        outcome = random.choices(["allow", "deny", "escalate"], weights=tool_cfg["weights"])[0]
        if outcome == "allow":
            params = tool_cfg["allow_params"]
            matched_rule = "default-allow"
            reason = f"{tool_cfg['tool']} permitted by policy"
        elif outcome == "deny":
            params = tool_cfg["deny_params"]
            matched_rule = tool_cfg["deny_rule"]
            reason = f"{tool_cfg['tool']} denied: {matched_rule.replace('_', ' ')}"
        else:
            params = tool_cfg["esc_params"] or tool_cfg["allow_params"]
            matched_rule = tool_cfg["esc_rule"]
            reason = f"{tool_cfg['tool']} requires human review: {matched_rule.replace('_', ' ')}"

        session.add(AuditRecord(
            record_id=uuid.uuid4(),
            timestamp=_random_ts(),
            customer_id=customer_id,
            agent_id=agent_id,
            session_id=str(uuid.uuid4()),
            policy_version="2.0",
            tool_name=tool_cfg["tool"],
            params=params,
            outcome=outcome,
            matched_rule=matched_rule,
            reason=reason,
            latency_ms=round(random.gauss(18, 10), 2),
        ))

    # ── escalation scenarios ──────────────────────────────────────────────────
    # status distribution: some pending (fresh), some approved, some denied, some expired
    esc_statuses = [
        ("pending",  _ago(minutes=10),  _from_now(minutes=20),  None,          None),
        ("pending",  _ago(minutes=25),  _from_now(minutes=5),   None,          None),
        ("pending",  _ago(hours=1),     _from_now(hours=23),    None,          None),
        ("approved", _ago(hours=3),     _from_now(hours=21),    "operator@" + customer_id, _ago(hours=2)),
        ("approved", _ago(days=1),      _ago(hours=20),         "admin@" + customer_id,    _ago(days=1, hours=-2)),
        ("denied",   _ago(hours=5),     _from_now(hours=19),    "operator@" + customer_id, _ago(hours=4)),
        ("denied",   _ago(days=2),      _ago(days=2, hours=-24),"admin@" + customer_id,    _ago(days=2, hours=-1)),
        ("expired",  _ago(days=3),      _ago(days=2, hours=22), None,          None),
        ("expired",  _ago(days=5),      _ago(days=4, hours=20), None,          None),
    ]

    # Flatten all escalation-capable tools across agents for use in esc rows
    esc_scenarios_pool = [
        {"agent_id": agent_id, **tool_cfg}
        for agent_id, tools in AGENT_TOOLS.items()
        for tool_cfg in tools
        if tool_cfg["esc_params"]  # only tools that have escalation params
    ]

    for i, (status, created_at, expires_at, resolved_by, res_ts) in enumerate(esc_statuses):
        scenario = esc_scenarios_pool[i % len(esc_scenarios_pool)]
        record_id = uuid.uuid4()
        esc_id = f"esc-{customer_id}-{uuid.uuid4().hex[:12]}"
        agent_id = scenario["agent_id"]

        esc_params = scenario["esc_params"] or scenario["allow_params"]
        esc_reason = f"{scenario['tool']} requires human review: {scenario['esc_rule'].replace('_', ' ')}"

        # Audit record
        session.add(AuditRecord(
            record_id=record_id,
            timestamp=created_at,
            customer_id=customer_id,
            agent_id=agent_id,
            session_id=str(uuid.uuid4()),
            policy_version="2.0",
            tool_name=scenario["tool"],
            params=esc_params,
            outcome="escalate",
            matched_rule=scenario["esc_rule"],
            reason=esc_reason,
            escalation_id=esc_id,
            resolved_by=resolved_by,
            resolution=status if status in ("approved", "denied") else None,
            resolution_timestamp=res_ts,
            latency_ms=round(random.uniform(2.0, 50.0), 2),
        ))

        # Escalation row
        session.add(Escalation(
            escalation_id=esc_id,
            record_id=record_id,
            customer_id=customer_id,
            agent_id=agent_id,
            tool_name=scenario["tool"],
            params=esc_params,
            reason=esc_reason,
            status=status,
            resolved_by=resolved_by,
            resolution_timestamp=res_ts,
            created_at=created_at,
            expires_at=expires_at,
        ))

    pending = sum(1 for s, *_ in esc_statuses if s == "pending")
    print(
        f"  ✅  {customer_id} — {n_regular} allow/deny records + "
        f"{len(esc_statuses)} escalations ({pending} pending)"
    )


# ── customer definitions ──────────────────────────────────────────────────────

CUSTOMERS = [
    {
        "customer_id": "acme-corp",
        "name": "Acme Corporation",
        "api_key": "acme_api_key_abc123",
        "users": [
            ("admin@acme.com",    "Admin User",    "admin",    "acme_admin_pass"),
            ("operator@acme.com", "Operator User", "operator", "acme_op_pass"),
            ("viewer@acme.com",   "Viewer User",   "viewer",   "acme_view_pass"),
        ],
        "audit_records": 400,
    },
    {
        "customer_id": "beta-corp",
        "name": "Beta Industries",
        "api_key": "beta_api_key_xyz789",
        "users": [
            ("admin@beta.com",  "Beta Admin",  "admin",  "beta_admin_pass"),
            ("viewer@beta.com", "Beta Viewer", "viewer", "beta_view_pass"),
        ],
        "audit_records": 200,
    },
    {
        "customer_id": "test_customer",
        "name": "Test Company",
        "api_key": "test_api_key_12345",
        "users": [
            ("admin@test.com",    "Admin User",    "admin",    "admin123"),
            ("operator@test.com", "Operator User", "operator", "operator123"),
            ("viewer@test.com",   "Viewer User",   "viewer",   "viewer123"),
        ],
        "audit_records": 150,
    },
]


# ── entry point ───────────────────────────────────────────────────────────────

async def init_database():
    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://aegis:aegis@localhost:5433/aegis_dashboard",
    )
    print(f"🔌  Connecting to {db_url.split('@')[1]} ...\n")
    engine = create_async_engine(db_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        print("📊  Creating tables ...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        print("\n👤  Seeding customers & users ...")
        async with async_session() as session:
            for cfg in CUSTOMERS:
                await seed_customer(session, cfg)
            await session.commit()

        print("\n📋  Seeding policies ...")
        async with async_session() as session:
            for cfg in CUSTOMERS:
                await seed_policies(session, cfg["customer_id"])
            await session.commit()

        print("\n📝  Seeding audit records & escalations ...")
        async with async_session() as session:
            for cfg in CUSTOMERS:
                await seed_audit_and_escalations(
                    session, cfg["customer_id"], cfg["audit_records"]
                )
            await session.commit()

        print("\n✅  Done!\n")
        print("─" * 55)
        print("  Account summary")
        print("─" * 55)
        for cfg in CUSTOMERS:
            print(f"\n  [{cfg['customer_id']}]  API key: {cfg['api_key']}")
            for email, _, role, password in cfg["users"]:
                print(f"    {role:10s}  {email}  /  {password}")
        print("\n─" * 55)
        print("  🌐  Dashboard: http://localhost:3003")
        print("  📡  Backend:   http://localhost:8000")
        print("  📚  API Docs:  http://localhost:8000/docs\n")

    except Exception as e:
        print(f"\n❌  Error: {e}")
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    print("🚀  Aegis Dashboard — seed database\n")
    asyncio.run(init_database())
