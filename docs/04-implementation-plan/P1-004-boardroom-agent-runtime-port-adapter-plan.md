# Boardroom AgentRuntimePort Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement P1-004 `Boardroom AgentRuntimePort adapter`（Boardroom 智能体运行时端口适配器） so callers can invoke the existing runtime through `AgentRuntimePort.invoke(invocation: AgentInvocation) -> AgentRunResult` without adding Boardroom governance state or configuration fallback.

**Architecture:** Add a small `runtime_port` module（运行时端口模块） that defines protocol boundaries and a composition-based adapter around any runner exposing `run(invocation)`. The adapter delegates to the existing `AgentLoop`（智能体循环） interface, validates only Python boundary types, returns `AgentRunResult`（智能体运行结果） unchanged, and deliberately avoids `ExecutionPackage`（执行包） mapping, event creation, artifact creation, or Boardroom closeout（收尾） decisions.

**Tech Stack:** Python 3.11+, `typing.Protocol`（协议类型）, existing Pydantic models（现有 Pydantic 模型）, pytest（测试框架）, existing atomic-agent runtime modules（现有原子智能体运行时模块）.

**Status:** implemented

---

## Scope

This plan implements P1-004 only.

In scope:

- Create `src/atomic_agent/runtime_port.py`（运行时端口模块）.
- Create `tests/test_runtime_port.py`（运行时端口契约测试）.
- Modify `src/atomic_agent/__init__.py` to export public port types（公共端口类型）.
- After implementation and verification pass, update P1-004 spec / plan / backlog / indexes from draft to implemented / completed.
- Verify no Boardroom governance events（治理事件）, environment fallback（环境兜底）, or default allow-all（默认全允许） patterns were introduced.

Out of scope:

- No Boardroom OS `ExecutionPackage`（执行包） model.
- No `ExecutionPackage -> AgentInvocation`（执行包到智能体调用请求） mapping.
- No real provider integration（真实模型供应商集成）.
- No new tools（新工具）.
- No new permission policy（新权限策略）.
- No new event types（新事件类型）.
- No `.env`, `os.environ`, `getenv`, or dotenv-based runtime configuration fallback（运行时配置兜底）.
- No Boardroom ticket completion（工单完成） or closeout commit（收尾提交） decision.
- No git commit unless the user explicitly requests one.

## File Structure

- Create: `tests/test_runtime_port.py`
  - Tests adapter delegation, completed result passthrough, failed result passthrough, invalid invocation rejection, invalid runner result rejection, exception propagation, and a real `AgentLoop`（智能体循环） integration path.
- Create: `src/atomic_agent/runtime_port.py`
  - Defines `AgentRuntimePort`（智能体运行时端口协议）, `AgentRuntimeRunner`（智能体运行时执行器协议）, and `BoardroomAgentRuntimePortAdapter`（Boardroom 智能体运行时端口适配器）.
- Modify: `src/atomic_agent/__init__.py`
  - Exports the new public runtime port types.
- Modify after implementation passes: `docs/04-implementation-backlog/backlog.md`
  - Marks P1-004 completed.
- Modify after implementation passes: `docs/04-implementation-spec/P1-004-boardroom-agent-runtime-port-adapter-spec.md`
  - Changes status from `draft` to `implemented`.
- Modify after implementation passes: `docs/04-implementation-plan/P1-004-boardroom-agent-runtime-port-adapter-plan.md`
  - Changes status from `draft` to `implemented`.
- Modify after implementation passes: `docs/04-implementation-spec/INDEX.md`
  - Moves P1-004 spec from active draft to completed / archived.
- Modify after implementation passes: `docs/04-implementation-plan/INDEX.md`
  - Moves this plan from active draft to completed / archived.
- Modify after implementation passes: `docs/INDEX.md`
  - Removes P1-004 draft active pointers once the implementation is completed and indexed as completed.

---

### Task 1: Add failing contract tests for the runtime port adapter

**Files:**

- Create: `tests/test_runtime_port.py`
- Verify: `src/atomic_agent/agent_loop.py`
- Verify: `src/atomic_agent/models.py`

- [ ] **Step 0: Confirm existing runtime interface compatibility**

Run:

```bash
grep -A 5 "def run" src/atomic_agent/agent_loop.py
grep "class Agent" src/atomic_agent/models.py
```

Expected evidence:

