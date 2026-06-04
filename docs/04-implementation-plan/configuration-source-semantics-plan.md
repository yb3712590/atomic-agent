# Configuration Source Semantics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish configuration source semantics（配置来源语义） for `atomic-agent`（原子智能体） and implement P0-001 core models without `.env` fallback（环境变量兜底） inside runtime（运行时）.

**Architecture:** `AgentRuntime`（智能体运行时） accepts one complete `AgentInvocation`（智能体调用请求） as its only runtime input. Boardroom-managed invocation（Boardroom 管理调用） must not read `.env`; standalone invocation（独立调用） may read `.env` only in an outer entrypoint that constructs a complete `AgentInvocation` before calling runtime.

**Tech Stack:** Python 3.11+, Pydantic v2（数据模型与校验）, pytest（测试）, Markdown（权威文档）.

---

## Scope

This plan implements the configuration source boundary needed before P0-001 and then implements P0-001 core contract models（核心契约模型）.

In scope:

- Document Boardroom-managed invocation as explicit-only input.
- Document standalone `.env` as an outer construction source, not runtime fallback.
- Create core models for `AgentInvocation`, `AgentRunResult`, `AgentAction`, and `AgentEvent`.
- Add contract tests proving missing required invocation fields fail validation even if environment variables exist.

Out of scope:

- No standalone CLI（独立命令行入口）.
- No `.env.example` until a standalone entrypoint exists.
- No `.env` loader（环境变量加载器） inside runtime.
- No filesystem tools, command tools, web tools, event recorder, or agent loop.

## File Structure

- Modify: `docs/04-implementation-spec/mvp-runtime-spec.md`
  - Adds configuration source semantics as MVP specification.
- Modify: `docs/04-implementation-plan/INDEX.md`
  - Registers this plan as an active implementation plan.
- Create: `pyproject.toml`
  - Defines the minimal Python package and test dependencies.
- Create: `src/atomic_agent/__init__.py`
  - Exposes package version and keeps import path stable.
- Create: `src/atomic_agent/models.py`
  - Defines P0-001 core contract models and strict validation.
- Create: `tests/test_models.py`
  - Tests model validation, extra-field rejection, failure result details, and no `.env` fallback.
- Modify: `docs/04-implementation-backlog/backlog.md`
  - Marks P0-001 completed only after tests pass.

---

### Task 1: Lock Configuration Source Semantics in Spec

**Files:**
- Modify: `docs/04-implementation-spec/mvp-runtime-spec.md`

- [ ] **Step 1: Confirm the spec contains the configuration source section**

Expected section content:

```markdown
## Configuration Source Semantics

MVP runtime（最小可行运行时）必须区分两种 invocation mode（调用模式）：

1. Boardroom-managed invocation（Boardroom 管理调用）。
2. Standalone invocation（独立调用）。

Boardroom-managed invocation 中，`AgentInvocation`（智能体调用请求）是 runtime 的完整输入。runtime 不得读取 `.env`、environment variables（环境变量）、local config files（本地配置文件）或 process defaults（进程默认值）来补全缺失的 `AgentInvocation` 字段。缺失必需字段时必须 fail closed（失败关闭），并返回结构化失败结果；该请求缺陷应在 Boardroom OS（Boardroom 操作系统）项目内修复。

Standalone invocation 中，standalone entrypoint（独立入口）可以读取 `.env` 来构造完整 `AgentInvocation`。构造完成后，runtime 只能接收显式 `AgentInvocation`，不能在执行过程中再次读取 `.env` 作为 fallback（兜底）。

所有可暴露 configurable options（可配置选项）不得在 runtime code（运行时代码）中硬编码。provider（模型供应商）、model（模型）、workspace root（工作区根目录）、allowed write set（允许写入集合）、tools（工具集合）、permission policy（权限策略）、command policy（命令策略）、network policy（网络策略）、budgets（预算）、timeouts（超时）、ports（端口）和 output requirements（输出要求）必须来自显式 invocation input（调用输入）或 standalone `.env` 构造过程。
```

- [ ] **Step 2: Review the spec diff**

Run:

```bash
git diff -- docs/04-implementation-spec/mvp-runtime-spec.md
```

Expected: The diff adds configuration source semantics and does not introduce `.env` fallback for Boardroom-managed invocation.

