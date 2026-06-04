from collections.abc import Callable
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from atomic_agent.models import AgentEvent, AgentEventType


EVENT_PROTOCOL_VERSION = 1
_SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")


_REQUIRED_PAYLOAD_FIELDS: dict[AgentEventType, set[str]] = {
    AgentEventType.RUN_STARTED: {"event_protocol_version", "invocation_id"},
    AgentEventType.RUN_COMPLETED: {"summary"},
    AgentEventType.RUN_FAILED: {"error"},
    AgentEventType.PROVIDER_TURN_STARTED: {"provider_turn_id"},
    AgentEventType.PROVIDER_TURN_COMPLETED: {"provider_turn_id", "output"},
    AgentEventType.PROVIDER_TURN_FAILED: {"provider_turn_id", "error"},
    AgentEventType.ACTION_PARSED: {"action"},
    AgentEventType.ACTION_REJECTED: {"error"},
    AgentEventType.PERMISSION_DECIDED: {"action_id", "decision", "policy_ref", "reason"},
    AgentEventType.TOOL_ATTEMPT_STARTED: {"tool_attempt_id", "action_id", "tool"},
    AgentEventType.TOOL_ATTEMPT_COMPLETED: {"tool_attempt_id", "action_id", "tool", "observation"},
    AgentEventType.TOOL_ATTEMPT_FAILED: {"tool_attempt_id", "action_id", "tool", "error"},
    AgentEventType.WORKSPACE_MUTATION_RECORDED: {"tool_attempt_id", "path", "before_hash", "after_hash", "diff"},
    AgentEventType.COMMAND_COMPLETED: {"tool_attempt_id", "command_id", "exit_code", "stdout", "stderr"},
    AgentEventType.NETWORK_FETCH_COMPLETED: {"tool_attempt_id", "url", "status_code", "response"},
    AgentEventType.RESULT_SUBMITTED: {"summary", "produced_paths", "artifact_refs"},
}


@dataclass(frozen=True)
class EventRecorderConfig:
    event_stream_path: Path
    event_stream_ref: str


class EventRecorderError(RuntimeError):
    pass


class EventRecorderConfigError(ValueError):
    pass


@dataclass(frozen=True)
class ArtifactReference:
    artifact_ref: str
    sha256: str
    size_bytes: int
    truncated_in_observation: bool

    def to_payload(self) -> dict[str, Any]:
        if not isinstance(self.artifact_ref, str) or self.artifact_ref == "":
            raise ValueError("artifact_ref must be a non-empty string")
        if not isinstance(self.sha256, str) or not _SHA256_PATTERN.fullmatch(self.sha256):
            raise ValueError("sha256 must use sha256:<64 lowercase hex chars>")
        if not isinstance(self.size_bytes, int) or isinstance(self.size_bytes, bool) or self.size_bytes < 0:
            raise ValueError("size_bytes must be a non-negative integer")
        if not isinstance(self.truncated_in_observation, bool):
            raise ValueError("truncated_in_observation must be a boolean")
        return {
            "artifact_ref": self.artifact_ref,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "truncated_in_observation": self.truncated_in_observation,
        }


@dataclass(frozen=True)
class EventError:
    kind: str
    message: str
    retryable: bool
    related_ref: str | None = None

    def to_payload(self) -> dict[str, Any]:
        if not isinstance(self.kind, str) or self.kind == "":
            raise ValueError("error kind must be a non-empty string")
        if not isinstance(self.message, str) or self.message == "":
            raise ValueError("error message must be a non-empty string")
        if not isinstance(self.retryable, bool):
            raise ValueError("retryable must be a boolean")
        if self.related_ref is not None and not isinstance(self.related_ref, str):
            raise ValueError("related_ref must be a string or None")
        return {
            "kind": self.kind,
            "message": self.message,
            "retryable": self.retryable,
            "related_ref": self.related_ref,
        }


