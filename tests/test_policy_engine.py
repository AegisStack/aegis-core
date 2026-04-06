"""
Tests for PolicyEngine core evaluation logic.
"""

import pytest
from aegis.core.policy_engine import PolicyEngine, Outcome, ConditionEvaluator


class TestConditionEvaluator:
    """Test condition evaluation operators."""

    def test_eq_operator(self):
        assert ConditionEvaluator.evaluate("draft", {"eq": "draft"}) is True
        assert ConditionEvaluator.evaluate("published", {"eq": "draft"}) is False

    def test_neq_operator(self):
        assert ConditionEvaluator.evaluate("published", {"neq": "draft"}) is True
        assert ConditionEvaluator.evaluate("draft", {"neq": "draft"}) is False

    def test_lt_operator(self):
        assert ConditionEvaluator.evaluate(50, {"lt": 100}) is True
        assert ConditionEvaluator.evaluate(100, {"lt": 100}) is False
        assert ConditionEvaluator.evaluate(150, {"lt": 100}) is False

    def test_lte_operator(self):
        assert ConditionEvaluator.evaluate(50, {"lte": 100}) is True
        assert ConditionEvaluator.evaluate(100, {"lte": 100}) is True
        assert ConditionEvaluator.evaluate(150, {"lte": 100}) is False

    def test_gt_operator(self):
        assert ConditionEvaluator.evaluate(150, {"gt": 100}) is True
        assert ConditionEvaluator.evaluate(100, {"gt": 100}) is False
        assert ConditionEvaluator.evaluate(50, {"gt": 100}) is False

    def test_gte_operator(self):
        assert ConditionEvaluator.evaluate(150, {"gte": 100}) is True
        assert ConditionEvaluator.evaluate(100, {"gte": 100}) is True
        assert ConditionEvaluator.evaluate(50, {"gte": 100}) is False

    def test_in_operator(self):
        assert ConditionEvaluator.evaluate("acme.com", {"in": ["acme.com", "trusted.com"]}) is True
        assert ConditionEvaluator.evaluate("evil.com", {"in": ["acme.com", "trusted.com"]}) is False

    def test_not_in_operator(self):
        assert ConditionEvaluator.evaluate("evil.com", {"not_in": ["acme.com", "trusted.com"]}) is True
        assert ConditionEvaluator.evaluate("acme.com", {"not_in": ["acme.com", "trusted.com"]}) is False

    def test_regex_operator(self):
        assert ConditionEvaluator.evaluate("/tmp/file.txt", {"regex": r"^/tmp/"}) is True
        assert ConditionEvaluator.evaluate("/home/file.txt", {"regex": r"^/tmp/"}) is False
        assert ConditionEvaluator.evaluate(123, {"regex": r"^/tmp/"}) is False  # Non-string

    def test_multiple_conditions_and_logic(self):
        # Multiple operators in one condition - all must match (AND)
        assert ConditionEvaluator.evaluate(150, {"gt": 100, "lt": 200}) is True
        assert ConditionEvaluator.evaluate(50, {"gt": 100, "lt": 200}) is False
        assert ConditionEvaluator.evaluate(250, {"gt": 100, "lt": 200}) is False


