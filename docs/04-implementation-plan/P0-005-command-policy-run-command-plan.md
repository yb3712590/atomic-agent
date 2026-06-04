# Command Policy and Run Command Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement P0-005 `command policy`（命令策略） and `run_command`（运行声明命令） so the runtime can execute only explicitly declared commands and return auditable command results.

**Architecture:** Add a focused `command_tools`（命令工具） module that owns `CommandPolicy`（命令策略）, `CommandSpec`（命令声明）, real subprocess execution, timeout（超时）, stdout/stderr hashing（输出哈希）, and output truncation（输出截断）. The module depends on `WorkspacePathGuard`（工作区路径守卫） for cwd（工作目录） authorization and returns structured `CommandToolResult`（命令工具结果） values; it does not emit events, implement AgentLoop（智能体循环）, access network policy（网络策略）, or claim OS-level sandboxing（操作系统级沙箱）.

**Tech Stack:** Python 3.11+, `dataclasses`（轻量数据结构）, `pathlib`（路径处理）, `subprocess`（进程执行）, `hashlib`（哈希）, `re`（命令标识校验）, pytest（测试）.

**Status:** implemented

---

## Scope

This plan implements P0-005 only.

In scope:

- Create `src/atomic_agent/command_tools.py`（命令工具模块）.
- Create `tests/test_command_tools.py`（命令工具测试）.
- Implement `CommandPolicy`（命令策略） and `CommandSpec`（命令声明）.
- Implement `CommandTools.run_command`（运行声明命令）.
- Implement `execute_command_action`（执行命令动作） dispatcher for `RUN_COMMAND` only.
- Reuse `WorkspacePathGuard`（工作区路径守卫） for every configured cwd（工作目录）.
- Use `shell=False` and argv list（参数数组） only.
- Use explicit env mapping（显式环境变量映射） only; do not inherit `os.environ`.
- Return structured command results with real exit code（退出码）, stdout/stderr（标准输出/标准错误）, hashes（哈希）, byte sizes（字节数）, truncation flags（截断标记）, and decode flags（解码标记）.

Out of scope:

- No event recorder（事件记录器） or JSONL event stream（JSONL 事件流）.
- No AgentLoop（智能体循环）.
- No global budget counters（全局预算计数器） such as max command runs（最大命令次数）.
- No `web_fetch`（网络获取） or NetworkPolicy（网络策略）.
- No OS-level network sandbox（操作系统级网络沙箱）.
- No service runner（服务运行器） or long-running process manager（长运行进程管理器）.
- No commit unless the user explicitly requests it.

## File Structure

- Create: `src/atomic_agent/command_tools.py`
  - Defines `CommandSpec`（命令声明）, `CommandToolConfig`（命令工具配置）, `CommandToolResult`（命令工具结果）, `CommandToolConfigError`（命令工具配置错误）, `CommandPolicy`（命令策略）, `CommandTools`（命令工具集合）, and `execute_command_action`（执行命令动作）.
- Create: `tests/test_command_tools.py`
  - Covers policy/config validation, real command execution, unknown command rejection, cwd guard（工作目录守卫）, timeout（超时）, output truncation（输出截断）, explicit env（显式环境变量）, non-zero exit code（非零退出码）, and dispatcher behavior.
- Modify after implementation passes: `docs/04-implementation-backlog/backlog.md`
  - Marks P0-005 completed only after tests pass and user review accepts implementation.
- Modify after implementation passes: `docs/04-implementation-spec/INDEX.md`
  - Moves `P0-005-command-policy-run-command-spec.md`（命令策略与运行命令规格） from draft/current to completed / archived.
- Modify after implementation passes: `docs/04-implementation-plan/INDEX.md`
  - Moves this plan from current draft to completed / archived.

---

### Task 1: Add command result, config, and policy boundary tests

**Files:**

- Create: `tests/test_command_tools.py`
- Create: `src/atomic_agent/command_tools.py`

- [ ] **Step 1: Write failing tests for result shape, config validation, and policy validation**

Write `tests/test_command_tools.py`:

