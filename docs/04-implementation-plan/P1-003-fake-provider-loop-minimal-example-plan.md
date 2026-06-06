# Fake Provider Loop Minimal Example Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement P1-003 `fake provider loop acceptance`（假模型供应商循环验收） and a real `minimal example`（最小示例） command that runs the existing AgentLoop（智能体循环）, writes auditable outputs, and updates README only after the command is verified.

**Architecture:** Add a focused examples package（示例包） that constructs an explicit standalone AgentInvocation（独立智能体调用请求） and uses the existing AgentLoop（智能体循环）, FilesystemTools（文件系统工具）, CommandTools（命令工具）, EventRecorder（事件记录器）, and ArtifactWriter（产物写入器）. The example uses a deterministic ScriptedProvider（脚本化假模型供应商） only to drive real runtime semantics: write a draft file, run a declared command that fails, patch the file, rerun the command successfully, and submit a result with event/artifact evidence.

**Tech Stack:** Python 3.11+, argparse（命令行参数解析）, pathlib（路径处理）, json（JSON 序列化）, time.monotonic（单调时钟）, subprocess-based pytest（基于子进程的测试）, existing atomic-agent runtime modules（现有原子智能体运行时模块）.

**Status:** implemented

---

## Scope

This plan implements P1-003 only.

In scope:

- Create `src/atomic_agent/examples/__init__.py`（示例包初始化文件）.
- Create `src/atomic_agent/examples/minimal_fake_loop.py`（最小假模型循环示例入口）.
- Create `tests/test_minimal_fake_loop_example.py`（最小示例端到端测试）.
- Update `README.md` only after the subprocess example command passes.
- Update P1-003 spec / plan / backlog / indexes only after implementation and verification pass.
- Use `PYTHONPATH=src python -m atomic_agent.examples.minimal_fake_loop ...` as the source-tree command（源码树命令） documented in README.

Out of scope:

- No real provider integration（真实模型供应商集成）.
- No Boardroom AgentRuntimePort adapter（Boardroom 智能体运行时端口适配器）.
- No new runtime loop（新运行时循环）.
- No new permission engine（新权限引擎）.
- No arbitrary shell（任意 shell）.
- No `.env`, `os.environ`, `getenv`, or dotenv-based configuration fallback（基于环境的配置兜底）.
- No network feature changes（网络能力变更）.
- No commit unless the user explicitly requests it.

## File Structure

- Create: `tests/test_minimal_fake_loop_example.py`
  - Runs the example as a real subprocess.
  - Verifies result JSON, event JSONL, workspace output, artifacts, command exit codes, and no-overwrite guards.
- Create: `src/atomic_agent/examples/__init__.py`
  - Makes `atomic_agent.examples`（原子智能体示例包） importable as a Python package.
- Create: `src/atomic_agent/examples/minimal_fake_loop.py`
  - Implements CLI parsing, explicit invocation construction, deterministic fake provider, runtime dependency wiring, no-overwrite path preparation, result writing, and JSON stdout/stderr summaries.
- Modify after implementation passes: `README.md`
  - Replace the current “no runnable minimal example” section with the verified source-tree command and output explanation.
- Modify after implementation passes: `docs/04-implementation-backlog/backlog.md`
  - Mark P1-003 completed and keep P1-004 dependency notes accurate.
- Modify after implementation passes: `docs/04-implementation-spec/P1-003-fake-provider-loop-minimal-example-spec.md`
  - Change status from `draft` to `implemented`.
- Modify after implementation passes: `docs/04-implementation-plan/P1-003-fake-provider-loop-minimal-example-plan.md`
  - Change status from `draft` to `implemented`.
- Modify after implementation passes: `docs/04-implementation-spec/INDEX.md`
  - Move the P1-003 spec from active draft to completed / archived.
- Modify after implementation passes: `docs/04-implementation-plan/INDEX.md`
  - Move this plan from active draft to completed / archived.
- Modify after implementation passes if global active pointers changed: `docs/INDEX.md`
  - Remove P1-003 draft pointers after completion.

---

### Task 1: Add failing subprocess tests for the minimal example

**Files:**

- Create: `tests/test_minimal_fake_loop_example.py`

- [ ] **Step 1: Write the failing end-to-end tests**

Create `tests/test_minimal_fake_loop_example.py` with this exact content:

