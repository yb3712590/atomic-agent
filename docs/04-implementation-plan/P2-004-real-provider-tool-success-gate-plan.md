# P2-004 Real Provider Tool Success Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a default-disabled success-only real provider tool gate that verifies an OpenAI-compatible provider can autonomously choose and complete atomic-agent's basic tool actions in independent small tasks.

**Architecture:** Keep P2-002 fail-closed semantics unchanged. Add a separate pytest integration module with explicit test functions backed by a shared `RealProviderToolCase` runner that constructs `AgentInvocation`, tools, command policy, event recorder, artifact writer, and evidence assertions per case.

**Tech Stack:** Python 3.11+, pytest, official OpenAI Python SDK via existing `OpenAICompatibleProviderAdapter`, existing `AgentLoop`, `FilesystemTools`, `CommandTools`, `EventRecorder`, `ArtifactWriter`, `verify_event_stream`, and `build_evidence_summary`.

---

## Current Context

P2-002 already implements the real provider minimal integration gate（真实供应商最小集成门禁）. It allows Outcome C（供应商响应失败关闭） as a valid gate pass, so it proves auditable fail-closed semantics but not provider success. P2-004 adds a stricter, separate success gate（成功门禁）. It must not change P2-002 behavior.

The provider config may reuse the local ignored file `.env.real-provider-test-p2-002-task7`, but tracked files must only document placeholder values.

---

## File Structure

### Create

- `tests/test_real_provider_tool_success.py`  
  Success-only real provider integration tests（成功型真实供应商集成测试）. Contains shared runner helpers plus explicit per-tool test cases.

### Modify

- `pyproject.toml`  
  Add `real_provider_tool_success` pytest marker.

- `docs/05-testing/testing-strategy.md`  
  Document success-only gate, enable flag, reuse of P2-002 Task 7 provider config, default skip behavior, and success-only semantics.

- `docs/04-implementation-backlog/backlog.md`  
  Add P2-004 as pending before implementation; mark completed after verification.

- `docs/04-implementation-spec/INDEX.md`  
  Add P2-004 spec as active draft before implementation; archive after completion.

- `docs/04-implementation-plan/INDEX.md`  
  Add P2-004 plan as active draft before implementation; archive after completion.

- `docs/INDEX.md`  
  Add global active document pointers while P2-004 is being implemented; remove after completion.

---

## Task 1: Register P2-004 Metadata and Index Entries

**Files:**

- Modify: `pyproject.toml`
- Modify: `docs/04-implementation-backlog/backlog.md`
- Modify: `docs/04-implementation-spec/INDEX.md`
- Modify: `docs/04-implementation-plan/INDEX.md`
- Modify: `docs/INDEX.md`

### Step 1: Verify metadata is absent

Run:

```bash
python - <<'PY'
from pathlib import Path
text = Path('pyproject.toml').read_text(encoding='utf-8')
assert 'real_provider_tool_success:' in text
PY
```

Expected before implementation:

- FAIL with `AssertionError`.

### Step 2: Add pytest marker

Edit `pyproject.toml` marker list to include:

```toml
"real_provider_tool_success: success-only OpenAI-compatible real provider tool integration tests; skipped unless ATOMIC_AGENT_RUN_REAL_PROVIDER_TOOL_SUCCESS=1",
```

Keep the existing `real_provider` marker unchanged.

### Step 3: Add backlog entry

In `docs/04-implementation-backlog/backlog.md`, add P2-004 after P2-003 or in the P2 table with status `pending` before implementation:

```markdown
| P2-004 | 建立 real provider tool success gate（真实供应商工具成功门禁） | pending | `P2-004-real-provider-tool-success-gate-spec.md`, `testing-strategy.md`, `agent-action-protocol.md`, `mvp-acceptance.md`, `roadmap.md` |
```

### Step 4: Add active spec / plan pointers

In `docs/04-implementation-spec/INDEX.md`, add to `Current Active Documents`:

```markdown
| `P2-004-real-provider-tool-success-gate-spec.md` | draft | 定义 P2-004 real provider tool success gate（真实供应商工具成功门禁）的成功型集成测试范围和验收标准 | 实施 P2-004 前 |
```

In `docs/04-implementation-plan/INDEX.md`, add to `Current Active Documents`:

