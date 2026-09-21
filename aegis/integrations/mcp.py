"""
MCP Server Integration

Decorator for MCP tool handlers with policy enforcement.
"""

from __future__ import annotations

import asyncio
import functools
from typing import Any, Callable, Optional, Union

from ..core.wrapper import ToolWrapper, wrap


def mcp_enforce(
    policy: Union[str, dict[str, Any], Callable],
    agent_id: str,
    customer_id: Optional[str] = None,
    on_deny: str = "raise",
    on_escalate: str = "block",
    **kwargs: Any,
) -> Callable:
    """
    Decorator for MCP tool call handlers.

    Wraps the handler with policy enforcement before the tool logic executes.
    The policy is loaded once at decoration time (or per-call if a callable is
    provided for dynamic customer policies).

    Args:
        policy: Path to YAML policy file, inline dict, or callable that returns
                policy (called with context on each invocation)
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
    # Cache a ToolWrapper for static policies so policy/engine/manager are not
    # re-created on every call. Dynamic (callable) policies still resolve per call.
    _static_wrapper: Optional[ToolWrapper] = None
    if not callable(policy) and not callable(customer_id):
        _wrapped: list[ToolWrapper] = wrap(  # type: ignore[assignment]
            tools=[lambda **_: None],  # placeholder; replaced per-call below
            policy=policy,
            agent_id=agent_id,
            customer_id=customer_id,
            on_deny=on_deny,
            on_escalate=on_escalate,
            **kwargs,
        )
        _static_wrapper = _wrapped[0]

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(name: str, arguments: dict, context: Any = None) -> Any:
            # Resolve dynamic policy/customer_id
            if callable(policy):
                resolved_policy = policy(context)
            else:
                resolved_policy = policy

            resolved_customer_id = customer_id(context) if callable(customer_id) else customer_id

            # Build a sync shim so ToolWrapper (which calls tools synchronously)
            # can invoke the async MCP handler correctly.
            def sync_shim(**args: Any) -> Any:
                coro = func(name, args, context)
                return asyncio.get_event_loop().run_until_complete(coro)

            sync_shim.__name__ = name

            tool_wrapper: ToolWrapper
            if _static_wrapper is not None:
                # Re-use the cached wrapper; swap out the underlying tool shim.
                _static_wrapper.tool = sync_shim  # type: ignore[attr-defined]
                tool_wrapper = _static_wrapper
            else:
                _dyn_wrapped: list[ToolWrapper] = wrap(  # type: ignore[assignment]
                    tools=[sync_shim],
                    policy=resolved_policy,
                    agent_id=agent_id,
                    customer_id=resolved_customer_id,
                    on_deny=on_deny,
                    on_escalate=on_escalate,
                    **kwargs,
                )
                tool_wrapper = _dyn_wrapped[0]

            # Run the synchronous ToolWrapper in a thread pool to avoid blocking
            # the event loop (ToolWrapper.__call__ is sync).
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, lambda: tool_wrapper(**arguments))

        return wrapper

    return decorator


def wrap_mcp_tools(
    tool_handlers: dict[str, Callable],
    policy: Union[str, dict[str, Any]],
    agent_id: str,
    **kwargs: Any,
) -> dict[str, Callable]:
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
