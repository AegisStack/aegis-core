"""
Tool Wrapper - Main interception mechanism for aegis.wrap().

Wraps tool callables with policy enforcement while preserving function signatures.
"""

import time
import functools
from typing import Any, Callable, Dict, List, Optional, Union

from .policy_engine import PolicyEngine, Outcome
from .policy_loader import load_customer_policy, PolicyLoader
from .escalation import EscalationManager
from ..audit.schema import create_audit_record
from ..audit.writer import AuditWriter
from ..exceptions import AegisViolationError, AegisPolicyLoadError, AegisConfigError


class ToolWrapper:
    """Wraps a single tool callable with policy enforcement."""

    def __init__(
        self,
        tool: Callable,
        policy_engine: PolicyEngine,
        agent_id: str,
        customer_id: Optional[str],
        session_id: Optional[str],
        on_deny: str,
        escalation_manager: Optional[EscalationManager],
        audit_writer: Optional[AuditWriter],
    ):
        """
        Initialize tool wrapper.

        Args:
            tool: Original tool callable
            policy_engine: PolicyEngine instance
            agent_id: Agent identifier
            customer_id: Customer identifier
            session_id: Session identifier
            on_deny: How to handle denials ('raise', 'return_error', 'silent')
            escalation_manager: EscalationManager instance
            audit_writer: AuditWriter instance
        """
        self.tool = tool
        self.policy_engine = policy_engine
        self.agent_id = agent_id
        self.customer_id = customer_id
        self.session_id = session_id
        self.on_deny = on_deny
        self.escalation_manager = escalation_manager
        self.audit_writer = audit_writer

        # Preserve original function metadata
        functools.update_wrapper(self, tool)

    def __call__(self, *args, **kwargs) -> Any:
        """
        Execute tool with policy enforcement.

        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Tool execution result if allowed

        Raises:
            AegisViolationError: If denied and on_deny='raise'
        """
        # Get tool name
        tool_name = getattr(self.tool, "__name__", str(self.tool))

        # Convert args to kwargs using function signature if possible
        params = kwargs.copy()
        if args:
            # Try to get parameter names from function signature
            try:
                import inspect
                sig = inspect.signature(self.tool)
                param_names = list(sig.parameters.keys())
                for i, arg in enumerate(args):
                    if i < len(param_names):
                        params[param_names[i]] = arg
            except Exception:
                # If signature inspection fails, use positional args
                for i, arg in enumerate(args):
                    params[f"arg{i}"] = arg

        # Start timing
        start_time = time.time()

        # Evaluate policy
        decision = self.policy_engine.evaluate(tool_name, params)
        latency_ms = (time.time() - start_time) * 1000

        # Handle DENY outcome
        if decision.outcome == Outcome.DENY:
            audit_record = create_audit_record(
                agent_id=self.agent_id,
                customer_id=self.customer_id,
                session_id=self.session_id,
                policy_version=decision.policy_version,
                tool_name=tool_name,
                params=params,
                outcome="deny",
                matched_rule=decision.matched_rule,
                reason=decision.reason,
                latency_ms=latency_ms,
            )

            if self.audit_writer:
                self.audit_writer.write(audit_record)

            if self.on_deny == "raise":
                raise AegisViolationError(tool_name, decision.reason, decision.matched_rule)
            elif self.on_deny == "return_error":
                return f"AEGIS_DENIED: {decision.reason}"
            else:  # silent
                return None

        # Handle ESCALATE outcome
        if decision.outcome == Outcome.ESCALATE:
            audit_record = create_audit_record(
                agent_id=self.agent_id,
                customer_id=self.customer_id,
                session_id=self.session_id,
                policy_version=decision.policy_version,
                tool_name=tool_name,
                params=params,
                outcome="escalate",
                matched_rule=decision.matched_rule,
                reason=decision.reason,
                latency_ms=latency_ms,
            )

            if self.audit_writer:
                self.audit_writer.write(audit_record)

            if self.escalation_manager:
                escalation = self.escalation_manager.escalate(
                    record_id=audit_record.record_id,
                    customer_id=self.customer_id,
                    agent_id=self.agent_id,
                    tool_name=tool_name,
                    params=params,
                    reason=decision.reason,
                )

                # Update audit record with escalation info
                audit_record.escalation_id = escalation.escalation_id

                # If blocking, wait for resolution
                if self.escalation_manager.on_escalate == "block":
                    if escalation.resolution == "denied":
                        # Escalation was denied by human
                        if self.on_deny == "raise":
                            raise AegisViolationError(
                                tool_name,
                                f"Escalation denied by {escalation.resolved_by}",
                                decision.matched_rule,
                            )
                        elif self.on_deny == "return_error":
                            return f"AEGIS_DENIED: Escalation denied by {escalation.resolved_by}"
                        else:
                            return None
                    # Otherwise, escalation was approved - continue to execution

        # Handle ALLOW outcome - execute the tool
        try:
            result = self.tool(*args, **kwargs)
            execution_error = None
        except Exception as e:
            result = None
            execution_error = str(e)
            # Re-raise the exception
            raise
        finally:
            # Write audit record with execution result
            execution_time = (time.time() - start_time) * 1000
            audit_record = create_audit_record(
                agent_id=self.agent_id,
                customer_id=self.customer_id,
                session_id=self.session_id,
                policy_version=decision.policy_version,
                tool_name=tool_name,
                params=params,
                outcome="allow",
                matched_rule=decision.matched_rule,
                reason=decision.reason,
                execution_result=result if not execution_error else None,
                execution_error=execution_error,
                latency_ms=execution_time,
            )

            if self.audit_writer:
                self.audit_writer.write(audit_record)

        return result


