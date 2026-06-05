# Fail-Closed Budget Limits Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement P0-008 `fail-closed budget limits`（失败关闭预算限制） so `AgentLoop`（智能体循环） fails closed on missing, invalid, or exhausted runtime budgets（运行时预算）, including `max_wall_seconds`（最大墙钟秒数）.

**Architecture:** Extend the existing `agent_loop`（智能体循环） module without creating a second budget system. `AgentInvocation.budgets`（智能体调用请求预算） remains the only budget source, while `AgentLoopDependencies`（智能体循环依赖） gains an explicit injectable monotonic `runtime_clock`（运行时时钟） so wall-time behavior is deterministic in tests and not hidden behind process defaults.

**Tech Stack:** Python 3.11+, `dataclasses`（轻量数据结构）, `typing.Callable`（可调用类型）, `math.isfinite`（有限数字校验）, pytest（测试）, existing `AgentLoop` / `EventRecorder` / `ArtifactWriter` / Pydantic models（现有智能体循环、事件记录器、产物写入器、Pydantic 模型）.

**Status:** implemented

---

## Scope

This plan implements P0-008 only.

In scope:

- Modify `src/atomic_agent/agent_loop.py`（智能体循环模块）.
- Modify `tests/test_agent_loop.py`（智能体循环测试）.
- Require explicit `budgets.max_wall_seconds` in `AgentInvocation.budgets`（调用预算）.
- Add explicit `AgentLoopDependencies.runtime_clock`（运行时时钟依赖）.
- Fail closed before provider turn（模型轮次前）、after provider turn（模型轮次后）、before tool / submit_result（工具或提交前）、and after tool result（工具结果后） when wall-time budget is exhausted.
- Preserve existing `max_steps`（最大步数） and `max_parse_failures`（最大解析失败次数） fail-closed behavior.
- Update P0-008 docs/index/backlog only after implementation and tests pass.

Out of scope:

- No token budget（token 预算）.
- No cost budget（成本预算）.
- No memory budget（内存预算）.
- No network budget（网络预算）.
- No provider API cancellation（模型供应商 API 取消）.
- No command process kill beyond existing command timeout（命令超时） behavior.
- No `web_fetch`（网络获取） or `NetworkPolicy`（网络策略） implementation.
- No Boardroom `AgentRuntimePort` adapter（Boardroom 智能体运行时端口适配器）.
- No README minimal example（最小示例） update.
- No commit unless the user explicitly requests it.

## File Structure

- Modify: `src/atomic_agent/agent_loop.py`
  - Add explicit `runtime_clock: Callable[[], float]` to `AgentLoopDependencies`（智能体循环依赖）.
  - Extend `_RuntimeRequirements`（运行时要求） with `max_wall_seconds: float`.
  - Validate `max_wall_seconds` as a finite positive number.
  - Add small helper methods for runtime clock reading and wall-time budget checks.
  - Insert wall-time checks at provider/tool/result boundaries.
- Modify: `tests/test_agent_loop.py`
  - Add deterministic `FakeRuntimeClock`（确定性假运行时时钟）.
  - Update `make_invocation` default budgets to include `max_wall_seconds`.
  - Update `make_loop` to pass `runtime_clock` into `AgentLoopDependencies`.
  - Add negative tests for missing/invalid wall budget and wall-time exhaustion at each boundary.
  - Keep regression tests for `max_steps` and invalid JSON retry exhaustion.
- Modify after implementation passes: `docs/04-implementation-backlog/backlog.md`
  - Mark P0-008 completed only after tests pass and user accepts implementation.
- Modify after implementation passes: `docs/04-implementation-spec/P0-008-fail-closed-budget-limits-spec.md`
  - Change status from `draft` to `implemented`.
- Modify after implementation passes: `docs/04-implementation-plan/P0-008-fail-closed-budget-limits-plan.md`
  - Change status from `draft` to `implemented`.
