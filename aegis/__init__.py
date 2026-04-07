"""
Aegis SDK - Policy Enforcement and Observability for Agent Builders

Main public API surface.
"""

__version__ = "0.1.0"

# Core functionality
from .core import (
    wrap,
    wrap_function_map,
    PolicyEngine,
    PolicyDecision,
    Outcome,
    PolicyLoader,
    FilesystemPolicyStore,
    S3PolicyStore,
    GCSPolicyStore,
    register_policy_store,
    load_customer_policy,
    EscalationManager,
    EscalationRequest,
)

# Exceptions
from .exceptions import (
    AegisError,
    AegisViolationError,
    AegisPolicyLoadError,
    AegisEscalationTimeout,
    AegisAmbiguityError,
    AegisConfigError,
)

# Audit trail
from .audit import AuditRecord, create_audit_record, AuditWriter

# Sinks
from .sinks import AuditSink, FileSink, WebhookSink, AegisDashboardSink

# Observability
from .obs import (
    ObservabilityEvent,
    ToolEvaluatedEvent,
    EscalationCreatedEvent,
    EscalationResolvedEvent,
    PolicyLoadedEvent,
    SessionSummaryEvent,
    ObsSink,
    ConsoleSink,
    PrometheusSink,
    ObsWriter,
)

# Integrations
from .integrations import mcp_enforce, wrap_mcp_tools, wrap_langchain_tools

__all__ = [
    # Version
    "__version__",
    # Core
    "wrap",
    "wrap_function_map",
    "PolicyEngine",
    "PolicyDecision",
    "Outcome",
    "PolicyLoader",
    "FilesystemPolicyStore",
    "S3PolicyStore",
    "GCSPolicyStore",
    "register_policy_store",
    "load_customer_policy",
    "EscalationManager",
    "EscalationRequest",
    # Exceptions
    "AegisError",
    "AegisViolationError",
    "AegisPolicyLoadError",
    "AegisEscalationTimeout",
    "AegisAmbiguityError",
    "AegisConfigError",
    # Audit
    "AuditRecord",
    "create_audit_record",
    "AuditWriter",
    # Sinks
    "AuditSink",
    "FileSink",
    "WebhookSink",
    "AegisDashboardSink",
    # Observability
    "ObservabilityEvent",
    "ToolEvaluatedEvent",
    "EscalationCreatedEvent",
    "EscalationResolvedEvent",
    "PolicyLoadedEvent",
    "SessionSummaryEvent",
    "ObsSink",
    "ConsoleSink",
    "PrometheusSink",
    "ObsWriter",
    # Integrations
    "mcp_enforce",
    "wrap_mcp_tools",
    "wrap_langchain_tools",
]
