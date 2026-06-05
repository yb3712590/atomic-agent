# Minimal AgentLoop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement P0-007 minimal `AgentLoop`（最小智能体循环） so a deterministic fake provider（确定性假模型供应商） can drive real filesystem / command tools（文件系统 / 命令工具）, feed observations（观察结果） into later turns, record JSONL events（JSONL 事件）, and return `AgentRunResult`（智能体运行结果）.

**Architecture:** Add a small `artifacts`（产物） module for real artifact files and a focused `agent_loop`（智能体循环） module that composes existing parser（解析器）, path guard（路径守卫）, filesystem tools（文件系统工具）, command tools（命令工具）, and event recorder（事件记录器）. The loop owns only one run's short-lived state and fails closed on invalid invocation, invalid provider output, denied permissions, tool failures, and max steps; it does not implement web/network, real provider API calls, Boardroom adapter（Boardroom 适配器）, or alternate fallback paths.

**Tech Stack:** Python 3.11+, `dataclasses`（轻量数据结构）, `typing.Protocol`（协议类型）, `pathlib`（路径处理）, `json`（JSON 序列化）, `hashlib`（哈希）, pytest（测试）, existing pydantic models（Pydantic 模型）.

**Status:** implemented

---

## Scope

This plan implements P0-007 only.

In scope:

- Create `src/atomic_agent/artifacts.py`（产物写入模块）.
- Create `tests/test_artifacts.py`（产物写入测试）.
- Create `src/atomic_agent/agent_loop.py`（智能体循环模块）.
- Create `tests/test_agent_loop.py`（智能体循环测试）.
- Reuse `parse_agent_action`（解析智能体动作）, `WorkspacePathGuard`（工作区路径守卫）, `FilesystemTools`（文件系统工具）, `CommandTools`（命令工具）, and `EventRecorder`（事件记录器）.
- Implement deterministic fake provider loop tests（确定性假模型供应商循环测试）.
- Implement P0 fail-closed behavior for invalid runtime requirements, invalid JSON, disabled tools, permission denied, command policy denial, tool failures, and max steps.
- Update P0-007 docs only after tests pass.

Out of scope:

- No `web_fetch`（网络获取） implementation.
- No `NetworkPolicy`（网络策略）.
- No real provider API integration（真实模型供应商 API 集成）.
- No Boardroom `AgentRuntimePort` adapter（Boardroom 智能体运行时端口适配器）.
- No native tool calling（原生工具调用）.
- No external coding agent bridge（外部编码智能体桥接）.
- No README minimal example（最小示例） update until a real end-to-end command is stable and accepted.
- No commit unless the user explicitly requests it.

## File Structure

- Create: `src/atomic_agent/artifacts.py`
  - Defines `ArtifactWriterConfig`（产物写入器配置）, `ArtifactWriterError`（产物写入器错误）, and `ArtifactWriter`（产物写入器）.
  - Owns artifact path validation（产物路径校验）, stable JSON/text writes（稳定 JSON / 文本写入）, SHA-256 hashing（哈希）, size calculation（大小计算）, and `artifact://` reference construction（产物引用构造）.
- Create: `tests/test_artifacts.py`
  - Covers config validation, path escape rejection, text writes, JSON writes, SHA-256 hash correctness, UTF-8 output, and no fallback behavior.
- Create: `src/atomic_agent/agent_loop.py`
  - Defines `ProviderContext`（模型上下文）, `ProviderAdapter`（模型供应商适配器）, `AgentLoopConfig`（智能体循环配置）, `AgentLoopDependencies`（智能体循环依赖）, `PermissionDecision`（权限判定）, `AgentLoopError`（智能体循环错误）, and `AgentLoop`（智能体循环）.
  - Owns per-run orchestration and short-lived state only.
- Create: `tests/test_agent_loop.py`
  - Covers multistep fake provider success, event stream facts, invalid JSON retry/fail closed, disabled tool denial, write outside allowed set denial, undeclared command denial, `web_fetch` denial, max steps failure, and provider failure.
- Modify after implementation passes: `docs/04-implementation-backlog/backlog.md`
  - Marks P0-007 completed only after full verification.
- Modify after implementation passes: `docs/04-implementation-spec/P0-007-minimal-agent-loop-spec.md`
  - Changes status from `draft` to `implemented`.
- Modify after implementation passes: `docs/04-implementation-plan/P0-007-minimal-agent-loop-plan.md`
  - Changes status from `draft` to `implemented`.
- Modify after implementation passes: `docs/04-implementation-spec/INDEX.md`
  - Moves the P0-007 spec from active to completed / archived.
- Modify after implementation passes: `docs/04-implementation-plan/INDEX.md`
  - Moves this plan from active to completed / archived.

---

### Task 1: Add ArtifactWriter（产物写入器） tests and implementation

**Files:**

- Create: `tests/test_artifacts.py`
- Create: `src/atomic_agent/artifacts.py`

- [ ] **Step 1: Write failing artifact writer tests**

Create `tests/test_artifacts.py`:

```python
import hashlib
import json

import pytest

from atomic_agent.artifacts import ArtifactWriter, ArtifactWriterConfig, ArtifactWriterError


def make_writer(tmp_path):
    root = tmp_path / "artifacts"
    root.mkdir()
    return ArtifactWriter(
        ArtifactWriterConfig(
            artifact_root=root,
            artifact_ref_prefix="artifact://run_001",
        )
    )


def test_artifact_writer_rejects_missing_root(tmp_path):
    config = ArtifactWriterConfig(
        artifact_root=tmp_path / "missing",
        artifact_ref_prefix="artifact://run_001",
    )

    with pytest.raises(ArtifactWriterError):
        ArtifactWriter(config)


def test_artifact_writer_rejects_file_root(tmp_path):
    root = tmp_path / "artifact-file"
    root.write_text("not a directory", encoding="utf-8")
    config = ArtifactWriterConfig(artifact_root=root, artifact_ref_prefix="artifact://run_001")

    with pytest.raises(ArtifactWriterError):
        ArtifactWriter(config)


def test_artifact_writer_rejects_empty_ref_prefix(tmp_path):
    root = tmp_path / "artifacts"
    root.mkdir()

    with pytest.raises(ArtifactWriterError):
        ArtifactWriter(ArtifactWriterConfig(artifact_root=root, artifact_ref_prefix=""))


@pytest.mark.parametrize("relative_path", ["", " ", "/absolute.txt", "../escape.txt", "nested/../../escape.txt"])
def test_artifact_writer_rejects_unsafe_relative_paths(tmp_path, relative_path):
    writer = make_writer(tmp_path)

    with pytest.raises(ArtifactWriterError):
        writer.write_text(relative_path, "content")


def test_write_text_creates_real_artifact_with_hash(tmp_path):
    writer = make_writer(tmp_path)

    payload = writer.write_text("provider/turn_000001.txt", "hello", truncated_in_observation=False)

    artifact_path = tmp_path / "artifacts" / "provider" / "turn_000001.txt"
    assert artifact_path.read_text(encoding="utf-8") == "hello"
    assert payload == {
        "artifact_ref": "artifact://run_001/provider/turn_000001.txt",
        "sha256": "sha256:" + hashlib.sha256(b"hello").hexdigest(),
        "size_bytes": 5,
        "truncated_in_observation": False,
    }


def test_write_json_uses_stable_utf8_json(tmp_path):
    writer = make_writer(tmp_path)
    data = {"z": 1, "a": "中文"}

    payload = writer.write_json("observations/tool_000001.json", data, truncated_in_observation=True)

    artifact_path = tmp_path / "artifacts" / "observations" / "tool_000001.json"
    expected_text = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    assert artifact_path.read_text(encoding="utf-8") == expected_text
    assert payload["artifact_ref"] == "artifact://run_001/observations/tool_000001.json"
    assert payload["sha256"] == "sha256:" + hashlib.sha256(expected_text.encode("utf-8")).hexdigest()
    assert payload["size_bytes"] == len(expected_text.encode("utf-8"))
    assert payload["truncated_in_observation"] is True
```

