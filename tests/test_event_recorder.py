import hashlib
import json
from pathlib import Path

import pytest

from atomic_agent.event_recorder import (
    EVENT_PROTOCOL_VERSION,
    ArtifactReference,
    EventError,
    EventRecorder,
    EventRecorderConfig,
    EventRecorderConfigError,
    EventRecorderError,
)
from atomic_agent.models import AgentEventType, AgentRunResult, AgentRunStatus


def fixed_clock():
    return "2026-06-05T00:00:00Z"


def make_config(tmp_path):
    return EventRecorderConfig(
        event_stream_path=tmp_path / "events.jsonl",
        event_stream_ref="artifact://run_001/events.jsonl",
    )


def make_recorder(tmp_path, run_id="run_001", clock=fixed_clock):
    return EventRecorder(run_id=run_id, config=make_config(tmp_path), clock=clock)


def read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_event_protocol_version_is_one():
    assert EVENT_PROTOCOL_VERSION == 1


def test_artifact_reference_to_payload():
    ref = ArtifactReference(
        artifact_ref="artifact://run_001/stdout/test.txt",
        sha256="sha256:" + "a" * 64,
        size_bytes=12,
        truncated_in_observation=True,
    )

    assert ref.to_payload() == {
        "artifact_ref": "artifact://run_001/stdout/test.txt",
        "sha256": "sha256:" + "a" * 64,
        "size_bytes": 12,
        "truncated_in_observation": True,
    }


@pytest.mark.parametrize(
    "ref",
    [
        ArtifactReference("", "sha256:" + "a" * 64, 1, False),
        ArtifactReference("artifact://x", "bad", 1, False),
        ArtifactReference("artifact://x", "sha256:" + "a" * 64, -1, False),
        ArtifactReference("artifact://x", "sha256:" + "a" * 64, 1, "false"),
    ],
)
def test_artifact_reference_rejects_invalid_values(ref):
    with pytest.raises(ValueError):
        ref.to_payload()


def test_event_error_to_payload():
    error = EventError(
        kind="permission_denied",
        message="command_id is not declared in command policy",
        retryable=False,
        related_ref="act_001",
    )

    assert error.to_payload() == {
        "kind": "permission_denied",
        "message": "command_id is not declared in command policy",
        "retryable": False,
        "related_ref": "act_001",
    }


@pytest.mark.parametrize(
    "error",
    [
        EventError("", "message", False, None),
        EventError("kind", "", False, None),
        EventError("kind", "message", "false", None),
        EventError("kind", "message", False, 123),
    ],
)
def test_event_error_rejects_invalid_values(error):
    with pytest.raises(ValueError):
        error.to_payload()


def test_event_recorder_rejects_empty_run_id(tmp_path):
    with pytest.raises(EventRecorderConfigError):
        EventRecorder(run_id="", config=make_config(tmp_path), clock=fixed_clock)


def test_event_recorder_rejects_empty_event_stream_ref(tmp_path):
    config = EventRecorderConfig(event_stream_path=tmp_path / "events.jsonl", event_stream_ref="")

    with pytest.raises(EventRecorderConfigError):
        EventRecorder(run_id="run_001", config=config, clock=fixed_clock)


def test_event_recorder_rejects_missing_parent_directory(tmp_path):
    config = EventRecorderConfig(
        event_stream_path=tmp_path / "missing" / "events.jsonl",
        event_stream_ref="artifact://run_001/events.jsonl",
    )

    with pytest.raises(EventRecorderConfigError):
        EventRecorder(run_id="run_001", config=config, clock=fixed_clock)


def test_event_recorder_rejects_directory_output_path(tmp_path):
    config = EventRecorderConfig(
        event_stream_path=tmp_path,
        event_stream_ref="artifact://run_001/events.jsonl",
    )

    with pytest.raises(EventRecorderConfigError):
        EventRecorder(run_id="run_001", config=config, clock=fixed_clock)


def test_event_recorder_rejects_non_empty_existing_stream(tmp_path):
    path = tmp_path / "events.jsonl"
    path.write_text("already-used\n", encoding="utf-8")
    config = EventRecorderConfig(
        event_stream_path=path,
        event_stream_ref="artifact://run_001/events.jsonl",
    )

    with pytest.raises(EventRecorderConfigError):
        EventRecorder(run_id="run_001", config=config, clock=fixed_clock)