```python
import json
import os
from pathlib import Path
import re
import subprocess
import sys


PYTHON = Path(sys.executable).resolve()
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")


def make_paths(tmp_path):
    base = tmp_path / "minimal-example"
    return {
        "workspace": base / "workspace",
        "event_stream": base / "events" / "events.jsonl",
        "artifact_root": base / "artifacts",
        "result": base / "result.json",
    }


def run_example(paths, env_overrides=None):
    env = dict(os.environ)
    if env_overrides:
        env.update(env_overrides)
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(SRC_ROOT) if not existing_pythonpath else f"{SRC_ROOT}{os.pathsep}{existing_pythonpath}"
    return subprocess.run(
        [
            str(PYTHON),
            "-m",
            "atomic_agent.examples.minimal_fake_loop",
            "--run-id",
            "minimal_example",
            "--workspace",
            str(paths["workspace"]),
            "--event-stream",
            str(paths["event_stream"]),
            "--artifact-root",
            str(paths["artifact_root"]),
            "--result",
            str(paths["result"]),
        ],
        cwd=PROJECT_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_minimal_fake_loop_example_runs_real_multistep_loop(tmp_path):
    paths = make_paths(tmp_path)

    completed = run_example(paths)

    assert completed.returncode == 0, completed.stderr
    assert completed.stderr == ""
    stdout_payload = json.loads(completed.stdout)
    assert '": "' in completed.stdout
    assert stdout_payload == {
        "status": "completed",
        "result_path": str(paths["result"].absolute()),
        "event_stream_path": str(paths["event_stream"].absolute()),
        "artifact_root": str(paths["artifact_root"].absolute()),
        "workspace_output_path": str((paths["workspace"] / "work" / "output.txt").absolute()),
    }

    assert (paths["workspace"] / "work" / "output.txt").read_text(encoding="utf-8") == "fixed"
    result_payload = json.loads(paths["result"].read_text(encoding="utf-8"))
    assert result_payload["run_id"] == "minimal_example"
    assert result_payload["status"] == "completed"
    assert result_payload["summary"] == "Created fixed output through a controlled fake provider loop."
    assert result_payload["event_stream_ref"] == "artifact://minimal_example/events.jsonl"
    assert SHA256_PATTERN.fullmatch(result_payload["events_hash"])
    assert [attempt["tool"] for attempt in result_payload["tool_attempts"]] == [
        "write_file",
        "run_command",
        "apply_patch",
        "run_command",
    ]
    assert [mutation["path"] for mutation in result_payload["workspace_mutations"]] == [
        "work/output.txt",
        "work/output.txt",
    ]

    events = read_jsonl(paths["event_stream"])
    event_types = [event["type"] for event in events]
    assert event_types[0] == "run.started"
    assert event_types[-2:] == ["result.submitted", "run.completed"]
    assert "provider.turn.completed" in event_types
    assert "action.parsed" in event_types
    assert "permission.decided" in event_types
    assert "tool.attempt.completed" in event_types
    assert event_types.count("workspace.mutation.recorded") == 2
    assert event_types.count("command.completed") == 2
    assert [event["sequence"] for event in events] == list(range(1, len(events) + 1))
    assert events[0]["previous_event_hash"] is None
    assert all(events[index]["previous_event_hash"] == events[index - 1]["event_hash"] for index in range(1, len(events)))

    command_events = [event for event in events if event["type"] == "command.completed"]
    assert [event["payload"]["exit_code"] for event in command_events] == [3, 0]
    assert all(event["payload"]["stdout"]["artifact_ref"].endswith(".stdout.txt") for event in command_events)
    assert all(event["payload"]["stderr"]["artifact_ref"].endswith(".stderr.txt") for event in command_events)

    expected_artifacts = [
        paths["artifact_root"] / "provider" / "turn_000001.txt",
        paths["artifact_root"] / "provider" / "turn_000005.txt",
        paths["artifact_root"] / "observations" / "tool_attempt_000002.json",
        paths["artifact_root"] / "diffs" / "tool_attempt_000001.diff",
        paths["artifact_root"] / "diffs" / "tool_attempt_000003.diff",
        paths["artifact_root"] / "commands" / "tool_attempt_000002.stdout.txt",
        paths["artifact_root"] / "commands" / "tool_attempt_000002.stderr.txt",
        paths["artifact_root"] / "commands" / "tool_attempt_000004.stdout.txt",
        paths["artifact_root"] / "commands" / "tool_attempt_000004.stderr.txt",
        paths["artifact_root"] / "results" / "step-0005.json",
    ]
    assert all(path.exists() for path in expected_artifacts)


def test_minimal_fake_loop_expands_tilde_paths(tmp_path):
    fake_home = tmp_path / "home"
    paths = {
        "workspace": "~/minimal-example/workspace",
        "event_stream": "~/minimal-example/events/events.jsonl",
        "artifact_root": "~/minimal-example/artifacts",
        "result": "~/minimal-example/result.json",
    }

    completed = run_example(paths, env_overrides={"HOME": str(fake_home)})

    assert completed.returncode == 0, completed.stderr
    stdout_payload = json.loads(completed.stdout)
    assert stdout_payload["workspace_output_path"] == str(fake_home / "minimal-example" / "workspace" / "work" / "output.txt")
    assert stdout_payload["result_path"] == str(fake_home / "minimal-example" / "result.json")
    assert (fake_home / "minimal-example" / "workspace" / "work" / "output.txt").read_text(encoding="utf-8") == "fixed"
    result_payload = json.loads((fake_home / "minimal-example" / "result.json").read_text(encoding="utf-8"))
    assert result_payload["status"] == "completed"


def test_minimal_fake_loop_refuses_to_overwrite_existing_result_file(tmp_path):
    paths = make_paths(tmp_path)
    paths["result"].parent.mkdir(parents=True)
    paths["result"].write_text("keep", encoding="utf-8")

    completed = run_example(paths)

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert paths["result"].read_text(encoding="utf-8") == "keep"
    error_payload = json.loads(completed.stderr)
    assert error_payload["status"] == "failed"
    assert "result path already exists" in error_payload["error"]


def test_minimal_fake_loop_refuses_non_empty_artifact_root(tmp_path):
    paths = make_paths(tmp_path)
    paths["artifact_root"].mkdir(parents=True)
    (paths["artifact_root"] / "old.txt").write_text("old", encoding="utf-8")

    completed = run_example(paths)

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert (paths["artifact_root"] / "old.txt").read_text(encoding="utf-8") == "old"
    error_payload = json.loads(completed.stderr)
    assert error_payload["status"] == "failed"
    assert "artifact root must be empty" in error_payload["error"]


def test_minimal_fake_loop_refuses_existing_workspace_output(tmp_path):
    paths = make_paths(tmp_path)
    output_path = paths["workspace"] / "work" / "output.txt"
    output_path.parent.mkdir(parents=True)
    output_path.write_text("keep", encoding="utf-8")

    completed = run_example(paths)

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert output_path.read_text(encoding="utf-8") == "keep"
    error_payload = json.loads(completed.stderr)
    assert error_payload["status"] == "failed"
    assert "workspace output path already exists" in error_payload["error"]
```