- [ ] **Step 2: Run artifact tests and confirm they fail because the module does not exist**

Run:

```bash
pytest tests/test_artifacts.py -v
```

Expected:

```text
ModuleNotFoundError: No module named 'atomic_agent.artifacts'
```

- [ ] **Step 3: Implement ArtifactWriter**

Create `src/atomic_agent/artifacts.py`:

```python
from dataclasses import dataclass
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from atomic_agent.event_recorder import ArtifactReference


@dataclass(frozen=True)
class ArtifactWriterConfig:
    artifact_root: Path
    artifact_ref_prefix: str


class ArtifactWriterError(RuntimeError):
    pass


class ArtifactWriter:
    def __init__(self, config: ArtifactWriterConfig):
        self.config = config
        self._validate_config()
        self.artifact_root = config.artifact_root.resolve(strict=True)
        self.artifact_ref_prefix = config.artifact_ref_prefix.rstrip("/")

    def write_text(
        self,
        relative_path: str,
        content: str,
        truncated_in_observation: bool = False,
    ) -> dict[str, Any]:
        if not isinstance(content, str):
            raise ArtifactWriterError("artifact content must be a string")
        if not isinstance(truncated_in_observation, bool):
            raise ArtifactWriterError("truncated_in_observation must be a boolean")
        return self._write_bytes(relative_path, content.encode("utf-8"), truncated_in_observation)

    def write_json(
        self,
        relative_path: str,
        payload: dict[str, Any] | list[Any],
        truncated_in_observation: bool = False,
    ) -> dict[str, Any]:
        text = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return self.write_text(relative_path, text, truncated_in_observation)

    def _write_bytes(self, relative_path: str, content: bytes, truncated_in_observation: bool) -> dict[str, Any]:
        normalized = self._normalize_relative_path(relative_path)
        target = self.artifact_root.joinpath(*normalized.parts)
        resolved_parent = target.parent.resolve(strict=False)
        if not resolved_parent.is_relative_to(self.artifact_root):
            raise ArtifactWriterError("artifact path must stay inside artifact_root")
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        except OSError as error:
            raise ArtifactWriterError(f"failed to write artifact: {error}") from error
        artifact_ref = f"{self.artifact_ref_prefix}/{normalized.as_posix()}"
        return ArtifactReference(
            artifact_ref=artifact_ref,
            sha256=self._sha256(content),
            size_bytes=len(content),
            truncated_in_observation=truncated_in_observation,
        ).to_payload()

    def _normalize_relative_path(self, relative_path: str) -> PurePosixPath:
        if not isinstance(relative_path, str) or not relative_path.strip():
            raise ArtifactWriterError("artifact relative_path must be a non-empty string")
        if self._is_absolute_like_path(relative_path):
            raise ArtifactWriterError("artifact relative_path must be relative")
        posix_path = PurePosixPath(relative_path)
        windows_path = PureWindowsPath(relative_path)
        if ".." in posix_path.parts or ".." in windows_path.parts:
            raise ArtifactWriterError("artifact relative_path cannot contain '..'")
        parts = tuple(part for part in posix_path.parts if part not in {"", "."})
        if not parts:
            raise ArtifactWriterError("artifact relative_path must contain a filename")
        return PurePosixPath(*parts)

    def _is_absolute_like_path(self, path: str) -> bool:
        windows_path = PureWindowsPath(path)
        return Path(path).is_absolute() or PurePosixPath(path).is_absolute() or windows_path.is_absolute() or bool(windows_path.drive or windows_path.root)

    def _validate_config(self) -> None:
        if not isinstance(self.config.artifact_root, Path):
            raise ArtifactWriterError("artifact_root must be a Path")
        if not self.config.artifact_root.exists():
            raise ArtifactWriterError("artifact_root must exist")
        if not self.config.artifact_root.is_dir():
            raise ArtifactWriterError("artifact_root must be a directory")
        if not isinstance(self.config.artifact_ref_prefix, str) or not self.config.artifact_ref_prefix:
            raise ArtifactWriterError("artifact_ref_prefix must be a non-empty string")

    def _sha256(self, content: bytes) -> str:
        import hashlib

        return f"sha256:{hashlib.sha256(content).hexdigest()}"
```

- [ ] **Step 4: Run artifact tests and confirm they pass**

Run:

```bash
pytest tests/test_artifacts.py -v
```

Expected:

```text
PASSED
```

---

### Task 2: Add AgentLoop（智能体循环） public boundary tests and skeleton

**Files:**

- Create: `tests/test_agent_loop.py`
- Create: `src/atomic_agent/agent_loop.py`

- [ ] **Step 1: Write failing tests for public boundary and invalid invocation budgets**

Create the beginning of `tests/test_agent_loop.py`:

```python
import json
from pathlib import Path
import sys

import pytest

from atomic_agent.agent_loop import AgentLoop, AgentLoopConfig, AgentLoopDependencies, ProviderContext
from atomic_agent.artifacts import ArtifactWriter, ArtifactWriterConfig
from atomic_agent.command_tools import CommandPolicy, CommandSpec, CommandToolConfig, CommandTools
from atomic_agent.event_recorder import EventRecorder, EventRecorderConfig
from atomic_agent.filesystem_tools import FilesystemToolConfig, FilesystemTools
from atomic_agent.models import AgentActionType, AgentInvocation, AgentRunStatus
from atomic_agent.path_guard import WorkspacePathGuard


PYTHON = Path(sys.executable).resolve()


class ScriptedProvider:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.contexts = []

    def complete(self, context: ProviderContext) -> str:
        self.contexts.append(context)
        if not self.outputs:
            raise AssertionError("no provider output scripted")
        output = self.outputs.pop(0)
        if isinstance(output, Exception):
            raise output
        return output


def fixed_clock():
    return "2026-06-05T00:00:00Z"


def action(action_id, action_name, input_payload):
    return json.dumps(
        {
            "action_id": action_id,
            "action": action_name,
            "reason_summary": f"Run {action_name}.",
            "input": input_payload,
        },
        sort_keys=True,
    )


def read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def make_invocation(tmp_path, tools=None, budgets=None, allowed_write_set=None):
    return AgentInvocation(
        invocation_id="inv_001",
        task="Create a fixed output file through a controlled loop.",
        workspace_root=str(tmp_path),
        allowed_write_set=allowed_write_set or ["work/"],
        tools=tools
        or [
            "list_files",
            "read_file",
            "search_files",
            "write_file",
            "apply_patch",
            "run_command",
            "submit_result",
        ],
        permission_policy={"policy_ref": "policy://test/minimal-loop"},
        provider_profile={"provider": "fake", "model": "fake-model"},
        budgets=budgets
        or {
            "max_steps": 8,
            "max_parse_failures": 1,
            "max_observation_chars": 10000,
        },
        output_requirements={"summary": True, "event_stream": True},
    )


def make_loop(tmp_path, provider):
    event_dir = tmp_path / "events"
    event_dir.mkdir()
    artifact_dir = tmp_path / "artifacts"
    artifact_dir.mkdir()
    guard = WorkspacePathGuard(tmp_path, allowed_write_set=["work/"])
    filesystem_tools = FilesystemTools(
        guard,
        FilesystemToolConfig(
            default_read_limit=12000,
            max_read_limit=50000,
            default_max_entries=200,
            max_entries_limit=1000,
            default_max_matches=50,
            max_matches_limit=500,
        ),
    )
    command_policy = CommandPolicy(
        {
            "check-output": CommandSpec(
                argv=(
                    str(PYTHON),
                    "-c",
                    "from pathlib import Path; import sys; content = Path('work/output.txt').read_text(encoding='utf-8'); sys.exit(0 if content == 'fixed' else 3)",
                )
            )
        }
    )
    command_tools = CommandTools(
        guard,
        command_policy,
        CommandToolConfig(default_timeout_seconds=2.0, max_timeout_seconds=5.0, max_output_bytes=4096),
    )
    recorder = EventRecorder(
        run_id="run_001",
        config=EventRecorderConfig(
            event_stream_path=event_dir / "events.jsonl",
            event_stream_ref="artifact://run_001/events.jsonl",
        ),
        clock=fixed_clock,
    )
    artifact_writer = ArtifactWriter(
        ArtifactWriterConfig(
            artifact_root=artifact_dir,
            artifact_ref_prefix="artifact://run_001",
        )
    )
    loop = AgentLoop(
        AgentLoopConfig(run_id="run_001"),
        AgentLoopDependencies(
            provider=provider,
            filesystem_tools=filesystem_tools,
            command_tools=command_tools,
            event_recorder=recorder,
            artifact_writer=artifact_writer,
        ),
    )
    return loop, recorder.config.event_stream_path


def test_agent_loop_fails_closed_when_budget_fields_are_missing(tmp_path):
    provider = ScriptedProvider([])
    loop, event_stream_path = make_loop(tmp_path, provider)
    invocation = make_invocation(tmp_path, budgets={"max_steps": 3})

    result = loop.run(invocation)

    assert result.status == AgentRunStatus.FAILED
    assert result.failure_kind == "invalid_invocation"
    events = read_jsonl(event_stream_path)
    assert [event["type"] for event in events] == ["run.started", "run.failed"]
```

- [ ] **Step 2: Run boundary test and confirm missing module failure**

Run:

```bash
pytest tests/test_agent_loop.py::test_agent_loop_fails_closed_when_budget_fields_are_missing -v
```

Expected:

```text
ModuleNotFoundError: No module named 'atomic_agent.agent_loop'
```

- [ ] **Step 3: Add AgentLoop skeleton with invalid invocation failure**

Create `src/atomic_agent/agent_loop.py` with public types and enough logic for invalid invocation failure:

```python
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from atomic_agent.artifacts import ArtifactWriter
from atomic_agent.command_tools import CommandTools
from atomic_agent.event_recorder import EventError, EventRecorder
from atomic_agent.filesystem_tools import FilesystemTools
from atomic_agent.models import AgentInvocation, AgentRunResult, AgentRunStatus


@dataclass(frozen=True)
class ProviderContext:
    invocation: AgentInvocation
    step: int
    observations: tuple[dict[str, Any], ...]


class ProviderAdapter(Protocol):
    def complete(self, context: ProviderContext) -> str:
        ...


@dataclass(frozen=True)
class AgentLoopConfig:
    run_id: str


@dataclass(frozen=True)
class AgentLoopDependencies:
    provider: ProviderAdapter
    filesystem_tools: FilesystemTools
    command_tools: CommandTools
    event_recorder: EventRecorder
    artifact_writer: ArtifactWriter


@dataclass(frozen=True)
class PermissionDecision:
    decision: Literal["allow", "deny"]
    reason: str
    policy_ref: str


class AgentLoopError(RuntimeError):
    pass


@dataclass
class _RunState:
    observations: list[dict[str, Any]] = field(default_factory=list)
    tool_attempts: list[dict[str, Any]] = field(default_factory=list)
    workspace_mutations: list[dict[str, Any]] = field(default_factory=list)
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    parse_failures: int = 0


@dataclass(frozen=True)
class _RuntimeRequirements:
    policy_ref: str
    max_steps: int
    max_parse_failures: int
    max_observation_chars: int


class AgentLoop:
    def __init__(self, config: AgentLoopConfig, dependencies: AgentLoopDependencies):
        if not isinstance(config.run_id, str) or not config.run_id:
            raise AgentLoopError("run_id must be a non-empty string")
        self.config = config
        self.dependencies = dependencies

    def run(self, invocation: AgentInvocation) -> AgentRunResult:
        state = _RunState()
        self.dependencies.event_recorder.record_run_started(invocation.invocation_id)
        requirements_or_error = self._runtime_requirements(invocation)
        if isinstance(requirements_or_error, str):
            return self._fail(
                state=state,
                failure_kind="invalid_invocation",
                failure_message=requirements_or_error,
                failed_action_ref=None,
            )
        return self._fail(
            state=state,
            failure_kind="max_steps_exceeded",
            failure_message="AgentLoop execution is not implemented beyond validation yet.",
            failed_action_ref=None,
        )

    def _runtime_requirements(self, invocation: AgentInvocation) -> _RuntimeRequirements | str:
        policy_ref = invocation.permission_policy.get("policy_ref")
        if not isinstance(policy_ref, str) or not policy_ref:
            return "permission_policy.policy_ref must be a non-empty string"
        max_steps = invocation.budgets.get("max_steps")
        max_parse_failures = invocation.budgets.get("max_parse_failures")
        max_observation_chars = invocation.budgets.get("max_observation_chars")
        if not isinstance(max_steps, int) or isinstance(max_steps, bool) or max_steps <= 0:
            return "budgets.max_steps must be a positive integer"
        if not isinstance(max_parse_failures, int) or isinstance(max_parse_failures, bool) or max_parse_failures < 0:
            return "budgets.max_parse_failures must be a non-negative integer"
        if not isinstance(max_observation_chars, int) or isinstance(max_observation_chars, bool) or max_observation_chars <= 0:
            return "budgets.max_observation_chars must be a positive integer"
        if "submit_result" not in invocation.tools:
            return "invocation.tools must include submit_result"
        return _RuntimeRequirements(policy_ref, max_steps, max_parse_failures, max_observation_chars)

    def _fail(
        self,
        state: _RunState,
        failure_kind: str,
        failure_message: str,
        failed_action_ref: str | None,
    ) -> AgentRunResult:
        self.dependencies.event_recorder.record_run_failed(
            EventError(
                kind=failure_kind,
                message=failure_message,
                retryable=False,
                related_ref=failed_action_ref,
            ).to_payload()
        )
        return AgentRunResult(
            run_id=self.config.run_id,
            status=AgentRunStatus.FAILED,
            event_stream_ref=self.dependencies.event_recorder.event_stream_ref,
            events_hash=self.dependencies.event_recorder.events_hash(),
            tool_attempts=state.tool_attempts,
            workspace_mutations=state.workspace_mutations,
            artifacts=state.artifacts,
            summary=f"Run failed closed: {failure_message}",
            failure_kind=failure_kind,
            failure_message=failure_message,
            failed_action_ref=failed_action_ref,
        )
```

- [ ] **Step 4: Run boundary test and confirm it passes**

Run:

```bash
pytest tests/test_agent_loop.py::test_agent_loop_fails_closed_when_budget_fields_are_missing -v
```

Expected:

```text
PASSED
```

---

### Task 3: Implement successful multistep fake provider loop

**Files:**

- Modify: `tests/test_agent_loop.py`
- Modify: `src/atomic_agent/agent_loop.py`

- [ ] **Step 1: Add failing multistep success test**

Append to `tests/test_agent_loop.py`:

```python

def test_agent_loop_runs_multistep_fake_provider_to_submit_result(tmp_path):
    provider = ScriptedProvider(
        [
            action("step-0001", "write_file", {"path": "work/output.txt", "content": "draft"}),
            action("step-0002", "run_command", {"command_id": "check-output"}),
            action("step-0003", "apply_patch", {"path": "work/output.txt", "old_text": "draft", "new_text": "fixed"}),
            action("step-0004", "run_command", {"command_id": "check-output"}),
            action(
                "step-0005",
                "submit_result",
                {
                    "summary": "Created fixed output.",
                    "produced_paths": ["work/output.txt"],
                    "evidence_refs": ["step-0001", "step-0004"],
                },
            ),
        ]
    )
    loop, event_stream_path = make_loop(tmp_path, provider)

    result = loop.run(make_invocation(tmp_path))

    assert result.status == AgentRunStatus.COMPLETED
    assert result.summary == "Created fixed output."
    assert (tmp_path / "work" / "output.txt").read_text(encoding="utf-8") == "fixed"
    assert len(provider.contexts) == 5
    assert provider.contexts[2].observations[-1]["tool"] == "run_command"
    assert '"exit_code":3' in provider.contexts[2].observations[-1]["visible"]
    assert result.event_stream_ref == "artifact://run_001/events.jsonl"
    assert result.events_hash.startswith("sha256:")
    assert len(result.tool_attempts) == 4
    assert [mutation["path"] for mutation in result.workspace_mutations] == ["work/output.txt", "work/output.txt"]
    assert any(artifact["artifact_ref"].endswith("results/step-0005.json") for artifact in result.artifacts)

    event_types = [event["type"] for event in read_jsonl(event_stream_path)]
    assert event_types[0] == "run.started"
    assert event_types[-2:] == ["result.submitted", "run.completed"]
```

- [ ] **Step 2: Run success test and confirm skeleton fails closed**

Run:

```bash
pytest tests/test_agent_loop.py::test_agent_loop_runs_multistep_fake_provider_to_submit_result -v
```

Expected before implementation:

```text
FAILED ... assert <AgentRunStatus.FAILED: 'failed'> == <AgentRunStatus.COMPLETED: 'completed'>
```

- [ ] **Step 3: Implement provider/action loop, tool dispatch, observations, and completed result**

Update `src/atomic_agent/agent_loop.py` by adding imports:

```python
import json

from atomic_agent.action_parser import ActionParseError, parse_agent_action
from atomic_agent.command_tools import CommandPolicy, execute_command_action
from atomic_agent.filesystem_tools import execute_filesystem_action
from atomic_agent.models import AgentAction, AgentActionType
from atomic_agent.path_guard import PathDecisionType
```

Replace the temporary `return self._fail(... max_steps_exceeded ...)` branch in `run` with the real loop:

```python
        requirements = requirements_or_error
        for step in range(1, requirements.max_steps + 1):
            provider_turn_id = f"turn_{step:06d}"
            self.dependencies.event_recorder.record_provider_turn_started(provider_turn_id)
            try:
                provider_output = self.dependencies.provider.complete(
                    ProviderContext(invocation=invocation, step=step, observations=tuple(state.observations))
                )
            except Exception as error:
                self.dependencies.event_recorder.record_provider_turn_failed(
                    provider_turn_id,
                    EventError("provider_failed", str(error), retryable=False, related_ref=provider_turn_id).to_payload(),
                )
                return self._fail(state, "provider_failed", str(error), None)

            provider_artifact = self.dependencies.artifact_writer.write_text(
                f"provider/{provider_turn_id}.txt",
                provider_output,
                truncated_in_observation=False,
            )
            state.artifacts.append(provider_artifact)
            self.dependencies.event_recorder.record_provider_turn_completed(provider_turn_id, provider_artifact)

            try:
                parsed_action = parse_agent_action(provider_output)
            except ActionParseError as error:
                state.parse_failures += 1
                self.dependencies.event_recorder.record_action_rejected(
                    EventError(error.kind, error.message, retryable=True, related_ref=provider_turn_id).to_payload()
                )
                self._append_observation(
                    state,
                    step,
                    provider_turn_id,
                    "action_parser",
                    False,
                    {"ok": False, "error_kind": error.kind, "error_message": error.message},
                    requirements.max_observation_chars,
                )
                if state.parse_failures > requirements.max_parse_failures:
                    return self._fail(state, "action_parse_failed", error.message, None)
                continue

            self.dependencies.event_recorder.record_action_parsed(parsed_action.model_dump(mode="json"))
            decision = self._decide_permission(invocation, parsed_action, requirements.policy_ref)
            self.dependencies.event_recorder.record_permission_decided(
                parsed_action.action_id,
                decision.decision,
                decision.policy_ref,
                decision.reason,
            )
            if decision.decision == "deny":
                return self._fail(state, "policy_denied", decision.reason, parsed_action.action_id)

            if parsed_action.action == AgentActionType.SUBMIT_RESULT:
                return self._submit_result(state, parsed_action)

            result = self._execute_tool_action(state, step, parsed_action, requirements.max_observation_chars)
            if isinstance(result, AgentRunResult):
                return result

        return self._fail(state, "max_steps_exceeded", "max_steps was exhausted before submit_result", None)
```

Add helper methods inside `AgentLoop`:

```python
    def _append_observation(
        self,
        state: _RunState,
        step: int,
        action_id: str,
        tool: str,
        ok: bool,
        payload: dict[str, Any],
        max_observation_chars: int,
    ) -> dict[str, Any]:
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        truncated = len(serialized) > max_observation_chars
        visible = serialized[:max_observation_chars]
        artifact = self.dependencies.artifact_writer.write_text(
            f"observations/step_{step:06d}_{tool}.json",
            serialized,
            truncated_in_observation=truncated,
        )
        state.artifacts.append(artifact)
        observation = {
            "step": step,
            "action_id": action_id,
            "tool": tool,
            "ok": ok,
            "visible": visible,
            "truncated": truncated,
            "artifact": artifact,
        }
        state.observations.append(observation)
        return observation

    def _submit_result(self, state: _RunState, action: AgentAction) -> AgentRunResult:
        summary = action.input["summary"]
        produced_paths = action.input["produced_paths"]
        submission_artifact = self.dependencies.artifact_writer.write_json(
            f"results/{action.action_id}.json",
            action.input,
            truncated_in_observation=False,
        )
        state.artifacts.append(submission_artifact)
        self.dependencies.event_recorder.record_result_submitted(summary, produced_paths, [submission_artifact])
        self.dependencies.event_recorder.record_run_completed(summary)
        return AgentRunResult(
            run_id=self.config.run_id,
            status=AgentRunStatus.COMPLETED,
            event_stream_ref=self.dependencies.event_recorder.event_stream_ref,
            events_hash=self.dependencies.event_recorder.events_hash(),
            tool_attempts=state.tool_attempts,
            workspace_mutations=state.workspace_mutations,
            artifacts=state.artifacts,
            summary=summary,
        )
```

Add `_decide_permission` and `_execute_tool_action` using the existing tools:

```python
    def _decide_permission(self, invocation: AgentInvocation, action: AgentAction, policy_ref: str) -> PermissionDecision:
        if action.action.value not in invocation.tools:
            return PermissionDecision("deny", f"tool_not_enabled:{action.action.value}", policy_ref)
        guard = self.dependencies.filesystem_tools.guard
        if action.action == AgentActionType.WEB_FETCH:
            return PermissionDecision("deny", "web_fetch_not_implemented", policy_ref)
        if action.action in {AgentActionType.LIST_FILES, AgentActionType.SEARCH_FILES}:
            path = action.input.get("path")
            if path is None:
                return PermissionDecision("allow", "read_path_allowed", policy_ref)
            decision = guard.resolve_read_path(path)
            return PermissionDecision("allow" if decision.decision == PathDecisionType.ALLOW else "deny", decision.reason, policy_ref)
        if action.action == AgentActionType.READ_FILE:
            path = action.input.get("path")
            if not isinstance(path, str):
                return PermissionDecision("deny", "path_required", policy_ref)
            decision = guard.resolve_read_path(path)
            return PermissionDecision("allow" if decision.decision == PathDecisionType.ALLOW else "deny", decision.reason, policy_ref)
        if action.action in {AgentActionType.WRITE_FILE, AgentActionType.APPLY_PATCH}:
            path = action.input.get("path")
            if not isinstance(path, str):
                return PermissionDecision("deny", "path_required", policy_ref)
            decision = guard.resolve_write_path(path)
            return PermissionDecision("allow" if decision.decision == PathDecisionType.ALLOW else "deny", decision.reason, policy_ref)
        if action.action == AgentActionType.RUN_COMMAND:
            command_id = action.input.get("command_id")
            if not CommandPolicy.is_valid_command_id(command_id):
                return PermissionDecision("deny", "invalid_command_id", policy_ref)
            if self.dependencies.command_tools.policy.resolve(command_id) is None:
                return PermissionDecision("deny", "command_id_not_declared", policy_ref)
            return PermissionDecision("allow", "command_id_allowed", policy_ref)
        if action.action == AgentActionType.SUBMIT_RESULT:
            if not isinstance(action.input.get("summary"), str) or not action.input["summary"]:
                return PermissionDecision("deny", "submit_result_summary_required", policy_ref)
            produced_paths = action.input.get("produced_paths")
            if not isinstance(produced_paths, list) or any(not isinstance(path, str) for path in produced_paths):
                return PermissionDecision("deny", "submit_result_produced_paths_required", policy_ref)
            evidence_refs = action.input.get("evidence_refs", [])
            if not isinstance(evidence_refs, list) or any(not isinstance(ref, str) for ref in evidence_refs):
                return PermissionDecision("deny", "submit_result_evidence_refs_invalid", policy_ref)
            return PermissionDecision("allow", "submit_result_allowed", policy_ref)
        return PermissionDecision("deny", f"unsupported_action:{action.action.value}", policy_ref)

    def _execute_tool_action(
        self,
        state: _RunState,
        step: int,
        action: AgentAction,
        max_observation_chars: int,
    ) -> AgentRunResult | None:
        tool_attempt_id = f"tool_{step:06d}"
        self.dependencies.event_recorder.record_tool_attempt_started(tool_attempt_id, action.action_id, action.action.value)
        if action.action == AgentActionType.RUN_COMMAND:
            result = execute_command_action(action, self.dependencies.command_tools)
            state.tool_attempts.append({"tool_attempt_id": tool_attempt_id, "action_id": action.action_id, "tool": action.action.value, "ok": result.ok, "data": result.data, "error_kind": result.error_kind})
            if not result.ok:
                self.dependencies.event_recorder.record_tool_attempt_failed(
                    tool_attempt_id,
                    action.action_id,
                    action.action.value,
                    EventError(result.error_kind or "tool_failed", result.error_message or "Command tool failed.", False, action.action_id).to_payload(),
                )
                return self._fail(state, "tool_failed", result.error_message or "Command tool failed.", action.action_id)
            stdout_artifact = self.dependencies.artifact_writer.write_text(
                f"commands/{tool_attempt_id}_stdout.txt",
                result.data["stdout"],
                truncated_in_observation=result.data["stdout_truncated"],
            )
            stderr_artifact = self.dependencies.artifact_writer.write_text(
                f"commands/{tool_attempt_id}_stderr.txt",
                result.data["stderr"],
                truncated_in_observation=result.data["stderr_truncated"],
            )
            state.artifacts.extend([stdout_artifact, stderr_artifact])
            self.dependencies.event_recorder.record_command_completed(
                tool_attempt_id,
                result.data["command_id"],
                result.data["exit_code"],
                stdout_artifact,
                stderr_artifact,
            )
            observation_artifact = self._append_observation(state, step, action.action_id, action.action.value, True, {"ok": True, "result": result.data}, max_observation_chars)
            self.dependencies.event_recorder.record_tool_attempt_completed(tool_attempt_id, action.action_id, action.action.value, observation_artifact["artifact"])
            return None

        result = execute_filesystem_action(action, self.dependencies.filesystem_tools)
        state.tool_attempts.append({"tool_attempt_id": tool_attempt_id, "action_id": action.action_id, "tool": action.action.value, "ok": result.ok, "data": result.data, "error_kind": result.error_kind})
        if not result.ok:
            self.dependencies.event_recorder.record_tool_attempt_failed(
                tool_attempt_id,
                action.action_id,
                action.action.value,
                EventError(result.error_kind or "tool_failed", result.error_message or "Filesystem tool failed.", False, action.action_id).to_payload(),
            )
            return self._fail(state, "tool_failed", result.error_message or "Filesystem tool failed.", action.action_id)
        observation_artifact = self._append_observation(state, step, action.action_id, action.action.value, True, {"ok": True, "result": result.data}, max_observation_chars)
        self.dependencies.event_recorder.record_tool_attempt_completed(tool_attempt_id, action.action_id, action.action.value, observation_artifact["artifact"])
        if action.action in {AgentActionType.WRITE_FILE, AgentActionType.APPLY_PATCH}:
            diff_artifact = self.dependencies.artifact_writer.write_text(
                f"diffs/{tool_attempt_id}.patch",
                result.data["diff"],
                truncated_in_observation=False,
            )
            state.artifacts.append(diff_artifact)
            mutation = {
                "tool_attempt_id": tool_attempt_id,
                "path": result.path,
                "before_hash": result.data["before_hash"],
                "after_hash": result.data["after_hash"],
                "diff": diff_artifact,
            }
            state.workspace_mutations.append(mutation)
            self.dependencies.event_recorder.record_workspace_mutation_recorded(
                tool_attempt_id,
                result.path or "",
                result.data["before_hash"],
                result.data["after_hash"],
                diff_artifact,
            )
        return None
```

- [ ] **Step 4: Run success test and confirm it passes**

Run:

```bash
pytest tests/test_agent_loop.py::test_agent_loop_runs_multistep_fake_provider_to_submit_result -v
```

Expected:

```text
PASSED
```

---

### Task 4: Verify auditable event stream details

**Files:**

- Modify: `tests/test_agent_loop.py`
- Modify: `src/atomic_agent/agent_loop.py` only if tests expose gaps

- [ ] **Step 1: Add event stream detail test**

Append to `tests/test_agent_loop.py`:

```python

def test_agent_loop_records_auditable_event_stream(tmp_path):
    provider = ScriptedProvider(
        [
            action("step-0001", "write_file", {"path": "work/output.txt", "content": "draft"}),
            action("step-0002", "run_command", {"command_id": "check-output"}),
            action("step-0003", "apply_patch", {"path": "work/output.txt", "old_text": "draft", "new_text": "fixed"}),
            action("step-0004", "run_command", {"command_id": "check-output"}),
            action("step-0005", "submit_result", {"summary": "Created fixed output.", "produced_paths": ["work/output.txt"], "evidence_refs": []}),
        ]
    )
    loop, event_stream_path = make_loop(tmp_path, provider)

    result = loop.run(make_invocation(tmp_path))
    events = read_jsonl(event_stream_path)
    event_types = [event["type"] for event in events]

    for required_type in [
        "run.started",
        "provider.turn.started",
        "provider.turn.completed",
        "action.parsed",
        "permission.decided",
        "tool.attempt.started",
        "tool.attempt.completed",
        "workspace.mutation.recorded",
        "command.completed",
        "result.submitted",
        "run.completed",
    ]:
        assert required_type in event_types
    assert [event["sequence"] for event in events] == list(range(1, len(events) + 1))
    assert events[0]["previous_event_hash"] is None
    for previous, current in zip(events, events[1:]):
        assert current["previous_event_hash"] == previous["event_hash"]
    command_events = [event for event in events if event["type"] == "command.completed"]
    assert [event["payload"]["exit_code"] for event in command_events] == [3, 0]
    assert all(event["payload"]["stdout"]["artifact_ref"].startswith("artifact://run_001/commands/") for event in command_events)
    mutation_events = [event for event in events if event["type"] == "workspace.mutation.recorded"]
    assert [event["payload"]["path"] for event in mutation_events] == ["work/output.txt", "work/output.txt"]
    assert all(event["payload"]["diff"]["artifact_ref"].startswith("artifact://run_001/diffs/") for event in mutation_events)
    assert result.events_hash.startswith("sha256:")
```

- [ ] **Step 2: Run event stream detail test**

Run:

```bash
pytest tests/test_agent_loop.py::test_agent_loop_records_auditable_event_stream -v
```

Expected:

```text
PASSED
```

If it fails because an event is missing, fix `AgentLoop` to record the missing event through `EventRecorder`; do not add assertions that weaken the event requirements.

---