```python
import hashlib
from pathlib import Path
import sys

import pytest
from pydantic import ValidationError

from atomic_agent.command_tools import (
    CommandPolicy,
    CommandSpec,
    CommandToolConfig,
    CommandToolConfigError,
    CommandToolResult,
    CommandTools,
)
from atomic_agent.models import AgentAction, AgentActionType
from atomic_agent.path_guard import WorkspacePathGuard


PYTHON = Path(sys.executable).resolve()


def command_config(max_output_bytes=64):
    return CommandToolConfig(
        default_timeout_seconds=1.0,
        max_timeout_seconds=3.0,
        max_output_bytes=max_output_bytes,
    )


def make_policy(command_id="python-ok", spec=None):
    if spec is None:
        spec = CommandSpec(argv=(str(PYTHON), "-c", "import sys; sys.stdout.write('ok')"))
    return CommandPolicy({command_id: spec})


def make_tools(tmp_path, policy=None, config=None):
    guard = WorkspacePathGuard(tmp_path, allowed_write_set=[])
    return CommandTools(guard, policy or make_policy(), config or command_config())


def test_command_tool_result_success_has_no_error_fields():
    result = CommandToolResult(
        ok=True,
        tool="run_command",
        command_id="test",
        data={"exit_code": 0},
    )

    assert result.ok is True
    assert result.error_kind is None
    assert result.error_message is None


def test_command_tool_result_success_rejects_error_fields():
    with pytest.raises(ValueError):
        CommandToolResult(
            ok=True,
            tool="run_command",
            command_id="test",
            data={"exit_code": 0},
            error_kind="permission_denied",
            error_message="Command denied.",
        )


def test_command_tool_result_failure_requires_error_kind():
    with pytest.raises(ValueError):
        CommandToolResult(
            ok=False,
            tool="run_command",
            command_id="missing",
            data={},
            error_message="Command denied.",
        )


def test_command_tool_result_failure_requires_error_message():
    with pytest.raises(ValueError):
        CommandToolResult(
            ok=False,
            tool="run_command",
            command_id="missing",
            data={},
            error_kind="permission_denied",
        )


def test_command_tool_result_failure_accepts_error_fields():
    result = CommandToolResult(
        ok=False,
        tool="run_command",
        command_id="missing",
        data={},
        error_kind="permission_denied",
        error_message="command_id is not declared in command policy",
    )

    assert result.ok is False
    assert result.error_kind == "permission_denied"
    assert result.error_message == "command_id is not declared in command policy"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"default_timeout_seconds": 0.0},
        {"max_timeout_seconds": 0.0},
        {"default_timeout_seconds": 4.0},
        {"max_output_bytes": 0},
    ],
)
def test_command_tools_rejects_invalid_config(tmp_path, kwargs):
    values = {
        "default_timeout_seconds": 1.0,
        "max_timeout_seconds": 3.0,
        "max_output_bytes": 64,
    }
    values.update(kwargs)
    guard = WorkspacePathGuard(tmp_path, allowed_write_set=[])

    with pytest.raises(CommandToolConfigError):
        CommandTools(guard, make_policy(), CommandToolConfig(**values))


def test_command_policy_rejects_empty_policy():
    with pytest.raises(CommandToolConfigError):
        CommandPolicy({})


@pytest.mark.parametrize("command_id", ["", " ", "bad id", "bad/id", "bad$id"])
def test_command_policy_rejects_invalid_command_id(command_id):
    spec = CommandSpec(argv=(str(PYTHON), "--version"))

    with pytest.raises(CommandToolConfigError):
        CommandPolicy({command_id: spec})


@pytest.mark.parametrize(
    "spec",
    [
        CommandSpec(argv=()),
        CommandSpec(argv=("",)),
        CommandSpec(argv=("python", "--version")),
        CommandSpec(argv=(str(PYTHON), "--version"), timeout_seconds=0.0),
        CommandSpec(argv=(str(PYTHON), "--version"), env={"": "value"}),
        CommandSpec(argv=(str(PYTHON), "--version"), env={"NAME": 123}),
        CommandSpec(argv=(str(PYTHON), "--version"), allow_network=True),
    ],
)
def test_command_policy_rejects_invalid_command_spec(spec):
    with pytest.raises(CommandToolConfigError):
        CommandPolicy({"test": spec})
```

- [ ] **Step 2: Run the new tests and confirm they fail because the module does not exist**

Run:

```bash
pytest tests/test_command_tools.py::test_command_tool_result_success_has_no_error_fields tests/test_command_tools.py::test_command_tools_rejects_invalid_config tests/test_command_tools.py::test_command_policy_rejects_empty_policy -v
```

Expected:

```text
ModuleNotFoundError: No module named 'atomic_agent.command_tools'
```

- [ ] **Step 3: Add the initial module with result, config, and policy validation**

Write `src/atomic_agent/command_tools.py`:

```python
from dataclasses import dataclass
import re
from pathlib import Path
from typing import Any

from atomic_agent.path_guard import WorkspacePathGuard


_COMMAND_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.:-]+$")


@dataclass(frozen=True)
class CommandSpec:
    argv: tuple[str, ...]
    cwd: str | None = None
    timeout_seconds: float | None = None
    env: dict[str, str] | None = None
    allow_network: bool = False


@dataclass(frozen=True)
class CommandToolConfig:
    default_timeout_seconds: float
    max_timeout_seconds: float
    max_output_bytes: int


@dataclass(frozen=True)
class CommandToolResult:
    ok: bool
    tool: str
    command_id: str | None
    data: dict[str, Any]
    error_kind: str | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        if self.ok and (self.error_kind is not None or self.error_message is not None):
            raise ValueError("successful CommandToolResult must not include error fields")
        if not self.ok and (not self.error_kind or not self.error_message):
            raise ValueError("failed CommandToolResult requires error_kind and error_message")


class CommandToolConfigError(ValueError):
    pass


class CommandPolicy:
    def __init__(self, commands: dict[str, CommandSpec]):
        if not isinstance(commands, dict) or not commands:
            raise CommandToolConfigError("command policy must declare at least one command")
        self.commands: dict[str, CommandSpec] = {}
        for command_id, spec in commands.items():
            self._validate_command_id_for_config(command_id)
            self._validate_spec(spec)
            self.commands[command_id] = spec

    def resolve(self, command_id: str) -> CommandSpec | None:
        return self.commands.get(command_id)

    @staticmethod
    def is_valid_command_id(command_id: object) -> bool:
        return isinstance(command_id, str) and bool(_COMMAND_ID_PATTERN.fullmatch(command_id))

    def _validate_command_id_for_config(self, command_id: object) -> None:
        if not self.is_valid_command_id(command_id):
            raise CommandToolConfigError("command_id must be a non-empty stable identifier")

    def _validate_spec(self, spec: object) -> None:
        if not isinstance(spec, CommandSpec):
            raise CommandToolConfigError("command spec must be a CommandSpec")
        if not isinstance(spec.argv, tuple) or not spec.argv:
            raise CommandToolConfigError("command argv must be a non-empty tuple")
        for item in spec.argv:
            if not isinstance(item, str) or item == "":
                raise CommandToolConfigError("command argv entries must be non-empty strings")
        if not Path(spec.argv[0]).is_absolute():
            raise CommandToolConfigError("command executable must be an absolute path")
        if spec.cwd is not None and not isinstance(spec.cwd, str):
            raise CommandToolConfigError("command cwd must be a string or None")
        if spec.timeout_seconds is not None and not self._is_positive_number(spec.timeout_seconds):
            raise CommandToolConfigError("command timeout_seconds must be positive")
        if spec.env is not None:
            if not isinstance(spec.env, dict):
                raise CommandToolConfigError("command env must be a mapping")
            for key, value in spec.env.items():
                if not isinstance(key, str) or key == "":
                    raise CommandToolConfigError("command env keys must be non-empty strings")
                if not isinstance(value, str):
                    raise CommandToolConfigError("command env values must be strings")
        if spec.allow_network:
            raise CommandToolConfigError("P0-005 does not support network-enabled commands")

    def _is_positive_number(self, value: object) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0


class CommandTools:
    def __init__(self, guard: WorkspacePathGuard, policy: CommandPolicy, config: CommandToolConfig):
        self.guard = guard
        self.policy = policy
        self.config = config
        self._validate_config()

    def _validate_config(self) -> None:
        if not self._is_positive_number(self.config.default_timeout_seconds):
            raise CommandToolConfigError("default_timeout_seconds must be positive")
        if not self._is_positive_number(self.config.max_timeout_seconds):
            raise CommandToolConfigError("max_timeout_seconds must be positive")
        if self.config.default_timeout_seconds > self.config.max_timeout_seconds:
            raise CommandToolConfigError("default_timeout_seconds must not exceed max_timeout_seconds")
        if not isinstance(self.config.max_output_bytes, int) or self.config.max_output_bytes <= 0:
            raise CommandToolConfigError("max_output_bytes must be a positive integer")

    def _is_positive_number(self, value: object) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0
```

- [ ] **Step 4: Run boundary tests and confirm they pass**

Run:

```bash
pytest tests/test_command_tools.py::test_command_tool_result_success_has_no_error_fields tests/test_command_tools.py::test_command_tool_result_success_rejects_error_fields tests/test_command_tools.py::test_command_tool_result_failure_requires_error_kind tests/test_command_tools.py::test_command_tool_result_failure_requires_error_message tests/test_command_tools.py::test_command_tool_result_failure_accepts_error_fields tests/test_command_tools.py::test_command_tools_rejects_invalid_config tests/test_command_tools.py::test_command_policy_rejects_empty_policy tests/test_command_tools.py::test_command_policy_rejects_invalid_command_id tests/test_command_tools.py::test_command_policy_rejects_invalid_command_spec -v
```

Expected:

```text
PASSED
```

---

### Task 2: Add cwd policy validation through path guard

**Files:**

- Modify: `tests/test_command_tools.py`
- Modify: `src/atomic_agent/command_tools.py`

- [ ] **Step 1: Add failing cwd validation tests**

Append to `tests/test_command_tools.py`:

```python

def test_command_tools_accepts_workspace_cwd(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    policy = make_policy(spec=CommandSpec(argv=(str(PYTHON), "--version"), cwd="work"))

    tools = make_tools(tmp_path, policy=policy)

    assert tools is not None


@pytest.mark.parametrize("cwd", ["../outside", "missing", "file.txt"])
def test_command_tools_rejects_invalid_cwd(tmp_path, cwd):
    (tmp_path / "file.txt").write_text("not a directory", encoding="utf-8")
    policy = make_policy(spec=CommandSpec(argv=(str(PYTHON), "--version"), cwd=cwd))
    guard = WorkspacePathGuard(tmp_path, allowed_write_set=[])

    with pytest.raises(CommandToolConfigError):
        CommandTools(guard, policy, command_config())


def test_command_tools_rejects_cwd_symlink_escape(tmp_path):
    outside = tmp_path.parent / f"{tmp_path.name}-outside-command-cwd"
    outside.mkdir()
    link = tmp_path / "link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"symlink creation is unavailable: {error}")
    policy = make_policy(spec=CommandSpec(argv=(str(PYTHON), "--version"), cwd="link"))
    guard = WorkspacePathGuard(tmp_path, allowed_write_set=[])

    with pytest.raises(CommandToolConfigError):
        CommandTools(guard, policy, command_config())
```