- [ ] **Step 2: Run the new tests and confirm they fail before implementation**

Run:

```bash
python -m pytest tests/test_minimal_fake_loop_example.py -q
```

Expected before implementation:

```text
FAILED tests/test_minimal_fake_loop_example.py::test_minimal_fake_loop_example_runs_real_multistep_loop
FAILED tests/test_minimal_fake_loop_example.py::test_minimal_fake_loop_refuses_to_overwrite_existing_result_file
FAILED tests/test_minimal_fake_loop_example.py::test_minimal_fake_loop_refuses_non_empty_artifact_root
FAILED tests/test_minimal_fake_loop_example.py::test_minimal_fake_loop_refuses_existing_workspace_output
```

The failure reason should show that `atomic_agent.examples.minimal_fake_loop`（原子智能体最小示例模块） does not exist yet.

---

### Task 2: Implement the examples package and minimal fake loop CLI

**Files:**

- Create: `src/atomic_agent/examples/__init__.py`
- Create: `src/atomic_agent/examples/minimal_fake_loop.py`

- [ ] **Step 1: Create the examples package**

Create `src/atomic_agent/examples/__init__.py`:

```python
"""Runnable examples for atomic-agent."""
```

- [ ] **Step 2: Create the minimal fake loop module**

Create `src/atomic_agent/examples/minimal_fake_loop.py` with this exact content:

```python
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
import time
from typing import Any, Sequence

from atomic_agent.agent_loop import AgentLoop, AgentLoopConfig, AgentLoopDependencies, ProviderContext
from atomic_agent.artifacts import ArtifactWriter, ArtifactWriterConfig
from atomic_agent.command_tools import CommandPolicy, CommandSpec, CommandToolConfig, CommandTools
from atomic_agent.event_recorder import EventRecorder, EventRecorderConfig
from atomic_agent.filesystem_tools import FilesystemToolConfig, FilesystemTools
from atomic_agent.models import AgentInvocation, AgentRunResult, AgentRunStatus
from atomic_agent.path_guard import WorkspacePathGuard


SUMMARY = "Created fixed output through a controlled fake provider loop."
WORKSPACE_OUTPUT_PATH = "work/output.txt"
EXPECTED_OUTPUT_CONTENT = "fixed"
CHECK_OUTPUT_SCRIPT = f"""\
from pathlib import Path
import sys

content = Path({WORKSPACE_OUTPUT_PATH!r}).read_text(encoding='utf-8')
sys.exit(0 if content == {EXPECTED_OUTPUT_CONTENT!r} else 3)
""".strip()


class ExampleInputError(ValueError):
    pass


@dataclass(frozen=True)
class ExamplePaths:
    workspace: Path
    event_stream: Path
    artifact_root: Path
    result: Path


class ScriptedProvider:
    def __init__(self, outputs: Sequence[str]):
        self.outputs = list(outputs)

    def complete(self, context: ProviderContext) -> str:
        # Fake provider（假模型供应商）是确定性脚本；接收 context 只用于满足 ProviderAdapter（模型供应商适配器）接口。
        _ = context
        if not self.outputs:
            raise RuntimeError("scripted provider has no remaining outputs")
        return self.outputs.pop(0)


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        paths = ExamplePaths(
            workspace=resolve_cli_path(args.workspace),
            event_stream=resolve_cli_path(args.event_stream),
            artifact_root=resolve_cli_path(args.artifact_root),
            result=resolve_cli_path(args.result),
        )
        prepare_paths(paths)
    except ExampleInputError as error:
        print_failure(str(error))
        return 2

    result = run_example(args.run_id, paths)
    write_result(paths.result, result)
    print_success(paths, result)
    return 0 if result.status == AgentRunStatus.COMPLETED else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the atomic-agent minimal fake provider loop example.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--event-stream", required=True)
    parser.add_argument("--artifact-root", required=True)
    parser.add_argument("--result", required=True)
    return parser


def resolve_cli_path(value: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ExampleInputError("path arguments must be non-empty strings")
    return Path(value).expanduser().absolute()


def prepare_paths(paths: ExamplePaths) -> None:
    workspace_output = paths.workspace / "work" / "output.txt"
    if paths.result.exists() or paths.result.is_symlink():
        raise ExampleInputError("result path already exists")
    if paths.event_stream.is_symlink() or paths.event_stream.is_dir():
        raise ExampleInputError("event stream path must be a file path")
    if paths.event_stream.exists() and paths.event_stream.stat().st_size > 0:
        raise ExampleInputError("event stream path must be empty or absent")
    if paths.artifact_root.is_symlink():
        raise ExampleInputError("artifact root must not be a symlink")
    if paths.artifact_root.exists():
        if not paths.artifact_root.is_dir():
            raise ExampleInputError("artifact root must be a directory")
        if any(paths.artifact_root.iterdir()):
            raise ExampleInputError("artifact root must be empty")
    if workspace_output.exists() or workspace_output.is_symlink():
        raise ExampleInputError("workspace output path already exists")

    ensure_directory(paths.workspace)
    ensure_directory(paths.event_stream.parent)
    ensure_directory(paths.artifact_root)
    ensure_directory(paths.result.parent)


def ensure_directory(path: Path) -> None:
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise ExampleInputError(f"failed to create directory {path}: {error}") from error
    if not path.is_dir():
        raise ExampleInputError(f"path is not a directory: {path}")


def run_example(run_id: str, paths: ExamplePaths) -> AgentRunResult:
    invocation = build_invocation(paths)
    loop = build_loop(run_id, paths)
    return loop.run(invocation)


def build_invocation(paths: ExamplePaths) -> AgentInvocation:
    return AgentInvocation(
        invocation_id="inv_minimal_example",
        task=f"Create {WORKSPACE_OUTPUT_PATH} with the content {EXPECTED_OUTPUT_CONTENT} through a controlled fake provider loop.",
        workspace_root=str(paths.workspace),
        allowed_write_set=["work/"],
        tools=["list_files", "read_file", "search_files", "write_file", "apply_patch", "run_command", "submit_result"],
        permission_policy={"policy_ref": "policy://examples/minimal-fake-loop"},
        provider_profile={"provider": "fake", "model": "scripted-minimal-loop"},
        budgets={
            "max_steps": 8,
            "max_parse_failures": 1,
            "max_observation_chars": 10000,
            "max_wall_seconds": 30.0,
        },
        output_requirements={"summary": True, "event_stream": True, "artifacts": True},
        metadata={"example": "minimal_fake_loop"},
    )


def build_loop(run_id: str, paths: ExamplePaths) -> AgentLoop:
    guard = WorkspacePathGuard(paths.workspace, allowed_write_set=["work/"])
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
    command_tools = CommandTools(
        guard,
        CommandPolicy(
            {
                "check-output": CommandSpec(
                    argv=(
                        str(Path(sys.executable).resolve()),
                        "-c",
                        CHECK_OUTPUT_SCRIPT,
                    )
                )
            }
        ),
        CommandToolConfig(default_timeout_seconds=2.0, max_timeout_seconds=5.0, max_output_bytes=4096),
    )
    recorder = EventRecorder(
        run_id=run_id,
        config=EventRecorderConfig(
            event_stream_path=paths.event_stream,
            event_stream_ref=f"artifact://{run_id}/events.jsonl",
        ),
        clock=utc_timestamp,
    )
    artifact_writer = ArtifactWriter(
        ArtifactWriterConfig(
            artifact_root=paths.artifact_root,
            artifact_ref_prefix=f"artifact://{run_id}",
        )
    )
    return AgentLoop(
        AgentLoopConfig(run_id=run_id),
        AgentLoopDependencies(
            provider=ScriptedProvider(provider_outputs()),
            filesystem_tools=filesystem_tools,
            command_tools=command_tools,
            event_recorder=recorder,
            artifact_writer=artifact_writer,
            runtime_clock=time.monotonic,
        ),
    )


def provider_outputs() -> list[str]:
    return [
        action("step-0001", "write_file", {"path": WORKSPACE_OUTPUT_PATH, "content": "draft"}),
        action("step-0002", "run_command", {"command_id": "check-output"}),
        action("step-0003", "apply_patch", {"path": WORKSPACE_OUTPUT_PATH, "old_text": "draft", "new_text": EXPECTED_OUTPUT_CONTENT}),
        action("step-0004", "run_command", {"command_id": "check-output"}),
        action(
            "step-0005",
            "submit_result",
            {
                "summary": SUMMARY,
                "produced_paths": [WORKSPACE_OUTPUT_PATH],
                "evidence_refs": ["step-0001", "step-0002", "step-0003", "step-0004"],
            },
        ),
    ]


def action(action_id: str, action_name: str, input_payload: dict[str, Any]) -> str:
    return json.dumps(
        {
            "action_id": action_id,
            "action": action_name,
            "reason_summary": f"Run {action_name} in the minimal fake provider loop.",
            "input": input_payload,
        },
        sort_keys=True,
    )


def utc_timestamp() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def write_result(path: Path, result: AgentRunResult) -> None:
    payload = result.model_dump(mode="json")
    path.write_text(json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def print_success(paths: ExamplePaths, result: AgentRunResult) -> None:
    status = "completed" if result.status == AgentRunStatus.COMPLETED else "failed"
    print(
        json.dumps(
            {
                "status": status,
                "result_path": str(paths.result),
                "event_stream_path": str(paths.event_stream),
                "artifact_root": str(paths.artifact_root),
                "workspace_output_path": str(paths.workspace / WORKSPACE_OUTPUT_PATH),
            },
            sort_keys=True,
            ensure_ascii=False,
        )
    )


def print_failure(message: str) -> None:
    print(json.dumps({"status": "failed", "error": message}, sort_keys=True, ensure_ascii=False), file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Run the subprocess tests and confirm they pass**

Run:

```bash
python -m pytest tests/test_minimal_fake_loop_example.py -q
```

Expected:

```text
5 passed
```

If the success test fails because the subprocess cannot import `atomic_agent`, verify the test command sets `PYTHONPATH` to the absolute `src` directory. Do not add environment-based runtime configuration fallback to the example.

---

### Task 3: Verify the example manually before touching README

**Files:**

- Verify: `src/atomic_agent/examples/minimal_fake_loop.py`

- [ ] **Step 1: Run the source-tree example command manually**

Run:

```bash
rm -rf /tmp/atomic-agent-minimal-example
PYTHONPATH=src python -m atomic_agent.examples.minimal_fake_loop \
  --run-id minimal_example \
  --workspace /tmp/atomic-agent-minimal-example/workspace \
  --event-stream /tmp/atomic-agent-minimal-example/events/events.jsonl \
  --artifact-root /tmp/atomic-agent-minimal-example/artifacts \
  --result /tmp/atomic-agent-minimal-example/result.json