- Modify after implementation passes: `docs/04-implementation-spec/INDEX.md`
  - Move P0-008 spec from active to completed / archived.
- Modify after implementation passes: `docs/04-implementation-plan/INDEX.md`
  - Move this plan from active to completed / archived.

---

### Task 1: Add wall-time budget tests and deterministic clock

**Files:**

- Modify: `tests/test_agent_loop.py`

- [ ] **Step 1: Add `math` import and `FakeRuntimeClock` helper**

Modify the imports near the top of `tests/test_agent_loop.py` from:

```python
import json
from pathlib import Path
import sys
```

To:

```python
import json
from pathlib import Path
import sys
```

Add this helper after `fixed_clock()`:

```python
class FakeRuntimeClock:
    def __init__(self, readings):
        self.readings = list(readings)
        self.calls = 0

    def __call__(self) -> float:
        self.calls += 1
        if self.readings:
            return self.readings.pop(0)
        return 0.0
```

- [ ] **Step 2: Require `max_wall_seconds` in default invocation budgets**

Change the default `budgets` block in `make_invocation` from:

```python
        budgets=budgets
        or {
            "max_steps": 8,
            "max_parse_failures": 1,
            "max_observation_chars": 10000,
        },
```

To:

```python
        budgets=budgets
        or {
            "max_steps": 8,
            "max_parse_failures": 1,
            "max_observation_chars": 10000,
            "max_wall_seconds": 30.0,
        },
```

- [ ] **Step 3: Update `make_loop` to accept a runtime clock**

Change the function signature from:

```python
def make_loop(tmp_path, provider):
```

To:

```python
def make_loop(tmp_path, provider, runtime_clock=None):
```

Add this before constructing `AgentLoop`:

```python
    if runtime_clock is None:
        runtime_clock = FakeRuntimeClock([0.0] * 100)
```

Change the `AgentLoopDependencies` construction from:

```python
        AgentLoopDependencies(
            provider=provider,
            filesystem_tools=filesystem_tools,
            command_tools=command_tools,
            event_recorder=recorder,
            artifact_writer=artifact_writer,
        ),
```

To:

```python
        AgentLoopDependencies(
            provider=provider,
            filesystem_tools=filesystem_tools,
            command_tools=command_tools,
            event_recorder=recorder,
            artifact_writer=artifact_writer,
            runtime_clock=runtime_clock,
        ),
```

- [ ] **Step 4: Add missing and invalid `max_wall_seconds` tests**

Append to `tests/test_agent_loop.py`:

```python

def test_agent_loop_fails_closed_when_max_wall_seconds_is_missing(tmp_path):
    provider = ScriptedProvider([])
    loop, event_stream_path = make_loop(tmp_path, provider)
    invocation = make_invocation(
        tmp_path,
        budgets={
            "max_steps": 3,
            "max_parse_failures": 1,
            "max_observation_chars": 10000,
        },
    )

    result = loop.run(invocation)

    assert result.status == AgentRunStatus.FAILED
    assert result.failure_kind == "invalid_invocation"
    assert "max_wall_seconds" in result.failure_message
    assert provider.contexts == []
    events = read_jsonl(event_stream_path)
    assert [event["type"] for event in events] == ["run.started", "run.failed"]


@pytest.mark.parametrize("max_wall_seconds", [0, -1, True, float("nan"), float("inf"), "30"])
def test_agent_loop_fails_closed_when_max_wall_seconds_is_invalid(tmp_path, max_wall_seconds):
    provider = ScriptedProvider([])
    loop, event_stream_path = make_loop(tmp_path, provider)
    invocation = make_invocation(
        tmp_path,
        budgets={
            "max_steps": 3,
            "max_parse_failures": 1,
            "max_observation_chars": 10000,
            "max_wall_seconds": max_wall_seconds,
        },
    )

    result = loop.run(invocation)

    assert result.status == AgentRunStatus.FAILED
    assert result.failure_kind == "invalid_invocation"
    assert "max_wall_seconds" in result.failure_message
    assert provider.contexts == []
    events = read_jsonl(event_stream_path)
    assert [event["type"] for event in events] == ["run.started", "run.failed"]
```

