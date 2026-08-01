"""
Aegis SDK Exception Classes

All custom exceptions raised by the Aegis SDK.
"""

from __future__ import annotations

from typing import Optional


class AegisError(Exception):
    """Base exception for all Aegis errors."""


class AegisViolationError(AegisError):
    """Raised when a tool call is explicitly denied by policy."""

    def __init__(self, tool_name: str, reason: str, matched_rule: Optional[str] = None):
        self.tool_name = tool_name
        self.reason = reason
        self.matched_rule = matched_rule
        super().__init__(f"Policy violation for '{tool_name}': {reason}")


class AegisPolicyLoadError(AegisError):
    """Raised when a policy file is malformed, missing, or has invalid schema."""

    def __init__(self, message: str, policy_path: Optional[str] = None):
        self.policy_path = policy_path
        super().__init__(
            f"Policy load error: {message}" + (f" (path: {policy_path})" if policy_path else "")
        )


class AegisEscalationTimeout(AegisError):
    """Raised when human does not resolve escalation within timeout window."""

    def __init__(self, escalation_id: str, timeout_minutes: int):
        self.escalation_id = escalation_id
        self.timeout_minutes = timeout_minutes
        super().__init__(f"Escalation {escalation_id} timed out after {timeout_minutes} minutes")


class AegisAmbiguityError(AegisError):
    """Raised when parameters are not evaluable against policy conditions."""

    def __init__(self, tool_name: str, message: str):
        self.tool_name = tool_name
        super().__init__(f"Ambiguity in policy evaluation for '{tool_name}': {message}")


class AegisConfigError(AegisError):
    """Raised when SDK is misconfigured at initialization."""

    def __init__(self, message: str):
        super().__init__(f"Configuration error: {message}")