```

Expected stdout:

```json
{"artifact_root": "/tmp/atomic-agent-minimal-example/artifacts", "event_stream_path": "/tmp/atomic-agent-minimal-example/events/events.jsonl", "result_path": "/tmp/atomic-agent-minimal-example/result.json", "status": "completed", "workspace_output_path": "/tmp/atomic-agent-minimal-example/workspace/work/output.txt"}
```

Expected exit code:

```text
0
```

- [ ] **Step 2: Inspect the result JSON**

Run:

```bash
python - <<'PY'
import json
from pathlib import Path
result = json.loads(Path('/tmp/atomic-agent-minimal-example/result.json').read_text(encoding='utf-8'))
print(result['status'])
print(result['summary'])
print(result['event_stream_ref'])
print([attempt['tool'] for attempt in result['tool_attempts']])
print([mutation['path'] for mutation in result['workspace_mutations']])
PY
```

Expected:

```text
completed
Created fixed output through a controlled fake provider loop.
artifact://minimal_example/events.jsonl
['write_file', 'run_command', 'apply_patch', 'run_command']
['work/output.txt', 'work/output.txt']
```

- [ ] **Step 3: Inspect event stream command evidence**

Run:

```bash
python - <<'PY'
import json
from pathlib import Path
events = [json.loads(line) for line in Path('/tmp/atomic-agent-minimal-example/events/events.jsonl').read_text(encoding='utf-8').splitlines()]
print(events[0]['type'])
print(events[-2]['type'])
print(events[-1]['type'])
print([event['payload']['exit_code'] for event in events if event['type'] == 'command.completed'])
print(sum(1 for event in events if event['type'] == 'workspace.mutation.recorded'))
PY
```

Expected:

```text
run.started
result.submitted
run.completed
[3, 0]
2
```

- [ ] **Step 4: Inspect workspace output and artifact directories**

Run:

```bash
python - <<'PY'
from pathlib import Path
root = Path('/tmp/atomic-agent-minimal-example')
print((root / 'workspace' / 'work' / 'output.txt').read_text(encoding='utf-8'))
for relative in [
    'artifacts/provider/turn_000001.txt',
    'artifacts/observations/tool_attempt_000002.json',
    'artifacts/diffs/tool_attempt_000003.diff',
    'artifacts/commands/tool_attempt_000004.stdout.txt',
    'artifacts/results/step-0005.json',
]:
    print(relative, (root / relative).exists())
