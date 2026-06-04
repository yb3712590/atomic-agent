# Event Recorder and JSONL Event Stream Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement P0-006 `event recorder`（事件记录器） and JSONL event stream（JSONL 事件流） so runtime events are append-only（只追加）, ordered（有序）, hash chained（哈希链化）, and usable by `AgentRunResult`（智能体运行结果）.

**Architecture:** Add a focused `event_recorder`（事件记录器） module that owns event sequence（事件序号）, deterministic event id（确定性事件标识）, timestamp injection（时间戳注入）, payload validation（载荷校验）, hash chain（哈希链）, JSONL writes（JSONL 写入）, and event stream hash（事件流哈希）. The module reuses existing `AgentEvent`（智能体事件） and `AgentEventType`（智能体事件类型） models; it does not execute tools, call providers, implement AgentLoop（智能体循环）, or create artifacts（产物）.

**Tech Stack:** Python 3.11+, `dataclasses`（轻量数据结构）, `pathlib`（路径处理）, `json`（JSON 序列化）, `hashlib`（哈希）, pytest（测试）, pydantic models（Pydantic 模型） already in `atomic_agent.models`.

**Status:** implemented

---

## Scope

This plan implements P0-006 only.

In scope:

- Create `src/atomic_agent/event_recorder.py`（事件记录器模块）.
- Create `tests/test_event_recorder.py`（事件记录器测试）.
- Implement `EventRecorderConfig`（事件记录器配置）, `EventRecorderError`（事件记录器错误）, `EventRecorderConfigError`（事件记录器配置错误）, `ArtifactReference`（产物引用）, `EventError`（事件错误载荷）, and `EventRecorder`（事件记录器）.
- Reuse `AgentEvent`（智能体事件） and `AgentEventType`（智能体事件类型） from `src/atomic_agent/models.py`.
- Write one JSON object（JSON 对象） per line to a configured JSONL path.
- Compute `event_hash`（事件哈希）, `previous_event_hash`（前序事件哈希）, and `events_hash`（事件流哈希） using real SHA-256.
- Validate required payload fields（必填载荷字段） before writing.
- Enforce basic ordering rules（顺序规则） for `run.started`, terminal events（终止事件）, tool attempt lifecycle（工具调用尝试生命周期）, workspace mutation（工作区变更）, command completed（命令完成）, and result submitted（结果提交）.
- Provide helper methods for all required event types in `docs/03-contracts/event-stream-protocol.md`（事件流协议）.
- Allow `AgentRunResult`（智能体运行结果） to consume recorder-provided `event_stream_ref` and `events_hash`.

Out of scope:

- No AgentLoop（智能体循环）.
- No provider adapter（模型供应商适配器）.
- No filesystem/command tool semantic changes（文件系统/命令工具语义变更）.
- No artifact store（产物存储） implementation.
- No web_fetch（网络获取） or NetworkPolicy（网络策略）.
- No event replay executor（事件重放执行器）.
- No secret scanner（密钥扫描器）.
- No Boardroom governance completion（Boardroom 治理完成） events.
- No commit unless the user explicitly requests it.

## File Structure

- Create: `src/atomic_agent/event_recorder.py`
  - Defines `EVENT_PROTOCOL_VERSION`（事件协议版本）, `EventRecorderConfig`（事件记录器配置）, `EventRecorderError`（事件记录器错误）, `EventRecorderConfigError`（事件记录器配置错误）, `ArtifactReference`（产物引用）, `EventError`（事件错误载荷）, and `EventRecorder`（事件记录器）.
  - Owns event writing, payload validation, ordering validation, event hash, hash chain, event stream reference, and event stream hash.
- Create: `tests/test_event_recorder.py`
  - Covers config validation, JSONL writing, event id and sequence allocation, event hash chain, event stream hash, required event helpers, payload validation, ordering validation, write failure behavior, and `AgentRunResult` consumption.
- Modify after implementation passes: `docs/04-implementation-backlog/backlog.md`
  - Marks P0-006 completed only after tests pass and user review accepts implementation.
- Modify after implementation passes: `docs/04-implementation-spec/P0-006-event-recorder-jsonl-spec.md`
  - Changes status from `draft` to `implemented`.
