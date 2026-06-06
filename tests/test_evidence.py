import hashlib
import json
from pathlib import Path

import pytest

from atomic_agent.event_recorder import ArtifactReference, EventRecorder, EventRecorderConfig
from atomic_agent.evidence import EvidenceMappingError, build_evidence_summary, describe_replay_status, verify_event_stream
from atomic_agent.examples.minimal_fake_loop import (
    WORKSPACE_OUTPUT_PATH,
    ExamplePaths,
    build_invocation,
    build_loop,
    prepare_paths,
)
from atomic_agent.models import AgentRunResult, AgentRunStatus


BANNED_GOVERNANCE_FIELDS = {
    "ticket_completed",
    "closeout_committed",
    "governance_status",
    "evidence_verified",
    "source_inventory_accepted",
}


def make_paths(tmp_path, name="evidence-example"):
    base = tmp_path / name
    return ExamplePaths(
        workspace=base / "workspace",
        event_stream=base / "events" / "events.jsonl",
        artifact_root=base / "artifacts",
        result=base / "result.json",
    )


def run_fake_loop(tmp_path, run_id="evidence_run"):
    paths = make_paths(tmp_path)
    prepare_paths(paths)
    loop = build_loop(run_id, paths)
    result = loop.run(build_invocation(paths))
    return paths, result


def read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def write_jsonl(path: Path, events):
    path.write_text(
        "\n".join(json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=False) for event in events)
        + "\n",
        encoding="utf-8",
    )


def sha256_bytes(content: bytes):
    return "sha256:" + hashlib.sha256(content).hexdigest()