PY
```

Expected:

```text
fixed
artifacts/provider/turn_000001.txt True
artifacts/observations/tool_attempt_000002.json True
artifacts/diffs/tool_attempt_000003.diff True
artifacts/commands/tool_attempt_000004.stdout.txt True
artifacts/results/step-0005.json True
```

Do not update README until all four manual checks match expected output.

---

### Task 4: Run focused and full verification before documentation completion

**Files:**

- Verify: all runtime and tests

- [ ] **Step 1: Run the new example tests**

Run:

```bash
python -m pytest tests/test_minimal_fake_loop_example.py -q
```

Expected:

```text
5 passed
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

- [ ] **Step 5: Run a no-fallback source scan**

Run:

```bash
python - <<'PY'
from pathlib import Path
needles = ('os.environ', 'getenv', 'dotenv', 'shell=True', 'allow_all', 'default_allow', "Path('.env')", 'Path(".env")', "'.env'", '".env"')
for path in Path('src/atomic_agent').rglob('*.py'):
    text = path.read_text(encoding='utf-8')
    for needle in needles:
        if needle in text:
            print(f'{path}: contains {needle}')
PY
```

Expected:

```text

```

No output means runtime source does not contain obvious hidden environment fallback, free shell, or default allow patterns. If output appears in executable runtime code, inspect and fix before claiming completion. Do not treat test-only `PYTHONPATH` setup as runtime configuration fallback.

- [ ] **Step 6: Check working tree scope before README/docs updates**

Run:

```bash
git status --short
```

Expected implementation-stage scope:

```text
 M docs/INDEX.md
 M docs/04-implementation-backlog/backlog.md
 M docs/04-implementation-plan/INDEX.md
 M docs/04-implementation-spec/INDEX.md
?? docs/04-implementation-plan/P1-003-fake-provider-loop-minimal-example-plan.md
?? docs/04-implementation-spec/P1-003-fake-provider-loop-minimal-example-spec.md
?? src/atomic_agent/examples/__init__.py
?? src/atomic_agent/examples/minimal_fake_loop.py
?? tests/test_minimal_fake_loop_example.py
```

If unrelated files appear, inspect them before continuing and do not include unrelated edits in P1-003.

---

### Task 5: Update README only after verified example success

**Files:**

- Modify: `README.md`

- [ ] **Step 1: Replace the stale minimal example section**

Replace README section `## 3. 如何运行最小示例` with:

```markdown
## 3. 如何运行最小示例

当前仓库提供一个 deterministic fake provider loop（确定性假模型供应商循环）作为 minimal example（最小示例）。它不证明真实模型能力；它用于证明 `AgentLoop`（智能体循环）会真实执行受控工具、记录 JSONL event stream（JSONL 事件流）、写入 artifact（产物），并输出 `AgentRunResult`（智能体运行结果）。

从仓库根目录运行：

```bash
rm -rf /tmp/atomic-agent-minimal-example
PYTHONPATH=src python -m atomic_agent.examples.minimal_fake_loop \
  --run-id minimal_example \
  --workspace /tmp/atomic-agent-minimal-example/workspace \
  --event-stream /tmp/atomic-agent-minimal-example/events/events.jsonl \
  --artifact-root /tmp/atomic-agent-minimal-example/artifacts \
  --result /tmp/atomic-agent-minimal-example/result.json
