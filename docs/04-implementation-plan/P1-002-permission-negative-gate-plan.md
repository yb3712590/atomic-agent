# Permission Negative Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement P1-002 `permission negative gate`（权限负向门禁） so atomic-agent（原子智能体） has one focused pytest gate proving fail-closed permission boundaries without adding duplicate runtime logic or hidden fallbacks.

**Architecture:** Reuse the existing AgentLoop（智能体循环）, action parser（动作解析器）, filesystem tools（文件系统工具）, command tools（命令工具）, web_fetch tools（网络获取工具）, EventRecorder（事件记录器）, and ArtifactWriter（产物写入器）. Add a pytest marker（测试标记） and a small number of missing AgentLoop capability tests（运行时能力测试） so the gate proves actual runtime behavior: denied actions do not execute tools, do not mutate workspace, do not issue network requests, and always end in auditable failed results.

**Tech Stack:** Python 3.11+, pytest marker（测试标记）, pytest parameter marks（参数化标记）, local temporary filesystem（临时文件系统）, local HTTP server（本地 HTTP 服务器）, existing atomic-agent runtime modules（现有原子智能体运行时模块）.

**Status:** implemented

---

## Scope

This plan implements P1-002 only.

In scope:

- Add `permission_negative` marker（权限负向标记） to `pyproject.toml`.
- Mark selected existing tests that already prove permission / fail-closed boundaries.
- Add focused AgentLoop capability tests for gaps not proven by existing tests.
- Add a concise testing strategy（测试策略） section documenting the gate command and coverage matrix.
- Add this spec and plan to implementation spec / plan indexes（实现规格 / 计划索引） as active draft documents.

Out of scope:

- No new permission engine（权限引擎）.
- No new runtime behavior unless the new gate exposes a real atomic-agent capability gap.
- No new action/tool types（动作 / 工具类型）.
- No README minimal example（最小示例） update.
- No Boardroom AgentRuntimePort adapter（Boardroom 智能体运行时端口适配器）.
- No broad marker over the whole test suite.
- No commit unless the user explicitly requests it.

## File Structure

- Modify: `pyproject.toml`
  - Declare `permission_negative` pytest marker.
- Modify: `tests/test_path_guard.py`
  - Mark selected path traversal（路径逃逸） and symlink escape（符号链接逃逸） guard tests.
- Modify: `tests/test_filesystem_tools.py`
  - Mark selected filesystem write deny（文件系统写入拒绝） tests.
- Modify: `tests/test_command_tools.py`
  - Mark selected undeclared command（未声明命令） and free shell string（自由 shell 字符串） tests.
- Modify: `tests/test_web_fetch_tools.py`
  - Mark selected network deny（网络拒绝） tests.
- Modify: `tests/test_action_parser.py`
  - Mark invalid JSON（无效 JSON）, unknown action（未知动作）, run_command shell string（运行命令字符串）, and invalid web_fetch（非法网络获取） parser tests.
- Modify: `tests/test_agent_loop.py`
  - Mark selected existing runtime fail-closed tests.
  - Add focused AgentLoop tests for path traversal, symlink escape, unknown action, and observation truncation capability gaps.
- Modify: `docs/05-testing/testing-strategy.md`
  - Document the gate command and coverage matrix.
- Modify: `docs/04-implementation-spec/INDEX.md`
  - Add active draft spec pointer for P1-002.
- Modify: `docs/04-implementation-plan/INDEX.md`
  - Add active draft plan pointer for P1-002.
- Modify after implementation passes: `docs/04-implementation-backlog/backlog.md`
  - Mark P1-002 completed only after gate and full tests pass.
- Modify after implementation passes: `docs/04-implementation-spec/P1-002-permission-negative-gate-spec.md`
  - Change status from `draft` to `implemented`.
- Modify after implementation passes: `docs/04-implementation-plan/P1-002-permission-negative-gate-plan.md`
  - Change status from `draft` to `implemented`.

---

### Task 1: Register the pytest marker

**Files:**

- Modify: `pyproject.toml`

- [ ] **Step 1: Add marker configuration**

Change `pyproject.toml` from:

