"""
Tests for tool wrapping and enforcement.
"""

import pytest
from aegis import wrap, wrap_function_map, AegisViolationError


def simple_tool(value: int) -> int:
    """A simple test tool."""
    return value * 2


def issue_refund(order_id: str, amount_usd: float) -> dict:
    """Issue a refund."""
    return {"refund_id": "ref_123", "amount": amount_usd}


class TestToolWrapper:
    """Test aegis.wrap() functionality."""

    def test_wrap_preserves_function_signature(self):
        policy = {
            "version": 1,
            "rules": [{"tool": "simple_tool", "allow": "always"}]
        }

        wrapped = wrap([simple_tool], policy=policy, agent_id="test-agent")
        wrapped_func = wrapped[0]

        # Check metadata preserved
        assert wrapped_func.__name__ == "simple_tool"
        assert "simple test tool" in wrapped_func.__doc__.lower()

    def test_wrap_allows_execution(self):
        policy = {
            "version": 1,
            "rules": [{"tool": "simple_tool", "allow": "always"}]
        }

        wrapped = wrap([simple_tool], policy=policy, agent_id="test-agent")
        result = wrapped[0](value=10)
        assert result == 20

    def test_wrap_denies_with_raise(self):
        policy = {
            "version": 1,
            "rules": [{"tool": "simple_tool", "deny": "always"}]
        }

        wrapped = wrap(
            [simple_tool],
            policy=policy,
            agent_id="test-agent",
            on_deny="raise"
        )

        with pytest.raises(AegisViolationError) as exc_info:
            wrapped[0](value=10)

        assert "simple_tool" in str(exc_info.value)

    def test_wrap_denies_with_return_error(self):
        policy = {
            "version": 1,
            "rules": [{"tool": "simple_tool", "deny": "always"}]
        }

        wrapped = wrap(
            [simple_tool],
            policy=policy,
            agent_id="test-agent",
            on_deny="return_error"
        )

        result = wrapped[0](value=10)
        assert result.startswith("AEGIS_DENIED:")

    def test_wrap_denies_with_silent(self):
        policy = {
            "version": 1,
            "rules": [{"tool": "simple_tool", "deny": "always"}]
        }

        wrapped = wrap(
            [simple_tool],
            policy=policy,
            agent_id="test-agent",
            on_deny="silent"
        )

        result = wrapped[0](value=10)
        assert result is None

    def test_wrap_conditional_policy(self):
        policy = {
            "version": 1,
            "rules": [
                {
                    "tool": "issue_refund",
                    "allow": [{"amount_usd": {"lte": 200}}],
                    "deny": [{"amount_usd": {"gt": 200}}]
                }
            ]
        }

        wrapped = wrap(
            [issue_refund],
            policy=policy,
            agent_id="test-agent",
            on_deny="raise"
        )

        # Small refund - allowed
        result = wrapped[0](order_id="ord_123", amount_usd=100)
        assert result["amount"] == 100

        # Large refund - denied
        with pytest.raises(AegisViolationError):
            wrapped[0](order_id="ord_123", amount_usd=500)

    def test_wrap_multiple_tools(self):
        def tool_a(x: int) -> int:
            return x + 1

        def tool_b(x: int) -> int:
            return x * 2

        policy = {
            "version": 1,
            "rules": [
                {"tool": "tool_a", "allow": "always"},
                {"tool": "tool_b", "deny": "always"}
            ]
        }

        wrapped = wrap([tool_a, tool_b], policy=policy, agent_id="test-agent")

        # tool_a should work
        assert wrapped[0](x=5) == 6

        # tool_b should be denied
        with pytest.raises(AegisViolationError):
            wrapped[1](x=5)

    def test_wrap_function_map(self):
        def tool_a(x: int) -> int:
            return x + 1

        def tool_b(x: int) -> int:
            return x * 2

        function_map = {
            "tool_a": tool_a,
            "tool_b": tool_b
        }

        policy = {
            "version": 1,
            "rules": [
                {"tool": "tool_a", "allow": "always"},
                {"tool": "tool_b", "deny": "always"}
            ]
        }

        wrapped = wrap_function_map(
            function_map,
            policy=policy,
            agent_id="test-agent"
        )

        assert "tool_a" in wrapped
        assert "tool_b" in wrapped
        assert wrapped["tool_a"](x=5) == 6

        with pytest.raises(AegisViolationError):
            wrapped["tool_b"](x=5)