```markdown
| `P2-004-real-provider-tool-success-gate-plan.md` | draft | 定义 P2-004 real provider tool success gate（真实供应商工具成功门禁）的 TDD 实施步骤 | 执行 P2-004 前 |
```

In `docs/INDEX.md`, add corresponding P2 active pointers.

### Step 5: Verify metadata

Run:

```bash
python - <<'PY'
from pathlib import Path
text = Path('pyproject.toml').read_text(encoding='utf-8')
assert 'real_provider_tool_success:' in text
for path in [
    'docs/04-implementation-backlog/backlog.md',
    'docs/04-implementation-spec/INDEX.md',
    'docs/04-implementation-plan/INDEX.md',
    'docs/INDEX.md',
]:
    assert 'P2-004-real-provider-tool-success-gate' in Path(path).read_text(encoding='utf-8')
PY
```

Expected:

- PASS with no output.

---

## Task 2: Write Failing Success Gate Tests

**Files:**

- Create: `tests/test_real_provider_tool_success.py`

### Step 1: Create the test module skeleton

Create `tests/test_real_provider_tool_success.py` with:

```python
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import sys
import time
from typing import Any, Callable

import pytest

from atomic_agent.agent_loop import AgentLoop, AgentLoopConfig, AgentLoopDependencies
from atomic_agent.artifacts import ArtifactWriter, ArtifactWriterConfig
from atomic_agent.command_tools import CommandPolicy, CommandSpec, CommandToolConfig, CommandTools
from atomic_agent.evidence import build_evidence_summary, verify_event_stream
from atomic_agent.event_recorder import EventRecorder, EventRecorderConfig
from atomic_agent.filesystem_tools import FilesystemToolConfig, FilesystemTools
from atomic_agent.models import AgentInvocation, AgentRunResult
from atomic_agent.path_guard import WorkspacePathGuard
from atomic_agent.providers.openai_compatible import OpenAICompatibleProviderAdapter, OpenAICompatibleProviderOptions


PYTHON = Path(sys.executable).resolve()
REQUIRED_ENV = (
    'ATOMIC_AGENT_REAL_PROVIDER_BASE_URL',
    'ATOMIC_AGENT_REAL_PROVIDER_API_KEY',
    'ATOMIC_AGENT_REAL_PROVIDER_MODEL',
)


@dataclass(frozen=True)
class RealProviderToolCase:
    name: str
    task: str
    enabled_tools: tuple[str, ...]
    required_tool: str | None
    expected_produced_paths: tuple[str, ...]
    setup_workspace: Callable[[Path], None]
    build_command_policy: Callable[[WorkspacePathGuard], CommandTools | None]
    assert_workspace: Callable[[Path], None]
    assert_summary: Callable[[str], None]
    required_event_types: tuple[str, ...]
```

Then add helper functions and explicit tests in later steps.

### Step 2: Implement default skip helper in the test file

Add:

```python
def require_real_provider_tool_success_enabled():
    if os.environ.get('ATOMIC_AGENT_RUN_REAL_PROVIDER_TOOL_SUCCESS') != '1':
        pytest.skip('set ATOMIC_AGENT_RUN_REAL_PROVIDER_TOOL_SUCCESS=1 to run real provider tool success gate')
    missing = [name for name in REQUIRED_ENV if not os.environ.get(name)]
    if missing:
        pytest.fail('missing required real provider success test configuration: ' + ', '.join(missing))
```

### Step 3: Add explicit test placeholders that call missing helper functions

Add explicit tests for all six cases:

```python
@pytest.mark.real_provider_tool_success
def test_real_provider_success_write_file(tmp_path):
    require_real_provider_tool_success_enabled()
    run_and_assert_case(write_file_case(), tmp_path)

@pytest.mark.real_provider_tool_success
def test_real_provider_success_read_file(tmp_path):
    require_real_provider_tool_success_enabled()
    run_and_assert_case(read_file_case(), tmp_path)

@pytest.mark.real_provider_tool_success
def test_real_provider_success_list_files(tmp_path):
    require_real_provider_tool_success_enabled()
    run_and_assert_case(list_files_case(), tmp_path)

@pytest.mark.real_provider_tool_success
def test_real_provider_success_apply_patch(tmp_path):
    require_real_provider_tool_success_enabled()
    run_and_assert_case(apply_patch_case(), tmp_path)

@pytest.mark.real_provider_tool_success
def test_real_provider_success_run_command(tmp_path):
    require_real_provider_tool_success_enabled()
    run_and_assert_case(run_command_case(), tmp_path)

@pytest.mark.real_provider_tool_success
def test_real_provider_success_submit_result(tmp_path):
    require_real_provider_tool_success_enabled()
    run_and_assert_case(submit_result_case(), tmp_path)
```