```toml
[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

To:

```toml
[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
markers = [
  "permission_negative: fail-closed permission and security boundary tests",
]
```

- [ ] **Step 2: Verify pytest recognizes the marker**

Run:

```bash
python -m pytest --markers | grep permission_negative
```

Expected:

```text
@pytest.mark.permission_negative: fail-closed permission and security boundary tests
```

If `grep` is unavailable in the environment, run:

```bash
python -m pytest --markers
```

Expected: output contains the exact `permission_negative` marker description.

---

### Task 2: Mark existing low-level permission tests selectively

**Files:**

- Modify: `tests/test_path_guard.py`
- Modify: `tests/test_filesystem_tools.py`
- Modify: `tests/test_command_tools.py`
- Modify: `tests/test_web_fetch_tools.py`
- Modify: `tests/test_action_parser.py`

- [ ] **Step 1: Mark path guard boundary tests**

In `tests/test_path_guard.py`, add `@pytest.mark.permission_negative` immediately above these tests:

```python
@pytest.mark.permission_negative
@pytest.mark.parametrize("requested_path", ["../outside.txt", "docs/../outside.txt"])
def test_resolve_read_path_rejects_path_traversal(tmp_path, requested_path):
```

```python
@pytest.mark.permission_negative
def test_resolve_read_path_rejects_symlink_escape(tmp_path):
```

```python
@pytest.mark.permission_negative
def test_resolve_write_path_rejects_path_outside_allowed_write_set(tmp_path):
```

```python
@pytest.mark.permission_negative
def test_guard_rejects_allowed_write_set_symlink_escape(tmp_path):
```

- [ ] **Step 2: Mark filesystem tool boundary tests**

In `tests/test_filesystem_tools.py`, add `@pytest.mark.permission_negative` immediately above these tests:

```python
@pytest.mark.permission_negative
def test_list_files_rejects_path_escape(tmp_path):
```

```python
@pytest.mark.permission_negative
def test_write_file_rejects_path_outside_allowed_write_set(tmp_path):
```

```python
@pytest.mark.permission_negative
def test_apply_patch_rejects_path_outside_allowed_write_set(tmp_path):
```

```python
@pytest.mark.permission_negative
def test_write_file_rejects_symlink_escape_inside_allowed_directory(tmp_path):
```

- [ ] **Step 3: Mark command boundary tests**

In `tests/test_command_tools.py`, add `@pytest.mark.permission_negative` immediately above:

```python
@pytest.mark.permission_negative
def test_run_command_rejects_unknown_command_without_execution(tmp_path):
```

```python
@pytest.mark.permission_negative
def test_agent_action_still_rejects_run_command_shell_string():
```

For `test_command_policy_rejects_invalid_command_spec`, only mark the `allow_network=True` parameter case to avoid pulling unrelated config validation into the gate. Change the parameter list so that the final case is:

```python
        pytest.param(
            CommandSpec(argv=(str(PYTHON), "--version"), allow_network=True),
            marks=pytest.mark.permission_negative,
        ),
```

- [ ] **Step 4: Mark network boundary tests**

In `tests/test_web_fetch_tools.py`, add `@pytest.mark.permission_negative` above:

```python
@pytest.mark.permission_negative
@pytest.mark.parametrize(
    "url",
    [
        "",
        "not a url",
        "ftp://example.com/docs",
        "https:///docs",
        "https://user:pass@example.com/docs",
        "https://example.com/docs#fragment",
        "https://example.com:444/docs",
        "https://other.example.com/docs",
        "https://example.com/private",
        "http://example.com/docs",
    ],
)
def test_network_policy_denies_unmatched_or_invalid_url(url):
```

```python
@pytest.mark.permission_negative
def test_network_policy_empty_rules_denies_all():
```

```python
@pytest.mark.permission_negative
def test_fetch_url_denies_unallowed_url_without_request(local_http_server):
```

- [ ] **Step 5: Mark action parser boundary tests**

In `tests/test_action_parser.py`, add `@pytest.mark.permission_negative` above:

```python
@pytest.mark.permission_negative
def test_parse_agent_action_rejects_invalid_json():
```

```python
@pytest.mark.permission_negative
def test_parse_agent_action_rejects_unknown_action():
```

```python
@pytest.mark.permission_negative
@pytest.mark.parametrize("forbidden_key", ["command", "shell", "cmd"])
def test_parse_agent_action_rejects_run_command_shell_string(forbidden_key):
```

```python
@pytest.mark.permission_negative
@pytest.mark.parametrize("input_payload", ["{}", "{\"url\": \"\"}", "{\"url\": \"https://example.com\", \"method\": \"POST\"}"])
def test_parse_agent_action_rejects_invalid_web_fetch_input(input_payload):
```

- [ ] **Step 6: Run selected gate to verify marker collection works**

Run:

```bash
python -m pytest -m permission_negative --collect-only -q
```

Expected:

```text
<non-zero number> tests collected
```

The exact count may change as Task 3 adds runtime tests. Do not assert a fixed count in code or docs.

---

### Task 3: Add focused AgentLoop permission capability tests

**Files:**

- Modify: `tests/test_agent_loop.py`

These tests prove atomic-agent runtime（运行时） behavior, not just helper behavior. They are intentionally few and focused.

- [ ] **Step 1: Add helper for symlink creation inside AgentLoop tests**

At the top of `tests/test_agent_loop.py`, imports already include `Path` and `sys`; add `subprocess` if not present:

```python
import subprocess
```

Add this helper near existing local test helpers:

```python
def create_escaping_directory_link(link: Path, target: Path):
    try:
        link.symlink_to(target, target_is_directory=True)
        return
    except OSError as error:
        if sys.platform != "win32":
            pytest.skip(f"symlink creation is unavailable: {error}")

    subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            "New-Item",
            "-ItemType",
            "Junction",
            "-Path",
            str(link),
            "-Target",
            str(target),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )
```

- [ ] **Step 2: Add AgentLoop path traversal denial test**

Append to `tests/test_agent_loop.py`:

```python

@pytest.mark.permission_negative
def test_agent_loop_denies_path_traversal_write_without_tool_attempt(tmp_path):
    outside = tmp_path.parent / f"{tmp_path.name}-outside-write.txt"
    provider = ScriptedProvider([action("step-outside", "write_file", {"path": "../outside-write.txt", "content": "secret"})])
    loop, event_stream_path = make_loop(tmp_path, provider)

    result = loop.run(make_invocation(tmp_path))

    assert result.status == AgentRunStatus.FAILED
    assert result.failure_kind == "policy_denied"
    assert result.failed_action_ref == "step-outside"
    assert not outside.exists()
    event_types = [event["type"] for event in read_jsonl(event_stream_path)]
    assert event_types[-3:] == ["permission.decided", "action.rejected", "run.failed"]
    assert "tool.attempt.started" not in event_types
    assert "workspace.mutation.recorded" not in event_types
```

- [ ] **Step 3: Add AgentLoop symlink escape denial test**

Append to `tests/test_agent_loop.py`:

```python

@pytest.mark.permission_negative
def test_agent_loop_denies_symlink_escape_write_without_mutation(tmp_path):
    outside = tmp_path.parent / f"{tmp_path.name}-outside-symlink"
    outside.mkdir()
    work = tmp_path / "work"
    work.mkdir()
    create_escaping_directory_link(work / "link", outside)
    provider = ScriptedProvider([action("step-link", "write_file", {"path": "work/link/secret.txt", "content": "secret"})])
    loop, event_stream_path = make_loop(tmp_path, provider)

    result = loop.run(make_invocation(tmp_path))

    assert result.status == AgentRunStatus.FAILED
    assert result.failure_kind == "policy_denied"
    assert result.failed_action_ref == "step-link"
    assert not (outside / "secret.txt").exists()
    event_types = [event["type"] for event in read_jsonl(event_stream_path)]
    assert event_types[-3:] == ["permission.decided", "action.rejected", "run.failed"]
    assert "tool.attempt.started" not in event_types
    assert "workspace.mutation.recorded" not in event_types
```

- [ ] **Step 4: Add AgentLoop unknown action rejection test**

Append to `tests/test_agent_loop.py`:

```python