```text
def run(self, invocation: AgentInvocation) -> AgentRunResult:
class AgentRunStatus(str, Enum):
class AgentActionType(str, Enum):
class AgentEventType(str, Enum):
class AgentInvocation(StrictModel):
class AgentAction(StrictModel):
class AgentEvent(StrictModel):
class AgentRunResult(StrictModel):
```

This confirms the existing `AgentLoop`（智能体循环） already matches the planned `AgentRuntimeRunner`（智能体运行时执行器） protocol. If the signature differs, stop and revise this plan before writing tests.

- [ ] **Step 1: Write the failing contract tests**

Create `tests/test_runtime_port.py` with this exact content:

```python
import pytest

from atomic_agent.examples.minimal_fake_loop import (
    EXPECTED_OUTPUT_CONTENT,
    WORKSPACE_OUTPUT_PATH,
    ExamplePaths,
    build_invocation,
    build_loop,
    prepare_paths,
)
from atomic_agent.models import AgentInvocation, AgentRunResult, AgentRunStatus
from atomic_agent.runtime_port import BoardroomAgentRuntimePortAdapter


BANNED_GOVERNANCE_FIELDS = {
    "ticket_completed",
    "closeout_committed",
    "governance_status",
    "evidence_verified",
    "source_inventory_accepted",
}


class RecordingRunner:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.invocations = []

    def run(self, invocation):
        self.invocations.append(invocation)
        if self.error is not None:
            raise self.error
        return self.result


def make_invocation():
    return AgentInvocation(
        invocation_id="inv_boardroom_001",
        task="Run a controlled atomic-agent invocation for Boardroom evidence input.",
        workspace_root="/workspace/project",
        allowed_write_set=["work/"],
        tools=["write_file", "run_command", "submit_result"],
        permission_policy={"policy_ref": "policy://boardroom/runtime-port"},
        provider_profile={"provider": "fake", "model": "scripted"},
        budgets={
            "max_steps": 8,
            "max_parse_failures": 1,
            "max_observation_chars": 10000,
            "max_wall_seconds": 30.0,
        },
        output_requirements={"summary": True, "event_stream": True, "artifacts": True},
        metadata={"boardroom_ticket": "ticket-123"},
    )


def make_completed_result():
    return AgentRunResult(
        run_id="run_boardroom_001",
        status=AgentRunStatus.COMPLETED,
        event_stream_ref="artifact://run_boardroom_001/events.jsonl",
        events_hash="sha256:" + "a" * 64,
        tool_attempts=[
            {
                "tool_attempt_id": "tool_attempt_000001",
                "action_id": "step-0001",
                "tool": "write_file",
                "ok": True,
            }
        ],
        workspace_mutations=[
            {
                "tool_attempt_id": "tool_attempt_000001",
                "action_id": "step-0001",
                "tool": "write_file",
                "path": "work/output.txt",
            }
        ],
        artifacts=[
            {
                "artifact_ref": "artifact://run_boardroom_001/results/step-0002.json",
                "sha256": "sha256:" + "b" * 64,
                "size_bytes": 42,
                "truncated_in_observation": False,
            }
        ],
        summary="Runtime submitted a result for Boardroom evidence verification.",
    )


def make_failed_result():
    return AgentRunResult(
        run_id="run_boardroom_002",
        status=AgentRunStatus.FAILED,
        event_stream_ref="artifact://run_boardroom_002/events.jsonl",
        events_hash="sha256:" + "c" * 64,
        tool_attempts=[],
        workspace_mutations=[],
        artifacts=[],
        summary="Run failed closed: command_id is not declared in command policy",
        failure_kind="policy_denied",
        failure_message="command_id is not declared in command policy",
        failed_action_ref="step-command",
    )


def assert_no_governance_fields(result):
    payload = result.model_dump(mode="json")
    assert BANNED_GOVERNANCE_FIELDS.isdisjoint(payload)


def test_adapter_invokes_runner_with_same_invocation_and_returns_completed_result_unchanged():
    invocation = make_invocation()
    expected_result = make_completed_result()
    runner = RecordingRunner(expected_result)
    adapter = BoardroomAgentRuntimePortAdapter(runner)

    result = adapter.invoke(invocation)

    assert result is expected_result
    assert runner.invocations == [invocation]
    assert result.status == AgentRunStatus.COMPLETED
    assert result.event_stream_ref == "artifact://run_boardroom_001/events.jsonl"
    assert result.events_hash == "sha256:" + "a" * 64
    assert result.tool_attempts == expected_result.tool_attempts
    assert result.workspace_mutations == expected_result.workspace_mutations
    assert result.artifacts == expected_result.artifacts
    assert result.summary == expected_result.summary
    assert_no_governance_fields(result)


def test_adapter_returns_failed_result_unchanged_without_converting_to_success():
    invocation = make_invocation()
    expected_result = make_failed_result()
    runner = RecordingRunner(expected_result)
    adapter = BoardroomAgentRuntimePortAdapter(runner)

    result = adapter.invoke(invocation)

    assert result is expected_result
    assert runner.invocations == [invocation]
    assert result.status == AgentRunStatus.FAILED
    assert result.failure_kind == "policy_denied"
    assert result.failure_message == "command_id is not declared in command policy"
    assert result.failed_action_ref == "step-command"
    assert_no_governance_fields(result)


def test_adapter_rejects_non_agent_invocation_without_calling_runner():
    runner = RecordingRunner(make_completed_result())
    adapter = BoardroomAgentRuntimePortAdapter(runner)

    with pytest.raises(TypeError, match="AgentRuntimePort.invoke requires AgentInvocation"):
        adapter.invoke({"invocation_id": "not-a-model"})

    assert runner.invocations == []


def test_adapter_rejects_runner_result_that_is_not_agent_run_result():
    invocation = make_invocation()
    runner = RecordingRunner({"status": "completed"})
    adapter = BoardroomAgentRuntimePortAdapter(runner)

    with pytest.raises(TypeError, match="runner.run must return AgentRunResult"):
        adapter.invoke(invocation)

    assert runner.invocations == [invocation]


def test_adapter_propagates_runner_exception_without_faking_result():
    invocation = make_invocation()
    runner = RecordingRunner(error=RuntimeError("runtime unavailable"))
    adapter = BoardroomAgentRuntimePortAdapter(runner)

    with pytest.raises(RuntimeError, match="runtime unavailable"):
        adapter.invoke(invocation)

    assert runner.invocations == [invocation]


def test_adapter_works_with_real_agent_loop(tmp_path):
    paths = ExamplePaths(
        workspace=tmp_path / "workspace",
        event_stream=tmp_path / "events" / "events.jsonl",
        artifact_root=tmp_path / "artifacts",
        result=tmp_path / "result.json",
    )
    prepare_paths(paths)
    loop = build_loop("runtime_port_integration", paths)
    invocation = build_invocation(paths)
    adapter = BoardroomAgentRuntimePortAdapter(loop)

    result = adapter.invoke(invocation)

    assert isinstance(result, AgentRunResult)
    assert result.status == AgentRunStatus.COMPLETED
    assert result.run_id == "runtime_port_integration"
    assert (paths.workspace / WORKSPACE_OUTPUT_PATH).read_text(encoding="utf-8") == EXPECTED_OUTPUT_CONTENT
    assert result.event_stream_ref == "artifact://runtime_port_integration/events.jsonl"
    assert [attempt["tool"] for attempt in result.tool_attempts] == [
        "write_file",
        "run_command",
        "apply_patch",
        "run_command",
    ]
    assert [mutation["path"] for mutation in result.workspace_mutations] == [
        WORKSPACE_OUTPUT_PATH,
        WORKSPACE_OUTPUT_PATH,
    ]
    assert_no_governance_fields(result)
```

