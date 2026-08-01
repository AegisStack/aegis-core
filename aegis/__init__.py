"""
Aegis SDK - Policy Enforcement and Observability for Agent Builders

Main public API surface.
"""

__version__ = "0.1.0"

# Core functionality
# Audit trail
from .audit import AuditRecord, AuditWriter, create_audit_record
from .core import (
    DashboardPolicyStore,
    EscalationManager,
    EscalationRequest,
    FilesystemPolicyStore,
    GCSPolicyStore,
    Outcome,
    PolicyDecision,
    PolicyEngine,
    PolicyLoader,
    S3PolicyStore,
    load_customer_policy,
    register_policy_store,
    wrap,
    wrap_function_map,
)

# Exceptions
from .exceptions import (
    AegisAmbiguityError,
    AegisConfigError,
    AegisError,
    AegisEscalationTimeout,
    AegisPolicyLoadError,
    AegisViolationError,
)

# Integrations
from .integrations import mcp_enforce, wrap_langchain_tools, wrap_mcp_tools

# Observability
from .obs import (
    ConsoleSink,
    EscalationCreatedEvent,
    EscalationResolvedEvent,
    ObservabilityEvent,
    ObsSink,
    ObsWriter,
    PolicyLoadedEvent,
    PrometheusSink,
    SessionSummaryEvent,
    ToolEvaluatedEvent,
)

# Sinks
from .sinks import AegisDashboardSink, AuditSink, FileSink, WebhookSink

__all__ = [
    "AegisAmbiguityError",
    "AegisConfigError",
    "AegisDashboardSink",
    # Exceptions
    "AegisError",
    "AegisEscalationTimeout",
    "AegisPolicyLoadError",
    "AegisViolationError",
    # Audit
    "AuditRecord",
    # Sinks
    "AuditSink",
    "AuditWriter",
    "ConsoleSink",
    "DashboardPolicyStore",
    "EscalationCreatedEvent",
    "EscalationManager",
    "EscalationRequest",
    "EscalationResolvedEvent",
    "FileSink",
    "FilesystemPolicyStore",
    "GCSPolicyStore",
    "ObsSink",
    "ObsWriter",
    # Observability
    "ObservabilityEvent",
    "Outcome",
    "PolicyDecision",
    "PolicyEngine",
    "PolicyLoadedEvent",
    "PolicyLoader",
    "PrometheusSink",
    "S3PolicyStore",
    "SessionSummaryEvent",
    "ToolEvaluatedEvent",
    "WebhookSink",
    # Version
    "__version__",
    "create_audit_record",
    "load_customer_policy",
    # Integrations
    "mcp_enforce",
    "register_policy_store",
    # Core
    "wrap",
    "wrap_function_map",
    "wrap_langchain_tools",
    "wrap_mcp_tools",
]
