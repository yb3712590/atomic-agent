# P2-001 Evidence Mapping and Artifact Hash Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement P2-001 evidence mapping（证据映射） and artifact hash hardening（产物哈希硬化） so `atomic-agent`（原子智能体） can derive auditable Boardroom evidence input（Boardroom 证据输入候选） from real event streams and artifacts without making governance decisions.

**Architecture:** Add a focused `evidence` module（证据模块） that reads immutable runtime facts from `AgentRunResult`（智能体运行结果） and JSONL `event stream`（事件流）, verifies event hash integrity（事件哈希完整性）, and derives provider/tool/workspace/command/network/source lineage（模型/工具/工作区/命令/网络/源码谱系） summaries. Keep this as a derived mapper（派生映射器）, not a second source of truth（第二事实源） and not a Boardroom EvidenceVerifier（证据验证器）.

**Tech Stack:** Python 3.11+, existing Pydantic models（现有 Pydantic 模型）, JSONL event protocol（JSONL 事件协议）, SHA-256 hashing（SHA-256 哈希）, pytest（测试框架）, existing minimal fake loop（现有最小假模型循环）.

**Status:** implemented

---

## Scope

This plan implements P2-001 only.

In scope:

- Create `src/atomic_agent/evidence.py`（证据模块）.
- Create `tests/test_evidence.py`（证据映射测试）.
- Extend `tests/test_minimal_fake_loop_example.py`（最小假模型循环示例测试） to assert the real example can be mapped into evidence summary（证据摘要）.
- Verify event stream integrity（事件流完整性） using real JSONL bytes, sequence（序号）, `previous_event_hash`（前序事件哈希）, per-event `event_hash`（事件哈希） and `AgentRunResult.events_hash`（运行结果事件流哈希）.
- Derive provider attempts（模型调用尝试）, tool attempts（工具调用尝试）, workspace mutations（工作区变更）, command results（命令结果）, network fetches（网络获取）, source inventory lineage（源码清单谱系） and replay status（重放状态）.
- Update P2-001 docs status and indexes only after implementation and verification pass.

Out of scope:

- No `AgentRuntimePort`（智能体运行时端口） contract field change.
- No Boardroom EvidenceVerifier（Boardroom 证据验证器） implementation.
- No Boardroom closeout gate（Boardroom 收尾门禁） implementation.
- No governance completion fields（治理完成字段）.
- No full replay engine（完整重放引擎）.
- No real provider integration gate（真实模型供应商集成门禁）; that remains P2-002.
- No external coding agent bridge（外部编码智能体桥接） design or implementation; that remains P2-003 and deferred（延后）.
- No new provider（模型供应商）, tool（工具）, permission policy（权限策略） or network policy（网络策略） capability.
- No `.env`, `os.environ`, `getenv`, dotenv or local config fallback（本地配置兜底）.
- No git commit unless the user explicitly requests one.

## Review Addendum

本计划按用户评审补充以下实施要求，并覆盖原 Task 1 / Task 2 中的测试与实现代码块：

1. `tests/test_evidence.py` 必须额外覆盖 event stream missing file（事件流文件不存在）、empty file（空文件）、non UTF-8（非 UTF-8）、invalid JSON（无效 JSON）、non-object JSON line（非对象 JSON 行）、event hash mismatch（事件哈希不匹配）、missing terminal event（缺少终止事件）。
2. replay status（重放状态）测试必须覆盖全部 snapshot 缺失、只有部分 snapshot、`*_snapshot_ref` 等价字段和全部 replay metadata 存在的场景。
3. SourceInventory lineage（源码清单谱系）测试必须覆盖同一路径三次 workspace mutation（工作区变更）按事件顺序保留，以及 before/after hash chain（变更前后哈希链）断裂时 `workspace_mutation_hash_chain_mismatch` 失败。
4. `provider_turn_id`（模型轮次标识）派生规则固定为：以 `action.parsed` 发生时关联的 provider turn 为准；无法关联时为 `null`。
5. `tool_attempts`（工具调用尝试）以 event stream（事件流）为 evidence summary（证据摘要）事实源；`AgentRunResult.tool_attempts` 仅保留为 runtime result summary（运行结果摘要）和兼容字段。
6. 错误信息必须包含 line number（行号）、sequence（序号）或 event id（事件标识）等定位信息。本轮不新增日志系统。
7. 本轮保留一次性读取 event stream 到内存；streaming verifier（流式校验器）和 event stream size limit（事件流大小限制）作为后续技术债。
8. no-governance source scan（无治理字段源码扫描）允许 `src/atomic_agent/evidence.py` 中出现用于拒绝输出的 `_BANNED_GOVERNANCE_FIELDS`（禁用治理字段清单），但不允许出现生成、写入或声明治理完成语义的代码。