```

成功时 stdout（标准输出）是 JSON：

```json
{"artifact_root": "/tmp/atomic-agent-minimal-example/artifacts", "event_stream_path": "/tmp/atomic-agent-minimal-example/events/events.jsonl", "result_path": "/tmp/atomic-agent-minimal-example/result.json", "status": "completed", "workspace_output_path": "/tmp/atomic-agent-minimal-example/workspace/work/output.txt"}
```

该示例的真实执行路径是：

1. fake provider（假模型供应商）请求 `write_file`（写文件），写入 `work/output.txt = draft`。
2. fake provider 请求 `run_command`（运行声明命令）执行 `check-output`，命令真实返回 exit code `3`。
3. command result（命令结果）作为 observation（观察结果）进入下一轮。
4. fake provider 请求 `apply_patch`（应用补丁），将 `draft` 修复为 `fixed`。
5. fake provider 再次请求 `run_command`，命令真实返回 exit code `0`。
6. fake provider 请求 `submit_result`（提交结果），runtime 写出 `AgentRunResult`（智能体运行结果）。

可检查的输出包括：

- `/tmp/atomic-agent-minimal-example/result.json`：结构化 `AgentRunResult`。
- `/tmp/atomic-agent-minimal-example/events/events.jsonl`：JSONL event stream（JSONL 事件流）。
- `/tmp/atomic-agent-minimal-example/artifacts/`：provider output（模型输出）、observation（观察结果）、diff（差异）、command stdout/stderr（命令输出）和 result artifact（结果产物）。
- `/tmp/atomic-agent-minimal-example/workspace/work/output.txt`：最终内容为 `fixed`。

该示例仍必须满足：真实执行、真实退出码、真实事件输出；不得以静态文本、模拟结果或 silent fallback（静默降级）伪装成功。
```

- [ ] **Step 2: Re-run README command exactly as documented**

Run:

```bash
rm -rf /tmp/atomic-agent-minimal-example
PYTHONPATH=src python -m atomic_agent.examples.minimal_fake_loop \
  --run-id minimal_example \
  --workspace /tmp/atomic-agent-minimal-example/workspace \
  --event-stream /tmp/atomic-agent-minimal-example/events/events.jsonl \
  --artifact-root /tmp/atomic-agent-minimal-example/artifacts \
  --result /tmp/atomic-agent-minimal-example/result.json
```

Expected: same JSON stdout as documented and exit code `0`.

---

### Task 6: Update P1-003 docs status and indexes after implementation passes

**Files:**

- Modify: `docs/04-implementation-backlog/backlog.md`
- Modify: `docs/04-implementation-spec/P1-003-fake-provider-loop-minimal-example-spec.md`
- Modify: `docs/04-implementation-plan/P1-003-fake-provider-loop-minimal-example-plan.md`
- Modify: `docs/04-implementation-spec/INDEX.md`
- Modify: `docs/04-implementation-plan/INDEX.md`
- Modify if active pointers change: `docs/INDEX.md`

- [ ] **Step 1: Mark P1-003 completed only after tests and README command pass**

Change `docs/04-implementation-backlog/backlog.md` P1-003 row from:

```markdown
| P1-003 | 固化 fake provider loop acceptance（假模型供应商循环验收）并建立真实 minimal example（最小示例）文档路径 | pending | `P1-003-fake-provider-loop-minimal-example-spec.md`, `testing-strategy.md`, `mvp-acceptance.md`, `README.md` |
```

To:

```markdown
| P1-003 | 固化 fake provider loop acceptance（假模型供应商循环验收）并建立真实 minimal example（最小示例）文档路径 | completed | `P1-003-fake-provider-loop-minimal-example-spec.md`, `testing-strategy.md`, `mvp-acceptance.md`, `README.md` |
```

- [ ] **Step 2: Mark spec implemented**

Change `docs/04-implementation-spec/P1-003-fake-provider-loop-minimal-example-spec.md` from:

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

