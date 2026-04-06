"""
Policy Engine - Core evaluation logic for tool calls against policy rules.

Evaluates tool calls against customer-configured policies with condition operators.
"""

import re
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from enum import Enum


class Outcome(Enum):
    """Policy evaluation outcomes."""
    ALLOW = "allow"
    DENY = "deny"
    ESCALATE = "escalate"


@dataclass
class PolicyDecision:
    """Result of policy evaluation."""
    outcome: Outcome
    matched_rule: Optional[str]
    reason: str
    policy_version: str
    tool_name: str
    params: Dict[str, Any]


class ConditionEvaluator:
    """Evaluates policy conditions against parameter values."""

    @staticmethod
    def evaluate(param_value: Any, condition: Dict[str, Any]) -> bool:
        """
        Evaluate a single condition against a parameter value.

        Args:
            param_value: The actual value of the parameter
            condition: Dictionary with operator and expected value(s)

        Returns:
            True if condition matches, False otherwise
        """
        if not isinstance(condition, dict):
            # Direct value comparison
            return param_value == condition

        for operator, expected in condition.items():
            if operator == "eq":
                if param_value != expected:
                    return False
            elif operator == "neq":
                if param_value == expected:
                    return False
            elif operator == "lt":
                if not (param_value < expected):
                    return False
            elif operator == "lte":
                if not (param_value <= expected):
                    return False
            elif operator == "gt":
                if not (param_value > expected):
                    return False
            elif operator == "gte":
                if not (param_value >= expected):
                    return False
            elif operator == "in":
                if param_value not in expected:
                    return False
            elif operator == "not_in":
                if param_value in expected:
                    return False
            elif operator == "regex":
                if not isinstance(param_value, str):
                    return False
                if not re.match(expected, param_value):
                    return False
            else:
                # Unknown operator - fail safe
                return False

        return True

    @staticmethod
    def evaluate_conditions(params: Dict[str, Any], conditions: List[Dict[str, Any]]) -> bool:
        """
        Evaluate a list of condition dictionaries against parameters.

        All conditions in a single dict must match (AND logic).
        At least one dict in the list must match (OR logic).

        Args:
            params: Actual tool call parameters
            conditions: List of condition dictionaries from policy

        Returns:
            True if any condition dict fully matches
        """
        for condition_dict in conditions:
            # Check if all conditions in this dict match (AND)
            all_match = True
            for param_name, condition in condition_dict.items():
                if param_name not in params:
                    all_match = False
                    break
                if not ConditionEvaluator.evaluate(params[param_name], condition):
                    all_match = False
                    break

            if all_match:
                return True

        return False