- [ ] **Step 5: Add wall-time exhaustion tests for each runtime boundary**

Append to `tests/test_agent_loop.py`:

```python

def test_agent_loop_fails_closed_when_wall_time_exceeded_before_provider_turn(tmp_path):
    provider = ScriptedProvider([action("step-0001", "submit_result", {"summary": "Done", "produced_paths": [], "evidence_refs": []})])
    runtime_clock = FakeRuntimeClock([0.0, 31.0])
    loop, event_stream_path = make_loop(tmp_path, provider, runtime_clock=runtime_clock)

    result = loop.run(make_invocation(tmp_path))

    assert result.status == AgentRunStatus.FAILED
    assert result.failure_kind == "max_wall_seconds_exceeded"
    assert result.failed_action_ref is None
    assert provider.contexts == []
    events = read_jsonl(event_stream_path)
    assert [event["type"] for event in events] == ["run.started", "run.failed"]


def test_agent_loop_fails_closed_when_wall_time_exceeded_after_provider_turn(tmp_path):
    provider = ScriptedProvider([action("step-0001", "write_file", {"path": "work/output.txt", "content": "draft"})])
    runtime_clock = FakeRuntimeClock([0.0, 0.0, 31.0])
    loop, event_stream_path = make_loop(tmp_path, provider, runtime_clock=runtime_clock)

    result = loop.run(make_invocation(tmp_path))

    assert result.status == AgentRunStatus.FAILED
    assert result.failure_kind == "max_wall_seconds_exceeded"
    assert result.failed_action_ref == "provider_turn_000001"
    assert len(provider.contexts) == 1
    assert not (tmp_path / "work" / "output.txt").exists()
    event_types = [event["type"] for event in read_jsonl(event_stream_path)]
    assert event_types == ["run.started", "provider.turn.started", "provider.turn.completed", "run.failed"]


def test_agent_loop_fails_closed_when_wall_time_exceeded_after_tool_result(tmp_path):
    provider = ScriptedProvider(
        [
            action("step-0001", "write_file", {"path": "work/output.txt", "content": "draft"}),
            action("step-0002", "submit_result", {"summary": "Done", "produced_paths": ["work/output.txt"], "evidence_refs": []}),
        ]
    )
    runtime_clock = FakeRuntimeClock([0.0, 0.0, 0.0, 0.0, 31.0])
    loop, event_stream_path = make_loop(tmp_path, provider, runtime_clock=runtime_clock)

    result = loop.run(make_invocation(tmp_path))

    assert result.status == AgentRunStatus.FAILED
    assert result.failure_kind == "max_wall_seconds_exceeded"
    assert result.failed_action_ref == "step-0001"
    assert len(provider.contexts) == 1
    assert (tmp_path / "work" / "output.txt").read_text(encoding="utf-8") == "draft"
    event_types = [event["type"] for event in read_jsonl(event_stream_path)]
    assert event_types[-4:] == [
        "tool.attempt.started",
        "tool.attempt.completed",
        "workspace.mutation.recorded",
        "run.failed",
    ]
    assert "result.submitted" not in event_types
    assert "run.completed" not in event_types


def test_agent_loop_fails_closed_when_runtime_clock_moves_backwards(tmp_path):
    provider = ScriptedProvider([action("step-0001", "submit_result", {"summary": "Done", "produced_paths": [], "evidence_refs": []})])
    runtime_clock = FakeRuntimeClock([10.0, 9.0])
    loop, event_stream_path = make_loop(tmp_path, provider, runtime_clock=runtime_clock)

    result = loop.run(make_invocation(tmp_path))

    assert result.status == AgentRunStatus.FAILED
    assert result.failure_kind == "invalid_invocation"
    assert provider.contexts == []
    assert [event["type"] for event in read_jsonl(event_stream_path)] == ["run.started", "run.failed"]


def test_agent_loop_fails_closed_when_runtime_clock_returns_non_finite_value(tmp_path):
    provider = ScriptedProvider([])
    runtime_clock = FakeRuntimeClock([float("nan")])
    loop, event_stream_path = make_loop(tmp_path, provider, runtime_clock=runtime_clock)

    result = loop.run(make_invocation(tmp_path))

    assert result.status == AgentRunStatus.FAILED
    assert result.failure_kind == "invalid_invocation"
    assert provider.contexts == []
    assert [event["type"] for event in read_jsonl(event_stream_path)] == ["run.started", "run.failed"]
```