def hash_event_without_hash(event):
    event_without_hash = dict(event)
    event_without_hash.pop("event_hash", None)
    canonical = json.dumps(event_without_hash, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256_bytes(canonical.encode("utf-8"))


def relink_events(events):
    previous_hash = None
    relinked = []
    for sequence, original in enumerate(events, start=1):
        event = dict(original)
        event["sequence"] = sequence
        event["event_id"] = f"evt_{sequence:06d}"
        event["previous_event_hash"] = previous_hash
        event["event_hash"] = hash_event_without_hash(event)
        previous_hash = event["event_hash"]
        relinked.append(event)
    return relinked


def artifact_payload(name="artifact"):
    return ArtifactReference(
        artifact_ref=f"artifact://missing_lineage/{name}.txt",
        sha256="sha256:" + "a" * 64,
        size_bytes=10,
        truncated_in_observation=False,
    ).to_payload()


def fixed_clock():
    return "2026-06-07T00:00:00Z"


def assert_no_banned_governance_fields(value):
    if isinstance(value, dict):
        assert BANNED_GOVERNANCE_FIELDS.isdisjoint(value)
        for child in value.values():
            assert_no_banned_governance_fields(child)
    elif isinstance(value, list):
        for child in value:
            assert_no_banned_governance_fields(child)


def test_verify_event_stream_accepts_valid_fake_loop_stream(tmp_path):
    paths, result = run_fake_loop(tmp_path)

    integrity = verify_event_stream(paths.event_stream, expected_events_hash=result.events_hash)

    assert integrity["ok"] is True
    assert integrity["event_count"] > 0
    assert integrity["terminal_event_type"] == "run.completed"
    assert integrity["events_hash"] == result.events_hash


def test_verify_event_stream_rejects_missing_file(tmp_path):
    missing = tmp_path / "missing.jsonl"

    integrity = verify_event_stream(missing)

    assert integrity["ok"] is False
    assert integrity["failure_kind"] == "event_stream_missing"
    assert str(missing) in integrity["message"]


def test_verify_event_stream_rejects_empty_file(tmp_path):
    stream = tmp_path / "events.jsonl"
    stream.write_text("", encoding="utf-8")

    integrity = verify_event_stream(stream)

    assert integrity["ok"] is False
    assert integrity["failure_kind"] == "event_stream_empty"
    assert "empty" in integrity["message"]


def test_verify_event_stream_rejects_non_utf8_file(tmp_path):
    stream = tmp_path / "events.jsonl"
    stream.write_bytes(b"\xff\xfe")

    integrity = verify_event_stream(stream)

    assert integrity["ok"] is False
    assert integrity["failure_kind"] == "event_stream_unreadable"
    assert "UTF-8" in integrity["message"]


def test_verify_event_stream_rejects_invalid_json_with_line_number(tmp_path):
    stream = tmp_path / "events.jsonl"
    stream.write_text('{"ok": true}\n{not-json}\n', encoding="utf-8")

    integrity = verify_event_stream(stream)

    assert integrity["ok"] is False
    assert integrity["failure_kind"] == "event_json_invalid"
    assert "line 2" in integrity["message"]


def test_verify_event_stream_rejects_non_object_json_line(tmp_path):
    stream = tmp_path / "events.jsonl"
    stream.write_text("[]\n", encoding="utf-8")

    integrity = verify_event_stream(stream)

    assert integrity["ok"] is False
    assert integrity["failure_kind"] == "event_schema_invalid"
    assert "line 1" in integrity["message"]


def test_verify_event_stream_rejects_previous_hash_mismatch(tmp_path):
    paths, _ = run_fake_loop(tmp_path)
    events = read_jsonl(paths.event_stream)
    events[1]["previous_event_hash"] = "sha256:" + "0" * 64
    write_jsonl(paths.event_stream, events)

    integrity = verify_event_stream(paths.event_stream)

    assert integrity["ok"] is False
    assert integrity["failure_kind"] == "event_previous_hash_mismatch"
    assert "sequence 2" in integrity["message"]
    assert "previous_event_hash" in integrity["message"]


def test_verify_event_stream_rejects_sequence_gap(tmp_path):
    paths, _ = run_fake_loop(tmp_path)
    events = read_jsonl(paths.event_stream)
    del events[1]
    write_jsonl(paths.event_stream, events)

    integrity = verify_event_stream(paths.event_stream)

    assert integrity["ok"] is False
    assert integrity["failure_kind"] == "event_sequence_gap"
    assert "sequence" in integrity["message"]


def test_verify_event_stream_rejects_event_hash_mismatch(tmp_path):
    paths, _ = run_fake_loop(tmp_path)
    events = read_jsonl(paths.event_stream)
    events[1]["payload"]["provider_turn_id"] = "tampered_turn"
    write_jsonl(paths.event_stream, events)

    integrity = verify_event_stream(paths.event_stream)

    assert integrity["ok"] is False
    assert integrity["failure_kind"] == "event_hash_mismatch"
    assert "sequence 2" in integrity["message"]


def test_verify_event_stream_rejects_missing_terminal_event(tmp_path):
    paths, _ = run_fake_loop(tmp_path)
    events = relink_events(read_jsonl(paths.event_stream)[:-1])
    write_jsonl(paths.event_stream, events)

    integrity = verify_event_stream(paths.event_stream)

    assert integrity["ok"] is False
    assert integrity["failure_kind"] == "event_terminal_missing"
    assert "sequence" in integrity["message"]


def test_build_evidence_summary_rejects_events_hash_mismatch(tmp_path):
    paths, result = run_fake_loop(tmp_path)
    wrong_result = result.model_copy(update={"events_hash": "sha256:" + "0" * 64})

    with pytest.raises(EvidenceMappingError) as raised:
        build_evidence_summary(wrong_result, paths.event_stream)

    assert raised.value.failure_kind == "events_hash_mismatch"


def test_describe_replay_status_reports_missing_direct_payload_fields(tmp_path):
    paths, _ = run_fake_loop(tmp_path)
    events = read_jsonl(paths.event_stream)

    replay = describe_replay_status(events)

    assert replay == {
        "status": "not_replayable",
        "reasons": ["missing_invocation_snapshot", "missing_policy_snapshot", "missing_tool_versions"],
    }


def test_describe_replay_status_accepts_snapshot_ref_equivalent_fields(tmp_path):
    paths, _ = run_fake_loop(tmp_path)
    events = read_jsonl(paths.event_stream)
    events[0]["payload"]["invocation_snapshot_ref"] = artifact_payload("invocation")
    events[0]["payload"]["policy_snapshot"] = {"policy_ref": "policy://test"}

    replay = describe_replay_status(events)

    assert replay == {"status": "not_replayable", "reasons": ["missing_tool_versions"]}


def test_describe_replay_status_reports_replayable_when_direct_metadata_exists(tmp_path):
    paths, _ = run_fake_loop(tmp_path)
    events = read_jsonl(paths.event_stream)
    events[0]["payload"].update(
        {
            "invocation_snapshot": {"invocation_id": "inv_001"},
            "policy_snapshot_ref": artifact_payload("policy"),
            "tool_versions": {"atomic-agent": "0.0.0"},
        }
    )

    replay = describe_replay_status(events)

    assert replay == {"status": "replayable", "reasons": []}


def test_build_evidence_summary_maps_fake_loop_evidence(tmp_path):
    paths, result = run_fake_loop(tmp_path)

    summary = build_evidence_summary(result, paths.event_stream)

    assert summary["run_id"] == result.run_id
    assert summary["status"] == "completed"
    assert summary["event_stream"]["event_stream_ref"] == result.event_stream_ref
    assert summary["event_stream"]["events_hash"] == result.events_hash
    assert summary["event_stream"]["integrity"]["ok"] is True
    assert len(summary["provider_attempts"]) == 5
    assert [attempt["tool"] for attempt in summary["tool_attempts"]] == [
        "write_file",
        "run_command",
        "apply_patch",
        "run_command",
    ]
    assert [mutation["path"] for mutation in summary["workspace_mutations"]] == [
        WORKSPACE_OUTPUT_PATH,
        WORKSPACE_OUTPUT_PATH,
    ]
    assert all(mutation["after_hash"].startswith("sha256:") for mutation in summary["workspace_mutations"])
    assert all(mutation["diff"]["sha256"].startswith("sha256:") for mutation in summary["workspace_mutations"])
    assert [command["exit_code"] for command in summary["command_results"]] == [3, 0]
    assert all(command["stdout"]["sha256"].startswith("sha256:") for command in summary["command_results"])
    assert all(command["stderr"]["sha256"].startswith("sha256:") for command in summary["command_results"])
    assert summary["replay"] == {
        "status": "not_replayable",
        "reasons": ["missing_invocation_snapshot", "missing_policy_snapshot", "missing_tool_versions"],
    }

    lineage = summary["source_inventory_lineage"]
    assert len(lineage) == 1
    assert lineage[0]["path"] == WORKSPACE_OUTPUT_PATH
    assert lineage[0]["lineage_status"] == "traceable"
    assert lineage[0]["latest_after_hash"] == summary["workspace_mutations"][-1]["after_hash"]
    assert [mutation["tool"] for mutation in lineage[0]["mutation_refs"]] == ["write_file", "apply_patch"]
    assert len(lineage[0]["diff_artifact_refs"]) == 2
    assert_no_banned_governance_fields(summary)


def test_source_inventory_lineage_marks_missing_workspace_mutation(tmp_path):
    event_dir = tmp_path / "events"
    event_dir.mkdir()
    recorder = EventRecorder(
        run_id="missing_lineage",
        config=EventRecorderConfig(
            event_stream_path=event_dir / "events.jsonl",
            event_stream_ref="artifact://missing_lineage/events.jsonl",
        ),
        clock=fixed_clock,
    )
    recorder.record_run_started("inv_missing_lineage")
    recorder.record_provider_turn_started("provider_turn_000001")
    recorder.record_provider_turn_completed("provider_turn_000001", artifact_payload("provider-output"))
    recorder.record_action_parsed(
        {
            "action_id": "step-submit",
            "action": "submit_result",
            "reason_summary": "Submit a path without a workspace mutation.",
            "input": {
                "summary": "Submitted external path.",
                "produced_paths": ["work/missing.txt"],
                "evidence_refs": [],
            },
        }
    )
    recorder.record_permission_decided(
        "step-submit",
        "allow",
        "policy://test/missing-lineage",
        "submit_result allowed by invocation policy",
    )
    result_artifact = artifact_payload("result")
    recorder.record_result_submitted("Submitted external path.", ["work/missing.txt"], [result_artifact])
    recorder.record_run_completed("Submitted external path.")
    result = AgentRunResult(
        run_id="missing_lineage",
        status=AgentRunStatus.COMPLETED,
        event_stream_ref="artifact://missing_lineage/events.jsonl",
        events_hash=recorder.events_hash(),
        tool_attempts=[],
        workspace_mutations=[],
        artifacts=[result_artifact],
        summary="Submitted external path.",
    )

    summary = build_evidence_summary(result, event_dir / "events.jsonl")

    assert summary["source_inventory_lineage"] == [
        {
            "path": "work/missing.txt",
            "lineage_status": "missing_workspace_mutation",
            "latest_after_hash": None,
            "mutation_refs": [],
            "diff_artifact_refs": [],
        }
    ]


def test_source_inventory_lineage_preserves_three_mutations_in_event_order(tmp_path):
    paths, result = run_fake_loop(tmp_path)
    events = read_jsonl(paths.event_stream)
    first_mutation = next(event for event in events if event["type"] == "workspace.mutation.recorded")
    final_mutation = next(event for event in reversed(events) if event["type"] == "workspace.mutation.recorded")
    extra_mutation = json.loads(json.dumps(final_mutation))
    extra_mutation["payload"]["before_hash"] = final_mutation["payload"]["after_hash"]
    extra_mutation["payload"]["after_hash"] = "sha256:" + "9" * 64
    events.insert(events.index(final_mutation) + 1, extra_mutation)
    events = relink_events(events)
    write_jsonl(paths.event_stream, events)
    updated_result = result.model_copy(update={"events_hash": sha256_bytes(paths.event_stream.read_bytes())})

    summary = build_evidence_summary(updated_result, paths.event_stream)

    lineage = summary["source_inventory_lineage"][0]
    assert lineage["lineage_status"] == "traceable"
    assert [mutation["after_hash"] for mutation in lineage["mutation_refs"]] == [
        first_mutation["payload"]["after_hash"],
        final_mutation["payload"]["after_hash"],
        "sha256:" + "9" * 64,
    ]
    assert lineage["latest_after_hash"] == "sha256:" + "9" * 64


def test_source_inventory_lineage_rejects_broken_workspace_mutation_hash_chain(tmp_path):
    paths, result = run_fake_loop(tmp_path)
    events = read_jsonl(paths.event_stream)
    second_mutation = [event for event in events if event["type"] == "workspace.mutation.recorded"][1]
    second_mutation["payload"]["before_hash"] = "sha256:" + "8" * 64
    events = relink_events(events)
    write_jsonl(paths.event_stream, events)
    updated_result = result.model_copy(update={"events_hash": sha256_bytes(paths.event_stream.read_bytes())})

    with pytest.raises(EvidenceMappingError) as raised:
        build_evidence_summary(updated_result, paths.event_stream)

    assert raised.value.failure_kind == "workspace_mutation_hash_chain_mismatch"
    assert WORKSPACE_OUTPUT_PATH in raised.value.message
