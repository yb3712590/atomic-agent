from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any

from pydantic import ValidationError

from atomic_agent.models import AgentEvent, AgentRunResult


_SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_TERMINAL_EVENT_TYPES = {"run.completed", "run.failed"}
_BANNED_GOVERNANCE_FIELDS = {
    "ticket_completed",
    "closeout_committed",
    "governance_status",
    "evidence_verified",
    "source_inventory_accepted",
}


class EvidenceMappingError(RuntimeError):
    def __init__(self, failure_kind: str, message: str):
        super().__init__(message)
        self.failure_kind = failure_kind
        self.message = message


def verify_event_stream(event_stream_path: Path, expected_events_hash: str | None = None) -> dict[str, Any]:
    loaded = _load_events(event_stream_path)
    if not loaded["ok"]:
        return loaded
    raw = loaded["raw"]
    events = loaded["events"]
    previous_hash: str | None = None
    for expected_sequence, event in enumerate(events, start=1):
        schema_error = _validate_event_schema(event)
        if schema_error is not None:
            return schema_error
        sequence = event["sequence"]
        event_id = event["event_id"]
        if sequence != expected_sequence:
            return _failure(
                "event_sequence_gap",
                f"event sequence gap at event_id {event_id}: expected sequence {expected_sequence}, got {sequence}",
            )
        if event["previous_event_hash"] != previous_hash:
            return _failure(
                "event_previous_hash_mismatch",
                f"event sequence {sequence} ({event_id}) previous_event_hash does not match the previous event hash",
            )
        recalculated_hash = _hash_event_without_event_hash(event)
        if event["event_hash"] != recalculated_hash:
            return _failure(
                "event_hash_mismatch",
                f"event sequence {sequence} ({event_id}) event_hash does not match canonical event hash",
            )
        previous_hash = event["event_hash"]

    terminal_event_type = events[-1]["type"]
    if terminal_event_type not in _TERMINAL_EVENT_TYPES:
        return _failure(
            "event_terminal_missing",
            f"event stream must end with run.completed or run.failed; last sequence {events[-1]['sequence']} has {terminal_event_type}",
        )

    events_hash = _sha256(raw)
    if expected_events_hash is not None and events_hash != expected_events_hash:
        return _failure(
            "events_hash_mismatch",
            "event stream bytes hash does not match AgentRunResult.events_hash",
        )

    return {
        "ok": True,
        "event_count": len(events),
        "terminal_event_type": terminal_event_type,
        "events_hash": events_hash,
    }


def build_evidence_summary(result: AgentRunResult, event_stream_path: Path) -> dict[str, Any]:
    if not isinstance(result, AgentRunResult):
        raise EvidenceMappingError("invalid_result", "build_evidence_summary requires AgentRunResult")
    integrity = verify_event_stream(event_stream_path, expected_events_hash=result.events_hash)
    if not integrity["ok"]:
        raise EvidenceMappingError(integrity["failure_kind"], integrity["message"])
    loaded = _load_events(event_stream_path)
    if not loaded["ok"]:
        raise EvidenceMappingError(loaded["failure_kind"], loaded["message"])
    events = loaded["events"]
    context = _build_mapping_context(events)
    _validate_workspace_mutation_hash_chains(context["workspace_mutations"])
    source_inventory_lineage = _build_source_inventory_lineage(
        produced_paths=_submitted_produced_paths(events),
        workspace_mutations=context["workspace_mutations"],
    )
    summary = {
        "run_id": result.run_id,
        "status": result.status.value,
        "event_stream": {
            "event_stream_ref": result.event_stream_ref,
            "events_hash": result.events_hash,
            "integrity": integrity,
        },
        "provider_attempts": context["provider_attempts"],
        "tool_attempts": context["tool_attempts"],
        "workspace_mutations": context["workspace_mutations"],
        "command_results": context["command_results"],
        "network_fetches": context["network_fetches"],
        "source_inventory_lineage": source_inventory_lineage,
        "artifacts": result.artifacts,
        "replay": describe_replay_status(events),
    }
    _assert_no_governance_fields(summary)
    return summary