### Step 4: Verify default skip behavior

Run:

```bash
python -m pytest tests/test_real_provider_tool_success.py -q
```

Expected before helper implementation is complete:

- All six tests SKIP if `ATOMIC_AGENT_RUN_REAL_PROVIDER_TOOL_SUCCESS` is not set.
- No provider network call.

### Step 5: Verify enabled tests fail before implementation

Run only if provider env is available:

```bash
set -a
source .env.real-provider-test-p2-002-task7
set +a
ATOMIC_AGENT_RUN_REAL_PROVIDER_TOOL_SUCCESS=1 \
python -m pytest tests/test_real_provider_tool_success.py -m real_provider_tool_success -q
```

Expected before implementation:

- FAIL with `NameError` for missing case builders or runner.

---

## Task 3: Implement Shared Runner and Provider Config Helpers

**Files:**

- Modify: `tests/test_real_provider_tool_success.py`

### Step 1: Add provider config helpers

Add helpers to parse env values without logging secrets:

```python
def env_value(name, default):
    return os.environ.get(name, default)


def env_int(name, default):
    return int(env_value(name, default))


def env_float_or_none(name, default):
    raw = os.environ.get(name, default)
    if raw in (None, ''):
        return None
    return float(raw)


def provider_options():
    return OpenAICompatibleProviderOptions(
        base_url=os.environ['ATOMIC_AGENT_REAL_PROVIDER_BASE_URL'],
        api_key=os.environ['ATOMIC_AGENT_REAL_PROVIDER_API_KEY'],
        model=os.environ['ATOMIC_AGENT_REAL_PROVIDER_MODEL'],
        context_window_tokens=env_int('ATOMIC_AGENT_REAL_PROVIDER_CONTEXT_WINDOW_TOKENS', '400000'),
        max_output_tokens=env_int('ATOMIC_AGENT_REAL_PROVIDER_MAX_OUTPUT_TOKENS', '128000'),
        stream_idle_timeout_seconds=float(env_value('ATOMIC_AGENT_REAL_PROVIDER_STREAM_IDLE_TIMEOUT_SECONDS', '30')),
        total_timeout_seconds=float(env_value('ATOMIC_AGENT_REAL_PROVIDER_TOTAL_TIMEOUT_SECONDS', '3600')),
        temperature=env_float_or_none('ATOMIC_AGENT_REAL_PROVIDER_TEMPERATURE', ''),
        provider_label=os.environ.get('ATOMIC_AGENT_REAL_PROVIDER_LABEL') or None,
    )
```

### Step 2: Add runner setup helpers

Add:

```python
def utc_timestamp():
    return datetime.now(UTC).isoformat().replace('+00:00', 'Z')


def make_filesystem_tools(workspace):
    guard = WorkspacePathGuard(workspace, allowed_write_set=['work/'])
    return guard, FilesystemTools(
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
```

### Step 3: Add invocation builder

Add a function that constructs a complete `AgentInvocation`:

```python
def build_invocation(case, workspace, options):
    return AgentInvocation(
        invocation_id=f'inv_{case.name}',
        task=case.task,
        workspace_root=str(workspace),
        allowed_write_set=['work/'],
        tools=list(case.enabled_tools),
        permission_policy={'policy_ref': f'policy://tests/real-provider-tool-success/{case.name}'},
        provider_profile={
            'provider': 'openai-compatible',
            'provider_label': options.provider_label,
            'model': options.model,
            'context_window_tokens': options.context_window_tokens,
            'max_output_tokens': options.max_output_tokens,
            'stream_idle_timeout_seconds': options.stream_idle_timeout_seconds,
            'total_timeout_seconds': options.total_timeout_seconds,
        },
        budgets={
            'max_steps': env_int('ATOMIC_AGENT_REAL_PROVIDER_MAX_STEPS', '100'),
            'max_parse_failures': 1,
            'max_observation_chars': 20000,
            'max_wall_seconds': options.total_timeout_seconds * env_int('ATOMIC_AGENT_REAL_PROVIDER_MAX_STEPS', '100') + 5.0,
        },
        output_requirements={'summary': True, 'event_stream': True, 'artifacts': True},
        metadata={'test': 'real_provider_tool_success', 'case': case.name},
    )
```