- [ ] **Step 6: Run new wall-time tests and confirm they fail for missing implementation**

Run:

```bash
pytest tests/test_agent_loop.py::test_agent_loop_fails_closed_when_max_wall_seconds_is_missing tests/test_agent_loop.py::test_agent_loop_fails_closed_when_max_wall_seconds_is_invalid tests/test_agent_loop.py::test_agent_loop_fails_closed_when_wall_time_exceeded_before_provider_turn tests/test_agent_loop.py::test_agent_loop_fails_closed_when_wall_time_exceeded_after_provider_turn tests/test_agent_loop.py::test_agent_loop_fails_closed_when_wall_time_exceeded_after_tool_result tests/test_agent_loop.py::test_agent_loop_fails_closed_when_runtime_clock_moves_backwards tests/test_agent_loop.py::test_agent_loop_fails_closed_when_runtime_clock_returns_non_finite_value -v
```

Expected before implementation:

```text
TypeError: AgentLoopDependencies.__init__() got an unexpected keyword argument 'runtime_clock'
```

---

### Task 2: Add explicit runtime clock dependency and budget validation

**Files:**

- Modify: `src/atomic_agent/agent_loop.py`

- [ ] **Step 1: Add imports for explicit clock and finite number validation**

Change imports near the top of `src/atomic_agent/agent_loop.py` from:

```python
from dataclasses import dataclass, field
import json
from typing import Any, Literal, Protocol
```

To:

```python
from collections.abc import Callable
from dataclasses import dataclass, field
import json
import math
from typing import Any, Literal, Protocol
```

- [ ] **Step 2: Add `runtime_clock` to dependencies**

Change `AgentLoopDependencies` from:

```python
@dataclass(frozen=True)
class AgentLoopDependencies:
    provider: ProviderAdapter
    filesystem_tools: FilesystemTools
    command_tools: CommandTools
    event_recorder: EventRecorder
    artifact_writer: ArtifactWriter
```

To:

```python
@dataclass(frozen=True)
class AgentLoopDependencies:
    provider: ProviderAdapter
    filesystem_tools: FilesystemTools
    command_tools: CommandTools
    event_recorder: EventRecorder
    artifact_writer: ArtifactWriter
    runtime_clock: Callable[[], float]
```

- [ ] **Step 3: Extend runtime requirements with `max_wall_seconds`**

Change `_RuntimeRequirements` from:

```python
@dataclass(frozen=True)
class _RuntimeRequirements:
    policy_ref: str
    max_steps: int
    max_parse_failures: int
    max_observation_chars: int
```

To:

```python
@dataclass(frozen=True)
class _RuntimeRequirements:
    policy_ref: str
    max_steps: int
    max_parse_failures: int
    max_observation_chars: int
    max_wall_seconds: float
```

- [ ] **Step 4: Validate `max_wall_seconds` in `_runtime_requirements`**

Add this after `max_observation_chars = invocation.budgets.get("max_observation_chars")`:

```python
        max_wall_seconds = invocation.budgets.get("max_wall_seconds")
```

Add this validation after the `max_observation_chars` validation:

```python
        if (
            not isinstance(max_wall_seconds, int | float)
            or isinstance(max_wall_seconds, bool)
            or not math.isfinite(max_wall_seconds)
            or max_wall_seconds <= 0
        ):
            return "budgets.max_wall_seconds must be a finite positive number"
```