- [ ] **Step 2: Run the new tests and confirm they fail before implementation**

Run:

```bash
python -m pytest tests/test_runtime_port.py -q
```

Expected before implementation:

```text
ERROR tests/test_runtime_port.py
```

The failure reason should show that `atomic_agent.runtime_port`（原子智能体运行时端口模块） does not exist yet.

---

### Task 2: Implement the runtime port adapter

**Files:**

- Create: `src/atomic_agent/runtime_port.py`
- Test: `tests/test_runtime_port.py`

- [ ] **Step 1: Create the runtime port module**

Create `src/atomic_agent/runtime_port.py` with this exact content:

```python
from typing import Protocol

from atomic_agent.models import AgentInvocation, AgentRunResult


class AgentRuntimePort(Protocol):
    def invoke(self, invocation: AgentInvocation) -> AgentRunResult:
        ...


class AgentRuntimeRunner(Protocol):
    def run(self, invocation: AgentInvocation) -> AgentRunResult:
        ...


class BoardroomAgentRuntimePortAdapter:
    def __init__(self, runner: AgentRuntimeRunner):
        self.runner = runner

    def invoke(self, invocation: AgentInvocation) -> AgentRunResult:
        if not isinstance(invocation, AgentInvocation):
            raise TypeError("AgentRuntimePort.invoke requires AgentInvocation")
        result = self.runner.run(invocation)
        if not isinstance(result, AgentRunResult):
            raise TypeError("runner.run must return AgentRunResult")
        return result
```

