# P2-006 Complex Real Provider Atomic Task Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build P2-006 `complex real provider atomic task gate`（复杂真实供应商原子任务门禁）, a default-disabled success-only real provider（真实供应商）integration gate that proves `atomic-agent`（原子智能体）can carry one longer but still atomic repair task with auditable evidence（证据）.

**Architecture:** Add a pytest-based integration harness（集成测试驱动） in `tests/test_real_provider_complex_task.py`. The harness creates a small broken Python project（破损 Python 项目） under `tmp_path`, runs `AgentLoop`（智能体循环） with `OpenAICompatibleProviderAdapter`（OpenAI 兼容供应商适配器）, restricts writes to `work/src/` and `work/output/`, and asserts event stream（事件流）, command history（命令历史）, workspace mutation（工作区变更） and source inventory lineage（源码清单谱系） evidence. Provider option（供应商参数） defaults live only in the integration harness, not runtime core（运行时核心）.

**Tech Stack:** Python 3.11+, pytest（测试框架）, pydantic（数据模型校验）, `AgentLoop`（智能体循环）, `FilesystemTools`（文件系统工具）, `CommandTools`（命令工具）, `EventRecorder`（事件记录器）, `ArtifactWriter`（产物写入器）, `OpenAICompatibleProviderAdapter`（OpenAI 兼容供应商适配器）.

---

## Scope and Non-Negotiables

- P2-006 is manual/nightly only（手动/夜间门禁）, not base CI（基础持续集成）.
- Default command must skip the real provider test and must not perform network I/O:

  ```bash
  python -m pytest tests/test_real_provider_complex_task.py -q
  ```

- Explicit enablement variable:

  ```text
  ATOMIC_AGENT_RUN_REAL_PROVIDER_COMPLEX_TASK=1
  ```

- Missing provider config after explicit enablement is failure, not skip.
- `reasoning_effort=high`（高推理强度） is an explicit integration harness default and must fail closed（失败关闭） if rejected by the provider; do not silently remove it and retry.
- Do not modify runtime core defaults for provider options.
- Do not allow writes to `work/tests/`, `work/expected/`, or `work/data/`.
- Do not count provider summary（供应商摘要） alone as success evidence.
- Do not mark P2-006 completed in backlog unless the explicitly enabled real provider gate passes.
- Commit steps in this plan are checkpoints only; execute them only when the user has explicitly authorized commits in the active session.

## File Structure

### Create

- `tests/test_real_provider_complex_task.py`
  - Owns the P2-006 pytest marker（pytest 标记） gate, env parsing（环境变量解析）, workspace fixture（工作区测试夹具）, command policy（命令策略）, `AgentInvocation`（智能体调用请求） construction, real provider execution, and success-only assertions.

- `docs/04-implementation-plan/P2-006-complex-real-provider-atomic-task-gate-plan.md`
  - This implementation plan（实施计划）.

### Modify

- `pyproject.toml`
  - Register `real_provider_complex_task` marker.

- `docs/05-testing/testing-strategy.md`
  - Document the marker, enablement env var, default skip, success-only behavior, and cost/flakiness risk.

- `docs/04-implementation-backlog/backlog.md`
  - Mark P2-006 completed only after explicit real provider success.

- `docs/04-implementation-spec/INDEX.md`
  - Move or reclassify P2-006 spec（规格） after implementation and verification.

- `docs/INDEX.md`
  - Update active document pointers if P2-006 plan/spec status changes.

- `docs/04-implementation-plan/INDEX.md`
  - Register this active plan now; move it to completed/archived after implementation finishes.

---

## Task 1: Register the pytest Marker（pytest 标记）

**Files:**
- Modify: `pyproject.toml`
- Test: `tests/test_real_provider_complex_task.py` after Task 2 creates it

- [ ] **Step 1: Add the marker entry**

Add this string to `[tool.pytest.ini_options].markers`:

```toml
"real_provider_complex_task: success-only OpenAI-compatible real provider complex atomic task gate; skipped unless ATOMIC_AGENT_RUN_REAL_PROVIDER_COMPLEX_TASK=1",
```

The marker list should include these entries:

```toml
markers = [
  "permission_negative: fail-closed permission and security boundary tests",
  "real_provider: OpenAI-compatible real provider integration tests; skipped unless ATOMIC_AGENT_RUN_REAL_PROVIDER=1",
  "real_provider_tool_success: success-only OpenAI-compatible real provider tool integration tests; skipped unless ATOMIC_AGENT_RUN_REAL_PROVIDER_TOOL_SUCCESS=1",
  "real_provider_complex_task: success-only OpenAI-compatible real provider complex atomic task gate; skipped unless ATOMIC_AGENT_RUN_REAL_PROVIDER_COMPLEX_TASK=1",
]
```

- [ ] **Step 2: Verify marker registration after Task 2 exists**

Run:

```bash
python -m pytest tests/test_real_provider_complex_task.py -q
```

Expected after Task 2:

```text
1 skipped
```

There must be no `PytestUnknownMarkWarning`.

- [ ] **Step 3: Commit checkpoint if authorized**

```bash
git add pyproject.toml
git commit -m "test: 注册P2复杂真实供应商门禁标记"
```

---

## Task 2: Create Gate Skeleton and Default Skip（默认跳过）

**Files:**
- Create: `tests/test_real_provider_complex_task.py`

- [ ] **Step 1: Write the skip behavior first**

Create `tests/test_real_provider_complex_task.py` with this initial content:

```python
import os
from pathlib import Path
import sys

import pytest


PYTHON = Path(sys.executable).resolve()
REQUIRED_ENV = (
    "ATOMIC_AGENT_REAL_PROVIDER_BASE_URL",
    "ATOMIC_AGENT_REAL_PROVIDER_API_KEY",
    "ATOMIC_AGENT_REAL_PROVIDER_MODEL",
)


def require_real_provider_complex_task_enabled():
    if os.environ.get("ATOMIC_AGENT_RUN_REAL_PROVIDER_COMPLEX_TASK") != "1":
        pytest.skip("set ATOMIC_AGENT_RUN_REAL_PROVIDER_COMPLEX_TASK=1 to run complex real provider gate")
    missing = [name for name in REQUIRED_ENV if not os.environ.get(name)]
    if missing:
        pytest.fail("missing required complex real provider test configuration: " + ", ".join(missing))


@pytest.mark.real_provider_complex_task
def test_real_provider_complex_atomic_task_gate(tmp_path):
    require_real_provider_complex_task_enabled()
    assert tmp_path.exists()
```