Change the return from:

```python
        return _RuntimeRequirements(policy_ref, max_steps, max_parse_failures, max_observation_chars)
```

To:

```python
        return _RuntimeRequirements(
            policy_ref=policy_ref,
            max_steps=max_steps,
            max_parse_failures=max_parse_failures,
            max_observation_chars=max_observation_chars,
            max_wall_seconds=float(max_wall_seconds),
        )
```

- [ ] **Step 5: Add runtime clock helper methods**

Add these methods inside `AgentLoop`, before `_runtime_requirements`:

```python
    def _read_runtime_clock(self) -> float | str:
        try:
            current = self.dependencies.runtime_clock()
        except Exception as error:
            message = str(error) or error.__class__.__name__
            return f"runtime_clock failed: {message}"
        if not isinstance(current, int | float) or isinstance(current, bool) or not math.isfinite(current):
            return "runtime_clock must return a finite number of monotonic seconds"
        return float(current)

    def _check_wall_time_budget(
        self,
        started_at: float,
        requirements: _RuntimeRequirements,
        phase: str,
    ) -> tuple[str, str] | None:
        current = self._read_runtime_clock()
        if isinstance(current, str):
            return "invalid_invocation", current
        elapsed_seconds = current - started_at
        if elapsed_seconds < 0:
            return "invalid_invocation", "runtime_clock must be monotonic and cannot move backwards"
        if elapsed_seconds > requirements.max_wall_seconds:
            return "max_wall_seconds_exceeded", f"max_wall_seconds exceeded {phase}"
        return None
```

- [ ] **Step 6: Run budget validation tests**

Run:

```bash
pytest tests/test_agent_loop.py::test_agent_loop_fails_closed_when_max_wall_seconds_is_missing tests/test_agent_loop.py::test_agent_loop_fails_closed_when_max_wall_seconds_is_invalid tests/test_agent_loop.py::test_agent_loop_fails_closed_when_runtime_clock_returns_non_finite_value -v
```

Expected after this task:

```text
PASSED
```

Wall-time exhaustion tests may still fail until Task 3 inserts checks into the loop.

---

### Task 3: Insert wall-time checks into AgentLoop boundaries

**Files:**

- Modify: `src/atomic_agent/agent_loop.py`

- [ ] **Step 1: Read `runtime_clock` after runtime requirements validation**

In `AgentLoop.run`, after:

```python
        requirements = requirements_or_error
```

Add:

```python
        started_at_or_error = self._read_runtime_clock()
        if isinstance(started_at_or_error, str):
            return self._fail(
                state=state,
                failure_kind="invalid_invocation",
                failure_message=started_at_or_error,
                failed_action_ref=None,
            )
        started_at = started_at_or_error
```

- [ ] **Step 2: Check wall-time budget before provider turn**

At the start of the loop body, immediately after:

```python
        for step in range(1, requirements.max_steps + 1):
            provider_turn_id = f"provider_turn_{step:06d}"
```

Add:

```python
            wall_time_failure = self._check_wall_time_budget(started_at, requirements, "before provider turn")
            if wall_time_failure is not None:
                failure_kind, failure_message = wall_time_failure
                return self._fail(
                    state=state,
                    failure_kind=failure_kind,
                    failure_message=failure_message,
                    failed_action_ref=None,
                )
```

- [ ] **Step 3: Check wall-time budget after provider output is recorded**

After:

```python
            self.dependencies.event_recorder.record_provider_turn_completed(provider_turn_id, output_artifact)
```

Add:

```python
            wall_time_failure = self._check_wall_time_budget(started_at, requirements, "after provider turn")
            if wall_time_failure is not None:
                failure_kind, failure_message = wall_time_failure
                return self._fail(
                    state=state,
                    failure_kind=failure_kind,
                    failure_message=failure_message,
                    failed_action_ref=provider_turn_id,
                )
```

