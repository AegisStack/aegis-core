"""
Webhook-based audit sink with async support.
"""

from __future__ import annotations

import queue
import threading
from typing import Optional

import requests

from ..audit.schema import AuditRecord


class WebhookSink:
    """
    Posts audit records to a webhook endpoint.

    Supports async mode with background queue for non-blocking writes.
    """

    def __init__(
        self,
        url: str,
        headers: Optional[dict[str, str]] = None,
        async_mode: bool = False,
        queue_size: int = 1000,
        timeout: int = 10,
    ):
        """
        Initialize webhook sink.

        Args:
            url: Webhook URL to POST records to
            headers: Optional HTTP headers (e.g., Authorization)
            async_mode: If True, queue records and send in background
            queue_size: Maximum queue size for async mode
            timeout: HTTP request timeout in seconds
        """
        self.url = url
        self.headers = headers or {}
        self.async_mode = async_mode
        self.timeout = timeout

        if self.async_mode:
            self._queue: queue.Queue = queue.Queue(maxsize=queue_size)
            self._stop_event = threading.Event()
            self._worker_thread = threading.Thread(target=self._worker, daemon=True)
            self._worker_thread.start()

    def write(self, record: AuditRecord) -> None:
        """
        Write audit record to webhook.

        Args:
            record: AuditRecord to write
        """
        if self.async_mode:
            try:
                self._queue.put_nowait(record)
            except queue.Full:
                # Queue full - drop record or log error
                print(f"WebhookSink queue full, dropping record {record.record_id}")
        else:
            self._send_record(record)

    def _send_record(self, record: AuditRecord) -> None:
        """Send a single record to the webhook."""
        try:
            response = requests.post(
                self.url,
                json=record.to_dict(),
                headers=self.headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as e:
            # Log error - don't raise to avoid breaking the caller
            print(f"WebhookSink error posting to {self.url}: {e}")

    def _worker(self) -> None:
        """Background worker thread for async mode."""
        while not self._stop_event.is_set():
            try:
                record = self._queue.get(timeout=1)
                self._send_record(record)
                self._queue.task_done()
            except queue.Empty:
                continue

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