class EventRecorder:
    def __init__(self, run_id: str, config: EventRecorderConfig, clock: Callable[[], str]):
        self.run_id = run_id
        self.config = config
        self.clock = clock
        self._sequence = 0
        self._previous_event_hash: str | None = None
        self._terminal_recorded = False
        self._tool_attempt_ids: set[str] = set()
        self._validate_config()

    @property
    def event_stream_ref(self) -> str:
        return self.config.event_stream_ref

    def record_run_started(self, invocation_id: str) -> AgentEvent:
        return self.record(
            AgentEventType.RUN_STARTED,
            {"event_protocol_version": EVENT_PROTOCOL_VERSION, "invocation_id": invocation_id},
        )

    def record_provider_turn_started(self, provider_turn_id: str) -> AgentEvent:
        return self.record(AgentEventType.PROVIDER_TURN_STARTED, {"provider_turn_id": provider_turn_id})

    def record_run_completed(self, summary: str) -> AgentEvent:
        return self.record(AgentEventType.RUN_COMPLETED, {"summary": summary})

    def record_run_failed(self, error: dict[str, Any]) -> AgentEvent:
        return self.record(AgentEventType.RUN_FAILED, {"error": error})

    def record_provider_turn_completed(self, provider_turn_id: str, output: dict[str, Any]) -> AgentEvent:
        return self.record(
            AgentEventType.PROVIDER_TURN_COMPLETED,
            {"provider_turn_id": provider_turn_id, "output": output},
        )

    def record_provider_turn_failed(self, provider_turn_id: str, error: dict[str, Any]) -> AgentEvent:
        return self.record(
            AgentEventType.PROVIDER_TURN_FAILED,
            {"provider_turn_id": provider_turn_id, "error": error},
        )

    def record_action_parsed(self, action: dict[str, Any]) -> AgentEvent:
        return self.record(AgentEventType.ACTION_PARSED, {"action": action})

    def record_action_rejected(self, error: dict[str, Any]) -> AgentEvent:
        return self.record(AgentEventType.ACTION_REJECTED, {"error": error})

    def record_permission_decided(self, action_id: str, decision: str, policy_ref: str, reason: str) -> AgentEvent:
        return self.record(
            AgentEventType.PERMISSION_DECIDED,
            {"action_id": action_id, "decision": decision, "policy_ref": policy_ref, "reason": reason},
        )

    def record_tool_attempt_started(self, tool_attempt_id: str, action_id: str, tool: str) -> AgentEvent:
        return self.record(
            AgentEventType.TOOL_ATTEMPT_STARTED,
            {"tool_attempt_id": tool_attempt_id, "action_id": action_id, "tool": tool},
        )

    def record_tool_attempt_completed(
        self,
        tool_attempt_id: str,
        action_id: str,
        tool: str,
        observation: dict[str, Any],
    ) -> AgentEvent:
        return self.record(
            AgentEventType.TOOL_ATTEMPT_COMPLETED,
            {"tool_attempt_id": tool_attempt_id, "action_id": action_id, "tool": tool, "observation": observation},
        )

    def record_tool_attempt_failed(
        self,
        tool_attempt_id: str,
        action_id: str,
        tool: str,
        error: dict[str, Any],
    ) -> AgentEvent:
        return self.record(
            AgentEventType.TOOL_ATTEMPT_FAILED,
            {"tool_attempt_id": tool_attempt_id, "action_id": action_id, "tool": tool, "error": error},
        )

    def record_workspace_mutation_recorded(
        self,
        tool_attempt_id: str,
        path: str,
        before_hash: str | None,
        after_hash: str,
        diff: dict[str, Any],
    ) -> AgentEvent:
        return self.record(
            AgentEventType.WORKSPACE_MUTATION_RECORDED,
            {
                "tool_attempt_id": tool_attempt_id,
                "path": path,
                "before_hash": before_hash,
                "after_hash": after_hash,
                "diff": diff,
            },
        )

    def record_command_completed(
        self,
        tool_attempt_id: str,
        command_id: str,
        exit_code: int,
        stdout: dict[str, Any],
        stderr: dict[str, Any],
    ) -> AgentEvent:
        return self.record(
            AgentEventType.COMMAND_COMPLETED,
            {
                "tool_attempt_id": tool_attempt_id,
                "command_id": command_id,
                "exit_code": exit_code,
                "stdout": stdout,
                "stderr": stderr,
            },
        )

    def record_network_fetch_completed(
        self,
        tool_attempt_id: str,
        url: str,
        status_code: int,
        response: dict[str, Any],
    ) -> AgentEvent:
        return self.record(
            AgentEventType.NETWORK_FETCH_COMPLETED,
            {"tool_attempt_id": tool_attempt_id, "url": url, "status_code": status_code, "response": response},
        )

    def record_result_submitted(
        self,
        summary: str,
        produced_paths: list[str],
        artifact_refs: list[dict[str, Any]],
    ) -> AgentEvent:
        return self.record(
            AgentEventType.RESULT_SUBMITTED,
            {"summary": summary, "produced_paths": produced_paths, "artifact_refs": artifact_refs},
        )

    def record(self, event_type: AgentEventType, payload: dict[str, Any]) -> AgentEvent:
        self._validate_ordering(event_type, payload)
        self._validate_payload(event_type, payload)
        timestamp = self.clock()
        if not isinstance(timestamp, str) or timestamp == "":
            raise EventRecorderError("clock must return a non-empty timestamp string")

        sequence = self._sequence + 1
        event_without_hash = {
            "event_id": self._event_id(sequence),
            "run_id": self.run_id,
            "sequence": sequence,
            "type": event_type.value,
            "timestamp": timestamp,
            "payload": payload,
            "previous_event_hash": self._previous_event_hash,
        }
        event_hash = self._hash_event(event_without_hash)
        event = AgentEvent(**event_without_hash, event_hash=event_hash)
        line = self._serialize_event(event)
        try:
            with self.config.event_stream_path.open("a", encoding="utf-8") as stream:
                stream.write(line)
                stream.write("\n")
        except OSError as error:
            raise EventRecorderError(f"failed to write event {event_type.value}: {error}") from error

        self._sequence = sequence
        self._previous_event_hash = event_hash
        self._update_ordering_state(event)
        return event

    def events_hash(self) -> str:
        try:
            content = self.config.event_stream_path.read_bytes()
        except OSError as error:
            raise EventRecorderError(f"failed to read event stream: {error}") from error
        if not content:
            raise EventRecorderError("event stream is empty or missing")
        return f"sha256:{hashlib.sha256(content).hexdigest()}"

    def _validate_ordering(self, event_type: AgentEventType, payload: dict[str, Any]) -> None:
        if self._terminal_recorded:
            raise EventRecorderError("cannot record events after terminal event")
        if self._sequence == 0 and event_type != AgentEventType.RUN_STARTED:
            raise EventRecorderError("run.started must be the first event")
        if event_type == AgentEventType.TOOL_ATTEMPT_STARTED:
            tool_attempt_id = payload.get("tool_attempt_id")
            if tool_attempt_id in self._tool_attempt_ids:
                raise EventRecorderError("tool_attempt_id has already been started")
        if event_type in {
            AgentEventType.TOOL_ATTEMPT_COMPLETED,
            AgentEventType.TOOL_ATTEMPT_FAILED,
            AgentEventType.WORKSPACE_MUTATION_RECORDED,
            AgentEventType.COMMAND_COMPLETED,
            AgentEventType.NETWORK_FETCH_COMPLETED,
        }:
            self._require_started_tool_attempt(payload)

    def _update_ordering_state(self, event: AgentEvent) -> None:
        if event.type == AgentEventType.TOOL_ATTEMPT_STARTED:
            self._tool_attempt_ids.add(event.payload["tool_attempt_id"])
        if event.type in {AgentEventType.RUN_COMPLETED, AgentEventType.RUN_FAILED}:
            self._terminal_recorded = True

    def _require_started_tool_attempt(self, payload: dict[str, Any]) -> None:
        tool_attempt_id = payload.get("tool_attempt_id")
        if tool_attempt_id not in self._tool_attempt_ids:
            raise EventRecorderError("tool_attempt_id must reference a started tool attempt")

    def _validate_payload(self, event_type: AgentEventType, payload: dict[str, Any]) -> None:
        if not isinstance(payload, dict):
            raise EventRecorderError("event payload must be a dict")
        required = _REQUIRED_PAYLOAD_FIELDS.get(event_type, set())
        missing = [field for field in sorted(required) if field not in payload]
        if missing:
            raise EventRecorderError(f"{event_type.value} missing required payload fields: {', '.join(missing)}")

        if "error" in payload:
            self._validate_error_payload(payload["error"])
        for field_name in ("output", "observation", "diff", "stdout", "stderr", "response"):
            if field_name in payload:
                self._validate_artifact_payload(payload[field_name], field_name)
        if event_type == AgentEventType.WORKSPACE_MUTATION_RECORDED:
            if payload["before_hash"] is not None:
                self._validate_sha256(payload["before_hash"], "before_hash")
            self._validate_sha256(payload["after_hash"], "after_hash")
        if event_type == AgentEventType.COMMAND_COMPLETED:
            if not isinstance(payload["command_id"], str) or payload["command_id"] == "":
                raise EventRecorderError("command.completed command_id must be a non-empty string")
            if not isinstance(payload["exit_code"], int) or isinstance(payload["exit_code"], bool):
                raise EventRecorderError("command.completed exit_code must be an integer")
        if event_type == AgentEventType.RESULT_SUBMITTED:
            self._validate_result_submission(payload)

    def _validate_error_payload(self, payload: object) -> None:
        if not isinstance(payload, dict):
            raise EventRecorderError("error payload must be a dict")
        missing = [field for field in ("kind", "message", "retryable", "related_ref") if field not in payload]
        if missing:
            raise EventRecorderError(f"error payload missing required fields: {', '.join(missing)}")
        try:
            EventError(
                kind=payload["kind"],
                message=payload["message"],
                retryable=payload["retryable"],
                related_ref=payload["related_ref"],
            ).to_payload()
        except ValueError as error:
            raise EventRecorderError(f"invalid error payload: {error}") from error

    def _validate_artifact_payload(self, payload: object, field_name: str) -> None:
        if not isinstance(payload, dict):
            raise EventRecorderError(f"{field_name} artifact payload must be a dict")
        missing = [
            field
            for field in ("artifact_ref", "sha256", "size_bytes", "truncated_in_observation")
            if field not in payload
        ]
        if missing:
            raise EventRecorderError(f"{field_name} artifact payload missing required fields: {', '.join(missing)}")
        try:
            ArtifactReference(
                artifact_ref=payload["artifact_ref"],
                sha256=payload["sha256"],
                size_bytes=payload["size_bytes"],
                truncated_in_observation=payload["truncated_in_observation"],
            ).to_payload()
        except ValueError as error:
            raise EventRecorderError(f"invalid {field_name} artifact payload: {error}") from error

    def _validate_sha256(self, value: object, field_name: str) -> None:
        if not isinstance(value, str) or not _SHA256_PATTERN.fullmatch(value):
            raise EventRecorderError(f"{field_name} must use sha256:<64 lowercase hex chars>")

    def _validate_result_submission(self, payload: dict[str, Any]) -> None:
        summary = payload["summary"]
        if not isinstance(summary, str) or summary == "":
            raise EventRecorderError("result.submitted summary must be a non-empty string")
        produced_paths = payload["produced_paths"]
        if not isinstance(produced_paths, list) or any(not isinstance(path, str) for path in produced_paths):
            raise EventRecorderError("result.submitted produced_paths must be a list of strings")
        artifact_refs = payload["artifact_refs"]
        if not isinstance(artifact_refs, list):
            raise EventRecorderError("result.submitted artifact_refs must be a list")
        for artifact_ref in artifact_refs:
            self._validate_artifact_payload(artifact_ref, "artifact_refs")

    def _event_id(self, sequence: int) -> str:
        return f"evt_{sequence:06d}"

    def _hash_event(self, event_without_hash: dict[str, Any]) -> str:
        canonical = json.dumps(event_without_hash, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"

    def _serialize_event(self, event: AgentEvent) -> str:
        return json.dumps(event.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    def _validate_config(self) -> None:
        if not isinstance(self.run_id, str) or self.run_id == "":
            raise EventRecorderConfigError("run_id must be a non-empty string")
        if not isinstance(self.config.event_stream_path, Path):
            raise EventRecorderConfigError("event_stream_path must be a Path")
        if not isinstance(self.config.event_stream_ref, str) or self.config.event_stream_ref == "":
            raise EventRecorderConfigError("event_stream_ref must be a non-empty string")
        parent = self.config.event_stream_path.parent
        if not parent.exists():
            raise EventRecorderConfigError("event stream parent directory must exist")
        if self.config.event_stream_path.exists() and self.config.event_stream_path.is_dir():
            raise EventRecorderConfigError("event_stream_path must not be a directory")
        if self.config.event_stream_path.exists() and self.config.event_stream_path.stat().st_size > 0:
            raise EventRecorderConfigError("event stream path must be empty or absent")