- [ ] **Step 2: Run the contract tests and confirm adapter behavior passes**

Run:

```bash
python -m pytest tests/test_runtime_port.py -q
```

Expected:

```text
7 passed
```

If any test fails, fix only `src/atomic_agent/runtime_port.py` or the test assertion that contradicts the P1-004 spec. Do not add Boardroom state mapping, event creation, or fallback configuration to make tests pass.

---

### Task 3: Export public runtime port types from the package root

**Files:**

- Modify: `src/atomic_agent/__init__.py`
- Modify: `tests/test_runtime_port.py`

- [ ] **Step 1: Add a failing export test**

Append this test to `tests/test_runtime_port.py`:

```python

def test_package_exports_runtime_port_types():
    from atomic_agent import AgentRuntimePort, AgentRuntimeRunner, BoardroomAgentRuntimePortAdapter as ExportedAdapter

    assert AgentRuntimePort.__name__ == "AgentRuntimePort"
    assert AgentRuntimeRunner.__name__ == "AgentRuntimeRunner"
    assert ExportedAdapter is BoardroomAgentRuntimePortAdapter
```

- [ ] **Step 2: Run the export test and confirm it fails before package export**

Run:

```bash
python -m pytest tests/test_runtime_port.py::test_package_exports_runtime_port_types -q
```

Expected before export:

```text
FAILED tests/test_runtime_port.py::test_package_exports_runtime_port_types
```

The failure reason should mention that `AgentRuntimePort`（智能体运行时端口协议） cannot be imported from `atomic_agent`（原子智能体包）.

- [ ] **Step 3: Update package exports**

Replace `src/atomic_agent/__init__.py` with this exact content:

```python
__version__ = "0.0.0"

from atomic_agent.runtime_port import AgentRuntimePort, AgentRuntimeRunner, BoardroomAgentRuntimePortAdapter

__all__ = (
    "__version__",
    "AgentRuntimePort",
    "AgentRuntimeRunner",
    "BoardroomAgentRuntimePortAdapter",
)
```

- [ ] **Step 4: Run runtime port tests again**

Run:

```bash
python -m pytest tests/test_runtime_port.py -q
```

Expected:

```text
7 passed
```

---

### Task 4: Verify no fallback, governance event, or runtime regression was introduced

**Files:**

- Verify: `src/atomic_agent/runtime_port.py`
- Verify: `src/atomic_agent/__init__.py`
- Verify: existing runtime and tests

- [ ] **Step 1: Run focused runtime port tests**

Run:

```bash
python -m pytest tests/test_runtime_port.py -q
```

Expected:

```text
7 passed
```

- [ ] **Step 2: Run existing AgentLoop tests**

Run:

```bash
python -m pytest tests/test_agent_loop.py -q
```

Expected: pytest exits with code 0 and reports no failures.

- [ ] **Step 3: Run the permission negative gate**

Run:

```bash
python -m pytest -m permission_negative -q
```

Expected: pytest exits with code 0 and reports no failures for the selected permission-negative tests.

- [ ] **Step 4: Run the full suite**

Run:

```bash
python -m pytest -q
```

Expected: pytest exits with code 0 and reports no failures.

- [ ] **Step 5: Run a no-fallback and no-governance source scan**

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

runtime_port = Path('src/atomic_agent/runtime_port.py')
if runtime_port.exists():
    text = runtime_port.read_text(encoding='utf-8')
    assigned_attrs = [line.strip() for line in text.splitlines() if line.strip().startswith('self.') and '=' in line]
    unexpected_attrs = [line for line in assigned_attrs if not line.startswith('self.runner =')]
    for line in unexpected_attrs:
        print(f'{runtime_port}: unexpected instance state {line}')
PY
```

Expected:

```text

```

No output means runtime source does not contain obvious environment fallback, Boardroom governance completion, default allow patterns, or unexpected adapter instance state. If output appears in executable runtime code, inspect and fix before claiming completion.

- [ ] **Step 6: Check working tree scope before documentation completion**

Run:

```bash
git status --short
```

Expected implementation-stage scope:

```text
 M docs/INDEX.md
 M docs/04-implementation-plan/INDEX.md
 M docs/04-implementation-spec/INDEX.md
 M src/atomic_agent/__init__.py