- Modify after implementation passes: `docs/04-implementation-plan/P0-006-event-recorder-jsonl-plan.md`
  - Changes status from `draft` to `implemented`.
- Modify after implementation passes: `docs/04-implementation-spec/INDEX.md`
  - Moves `P0-006-event-recorder-jsonl-spec.md`（事件记录器与 JSONL 事件流规格） from active to completed / archived.
- Modify after implementation passes: `docs/04-implementation-plan/INDEX.md`
  - Moves this plan from active to completed / archived.

---

### Task 1: Add event recorder config and boundary tests

**Files:**

- Create: `tests/test_event_recorder.py`
- Create: `src/atomic_agent/event_recorder.py`

- [ ] **Step 1: Write failing tests for config validation and value objects**

Write `tests/test_event_recorder.py`:

```python
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
```

- [ ] **Step 2: Run the new tests and confirm they fail because the module does not exist**

Run:

```bash
pytest tests/test_event_recorder.py::test_event_protocol_version_is_one tests/test_event_recorder.py::test_artifact_reference_to_payload tests/test_event_recorder.py::test_event_recorder_rejects_empty_run_id -v
```

Expected:

```text
ModuleNotFoundError: No module named 'atomic_agent.event_recorder'
```

- [ ] **Step 3: Add initial event recorder module with config and value objects**

Write `src/atomic_agent/event_recorder.py`:

```python
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

from atomic_agent.models import AgentEvent, AgentEventType


EVENT_PROTOCOL_VERSION = 1
_SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")


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
```

- [ ] **Step 4: Run boundary tests and confirm they pass**

Run:

```bash
pytest tests/test_event_recorder.py::test_event_protocol_version_is_one tests/test_event_recorder.py::test_artifact_reference_to_payload tests/test_event_recorder.py::test_artifact_reference_rejects_invalid_values tests/test_event_recorder.py::test_event_error_to_payload tests/test_event_recorder.py::test_event_error_rejects_invalid_values tests/test_event_recorder.py::test_event_recorder_rejects_empty_run_id tests/test_event_recorder.py::test_event_recorder_rejects_empty_event_stream_ref tests/test_event_recorder.py::test_event_recorder_rejects_missing_parent_directory tests/test_event_recorder.py::test_event_recorder_rejects_directory_output_path tests/test_event_recorder.py::test_event_recorder_rejects_non_empty_existing_stream -v
```

Expected:

```text
PASSED
```

---

### Task 2: Implement generic JSONL recording, event ids, sequences, and hash chain

**Files:**

- Modify: `tests/test_event_recorder.py`
- Modify: `src/atomic_agent/event_recorder.py`

- [ ] **Step 1: Add failing JSONL and hash chain tests**

Append to `tests/test_event_recorder.py`:

```python

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
```

Also update the imports near the top of `tests/test_event_recorder.py`:

```python
from atomic_agent.models import AgentEventType, AgentRunResult, AgentRunStatus
```

- [ ] **Step 2: Run JSONL/hash tests and confirm methods are missing**

Run:

```bash
pytest tests/test_event_recorder.py::test_record_run_started_writes_first_jsonl_event tests/test_event_recorder.py::test_event_hash_uses_canonical_event_without_event_hash tests/test_event_recorder.py::test_record_two_events_increments_sequence_and_links_previous_hash tests/test_event_recorder.py::test_record_requires_run_started_as_first_event tests/test_event_recorder.py::test_record_rejects_empty_clock_value -v
```

Expected:

```text
AttributeError: 'EventRecorder' object has no attribute 'record_run_started'
```

- [ ] **Step 3: Implement generic record path and first helper methods**

Add imports to `src/atomic_agent/event_recorder.py`:

```python
import hashlib
import json
```

Add these methods inside `EventRecorder` after `event_stream_ref`:

```python
    def record_run_started(self, invocation_id: str) -> AgentEvent:
        return self.record(
            AgentEventType.RUN_STARTED,
            {"event_protocol_version": EVENT_PROTOCOL_VERSION, "invocation_id": invocation_id},
        )

    def record_provider_turn_started(self, provider_turn_id: str) -> AgentEvent:
        return self.record(AgentEventType.PROVIDER_TURN_STARTED, {"provider_turn_id": provider_turn_id})

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

    def _validate_ordering(self, event_type: AgentEventType, payload: dict[str, Any]) -> None:
        if self._terminal_recorded:
            raise EventRecorderError("cannot record events after terminal event")
        if self._sequence == 0 and event_type != AgentEventType.RUN_STARTED:
            raise EventRecorderError("run.started must be the first event")

    def _update_ordering_state(self, event: AgentEvent) -> None:
        if event.type in {AgentEventType.RUN_COMPLETED, AgentEventType.RUN_FAILED}:
            self._terminal_recorded = True

    def _validate_payload(self, event_type: AgentEventType, payload: dict[str, Any]) -> None:
        if not isinstance(payload, dict):
            raise EventRecorderError("event payload must be a dict")
        required = _REQUIRED_PAYLOAD_FIELDS.get(event_type, set())
        missing = [field for field in sorted(required) if field not in payload]
        if missing:
            raise EventRecorderError(f"{event_type.value} missing required payload fields: {', '.join(missing)}")

    def _event_id(self, sequence: int) -> str:
        return f"evt_{sequence:06d}"

    def _hash_event(self, event_without_hash: dict[str, Any]) -> str:
        canonical = json.dumps(event_without_hash, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"

    def _serialize_event(self, event: AgentEvent) -> str:
        return json.dumps(event.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
```

Add this module-level constant above `EventRecorder`:

```python
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
```

- [ ] **Step 4: Run JSONL/hash tests and confirm they pass**

Run:

```bash
pytest tests/test_event_recorder.py::test_record_run_started_writes_first_jsonl_event tests/test_event_recorder.py::test_event_hash_uses_canonical_event_without_event_hash tests/test_event_recorder.py::test_record_two_events_increments_sequence_and_links_previous_hash tests/test_event_recorder.py::test_record_requires_run_started_as_first_event tests/test_event_recorder.py::test_record_rejects_empty_clock_value -v
```

Expected:

```text
PASSED
```

---

### Task 3: Add required event helper methods and payload validation

**Files:**

- Modify: `tests/test_event_recorder.py`
- Modify: `src/atomic_agent/event_recorder.py`

- [ ] **Step 1: Add failing tests for all required event helpers**

Append to `tests/test_event_recorder.py`:

```python

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
```

- [ ] **Step 2: Run helper tests and confirm methods are missing**

Run:

```bash
pytest tests/test_event_recorder.py::test_required_event_helpers_write_expected_event_types tests/test_event_recorder.py::test_record_rejects_missing_required_payload_fields tests/test_event_recorder.py::test_record_run_failed_uses_error_payload -v
```

Expected:

```text
AttributeError: 'EventRecorder' object has no attribute 'record_provider_turn_completed'
```

- [ ] **Step 3: Add helper methods for all required event types**

Add these methods inside `EventRecorder` after `record_provider_turn_started`:

```python
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
```

- [ ] **Step 4: Run helper tests and confirm they pass**

Run:

```bash
pytest tests/test_event_recorder.py::test_required_event_helpers_write_expected_event_types tests/test_event_recorder.py::test_record_rejects_missing_required_payload_fields tests/test_event_recorder.py::test_record_run_failed_uses_error_payload -v
```

Expected:

```text
PASSED
```

---

### Task 4: Enforce ordering, terminal state, and tool attempt lifecycle

**Files:**

- Modify: `tests/test_event_recorder.py`
- Modify: `src/atomic_agent/event_recorder.py`

- [ ] **Step 1: Add failing ordering tests**

Append to `tests/test_event_recorder.py`:

```python

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
```

- [ ] **Step 2: Run ordering tests and confirm missing lifecycle checks**

Run:

```bash
pytest tests/test_event_recorder.py::test_terminal_event_prevents_later_events tests/test_event_recorder.py::test_tool_attempt_completed_requires_started_attempt tests/test_event_recorder.py::test_tool_attempt_failed_requires_started_attempt tests/test_event_recorder.py::test_workspace_mutation_requires_started_attempt tests/test_event_recorder.py::test_command_completed_requires_started_attempt tests/test_event_recorder.py::test_duplicate_tool_attempt_started_is_rejected -v
```