- [ ] **Step 2: Run the default skip test**

Run:

```bash
python -m pytest tests/test_real_provider_complex_task.py -q
```

Expected:

```text
1 skipped
```

- [ ] **Step 3: Verify explicit enablement without config fails**

Run:

```bash
ATOMIC_AGENT_RUN_REAL_PROVIDER_COMPLEX_TASK=1 \
python -m pytest tests/test_real_provider_complex_task.py -q
```

Expected: fail with text containing:

```text
missing required complex real provider test configuration
```

- [ ] **Step 4: Commit checkpoint if authorized**

```bash
git add tests/test_real_provider_complex_task.py
git commit -m "test: 添加P2复杂真实供应商门禁骨架"
```

---

## Task 3: Add Provider Option Parsing（供应商参数解析）

**Files:**
- Modify: `tests/test_real_provider_complex_task.py`

- [ ] **Step 1: Write failing provider option tests**

Append these imports and tests:

```python
import json

from atomic_agent.providers.openai_compatible import OpenAICompatibleProviderOptions


def test_provider_options_defaults_to_complex_gate_profile(monkeypatch):
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_BASE_URL", "https://provider.example/v1")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_API_KEY", "secret-key")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_MODEL", "provider-model")

    options = provider_options()

    assert options.context_window_tokens == 400000
    assert options.max_output_tokens == 128000
    assert options.stream_idle_timeout_seconds == 30.0
    assert options.total_timeout_seconds == 600.0
    assert options.reasoning_effort == "high"


def test_provider_options_reads_explicit_p2_005_env(monkeypatch):
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_BASE_URL", "https://provider.example/v1")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_API_KEY", "secret-key")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_MODEL", "provider-model")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_CONTEXT_WINDOW_TOKENS", "123456")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_MAX_OUTPUT_TOKENS", "4096")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_STREAM_IDLE_TIMEOUT_SECONDS", "12.5")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_TOTAL_TIMEOUT_SECONDS", "777")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_TEMPERATURE", "0.2")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_REASONING_EFFORT", "medium")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_TOP_P", "1.0")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_PRESENCE_PENALTY", "0.0")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_FREQUENCY_PENALTY", "0.0")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_SEED", "20260608")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_STOP", '["END_ACTION"]')
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_RESPONSE_FORMAT_JSON", '{"type":"json_object"}')
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_STREAM_OPTIONS_JSON", '{"include_usage":true}')
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_SERVICE_TIER", "default")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_USER", "atomic-agent-boardroom-os")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_LABEL", "boardroom-os-real-provider")

    options = provider_options()

    assert options.context_window_tokens == 123456
    assert options.max_output_tokens == 4096
    assert options.stream_idle_timeout_seconds == 12.5
    assert options.total_timeout_seconds == 777.0
    assert options.temperature == 0.2
    assert options.reasoning_effort == "medium"
    assert options.top_p == 1.0
    assert options.presence_penalty == 0.0
    assert options.frequency_penalty == 0.0
    assert options.seed == 20260608
    assert options.stop == ("END_ACTION",)
    assert options.response_format == {"type": "json_object"}
    assert options.stream_options == {"include_usage": True}
    assert options.service_tier == "default"
    assert options.user == "atomic-agent-boardroom-os"
    assert options.provider_label == "boardroom-os-real-provider"


def test_provider_options_rejects_non_object_json_env(monkeypatch):
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_BASE_URL", "https://provider.example/v1")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_API_KEY", "secret-key")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_MODEL", "provider-model")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_RESPONSE_FORMAT_JSON", "[]")

    with pytest.raises(ValueError, match="ATOMIC_AGENT_REAL_PROVIDER_RESPONSE_FORMAT_JSON must be a JSON object"):
        provider_options()


def test_provider_options_rejects_invalid_stop_env(monkeypatch):
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_BASE_URL", "https://provider.example/v1")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_API_KEY", "secret-key")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_MODEL", "provider-model")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_STOP", "[]")

    with pytest.raises(ValueError, match="ATOMIC_AGENT_REAL_PROVIDER_STOP must be a non-empty JSON array"):
        provider_options()
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/test_real_provider_complex_task.py -k "provider_options" -q
```

Expected: fail with `NameError: name 'provider_options' is not defined`.

- [ ] **Step 3: Implement provider option helpers**

Add this helper code above the tests:

```python
def env_value(name, default):
    return os.environ.get(name, default)


def env_int(name, default):
    return int(env_value(name, default))


def env_float_or_none(name, default):
    raw = os.environ.get(name, default)
    if raw in (None, ""):
        return None
    return float(raw)


def env_int_or_none(name, default):
    raw = os.environ.get(name, default)
    if raw in (None, ""):
        return None
    return int(raw)


def env_json_object_or_none(name, default):
    raw = os.environ.get(name, default)
    if raw in (None, ""):
        return None
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError(f"{name} must be a JSON object or empty string")
    return parsed


def env_stop_or_none(name, default):
    raw = os.environ.get(name, default)
    if raw in (None, ""):
        return None
    parsed = json.loads(raw)
    if not isinstance(parsed, list) or not parsed or any(not isinstance(item, str) or item == "" for item in parsed):
        raise ValueError(f"{name} must be a non-empty JSON array of non-empty strings or empty string")
    return tuple(parsed)


def provider_options():
    return OpenAICompatibleProviderOptions(
        base_url=os.environ["ATOMIC_AGENT_REAL_PROVIDER_BASE_URL"],
        api_key=os.environ["ATOMIC_AGENT_REAL_PROVIDER_API_KEY"],
        model=os.environ["ATOMIC_AGENT_REAL_PROVIDER_MODEL"],
        context_window_tokens=env_int("ATOMIC_AGENT_REAL_PROVIDER_CONTEXT_WINDOW_TOKENS", "400000"),
        max_output_tokens=env_int("ATOMIC_AGENT_REAL_PROVIDER_MAX_OUTPUT_TOKENS", "128000"),
        stream_idle_timeout_seconds=float(env_value("ATOMIC_AGENT_REAL_PROVIDER_STREAM_IDLE_TIMEOUT_SECONDS", "30")),
        total_timeout_seconds=float(env_value("ATOMIC_AGENT_REAL_PROVIDER_TOTAL_TIMEOUT_SECONDS", "600")),
        temperature=env_float_or_none("ATOMIC_AGENT_REAL_PROVIDER_TEMPERATURE", ""),
        provider_label=os.environ.get("ATOMIC_AGENT_REAL_PROVIDER_LABEL") or None,
        reasoning_effort=os.environ.get("ATOMIC_AGENT_REAL_PROVIDER_REASONING_EFFORT") or "high",
        top_p=env_float_or_none("ATOMIC_AGENT_REAL_PROVIDER_TOP_P", ""),
        presence_penalty=env_float_or_none("ATOMIC_AGENT_REAL_PROVIDER_PRESENCE_PENALTY", ""),
        frequency_penalty=env_float_or_none("ATOMIC_AGENT_REAL_PROVIDER_FREQUENCY_PENALTY", ""),
        seed=env_int_or_none("ATOMIC_AGENT_REAL_PROVIDER_SEED", ""),
        stop=env_stop_or_none("ATOMIC_AGENT_REAL_PROVIDER_STOP", ""),
        response_format=env_json_object_or_none("ATOMIC_AGENT_REAL_PROVIDER_RESPONSE_FORMAT_JSON", ""),
        stream_options=env_json_object_or_none("ATOMIC_AGENT_REAL_PROVIDER_STREAM_OPTIONS_JSON", ""),
        service_tier=os.environ.get("ATOMIC_AGENT_REAL_PROVIDER_SERVICE_TIER") or None,
        user=os.environ.get("ATOMIC_AGENT_REAL_PROVIDER_USER") or None,
    )
```