### Step 4: Add shared `run_and_assert_case`

Add:

```python
def run_and_assert_case(case, tmp_path):
    base = tmp_path / case.name
    workspace = base / 'workspace'
    event_stream = base / 'events' / 'events.jsonl'
    artifact_root = base / 'artifacts'
    workspace.mkdir(parents=True)
    event_stream.parent.mkdir(parents=True)
    artifact_root.mkdir(parents=True)
    (workspace / 'work').mkdir()
    case.setup_workspace(workspace)

    options = provider_options()
    guard, filesystem_tools = make_filesystem_tools(workspace)
    command_tools = case.build_command_policy(guard)
    recorder = EventRecorder(
        run_id=f'real_provider_tool_success_{case.name}',
        config=EventRecorderConfig(
            event_stream_path=event_stream,
            event_stream_ref=f'artifact://real_provider_tool_success/{case.name}/events.jsonl',
        ),
        clock=utc_timestamp,
    )
    artifact_writer = ArtifactWriter(
        ArtifactWriterConfig(
            artifact_root=artifact_root,
            artifact_ref_prefix=f'artifact://real_provider_tool_success/{case.name}',
        )
    )
    loop = AgentLoop(
        AgentLoopConfig(run_id=f'real_provider_tool_success_{case.name}'),
        AgentLoopDependencies(
            provider=OpenAICompatibleProviderAdapter(options=options),
            filesystem_tools=filesystem_tools,
            command_tools=command_tools,
            event_recorder=recorder,
            artifact_writer=artifact_writer,
            runtime_clock=time.monotonic,
        ),
    )

    result = loop.run(build_invocation(case, workspace, options))
    assert result.status.value == 'completed', result.model_dump(mode='json')
    integrity = verify_event_stream(event_stream, expected_events_hash=result.events_hash)
    assert integrity['ok'] is True, integrity
    events = [json.loads(line) for line in event_stream.read_text(encoding='utf-8').splitlines()]
    event_types = [event['type'] for event in events]
    assert event_types[-1] == 'run.completed'
    for event_type in case.required_event_types:
        assert event_type in event_types
    if case.required_tool is not None:
        completed_tools = [event['payload']['tool'] for event in events if event['type'] == 'tool.attempt.completed']
        assert case.required_tool in completed_tools
    summary = build_evidence_summary(result, event_stream)
    assert summary['event_stream']['integrity']['ok'] is True
    for path in case.expected_produced_paths:
        lineage = [item for item in summary['source_inventory_lineage'] if item['path'] == path]
        assert lineage and lineage[0]['lineage_status'] == 'traceable'
    case.assert_workspace(workspace)
    case.assert_summary(result.summary)
    return result, events, summary, workspace
```

### Step 5: Run default skip test again

Run:

```bash
python -m pytest tests/test_real_provider_tool_success.py -q
```

Expected:

- SKIPPED by default.

---

## Task 4: Implement Tool Case Builders

**Files:**

- Modify: `tests/test_real_provider_tool_success.py`

### Step 1: Add no-op helpers

Add:

```python
def noop_workspace(workspace):
    return None


def no_command_policy(guard):
    return None


def assert_noop_workspace(workspace):
    return None


def assert_summary_non_empty(summary):
    assert isinstance(summary, str) and summary
```

### Step 2: Add `write_file_case`

Add:

```python
def write_file_case():
    return RealProviderToolCase(
        name='write_file',
        task=(
            'You must complete this task by using write_file before submit_result. '
            'Create work/write-success.txt with content containing exactly the phrase real provider write success. '
            'Do not submit_result until after the write_file observation confirms success. '
            'Return exactly one AgentAction JSON object per turn.'
        ),
        enabled_tools=('write_file', 'submit_result'),
        required_tool='write_file',
        expected_produced_paths=('work/write-success.txt',),
        setup_workspace=noop_workspace,
        build_command_policy=no_command_policy,
        assert_workspace=lambda workspace: assert_file_contains(workspace / 'work' / 'write-success.txt', 'real provider write success'),
        assert_summary=assert_summary_non_empty,
        required_event_types=('workspace.mutation.recorded', 'result.submitted'),
    )
```

### Step 3: Add `read_file_case`

Add:

```python
def setup_read_workspace(workspace):
    (workspace / 'work' / 'read-input.txt').write_text('read fixture token', encoding='utf-8')


def assert_summary_mentions_read_token(summary):
    assert 'read fixture token' in summary


def read_file_case():
    return RealProviderToolCase(
        name='read_file',
        task=(
            'You must complete this task by using read_file before submit_result. '
            'Read work/read-input.txt and include the exact phrase read fixture token in submit_result input.summary. '
            'Do not submit_result until after the read_file observation confirms success. '
            'Return exactly one AgentAction JSON object per turn.'
        ),
        enabled_tools=('read_file', 'submit_result'),
        required_tool='read_file',
        expected_produced_paths=(),
        setup_workspace=setup_read_workspace,
        build_command_policy=no_command_policy,
        assert_workspace=lambda workspace: assert_file_contains(workspace / 'work' / 'read-input.txt', 'read fixture token'),
        assert_summary=assert_summary_mentions_read_token,
        required_event_types=('tool.attempt.completed', 'result.submitted'),
    )
```

### Step 4: Add `list_files_case`

Add setup and assertions for `work/list-a.txt` and `work/nested/list-b.txt`.

### Step 5: Add `apply_patch_case`

Add setup and assertion that `work/patch-target.txt` changes from `before patch` to `after patch`.

### Step 6: Add `run_command_case`

Add command policy:

```python
def build_check_command_policy(guard):
    return CommandTools(
        guard,
        CommandPolicy(
            {
                'check-command-input': CommandSpec(
                    argv=(
                        str(PYTHON),
                        '-c',
                        "from pathlib import Path; import sys; content = Path('work/command-input.txt').read_text(encoding='utf-8'); sys.exit(0 if content == 'command ok' else 3)",
                    )
                )
            }
        ),
        CommandToolConfig(default_timeout_seconds=2.0, max_timeout_seconds=5.0, max_output_bytes=4096),
    )
```

The task must require provider to use `run_command` with `command_id` exactly `check-command-input`.

### Step 7: Add `submit_result_case`

This case enables only `submit_result`; it requires no target tool and no `tool.attempt.started`.

### Step 8: Run enabled success gate if provider env is available

Run:

```bash
set -a
source .env.real-provider-test-p2-002-task7
set +a
ATOMIC_AGENT_RUN_REAL_PROVIDER_TOOL_SUCCESS=1 \
python -m pytest tests/test_real_provider_tool_success.py -m real_provider_tool_success -q
```

Expected:

- All six tests PASS.
- If any provider output is empty, invalid JSON, skips required tool, or fails a tool, the relevant test FAILS.

---

## Task 5: Harden Failure Diagnostics and Secret Safety

**Files:**

- Modify: `tests/test_real_provider_tool_success.py`

### Step 1: Add failure diagnostic helper

Add helper that reports non-secret paths and event types on failure, but never prints env values:

```python
def failure_context(result, event_stream):
    context = {'result': result.model_dump(mode='json')}
    if event_stream.exists():
        events = [json.loads(line) for line in event_stream.read_text(encoding='utf-8').splitlines()]
        context['event_types'] = [event['type'] for event in events]
    return context
```

Use it in assertions like:

```python
assert result.status.value == 'completed', failure_context(result, event_stream)
```

### Step 2: Add tracked-file secret scan command to plan verification

Do not add the secret scan as a pytest test because the real key is local-only. Use it as a manual verification command:

```bash
if grep -R --exclude='.env.real-provider-test-p2-002-task7' --exclude-dir='.git' --exclude-dir='.pytest_cache' --exclude-dir='__pycache__' -q '<real-api-key>' .; then
  printf 'secret_found_in_tracked_search\n'
else
  printf 'secret_not_found_in_tracked_search\n'
fi
```