### Task 5: Implement invalid JSON retry and fail-closed behavior

**Files:**

- Modify: `tests/test_agent_loop.py`
- Modify: `src/atomic_agent/agent_loop.py` only if tests expose gaps

- [ ] **Step 1: Add invalid JSON retry/failure test**

Append to `tests/test_agent_loop.py`:

```python

def test_agent_loop_fails_closed_after_invalid_json_retry_limit(tmp_path):
    provider = ScriptedProvider(["not json", "still not json"])
    loop, event_stream_path = make_loop(tmp_path, provider)
    invocation = make_invocation(
        tmp_path,
        budgets={"max_steps": 4, "max_parse_failures": 1, "max_observation_chars": 10000},
    )

    result = loop.run(invocation)

    assert result.status == AgentRunStatus.FAILED
    assert result.failure_kind == "action_parse_failed"
    assert len(provider.contexts) == 2
    assert provider.contexts[1].observations[-1]["tool"] == "action_parser"
    events = read_jsonl(event_stream_path)
    assert [event["type"] for event in events].count("action.rejected") == 2
    assert events[-1]["type"] == "run.failed"
```

- [ ] **Step 2: Run invalid JSON test**

Run:

```bash
pytest tests/test_agent_loop.py::test_agent_loop_fails_closed_after_invalid_json_retry_limit -v
```

Expected:

```text
PASSED
```

If it fails, fix parse failure counting so `max_parse_failures = 1` means one retry is allowed and the second consecutive parse failure fails closed.

---

### Task 6: Implement permission denial fail-closed scenarios

**Files:**

- Modify: `tests/test_agent_loop.py`
- Modify: `src/atomic_agent/agent_loop.py` only if tests expose gaps

- [ ] **Step 1: Add disabled tool, write escape, undeclared command, and web_fetch tests**

Append to `tests/test_agent_loop.py`:

```python

def test_agent_loop_denies_tool_not_enabled(tmp_path):
    provider = ScriptedProvider([action("step-0001", "read_file", {"path": "README.md"})])
    loop, event_stream_path = make_loop(tmp_path, provider)
    invocation = make_invocation(tmp_path, tools=["submit_result"])

    result = loop.run(invocation)

    assert result.status == AgentRunStatus.FAILED
    assert result.failure_kind == "policy_denied"
    events = read_jsonl(event_stream_path)
    permission_events = [event for event in events if event["type"] == "permission.decided"]
    assert permission_events[0]["payload"]["decision"] == "deny"
    assert permission_events[0]["payload"]["reason"] == "tool_not_enabled:read_file"
    assert "tool.attempt.started" not in [event["type"] for event in events]


def test_agent_loop_fails_closed_on_write_outside_allowed_set(tmp_path):
    provider = ScriptedProvider([action("step-0001", "write_file", {"path": "outside.txt", "content": "no"})])
    loop, event_stream_path = make_loop(tmp_path, provider)

    result = loop.run(make_invocation(tmp_path))

    assert result.status == AgentRunStatus.FAILED
    assert result.failure_kind == "policy_denied"
    assert not (tmp_path / "outside.txt").exists()
    permission_events = [event for event in read_jsonl(event_stream_path) if event["type"] == "permission.decided"]
    assert permission_events[0]["payload"]["decision"] == "deny"
    assert permission_events[0]["payload"]["reason"] == "write_not_allowed"


def test_agent_loop_fails_closed_on_undeclared_command(tmp_path):
    provider = ScriptedProvider([action("step-0001", "run_command", {"command_id": "missing"})])
    loop, event_stream_path = make_loop(tmp_path, provider)

    result = loop.run(make_invocation(tmp_path))

    assert result.status == AgentRunStatus.FAILED
    assert result.failure_kind == "policy_denied"
    permission_events = [event for event in read_jsonl(event_stream_path) if event["type"] == "permission.decided"]
    assert permission_events[0]["payload"]["decision"] == "deny"
    assert permission_events[0]["payload"]["reason"] == "command_id_not_declared"


def test_agent_loop_denies_web_fetch_until_network_policy_exists(tmp_path):
    provider = ScriptedProvider([action("step-0001", "web_fetch", {"url": "https://example.com"})])
    loop, event_stream_path = make_loop(tmp_path, provider)
    invocation = make_invocation(tmp_path, tools=["web_fetch", "submit_result"])

    result = loop.run(invocation)

    assert result.status == AgentRunStatus.FAILED
    assert result.failure_kind == "policy_denied"
    permission_events = [event for event in read_jsonl(event_stream_path) if event["type"] == "permission.decided"]
    assert permission_events[0]["payload"]["decision"] == "deny"
    assert permission_events[0]["payload"]["reason"] == "web_fetch_not_implemented"
```

- [ ] **Step 2: Run permission denial tests**

Run:

```bash
pytest tests/test_agent_loop.py::test_agent_loop_denies_tool_not_enabled tests/test_agent_loop.py::test_agent_loop_fails_closed_on_write_outside_allowed_set tests/test_agent_loop.py::test_agent_loop_fails_closed_on_undeclared_command tests/test_agent_loop.py::test_agent_loop_denies_web_fetch_until_network_policy_exists -v
```

Expected:

```text
PASSED
```

If any test fails by executing a tool after denial, fix `_decide_permission` / `run` so denial returns failed `AgentRunResult` before `tool.attempt.started`.

---

### Task 7: Implement max steps and provider failure fail-closed scenarios

**Files:**

- Modify: `tests/test_agent_loop.py`
- Modify: `src/atomic_agent/agent_loop.py` only if tests expose gaps

- [ ] **Step 1: Add max steps and provider failure tests**

Append to `tests/test_agent_loop.py`:

```python

def test_agent_loop_fails_closed_when_max_steps_exceeded(tmp_path):
    provider = ScriptedProvider([action("step-0001", "list_files", {})])
    loop, event_stream_path = make_loop(tmp_path, provider)
    invocation = make_invocation(
        tmp_path,
        budgets={"max_steps": 1, "max_parse_failures": 1, "max_observation_chars": 10000},
    )

    result = loop.run(invocation)

    assert result.status == AgentRunStatus.FAILED
    assert result.failure_kind == "max_steps_exceeded"
    assert result.failed_action_ref is None
    events = read_jsonl(event_stream_path)
    assert events[-1]["type"] == "run.failed"
    assert "run.completed" not in [event["type"] for event in events]


def test_agent_loop_records_provider_failure_and_fails_closed(tmp_path):
    provider = ScriptedProvider([RuntimeError("provider unavailable")])
    loop, event_stream_path = make_loop(tmp_path, provider)

    result = loop.run(make_invocation(tmp_path))

    assert result.status == AgentRunStatus.FAILED
    assert result.failure_kind == "provider_failed"
    events = read_jsonl(event_stream_path)
    assert "provider.turn.failed" in [event["type"] for event in events]
    assert events[-1]["type"] == "run.failed"
```