class TestPolicyEngine:
    """Test policy engine evaluation."""

    def test_allow_always(self):
        policy = {
            "version": 1,
            "rules": [
                {"tool": "safe_tool", "allow": "always"}
            ]
        }
        engine = PolicyEngine(policy)
        decision = engine.evaluate("safe_tool", {})
        assert decision.outcome == Outcome.ALLOW

    def test_deny_always(self):
        policy = {
            "version": 1,
            "rules": [
                {"tool": "dangerous_tool", "deny": "always"}
            ]
        }
        engine = PolicyEngine(policy)
        decision = engine.evaluate("dangerous_tool", {})
        assert decision.outcome == Outcome.DENY

    def test_escalate_always(self):
        policy = {
            "version": 1,
            "rules": [
                {"tool": "sensitive_tool", "escalate": "always"}
            ]
        }
        engine = PolicyEngine(policy)
        decision = engine.evaluate("sensitive_tool", {})
        assert decision.outcome == Outcome.ESCALATE

    def test_conditional_allow(self):
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
        engine = PolicyEngine(policy)

        # Should allow small refund
        decision = engine.evaluate("issue_refund", {"amount_usd": 100})
        assert decision.outcome == Outcome.ALLOW

        # Should deny large refund
        decision = engine.evaluate("issue_refund", {"amount_usd": 500})
        assert decision.outcome == Outcome.DENY

    def test_conditional_escalate(self):
        policy = {
            "version": 1,
            "rules": [
                {
                    "tool": "issue_refund",
                    "allow": [{"amount_usd": {"lte": 200}}],
                    "escalate": [{"amount_usd": {"gt": 200, "lte": 2000}}],
                    "deny": [{"amount_usd": {"gt": 2000}}]
                }
            ]
        }
        engine = PolicyEngine(policy)

        decision = engine.evaluate("issue_refund", {"amount_usd": 100})
        assert decision.outcome == Outcome.ALLOW

        decision = engine.evaluate("issue_refund", {"amount_usd": 500})
        assert decision.outcome == Outcome.ESCALATE

        decision = engine.evaluate("issue_refund", {"amount_usd": 5000})
        assert decision.outcome == Outcome.DENY

    def test_evaluation_order_deny_first(self):
        """Deny conditions are checked before escalate and allow."""
        policy = {
            "version": 1,
            "rules": [
                {
                    "tool": "test_tool",
                    "deny": [{"value": {"gt": 1000}}],
                    "escalate": [{"value": {"gt": 500}}],
                    "allow": [{"value": {"gt": 0}}]
                }
            ]
        }
        engine = PolicyEngine(policy)

        # Value 2000 matches all three, but deny should win
        decision = engine.evaluate("test_tool", {"value": 2000})
        assert decision.outcome == Outcome.DENY

    def test_evaluation_order_escalate_before_allow(self):
        """Escalate conditions checked before allow."""
        policy = {
            "version": 1,
            "rules": [
                {
                    "tool": "test_tool",
                    "escalate": [{"value": {"gt": 500}}],
                    "allow": [{"value": {"gt": 0}}]
                }
            ]
        }
        engine = PolicyEngine(policy)

        # Value 800 matches both, escalate should win
        decision = engine.evaluate("test_tool", {"value": 800})
        assert decision.outcome == Outcome.ESCALATE

    def test_unmatched_tool_default_deny(self):
        policy = {
            "version": 1,
            "rules": [],
            "defaults": {"unmatched_tool": "deny"}
        }
        engine = PolicyEngine(policy)
        decision = engine.evaluate("unknown_tool", {})
        assert decision.outcome == Outcome.DENY

    def test_unmatched_tool_default_escalate(self):
        policy = {
            "version": 1,
            "rules": [],
            "defaults": {"unmatched_tool": "escalate"}
        }
        engine = PolicyEngine(policy)
        decision = engine.evaluate("unknown_tool", {})
        assert decision.outcome == Outcome.ESCALATE

    def test_unmatched_param_default_deny(self):
        policy = {
            "version": 1,
            "rules": [
                {
                    "tool": "test_tool",
                    "allow": [{"known_param": {"eq": "value"}}]
                }
            ],
            "defaults": {"unmatched_param": "deny"}
        }
        engine = PolicyEngine(policy)

        # Params don't match any allow condition
        decision = engine.evaluate("test_tool", {"known_param": "other_value"})
        assert decision.outcome == Outcome.DENY

    def test_unmatched_param_default_escalate(self):
        policy = {
            "version": 1,
            "rules": [
                {
                    "tool": "test_tool",
                    "allow": [{"known_param": {"eq": "value"}}]
                }
            ],
            "defaults": {"unmatched_param": "escalate"}
        }
        engine = PolicyEngine(policy)

        decision = engine.evaluate("test_tool", {"known_param": "other_value"})
        assert decision.outcome == Outcome.ESCALATE

    def test_multiple_params_and_logic(self):
        """Multiple params in one condition require all to match."""
        policy = {
            "version": 1,
            "rules": [
                {
                    "tool": "send_email",
                    "allow": [
                        {
                            "recipient_domain": {"in": ["acme.com"]},
                            "sender": {"eq": "bot@acme.com"}
                        }
                    ]
                }
            ]
        }
        engine = PolicyEngine(policy)

        # Both match - allow
        decision = engine.evaluate("send_email", {
            "recipient_domain": "acme.com",
            "sender": "bot@acme.com"
        })
        assert decision.outcome == Outcome.ALLOW

        # Only one matches - deny
        decision = engine.evaluate("send_email", {
            "recipient_domain": "acme.com",
            "sender": "other@acme.com"
        })
        assert decision.outcome == Outcome.DENY

    def test_invalid_policy_missing_version(self):
        with pytest.raises(ValueError, match="missing required 'version'"):
            PolicyEngine({"rules": []})

    def test_invalid_policy_missing_rules(self):
        with pytest.raises(ValueError, match="missing required 'rules'"):
            PolicyEngine({"version": 1})

    def test_policy_version_computed(self):
        policy = {"version": 1, "rules": []}
        engine = PolicyEngine(policy)
        assert engine.policy_version.startswith("policy-v1@sha256:")