- [ ] **Step 4: Check wall-time budget before submit_result or tool execution**

After the permission denial branch:

```python
            if decision.decision == "deny":
                self.dependencies.event_recorder.record_action_rejected(
                    EventError("policy_denied", decision.reason, retryable=False, related_ref=action.action_id).to_payload()
                )
                return self._fail(state, "policy_denied", decision.reason, action.action_id)
```

Add:

```python
            wall_time_failure = self._check_wall_time_budget(started_at, requirements, "before action execution")
            if wall_time_failure is not None:
                failure_kind, failure_message = wall_time_failure
                return self._fail(
                    state=state,
                    failure_kind=failure_kind,
                    failure_message=failure_message,
                    failed_action_ref=action.action_id,
                )
```

- [ ] **Step 5: Check wall-time budget after successful tool result recording**

After:

```python
            if not result.ok:
                message = result.error_message or "tool action failed"
                return self._fail(state, "tool_failed", message, action.action_id)
```

Add:

```python
            wall_time_failure = self._check_wall_time_budget(started_at, requirements, "after tool execution")
            if wall_time_failure is not None:
                failure_kind, failure_message = wall_time_failure
                return self._fail(
                    state=state,
                    failure_kind=failure_kind,
                    failure_message=failure_message,
                    failed_action_ref=action.action_id,
                )
```

- [ ] **Step 6: Run wall-time exhaustion tests**

Run:

```bash
pytest tests/test_agent_loop.py::test_agent_loop_fails_closed_when_wall_time_exceeded_before_provider_turn tests/test_agent_loop.py::test_agent_loop_fails_closed_when_wall_time_exceeded_after_provider_turn tests/test_agent_loop.py::test_agent_loop_fails_closed_when_wall_time_exceeded_after_tool_result tests/test_agent_loop.py::test_agent_loop_fails_closed_when_runtime_clock_moves_backwards -v
```

Expected:

```text
PASSED
```

If `test_agent_loop_fails_closed_when_runtime_clock_moves_backwards` returns `max_wall_seconds_exceeded` instead of `invalid_invocation`, ensure `_check_wall_time_budget` checks `elapsed_seconds < 0` before checking `elapsed_seconds > max_wall_seconds`.

---

### Task 4: Preserve existing max steps and invalid JSON retry behavior

**Files:**

- Modify: `tests/test_agent_loop.py`
- Modify: `src/atomic_agent/agent_loop.py` only if regressions appear

- [ ] **Step 1: Update existing max steps test budgets to include `max_wall_seconds`**

In the parameterized `max_steps_exceeded` case, change:

```python
{"budgets": {"max_steps": 1, "max_parse_failures": 1, "max_observation_chars": 10000}},
```

To:

```python
{"budgets": {"max_steps": 1, "max_parse_failures": 1, "max_observation_chars": 10000, "max_wall_seconds": 30.0}},
```

- [ ] **Step 2: Add a focused invalid JSON retry regression test with wall budget**

Append to `tests/test_agent_loop.py`:

```python

def test_agent_loop_preserves_invalid_json_retry_limit_with_wall_budget(tmp_path):
    provider = ScriptedProvider(["not json", "still not json"])
    runtime_clock = FakeRuntimeClock([0.0] * 100)
    loop, event_stream_path = make_loop(tmp_path, provider, runtime_clock=runtime_clock)
    invocation = make_invocation(
        tmp_path,
        budgets={
            "max_steps": 4,
            "max_parse_failures": 1,
            "max_observation_chars": 10000,
            "max_wall_seconds": 30.0,
        },
    )

    result = loop.run(invocation)

    assert result.status == AgentRunStatus.FAILED
    assert result.failure_kind == "action_parse_failed"
    assert len(provider.contexts) == 2
    event_types = [event["type"] for event in read_jsonl(event_stream_path)]
    assert event_types.count("action.rejected") == 2
    assert event_types[-1] == "run.failed"
```

