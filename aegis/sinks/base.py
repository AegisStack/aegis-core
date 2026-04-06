"""
Base protocol for audit sinks.
"""

from typing import Protocol
from ..audit.schema import AuditRecord


class AuditSink(Protocol):
    """Protocol for audit sink implementations."""

    def write(self, record: AuditRecord) -> None:
        """
        Write an audit record.

        Args:
            record: AuditRecord to write
        """
        ...