Expected before the fix:

```text
FAILED tests/test_event_recorder.py::test_tool_attempt_completed_requires_started_attempt
FAILED tests/test_event_recorder.py::test_tool_attempt_failed_requires_started_attempt
FAILED tests/test_event_recorder.py::test_workspace_mutation_requires_started_attempt
FAILED tests/test_event_recorder.py::test_command_completed_requires_started_attempt
FAILED tests/test_event_recorder.py::test_duplicate_tool_attempt_started_is_rejected
```

`test_terminal_event_prevents_later_events` may already pass after Task 2.

- [ ] **Step 3: Add tool attempt ordering checks**

Replace `_validate_ordering` and `_update_ordering_state` in `src/atomic_agent/event_recorder.py` with:

```python
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
```

- [ ] **Step 4: Run ordering tests and confirm they pass**

Run:

```bash
pytest tests/test_event_recorder.py::test_terminal_event_prevents_later_events tests/test_event_recorder.py::test_tool_attempt_completed_requires_started_attempt tests/test_event_recorder.py::test_tool_attempt_failed_requires_started_attempt tests/test_event_recorder.py::test_workspace_mutation_requires_started_attempt tests/test_event_recorder.py::test_command_completed_requires_started_attempt tests/test_event_recorder.py::test_duplicate_tool_attempt_started_is_rejected -v
```

Expected:

```text
PASSED
```

---

### Task 5: Validate payload shapes for errors, artifacts, hashes, and result submission

**Files:**

- Modify: `tests/test_event_recorder.py`
- Modify: `src/atomic_agent/event_recorder.py`

- [ ] **Step 1: Add failing payload shape tests**

Append to `tests/test_event_recorder.py`:

```python

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
```

- [ ] **Step 2: Run payload shape tests and confirm validation is missing**

Run:

```bash
pytest tests/test_event_recorder.py::test_error_event_requires_valid_error_payload tests/test_event_recorder.py::test_provider_output_requires_valid_artifact_payload tests/test_event_recorder.py::test_workspace_mutation_requires_valid_hashes_and_diff_artifact tests/test_event_recorder.py::test_command_completed_requires_exit_code_and_artifact_payloads tests/test_event_recorder.py::test_result_submitted_requires_summary_paths_and_artifact_refs -v
```

Expected before the fix:

```text
FAILED tests/test_event_recorder.py::test_error_event_requires_valid_error_payload
FAILED tests/test_event_recorder.py::test_provider_output_requires_valid_artifact_payload
FAILED tests/test_event_recorder.py::test_workspace_mutation_requires_valid_hashes_and_diff_artifact
FAILED tests/test_event_recorder.py::test_command_completed_requires_exit_code_and_artifact_payloads
FAILED tests/test_event_recorder.py::test_result_submitted_requires_summary_paths_and_artifact_refs
```

- [ ] **Step 3: Add payload shape validation helpers**

Extend `_validate_payload` in `src/atomic_agent/event_recorder.py` after required field validation:

```python
        if "error" in payload:
            self._validate_error_payload(payload["error"])
        for field in ("output", "observation", "diff", "stdout", "stderr", "response"):
            if field in payload:
                self._validate_artifact_payload(payload[field], field)
        if "before_hash" in payload and payload["before_hash"] is not None:
            self._validate_sha256(payload["before_hash"], "before_hash")
        if "after_hash" in payload:
            self._validate_sha256(payload["after_hash"], "after_hash")
        if event_type == AgentEventType.COMMAND_COMPLETED:
            if not isinstance(payload["exit_code"], int) or isinstance(payload["exit_code"], bool):
                raise EventRecorderError("command.completed exit_code must be an integer")
            if not isinstance(payload["command_id"], str) or payload["command_id"] == "":
                raise EventRecorderError("command.completed command_id must be a non-empty string")
        if event_type == AgentEventType.RESULT_SUBMITTED:
            self._validate_result_submission(payload)
```

