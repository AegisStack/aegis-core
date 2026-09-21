"""
File-based audit sink with rotation support.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..audit.schema import AuditRecord


class FileSink:
    """
    Writes audit records to newline-delimited JSON files.

    Supports daily rotation for easy ingestion into data warehouses.
    """

    def __init__(
        self,
        path: str = "./audit/aegis.jsonl",
        rotate: Optional[str] = None,
        buffer_size: int = 1,
    ):
        """
        Initialize file sink.

        Args:
            path: Path to audit log file
            rotate: Rotation strategy ('daily', 'hourly', or None)
            buffer_size: Number of records to buffer before flush (1 = no buffering)
        """
        self.base_path = Path(path)
        self.rotate = rotate
        self.buffer_size = buffer_size
        self._buffer: list[AuditRecord] = []
        self._current_date: Optional[str] = None

        # Create directory if it doesn't exist
        self.base_path.parent.mkdir(parents=True, exist_ok=True)

    def _get_file_path(self) -> Path:
        """Get the current file path based on rotation strategy."""
        if self.rotate == "daily":
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            self._current_date = date_str
            stem = self.base_path.stem
            suffix = self.base_path.suffix
            return self.base_path.parent / f"{stem}-{date_str}{suffix}"

        elif self.rotate == "hourly":
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H")
            self._current_date = date_str
            stem = self.base_path.stem
            suffix = self.base_path.suffix
            return self.base_path.parent / f"{stem}-{date_str}{suffix}"

        else:
            return self.base_path

    def write(self, record: AuditRecord) -> None:
        """
        Write audit record to file.

        Args:
            record: AuditRecord to write
        """
        file_path = self._get_file_path()

        # Write directly or buffer
        if self.buffer_size == 1:
            with open(file_path, "a") as f:
                f.write(record.to_json() + "\n")
        else:
            self._buffer.append(record)
            if len(self._buffer) >= self.buffer_size:
                self.flush()

    def flush(self) -> None:
        """Flush buffered records to disk."""
        if not self._buffer:
            return

        file_path = self._get_file_path()
        with open(file_path, "a") as f:
            f.writelines(record.to_json() + "\n" for record in self._buffer)

        self._buffer.clear()

    def close(self) -> None:
        """Close the sink and flush any buffered records."""
        self.flush()

    def __del__(self) -> None:
        """Ensure file is closed on deletion."""
        self.close()