Change `docs/04-implementation-plan/P1-003-fake-provider-loop-minimal-example-plan.md` from:

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
| `P1-003-fake-provider-loop-minimal-example-spec.md` | draft | 定义 P1-003 fake provider loop acceptance（假模型供应商循环验收）和 minimal example（最小示例）的输入、输出、事件、产物和无兜底要求 | 实现 P1-003 前 |
```

Add this completed row:

```markdown
| `P1-003-fake-provider-loop-minimal-example-spec.md` | 2026-06-06 | 已实现 P1-003 fake provider loop acceptance（假模型供应商循环验收）和 minimal example（最小示例），保留为示例验收规格记录 |
```

- [ ] **Step 5: Move plan index entry to completed / archived**

Remove this active row from `docs/04-implementation-plan/INDEX.md`:

```markdown
| `P1-003-fake-provider-loop-minimal-example-plan.md` | draft | 实施 P1-003 fake provider loop acceptance（假模型供应商循环验收）和 minimal example（最小示例）的 TDD 计划 | 执行 P1-003 时 |
```

Add this completed row:

```markdown
| `P1-003-fake-provider-loop-minimal-example-plan.md` | 2026-06-06 | 已实施 P1-003 fake provider loop acceptance（假模型供应商循环验收）和 minimal example（最小示例），保留为 TDD 实施记录 |
```

- [ ] **Step 6: Remove P1-003 draft pointers from global active documents after completion**

Remove P1-003 spec and plan draft rows from `docs/INDEX.md` Current Active Documents（当前活跃文档指针） after they move to completed sections in their subdirectory indexes.

---

### Task 7: Final verification and completion report

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

- [ ] **Step 3: Run README minimal example command one final time**

Run:

```bash
rm -rf /tmp/atomic-agent-minimal-example
PYTHONPATH=src python -m atomic_agent.examples.minimal_fake_loop \
  --run-id minimal_example \
  --workspace /tmp/atomic-agent-minimal-example/workspace \
  --event-stream /tmp/atomic-agent-minimal-example/events/events.jsonl \
  --artifact-root /tmp/atomic-agent-minimal-example/artifacts \
  --result /tmp/atomic-agent-minimal-example/result.json
```

Expected: documented JSON stdout and exit code `0`.

- [ ] **Step 4: Check working tree scope**

Run:

```bash
git status --short
```

Expected final scope:

```text
 M README.md
 M docs/04-implementation-backlog/backlog.md
 M docs/04-implementation-plan/INDEX.md
 M docs/04-implementation-spec/INDEX.md
?? docs/04-implementation-plan/P1-003-fake-provider-loop-minimal-example-plan.md
?? docs/04-implementation-spec/P1-003-fake-provider-loop-minimal-example-spec.md
?? src/atomic_agent/examples/__init__.py
?? src/atomic_agent/examples/minimal_fake_loop.py
?? tests/test_minimal_fake_loop_example.py
```

`docs/INDEX.md` may be absent from the final diff if draft active pointers were added during planning and then removed after completion, leaving the global index identical to baseline.

If additional files appear, inspect them and explain before claiming completion.

---

## Self-Review Checklist

Before implementation is considered ready for user review:

- [ ] Spec coverage: Every requirement in `docs/04-implementation-spec/P1-003-fake-provider-loop-minimal-example-spec.md` is covered by a task, test, README update, verification command, or explicit out-of-scope statement.
- [ ] Placeholder scan: This plan contains no placeholder markers, no vague “add tests” step, no mock success path, and no silent fallback.
- [ ] Type consistency: `ScriptedProvider`, `AgentInvocation`, `AgentRunResult`, `AgentLoop`, `CommandPolicy`, `CommandSpec`, `EventRecorder`, `ArtifactWriter`, `tool.attempt.completed`, `workspace.mutation.recorded`, and `command.completed` names match existing code and contracts.
- [ ] Scope check: No real provider, Boardroom adapter, new runtime, arbitrary shell, `.env` fallback, network change, or unreviewed architecture decision is included.
- [ ] Fail-closed check: Existing result path, non-empty artifact root, existing workspace output, missing command success, runtime failed result, and unsupported overwrite cases do not produce misleading success.
- [ ] Evidence check: Successful example writes `AgentRunResult`, JSONL events, provider artifacts, observation artifacts, diff artifacts, command stdout/stderr artifacts, result artifact, and final workspace output.
- [ ] Verification check: subprocess tests, AgentLoop tests, permission negative gate, full suite, no-fallback scan, and README command pass before any completion claim.

## Self-Review Result

- Spec coverage（规格覆盖）：计划覆盖 P1-003 spec（规格）中的 CLI contract（命令行契约）、example scenario（示例场景）、输出证据、文档要求、安全无兜底规则和验收标准。
- Placeholder scan（占位符扫描）：未使用占位式标记、空泛“补充测试”或未定义步骤；新增测试和实现文件均提供完整代码。
- Type consistency（类型一致性）：计划中的类名、函数名、事件名、文件名、命令和状态值与现有代码及新规格保持一致。
- Scope check（范围检查）：未纳入 P1-004 Boardroom adapter、真实 provider、网络扩展、权限引擎、长期配置系统或任意 shell。
- No-fallback check（无兜底检查）：计划明确要求显式 CLI 参数、显式 AgentInvocation、声明命令、无环境配置补齐、不覆盖用户文件、失败不伪装成功。