Add these helper methods inside `EventRecorder`:

```python
    def _validate_error_payload(self, payload: object) -> None:
        if not isinstance(payload, dict):
            raise EventRecorderError("error payload must be a dict")
        for field in ("kind", "message", "retryable", "related_ref"):
            if field not in payload:
                raise EventRecorderError(f"error payload missing {field}")
        EventError(
            kind=payload["kind"],
            message=payload["message"],
            retryable=payload["retryable"],
            related_ref=payload["related_ref"],
        ).to_payload()

    def _validate_artifact_payload(self, payload: object, field_name: str) -> None:
        if not isinstance(payload, dict):
            raise EventRecorderError(f"{field_name} artifact payload must be a dict")
        for field in ("artifact_ref", "sha256", "size_bytes", "truncated_in_observation"):
            if field not in payload:
                raise EventRecorderError(f"{field_name} artifact payload missing {field}")
        ArtifactReference(
            artifact_ref=payload["artifact_ref"],
            sha256=payload["sha256"],
            size_bytes=payload["size_bytes"],
            truncated_in_observation=payload["truncated_in_observation"],
        ).to_payload()

    def _validate_sha256(self, value: object, field_name: str) -> None:
        if not isinstance(value, str) or not _SHA256_PATTERN.fullmatch(value):
            raise EventRecorderError(f"{field_name} must use sha256:<64 lowercase hex chars>")

    def _validate_result_submission(self, payload: dict[str, Any]) -> None:
        if not isinstance(payload["summary"], str) or payload["summary"] == "":
            raise EventRecorderError("result.submitted summary must be a non-empty string")
        if not isinstance(payload["produced_paths"], list) or any(not isinstance(path, str) for path in payload["produced_paths"]):
            raise EventRecorderError("result.submitted produced_paths must be a list of strings")
        if not isinstance(payload["artifact_refs"], list):
            raise EventRecorderError("result.submitted artifact_refs must be a list")
        for artifact in payload["artifact_refs"]:
            self._validate_artifact_payload(artifact, "artifact_refs")
```

- [ ] **Step 4: Run payload shape tests and confirm they pass**

Run:

```bash
pytest tests/test_event_recorder.py::test_error_event_requires_valid_error_payload tests/test_event_recorder.py::test_provider_output_requires_valid_artifact_payload tests/test_event_recorder.py::test_workspace_mutation_requires_valid_hashes_and_diff_artifact tests/test_event_recorder.py::test_command_completed_requires_exit_code_and_artifact_payloads tests/test_event_recorder.py::test_result_submitted_requires_summary_paths_and_artifact_refs -v
```

Expected:

```text
PASSED
```

---

### Task 6: Implement event stream hash and AgentRunResult consumption

**Files:**

- Modify: `tests/test_event_recorder.py`
- Modify: `src/atomic_agent/event_recorder.py`

- [ ] **Step 1: Add failing event stream hash and result tests**

Append to `tests/test_event_recorder.py`:

```python

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
```

- [ ] **Step 2: Run event stream hash tests and confirm method is missing**

Run:

```bash
pytest tests/test_event_recorder.py::test_events_hash_hashes_complete_jsonl_bytes tests/test_event_recorder.py::test_events_hash_fails_when_stream_missing tests/test_event_recorder.py::test_agent_run_result_accepts_recorder_event_stream_ref_and_hash -v
```

Expected:

```text
AttributeError: 'EventRecorder' object has no attribute 'events_hash'
```

- [ ] **Step 3: Add events_hash method**

Add this method inside `EventRecorder` after `record`:

```python
    def events_hash(self) -> str:
        try:
            content = self.config.event_stream_path.read_bytes()
        except OSError as error:
            raise EventRecorderError(f"failed to read event stream: {error}") from error
        if not content:
            raise EventRecorderError("event stream is empty or missing")
        return f"sha256:{hashlib.sha256(content).hexdigest()}"
```

- [ ] **Step 4: Run event stream hash tests and confirm they pass**

Run:

```bash
pytest tests/test_event_recorder.py::test_events_hash_hashes_complete_jsonl_bytes tests/test_event_recorder.py::test_events_hash_fails_when_stream_missing tests/test_event_recorder.py::test_agent_run_result_accepts_recorder_event_stream_ref_and_hash -v
```