def canonical_hash(event_without_hash):
    canonical = json.dumps(event_without_hash, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def test_record_run_started_writes_first_jsonl_event(tmp_path):
    recorder = make_recorder(tmp_path)

    event = recorder.record_run_started(invocation_id="inv_001")

    assert event.event_id == "evt_000001"
    assert event.run_id == "run_001"
    assert event.sequence == 1
    assert event.type == AgentEventType.RUN_STARTED
    assert event.timestamp == "2026-06-05T00:00:00Z"
    assert event.payload == {"event_protocol_version": 1, "invocation_id": "inv_001"}
    assert event.previous_event_hash is None

    lines = read_jsonl(tmp_path / "events.jsonl")
    assert len(lines) == 1
    assert lines[0] == event.model_dump(mode="json")


def test_event_hash_uses_canonical_event_without_event_hash(tmp_path):
    recorder = make_recorder(tmp_path)

    event = recorder.record_run_started(invocation_id="inv_001")

    expected_input = {
        "event_id": "evt_000001",
        "run_id": "run_001",
        "sequence": 1,
        "type": "run.started",
        "timestamp": "2026-06-05T00:00:00Z",
        "payload": {"event_protocol_version": 1, "invocation_id": "inv_001"},
        "previous_event_hash": None,
    }
    assert event.event_hash == canonical_hash(expected_input)


def test_record_two_events_increments_sequence_and_links_previous_hash(tmp_path):
    recorder = make_recorder(tmp_path)

    first = recorder.record_run_started(invocation_id="inv_001")
    second = recorder.record_provider_turn_started(provider_turn_id="turn_001")

    assert first.event_id == "evt_000001"
    assert second.event_id == "evt_000002"
    assert second.sequence == 2
    assert second.previous_event_hash == first.event_hash
    lines = read_jsonl(tmp_path / "events.jsonl")
    assert [line["sequence"] for line in lines] == [1, 2]
    assert lines[1]["previous_event_hash"] == lines[0]["event_hash"]


def test_record_requires_run_started_as_first_event(tmp_path):
    recorder = make_recorder(tmp_path)

    with pytest.raises(EventRecorderError):
        recorder.record_provider_turn_started(provider_turn_id="turn_001")

    assert not (tmp_path / "events.jsonl").exists()


def test_record_rejects_empty_clock_value(tmp_path):
    recorder = make_recorder(tmp_path, clock=lambda: "")

    with pytest.raises(EventRecorderError):
        recorder.record_run_started(invocation_id="inv_001")

    assert not (tmp_path / "events.jsonl").exists()


def artifact_payload(name="artifact"):
    return ArtifactReference(
        artifact_ref=f"artifact://run_001/{name}.txt",
        sha256="sha256:" + "b" * 64,
        size_bytes=10,
        truncated_in_observation=False,
    ).to_payload()


def error_payload(kind="provider_failed"):
    return EventError(kind=kind, message="Something failed.", retryable=False, related_ref="ref_001").to_payload()


def test_required_event_helpers_write_expected_event_types(tmp_path):
    recorder = make_recorder(tmp_path)

    events = [
        recorder.record_run_started(invocation_id="inv_001"),
        recorder.record_provider_turn_started(provider_turn_id="turn_001"),
        recorder.record_provider_turn_completed(provider_turn_id="turn_001", output=artifact_payload("provider-output")),
        recorder.record_provider_turn_failed(provider_turn_id="turn_002", error=error_payload()),
        recorder.record_action_parsed(action={"action_id": "act_001", "action": "read_file"}),
        recorder.record_action_rejected(error=error_payload("invalid_action")),
        recorder.record_permission_decided(action_id="act_001", decision="allow", policy_ref="policy://default", reason="read allowed"),
        recorder.record_tool_attempt_started(tool_attempt_id="tool_001", action_id="act_001", tool="read_file"),
        recorder.record_tool_attempt_completed(
            tool_attempt_id="tool_001",
            action_id="act_001",
            tool="read_file",
            observation=artifact_payload("observation"),
        ),
        recorder.record_tool_attempt_started(tool_attempt_id="tool_002", action_id="act_002", tool="run_command"),
        recorder.record_tool_attempt_failed(
            tool_attempt_id="tool_002",
            action_id="act_002",
            tool="run_command",
            error=error_payload("timeout"),
        ),
        recorder.record_workspace_mutation_recorded(
            tool_attempt_id="tool_001",
            path="README.md",
            before_hash="sha256:" + "1" * 64,
            after_hash="sha256:" + "2" * 64,
            diff=artifact_payload("diff"),
        ),
        recorder.record_command_completed(
            tool_attempt_id="tool_002",
            command_id="test",
            exit_code=0,
            stdout=artifact_payload("stdout"),
            stderr=artifact_payload("stderr"),
        ),
        recorder.record_network_fetch_completed(
            tool_attempt_id="tool_002",
            url="https://example.com",
            status_code=200,
            response=artifact_payload("response"),
        ),
        recorder.record_result_submitted(
            summary="Done.",
            produced_paths=["README.md"],
            artifact_refs=[artifact_payload("result")],
        ),
        recorder.record_run_completed(summary="Run completed."),
    ]

    assert [event.type for event in events] == [
        AgentEventType.RUN_STARTED,
        AgentEventType.PROVIDER_TURN_STARTED,
        AgentEventType.PROVIDER_TURN_COMPLETED,
        AgentEventType.PROVIDER_TURN_FAILED,
        AgentEventType.ACTION_PARSED,
        AgentEventType.ACTION_REJECTED,
        AgentEventType.PERMISSION_DECIDED,
        AgentEventType.TOOL_ATTEMPT_STARTED,
        AgentEventType.TOOL_ATTEMPT_COMPLETED,
        AgentEventType.TOOL_ATTEMPT_STARTED,
        AgentEventType.TOOL_ATTEMPT_FAILED,
        AgentEventType.WORKSPACE_MUTATION_RECORDED,
        AgentEventType.COMMAND_COMPLETED,
        AgentEventType.NETWORK_FETCH_COMPLETED,
        AgentEventType.RESULT_SUBMITTED,
        AgentEventType.RUN_COMPLETED,
    ]
    assert len(read_jsonl(tmp_path / "events.jsonl")) == len(events)


@pytest.mark.parametrize(
    "event_type,payload",
    [
        (AgentEventType.RUN_STARTED, {"event_protocol_version": 1}),
        (AgentEventType.RUN_FAILED, {}),
        (AgentEventType.PROVIDER_TURN_COMPLETED, {"provider_turn_id": "turn_001"}),
        (AgentEventType.PERMISSION_DECIDED, {"action_id": "act_001", "decision": "allow", "policy_ref": "policy://default"}),
        (AgentEventType.TOOL_ATTEMPT_STARTED, {"tool_attempt_id": "tool_001", "action_id": "act_001"}),
        (AgentEventType.COMMAND_COMPLETED, {"tool_attempt_id": "tool_001", "command_id": "test", "exit_code": 0, "stdout": artifact_payload("stdout")}),
    ],
)
def test_record_rejects_missing_required_payload_fields(tmp_path, event_type, payload):
    recorder = make_recorder(tmp_path)
    recorder.record_run_started(invocation_id="inv_001")

    with pytest.raises(EventRecorderError):
        recorder.record(event_type, payload)

    assert len(read_jsonl(tmp_path / "events.jsonl")) == 1


def test_record_run_failed_uses_error_payload(tmp_path):
    recorder = make_recorder(tmp_path)
    recorder.record_run_started(invocation_id="inv_001")

    event = recorder.record_run_failed(error=error_payload("budget_exceeded"))

    assert event.type == AgentEventType.RUN_FAILED
    assert event.payload["error"]["kind"] == "budget_exceeded"


def test_terminal_event_prevents_later_events(tmp_path):
    recorder = make_recorder(tmp_path)
    recorder.record_run_started(invocation_id="inv_001")
    recorder.record_run_completed(summary="Done.")

    with pytest.raises(EventRecorderError):
        recorder.record_provider_turn_started(provider_turn_id="turn_after_done")

    assert len(read_jsonl(tmp_path / "events.jsonl")) == 2


def test_tool_attempt_completed_requires_started_attempt(tmp_path):
    recorder = make_recorder(tmp_path)
    recorder.record_run_started(invocation_id="inv_001")

    with pytest.raises(EventRecorderError):
        recorder.record_tool_attempt_completed(
            tool_attempt_id="missing_tool",
            action_id="act_001",
            tool="read_file",
            observation=artifact_payload("observation"),
        )

    assert len(read_jsonl(tmp_path / "events.jsonl")) == 1


def test_tool_attempt_failed_requires_started_attempt(tmp_path):
    recorder = make_recorder(tmp_path)
    recorder.record_run_started(invocation_id="inv_001")

    with pytest.raises(EventRecorderError):
        recorder.record_tool_attempt_failed(
            tool_attempt_id="missing_tool",
            action_id="act_001",
            tool="read_file",
            error=error_payload("io_error"),
        )

    assert len(read_jsonl(tmp_path / "events.jsonl")) == 1


def test_workspace_mutation_requires_started_attempt(tmp_path):
    recorder = make_recorder(tmp_path)
    recorder.record_run_started(invocation_id="inv_001")

    with pytest.raises(EventRecorderError):
        recorder.record_workspace_mutation_recorded(
            tool_attempt_id="missing_tool",
            path="README.md",
            before_hash=None,
            after_hash="sha256:" + "2" * 64,
            diff=artifact_payload("diff"),
        )

    assert len(read_jsonl(tmp_path / "events.jsonl")) == 1


def test_command_completed_requires_started_attempt(tmp_path):
    recorder = make_recorder(tmp_path)
    recorder.record_run_started(invocation_id="inv_001")

    with pytest.raises(EventRecorderError):
        recorder.record_command_completed(
            tool_attempt_id="missing_tool",
            command_id="test",
            exit_code=0,
            stdout=artifact_payload("stdout"),
            stderr=artifact_payload("stderr"),
        )

    assert len(read_jsonl(tmp_path / "events.jsonl")) == 1


def test_duplicate_tool_attempt_started_is_rejected(tmp_path):
    recorder = make_recorder(tmp_path)
    recorder.record_run_started(invocation_id="inv_001")
    recorder.record_tool_attempt_started(tool_attempt_id="tool_001", action_id="act_001", tool="read_file")

    with pytest.raises(EventRecorderError):
        recorder.record_tool_attempt_started(tool_attempt_id="tool_001", action_id="act_001", tool="read_file")

    assert len(read_jsonl(tmp_path / "events.jsonl")) == 2


def test_error_event_requires_valid_error_payload(tmp_path):
    recorder = make_recorder(tmp_path)
    recorder.record_run_started(invocation_id="inv_001")

    with pytest.raises(EventRecorderError):
        recorder.record_run_failed(error={"kind": "missing_message"})

    assert len(read_jsonl(tmp_path / "events.jsonl")) == 1


def test_provider_output_requires_valid_artifact_payload(tmp_path):
    recorder = make_recorder(tmp_path)
    recorder.record_run_started(invocation_id="inv_001")

    with pytest.raises(EventRecorderError):
        recorder.record_provider_turn_completed(provider_turn_id="turn_001", output={"artifact_ref": "artifact://x"})

    assert len(read_jsonl(tmp_path / "events.jsonl")) == 1


def test_workspace_mutation_requires_valid_hashes_and_diff_artifact(tmp_path):
    recorder = make_recorder(tmp_path)
    recorder.record_run_started(invocation_id="inv_001")
    recorder.record_tool_attempt_started(tool_attempt_id="tool_001", action_id="act_001", tool="write_file")

    with pytest.raises(EventRecorderError):
        recorder.record_workspace_mutation_recorded(
            tool_attempt_id="tool_001",
            path="README.md",
            before_hash="not-a-hash",
            after_hash="sha256:" + "2" * 64,
            diff=artifact_payload("diff"),
        )

    with pytest.raises(EventRecorderError):
        recorder.record_workspace_mutation_recorded(
            tool_attempt_id="tool_001",
            path="README.md",
            before_hash=None,
            after_hash="sha256:" + "2" * 64,
            diff={"artifact_ref": "artifact://run_001/diff.patch"},
        )

    assert len(read_jsonl(tmp_path / "events.jsonl")) == 2


def test_command_completed_requires_exit_code_and_artifact_payloads(tmp_path):
    recorder = make_recorder(tmp_path)
    recorder.record_run_started(invocation_id="inv_001")
    recorder.record_tool_attempt_started(tool_attempt_id="tool_001", action_id="act_001", tool="run_command")

    with pytest.raises(EventRecorderError):
        recorder.record_command_completed(
            tool_attempt_id="tool_001",
            command_id="test",
            exit_code="0",
            stdout=artifact_payload("stdout"),
            stderr=artifact_payload("stderr"),
        )

    with pytest.raises(EventRecorderError):
        recorder.record_command_completed(
            tool_attempt_id="tool_001",
            command_id="test",
            exit_code=0,
            stdout={"artifact_ref": "artifact://run_001/stdout.txt"},
            stderr=artifact_payload("stderr"),
        )

    assert len(read_jsonl(tmp_path / "events.jsonl")) == 2


def test_result_submitted_requires_summary_paths_and_artifact_refs(tmp_path):
    recorder = make_recorder(tmp_path)
    recorder.record_run_started(invocation_id="inv_001")

    with pytest.raises(EventRecorderError):
        recorder.record_result_submitted(summary="", produced_paths=["README.md"], artifact_refs=[])

    with pytest.raises(EventRecorderError):
        recorder.record_result_submitted(summary="Done", produced_paths=[123], artifact_refs=[])

    with pytest.raises(EventRecorderError):
        recorder.record_result_submitted(summary="Done", produced_paths=[], artifact_refs=[{"artifact_ref": "artifact://x"}])

    assert len(read_jsonl(tmp_path / "events.jsonl")) == 1


def test_events_hash_hashes_complete_jsonl_bytes(tmp_path):
    recorder = make_recorder(tmp_path)
    recorder.record_run_started(invocation_id="inv_001")
    recorder.record_run_completed(summary="Done.")

    raw = (tmp_path / "events.jsonl").read_bytes()
    assert recorder.events_hash() == "sha256:" + hashlib.sha256(raw).hexdigest()


def test_events_hash_fails_when_stream_missing(tmp_path):
    recorder = make_recorder(tmp_path)

    with pytest.raises(EventRecorderError):
        recorder.events_hash()


def test_agent_run_result_accepts_recorder_event_stream_ref_and_hash(tmp_path):
    recorder = make_recorder(tmp_path)
    recorder.record_run_started(invocation_id="inv_001")
    recorder.record_run_completed(summary="Done.")

    result = AgentRunResult(
        run_id="run_001",
        status=AgentRunStatus.COMPLETED,
        event_stream_ref=recorder.event_stream_ref,
        events_hash=recorder.events_hash(),
        tool_attempts=[],
        workspace_mutations=[],
        artifacts=[],
        summary="Done.",
    )

    assert result.event_stream_ref == "artifact://run_001/events.jsonl"
    assert result.events_hash.startswith("sha256:")


def test_record_write_failure_raises_without_sequence_increment(tmp_path):
    recorder = make_recorder(tmp_path)
    recorder.record_run_started(invocation_id="inv_001")
    stream_path = tmp_path / "events.jsonl"
    stream_path.unlink()
    stream_path.mkdir()

    with pytest.raises(EventRecorderError):
        recorder.record_provider_turn_started(provider_turn_id="turn_001")

    assert recorder._sequence == 1
    assert recorder._previous_event_hash is not None


def test_payload_validation_failure_does_not_write_event_or_increment_sequence(tmp_path):
    recorder = make_recorder(tmp_path)
    recorder.record_run_started(invocation_id="inv_001")

    with pytest.raises(EventRecorderError):
        recorder.record_run_failed(error={"kind": "missing_message"})

    assert recorder._sequence == 1
    assert len(read_jsonl(tmp_path / "events.jsonl")) == 1