@pytest.mark.permission_negative
def test_agent_loop_rejects_unknown_action_and_fails_closed(tmp_path):
    provider = ScriptedProvider(
        [
            json.dumps(
                {
                    "action_id": "step-unknown",
                    "action": "free_shell",
                    "reason_summary": "Run an unsupported action.",
                    "input": {"command": "rm -rf ."},
                }
            ),
            json.dumps(
                {
                    "action_id": "step-unknown-again",
                    "action": "free_shell",
                    "reason_summary": "Run an unsupported action again.",
                    "input": {"command": "rm -rf ."},
                }
            ),
        ]
    )
    loop, event_stream_path = make_loop(tmp_path, provider)

    result = loop.run(make_invocation(tmp_path))

    assert result.status == AgentRunStatus.FAILED
    assert result.failure_kind == "action_parse_failed"
    assert result.failed_action_ref == "provider_turn_000002"
    event_types = [event["type"] for event in read_jsonl(event_stream_path)]
    assert event_types.count("action.rejected") == 2
    assert "tool.attempt.started" not in event_types
    assert event_types[-1] == "run.failed"
```

- [ ] **Step 5: Add observation truncation capability test**

Append to `tests/test_agent_loop.py`:

```python

@pytest.mark.permission_negative
def test_agent_loop_truncates_oversized_observation_without_losing_artifact(tmp_path):
    provider = ScriptedProvider(
        [
            action("step-write", "write_file", {"path": "work/output.txt", "content": "x" * 200}),
            action(
                "step-submit",
                "submit_result",
                {
                    "summary": "Created output.",
                    "produced_paths": ["work/output.txt"],
                    "evidence_refs": ["step-write"],
                },
            ),
        ]
    )
    loop, event_stream_path = make_loop(tmp_path, provider)
    invocation = make_invocation(
        tmp_path,
        budgets={
            "max_steps": 4,
            "max_parse_failures": 1,
            "max_observation_chars": 80,
            "max_wall_seconds": 30.0,
        },
    )

    result = loop.run(invocation)

    assert result.status == AgentRunStatus.COMPLETED
    assert len(provider.contexts) == 2
    observation = provider.contexts[1].observations[-1]
    assert observation["truncated"] is True
    assert len(observation["visible"]) == 80
    assert observation["artifact"]["artifact_ref"].endswith("observations/tool_attempt_000001.json")
    assert observation["artifact"]["truncated_in_observation"] is True
    assert any(event["type"] == "workspace.mutation.recorded" for event in read_jsonl(event_stream_path))
```

- [ ] **Step 6: Mark selected existing AgentLoop negative tests**

In `tests/test_agent_loop.py`, add `@pytest.mark.permission_negative` above these existing tests:

```python
@pytest.mark.permission_negative
def test_agent_loop_fails_closed_when_budget_fields_are_missing(tmp_path):
```

```python
@pytest.mark.permission_negative
@pytest.mark.parametrize(
    ("name", "provider_outputs", "invocation_kwargs", "failure_kind", "failed_action_ref", "expected_event"),
    [
        ...
    ],
)
def test_agent_loop_fails_closed_for_runtime_errors(...):
```

```python
@pytest.mark.permission_negative
def test_agent_loop_fails_closed_when_web_fetch_tools_are_not_configured(tmp_path):
```

```python
@pytest.mark.permission_negative
def test_agent_loop_denies_unallowed_web_fetch_without_tool_attempt(tmp_path, local_http_server):
```

```python
@pytest.mark.permission_negative
def test_agent_loop_fails_closed_when_max_wall_seconds_is_missing(tmp_path):
```

```python
@pytest.mark.permission_negative
def test_agent_loop_fails_closed_when_wall_time_exceeded_before_provider_turn(tmp_path):
```

```python
@pytest.mark.permission_negative
def test_agent_loop_preserves_invalid_json_retry_limit_with_wall_budget(tmp_path):
```

```python
@pytest.mark.permission_negative
def test_agent_loop_preserves_max_steps_failure_with_wall_budget(tmp_path):
```

- [ ] **Step 7: Run focused new AgentLoop tests**

Run:

```bash
python -m pytest \
  tests/test_agent_loop.py::test_agent_loop_denies_path_traversal_write_without_tool_attempt \
  tests/test_agent_loop.py::test_agent_loop_denies_symlink_escape_write_without_mutation \
  tests/test_agent_loop.py::test_agent_loop_rejects_unknown_action_and_fails_closed \
  tests/test_agent_loop.py::test_agent_loop_truncates_oversized_observation_without_losing_artifact \
  -q