---

### Task 2: Add Minimal Python Project Skeleton

**Files:**
- Create: `pyproject.toml`
- Create: `src/atomic_agent/__init__.py`

- [ ] **Step 1: Create package metadata and test configuration**

Write `pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=69.0"]
build-backend = "setuptools.build_meta"

[project]
name = "atomic-agent"
version = "0.0.0"
description = "Small auditable permission-controlled agent runtime"
requires-python = ">=3.11"
dependencies = [
  "pydantic>=2.7,<3.0",
]

[project.optional-dependencies]
test = [
  "pytest>=8.0,<9.0",
]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

- [ ] **Step 2: Create package entrypoint**

Write `src/atomic_agent/__init__.py`:

```python
__version__ = "0.0.0"
```

- [ ] **Step 3: Install the package for local testing**

Run:

```bash
python -m pip install -e ".[test]"
```

Expected: pip installs `atomic-agent`, `pydantic`, and `pytest` without errors.

---

### Task 3: Write Contract Tests First

**Files:**
- Create: `tests/test_models.py`

- [ ] **Step 1: Write failing tests for P0-001 models**

Write `tests/test_models.py`:

```python
import pytest
from pydantic import ValidationError

from atomic_agent.models import (
    AgentAction,
    AgentActionType,
    AgentEvent,
    AgentEventType,
    AgentInvocation,
    AgentRunResult,
    AgentRunStatus,
)


def valid_invocation_payload():
    return {
        "invocation_id": "inv_001",
        "task": "Read README and summarize current phase.",
        "workspace_root": "/workspace/project",
        "allowed_write_set": ["docs/04-implementation-plan/configuration-source-semantics-plan.md"],
        "tools": ["list_files", "read_file"],
        "permission_policy": {"file_reads": "workspace", "file_writes": "allowed_write_set"},
        "provider_profile": {"provider": "anthropic", "model": "claude-opus-4-7"},
        "budgets": {"max_steps": 8, "max_wall_seconds": 120},
        "output_requirements": {"summary": True, "event_stream": True},
    }


def test_agent_action_accepts_known_action():
    action = AgentAction(
        action_id="step-0001",
        action=AgentActionType.READ_FILE,
        reason_summary="Read the target file before patching.",
        input={"path": "README.md", "offset": 0, "limit": 12000},
    )

    assert action.action == AgentActionType.READ_FILE
    assert action.input["path"] == "README.md"


def test_agent_action_rejects_extra_fields():
    with pytest.raises(ValidationError):
        AgentAction(
            action_id="step-0001",
            action="read_file",
            reason_summary="Read the target file before patching.",
            input={"path": "README.md"},
            unexpected="not allowed",
        )


def test_agent_action_rejects_unknown_action():
    with pytest.raises(ValidationError):
        AgentAction(
            action_id="step-0001",
            action="free_shell",
            reason_summary="Run a shell command.",
            input={"command": "rm -rf ."},
        )


def test_agent_invocation_requires_explicit_provider_profile():
    payload = valid_invocation_payload()
    del payload["provider_profile"]

    with pytest.raises(ValidationError):
        AgentInvocation(**payload)


def test_agent_invocation_does_not_read_env_defaults(monkeypatch):
    monkeypatch.setenv("ATOMIC_AGENT_PROVIDER", "anthropic")
    monkeypatch.setenv("ATOMIC_AGENT_MODEL", "claude-opus-4-7")
    payload = valid_invocation_payload()
    del payload["provider_profile"]

    with pytest.raises(ValidationError):
        AgentInvocation(**payload)


def test_agent_invocation_accepts_complete_payload():
    invocation = AgentInvocation(**valid_invocation_payload())

    assert invocation.invocation_id == "inv_001"
    assert invocation.provider_profile["model"] == "claude-opus-4-7"
    assert invocation.budgets["max_steps"] == 8


def test_failed_agent_run_result_requires_failure_details():
    with pytest.raises(ValidationError):
        AgentRunResult(
            run_id="run_001",
            status=AgentRunStatus.FAILED,
            event_stream_ref="artifact://run_001/events.jsonl",
            events_hash="sha256:events",
            tool_attempts=[],
            workspace_mutations=[],
            artifacts=[],
            summary="The run failed.",
        )