?? docs/04-implementation-plan/P1-004-boardroom-agent-runtime-port-adapter-plan.md
?? docs/04-implementation-spec/P1-004-boardroom-agent-runtime-port-adapter-spec.md
?? src/atomic_agent/runtime_port.py
?? tests/test_runtime_port.py
```

`docs/04-implementation-backlog/backlog.md` should remain unchanged until implementation verification passes. If unrelated files appear, inspect them before continuing and do not include unrelated edits in P1-004.

---

### Task 5: Update P1-004 documentation status after implementation passes

**Files:**

- Modify: `docs/04-implementation-backlog/backlog.md`
- Modify: `docs/04-implementation-spec/P1-004-boardroom-agent-runtime-port-adapter-spec.md`
- Modify: `docs/04-implementation-plan/P1-004-boardroom-agent-runtime-port-adapter-plan.md`
- Modify: `docs/04-implementation-spec/INDEX.md`
- Modify: `docs/04-implementation-plan/INDEX.md`
- Modify: `docs/INDEX.md`

- [ ] **Step 1: Mark P1-004 completed only after tests pass**

Change `docs/04-implementation-backlog/backlog.md` P1-004 row from:

```markdown
| P1-004 | 实现 Boardroom AgentRuntimePort adapter（Boardroom 智能体运行时端口适配器） | pending | `agent-runtime-port.md`, `boardroom-os-integration-summary.md`, `0004-keep-boardroom-os-as-governance-source.md` |
```

To:

```markdown
| P1-004 | 实现 Boardroom AgentRuntimePort adapter（Boardroom 智能体运行时端口适配器） | completed | `agent-runtime-port.md`, `boardroom-os-integration-summary.md`, `0004-keep-boardroom-os-as-governance-source.md` |
```

- [ ] **Step 2: Mark spec implemented**

Change `docs/04-implementation-spec/P1-004-boardroom-agent-runtime-port-adapter-spec.md` from:

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

Change `docs/04-implementation-plan/P1-004-boardroom-agent-runtime-port-adapter-plan.md` from:

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
| `P1-004-boardroom-agent-runtime-port-adapter-spec.md` | draft | 定义 P1-004 Boardroom AgentRuntimePort adapter（Boardroom 智能体运行时端口适配器）的端口边界、透传语义、治理边界和无兜底要求 | 实现或评审 P1-004 前 |
```

Add this completed row:

```markdown
| `P1-004-boardroom-agent-runtime-port-adapter-spec.md` | 2026-06-06 | 已实现 P1-004 Boardroom AgentRuntimePort adapter（Boardroom 智能体运行时端口适配器），保留为端口适配器规格记录 |
```

- [ ] **Step 5: Move plan index entry to completed / archived**

Remove this active row from `docs/04-implementation-plan/INDEX.md`:

```markdown
| `P1-004-boardroom-agent-runtime-port-adapter-plan.md` | draft | 实施 P1-004 Boardroom AgentRuntimePort adapter（Boardroom 智能体运行时端口适配器）的 TDD 计划 | 执行或评审 P1-004 时 |
```

Add this completed row:

```markdown
| `P1-004-boardroom-agent-runtime-port-adapter-plan.md` | 2026-06-06 | 已实施 P1-004 Boardroom AgentRuntimePort adapter（Boardroom 智能体运行时端口适配器），保留为 TDD 实施记录 |
```

- [ ] **Step 6: Remove P1-004 draft pointers from global active documents after completion**

Remove these rows from `docs/INDEX.md` Current Active Documents（当前活跃文档指针） after P1-004 moves to completed sections in subdirectory indexes:

```markdown
| P0 | `docs/04-implementation-spec/P1-004-boardroom-agent-runtime-port-adapter-spec.md` | draft | 评审或实现 P1-004 Boardroom AgentRuntimePort adapter（Boardroom 智能体运行时端口适配器）前 |
| P0 | `docs/04-implementation-plan/P1-004-boardroom-agent-runtime-port-adapter-plan.md` | draft | 评审或执行 P1-004 Boardroom AgentRuntimePort adapter（Boardroom 智能体运行时端口适配器）计划时 |
```

---

### Task 6: Final verification and completion report

**Files:**

- Verify: all touched files

- [ ] **Step 1: Run final test suite**

Run:

```bash
python -m pytest -q
```

Expected: pytest exits with code 0 and reports no failures.

- [ ] **Step 2: Run final permission negative gate**

Run:

```bash
python -m pytest -m permission_negative -q
```

Expected: pytest exits with code 0 and reports no failures for the selected permission-negative tests.

- [ ] **Step 3: Run no-fallback and no-governance source scan one final time**

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

runtime_port = Path('src/atomic_agent/runtime_port.py')
if runtime_port.exists():
    text = runtime_port.read_text(encoding='utf-8')
    assigned_attrs = [line.strip() for line in text.splitlines() if line.strip().startswith('self.') and '=' in line]
    unexpected_attrs = [line for line in assigned_attrs if not line.startswith('self.runner =')]
    for line in unexpected_attrs:
        print(f'{runtime_port}: unexpected instance state {line}')
PY
```

Expected:

```text

```

No output means runtime source does not contain obvious environment fallback, Boardroom governance completion, default allow patterns, or unexpected adapter instance state.

- [ ] **Step 4: Check final working tree scope**

Run:

```bash
git status --short
```

Expected final scope:

```text
 M docs/04-implementation-backlog/backlog.md
 M docs/04-implementation-plan/INDEX.md
 M docs/04-implementation-spec/INDEX.md
 M src/atomic_agent/__init__.py
?? docs/04-implementation-plan/P1-004-boardroom-agent-runtime-port-adapter-plan.md
?? docs/04-implementation-spec/P1-004-boardroom-agent-runtime-port-adapter-spec.md
?? src/atomic_agent/runtime_port.py
?? tests/test_runtime_port.py
```

`docs/INDEX.md` may be absent from the final diff if P1-004 draft active pointers are added during planning and removed after completion, leaving the global index identical to baseline. If additional files appear, inspect them and explain before claiming completion.

- [ ] **Step 5: Report completion without claiming Boardroom closeout**

The completion report must say that P1-004 exposes a runtime port adapter and tests pass. It must not say the Boardroom ticket is completed, closeout is committed, evidence is verified, or source inventory is accepted.

---

## Self-Review Checklist

Before implementation is considered ready for user review:

- [ ] Spec coverage: Every requirement in `docs/04-implementation-spec/P1-004-boardroom-agent-runtime-port-adapter-spec.md` is covered by a task, test, verification command, docs update, or explicit out-of-scope statement.
- [ ] Placeholder scan: This plan contains no unfinished markers, vague “add tests” step, mock success path, or silent fallback.
- [ ] Type consistency: `AgentRuntimePort`, `AgentRuntimeRunner`, `BoardroomAgentRuntimePortAdapter`, `AgentInvocation`, `AgentRunResult`, and `AgentRunStatus` names match existing contracts and planned implementation.
- [ ] Scope check: No Boardroom OS model, `ExecutionPackage` mapping, real provider integration, new tool, new permission policy, new event type, `.env` fallback, or governance completion decision is included.
- [ ] Fail-closed check: Invalid invocation type, invalid runner result type, and runner exception do not produce misleading success.
- [ ] Evidence boundary check: Adapter preserves existing `AgentRunResult` evidence fields and does not create a second event stream, artifact store, or Boardroom governance state.
- [ ] Verification check: Runtime port tests, AgentLoop tests, permission negative gate, full suite, and source scan pass before any completion claim.

## Self-Review Result

- Spec coverage（规格覆盖）：计划覆盖 P1-004 spec（规格）中的 port contract（端口契约）、adapter behavior（适配器行为）、invocation requirements（调用请求要求）、result and governance boundary（结果与治理边界）、security no-fallback rules（安全无兜底规则）、documentation requirements（文档要求）和 acceptance criteria（验收标准）。
- Placeholder scan（占位符扫描）：未使用占位式标记、空泛“补测试”或未定义步骤；新增测试和实现文件均提供完整代码。
- Type consistency（类型一致性）：计划中的类名、函数名、事件边界、文件名、命令和状态值与现有代码及新规格保持一致。
- Scope check（范围检查）：未纳入 Boardroom OS 数据模型、ExecutionPackage 映射、真实 provider、网络扩展、权限引擎、长期配置系统、新事件类型或任意 shell。
- No-fallback check（无兜底检查）：计划明确要求完整 AgentInvocation、runner 组合、结果原样透传、类型错误清晰失败、runner 异常传播、无环境配置补齐、无治理完成事件、无第二事实源。
