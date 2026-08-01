"""
LangChain Integration

Wraps LangChain tools with policy enforcement.
"""

from __future__ import annotations

from typing import Any, Optional, Union

from ..core.wrapper import wrap


def wrap_langchain_tools(
    tools: list[Any],
    policy: Union[str, dict[str, Any]],
    agent_id: str,
    customer_id: Optional[str] = None,
    **kwargs,
) -> list[Any]:
    """
    Wrap LangChain Tool objects with policy enforcement.

    Args:
        tools: List of LangChain Tool objects
        policy: Path to YAML policy file or inline dict
        agent_id: Agent identifier
        customer_id: Customer identifier
        **kwargs: Additional arguments for wrap()

    Returns:
        List of LangChain Tools with wrapped func callables

    Example:
        >>> from langchain.tools import Tool
        >>> import aegis
        >>>
        >>> raw_tools = [
        ...     Tool(name='issue_refund', func=issue_refund, description='...'),
        ...     Tool(name='update_crm', func=update_crm, description='...'),
        ... ]
        >>>
        >>> tools = aegis.wrap_langchain_tools(
        ...     raw_tools,
        ...     policy='./policies/acme.yaml',
        ...     agent_id='billing-agent',
        ...     customer_id='acme-corp'
        ... )
    """
    # Extract the func callables
    funcs = [tool.func for tool in tools]

    # Wrap them
    wrapped_funcs = wrap(
        tools=funcs, policy=policy, agent_id=agent_id, customer_id=customer_id, **kwargs
    )

    # Create new Tool objects with wrapped funcs
    # We preserve the original Tool object but replace its func
    wrapped_tools = []
    for tool, wrapped_func in zip(tools, wrapped_funcs):
        # LangChain Tool objects are typically immutable, so we need to create new ones
        try:
            # Try to import LangChain Tool
            from langchain.tools import Tool

            wrapped_tool = Tool(
                name=tool.name,
                func=wrapped_func,
                description=tool.description,
                # Preserve other attributes if they exist
                return_direct=getattr(tool, "return_direct", False),
                verbose=getattr(tool, "verbose", False),
            )
            wrapped_tools.append(wrapped_tool)
        except ImportError:
            # If LangChain not available, just return wrapped funcs
            # This allows testing without LangChain installed
            wrapped_tools.append(wrapped_func)

    return wrapped_tools