def test_failed_agent_run_result_accepts_failure_details():
    result = AgentRunResult(
        run_id="run_001",
        status=AgentRunStatus.FAILED,
        event_stream_ref="artifact://run_001/events.jsonl",
        events_hash="sha256:events",
        tool_attempts=[],
        workspace_mutations=[],
        artifacts=[],
        summary="The run failed closed.",
        failure_kind="policy_denied",
        failure_message="The action attempted to write outside the allowed write set.",
        failed_action_ref="step-0004",
    )

    assert result.failure_kind == "policy_denied"
    assert result.failed_action_ref == "step-0004"


def test_agent_event_accepts_first_event_without_previous_hash():
    event = AgentEvent(
        event_id="evt_000001",
        run_id="run_001",
        sequence=1,
        type=AgentEventType.RUN_STARTED,
        timestamp="2026-06-04T00:00:00Z",
        payload={"event_protocol_version": 1},
        previous_event_hash=None,
        event_hash="sha256:first",
    )

    assert event.previous_event_hash is None
    assert event.type == AgentEventType.RUN_STARTED


def test_agent_event_rejects_zero_sequence():
    with pytest.raises(ValidationError):
        AgentEvent(
            event_id="evt_000000",
            run_id="run_001",
            sequence=0,
            type=AgentEventType.RUN_STARTED,
            timestamp="2026-06-04T00:00:00Z",
            payload={},
            previous_event_hash=None,
            event_hash="sha256:first",
        )
```

- [ ] **Step 2: Run tests and confirm they fail before implementation**

Run:

```bash
python -m pytest tests/test_models.py -q
```

Expected: FAIL with an import error because `atomic_agent.models` does not exist yet.

---

### Task 4: Implement Core Contract Models

**Files:**
- Create: `src/atomic_agent/models.py`

- [ ] **Step 1: Implement strict P0-001 models**

Write `src/atomic_agent/models.py`:

```python
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AgentRunStatus(str, Enum):
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"
    REQUIRES_APPROVAL = "requires_approval"


class AgentActionType(str, Enum):
    LIST_FILES = "list_files"
    READ_FILE = "read_file"
    SEARCH_FILES = "search_files"
    WRITE_FILE = "write_file"
    APPLY_PATCH = "apply_patch"
    RUN_COMMAND = "run_command"
    WEB_FETCH = "web_fetch"
    SUBMIT_RESULT = "submit_result"


class AgentEventType(str, Enum):
    RUN_STARTED = "run.started"
    RUN_COMPLETED = "run.completed"
    RUN_FAILED = "run.failed"
    PROVIDER_TURN_STARTED = "provider.turn.started"
    PROVIDER_TURN_COMPLETED = "provider.turn.completed"
    PROVIDER_TURN_FAILED = "provider.turn.failed"
    ACTION_PARSED = "action.parsed"
    ACTION_REJECTED = "action.rejected"
    PERMISSION_DECIDED = "permission.decided"
    TOOL_ATTEMPT_STARTED = "tool.attempt.started"
    TOOL_ATTEMPT_COMPLETED = "tool.attempt.completed"
    TOOL_ATTEMPT_FAILED = "tool.attempt.failed"
    WORKSPACE_MUTATION_RECORDED = "workspace.mutation.recorded"
    COMMAND_COMPLETED = "command.completed"
    NETWORK_FETCH_COMPLETED = "network.fetch.completed"
    RESULT_SUBMITTED = "result.submitted"


class AgentInvocation(StrictModel):
    invocation_id: str
    task: str
    workspace_root: str
    allowed_write_set: list[str]
    tools: list[str]
    permission_policy: dict[str, Any]
    provider_profile: dict[str, Any]
    budgets: dict[str, Any]
    output_requirements: dict[str, Any]
    role_context: str | None = None
    skill_context: dict[str, Any] | None = None
    initial_files: list[str] | None = None
    metadata: dict[str, Any] | None = None


class AgentAction(StrictModel):
    action_id: str
    action: AgentActionType
    reason_summary: str
    input: dict[str, Any]


class AgentEvent(StrictModel):
    event_id: str
    run_id: str
    sequence: int = Field(ge=1)
    type: AgentEventType
    timestamp: str
    payload: dict[str, Any]
    previous_event_hash: str | None
    event_hash: str