- [ ] **Step 2: Run max steps and provider failure tests**

Run:

```bash
pytest tests/test_agent_loop.py::test_agent_loop_fails_closed_when_max_steps_exceeded tests/test_agent_loop.py::test_agent_loop_records_provider_failure_and_fails_closed -v
```

Expected:

```text
PASSED
```

If max steps returns completed without `submit_result`, remove that path; completion is only valid after `submit_result`.

---

### Task 8: Run focused and full verification

**Files:**

- Verify: `src/atomic_agent/artifacts.py`
- Verify: `src/atomic_agent/agent_loop.py`
- Verify: all tests

- [ ] **Step 1: Run focused new tests**

Run:

```bash
pytest tests/test_artifacts.py tests/test_agent_loop.py -v
```

Expected:

```text
PASSED
```

- [ ] **Step 2: Run existing test suite**

Run:

```bash
pytest tests/test_models.py tests/test_action_parser.py tests/test_path_guard.py tests/test_filesystem_tools.py tests/test_command_tools.py tests/test_event_recorder.py -v
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

- [ ] **Step 4: Check runtime source for forbidden fallback and shell patterns**

Run:

```bash
python - <<'PY'
from pathlib import Path
for path in Path('src/atomic_agent').rglob('*.py'):
    text = path.read_text(encoding='utf-8')
    for needle in ('os.environ', 'getenv', 'dotenv', '.env', 'shell=True', 'TemporaryDirectory', 'NamedTemporaryFile', 'mkstemp', 'fallback'):
        if needle in text:
            print(f'{path}: contains {needle}')
PY
```

Expected:

```text

```

No output means no forbidden fallback / shell pattern appears in runtime source. If output appears in comments or docstrings, either remove the misleading wording or justify it in the implementation review.

- [ ] **Step 5: Check working tree scope**

Run:

```bash
git status --short
```

Expected before docs completion updates:

```text
 M docs/04-implementation-backlog/backlog.md
 M docs/04-implementation-plan/INDEX.md
 M docs/04-implementation-spec/INDEX.md
?? docs/04-implementation-plan/P0-007-minimal-agent-loop-plan.md
?? docs/04-implementation-spec/P0-007-minimal-agent-loop-spec.md
?? src/atomic_agent/agent_loop.py
?? src/atomic_agent/artifacts.py
?? tests/test_agent_loop.py
?? tests/test_artifacts.py
```

Only P0-007 docs, implementation, and tests should be present.

---

### Task 9: Update docs after implementation passes

**Files:**

- Modify: `docs/04-implementation-backlog/backlog.md`
- Modify: `docs/04-implementation-spec/P0-007-minimal-agent-loop-spec.md`
- Modify: `docs/04-implementation-plan/P0-007-minimal-agent-loop-plan.md`
- Modify: `docs/04-implementation-spec/INDEX.md`
- Modify: `docs/04-implementation-plan/INDEX.md`

- [ ] **Step 1: Mark P0-007 completed only after tests pass**

Change `docs/04-implementation-backlog/backlog.md` from:

```markdown
| P0-007 | 实现最小 AgentLoop（智能体循环） | pending | `P0-007-minimal-agent-loop-spec.md`, `runtime-architecture.md` |
```

To:

```markdown
| P0-007 | 实现最小 AgentLoop（智能体循环） | completed | `P0-007-minimal-agent-loop-spec.md`, `runtime-architecture.md` |
```

- [ ] **Step 2: Mark spec implemented**

Change `docs/04-implementation-spec/P0-007-minimal-agent-loop-spec.md` from:

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

Change `docs/04-implementation-plan/P0-007-minimal-agent-loop-plan.md` from:

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
| `P0-007-minimal-agent-loop-spec.md` | draft | 定义 P0-007 minimal AgentLoop（最小智能体循环）的 provider/action/tool/observation/event/result 语义 | 实现 P0-007 前 |
```

Add this completed row:

```markdown
| `P0-007-minimal-agent-loop-spec.md` | 2026-06-05 | 已实现 P0-007 minimal AgentLoop（最小智能体循环），保留为循环规格记录 |
```

- [ ] **Step 5: Move plan index entry to completed / archived**

Remove this active row from `docs/04-implementation-plan/INDEX.md`:

```markdown
| `P0-007-minimal-agent-loop-plan.md` | draft | 实施 P0-007 minimal AgentLoop（最小智能体循环）的 TDD 计划 | 执行 P0-007 时 |
```

Add this completed row:

```markdown
| `P0-007-minimal-agent-loop-plan.md` | 2026-06-05 | 已实施 P0-007 minimal AgentLoop（最小智能体循环），保留为 TDD 实施记录 |
```

- [ ] **Step 6: Run final verification after docs updates**

Run:

```bash
pytest -v
git status --short
```

Expected:

```text
PASSED
```

`git status --short` should show only P0-007 implementation, tests, and required docs/index updates.

---

## Self-Review Checklist

Before implementation is considered ready for user review:

- [ ] Spec coverage: Every requirement in `docs/04-implementation-spec/P0-007-minimal-agent-loop-spec.md` is covered by a task, test, or explicit out-of-scope statement.
- [ ] Placeholder scan: This plan contains no placeholder markers, no deferred behavior inside P0-007 scope, no mock success path, and no silent fallback.
- [ ] Type consistency: `ArtifactWriterConfig`, `ArtifactWriter`, `ProviderContext`, `ProviderAdapter`, `AgentLoopConfig`, `AgentLoopDependencies`, `PermissionDecision`, `AgentLoopError`, and `AgentLoop` names match across tests, implementation steps, and spec.
- [ ] Scope check: No web_fetch implementation, NetworkPolicy, real provider integration, Boardroom adapter, native tool calling, service runner, or external coding agent bridge is included.
- [ ] Reuse check: The plan reuses existing action parser, path guard, filesystem tools, command tools, and event recorder instead of duplicating them.
- [ ] Fail-closed check: invalid invocation, invalid JSON retry exhaustion, provider failure, disabled tool, write outside allowed set, undeclared command, web_fetch, tool failure, and max steps all return failed results or raise clear errors.
- [ ] Evidence check: provider output, observations, diffs, stdout/stderr, and result submission are represented by real artifacts with hashes; provider output alone is not treated as implementation evidence.
- [ ] Verification check: `pytest -v` and forbidden fallback scans pass before any completion claim.