## File Structure

- Create: `tests/test_evidence.py`
  - Unit and integration tests for event stream integrity verification（事件流完整性校验）, evidence summary mapping（证据摘要映射）, replay status（重放状态）, missing lineage（缺失谱系） and governance field exclusion（治理字段排除）.
- Create: `src/atomic_agent/evidence.py`
  - Defines `EvidenceMappingError`（证据映射错误）, `verify_event_stream()`（验证事件流）, `build_evidence_summary()`（构造证据摘要） and `describe_replay_status()`（描述重放状态）.
- Modify: `tests/test_minimal_fake_loop_example.py`
  - Adds one assertion path proving the documented CLI example output can be mapped into evidence summary with command artifact hashes（命令产物哈希） and source lineage（源码谱系）.
- Modify after implementation passes: `docs/04-implementation-backlog/backlog.md`
  - Adds the P2-001 spec as basis if not already present; marks P2-001 completed only after code and verification pass.
- Modify after implementation passes: `docs/04-implementation-spec/P2-001-evidence-mapping-artifact-hash-hardening-spec.md`
  - Changes status from `draft` to `implemented`.
- Modify after implementation passes: `docs/04-implementation-plan/P2-001-evidence-mapping-artifact-hash-hardening-plan.md`
  - Changes status from `draft` to `implemented`.
- Modify after implementation passes: `docs/04-implementation-spec/INDEX.md`
  - Moves the P2-001 spec from active draft to completed / archived.
- Modify after implementation passes: `docs/04-implementation-plan/INDEX.md`
  - Moves this plan from active draft to completed / archived.
- Modify after implementation passes: `docs/INDEX.md`
  - Removes P2-001 draft active pointers if they were added for review / implementation.

---

### Task 1: Add failing evidence mapping tests

**Files:**

- Create: `tests/test_evidence.py`
- Verify: `src/atomic_agent/examples/minimal_fake_loop.py`
- Verify: `src/atomic_agent/event_recorder.py`
- Verify: `src/atomic_agent/models.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_evidence.py` with this exact content:

```python
import hashlib
import json
from pathlib import Path

import pytest

from atomic_agent.event_recorder import ArtifactReference, EventRecorder, EventRecorderConfig
from atomic_agent.evidence import EvidenceMappingError, build_evidence_summary, verify_event_stream
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


def test_verify_event_stream_rejects_previous_hash_mismatch(tmp_path):
    paths, _ = run_fake_loop(tmp_path)
    events = read_jsonl(paths.event_stream)
    events[1]["previous_event_hash"] = "sha256:" + "0" * 64
    write_jsonl(paths.event_stream, events)

    integrity = verify_event_stream(paths.event_stream)

    assert integrity["ok"] is False
    assert integrity["failure_kind"] == "event_previous_hash_mismatch"
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


def test_build_evidence_summary_rejects_events_hash_mismatch(tmp_path):
    paths, result = run_fake_loop(tmp_path)
    wrong_result = result.model_copy(update={"events_hash": "sha256:" + "0" * 64})

    with pytest.raises(EvidenceMappingError) as raised:
        build_evidence_summary(wrong_result, paths.event_stream)

    assert raised.value.failure_kind == "events_hash_mismatch"


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
```