def describe_replay_status(events: list[dict[str, Any]]) -> dict[str, Any]:
    run_started_payload = events[0].get("payload", {}) if events else {}
    reasons: list[str] = []
    if not _has_any_key(run_started_payload, ("invocation_snapshot", "invocation_snapshot_ref")):
        reasons.append("missing_invocation_snapshot")
    if not _has_any_key(run_started_payload, ("policy_snapshot", "policy_snapshot_ref")):
        reasons.append("missing_policy_snapshot")
    if not _has_any_key(run_started_payload, ("tool_versions", "tool_versions_ref")):
        reasons.append("missing_tool_versions")
    if reasons:
        return {"status": "not_replayable", "reasons": reasons}
    return {"status": "replayable", "reasons": []}


def _load_events(event_stream_path: Path) -> dict[str, Any]:
    if not isinstance(event_stream_path, Path):
        return _failure("event_stream_path_invalid", "event_stream_path must be a Path")
    if not event_stream_path.exists():
        return _failure("event_stream_missing", f"event stream path does not exist: {event_stream_path}")
    if event_stream_path.is_dir():
        return _failure("event_stream_unreadable", f"event stream path must be a file: {event_stream_path}")
    try:
        raw = event_stream_path.read_bytes()
    except OSError as error:
        return _failure("event_stream_unreadable", f"failed to read event stream {event_stream_path}: {error}")
    if not raw:
        return _failure("event_stream_empty", f"event stream is empty: {event_stream_path}")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        return _failure("event_stream_unreadable", f"event stream is not UTF-8 at {event_stream_path}: {error}")
    events: list[dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            return _failure("event_json_invalid", f"event stream line {line_number} is empty")
        try:
            event = json.loads(line)
        except json.JSONDecodeError as error:
            return _failure("event_json_invalid", f"event stream line {line_number} is invalid JSON: {error}")
        if not isinstance(event, dict):
            return _failure("event_schema_invalid", f"event stream line {line_number} must be a JSON object")
        events.append(event)
    if not events:
        return _failure("event_stream_empty", f"event stream contains no events: {event_stream_path}")
    return {"ok": True, "raw": raw, "events": events}


def _validate_event_schema(event: dict[str, Any]) -> dict[str, Any] | None:
    try:
        AgentEvent(**event)
    except ValidationError as error:
        event_id = event.get("event_id", "<missing>")
        sequence = event.get("sequence", "<missing>")
        return _failure("event_schema_invalid", f"invalid AgentEvent schema at sequence {sequence} ({event_id}): {error}")
    if not _is_sha256(event.get("event_hash")):
        return _failure("event_schema_invalid", f"event_hash must use sha256:<64 lowercase hex chars at sequence {event.get('sequence')}")
    previous_event_hash = event.get("previous_event_hash")
    if previous_event_hash is not None and not _is_sha256(previous_event_hash):
        return _failure(
            "event_schema_invalid",
            f"previous_event_hash must be null or sha256:<64 lowercase hex chars at sequence {event.get('sequence')}",
        )
    return None


def _build_mapping_context(events: list[dict[str, Any]]) -> dict[str, Any]:
    current_provider_turn_id: str | None = None
    action_to_provider_turn: dict[str, str | None] = {}
    tool_attempts_by_id: dict[str, dict[str, Any]] = {}
    tool_attempt_order: list[str] = []
    provider_attempts: list[dict[str, Any]] = []
    workspace_mutations: list[dict[str, Any]] = []
    command_results: list[dict[str, Any]] = []
    network_fetches: list[dict[str, Any]] = []

    for event in events:
        event_type = event["type"]
        payload = event["payload"]
        if event_type == "provider.turn.started":
            current_provider_turn_id = payload["provider_turn_id"]
        elif event_type == "provider.turn.completed":
            _validate_artifact_payload(payload["output"], "provider output")
            provider_attempts.append(
                {
                    "event_id": event["event_id"],
                    "provider_turn_id": payload["provider_turn_id"],
                    "output": payload["output"],
                }
            )
        elif event_type == "action.parsed":
            action = payload["action"]
            action_id = action.get("action_id")
            if isinstance(action_id, str) and action_id:
                action_to_provider_turn[action_id] = current_provider_turn_id
        elif event_type == "tool.attempt.started":
            tool_attempt_id = payload["tool_attempt_id"]
            action_id = payload["action_id"]
            tool_attempts_by_id[tool_attempt_id] = {
                "event_id": event["event_id"],
                "tool_attempt_id": tool_attempt_id,
                "action_id": action_id,
                "tool": payload["tool"],
                "provider_turn_id": action_to_provider_turn.get(action_id),
                "status": "started",
            }
            tool_attempt_order.append(tool_attempt_id)
        elif event_type == "tool.attempt.completed":
            tool_attempt = _require_tool_attempt(tool_attempts_by_id, payload["tool_attempt_id"])
            _validate_artifact_payload(payload["observation"], "tool observation")
            tool_attempt.update(
                {
                    "status": "completed",
                    "completed_event_id": event["event_id"],
                    "observation": payload["observation"],
                }
            )
        elif event_type == "tool.attempt.failed":
            tool_attempt = _require_tool_attempt(tool_attempts_by_id, payload["tool_attempt_id"])
            tool_attempt.update(
                {
                    "status": "failed",
                    "failed_event_id": event["event_id"],
                    "error": payload["error"],
                }
            )
        elif event_type == "workspace.mutation.recorded":
            tool_attempt = _require_tool_attempt(tool_attempts_by_id, payload["tool_attempt_id"])
            _validate_optional_sha256(payload["before_hash"], "before_hash")
            _validate_sha256(payload["after_hash"], "after_hash")
            _validate_artifact_payload(payload["diff"], "workspace mutation diff")
            workspace_mutations.append(
                {
                    "event_id": event["event_id"],
                    "tool_attempt_id": payload["tool_attempt_id"],
                    "action_id": tool_attempt["action_id"],
                    "tool": tool_attempt["tool"],
                    "provider_turn_id": tool_attempt["provider_turn_id"],
                    "path": payload["path"],
                    "before_hash": payload["before_hash"],
                    "after_hash": payload["after_hash"],
                    "diff": payload["diff"],
                }
            )
        elif event_type == "command.completed":
            tool_attempt = _require_tool_attempt(tool_attempts_by_id, payload["tool_attempt_id"])
            _validate_artifact_payload(payload["stdout"], "command stdout")
            _validate_artifact_payload(payload["stderr"], "command stderr")
            command_results.append(
                {
                    "event_id": event["event_id"],
                    "tool_attempt_id": payload["tool_attempt_id"],
                    "action_id": tool_attempt["action_id"],
                    "tool": tool_attempt["tool"],
                    "provider_turn_id": tool_attempt["provider_turn_id"],
                    "command_id": payload["command_id"],
                    "exit_code": payload["exit_code"],
                    "stdout": payload["stdout"],
                    "stderr": payload["stderr"],
                }
            )
        elif event_type == "network.fetch.completed":
            tool_attempt = _require_tool_attempt(tool_attempts_by_id, payload["tool_attempt_id"])
            _validate_artifact_payload(payload["response"], "network response")
            network_fetches.append(
                {
                    "event_id": event["event_id"],
                    "tool_attempt_id": payload["tool_attempt_id"],
                    "action_id": tool_attempt["action_id"],
                    "tool": tool_attempt["tool"],
                    "provider_turn_id": tool_attempt["provider_turn_id"],
                    "url": payload["url"],
                    "status_code": payload["status_code"],
                    "response": payload["response"],
                }
            )

    return {
        "provider_attempts": provider_attempts,
        "tool_attempts": [tool_attempts_by_id[tool_attempt_id] for tool_attempt_id in tool_attempt_order],
        "workspace_mutations": workspace_mutations,
        "command_results": command_results,
        "network_fetches": network_fetches,
    }


def _submitted_produced_paths(events: list[dict[str, Any]]) -> list[str]:
    produced_paths: list[str] = []
    for event in events:
        if event["type"] == "result.submitted":
            produced_paths = list(event["payload"].get("produced_paths", []))
    return produced_paths


def _validate_workspace_mutation_hash_chains(workspace_mutations: list[dict[str, Any]]) -> None:
    latest_after_hash_by_path: dict[str, str] = {}
    for mutation in workspace_mutations:
        path = mutation["path"]
        previous_after_hash = latest_after_hash_by_path.get(path)
        if previous_after_hash is not None and mutation["before_hash"] != previous_after_hash:
            raise EvidenceMappingError(
                "workspace_mutation_hash_chain_mismatch",
                f"workspace mutation hash chain mismatch for {path} at event {mutation['event_id']}: "
                f"before_hash does not match previous after_hash",
            )
        latest_after_hash_by_path[path] = mutation["after_hash"]


def _build_source_inventory_lineage(
    produced_paths: list[str],
    workspace_mutations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    lineage: list[dict[str, Any]] = []
    for path in produced_paths:
        mutation_refs = [mutation for mutation in workspace_mutations if mutation["path"] == path]
        if not mutation_refs:
            lineage.append(
                {
                    "path": path,
                    "lineage_status": "missing_workspace_mutation",
                    "latest_after_hash": None,
                    "mutation_refs": [],
                    "diff_artifact_refs": [],
                }
            )
            continue
        lineage.append(
            {
                "path": path,
                "lineage_status": "traceable",
                "latest_after_hash": mutation_refs[-1]["after_hash"],
                "mutation_refs": mutation_refs,
                "diff_artifact_refs": [mutation["diff"] for mutation in mutation_refs],
            }
        )
    return lineage


def _require_tool_attempt(tool_attempts_by_id: dict[str, dict[str, Any]], tool_attempt_id: str) -> dict[str, Any]:
    tool_attempt = tool_attempts_by_id.get(tool_attempt_id)
    if tool_attempt is None:
        raise EvidenceMappingError(
            "tool_attempt_missing_start",
            f"event references tool_attempt_id without a started tool attempt: {tool_attempt_id}",
        )
    return tool_attempt


def _validate_artifact_payload(payload: object, label: str) -> None:
    if not isinstance(payload, dict):
        raise EvidenceMappingError("artifact_payload_invalid", f"{label} artifact payload must be a dict")
    required = ("artifact_ref", "sha256", "size_bytes", "truncated_in_observation")
    missing = [field for field in required if field not in payload]
    if missing:
        raise EvidenceMappingError(
            "artifact_payload_invalid",
            f"{label} artifact payload missing required fields: {', '.join(missing)}",
        )
    if not isinstance(payload["artifact_ref"], str) or payload["artifact_ref"] == "":
        raise EvidenceMappingError("artifact_payload_invalid", f"{label} artifact_ref must be a non-empty string")
    _validate_sha256(payload["sha256"], f"{label} sha256")
    if not isinstance(payload["size_bytes"], int) or isinstance(payload["size_bytes"], bool) or payload["size_bytes"] < 0:
        raise EvidenceMappingError("artifact_payload_invalid", f"{label} size_bytes must be a non-negative integer")
    if not isinstance(payload["truncated_in_observation"], bool):
        raise EvidenceMappingError("artifact_payload_invalid", f"{label} truncated_in_observation must be a boolean")


def _validate_optional_sha256(value: object, label: str) -> None:
    if value is None:
        return
    _validate_sha256(value, label)


def _validate_sha256(value: object, label: str) -> None:
    if not _is_sha256(value):
        raise EvidenceMappingError("sha256_invalid", f"{label} must use sha256:<64 lowercase hex chars")


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and _SHA256_PATTERN.fullmatch(value) is not None


def _hash_event_without_event_hash(event: dict[str, Any]) -> str:
    event_without_hash = dict(event)
    event_without_hash.pop("event_hash", None)
    canonical = json.dumps(event_without_hash, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return _sha256(canonical.encode("utf-8"))


def _sha256(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()


def _failure(failure_kind: str, message: str) -> dict[str, Any]:
    return {"ok": False, "failure_kind": failure_kind, "message": message}


def _has_any_key(payload: dict[str, Any], keys: tuple[str, ...]) -> bool:
    return any(key in payload for key in keys)


def _assert_no_governance_fields(value: object) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in _BANNED_GOVERNANCE_FIELDS:
                raise EvidenceMappingError("governance_field_forbidden", f"forbidden governance field in evidence summary: {key}")
            _assert_no_governance_fields(child)
    elif isinstance(value, list):
        for child in value:
            _assert_no_governance_fields(child)