- [ ] **Step 2: Run cwd tests and confirm validation is missing**

Run:

```bash
pytest tests/test_command_tools.py::test_command_tools_accepts_workspace_cwd tests/test_command_tools.py::test_command_tools_rejects_invalid_cwd tests/test_command_tools.py::test_command_tools_rejects_cwd_symlink_escape -v
```

Expected before the fix:

```text
FAILED tests/test_command_tools.py::test_command_tools_rejects_invalid_cwd
FAILED tests/test_command_tools.py::test_command_tools_rejects_cwd_symlink_escape
```

- [ ] **Step 3: Add cwd validation helpers**

In `src/atomic_agent/command_tools.py`, add this import:

```python
from atomic_agent.path_guard import PathDecisionType, WorkspacePathGuard
```

Replace the existing `CommandTools` class with:

```python
class CommandTools:
    def __init__(self, guard: WorkspacePathGuard, policy: CommandPolicy, config: CommandToolConfig):
        self.guard = guard
        self.policy = policy
        self.config = config
        self._cwd_by_command_id: dict[str, Path] = {}
        self._validate_config()
        self._validate_policy_against_workspace()

    def _validate_config(self) -> None:
        if not self._is_positive_number(self.config.default_timeout_seconds):
            raise CommandToolConfigError("default_timeout_seconds must be positive")
        if not self._is_positive_number(self.config.max_timeout_seconds):
            raise CommandToolConfigError("max_timeout_seconds must be positive")
        if self.config.default_timeout_seconds > self.config.max_timeout_seconds:
            raise CommandToolConfigError("default_timeout_seconds must not exceed max_timeout_seconds")
        if not isinstance(self.config.max_output_bytes, int) or self.config.max_output_bytes <= 0:
            raise CommandToolConfigError("max_output_bytes must be a positive integer")

    def _validate_policy_against_workspace(self) -> None:
        for command_id, spec in self.policy.commands.items():
            timeout = spec.timeout_seconds if spec.timeout_seconds is not None else self.config.default_timeout_seconds
            if timeout > self.config.max_timeout_seconds:
                raise CommandToolConfigError("command timeout_seconds exceeds configured maximum")
            self._cwd_by_command_id[command_id] = self._resolve_cwd_for_config(spec.cwd)

    def _resolve_cwd_for_config(self, cwd: str | None) -> Path:
        if cwd is None:
            return self.guard.workspace_root
        decision = self.guard.resolve_read_path(cwd)
        if decision.decision == PathDecisionType.DENY:
            raise CommandToolConfigError(f"command cwd denied: {decision.reason}")
        target = Path(decision.normalized_path)
        if not target.exists():
            raise CommandToolConfigError("command cwd must exist")
        if not target.is_dir():
            raise CommandToolConfigError("command cwd must be a directory")
        return target

    def _is_positive_number(self, value: object) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0
```

- [ ] **Step 4: Run cwd tests and confirm they pass**

Run:

```bash
pytest tests/test_command_tools.py::test_command_tools_accepts_workspace_cwd tests/test_command_tools.py::test_command_tools_rejects_invalid_cwd tests/test_command_tools.py::test_command_tools_rejects_cwd_symlink_escape -v
```

Expected:

```text
PASSED
```

---

### Task 3: Implement real command execution and unknown command denial

**Files:**

- Modify: `tests/test_command_tools.py`
- Modify: `src/atomic_agent/command_tools.py`

- [ ] **Step 1: Add failing run_command tests**

Append to `tests/test_command_tools.py`:

```python

def test_run_command_executes_declared_command_and_captures_output(tmp_path):
    policy = make_policy(
        "python-io",
        CommandSpec(
            argv=(str(PYTHON), "-c", "import sys; sys.stdout.write('ok'); sys.stderr.write('warn')"),
        ),
    )
    tools = make_tools(tmp_path, policy=policy)

    result = tools.run_command("python-io")

    assert result.ok is True
    assert result.tool == "run_command"
    assert result.command_id == "python-io"
    assert result.data["command_id"] == "python-io"
    assert result.data["argv"] == [str(PYTHON), "-c", "import sys; sys.stdout.write('ok'); sys.stderr.write('warn')"]
    assert result.data["cwd"] == str(tmp_path.resolve())
    assert result.data["exit_code"] == 0
    assert result.data["stdout"] == "ok"
    assert result.data["stderr"] == "warn"
    assert result.data["stdout_hash"] == "sha256:" + hashlib.sha256(b"ok").hexdigest()
    assert result.data["stderr_hash"] == "sha256:" + hashlib.sha256(b"warn").hexdigest()
    assert result.data["stdout_size_bytes"] == 2
    assert result.data["stderr_size_bytes"] == 4
    assert result.data["stdout_truncated"] is False
    assert result.data["stderr_truncated"] is False
    assert result.data["stdout_decoded_with_replacement"] is False
    assert result.data["stderr_decoded_with_replacement"] is False
    assert result.data["timeout_seconds"] == 1.0


def test_run_command_returns_completed_result_for_nonzero_exit_code(tmp_path):
    policy = make_policy(
        "python-fail",
        CommandSpec(argv=(str(PYTHON), "-c", "import sys; sys.stderr.write('failed'); sys.exit(3)")),
    )
    tools = make_tools(tmp_path, policy=policy)

    result = tools.run_command("python-fail")

    assert result.ok is True
    assert result.data["exit_code"] == 3
    assert result.data["stderr"] == "failed"


def test_run_command_rejects_unknown_command_without_execution(tmp_path):
    tools = make_tools(tmp_path)

    result = tools.run_command("missing")

    assert result.ok is False
    assert result.command_id == "missing"
    assert result.error_kind == "permission_denied"
    assert result.error_message == "command_id is not declared in command policy"
    assert result.data == {}


@pytest.mark.parametrize("command_id", ["", " ", "bad id", 123])
def test_run_command_rejects_invalid_command_id_input(tmp_path, command_id):
    tools = make_tools(tmp_path)

    result = tools.run_command(command_id)

    assert result.ok is False
    assert result.error_kind == "invalid_input"
    assert result.data == {}
```

- [ ] **Step 2: Run run_command tests and confirm method is missing**

Run:

```bash
pytest tests/test_command_tools.py::test_run_command_executes_declared_command_and_captures_output tests/test_command_tools.py::test_run_command_returns_completed_result_for_nonzero_exit_code tests/test_command_tools.py::test_run_command_rejects_unknown_command_without_execution tests/test_command_tools.py::test_run_command_rejects_invalid_command_id_input -v
```

Expected:

```text
AttributeError: 'CommandTools' object has no attribute 'run_command'
```

- [ ] **Step 3: Add subprocess execution implementation**

At the top of `src/atomic_agent/command_tools.py`, add imports:

```python
import hashlib
import subprocess
```

Inside `CommandTools`, add these methods before `_is_positive_number`:

```python
    def run_command(self, command_id: str) -> CommandToolResult:
        if not CommandPolicy.is_valid_command_id(command_id):
            return self._failure(
                command_id if isinstance(command_id, str) else None,
                "invalid_input",
                "command_id must be a non-empty stable identifier",
            )
        spec = self.policy.resolve(command_id)
        if spec is None:
            return self._failure(
                command_id,
                "permission_denied",
                "command_id is not declared in command policy",
            )

        timeout = spec.timeout_seconds if spec.timeout_seconds is not None else self.config.default_timeout_seconds
        cwd = self._cwd_by_command_id[command_id]
        env = dict(spec.env) if spec.env is not None else {}

        try:
            completed = subprocess.run(
                list(spec.argv),
                cwd=str(cwd),
                env=env,
                shell=False,
                capture_output=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return self._failure(command_id, "timeout", "Command exceeded timeout_seconds")
        except OSError as error:
            return self._failure(command_id, "execution_failed", str(error))

        stdout_data = self._stream_data(completed.stdout)
        stderr_data = self._stream_data(completed.stderr)
        return CommandToolResult(
            ok=True,
            tool="run_command",
            command_id=command_id,
            data={
                "command_id": command_id,
                "argv": list(spec.argv),
                "cwd": str(cwd),
                "exit_code": completed.returncode,
                "stdout": stdout_data["text"],
                "stderr": stderr_data["text"],
                "stdout_hash": stdout_data["hash"],
                "stderr_hash": stderr_data["hash"],
                "stdout_size_bytes": stdout_data["size_bytes"],
                "stderr_size_bytes": stderr_data["size_bytes"],
                "stdout_truncated": stdout_data["truncated"],
                "stderr_truncated": stderr_data["truncated"],
                "stdout_decoded_with_replacement": stdout_data["decoded_with_replacement"],
                "stderr_decoded_with_replacement": stderr_data["decoded_with_replacement"],
                "timeout_seconds": timeout,
            },
        )

    def _stream_data(self, content: bytes) -> dict[str, Any]:
        size_bytes = len(content)
        truncated = size_bytes > self.config.max_output_bytes
        visible = content[: self.config.max_output_bytes]
        text, decoded_with_replacement = self._decode_bytes(visible)
        return {
            "text": text,
            "hash": self._sha256(content),
            "size_bytes": size_bytes,
            "truncated": truncated,
            "decoded_with_replacement": decoded_with_replacement,
        }

    def _decode_bytes(self, content: bytes) -> tuple[str, bool]:
        try:
            return content.decode("utf-8"), False
        except UnicodeDecodeError:
            return content.decode("utf-8", errors="replace"), True

    def _sha256(self, content: bytes) -> str:
        return f"sha256:{hashlib.sha256(content).hexdigest()}"

    def _failure(self, command_id: str | None, error_kind: str, error_message: str) -> CommandToolResult:
        return CommandToolResult(
            ok=False,
            tool="run_command",
            command_id=command_id,
            data={},
            error_kind=error_kind,
            error_message=error_message,
        )
```