- [ ] **Step 2: Run the new tests and confirm they fail before implementation**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_evidence.py -q
```

Expected before implementation:

```text
ERROR tests/test_evidence.py
```

The failure reason should mention that `atomic_agent.evidence`（原子智能体证据模块） does not exist yet. If a different failure appears, inspect it before implementation; do not modify tests to hide a real mismatch with the P2-001 spec（规格）.

---

### Task 2: Implement the evidence module

**Files:**

- Create: `src/atomic_agent/evidence.py`
- Test: `tests/test_evidence.py`

- [ ] **Step 1: Create `src/atomic_agent/evidence.py`**

Create `src/atomic_agent/evidence.py` with this exact content:

```python
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
        if sequence != expected_sequence:
            return _failure(
                "event_sequence_gap",
                f"event sequence must be continuous from 1; expected {expected_sequence}, got {sequence}",
            )
        if event["previous_event_hash"] != previous_hash:
            return _failure(
                "event_previous_hash_mismatch",
                f"event {sequence} previous_event_hash does not match the previous event hash",
            )
        recalculated_hash = _hash_event_without_event_hash(event)
        if event["event_hash"] != recalculated_hash:
            return _failure(
                "event_hash_mismatch",
                f"event {sequence} event_hash does not match canonical event hash",
            )
        previous_hash = event["event_hash"]

    terminal_event_type = events[-1]["type"]
    if terminal_event_type not in _TERMINAL_EVENT_TYPES:
        return _failure(
            "event_terminal_missing",
            "event stream must end with run.completed or run.failed",
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
        return _failure("event_stream_missing", "event stream path does not exist")
    if event_stream_path.is_dir():
        return _failure("event_stream_unreadable", "event stream path must be a file")
    try:
        raw = event_stream_path.read_bytes()
    except OSError as error:
        return _failure("event_stream_unreadable", f"failed to read event stream: {error}")
    if not raw:
        return _failure("event_stream_empty", "event stream is empty")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        return _failure("event_stream_unreadable", f"event stream is not UTF-8: {error}")
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
        return _failure("event_stream_empty", "event stream contains no events")
    return {"ok": True, "raw": raw, "events": events}


def _validate_event_schema(event: dict[str, Any]) -> dict[str, Any] | None:
    try:
        AgentEvent(**event)
    except ValidationError as error:
        return _failure("event_schema_invalid", f"invalid AgentEvent schema: {error}")
    if not _is_sha256(event.get("event_hash")):
        return _failure("event_schema_invalid", "event_hash must use sha256:<64 lowercase hex chars>")
    previous_event_hash = event.get("previous_event_hash")
    if previous_event_hash is not None and not _is_sha256(previous_event_hash):
        return _failure("event_schema_invalid", "previous_event_hash must be null or sha256:<64 lowercase hex chars>")
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
        raise EvidenceMappingError("sha256_invalid", f"{label} must use sha256:<64 lowercase hex chars>")


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
```

- [ ] **Step 2: Run focused evidence tests**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_evidence.py -q
```

Expected:

```text
6 passed
```

If tests fail, fix `src/atomic_agent/evidence.py` only unless the test contradicts the P2-001 spec（规格）. Do not weaken event hash verification, replay status, missing lineage behavior, or governance field exclusion to make tests pass.

---

### Task 3: Integrate evidence mapping into the minimal fake loop example test

**Files:**

- Modify: `tests/test_minimal_fake_loop_example.py`
- Test: `tests/test_minimal_fake_loop_example.py`

- [ ] **Step 1: Add evidence import**

In `tests/test_minimal_fake_loop_example.py`, add this import after existing imports:

```python
from atomic_agent.evidence import build_evidence_summary
```

- [ ] **Step 2: Add evidence mapping assertions to the real multistep example test**

In `test_minimal_fake_loop_example_runs_real_multistep_loop`, after the `expected_artifacts` assertion, add:

```python
    evidence_summary = build_evidence_summary(
        AgentRunResult.model_validate(result_payload),
        paths["event_stream"],
    )
    assert evidence_summary["event_stream"]["integrity"]["ok"] is True
    assert [command["exit_code"] for command in evidence_summary["command_results"]] == [3, 0]
    assert all(command["stdout"]["sha256"].startswith("sha256:") for command in evidence_summary["command_results"])
    assert all(command["stderr"]["sha256"].startswith("sha256:") for command in evidence_summary["command_results"])
    assert evidence_summary["source_inventory_lineage"]
    assert evidence_summary["source_inventory_lineage"][0]["path"] == "work/output.txt"
    assert evidence_summary["source_inventory_lineage"][0]["lineage_status"] == "traceable"
    assert [mutation["tool"] for mutation in evidence_summary["source_inventory_lineage"][0]["mutation_refs"]] == [
        "write_file",
        "apply_patch",
    ]
    assert evidence_summary["replay"]["status"] == "not_replayable"
```

The file already imports `AgentRunResult` in the P2-001 baseline? If it does not, add:

```python
from atomic_agent.models import AgentRunResult
```

Do not add fake result objects here. This test must keep using the real CLI example output and real event stream.

- [ ] **Step 3: Run the minimal fake loop tests**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_minimal_fake_loop_example.py -q
```

Expected: pytest exits with code 0 and reports no failures.

---

### Task 4: Verify permission, runtime and full-suite behavior

**Files:**

- Verify: `src/atomic_agent/evidence.py`
- Verify: existing runtime tests
- Verify: existing permission negative gate（权限负向门禁）

- [ ] **Step 1: Run evidence tests**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_evidence.py -q
```

Expected:

```text
6 passed
```

- [ ] **Step 2: Run minimal fake loop tests**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_minimal_fake_loop_example.py -q
```

Expected: pytest exits with code 0 and reports no failures.

- [ ] **Step 3: Run AgentLoop regression tests**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_agent_loop.py -q
```

Expected: pytest exits with code 0 and reports no failures.

- [ ] **Step 4: Run runtime port regression tests**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_runtime_port.py -q
```

Expected: pytest exits with code 0 and reports no failures.

- [ ] **Step 5: Run permission negative gate**

Run:

```bash
PYTHONPATH=src python -m pytest -m permission_negative -q
```

Expected: pytest exits with code 0 and reports no failures for selected permission negative tests（权限负向测试）.

- [ ] **Step 6: Run full suite**

Run:

```bash
PYTHONPATH=src python -m pytest -q
```

Expected: pytest exits with code 0 and reports no failures.

- [ ] **Step 7: Run no-fallback and no-governance source scan**

Run:

```bash
python - <<'PY'
from pathlib import Path
needles = (
    'os.environ',
    'getenv',
    'dotenv',
    'TICKET_COMPLETED',
    'CLOSEOUT_COMMITTED',
    'ticket_completed',
    'closeout_committed',
    'governance_status',
    'evidence_verified',
    'source_inventory_accepted',
    'allow_all',
    'default_allow',
    "Path('.env')",
    'Path(".env")',
)
for path in Path('src/atomic_agent').rglob('*.py'):
    text = path.read_text(encoding='utf-8')
    for needle in needles:
        if needle in text:
            print(f'{path}: contains {needle}')
PY
```

Expected output after P2-001 implementation:

```text
```

If output appears in executable runtime code, inspect it before claiming completion. Test-only references to banned field names are acceptable only when they assert those fields are absent from outputs; executable runtime modules must not add governance completion semantics.

---

### Task 5: Update documentation after implementation passes

**Files:**

- Modify: `docs/04-implementation-backlog/backlog.md`
- Modify: `docs/04-implementation-spec/P2-001-evidence-mapping-artifact-hash-hardening-spec.md`
- Modify: `docs/04-implementation-plan/P2-001-evidence-mapping-artifact-hash-hardening-plan.md`
- Modify: `docs/04-implementation-spec/INDEX.md`
- Modify: `docs/04-implementation-plan/INDEX.md`
- Modify: `docs/INDEX.md`

- [ ] **Step 1: Mark P2-001 completed only after tests pass**

Change the P2-001 row in `docs/04-implementation-backlog/backlog.md` from:

```markdown
| P2-001 | 完善 event stream / evidence mapping（事件流 / 证据映射）和 artifact hash（产物哈希）硬化 | pending | `P2-001-evidence-mapping-artifact-hash-hardening-spec.md`, `event-stream-protocol.md`, `event-and-evidence-architecture.md`, `agent-runtime-port.md`, `mvp-acceptance.md`, `roadmap.md` |
```

To:

```markdown
| P2-001 | 完善 event stream / evidence mapping（事件流 / 证据映射）和 artifact hash（产物哈希）硬化 | completed | `P2-001-evidence-mapping-artifact-hash-hardening-spec.md`, `event-stream-protocol.md`, `event-and-evidence-architecture.md`, `agent-runtime-port.md`, `mvp-acceptance.md`, `roadmap.md` |
```

- [ ] **Step 2: Mark spec implemented**

Change `docs/04-implementation-spec/P2-001-evidence-mapping-artifact-hash-hardening-spec.md` from:

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

Change this plan from:

```markdown
**Status:** draft
```

To:

```markdown
**Status:** implemented
```

- [ ] **Step 4: Move spec index entry to completed / archived**

Remove this active row from `docs/04-implementation-spec/INDEX.md`:

```markdown
| `P2-001-evidence-mapping-artifact-hash-hardening-spec.md` | draft | 定义 P2-001 event stream / evidence mapping（事件流 / 证据映射）、artifact hash（产物哈希）、SourceInventory lineage（源码清单谱系）和 replay status（重放状态）硬化规格 | 评审或实现 P2-001 前 |
```

Add this completed row:

```markdown
| `P2-001-evidence-mapping-artifact-hash-hardening-spec.md` | 2026-06-07 | 已实现 P2-001 event stream / evidence mapping（事件流 / 证据映射）和 artifact hash（产物哈希）硬化，保留为证据映射规格记录 |
```

- [ ] **Step 5: Move plan index entry to completed / archived**

Remove this active row from `docs/04-implementation-plan/INDEX.md`:

```markdown
| `P2-001-evidence-mapping-artifact-hash-hardening-plan.md` | draft | 实施 P2-001 event stream / evidence mapping（事件流 / 证据映射）和 artifact hash（产物哈希）硬化的 TDD 计划 | 执行或评审 P2-001 时 |
```

Add this completed row:

```markdown
| `P2-001-evidence-mapping-artifact-hash-hardening-plan.md` | 2026-06-07 | 已实施 P2-001 event stream / evidence mapping（事件流 / 证据映射）和 artifact hash（产物哈希）硬化，保留为 TDD 实施记录 |
```

- [ ] **Step 6: Remove P2-001 draft pointers from global active documents after completion**

Remove these rows from `docs/INDEX.md` Current Active Documents（当前活跃文档指针） after P2-001 moves to completed sections in subdirectory indexes:

```markdown
| P0 | `docs/04-implementation-spec/P2-001-evidence-mapping-artifact-hash-hardening-spec.md` | draft | 评审或实现 P2-001 evidence mapping（证据映射）和 artifact hash（产物哈希）硬化前 |
| P0 | `docs/04-implementation-plan/P2-001-evidence-mapping-artifact-hash-hardening-plan.md` | draft | 评审或执行 P2-001 evidence mapping（证据映射）和 artifact hash（产物哈希）硬化计划时 |
```

---

### Task 6: Final verification and completion report

**Files:**

- Verify: all touched files

- [ ] **Step 1: Run final full suite**

Run:

```bash
PYTHONPATH=src python -m pytest -q
```

Expected: pytest exits with code 0 and reports no failures.

- [ ] **Step 2: Run final permission negative gate**

Run:

```bash
PYTHONPATH=src python -m pytest -m permission_negative -q
```

Expected: pytest exits with code 0 and reports no failures.

- [ ] **Step 3: Check working tree scope**

Run:

```bash
git status --short
```

Expected final implementation scope:

```text
 M docs/INDEX.md
 M docs/04-implementation-backlog/backlog.md
 M docs/04-implementation-plan/INDEX.md
 M docs/04-implementation-plan/P2-001-evidence-mapping-artifact-hash-hardening-plan.md
 M docs/04-implementation-spec/INDEX.md
 M docs/04-implementation-spec/P2-001-evidence-mapping-artifact-hash-hardening-spec.md
 M tests/test_minimal_fake_loop_example.py
?? src/atomic_agent/evidence.py
?? tests/test_evidence.py
```

If additional files appear, inspect them and explain before claiming completion.

- [ ] **Step 4: Completion report boundary**

The completion report must say that P2-001 adds evidence mapping（证据映射）, event stream integrity verification（事件流完整性校验）, artifact hash checks（产物哈希检查） and source lineage（源码谱系） derivation. It must not say Boardroom ticket completed（工单完成）, closeout committed（收尾提交）, evidence verified（证据已验证） or source inventory accepted（源码清单已接受）.

---

## Self-Review Checklist

Before implementation is considered ready for user review:

- [ ] Spec coverage: Every requirement in `docs/04-implementation-spec/P2-001-evidence-mapping-artifact-hash-hardening-spec.md` is covered by a task, test, verification command, documentation update or explicit out-of-scope statement.
- [ ] Placeholder scan: This plan contains no unfinished markers, vague “add tests” step, fake evidence placeholder or silent fallback.
- [ ] Type consistency: `EvidenceMappingError`, `verify_event_stream`, `build_evidence_summary`, `describe_replay_status`, `AgentRunResult`, event type strings and artifact payload fields match the planned implementation and existing contracts.
- [ ] Scope check: No Boardroom EvidenceVerifier, closeout gate, `AgentRuntimePort` contract change, real provider gate, external coding agent bridge, full replay engine, new tool or new permission policy is included.
- [ ] Fail-closed check: Missing event stream, invalid JSON, schema error, sequence gap, previous hash mismatch, event hash mismatch, events hash mismatch and missing terminal event all produce explicit failure.
- [ ] Evidence boundary check: Evidence summary is derived from existing result/events/artifacts and does not create a second event stream, artifact store, Boardroom governance state or default replayable claim.
- [ ] Verification check: Evidence tests, minimal fake loop tests, AgentLoop tests, runtime port tests, permission negative gate, full suite and source scan pass before any completion claim.

## Self-Review Result

- Spec coverage（规格覆盖）：计划覆盖 P2-001 spec（规格）中的 event stream integrity（事件流完整性）、evidence summary shape（证据摘要结构）、workspace mutation evidence（工作区变更证据）、command evidence（命令证据）、network evidence（网络证据）、SourceInventory lineage（源码清单谱系）、replay status（重放状态）、安全无兜底规则、文档要求和验收标准。
- Placeholder scan（占位符扫描）：未使用占位式标记、空泛“补测试”或未定义步骤；新增测试和实现模块均提供完整代码。
- Type consistency（类型一致性）：计划中的函数名、类名、事件类型、artifact payload（产物载荷）字段、failure kind（失败类型）和文件路径与现有代码及新规格保持一致。
- Scope check（范围检查）：未纳入 Boardroom OS EvidenceVerifier、closeout gate、真实 provider、外部 coding agent bridge、完整重放引擎、权限引擎、长期配置系统、新事件类型或破坏性契约变更。
- No-fallback check（无兜底检查）：计划明确要求事件流缺失/损坏/hash mismatch 时失败关闭，不补造 artifact hash，不默认 replayable，不读取环境或本地配置补齐字段，不添加治理完成语义，不创建第二事实源。
