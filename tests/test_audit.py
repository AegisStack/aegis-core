"""
Tests for audit trail and sinks.
"""

import json
import tempfile
from pathlib import Path

import pytest

from aegis.audit import AuditWriter, create_audit_record
from aegis.sinks import FileSink


class TestAuditRecord:
    """Test audit record creation."""

    def test_create_audit_record(self):
        record = create_audit_record(
            agent_id="test-agent",
            customer_id="acme-corp",
            session_id="sess_123",
            policy_version="policy-v1@sha256:abc",
            tool_name="issue_refund",
            params={"amount_usd": 100},
            outcome="allow",
            matched_rule="issue_refund.allow[0]",
            reason="Amount within limit",
        )

        assert record.agent_id == "test-agent"
        assert record.customer_id == "acme-corp"
        assert record.tool_name == "issue_refund"
        assert record.outcome == "allow"
        assert record.record_id is not None
        assert record.timestamp is not None

    def test_audit_record_to_dict(self):
        record = create_audit_record(
            agent_id="test-agent",
            customer_id="acme-corp",
            session_id="sess_123",
            policy_version="policy-v1",
            tool_name="test_tool",
            params={"x": 1},
            outcome="allow",
            matched_rule="test_tool.allow",
            reason="Test",
        )

        record_dict = record.to_dict()
        assert isinstance(record_dict, dict)
        assert record_dict["agent_id"] == "test-agent"
        assert record_dict["outcome"] == "allow"

    def test_audit_record_to_json(self):
        record = create_audit_record(
            agent_id="test-agent",
            customer_id=None,
            session_id=None,
            policy_version="policy-v1",
            tool_name="test_tool",
            params={},
            outcome="deny",
            matched_rule="test_tool.deny",
            reason="Test denial",
        )

        json_str = record.to_json()
        parsed = json.loads(json_str)
        assert parsed["outcome"] == "deny"

    def test_invalid_outcome(self):
        with pytest.raises(ValueError, match="Invalid outcome"):
            create_audit_record(
                agent_id="test-agent",
                customer_id=None,
                session_id=None,
                policy_version="policy-v1",
                tool_name="test_tool",
                params={},
                outcome="invalid",
                matched_rule="",
                reason="",
            )


class TestFileSink:
    """Test file-based audit sink."""

    def test_file_sink_writes_jsonl(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sink = FileSink(path=f"{tmpdir}/audit.jsonl")

            record = create_audit_record(
                agent_id="test-agent",
                customer_id="acme",
                session_id="sess_1",
                policy_version="v1",
                tool_name="test",
                params={},
                outcome="allow",
                matched_rule="rule",
                reason="test",
            )

            sink.write(record)
            sink.close()

            # Read and verify
            with open(f"{tmpdir}/audit.jsonl") as f:
                lines = f.readlines()
                assert len(lines) == 1
                parsed = json.loads(lines[0])
                assert parsed["agent_id"] == "test-agent"

    def test_file_sink_multiple_records(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sink = FileSink(path=f"{tmpdir}/audit.jsonl")

            for i in range(3):
                record = create_audit_record(
                    agent_id=f"agent-{i}",
                    customer_id="acme",
                    session_id=f"sess_{i}",
                    policy_version="v1",
                    tool_name="test",
                    params={},
                    outcome="allow",
                    matched_rule="rule",
                    reason="test",
                )
                sink.write(record)

            sink.close()

            with open(f"{tmpdir}/audit.jsonl") as f:
                lines = f.readlines()
                assert len(lines) == 3


class TestAuditWriter:
    """Test audit writer with multiple sinks."""

    def test_audit_writer_writes_to_sinks(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sink1 = FileSink(path=f"{tmpdir}/audit1.jsonl")
            sink2 = FileSink(path=f"{tmpdir}/audit2.jsonl")

            writer = AuditWriter(sinks=[sink1, sink2])

            record = create_audit_record(
                agent_id="test-agent",
                customer_id="acme",
                session_id="sess_1",
                policy_version="v1",
                tool_name="test",
                params={},
                outcome="allow",
                matched_rule="rule",
                reason="test",
            )

            writer.write(record)
            sink1.close()
            sink2.close()

            # Both files should have the record
            assert Path(f"{tmpdir}/audit1.jsonl").exists()
            assert Path(f"{tmpdir}/audit2.jsonl").exists()