- [ ] **Step 4: Run provider option tests**

Run:

```bash
python -m pytest tests/test_real_provider_complex_task.py -k "provider_options" -q
```

Expected:

```text
4 passed
```

- [ ] **Step 5: Commit checkpoint if authorized**

```bash
git add tests/test_real_provider_complex_task.py
git commit -m "test: 添加P2复杂门禁供应商参数解析"
```

---

## Task 4: Build the Broken Workspace Fixture（破损工作区夹具）

**Files:**
- Modify: `tests/test_real_provider_complex_task.py`

- [ ] **Step 1: Write failing fixture tests**

Add imports:

```python
import hashlib
```

Add tests:

```python
def test_complex_workspace_fixture_starts_broken(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    original_hashes = setup_complex_workspace(workspace)

    assert (workspace / "work" / "README.md").exists()
    assert (workspace / "work" / "src" / "report.py").exists()
    assert (workspace / "work" / "src" / "validator.py").exists()
    assert (workspace / "work" / "tests" / "test_report.py").exists()
    assert (workspace / "work" / "expected" / "report.txt").exists()
    assert original_hashes["work/data/orders.json"].startswith("sha256:")

    command_tools = build_complex_command_policy(make_path_guard(workspace))
    first_test_run = command_tools.run_command("run-tests")
    first_validation = command_tools.run_command("validate-report")

    assert first_test_run.ok is True
    assert first_test_run.data["exit_code"] != 0
    assert first_validation.ok is True
    assert first_validation.data["exit_code"] != 0


def test_forbidden_fixture_hashes_detect_mutation(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    original_hashes = setup_complex_workspace(workspace)

    (workspace / "work" / "data" / "orders.json").write_text("[]\n", encoding="utf-8")

    assert forbidden_fixture_hashes(workspace) != original_hashes
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/test_real_provider_complex_task.py -k "complex_workspace_fixture or forbidden_fixture_hashes" -q
```

Expected: fail with undefined helper names.

- [ ] **Step 3: Implement workspace fixture helpers**

Add these helpers:

```python
FORBIDDEN_FIXTURE_PATHS = (
    "work/data/orders.json",
    "work/data/users.json",
    "work/tests/test_report.py",
    "work/expected/report.txt",
)

EXPECTED_REPORT = """Customer Revenue Report
Ada Lovelace: orders=2 total=17.75
Grace Hopper: orders=1 total=20.00
Katherine Johnson: orders=1 total=7.25
Grand Total: 45.00
"""


def write_text(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def setup_complex_workspace(workspace):
    work = workspace / "work"
    for relative in ("data", "src", "tests", "expected", "output"):
        (work / relative).mkdir(parents=True, exist_ok=True)

    write_text(
        work / "README.md",
        """# Repair Task

This workspace contains a small broken customer revenue report generator.
Fix the implementation in `work/src/report.py`, produce `work/output/report.txt`,
and write `work/output/repair-summary.md`.

Do not modify `work/data/`, `work/tests/`, or `work/expected/`.
""",
    )
    write_text(
        work / "data" / "users.json",
        json.dumps(
            [
                {"id": "u1", "name": "Ada Lovelace"},
                {"id": "u2", "name": "Grace Hopper"},
                {"id": "u3", "name": "Katherine Johnson"},
            ],
            sort_keys=True,
            indent=2,
        )
        + "\n",
    )
    write_text(
        work / "data" / "orders.json",
        json.dumps(
            [
                {"id": "o-001", "user_id": "u2", "status": "paid", "total": "20.00"},
                {"id": "o-002", "user_id": "u1", "status": "paid", "total": "12.25"},
                {"id": "o-003", "user_id": "u1", "status": "cancelled", "total": "99.99"},
                {"id": "o-004", "user_id": "u1", "status": "paid", "total": "5.50"},
                {"id": "o-005", "user_id": "u3", "status": "paid", "total": "7.25"},
            ],
            sort_keys=True,
            indent=2,
        )
        + "\n",
    )
    write_text(work / "expected" / "report.txt", EXPECTED_REPORT)
    write_text(work / "src" / "report.py", BROKEN_REPORT_PY)
    write_text(work / "src" / "validator.py", VALIDATOR_PY)
    write_text(work / "tests" / "test_report.py", TEST_REPORT_PY)
    return forbidden_fixture_hashes(workspace)


BROKEN_REPORT_PY = '''from __future__ import annotations

import json
from pathlib import Path


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_users(path: Path):
    return load_json(path)


def load_orders(path: Path):
    return load_json(path)


def summarize_orders(users, orders):
    names_by_id = {user["id"]: user["id"] for user in users}
    totals_by_user = {}
    counts_by_user = {}
    for order in orders:
        user_id = order["user_id"]
        counts_by_user[user_id] = counts_by_user.get(user_id, 0) + 1
        totals_by_user[user_id] = totals_by_user.get(user_id, 0.0) + int(float(order["total"]))
    return [
        (names_by_id.get(user_id, user_id), counts_by_user[user_id], totals_by_user[user_id])
        for user_id in totals_by_user
    ]


def render_report(users, orders):
    rows = summarize_orders(users, orders)
    lines = ["Customer Revenue Report"]
    for name, count, total in rows:
        lines.append(f"{name}: orders={count} total={total:.2f}")
    lines.append(f"Grand Total: {sum(total for _, _, total in rows):.2f}")
    return "\\n".join(lines) + "\\n"


def write_report(users_path: Path, orders_path: Path, output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_report(load_users(users_path), load_orders(orders_path)), encoding="utf-8")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    write_report(root / "data" / "users.json", root / "data" / "orders.json", root / "output" / "report.txt")
    print("report written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

VALIDATOR_PY = '''from __future__ import annotations

from pathlib import Path
import sys


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    expected = root / "expected" / "report.txt"
    actual = root / "output" / "report.txt"
    if not actual.exists():
        print("missing work/output/report.txt", file=sys.stderr)
        return 2
    expected_text = expected.read_text(encoding="utf-8")
    actual_text = actual.read_text(encoding="utf-8")
    if actual_text != expected_text:
        print("report content does not match expected output", file=sys.stderr)
        print("expected:", file=sys.stderr)
        print(expected_text, file=sys.stderr)
        print("actual:", file=sys.stderr)
        print(actual_text, file=sys.stderr)
        return 3
    print("report validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

TEST_REPORT_PY = '''from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from report import load_orders, load_users, render_report, write_report

DATA = ROOT / "data"
EXPECTED = (ROOT / "expected" / "report.txt").read_text(encoding="utf-8")


def rendered_report():
    return render_report(load_users(DATA / "users.json"), load_orders(DATA / "orders.json"))


def test_report_matches_expected_output():
    assert rendered_report() == EXPECTED


def test_cancelled_orders_are_excluded_from_totals():
    output = rendered_report()
    assert "orders=3" not in output
    assert "117.74" not in output
    assert "Grand Total: 45.00" in output


def test_customer_names_and_sorting_are_stable():
    lines = rendered_report().splitlines()
    assert lines == [
        "Customer Revenue Report",
        "Ada Lovelace: orders=2 total=17.75",
        "Grace Hopper: orders=1 total=20.00",
        "Katherine Johnson: orders=1 total=7.25",
        "Grand Total: 45.00",
    ]


def test_write_report_creates_expected_file(tmp_path):
    output_path = tmp_path / "report.txt"
    write_report(DATA / "users.json", DATA / "orders.json", output_path)
    assert output_path.read_text(encoding="utf-8") == EXPECTED
'''


def sha256_file(path):
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def forbidden_fixture_hashes(workspace):
    return {relative: sha256_file(workspace / relative) for relative in FORBIDDEN_FIXTURE_PATHS}
```

- [ ] **Step 4: Implement the path guard and command policy used by fixture tests**

Add imports:

```python
from atomic_agent.command_tools import CommandPolicy, CommandSpec, CommandToolConfig, CommandTools
from atomic_agent.path_guard import WorkspacePathGuard
```

Add helpers:

```python
def make_path_guard(workspace):
    return WorkspacePathGuard(workspace, allowed_write_set=["work/src/", "work/output/"])


def build_complex_command_policy(guard):
    return CommandTools(
        guard,
        CommandPolicy(
            {
                "run-tests": CommandSpec(
                    argv=(str(PYTHON), "-m", "pytest", "work/tests/test_report.py", "-q"),
                    timeout_seconds=20.0,
                    allow_network=False,
                ),
                "validate-report": CommandSpec(
                    argv=(str(PYTHON), "work/src/validator.py"),
                    timeout_seconds=10.0,
                    allow_network=False,
                ),
            }
        ),
        CommandToolConfig(default_timeout_seconds=10.0, max_timeout_seconds=30.0, max_output_bytes=20000),
    )
```

- [ ] **Step 5: Run fixture tests**

Run:

```bash
python -m pytest tests/test_real_provider_complex_task.py -k "complex_workspace_fixture or forbidden_fixture_hashes" -q
```

Expected:

```text
2 passed
```

- [ ] **Step 6: Commit checkpoint if authorized**

```bash
git add tests/test_real_provider_complex_task.py
git commit -m "test: 添加P2复杂门禁破损工作区夹具"
```

---

## Task 5: Build AgentLoop Invocation（智能体循环调用）

**Files:**
- Modify: `tests/test_real_provider_complex_task.py`

- [ ] **Step 1: Write failing invocation tests**

Add imports:

```python
from atomic_agent.models import AgentInvocation
```

Add tests:

```python
def test_build_invocation_uses_complex_gate_bounds(monkeypatch, tmp_path):
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_BASE_URL", "https://provider.example/v1")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_API_KEY", "secret-key")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_MODEL", "provider-model")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    options = provider_options()

    invocation = build_invocation(workspace, options)

    assert isinstance(invocation, AgentInvocation)
    assert invocation.allowed_write_set == ["work/src/", "work/output/"]
    assert invocation.tools == [
        "list_files",
        "read_file",
        "search_files",
        "apply_patch",
        "write_file",
        "run_command",
        "submit_result",
    ]
    assert invocation.budgets["max_steps"] == 100
    assert invocation.budgets["max_parse_failures"] == 1
    assert invocation.metadata["test"] == "real_provider_complex_task"
    assert invocation.metadata["provider_config_summary"]["reasoning_effort"] == "high"
    assert "work/output/repair-summary.md" in invocation.task
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest tests/test_real_provider_complex_task.py -k "build_invocation" -q
```

Expected: fail with `NameError: name 'build_invocation' is not defined`.

- [ ] **Step 3: Implement invocation builder**

Add this code:

```python
COMPLEX_GATE_TOOLS = [
    "list_files",
    "read_file",
    "search_files",
    "apply_patch",
    "write_file",
    "run_command",
    "submit_result",
]

REQUIRED_PRODUCED_PATHS = [
    "work/src/report.py",
    "work/output/report.txt",
    "work/output/repair-summary.md",
]


def provider_config_summary(options):
    return {
        "base_url_configured": bool(options.base_url),
        "api_key_configured": bool(options.api_key),
        "model": options.model,
        "provider_label": options.provider_label,
        "context_window_tokens": options.context_window_tokens,
        "max_output_tokens": options.max_output_tokens,
        "stream_idle_timeout_seconds": options.stream_idle_timeout_seconds,
        "total_timeout_seconds": options.total_timeout_seconds,
        "temperature": options.temperature,
        "reasoning_effort": options.reasoning_effort,
        "top_p": options.top_p,
        "presence_penalty": options.presence_penalty,
        "frequency_penalty": options.frequency_penalty,
        "seed": options.seed,
        "stop_configured": options.stop is not None,
        "response_format_configured": options.response_format is not None,
        "stream_options_configured": options.stream_options is not None,
        "service_tier": options.service_tier,
        "user": options.user,
    }


def build_invocation(workspace, options):
    max_steps = env_int("ATOMIC_AGENT_REAL_PROVIDER_MAX_STEPS", "100")
    task = (
        "You are repairing a small Python report project under work/. "
        "Return exactly one AgentAction JSON object per turn, with no markdown and no code fences. "
        "Every action object must include action_id, action, reason_summary, and input. "
        "Use list_files, read_file, and search_files to understand the project. "
        "You must run run_command with command_id run-tests at least once before making a final submission, "
        "then repair the project so the tests pass. "
        "After repairing, run run_command with command_id run-tests again and run command_id validate-report. "
        "Only modify files under work/src/ and work/output/. Do not modify work/tests/, work/expected/, or work/data/. "
        "The final submit_result input.produced_paths must be exactly "
        "[\"work/src/report.py\", \"work/output/report.txt\", \"work/output/repair-summary.md\"]. "
        "Write work/output/report.txt with the final report content, and write work/output/repair-summary.md with a concise repair summary. "
        "When the task is complete, use submit_result with a non-empty summary and evidence_refs as a list of strings. "
        "Do not use tools that are not listed in invocation.tools."
    )
    return AgentInvocation(
        invocation_id="inv_real_provider_complex_task",
        task=task,
        workspace_root=str(workspace),
        allowed_write_set=["work/src/", "work/output/"],
        tools=COMPLEX_GATE_TOOLS,
        permission_policy={"policy_ref": "policy://tests/real-provider-complex-task"},
        provider_profile=options.to_provider_profile(),
        budgets={
            "max_steps": max_steps,
            "max_parse_failures": 1,
            "max_observation_chars": 30000,
            "max_wall_seconds": options.total_timeout_seconds * max_steps + 5.0,
        },
        output_requirements={"summary": True, "event_stream": True, "artifacts": True},
        metadata={
            "test": "real_provider_complex_task",
            "provider_config_summary": provider_config_summary(options),
        },
    )
```

- [ ] **Step 4: Run invocation test**

Run:

```bash
python -m pytest tests/test_real_provider_complex_task.py -k "build_invocation" -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Commit checkpoint if authorized**

```bash
git add tests/test_real_provider_complex_task.py
git commit -m "test: 构造P2复杂真实供应商调用"
```

---

## Task 6: Build Real Provider Loop Runner（真实供应商循环运行器）

**Files:**
- Modify: `tests/test_real_provider_complex_task.py`

- [ ] **Step 1: Write the runner code**

Add imports:

```python
from dataclasses import dataclass
from datetime import UTC, datetime
import time

from atomic_agent.agent_loop import AgentLoop, AgentLoopConfig, AgentLoopDependencies
from atomic_agent.artifacts import ArtifactWriter, ArtifactWriterConfig
from atomic_agent.event_recorder import EventRecorder, EventRecorderConfig
from atomic_agent.filesystem_tools import FilesystemToolConfig, FilesystemTools
from atomic_agent.providers.openai_compatible import OpenAICompatibleProviderAdapter
```

Add code:

```python
@dataclass(frozen=True)
class ComplexGateRun:
    result: object
    event_stream: Path
    artifact_root: Path
    workspace: Path
    original_forbidden_hashes: dict[str, str]


def utc_timestamp():
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def make_filesystem_tools(guard):
    return FilesystemTools(
        guard,
        FilesystemToolConfig(
            default_read_limit=20000,
            max_read_limit=80000,
            default_max_entries=300,
            max_entries_limit=1500,
            default_max_matches=100,
            max_matches_limit=1000,
        ),
    )


def run_complex_gate(tmp_path):
    base = tmp_path / "real-provider-complex-task"
    workspace = base / "workspace"
    event_stream = base / "events" / "events.jsonl"
    artifact_root = base / "artifacts"
    workspace.mkdir(parents=True)
    event_stream.parent.mkdir(parents=True)
    artifact_root.mkdir(parents=True)

    original_hashes = setup_complex_workspace(workspace)
    options = provider_options()
    guard = make_path_guard(workspace)
    filesystem_tools = make_filesystem_tools(guard)
    command_tools = build_complex_command_policy(guard)
    run_id = "real_provider_complex_task"
    recorder = EventRecorder(
        run_id=run_id,
        config=EventRecorderConfig(
            event_stream_path=event_stream,
            event_stream_ref=f"artifact://{run_id}/events.jsonl",
        ),
        clock=utc_timestamp,
    )
    artifact_writer = ArtifactWriter(
        ArtifactWriterConfig(
            artifact_root=artifact_root,
            artifact_ref_prefix=f"artifact://{run_id}",
        )
    )
    loop = AgentLoop(
        AgentLoopConfig(run_id=run_id),
        AgentLoopDependencies(
            provider=OpenAICompatibleProviderAdapter(options=options),
            filesystem_tools=filesystem_tools,
            command_tools=command_tools,
            event_recorder=recorder,
            artifact_writer=artifact_writer,
            runtime_clock=time.monotonic,
        ),
    )
    result = loop.run(build_invocation(workspace, options))
    return ComplexGateRun(
        result=result,
        event_stream=event_stream,
        artifact_root=artifact_root,
        workspace=workspace,
        original_forbidden_hashes=original_hashes,
    )
```

- [ ] **Step 2: Keep default test skipped**

Update the skeleton integration test body:

```python
@pytest.mark.real_provider_complex_task
def test_real_provider_complex_atomic_task_gate(tmp_path):
    require_real_provider_complex_task_enabled()
    run = run_complex_gate(tmp_path)
    assert_complex_gate_success(run)
