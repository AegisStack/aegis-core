"""
Aegis Dashboard Sink - Posts audit records to Aegis Cloud dashboard.
"""

import json
import queue
import threading
from typing import Optional, List
import requests
from ..audit.schema import AuditRecord


class AegisDashboardSink:
    """
    Posts audit records to Aegis Cloud dashboard API.

    Batches records for efficiency and uses background thread for async mode.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "http://localhost:8000",
        async_mode: bool = True,
        batch_size: int = 10,
        batch_timeout_ms: int = 1000,
        queue_size: int = 1000,
        timeout: int = 10,
    ):
        """
        Initialize dashboard sink.

        Args:
            api_key: API key for authentication
            base_url: Base URL of dashboard API
            async_mode: If True, queue records and send in background
            batch_size: Number of records to batch before sending
            batch_timeout_ms: Max time to wait before sending partial batch
            queue_size: Maximum queue size for async mode
            timeout: HTTP request timeout in seconds
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.async_mode = async_mode
        self.batch_size = batch_size
        self.batch_timeout_ms = batch_timeout_ms
        self.timeout = timeout

        if self.async_mode:
            self._queue: queue.Queue = queue.Queue(maxsize=queue_size)
            self._stop_event = threading.Event()
            self._worker_thread = threading.Thread(target=self._worker, daemon=True)
            self._worker_thread.start()

    def write(self, record: AuditRecord) -> None:
        """
        Write audit record to dashboard.

        Args:
            record: AuditRecord to write
        """
        if self.async_mode:
            try:
                self._queue.put_nowait(record)
            except queue.Full:
                print(f"AegisDashboardSink queue full, dropping record {record.record_id}")
        else:
            self._send_batch([record])

    def _worker(self) -> None:
        """Background worker thread for async mode."""
        batch = []
        while not self._stop_event.is_set():
            try:
                record = self._queue.get(timeout=self.batch_timeout_ms / 1000)
                batch.append(record)

                if len(batch) >= self.batch_size:
                    self._send_batch(batch)
                    batch = []

            except queue.Empty:
                if batch:
                    self._send_batch(batch)
                    batch = []

    def _send_batch(self, records: List[AuditRecord]) -> None:
        """Send a batch of records to the dashboard API."""
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/ingest/audit",
                json=[r.to_dict() for r in records],
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": self.api_key,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"AegisDashboardSink error posting to {self.base_url}: {e}")

    def flush(self) -> None:
        """Flush any buffered records."""
        if self.async_mode:
            # Wait for queue to drain
            self._queue.join()

    def close(self) -> None:
        """Close the sink and wait for queue to drain."""
        if self.async_mode:
            # Wait for queue to drain
            self._queue.join()
            # Stop worker thread
            self._stop_event.set()
            self._worker_thread.join(timeout=5)

    def __del__(self):
        """Ensure cleanup on deletion."""
        self.close()
