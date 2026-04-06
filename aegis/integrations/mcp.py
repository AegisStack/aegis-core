"""
MCP Server Integration

Decorator for MCP tool handlers with policy enforcement.
"""

import functools
from typing import Any, Callable, Dict, Optional, Union

from ..core.policy_engine import PolicyEngine
from ..core.wrapper import wrap
from ..exceptions import AegisViolationError


def mcp_enforce(
    policy: Union[str, Dict[str, Any], Callable],
    agent_id: str,
    customer_id: Optional[str] = None,
    on_deny: str = "raise",
    on_escalate: str = "block",
    **kwargs
):
    """
    Decorator for MCP tool call handlers.

    Wraps the handler with policy enforcement before the tool logic executes.

    Args:
        policy: Path to YAML policy file, inline dict, or callable that returns policy
        agent_id: Agent identifier
        customer_id: Customer identifier (or callable to extract from context)
        on_deny: How to handle denials ('raise', 'return_error', 'silent')
        on_escalate: How to handle escalations ('block', 'notify_and_proceed')
        **kwargs: Additional arguments for wrap()

    Returns:
        Decorated function

    Example:
        >>> from mcp.server import Server
        >>> import aegis
        >>>
        >>> server = Server('billing-agent')
        >>>
        >>> @server.call_tool()
        >>> @aegis.mcp_enforce(
        ...     policy=lambda ctx: aegis.load_customer_policy(ctx.customer_id),
        ...     agent_id='billing-agent'
        ... )
        >>> async def handle_tool_call(name: str, arguments: dict):
        ...     if name == 'issue_refund':
        ...         return await issue_refund(**arguments)
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(name: str, arguments: dict, context: Any = None):
            # Resolve policy if callable
            if callable(policy):
                resolved_policy = policy(context)
            else:
                resolved_policy = policy

            # Resolve customer_id if callable
            resolved_customer_id = customer_id
            if callable(customer_id) and context:
                resolved_customer_id = customer_id(context)

            # Create a temporary tool function for this specific call
            async def temp_tool(**args):
                return await func(name, args, context)

            # Set the name for policy evaluation
            temp_tool.__name__ = name

            # Wrap and execute
            wrapped_tools = wrap(
                tools=[temp_tool],
                policy=resolved_policy,
                agent_id=agent_id,
                customer_id=resolved_customer_id,
                on_deny=on_deny,
                on_escalate=on_escalate,
                **kwargs
            )

            wrapped_tool = wrapped_tools[0]

            # Execute with enforcement
            return await wrapped_tool(**arguments)

        return wrapper

    return decorator


def wrap_mcp_tools(
    tool_handlers: Dict[str, Callable],
    policy: Union[str, Dict[str, Any]],
    agent_id: str,
    **kwargs
) -> Dict[str, Callable]:
    """
    Wrap a dictionary of MCP tool handlers.

    Alternative to decorator for programmatic wrapping.

    Args:
        tool_handlers: Dictionary mapping tool names to handler functions
        policy: Path to YAML policy file or inline dict
        agent_id: Agent identifier
        **kwargs: Additional arguments for wrap()

    Returns:
        Dictionary with wrapped handlers

    Example:
        >>> handlers = {
        ...     'issue_refund': handle_refund,
        ...     'update_crm': handle_crm,
        ... }
        >>> wrapped = wrap_mcp_tools(
        ...     handlers,
        ...     policy='./policies/acme.yaml',
        ...     agent_id='billing-agent'
        ... )
    """
    from ..core.wrapper import wrap_function_map
    return wrap_function_map(tool_handlers, policy, agent_id, **kwargs)