- [ ] **Step 3: Add a focused max steps regression test with wall budget**

Append to `tests/test_agent_loop.py`:

```python

def test_agent_loop_preserves_max_steps_failure_with_wall_budget(tmp_path):
    (tmp_path / "work").mkdir()
    provider = ScriptedProvider([action("step-0001", "list_files", {"path": "work", "recursive": False})])
    runtime_clock = FakeRuntimeClock([0.0] * 100)
    loop, event_stream_path = make_loop(tmp_path, provider, runtime_clock=runtime_clock)
    invocation = make_invocation(
        tmp_path,
        budgets={
            "max_steps": 1,
            "max_parse_failures": 1,
            "max_observation_chars": 10000,
            "max_wall_seconds": 30.0,
        },
    )

    result = loop.run(invocation)

    assert result.status == AgentRunStatus.FAILED
    assert result.failure_kind == "max_steps_exceeded"
    assert result.failed_action_ref is None
    event_types = [event["type"] for event in read_jsonl(event_stream_path)]
    assert event_types[-1] == "run.failed"
    assert "run.completed" not in event_types
```

- [ ] **Step 4: Run regression tests**

Run:

```bash
pytest tests/test_agent_loop.py::test_agent_loop_preserves_invalid_json_retry_limit_with_wall_budget tests/test_agent_loop.py::test_agent_loop_preserves_max_steps_failure_with_wall_budget tests/test_agent_loop.py::test_agent_loop_fails_closed_for_runtime_errors -v
```

Expected:

```text
PASSED
```

If existing parameterized tests fail because custom budgets omit `max_wall_seconds`, update those test invocations to include explicit `max_wall_seconds`; do not add a default in runtime code.

---

### Task 5: Run focused and full verification

**Files:**

- Verify: `src/atomic_agent/agent_loop.py`
- Verify: `tests/test_agent_loop.py`
- Verify: all tests

- [ ] **Step 1: Run focused AgentLoop tests**

Run:

```bash
pytest tests/test_agent_loop.py -v
```

Expected:

```text
PASSED
```

- [ ] **Step 2: Run related runtime tests**

Run:

```bash
pytest tests/test_action_parser.py tests/test_artifacts.py tests/test_command_tools.py tests/test_event_recorder.py tests/test_filesystem_tools.py tests/test_models.py tests/test_path_guard.py -v
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

- [ ] **Step 4: Check runtime source for forbidden fallback and budget default patterns**

Run:

```bash
python - <<'PY'
from pathlib import Path
for path in Path('src/atomic_agent').rglob('*.py'):
    text = path.read_text(encoding='utf-8')
    for needle in ('os.environ', 'getenv', 'dotenv', '.env', 'fallback'):
        if needle in text:
            print(f'{path}: contains {needle}')
loop_text = Path('src/atomic_agent/agent_loop.py').read_text(encoding='utf-8')
for forbidden in ('time.monotonic', 'time.time', 'max_wall_seconds = 30', 'max_steps = 8', 'max_parse_failures = 1'):
    if forbidden in loop_text:
        print(f'src/atomic_agent/agent_loop.py: forbidden hidden budget/default pattern: {forbidden}')
PY
```

Expected:

```text

```

No output means runtime source does not read environment fallback or hide budget defaults. If output appears in comments or docs, remove misleading wording or explain it in implementation review; if output appears in executable code, fix it.

- [ ] **Step 5: Check working tree scope**

Run:

```bash
git status --short
```

Expected before docs completion updates:

```text
 M docs/04-implementation-plan/INDEX.md
 M docs/04-implementation-spec/INDEX.md
 M tests/test_agent_loop.py
 M src/atomic_agent/agent_loop.py
