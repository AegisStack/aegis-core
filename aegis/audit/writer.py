"""
Audit Writer

Writes structured audit records to configured sinks.
"""

from typing import List, Optional
from .schema import AuditRecord


class AuditWriter:
    """
    Writes audit records to one or more sinks.

    Handles async/sync writing and error handling.
    """

    def __init__(self, sinks: Optional[List] = None):
        """
        Initialize audit writer.

        Args:
            sinks: List of AuditSink instances
        """
        self.sinks = sinks or []

    def write(self, record: AuditRecord) -> None:
        """
        Write audit record to all configured sinks.

        Args:
            record: AuditRecord to write

        Note:
            Errors from individual sinks are logged but don't prevent
            writing to other sinks.
        """
        for sink in self.sinks:
            try:
                sink.write(record)
            except Exception as e:
                # Log error but continue to other sinks
                # In production, this should use proper logging
                print(f"Error writing to sink {sink.__class__.__name__}: {e}")

    def add_sink(self, sink) -> None:
        """Add a sink to the writer."""
        self.sinks.append(sink)

    def remove_sink(self, sink) -> None:
        """Remove a sink from the writer."""
        if sink in self.sinks:
            self.sinks.remove(sink)