The real key must not be written into this plan; the command shape is documented only for the implementer to run locally with their own secret value.

### Step 3: Run full tests

Run:

```bash
python -m pytest -q
```

Expected:

- PASS.
- The success gate is skipped unless explicitly enabled.

---

## Task 6: Documentation Completion After Verification

**Files:**

- Modify: `docs/05-testing/testing-strategy.md`
- Modify: `docs/04-implementation-backlog/backlog.md`
- Modify: `docs/04-implementation-spec/INDEX.md`
- Modify: `docs/04-implementation-plan/INDEX.md`
- Modify: `docs/INDEX.md`

### Preconditions

Only do this after:

```bash
python -m pytest -q
python -m pytest tests/test_real_provider_tool_success.py -q
```

and, with valid provider config:

```bash
set -a
source .env.real-provider-test-p2-002-task7
set +a
ATOMIC_AGENT_RUN_REAL_PROVIDER_TOOL_SUCCESS=1 \
python -m pytest tests/test_real_provider_tool_success.py -m real_provider_tool_success -q
```

### Step 1: Update testing strategy

Add a section documenting:

- `real_provider_tool_success` marker
- `ATOMIC_AGENT_RUN_REAL_PROVIDER_TOOL_SUCCESS=1`
- reuse of `.env.real-provider-test-p2-002-task7` provider config
- success-only semantics
- all six tool cases
- default skip behavior

### Step 2: Mark backlog completed

Change P2-004 status to completed:

```markdown
| P2-004 | 建立 real provider tool success gate（真实供应商工具成功门禁） | completed | `P2-004-real-provider-tool-success-gate-spec.md`, `testing-strategy.md`, `agent-action-protocol.md`, `mvp-acceptance.md`, `roadmap.md` |
```

### Step 3: Archive spec / plan pointers

Move P2-004 spec / plan out of current active documents into completed / archived rows in their subdirectory indexes with actual completion date.

### Step 4: Update global docs index

Remove P2-004 active draft pointers after completion.

---

## Task 7: Final Verification and Report

Run:

```bash
python -m pytest -q
python -m pytest tests/test_real_provider_tool_success.py -q
```

With valid provider config, run:

```bash
set -a
source .env.real-provider-test-p2-002-task7
set +a
ATOMIC_AGENT_RUN_REAL_PROVIDER_TOOL_SUCCESS=1 \
python -m pytest tests/test_real_provider_tool_success.py -m real_provider_tool_success -q
```

Run secret checks locally without printing secret values.

Final report must include:

- files created/modified
- default skip result
- explicit success gate result
- per-tool pass/fail summary
- whether any case failed due to provider response emptiness or invalid action
- statement that no commit was created unless explicitly requested

---

## Risks and Mitigations

1. **Provider autonomy reduces stability**  
   Tests must fail clearly if provider chooses wrong tool or skips required tool. Do not downgrade to guided two-turn without a spec update.

2. **Cost and runtime**  
   Six independent tests may perform many provider calls. The gate remains manual/nightly only.

3. **Direct submit_result shortcut**  
   For all cases except `submit_result`, the runner must require the target tool's successful event before accepting `run.completed`.

4. **Command policy safety**  
   `run_command` case must use declared `command_id` only and a fixed safe Python command. No free shell strings.

5. **Credential leakage**  
   Do not print env values, provider config, or real URL/key in tracked files or assertion messages.

---

## Self-Review

- **Coverage（覆盖）**：本计划 covers marker metadata, test harness, six independent success cases, failure diagnostics, docs, and verification.
- **No placeholders（无占位）**：每个 task has concrete files, commands, expected outcomes, and helper design.
- **Boundary（边界）**：P2-004 does not change P2-002 and does not introduce native tool calling, provider registry, or Boardroom governance changes.
- **TDD（测试驱动）**：Tasks require default skip red test, enabled failing tests before runner implementation, and explicit success gate verification.

---

## Execution Handoff

Do not implement before user review approves this spec and plan.

Recommended execution after approval:

1. Use `subagent-driven-development`（子智能体驱动开发） for implementation.
2. Keep all provider credentials local in ignored `.env.real-provider-test-p2-002-task7`.
3. Do not commit unless explicitly requested.