```

`assert_complex_gate_success` is implemented in Task 7.

- [ ] **Step 3: Run default file command**

Run:

```bash
python -m pytest tests/test_real_provider_complex_task.py -q
```

Expected after Tasks 3-6 and before Task 7:

```text
7 passed, 1 skipped
```

If the count differs because additional local tests were added, the real provider test must still be skipped and no network call may occur.

- [ ] **Step 4: Commit checkpoint if authorized**

```bash
git add tests/test_real_provider_complex_task.py
git commit -m "test: 添加P2复杂门禁真实循环运行器"
```

---

## Task 7: Add Success-Only Evidence Assertions（只接受成功的证据断言）

**Files:**
- Modify: `tests/test_real_provider_complex_task.py`

- [ ] **Step 1: Add evidence imports**

```python
from atomic_agent.evidence import build_evidence_summary, verify_event_stream
from atomic_agent.models import AgentRunStatus
```

- [ ] **Step 2: Add assertion helpers**

```python
_SHA256_PREFIX = "sha256:"


def read_events(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def event_types(events):
    return [event["type"] for event in events]


def submitted_produced_paths(events):
    for event in reversed(events):
        if event["type"] == "result.submitted":
            return event["payload"]["produced_paths"]
    return []


def completed_tools(events):
    return [event["payload"]["tool"] for event in events if event["type"] == "tool.attempt.completed"]


def command_exit_history(summary, command_id):
    return [item["exit_code"] for item in summary["command_results"] if item["command_id"] == command_id]


def assert_sha256(value, label):
    assert isinstance(value, str) and value.startswith(_SHA256_PREFIX) and len(value) == 71, {label: value}


def assert_command_artifacts_have_sha256(summary):
    for command in summary["command_results"]:
        assert_sha256(command["stdout"]["sha256"], f"{command['command_id']} stdout sha256")
        assert_sha256(command["stderr"]["sha256"], f"{command['command_id']} stderr sha256")


def assert_required_tool_coverage(events):
    tools = completed_tools(events)
    for required in ("list_files", "read_file", "run_command"):
        assert required in tools, {"missing_tool": required, "completed_tools": tools}
    flexible = {"search_files", "apply_patch", "write_file"}
    used_flexible = flexible.intersection(tools)
    assert len(used_flexible) >= 2, {"expected_at_least_two_of": sorted(flexible), "actual": sorted(used_flexible)}


def assert_required_command_history(summary):
    run_tests = command_exit_history(summary, "run-tests")
    validate_report = command_exit_history(summary, "validate-report")
    assert len(run_tests) >= 2, {"run-tests history": run_tests}
    assert any(exit_code != 0 for exit_code in run_tests), {"run-tests history": run_tests}
    assert run_tests[-1] == 0, {"run-tests history": run_tests}
    assert validate_report, {"validate-report history": validate_report}
    assert validate_report[-1] == 0, {"validate-report history": validate_report}


def assert_required_workspace_mutations(summary):
    mutations = summary["workspace_mutations"]
    assert mutations, "expected at least one workspace mutation"
    mutated_paths = {mutation["path"] for mutation in mutations}
    assert "work/src/report.py" in mutated_paths, mutated_paths
    assert "work/output/report.txt" in mutated_paths, mutated_paths
    assert "work/output/repair-summary.md" in mutated_paths, mutated_paths
    for mutation in mutations:
        assert "work/tests/" not in mutation["path"]
        assert "work/expected/" not in mutation["path"]
        assert "work/data/" not in mutation["path"]
        assert_sha256(mutation["after_hash"], "mutation after_hash")
        assert mutation["diff"]["artifact_ref"], mutation
        assert_sha256(mutation["diff"]["sha256"], "mutation diff sha256")


def assert_required_lineage(summary):
    lineage_by_path = {item["path"]: item for item in summary["source_inventory_lineage"]}
    for path in REQUIRED_PRODUCED_PATHS:
        assert path in lineage_by_path, summary["source_inventory_lineage"]
        assert lineage_by_path[path]["lineage_status"] == "traceable", lineage_by_path[path]


def assert_forbidden_fixture_unchanged(run):
    assert forbidden_fixture_hashes(run.workspace) == run.original_forbidden_hashes
```

- [ ] **Step 3: Add the final success assertion function**

```python
def assert_complex_gate_success(run):
    result = run.result
    assert result.status == AgentRunStatus.COMPLETED, failure_context(result, run.event_stream)

    integrity = verify_event_stream(run.event_stream, expected_events_hash=result.events_hash)
    assert integrity["ok"] is True, integrity

    events = read_events(run.event_stream)
    types = event_types(events)
    assert types[-1] == "run.completed", types
    assert "provider.turn.completed" in types, types
    assert "result.submitted" in types, types
    assert submitted_produced_paths(events) == REQUIRED_PRODUCED_PATHS
    assert_required_tool_coverage(events)

    summary = build_evidence_summary(result, run.event_stream)
    assert summary["event_stream"]["integrity"]["ok"] is True
    assert summary["provider_attempts"], summary
    assert_required_command_history(summary)
    assert_required_workspace_mutations(summary)
    assert_required_lineage(summary)
    assert_command_artifacts_have_sha256(summary)
    assert_forbidden_fixture_unchanged(run)

    assert (run.workspace / "work" / "output" / "report.txt").read_text(encoding="utf-8") == EXPECTED_REPORT
    assert (run.workspace / "work" / "output" / "repair-summary.md").read_text(encoding="utf-8").strip()


def failure_context(result, event_stream):
    context = {"result": redact_sensitive_values(result.model_dump(mode="json"))}
    if event_stream.exists():
        events = read_events(event_stream)
        context["event_types"] = event_types(events)
    return context


def redact_sensitive_values(value):
    if isinstance(value, dict):
        return {key: redact_sensitive_values(child) for key, child in value.items()}
    if isinstance(value, list):
        return [redact_sensitive_values(child) for child in value]
    if isinstance(value, str):
        redacted = value
        replacements = {
            os.environ.get("ATOMIC_AGENT_REAL_PROVIDER_API_KEY"): "[REDACTED_API_KEY]",
            os.environ.get("ATOMIC_AGENT_REAL_PROVIDER_BASE_URL"): "[REDACTED_BASE_URL]",
        }
        for raw, replacement in replacements.items():
            if raw:
                redacted = redacted.replace(raw, replacement)
        return redacted
    return value
```

- [ ] **Step 4: Run local non-provider tests**

Run:

```bash
python -m pytest tests/test_real_provider_complex_task.py -q
```

Expected:

```text
7 passed, 1 skipped
```

If exact local count differs, all unmarked local tests must pass and the marked real provider test must skip.

- [ ] **Step 5: Commit checkpoint if authorized**

```bash
git add tests/test_real_provider_complex_task.py
git commit -m "test: 添加P2复杂门禁证据验收"
```

---

## Task 8: Run the Real Provider Gate（真实供应商门禁）

**Files:**
- No source file changes unless this task exposes a real bug in Tasks 1-7.

- [ ] **Step 1: Run base local checks first**

```bash
python -m pytest tests/test_real_provider_complex_task.py -q
```

Expected: all local tests pass and the real provider test skips.

- [ ] **Step 2: Run related existing real-provider helper tests**

```bash
python -m pytest \
  tests/test_real_provider_integration.py \
  tests/test_real_provider_tool_success.py \
  tests/test_minimal_real_provider_loop.py \
  -q
```

Expected: existing local tests pass; default-disabled real provider tests skip unless explicitly enabled.

- [ ] **Step 3: Run full base CI**

```bash
python -m pytest -q
```

Expected: pass with default-disabled real provider gates skipped. There must be no real provider network call without explicit enablement.

- [ ] **Step 4: Run explicit complex gate with real provider config**

Use an existing git-ignored local env profile if available, then run:

```bash
ATOMIC_AGENT_RUN_REAL_PROVIDER_COMPLEX_TASK=1 \
ATOMIC_AGENT_REAL_PROVIDER_REASONING_EFFORT=high \
python -m pytest tests/test_real_provider_complex_task.py -m real_provider_complex_task -q
```

Expected success:

```text
1 passed
```

If provider config is missing, auth fails, provider rejects explicit options, response parsing fails, permission is denied, command validation fails, or the provider cannot complete the repair, this task is not complete. Preserve the event stream and artifact paths from pytest failure output for diagnosis; do not relax assertions first.

- [ ] **Step 5: Diagnose failures without silent fallback**

Use this order:

1. Terminal status（终止状态）: `provider_failed`, `action_parse_failed`, `policy_denied`, `tool_failed`, or `max_steps_exceeded`.
2. Command history（命令历史）: `run-tests` initial failure, final success, and `validate-report` final success.
3. Workspace mutations（工作区变更）: only `work/src/` and `work/output/`, all required produced paths traceable.
4. Provider behavior（供应商行为）: looping, low tool coverage, invalid JSON, or unsupported explicit provider options.
5. Fixture difficulty（夹具难度）: only adjust after proving prompt/permissions/parser are correct.

- [ ] **Step 6: Commit checkpoint if authorized and the gate passes**

```bash
git add tests/test_real_provider_complex_task.py pyproject.toml
git commit -m "test: 建立P2复杂真实供应商原子任务门禁"
```

---

## Task 9: Update Testing Documentation（测试文档）

**Files:**
- Modify: `docs/05-testing/testing-strategy.md`

- [ ] **Step 1: Add documentation after P2-004 real provider section**

Insert this section after the `real_provider_tool_success` section:

```markdown
P2-006 adds a separate default-disabled `real_provider_complex_task` marker（复杂真实供应商原子任务标记）. It is a success-only manual/nightly gate（只接受成功的手动/夜间门禁） that asks a real provider（真实供应商） to repair one small broken Python report project, run declared commands, produce workspace outputs, and submit auditable evidence（可审计证据）.

默认命令：

```bash
python -m pytest tests/test_real_provider_complex_task.py -q
```

默认结果必须 skip（跳过）the real provider integration test and must not make a provider network call, because it is not enabled unless:

```text
ATOMIC_AGENT_RUN_REAL_PROVIDER_COMPLEX_TASK=1
```

显式启用命令可复用 P2-005 provider options（供应商参数）:

```bash
ATOMIC_AGENT_RUN_REAL_PROVIDER_COMPLEX_TASK=1 \
ATOMIC_AGENT_REAL_PROVIDER_BASE_URL="https://provider.example/v1" \
ATOMIC_AGENT_REAL_PROVIDER_API_KEY="replace-with-real-key" \
ATOMIC_AGENT_REAL_PROVIDER_MODEL="provider-model" \
ATOMIC_AGENT_REAL_PROVIDER_REASONING_EFFORT=high \
python -m pytest tests/test_real_provider_complex_task.py -m real_provider_complex_task -q
```

Required env vars（必需环境变量）:

```text
ATOMIC_AGENT_RUN_REAL_PROVIDER_COMPLEX_TASK=1
ATOMIC_AGENT_REAL_PROVIDER_BASE_URL
ATOMIC_AGENT_REAL_PROVIDER_API_KEY
ATOMIC_AGENT_REAL_PROVIDER_MODEL
```

Recommended explicit defaults（建议显式默认值）:

```text
ATOMIC_AGENT_REAL_PROVIDER_MAX_STEPS=100
ATOMIC_AGENT_REAL_PROVIDER_TOTAL_TIMEOUT_SECONDS=600
ATOMIC_AGENT_REAL_PROVIDER_STREAM_IDLE_TIMEOUT_SECONDS=30
ATOMIC_AGENT_REAL_PROVIDER_REASONING_EFFORT=high
```

Success requires `run.completed`（运行完成）, event stream integrity（事件流完整性）, at least one provider turn（供应商轮次）, required tool coverage（工具覆盖）, `run-tests` failing then passing, `validate-report` passing, traceable produced paths（可追溯产出路径）, command stdout/stderr artifact sha256（命令输出产物哈希）, and no mutation under `work/tests/`, `work/expected/`, or `work/data/`.

Provider failure（供应商失败）, parse failure（解析失败）, permission denied（权限拒绝）, tool failure（工具失败）, missing credentials（缺失凭据）, auth/network failure（认证/网络失败）, or unsupported explicit provider options（不支持显式供应商参数） cannot pass this gate. The gate is costlier and more variable than P2-004, so it remains manual/nightly and must not enter base CI（基础持续集成）.
```

- [ ] **Step 2: Run markdown-only sanity check**

Run:

```bash
git diff --check docs/05-testing/testing-strategy.md
```

Expected: no output.

- [ ] **Step 3: Commit checkpoint if authorized**

```bash
git add docs/05-testing/testing-strategy.md
git commit -m "docs: 记录P2复杂真实供应商门禁"
```

---

## Task 10: Update Backlog and Indexes（待办与索引）

**Files:**
- Modify: `docs/04-implementation-backlog/backlog.md`
- Modify: `docs/04-implementation-spec/INDEX.md`
- Modify: `docs/INDEX.md`
- Modify: `docs/04-implementation-plan/INDEX.md`

- [ ] **Step 1: Only proceed after explicit real provider success**

Do not mark P2-006 completed unless this command passed with real provider config:

```bash
ATOMIC_AGENT_RUN_REAL_PROVIDER_COMPLEX_TASK=1 \
python -m pytest tests/test_real_provider_complex_task.py -m real_provider_complex_task -q
```

- [ ] **Step 2: Update backlog**

Change P2-006 status in `docs/04-implementation-backlog/backlog.md` from `pending` to `completed`.

Expected row:

```markdown
| P2-006 | 建立 complex real provider atomic task gate（复杂真实供应商原子任务门禁） | completed | `P2-006-complex-real-provider-atomic-task-gate-spec.md`, `P2-005-openai-compatible-provider-options-hardening-spec.md`, `testing-strategy.md`, `mvp-acceptance.md`, `roadmap.md` |
```

- [ ] **Step 3: Update implementation spec index**

Move `P2-006-complex-real-provider-atomic-task-gate-spec.md` out of Current Active Documents and into Completed / Archived Documents with completion date `2026-06-08` after the gate passes.

Completed row:

```markdown
| `P2-006-complex-real-provider-atomic-task-gate-spec.md` | 2026-06-08 | 已实现 P2-006 complex real provider atomic task gate（复杂真实供应商原子任务门禁），保留为真实供应商复杂原子任务门禁规格记录 |
```

- [ ] **Step 4: Update global docs index**

Remove the P2 active pointer for the P2-006 spec from `docs/INDEX.md` after completion. If P2 has no pending active spec/plan, do not invent a replacement pointer.

- [ ] **Step 5: Update implementation plan index**

Move this plan from Current Active Documents to Completed / Archived Documents with completion date `2026-06-08`.

Completed row:

```markdown
| `P2-006-complex-real-provider-atomic-task-gate-plan.md` | 2026-06-08 | 已实施 P2-006 complex real provider atomic task gate（复杂真实供应商原子任务门禁），保留为 TDD 实施记录 |
```

- [ ] **Step 6: Run documentation diff check**

```bash
git diff --check docs/04-implementation-backlog/backlog.md docs/04-implementation-spec/INDEX.md docs/INDEX.md docs/04-implementation-plan/INDEX.md
```

Expected: no output.

- [ ] **Step 7: Commit checkpoint if authorized**

```bash
git add \
  docs/04-implementation-backlog/backlog.md \
  docs/04-implementation-spec/INDEX.md \
  docs/INDEX.md \
  docs/04-implementation-plan/INDEX.md
git commit -m "docs: 完成P2复杂真实供应商门禁收尾"
```

---

## Task 11: Final Verification（最终验证）

**Files:**
- No new files unless prior verification exposes defects.

- [ ] **Step 1: Run focused local test file**

```bash
python -m pytest tests/test_real_provider_complex_task.py -q
```

Expected: provider option and fixture tests pass; the real provider test skips by default.

- [ ] **Step 2: Run related tests**

```bash
python -m pytest \
  tests/test_real_provider_integration.py \
  tests/test_real_provider_tool_success.py \
  tests/test_minimal_real_provider_loop.py \
  -q
```

Expected: pass/skip according to default-disabled real provider settings.

- [ ] **Step 3: Run full base suite**

```bash
python -m pytest -q
```

Expected: pass; base CI does not require real provider credentials.

- [ ] **Step 4: Run explicit P2-006 gate**

```bash
ATOMIC_AGENT_RUN_REAL_PROVIDER_COMPLEX_TASK=1 \
python -m pytest tests/test_real_provider_complex_task.py -m real_provider_complex_task -q
```

Expected with valid provider config:

```text
1 passed
```

- [ ] **Step 5: Record verification status honestly**

Use these exact completion statements:

- If Step 1-3 pass but Step 4 was not run due missing credentials:
  - “P2-006 gate scaffold（门禁脚手架） is implemented and base CI-safe; explicit real provider acceptance was not run, so backlog remains pending.”
- If Step 4 fails:
  - “P2-006 explicit real provider gate failed; backlog remains pending. Failure kind and artifact paths are: ...”
- If Step 4 passes:
  - “P2-006 is completed and verified with explicit real provider gate; backlog/docs indexes were updated.”

---

## Self-Review

### Spec Coverage（规格覆盖）

- Covers the required marker `real_provider_complex_task`.
- Covers explicit enablement `ATOMIC_AGENT_RUN_REAL_PROVIDER_COMPLEX_TASK=1`.
- Reuses P2-005 provider options and defaults `reasoning_effort=high` only in the integration harness.
- Creates a small broken Python report project in `tmp_path`.
- Enables all required tools: `list_files`, `read_file`, `search_files`, `apply_patch`, `write_file`, `run_command`, `submit_result`.
- Restricts writes to `work/src/` and `work/output/`.
- Declares `run-tests` and `validate-report` with absolute Python executable and `shell=False`.
- Requires initial command failure, final command success, event integrity, workspace mutations, artifact sha256, produced paths, and traceable lineage.
- Keeps provider failure, parse failure, permission denied, and tool failure as failures.
- Keeps the gate out of base CI.

### Placeholder Scan（占位扫描）

- No `TBD`, `TODO`, “implement later”, or open-ended placeholder steps.
- Code snippets define concrete helper names, env vars, command ids, paths, and expected outputs.
- Deferred behavior is explicit: backlog completion waits for explicit real provider success.

### Type and Naming Consistency（类型与命名一致性）

- Test file: `tests/test_real_provider_complex_task.py`.
- Marker: `real_provider_complex_task`.
- Enablement env var: `ATOMIC_AGENT_RUN_REAL_PROVIDER_COMPLEX_TASK`.
- Commands: `run-tests`, `validate-report`.
- Produced paths: `work/src/report.py`, `work/output/report.txt`, `work/output/repair-summary.md`.
- Required status: `AgentRunStatus.COMPLETED` and terminal event `run.completed`.