- [ ] **Step 4: Run run_command tests and confirm they pass**

Run:

```bash
pytest tests/test_command_tools.py::test_run_command_executes_declared_command_and_captures_output tests/test_command_tools.py::test_run_command_returns_completed_result_for_nonzero_exit_code tests/test_command_tools.py::test_run_command_rejects_unknown_command_without_execution tests/test_command_tools.py::test_run_command_rejects_invalid_command_id_input -v
```

Expected:

```text
PASSED
```

---

### Task 4: Add timeout, output truncation, explicit env, cwd execution, and decode coverage

**Files:**

- Modify: `tests/test_command_tools.py`
- Verify: `src/atomic_agent/command_tools.py`

- [ ] **Step 1: Add behavior tests for limits and execution context**

Append to `tests/test_command_tools.py`:

```python

def test_run_command_times_out_and_returns_failure(tmp_path):
    policy = make_policy(
        "python-sleep",
        CommandSpec(
            argv=(str(PYTHON), "-c", "import time; time.sleep(2)"),
            timeout_seconds=0.1,
        ),
    )
    tools = make_tools(tmp_path, policy=policy)

    result = tools.run_command("python-sleep")

    assert result.ok is False
    assert result.error_kind == "timeout"
    assert result.data == {}


def test_run_command_truncates_stdout_and_hashes_full_output(tmp_path):
    policy = make_policy(
        "python-output",
        CommandSpec(argv=(str(PYTHON), "-c", "import sys; sys.stdout.write('abcdef')")),
    )
    tools = make_tools(tmp_path, policy=policy, config=command_config(max_output_bytes=4))

    result = tools.run_command("python-output")

    assert result.ok is True
    assert result.data["stdout"] == "abcd"
    assert result.data["stdout_size_bytes"] == 6
    assert result.data["stdout_hash"] == "sha256:" + hashlib.sha256(b"abcdef").hexdigest()
    assert result.data["stdout_truncated"] is True


def test_run_command_truncates_stderr_and_hashes_full_output(tmp_path):
    policy = make_policy(
        "python-stderr",
        CommandSpec(argv=(str(PYTHON), "-c", "import sys; sys.stderr.write('uvwxyz')")),
    )
    tools = make_tools(tmp_path, policy=policy, config=command_config(max_output_bytes=3))

    result = tools.run_command("python-stderr")

    assert result.ok is True
    assert result.data["stderr"] == "uvw"
    assert result.data["stderr_size_bytes"] == 6
    assert result.data["stderr_hash"] == "sha256:" + hashlib.sha256(b"uvwxyz").hexdigest()
    assert result.data["stderr_truncated"] is True


def test_run_command_records_decode_replacement_for_non_utf8_output(tmp_path):
    policy = make_policy(
        "python-binary-output",
        CommandSpec(argv=(str(PYTHON), "-c", "import sys; sys.stdout.buffer.write(b'\\xff')")),
    )
    tools = make_tools(tmp_path, policy=policy)

    result = tools.run_command("python-binary-output")

    assert result.ok is True
    assert result.data["stdout"] == "�"
    assert result.data["stdout_decoded_with_replacement"] is True


def test_run_command_uses_explicit_env_without_inheriting_process_env(tmp_path, monkeypatch):
    monkeypatch.setenv("ATOMIC_AGENT_SHOULD_NOT_LEAK", "leaked")
    policy = make_policy(
        "python-env",
        CommandSpec(
            argv=(
                str(PYTHON),
                "-c",
                "import os, sys; sys.stdout.write(os.environ.get('VISIBLE', 'missing') + ':' + os.environ.get('ATOMIC_AGENT_SHOULD_NOT_LEAK', 'not-leaked'))",
            ),
            env={"VISIBLE": "yes"},
        ),
    )
    tools = make_tools(tmp_path, policy=policy)

    result = tools.run_command("python-env")

    assert result.ok is True
    assert result.data["stdout"] == "yes:not-leaked"


def test_run_command_executes_in_declared_workspace_cwd(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    policy = make_policy(
        "python-cwd",
        CommandSpec(
            argv=(str(PYTHON), "-c", "from pathlib import Path; print(Path.cwd().name, end='')"),
            cwd="work",
        ),
    )
    tools = make_tools(tmp_path, policy=policy)

    result = tools.run_command("python-cwd")

    assert result.ok is True
    assert result.data["stdout"] == "work"
    assert result.data["cwd"] == str(work.resolve())
```

- [ ] **Step 2: Run behavior tests and confirm they pass with current implementation**

Run:

```bash
pytest tests/test_command_tools.py::test_run_command_times_out_and_returns_failure tests/test_command_tools.py::test_run_command_truncates_stdout_and_hashes_full_output tests/test_command_tools.py::test_run_command_truncates_stderr_and_hashes_full_output tests/test_command_tools.py::test_run_command_records_decode_replacement_for_non_utf8_output tests/test_command_tools.py::test_run_command_uses_explicit_env_without_inheriting_process_env tests/test_command_tools.py::test_run_command_executes_in_declared_workspace_cwd -v
```

Expected:

```text
PASSED
```

If any test fails, adjust only `src/atomic_agent/command_tools.py` so the behavior matches P0-005 spec; do not weaken tests, do not inherit process env, and do not replace the declared command.

---

### Task 5: Add command action dispatcher and parser boundary regression

**Files:**

- Modify: `tests/test_command_tools.py`
- Modify: `src/atomic_agent/command_tools.py`
- Verify: `tests/test_action_parser.py`
- Verify: `tests/test_models.py`

- [ ] **Step 1: Add failing dispatcher tests**

Update the `atomic_agent.command_tools` import in `tests/test_command_tools.py` to include `execute_command_action`:

```python
from atomic_agent.command_tools import (
    CommandPolicy,
    CommandSpec,
    CommandToolConfig,
    CommandToolConfigError,
    CommandToolResult,
    CommandTools,
    execute_command_action,
)
```

Append to `tests/test_command_tools.py`:

```python

def test_execute_command_action_dispatches_run_command(tmp_path):
    policy = make_policy(
        "python-dispatch",
        CommandSpec(argv=(str(PYTHON), "-c", "import sys; sys.stdout.write('dispatch')")),
    )
    tools = make_tools(tmp_path, policy=policy)
    action = AgentAction(
        action_id="act-command",
        action=AgentActionType.RUN_COMMAND,
        reason_summary="Run declared command.",
        input={"command_id": "python-dispatch"},
    )

    result = execute_command_action(action, tools)

    assert result.ok is True
    assert result.tool == "run_command"
    assert result.command_id == "python-dispatch"
    assert result.data["stdout"] == "dispatch"


def test_execute_command_action_rejects_non_command_action(tmp_path):
    tools = make_tools(tmp_path)
    action = AgentAction(
        action_id="act-read",
        action=AgentActionType.READ_FILE,
        reason_summary="Read file.",
        input={"path": "README.md"},
    )

    result = execute_command_action(action, tools)

    assert result.ok is False
    assert result.tool == "read_file"
    assert result.command_id is None
    assert result.error_kind == "unsupported_action"
    assert result.data == {}


def test_agent_action_still_rejects_run_command_shell_string():
    with pytest.raises(ValidationError):
        AgentAction(
            action_id="act-shell",
            action=AgentActionType.RUN_COMMAND,
            reason_summary="Run shell.",
            input={"command": "pytest -v"},
        )
```

- [ ] **Step 2: Run dispatcher tests and confirm function is missing or unsupported**

Run:

```bash
pytest tests/test_command_tools.py::test_execute_command_action_dispatches_run_command tests/test_command_tools.py::test_execute_command_action_rejects_non_command_action tests/test_command_tools.py::test_agent_action_still_rejects_run_command_shell_string -v
```

Expected before dispatcher implementation:

```text
ImportError: cannot import name 'execute_command_action'
```

If the import already exists from an earlier partial implementation, the expected failure is a failed dispatcher assertion.

- [ ] **Step 3: Add dispatcher imports and function**

At the top of `src/atomic_agent/command_tools.py`, add:

```python
from atomic_agent.models import AgentAction, AgentActionType
```

Add this function at module level after `CommandTools`:

```python
def execute_command_action(action: AgentAction, tools: CommandTools) -> CommandToolResult:
    if action.action != AgentActionType.RUN_COMMAND:
        return CommandToolResult(
            ok=False,
            tool=action.action.value,
            command_id=None,
            data={},
            error_kind="unsupported_action",
            error_message="Action is not a command action.",
        )
    try:
        return tools.run_command(**action.input)
    except TypeError as error:
        command_id = action.input.get("command_id") if isinstance(action.input.get("command_id"), str) else None
        return CommandToolResult(
            ok=False,
            tool=action.action.value,
            command_id=command_id,
            data={},
            error_kind="invalid_input",
            error_message=str(error),
        )
```

- [ ] **Step 4: Run dispatcher and parser boundary tests**

Run:

```bash
pytest tests/test_command_tools.py::test_execute_command_action_dispatches_run_command tests/test_command_tools.py::test_execute_command_action_rejects_non_command_action tests/test_command_tools.py::test_agent_action_still_rejects_run_command_shell_string tests/test_action_parser.py tests/test_models.py -v
```

Expected:

```text
PASSED
```

---

### Task 6: Run full verification and safety checks

**Files:**

- Verify: `src/atomic_agent/command_tools.py`
- Verify: `tests/test_command_tools.py`
- Verify: existing tests

- [ ] **Step 1: Run command tool tests**

Run:

```bash
pytest tests/test_command_tools.py -v
```

Expected:

```text
PASSED
```

- [ ] **Step 2: Run full test suite**