```

Expected:

```text
4 passed
```

If any test fails because the runtime permits an unsafe action or misses required event facts, fix the atomic-agent runtime capability directly. Do not weaken these tests and do not add fallback behavior.

---

### Task 4: Verify the gate and full test suite

**Files:**

- Verify: all tests

- [ ] **Step 1: Run the permission negative gate**

Run:

```bash
python -m pytest -m permission_negative -q
```

Expected:

```text
<all selected tests passed>
```

No fixed test count is required; count may change as the suite evolves.

- [ ] **Step 2: Run the full suite**

Run:

```bash
python -m pytest -q
```

Expected:

```text
<all tests passed>
```

- [ ] **Step 3: Run a no-fallback source scan**

Run:

```bash
python - <<'PY'
from pathlib import Path
for path in Path('src/atomic_agent').rglob('*.py'):
    text = path.read_text(encoding='utf-8')
    for needle in ('os.environ', 'getenv', 'dotenv', '.env', 'allow_all', 'default_allow', 'shell=True'):
        if needle in text:
            print(f'{path}: contains {needle}')
PY
```

Expected:

```text

```

No output means the runtime source does not contain obvious hidden environment fallback, default allowlist, or free shell escape patterns. If output appears in executable source, inspect and fix before claiming completion.

- [ ] **Step 4: Check working tree scope**

Run:

```bash
git status --short
```

Expected implementation-stage scope:

```text
 M pyproject.toml
 M docs/05-testing/testing-strategy.md
 M docs/04-implementation-spec/INDEX.md
 M docs/04-implementation-plan/INDEX.md
 M tests/test_action_parser.py
 M tests/test_agent_loop.py
 M tests/test_command_tools.py
 M tests/test_filesystem_tools.py
 M tests/test_path_guard.py
 M tests/test_web_fetch_tools.py
?? docs/04-implementation-spec/P1-002-permission-negative-gate-spec.md
?? docs/04-implementation-plan/P1-002-permission-negative-gate-plan.md
```

If runtime source changes appear, explain which new AgentLoop capability gap required them. If unrelated files appear, inspect before continuing and do not include unrelated edits.

---

### Task 5: Update docs after implementation passes

**Files:**

- Modify: `docs/05-testing/testing-strategy.md`
- Modify: `docs/04-implementation-backlog/backlog.md`
- Modify: `docs/04-implementation-spec/P1-002-permission-negative-gate-spec.md`
- Modify: `docs/04-implementation-plan/P1-002-permission-negative-gate-plan.md`
- Modify: `docs/04-implementation-spec/INDEX.md`
- Modify: `docs/04-implementation-plan/INDEX.md`
- Modify if active pointers change: `docs/INDEX.md`

- [ ] **Step 1: Document the gate command**

In `docs/05-testing/testing-strategy.md`, add this section after `## Negative Tests`:

```markdown
## Permission Negative Gate

P1-002 defines a focused permission negative gate（权限负向门禁）:

```bash
python -m pytest -m permission_negative -q
```

This gate covers fail-closed（失败关闭） behavior for path traversal（路径逃逸）、symlink escape（符号链接逃逸）、AllowedWriteSet（允许写入集合）、undeclared command（未声明命令）、free shell string（自由命令字符串）、network deny（网络拒绝）、missing network policy（缺失网络策略）、invalid provider JSON（无效模型 JSON）、unknown action（未知动作）、max steps（最大步数） and observation truncation（观察结果截断）.

The gate is not a replacement for the full suite:

```bash
python -m pytest -q
```
```

- [ ] **Step 2: Mark P1-002 completed only after tests pass**

Change `docs/04-implementation-backlog/backlog.md` from:

```markdown
| P1-002 | 整合现有 permission negative tests（权限负向测试）为单一门禁，并补齐网络拒绝场景 | pending | `testing-strategy.md`, `mvp-acceptance.md`, `0003-use-fail-closed-permission-model.md` |
```

To:

```markdown
| P1-002 | 整合现有 permission negative tests（权限负向测试）为单一门禁，并补齐网络拒绝场景 | completed | `P1-002-permission-negative-gate-spec.md`, `testing-strategy.md`, `mvp-acceptance.md`, `0003-use-fail-closed-permission-model.md` |
```