Expected:

```text
PASSED
```

---

### Task 7: Cover write failure and no silent fallback behavior

**Files:**

- Modify: `tests/test_event_recorder.py`
- Modify: `src/atomic_agent/event_recorder.py` only if tests expose gaps

- [ ] **Step 1: Add write failure tests**

Append to `tests/test_event_recorder.py`:

```python

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
```

- [ ] **Step 2: Run write failure tests**

Run:

```bash
pytest tests/test_event_recorder.py::test_record_write_failure_raises_without_sequence_increment tests/test_event_recorder.py::test_payload_validation_failure_does_not_write_event_or_increment_sequence -v
```

Expected:

```text
PASSED
```

If `test_record_write_failure_raises_without_sequence_increment` fails because a platform permits the write differently, replace the directory-swap fixture with a monkeypatched writer method in the test and expose a small `_write_event_line` method in `EventRecorder`. Do not implement fallback to another path.

---

### Task 8: Run full verification and safety checks

**Files:**

- Verify: `src/atomic_agent/event_recorder.py`
- Verify: `tests/test_event_recorder.py`
- Verify: existing tests

- [ ] **Step 1: Run event recorder tests**

Run:

```bash
pytest tests/test_event_recorder.py -v
```

Expected:

```text
PASSED
```

- [ ] **Step 2: Run existing model and tool tests**

Run:

```bash
pytest tests/test_models.py tests/test_action_parser.py tests/test_path_guard.py tests/test_filesystem_tools.py tests/test_command_tools.py -v
```

Expected:

```text
PASSED
```

- [ ] **Step 3: Run full test suite**

Run:

```bash
pytest -v
```

Expected:

```text
PASSED
```

- [ ] **Step 4: Check runtime source for environment fallback reads**

Run:

```bash
python - <<'PY'
from pathlib import Path
for path in Path('src').rglob('*.py'):
    text = path.read_text(encoding='utf-8')
    for needle in ('os.environ', 'getenv', 'dotenv', '.env'):
        if needle in text:
            print(f'{path}: contains {needle}')
PY
```

Expected:

```text

```

No output means runtime source does not read environment fallback. If output appears in `src/atomic_agent/event_recorder.py`, remove the fallback read and require explicit config input.

- [ ] **Step 5: Check event recorder does not use output path fallback**

Run:

```bash
python - <<'PY'
from pathlib import Path
text = Path('src/atomic_agent/event_recorder.py').read_text(encoding='utf-8')
for forbidden in ('TemporaryDirectory', 'NamedTemporaryFile', 'mkstemp', 'tempfile', 'fallback'):
    if forbidden in text:
        print(f'forbidden event output fallback pattern: {forbidden}')
PY
```

Expected:

```text

```

No output means event recorder does not fall back to temp files or hidden alternate paths.

- [ ] **Step 6: Check working tree scope**

Run:

```bash
git status --short
```

Expected before implementation review:

```text
 M docs/04-implementation-plan/INDEX.md
 M docs/04-implementation-spec/INDEX.md
?? docs/04-implementation-plan/P0-006-event-recorder-jsonl-plan.md
?? docs/04-implementation-spec/P0-006-event-recorder-jsonl-spec.md
```

Expected after implementation:

```text
 M docs/04-implementation-backlog/backlog.md
 M docs/04-implementation-plan/INDEX.md
 M docs/04-implementation-spec/INDEX.md
?? docs/04-implementation-plan/P0-006-event-recorder-jsonl-plan.md
?? docs/04-implementation-spec/P0-006-event-recorder-jsonl-spec.md
?? src/atomic_agent/event_recorder.py
?? tests/test_event_recorder.py
```

Only P0-006 docs, implementation, tests, and required index/backlog updates should be present.

---

### Task 9: Update docs after implementation passes

**Files:**

- Modify: `docs/04-implementation-backlog/backlog.md`
- Modify: `docs/04-implementation-spec/P0-006-event-recorder-jsonl-spec.md`
- Modify: `docs/04-implementation-plan/P0-006-event-recorder-jsonl-plan.md`
- Modify: `docs/04-implementation-spec/INDEX.md`
- Modify: `docs/04-implementation-plan/INDEX.md`