Run:

```bash
pytest -v
```

Expected:

```text
PASSED
```

- [ ] **Step 3: Check runtime source for environment fallback reads**

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

No output means runtime source does not read environment fallback. If output appears in `src/atomic_agent/command_tools.py`, remove the fallback read and pass env explicitly from `CommandSpec.env`.

- [ ] **Step 4: Check command execution does not use shell mode**

Run:

```bash
python - <<'PY'
from pathlib import Path
text = Path('src/atomic_agent/command_tools.py').read_text(encoding='utf-8')
for forbidden in ('shell=True', 'os.system', 'popen(', 'getoutput('):
    if forbidden in text:
        print(f'forbidden command execution pattern: {forbidden}')
PY
```

Expected:

```text

```

No output means command execution avoids the forbidden shell execution patterns.

- [ ] **Step 5: Check working tree scope**

Run:

```bash
git status --short
```

Expected after implementation, before marking P0-005 completed:

```text
 M docs/04-implementation-plan/INDEX.md
 M docs/04-implementation-spec/INDEX.md
?? docs/04-implementation-plan/P0-005-command-policy-run-command-plan.md
?? docs/04-implementation-spec/P0-005-command-policy-run-command-spec.md
?? src/atomic_agent/command_tools.py
?? tests/test_command_tools.py
```

If `git status --short` shows unrelated files, inspect them before continuing and do not include unrelated changes in this task.

---

### Task 7: Update docs after implementation passes

**Files:**

- Modify: `docs/04-implementation-backlog/backlog.md`
- Modify: `docs/04-implementation-spec/P0-005-command-policy-run-command-spec.md`
- Modify: `docs/04-implementation-plan/P0-005-command-policy-run-command-plan.md`
- Modify: `docs/04-implementation-spec/INDEX.md`
- Modify: `docs/04-implementation-plan/INDEX.md`

- [ ] **Step 1: Mark P0-005 completed only after tests pass**

Change `docs/04-implementation-backlog/backlog.md` from:

```markdown
| P0-005 | 实现 command policy（命令策略）和 run_command | pending | `mvp-runtime-spec.md` |
```

To:

```markdown
| P0-005 | 实现 command policy（命令策略）和 run_command | completed | `P0-005-command-policy-run-command-spec.md`, `mvp-runtime-spec.md` |
```

- [ ] **Step 2: Mark spec implemented**

Change `docs/04-implementation-spec/P0-005-command-policy-run-command-spec.md` from:

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

Change `docs/04-implementation-plan/P0-005-command-policy-run-command-plan.md` from:

```markdown
**Status:** draft
```

To:

```markdown
**Status:** implemented
```

- [ ] **Step 4: Move spec index entry to completed / archived**

Change `docs/04-implementation-spec/INDEX.md` by removing the current active row:

```markdown
| `P0-005-command-policy-run-command-spec.md` | draft | 定义 P0-005 command policy（命令策略）和 run_command（运行声明命令）的输入、输出、权限边界和失败语义 | 实现 P0-005 前 |
```

Add this completed row:

```markdown
| `P0-005-command-policy-run-command-spec.md` | 2026-06-05 | 已实现 P0-005 command policy（命令策略）和 run_command（运行声明命令），保留为命令工具规格记录 |
```

- [ ] **Step 5: Move plan index entry to completed / archived**

Change `docs/04-implementation-plan/INDEX.md` by removing the current active row:

```markdown
| `P0-005-command-policy-run-command-plan.md` | draft | 实施 P0-005 command policy（命令策略）和 run_command（运行声明命令）的 TDD 计划 | 执行 P0-005 时 |
```

Add this completed row:

```markdown
| `P0-005-command-policy-run-command-plan.md` | 2026-06-05 | 已实施 P0-005 command policy（命令策略）和 run_command（运行声明命令），保留为 TDD 实施记录 |
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

`git status --short` should show only P0-005 implementation, tests, and required docs/index updates.

---

## Self-Review Checklist

Before implementation is considered ready for review:

- [ ] Spec coverage: Every requirement in `docs/04-implementation-spec/P0-005-command-policy-run-command-spec.md` is covered by a task, test, or explicit out-of-scope statement.
- [ ] Placeholder scan: This plan contains no deferred command behavior, no unspecified test case, no silent fallback, and no mock success path.
- [ ] Type consistency: `CommandSpec`, `CommandToolConfig`, `CommandToolResult`, `CommandToolConfigError`, `CommandPolicy`, `CommandTools`, and `execute_command_action` names match across tests, implementation steps, and spec.
- [ ] Scope check: No event recorder, JSONL output, network policy, provider logic, global budget logic, service runner, or AgentLoop logic is included.
- [ ] Security check: Every configured cwd goes through `WorkspacePathGuard`; unknown commands are denied; env is explicit; `shell=True` is not used; executable lookup does not rely on PATH.
- [ ] Result check: Non-zero exit code is a completed command result, while timeout and execution startup failure are structured tool failures.
- [ ] Verification check: `pytest -v` passes with real execution output.
