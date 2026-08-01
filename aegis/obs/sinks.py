"""
Observability Sinks

Destinations for observability events.
"""

from __future__ import annotations

import json
import sys
from typing import Optional, Protocol

from .events import ObservabilityEvent


class ObsSink(Protocol):
    """Protocol for observability sink implementations."""

    def emit(self, event: ObservabilityEvent) -> None:
        """
        Emit an observability event.

        Args:
            event: ObservabilityEvent to emit
        """
        ...


class ConsoleSink:
    """
    Writes structured JSON events to stdout.

    For local development and debugging.
    """

    def __init__(self, pretty: bool = False):
        """
        Initialize console sink.

        Args:
            pretty: If True, pretty-print JSON
        """
        self.pretty = pretty

    def emit(self, event: ObservabilityEvent) -> None:
        """Emit event to stdout."""
        if self.pretty:
            print(json.dumps(event.to_dict(), indent=2, default=str))
        else:
            print(json.dumps(event.to_dict(), default=str))
        sys.stdout.flush()


class PrometheusSink:
    """
    Exposes metrics via Prometheus endpoint.

    Phase 2 - placeholder for now.
    """

    def __init__(self, port: int = 9090):
        """
        Initialize Prometheus sink.

        Args:
            port: Port to expose metrics on
        """
        self.port = port
        # Placeholder - would integrate with prometheus_client

    def emit(self, event: ObservabilityEvent) -> None:
        """Emit event as Prometheus metrics."""
        # Placeholder - would update counters/gauges


class ObsWriter:
    """
    Writes observability events to configured sinks.

    Similar to AuditWriter but for observability events.
    """

    def __init__(self, sinks: Optional[list] = None):
        """
        Initialize observability writer.

        Args:
            sinks: List of ObsSink instances
        """
        self.sinks = sinks or []

    def emit(self, event: ObservabilityEvent) -> None:
        """
        Emit event to all configured sinks.

        Args:
            event: ObservabilityEvent to emit
        """
        for sink in self.sinks:
            try:
                sink.emit(event)
            except Exception as e:
                # Log error but continue to other sinks
                print(f"Error emitting to sink {sink.__class__.__name__}: {e}")

    def add_sink(self, sink: ObsSink) -> None:
        """Add a sink."""
        self.sinks.append(sink)

    def remove_sink(self, sink: ObsSink) -> None:
        """Remove a sink."""
        if sink in self.sinks:
            self.sinks.remove(sink)