class AgentRunResult(StrictModel):
    run_id: str
    status: AgentRunStatus
    event_stream_ref: str
    events_hash: str
    tool_attempts: list[dict[str, Any]]
    workspace_mutations: list[dict[str, Any]]
    artifacts: list[dict[str, Any]]
    summary: str
    failure_kind: str | None = None
    failure_message: str | None = None
    failed_action_ref: str | None = None

    @model_validator(mode="after")
    def failed_results_include_failure_details(self):
        if self.status == AgentRunStatus.FAILED and not self.failure_kind:
            raise ValueError("failed AgentRunResult requires failure_kind")
        if self.status == AgentRunStatus.FAILED and not self.failure_message:
            raise ValueError("failed AgentRunResult requires failure_message")
        return self
```

- [ ] **Step 2: Run model tests**

Run:

```bash
python -m pytest tests/test_models.py -q
```

Expected: PASS for all tests in `tests/test_models.py`.

---

### Task 5: Verify No Runtime `.env` Fallback Exists

**Files:**
- Inspect: `src/atomic_agent/models.py`
- Inspect: `tests/test_models.py`

- [ ] **Step 1: Search for environment reads in runtime source**

Run:

```bash
grep -R "os\.environ\|getenv\|dotenv\|\.env" src tests
```

Expected: No matches in `src/`. The only allowed match is the test name or environment variable setup in `tests/test_models.py` proving missing invocation fields still fail validation.

- [ ] **Step 2: Run full test suite**

Run:

```bash
python -m pytest -q
```

Expected: PASS for all tests.

---

### Task 6: Update Backlog After Verification

**Files:**
- Modify: `docs/04-implementation-backlog/backlog.md`

- [ ] **Step 1: Mark P0-001 completed only after tests pass**

Change this row:

```markdown
| P0-001 | 定义核心数据模型：AgentInvocation、AgentRunResult、AgentAction、AgentEvent | pending | `docs/03-contracts/` |
```

To:

```markdown
| P0-001 | 定义核心数据模型：AgentInvocation、AgentRunResult、AgentAction、AgentEvent | completed | `docs/03-contracts/` |
```

- [ ] **Step 2: Review backlog diff**

Run:

```bash
git diff -- docs/04-implementation-backlog/backlog.md
```

Expected: Only P0-001 status changes from `pending` to `completed`.

---

### Task 7: Final Verification and Optional Commit

**Files:**
- Inspect: all changed files

- [ ] **Step 1: Check working tree**

Run:

```bash
git status --short
```

Expected: Changed files are limited to this plan, MVP spec, implementation plan index, `pyproject.toml`, `src/atomic_agent/`, `tests/test_models.py`, and backlog status.

- [ ] **Step 2: Review total diff**

Run:

```bash
git diff
```

Expected: Diff contains no `.env` fallback in runtime source and no hardcoded provider/model/budget defaults outside test payloads.

- [ ] **Step 3: Commit only if the user explicitly requests a commit**

Run only after explicit user approval:

```bash
git add docs/04-implementation-spec/mvp-runtime-spec.md docs/04-implementation-plan/INDEX.md docs/04-implementation-plan/configuration-source-semantics-plan.md docs/04-implementation-backlog/backlog.md pyproject.toml src/atomic_agent/__init__.py src/atomic_agent/models.py tests/test_models.py
git commit -m "feat: 定义核心模型配置边界"
```

Expected: A new commit is created with the project commit format.

---

## Self-Review Checklist

- Spec coverage: The plan covers Boardroom-managed invocation, standalone invocation, no `.env` fallback, no hardcoded configurable options, core model validation, and backlog completion.
- Placeholder scan: The plan contains no placeholder tasks, incomplete requirements, or deferred implementation inside scoped tasks.
- Type consistency: `AgentInvocation`, `AgentRunResult`, `AgentAction`, `AgentEvent`, enum names, and field names match the contract documents.
- Scope check: The plan does not implement standalone CLI, `.env.example`, tool execution, event recorder, or agent loop.
- Safety check: Boardroom request defects fail validation in atomic-agent and must be fixed in Boardroom OS, not hidden by local fallback.
