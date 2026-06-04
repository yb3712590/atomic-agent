# Action Parser Implementation Plan

## Status

implemented

## Goal

实现 P0-002 `JSON action parser`（JSON 动作解析器），把 provider output（模型供应商输出）严格转换为 `AgentAction`（智能体动作），并为后续 AgentLoop（智能体循环）的 `action.rejected` event（动作拒绝事件）提供结构化失败信息。

## Architecture

新增 `src/atomic_agent/action_parser.py`（动作解析器模块），让它只负责 JSON parsing（JSON 解析）和 schema validation（模式校验）。继续复用 `src/atomic_agent/models.py` 中的 `AgentAction`（智能体动作）作为 envelope schema（信封结构模式）事实源；在 `AgentAction` 上补充最小 `run_command`（运行命令）约束，防止直接构造模型绕过 parser（解析器）。

## Tech Stack

- Python 3.11+
- Pydantic v2
- pytest

---

## Files

- Create: `src/atomic_agent/action_parser.py`
- Create: `tests/test_action_parser.py`
- Modify: `src/atomic_agent/models.py`
- Modify: `docs/04-implementation-backlog/backlog.md` after implementation passes
- Verify: `tests/test_models.py`

## Task 1: Add parser tests first

**Files:**

- Create: `tests/test_action_parser.py`

- [ ] **Step 1: Write failing tests for successful parsing and structured failures**

Add:

```python
import pytest

from atomic_agent.action_parser import ActionParseError, parse_agent_action
from atomic_agent.models import AgentActionType


def test_parse_agent_action_accepts_valid_json_text():
    action = parse_agent_action(
        """
        {
          "action_id": "step-0001",
          "action": "read_file",
          "reason_summary": "Read the target file before patching.",
          "input": {"path": "README.md", "offset": 0, "limit": 12000}
        }
        """
    )

    assert action.action_id == "step-0001"
    assert action.action == AgentActionType.READ_FILE
    assert action.input["path"] == "README.md"


def test_parse_agent_action_accepts_run_command_with_command_id():
    action = parse_agent_action(
        """
        {
          "action_id": "step-0002",
          "action": "run_command",
          "reason_summary": "Run the declared test command.",
          "input": {"command_id": "test"}
        }
        """
    )

    assert action.action == AgentActionType.RUN_COMMAND
    assert action.input == {"command_id": "test"}


def test_parse_agent_action_rejects_invalid_json():
    with pytest.raises(ActionParseError) as error:
        parse_agent_action("not json")

    assert error.value.kind == "invalid_json"
    assert "valid JSON" in error.value.message


def test_parse_agent_action_rejects_non_object_json():
    with pytest.raises(ActionParseError) as error:
        parse_agent_action("[]")

    assert error.value.kind == "invalid_action"
    assert "object" in error.value.message


def test_parse_agent_action_rejects_unknown_action():
    with pytest.raises(ActionParseError) as error:
        parse_agent_action(
            """
            {
              "action_id": "step-0003",
              "action": "free_shell",
              "reason_summary": "Run a shell command.",
              "input": {"command": "rm -rf ."}
            }
            """
        )

    assert error.value.kind == "schema_validation_failed"


def test_parse_agent_action_rejects_extra_envelope_fields():
    with pytest.raises(ActionParseError) as error:
        parse_agent_action(
            """
            {
              "action_id": "step-0004",
              "action": "read_file",
              "reason_summary": "Read a file.",
              "input": {"path": "README.md"},
              "unexpected": "not allowed"
            }
            """
        )

    assert error.value.kind == "schema_validation_failed"


def test_parse_agent_action_rejects_run_command_shell_string():
    with pytest.raises(ActionParseError) as error:
        parse_agent_action(
            """
            {
              "action_id": "step-0005",
              "action": "run_command",
              "reason_summary": "Run tests.",
              "input": {"command": "pytest -v"}
            }
            """
        )

    assert error.value.kind == "schema_validation_failed"
    assert "command_id" in error.value.message
```

- [ ] **Step 2: Run the new tests and confirm they fail because the module does not exist**

Run:

```bash
pytest tests/test_action_parser.py -v
```

Expected:

```text
ModuleNotFoundError: No module named 'atomic_agent.action_parser'
```

## Task 2: Implement the parser module

**Files:**

- Create: `src/atomic_agent/action_parser.py`

- [ ] **Step 1: Add `ActionParseError` and `parse_agent_action`**

Add:

```python
import json
from typing import Any

from pydantic import ValidationError

from atomic_agent.models import AgentAction


class ActionParseError(ValueError):
    def __init__(self, kind: str, message: str):
        self.kind = kind
        self.message = message
        super().__init__(message)


def parse_agent_action(provider_output: str) -> AgentAction:
    try:
        parsed: Any = json.loads(provider_output)
    except json.JSONDecodeError as error:
        raise ActionParseError("invalid_json", "Provider output must be valid JSON.") from error

    if not isinstance(parsed, dict):
        raise ActionParseError("invalid_action", "Provider output JSON must be an object.")

    try:
        return AgentAction.model_validate(parsed)
    except ValidationError as error:
        raise ActionParseError("schema_validation_failed", str(error)) from error
```

- [ ] **Step 2: Run parser tests**

Run:

```bash
pytest tests/test_action_parser.py -v
```

Expected:

```text
FAILED tests/test_action_parser.py::test_parse_agent_action_rejects_run_command_shell_string
```

The expected failure proves the generic parser exists but `run_command` input still needs action-specific validation.

## Task 3: Add minimal `run_command` validation to the model

**Files:**

- Modify: `src/atomic_agent/models.py`
- Modify: `tests/test_models.py`

- [ ] **Step 1: Add model tests that direct construction cannot bypass `run_command` rules**

Append to `tests/test_models.py`:

```python

def test_agent_action_rejects_run_command_without_command_id():
    with pytest.raises(ValidationError):
        AgentAction(
            action_id="step-0006",
            action="run_command",
            reason_summary="Run tests.",
            input={"command": "pytest -v"},
        )


def test_agent_action_accepts_run_command_with_command_id():
    action = AgentAction(
        action_id="step-0007",
        action="run_command",
        reason_summary="Run declared tests.",
        input={"command_id": "test"},
    )

    assert action.input == {"command_id": "test"}
```

- [ ] **Step 2: Run the targeted model tests and confirm the first new test fails**

Run:

```bash
pytest tests/test_models.py::test_agent_action_rejects_run_command_without_command_id tests/test_models.py::test_agent_action_accepts_run_command_with_command_id -v
```

Expected:

```text
FAILED tests/test_models.py::test_agent_action_rejects_run_command_without_command_id
PASSED tests/test_models.py::test_agent_action_accepts_run_command_with_command_id
```

- [ ] **Step 3: Add the validator to `AgentAction`**

Modify `AgentAction` in `src/atomic_agent/models.py` to:

```python
class AgentAction(StrictModel):
    action_id: str
    action: AgentActionType
    reason_summary: str
    input: dict[str, Any]

    @model_validator(mode="after")
    def run_command_uses_command_id(self):
        if self.action != AgentActionType.RUN_COMMAND:
            return self
        forbidden_keys = {"command", "shell", "cmd"}
        if forbidden_keys.intersection(self.input):
            raise ValueError("run_command input must use command_id, not a shell command string")
        if "command_id" not in self.input:
            raise ValueError("run_command input requires command_id")
        return self
```

- [ ] **Step 4: Run parser and model tests**

Run:

```bash
pytest tests/test_action_parser.py tests/test_models.py -v
```

Expected:

```text
PASSED
```

## Task 4: Run full verification

**Files:**

- Verify all tests

- [ ] **Step 1: Run the full test suite**

Run:

```bash
pytest -v
```

Expected:

```text
PASSED
```

- [ ] **Step 2: Check git diff for accidental unrelated changes**

Run:

```bash
git diff -- src/atomic_agent/action_parser.py src/atomic_agent/models.py tests/test_action_parser.py tests/test_models.py docs/04-implementation-backlog/backlog.md docs/04-implementation-spec/INDEX.md docs/04-implementation-plan/INDEX.md
```

Expected:

```text
Only P0-002 parser, tests, and required docs/index changes are present.
```

## Task 5: Update backlog after implementation passes

**Files:**

- Modify: `docs/04-implementation-backlog/backlog.md`

- [ ] **Step 1: Mark P0-002 completed**

Change:

```markdown
| P0-002 | 实现 JSON action parser（JSON 动作解析器）和严格 schema validation（模式校验） | pending | `agent-action-protocol.md` |
```

To:

```markdown
| P0-002 | 实现 JSON action parser（JSON 动作解析器）和严格 schema validation（模式校验） | completed | `agent-action-protocol.md` |
```

- [ ] **Step 2: Run final verification**

Run:

```bash
pytest -v
```

Expected:

```text
PASSED
```

## Self-Review Checklist

Before implementation is considered ready for review:

- [ ] No parser fallback extracts JSON from Markdown code fences.
- [ ] No environment variables, `.env`, local config files, or process defaults are read.
- [ ] Invalid provider output cannot produce a default or empty `AgentAction`.
- [ ] `run_command` cannot accept free shell strings through parser or direct model construction.
- [ ] Path, command policy, network policy, events, tools, and AgentLoop remain outside this task.
- [ ] `pytest -v` passes with real execution output.