def wrap(
    tools: List[Callable],
    policy: Union[str, Dict[str, Any]],
    agent_id: str,
    customer_id: Optional[str] = None,
    session_id: Optional[str] = None,
    on_deny: str = "raise",
    on_escalate: str = "block",
    audit_sink = None,
    obs_sink = None,
    escalation_webhook: Optional[str] = None,
    escalation_timeout_minutes: int = 30,
) -> List[Callable]:
    """
    Wrap tool callables with policy enforcement.

    This is the primary integration point for Aegis SDK.

    Args:
        tools: List of tool callables to wrap
        policy: Path to YAML policy file or inline dict
        agent_id: Agent identifier (scopes audit trail)
        customer_id: Customer identifier (for multi-tenant)
        session_id: Session identifier
        on_deny: How to handle denials ('raise', 'return_error', 'silent')
        on_escalate: How to handle escalations ('block', 'notify_and_proceed')
        audit_sink: Where to write audit records (AuditSink instance)
        obs_sink: Where to forward observability events (ObsSink instance)
        escalation_webhook: Webhook URL for escalation notifications
        escalation_timeout_minutes: Timeout for escalation resolution

    Returns:
        List of wrapped callables with identical interfaces

    Raises:
        AegisConfigError: If configuration is invalid
        AegisPolicyLoadError: If policy cannot be loaded

    Example:
        >>> wrapped_tools = wrap(
        ...     tools=[issue_refund, update_crm],
        ...     policy="./policies/acme-billing.yaml",
        ...     agent_id="billing-agent",
        ...     customer_id="acme-corp"
        ... )
    """
    # Validate configuration
    if not agent_id:
        raise AegisConfigError("agent_id is required")

    if on_deny not in ("raise", "return_error", "silent"):
        raise AegisConfigError(f"Invalid on_deny value: {on_deny}")

    if on_escalate not in ("block", "notify_and_proceed"):
        raise AegisConfigError(f"Invalid on_escalate value: {on_escalate}")

    # Load policy
    if isinstance(policy, str):
        # Path to YAML file
        import yaml
        from pathlib import Path
        policy_path = Path(policy)
        if not policy_path.exists():
            raise AegisPolicyLoadError(f"Policy file not found", str(policy_path))

        with open(policy_path, "r") as f:
            policy_dict = yaml.safe_load(f)
    elif isinstance(policy, dict):
        policy_dict = policy
    else:
        raise AegisConfigError("policy must be a file path string or dictionary")

    # Create policy engine
    policy_engine = PolicyEngine(policy_dict)

    # Create escalation manager
    escalation_manager = None
    if on_escalate or escalation_webhook:
        escalation_manager = EscalationManager(
            webhook_url=escalation_webhook,
            timeout_minutes=escalation_timeout_minutes,
            on_escalate=on_escalate,
        )

    # Create audit writer
    audit_writer = None
    if audit_sink:
        from ..audit.writer import AuditWriter
        if isinstance(audit_sink, list):
            audit_writer = AuditWriter(sinks=audit_sink)
        else:
            audit_writer = AuditWriter(sinks=[audit_sink])

    # Wrap each tool
    wrapped = []
    for tool in tools:
        wrapper = ToolWrapper(
            tool=tool,
            policy_engine=policy_engine,
            agent_id=agent_id,
            customer_id=customer_id,
            session_id=session_id,
            on_deny=on_deny,
            escalation_manager=escalation_manager,
            audit_writer=audit_writer,
        )
        wrapped.append(wrapper)

    return wrapped


def wrap_function_map(
    function_map: Dict[str, Callable],
    policy: Union[str, Dict[str, Any]],
    agent_id: str,
    customer_id: Optional[str] = None,
    **kwargs
) -> Dict[str, Callable]:
    """
    Wrap a dictionary of functions (for raw OpenAI function calling).

    Args:
        function_map: Dictionary mapping function names to callables
        policy: Path to YAML policy file or inline dict
        agent_id: Agent identifier
        customer_id: Customer identifier
        **kwargs: Additional arguments passed to wrap()

    Returns:
        Dictionary with same keys but wrapped callables

    Example:
        >>> function_map = {
        ...     'issue_refund': issue_refund,
        ...     'update_crm': update_crm,
        ... }
        >>> wrapped = wrap_function_map(
        ...     function_map,
        ...     policy="./policies/acme.yaml",
        ...     agent_id="billing-agent"
        ... )
    """
    tools = list(function_map.values())
    wrapped_tools = wrap(
        tools=tools,
        policy=policy,
        agent_id=agent_id,
        customer_id=customer_id,
        **kwargs
    )

    # Rebuild dictionary
    wrapped_map = {}
    for (name, _), wrapped_tool in zip(function_map.items(), wrapped_tools):
        wrapped_map[name] = wrapped_tool

    return wrapped_map