?? docs/04-implementation-plan/P0-008-fail-closed-budget-limits-plan.md
?? docs/04-implementation-spec/P0-008-fail-closed-budget-limits-spec.md
```

Only P0-008 docs, implementation, tests, and required index updates should be present.

---

### Task 6: Update docs after implementation passes

**Files:**

- Modify: `docs/04-implementation-backlog/backlog.md`
- Modify: `docs/04-implementation-spec/P0-008-fail-closed-budget-limits-spec.md`
- Modify: `docs/04-implementation-plan/P0-008-fail-closed-budget-limits-plan.md`
- Modify: `docs/04-implementation-spec/INDEX.md`
- Modify: `docs/04-implementation-plan/INDEX.md`

- [ ] **Step 1: Mark P0-008 completed only after tests pass**

Change `docs/04-implementation-backlog/backlog.md` from:

```markdown
| P0-008 | 实现 fail-closed budget limits（失败关闭预算限制） | pending | `mvp-acceptance.md` |
```

To:

```markdown
| P0-008 | 实现 fail-closed budget limits（失败关闭预算限制） | completed | `P0-008-fail-closed-budget-limits-spec.md`, `mvp-acceptance.md` |
```

- [ ] **Step 2: Mark spec implemented**

Change `docs/04-implementation-spec/P0-008-fail-closed-budget-limits-spec.md` from:

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

Change `docs/04-implementation-plan/P0-008-fail-closed-budget-limits-plan.md` from:

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
| `P0-008-fail-closed-budget-limits-spec.md` | draft | 定义 P0-008 fail-closed budget limits（失败关闭预算限制）的显式预算、最大步数、解析重试和最大墙钟时间语义 | 实现 P0-008 前 |
```

Add this completed row:

```markdown
| `P0-008-fail-closed-budget-limits-spec.md` | 2026-06-05 | 已实现 P0-008 fail-closed budget limits（失败关闭预算限制），保留为预算语义规格记录 |
```

- [ ] **Step 5: Move plan index entry to completed / archived**

Remove this active row from `docs/04-implementation-plan/INDEX.md`:

```markdown
| `P0-008-fail-closed-budget-limits-plan.md` | draft | 实施 P0-008 fail-closed budget limits（失败关闭预算限制）的 TDD 计划 | 执行 P0-008 时 |
```

Add this completed row:

```markdown
| `P0-008-fail-closed-budget-limits-plan.md` | 2026-06-05 | 已实施 P0-008 fail-closed budget limits（失败关闭预算限制），保留为 TDD 实施记录 |
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

`git status --short` should show only P0-008 implementation, tests, and required docs/index/backlog updates.

---

## Self-Review Checklist

Before implementation is considered ready for user review:

- [ ] Spec coverage: Every requirement in `docs/04-implementation-spec/P0-008-fail-closed-budget-limits-spec.md` is covered by a task, test, or explicit out-of-scope statement.
- [ ] Placeholder scan: This plan contains no placeholder markers, no deferred behavior inside P0-008 scope, no mock success path, and no silent fallback.
- [ ] Type consistency: `AgentLoopDependencies.runtime_clock`, `_RuntimeRequirements.max_wall_seconds`, `FakeRuntimeClock`, `max_wall_seconds_exceeded`, `invalid_invocation`, `action_parse_failed`, and `max_steps_exceeded` names match across tests, implementation steps, and spec.
- [ ] Scope check: No token budget, cost budget, provider cancellation, command kill, network policy, Boardroom adapter, README minimal example, or external agent bridge is included.
- [ ] Reuse check: The plan reuses existing `AgentInvocation.budgets`, `AgentLoop`, `EventRecorder`, `ArtifactWriter`, and parser/tool modules instead of creating a second budget implementation.
- [ ] Fail-closed check: Missing/invalid budgets, invalid runtime clock, backwards runtime clock, exhausted max steps, exhausted parse retry budget, and exhausted wall-time budget all return failed results with terminal events.
- [ ] Evidence check: Wall-time failure after provider/tool preserves already-recorded real events and artifacts; it does not delete facts or fake completion.
- [ ] Verification check: `pytest -v` and forbidden fallback scans pass before any completion claim.