- [ ] **Step 3: Mark spec implemented**

Change `docs/04-implementation-spec/P1-002-permission-negative-gate-spec.md` from:

```markdown
## Status

draft
```

To:

```markdown
## Status

implemented
```

- [ ] **Step 4: Mark plan implemented**

Change `docs/04-implementation-plan/P1-002-permission-negative-gate-plan.md` from:

```markdown
**Status:** draft
```

To:

```markdown
**Status:** implemented
```

- [ ] **Step 5: Move spec index entry to completed / archived**

Remove this active row from `docs/04-implementation-spec/INDEX.md`:

```markdown
| `P1-002-permission-negative-gate-spec.md` | draft | 定义 P1-002 permission negative gate（权限负向门禁）的范围、覆盖矩阵、事件语义和无兜底要求 | 实现 P1-002 前 |
```

Add this completed row:

```markdown
| `P1-002-permission-negative-gate-spec.md` | 2026-06-06 | 已实现 P1-002 permission negative gate（权限负向门禁），保留为负向门禁规格记录 |
```

- [ ] **Step 6: Move plan index entry to completed / archived**

Remove this active row from `docs/04-implementation-plan/INDEX.md`:

```markdown
| `P1-002-permission-negative-gate-plan.md` | draft | 实施 P1-002 permission negative gate（权限负向门禁）的 TDD 计划 | 执行 P1-002 时 |
```

Add this completed row:

```markdown
| `P1-002-permission-negative-gate-plan.md` | 2026-06-06 | 已实施 P1-002 permission negative gate（权限负向门禁），保留为 TDD 实施记录 |
```

- [ ] **Step 7: Run final verification after docs updates**

Run:

```bash
python -m pytest -m permission_negative -q
python -m pytest -q
git status --short
```

Expected:

```text
<permission negative gate passed>
<full suite passed>
```

`git status --short` should show only P1-002 implementation, tests, and required docs/index/backlog updates.

---

## Self-Review Checklist

Before implementation is considered ready for user review:

- [ ] Spec coverage: Every requirement in `docs/04-implementation-spec/P1-002-permission-negative-gate-spec.md` is covered by a task, selected test, new focused AgentLoop test, or explicit out-of-scope statement.
- [ ] Placeholder scan: This plan contains no placeholder markers, no vague “add tests” step, no mock success path, and no silent fallback.
- [ ] Minimality check: New tests are limited to AgentLoop runtime capability gaps; existing tests are reused instead of duplicated.
- [ ] Type consistency: `permission_negative`, `AgentLoop`, `AgentRunResult`, `permission.decided`, `action.rejected`, `tool.attempt.started`, `workspace.mutation.recorded`, and `network.fetch.completed` names match existing code and contracts.
- [ ] Scope check: No new permission engine, new tool, Boardroom adapter, README minimal example, or real provider integration is included.
- [ ] Fail-closed check: Denied path, denied symlink, denied write set, undeclared command, free shell string, denied URL, missing network policy, invalid JSON, unknown action, max steps, and observation truncation are all proved without fallback.
- [ ] Verification check: `python -m pytest -m permission_negative -q`, `python -m pytest -q`, no-fallback source scan, and working tree scope check pass before any completion claim.

## Self-Review Result

- Spec coverage（规格覆盖）：计划覆盖 P1-002 spec（规格）中的 gate command（门禁命令）、验收矩阵、最小测试选择规则、事件语义、文档影响和无兜底要求。
- Placeholder scan（占位符扫描）：未使用占位式标记、空泛“补充测试”或未定义步骤；每个新增测试都有完整代码和预期命令。
- Minimality check（最小性检查）：计划优先标记现有测试，只新增四个 AgentLoop capability tests（运行时能力测试）补齐现有缺口，避免不必要测试扩张。
- Type consistency（类型一致性）：marker、测试名、事件名、失败类型和文件路径与当前代码命名一致。
- Scope check（范围检查）：未纳入 P1-003 minimal example、P1-004 Boardroom adapter、新工具、新动作、真实 provider 或外部 agent bridge。
- No-fallback check（无兜底检查）：计划明确要求拒绝后不执行 tool、不写 mutation、不发网络请求、不使用默认策略、不伪造成成功。