class PolicyEngine:
    """
    Core policy evaluation engine.

    Evaluates tool calls against YAML-defined policies with support for
    allow, deny, and escalate outcomes.
    """

    def __init__(self, policy: Dict[str, Any]):
        """
        Initialize policy engine with a parsed policy.

        Args:
            policy: Parsed policy dictionary (from YAML)

        Raises:
            ValueError: If policy is invalid
        """
        self._validate_policy(policy)
        self.policy = policy
        self.policy_version = self._compute_version(policy)

    @staticmethod
    def _validate_policy(policy: Dict[str, Any]) -> None:
        """Validate policy structure."""
        if not isinstance(policy, dict):
            raise ValueError("Policy must be a dictionary")

        if "version" not in policy:
            raise ValueError("Policy missing required 'version' field")

        if "rules" not in policy:
            raise ValueError("Policy missing required 'rules' field")

        if not isinstance(policy["rules"], list):
            raise ValueError("Policy 'rules' must be a list")

    @staticmethod
    def _compute_version(policy: Dict[str, Any]) -> str:
        """Compute a version hash for the policy."""
        import hashlib
        import json

        # Serialize policy to stable JSON and hash it
        policy_str = json.dumps(policy, sort_keys=True)
        hash_obj = hashlib.sha256(policy_str.encode())
        return f"policy-v{policy.get('version', 1)}@sha256:{hash_obj.hexdigest()[:16]}"

    def evaluate(self, tool_name: str, params: Dict[str, Any]) -> PolicyDecision:
        """
        Evaluate a tool call against the policy.

        Evaluation order:
        1. Check if tool is in policy (apply defaults.unmatched_tool if not)
        2. Evaluate deny conditions (first match blocks immediately)
        3. Evaluate escalate conditions (first match pauses execution)
        4. Evaluate allow conditions (first match permits execution)
        5. If no allow matches, apply defaults.unmatched_param

        Args:
            tool_name: Name of the tool being called
            params: Parameters passed to the tool

        Returns:
            PolicyDecision with outcome and reasoning
        """
        # Find the tool rule
        tool_rule = None
        rule_index = None
        for idx, rule in enumerate(self.policy["rules"]):
            if rule.get("tool") == tool_name:
                tool_rule = rule
                rule_index = idx
                break

        # If tool not found in policy, apply default
        if tool_rule is None:
            defaults = self.policy.get("defaults", {})
            default_action = defaults.get("unmatched_tool", "deny")
            outcome = Outcome.DENY if default_action == "deny" else Outcome.ESCALATE
            return PolicyDecision(
                outcome=outcome,
                matched_rule="defaults.unmatched_tool",
                reason=f"Tool '{tool_name}' not found in policy, applying default: {default_action}",
                policy_version=self.policy_version,
                tool_name=tool_name,
                params=params,
            )

        # Step 1: Check deny conditions (first match wins)
        deny_conditions = tool_rule.get("deny")
        if deny_conditions is not None:
            if deny_conditions == "always":
                return PolicyDecision(
                    outcome=Outcome.DENY,
                    matched_rule=f"{tool_name}.deny.always",
                    reason=f"Tool '{tool_name}' is unconditionally denied by policy",
                    policy_version=self.policy_version,
                    tool_name=tool_name,
                    params=params,
                )
            elif isinstance(deny_conditions, list):
                for cond_idx, condition in enumerate(deny_conditions):
                    if ConditionEvaluator.evaluate_conditions(params, [condition]):
                        return PolicyDecision(
                            outcome=Outcome.DENY,
                            matched_rule=f"{tool_name}.deny[{cond_idx}]",
                            reason=self._build_reason("denied", params, condition),
                            policy_version=self.policy_version,
                            tool_name=tool_name,
                            params=params,
                        )

        # Step 2: Check escalate conditions (first match wins)
        escalate_conditions = tool_rule.get("escalate")
        if escalate_conditions is not None:
            if escalate_conditions == "always":
                return PolicyDecision(
                    outcome=Outcome.ESCALATE,
                    matched_rule=f"{tool_name}.escalate.always",
                    reason=f"Tool '{tool_name}' requires escalation by policy",
                    policy_version=self.policy_version,
                    tool_name=tool_name,
                    params=params,
                )
            elif isinstance(escalate_conditions, list):
                for cond_idx, condition in enumerate(escalate_conditions):
                    if ConditionEvaluator.evaluate_conditions(params, [condition]):
                        return PolicyDecision(
                            outcome=Outcome.ESCALATE,
                            matched_rule=f"{tool_name}.escalate[{cond_idx}]",
                            reason=self._build_reason("escalated", params, condition),
                            policy_version=self.policy_version,
                            tool_name=tool_name,
                            params=params,
                        )

        # Step 3: Check allow conditions (first match wins)
        allow_conditions = tool_rule.get("allow")
        if allow_conditions is not None:
            if allow_conditions == "always":
                return PolicyDecision(
                    outcome=Outcome.ALLOW,
                    matched_rule=f"{tool_name}.allow.always",
                    reason=f"Tool '{tool_name}' is unconditionally allowed by policy",
                    policy_version=self.policy_version,
                    tool_name=tool_name,
                    params=params,
                )
            elif isinstance(allow_conditions, list):
                for cond_idx, condition in enumerate(allow_conditions):
                    if ConditionEvaluator.evaluate_conditions(params, [condition]):
                        return PolicyDecision(
                            outcome=Outcome.ALLOW,
                            matched_rule=f"{tool_name}.allow[{cond_idx}]",
                            reason=self._build_reason("allowed", params, condition),
                            policy_version=self.policy_version,
                            tool_name=tool_name,
                            params=params,
                        )

        # Step 4: No allow condition matched - apply default
        defaults = self.policy.get("defaults", {})
        default_action = defaults.get("unmatched_param", "deny")

        if default_action == "escalate":
            outcome = Outcome.ESCALATE
            reason = f"Parameters for '{tool_name}' did not match any allow rule, escalating by default"
        else:
            outcome = Outcome.DENY
            reason = f"Parameters for '{tool_name}' did not match any allow rule, denying by default"

        return PolicyDecision(
            outcome=outcome,
            matched_rule="defaults.unmatched_param",
            reason=reason,
            policy_version=self.policy_version,
            tool_name=tool_name,
            params=params,
        )

    @staticmethod
    def _build_reason(action: str, params: Dict[str, Any], condition: Dict[str, Any]) -> str:
        """Build a human-readable reason string."""
        # Extract the first condition for the reason
        if not condition:
            return f"Tool call {action}"

        parts = []
        for param_name, cond_value in condition.items():
            actual_value = params.get(param_name)
            if isinstance(cond_value, dict):
                # Extract operator and value
                for op, expected in cond_value.items():
                    if op == "lte":
                        parts.append(f"{param_name} {actual_value} <= {expected}")
                    elif op == "gte":
                        parts.append(f"{param_name} {actual_value} >= {expected}")
                    elif op == "lt":
                        parts.append(f"{param_name} {actual_value} < {expected}")
                    elif op == "gt":
                        parts.append(f"{param_name} {actual_value} > {expected}")
                    elif op == "in":
                        parts.append(f"{param_name} '{actual_value}' in allowed list")
                    elif op == "not_in":
                        parts.append(f"{param_name} '{actual_value}' not in allowed list")
                    elif op == "regex":
                        parts.append(f"{param_name} '{actual_value}' matches pattern")
                    else:
                        parts.append(f"{param_name} {op} {expected}")
            else:
                parts.append(f"{param_name} = {actual_value}")

        reason_str = ", ".join(parts)
        return f"Tool call {action}: {reason_str}"