- [ ] **Step 1: Mark P0-006 completed only after tests pass**

Change `docs/04-implementation-backlog/backlog.md` from:

```markdown
| P0-006 | 实现 event recorder（事件记录器）和 JSONL 输出 | pending | `event-stream-protocol.md` |
```

To:

```markdown
| P0-006 | 实现 event recorder（事件记录器）和 JSONL 输出 | completed | `P0-006-event-recorder-jsonl-spec.md`, `event-stream-protocol.md` |
```

- [ ] **Step 2: Mark spec implemented**

Change `docs/04-implementation-spec/P0-006-event-recorder-jsonl-spec.md` from:

```markdown
## Status

draft
```

To:

```markdown
## Status

implemented
```

- [ ] **Step 3: Mark plan implemented**

Change `docs/04-implementation-plan/P0-006-event-recorder-jsonl-plan.md` from:

```markdown
**Status:** draft
```

To:

```markdown
**Status:** implemented
```

- [ ] **Step 4: Move spec index entry to completed / archived**

Change `docs/04-implementation-spec/INDEX.md` by removing this active row:

```markdown
| `P0-006-event-recorder-jsonl-spec.md` | draft | 定义 P0-006 event recorder（事件记录器）和 JSONL event stream（JSONL 事件流）的输入、输出、哈希链、顺序规则和失败语义 | 实现 P0-006 前 |
```

Add this completed row:

```markdown
| `P0-006-event-recorder-jsonl-spec.md` | 2026-06-05 | 已实现 P0-006 event recorder（事件记录器）和 JSONL event stream（JSONL 事件流），保留为事件记录规格记录 |
```

- [ ] **Step 5: Move plan index entry to completed / archived**

Change `docs/04-implementation-plan/INDEX.md` by removing this active row:

```markdown
| `P0-006-event-recorder-jsonl-plan.md` | draft | 实施 P0-006 event recorder（事件记录器）和 JSONL event stream（JSONL 事件流）的 TDD 计划 | 执行 P0-006 时 |
```

Add this completed row:

```markdown
| `P0-006-event-recorder-jsonl-plan.md` | 2026-06-05 | 已实施 P0-006 event recorder（事件记录器）和 JSONL event stream（JSONL 事件流），保留为 TDD 实施记录 |
```

- [ ] **Step 6: Run final verification**

Run:

```bash
pytest -v
git status --short
```

Expected:

```text
PASSED
```

`git status --short` should show only P0-006 implementation, tests, and required docs/index updates.

---

## Self-Review Checklist

Before implementation is considered ready for review:

- [ ] Spec coverage: Every requirement in `docs/04-implementation-spec/P0-006-event-recorder-jsonl-spec.md` is covered by a task, test, or explicit out-of-scope statement.
- [ ] Placeholder scan: This plan contains no deferred event recorder behavior, no unspecified test case, no silent fallback, and no mock success path.
- [ ] Type consistency: `EventRecorderConfig`, `EventRecorderError`, `EventRecorderConfigError`, `ArtifactReference`, `EventError`, `EventRecorder`, `EVENT_PROTOCOL_VERSION`, and helper method names match across tests, implementation steps, and spec.
- [ ] Scope check: No AgentLoop, provider adapter, artifact store, network policy, replay executor, secret scanner, or Boardroom governance completion logic is included.
- [ ] Event protocol check: Required event types match `docs/03-contracts/event-stream-protocol.md`; `run.started` includes `event_protocol_version = 1`; JSONL rows include `event_id`, `run_id`, `sequence`, `type`, `timestamp`, `payload`, `previous_event_hash`, and `event_hash`.
- [ ] Hash check: `event_hash` excludes `event_hash` itself; `previous_event_hash` links to prior event; `events_hash()` hashes actual JSONL bytes.
- [ ] Failure check: Missing payload fields, illegal ordering, write failure, and empty event stream hash all fail clearly.
- [ ] Verification check: `pytest -v` passes with real execution output.
