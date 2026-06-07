# P2-002 Real Provider Minimal Integration Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a default-disabled OpenAI-compatible streaming real provider integration gate that proves the existing `AgentLoop` can consume real provider output, parse provider-agnostic `AgentAction` JSON, execute controlled tools, record auditable events, and build evidence summary without destabilizing base CI.

**Architecture:** Add a task-agnostic `OpenAICompatibleProviderAdapter` behind the existing `ProviderAdapter.complete(context) -> str` protocol. Keep tool execution, permission decisions, action parsing, event recording, and evidence mapping inside the existing runtime path; the adapter only turns `ProviderContext` into OpenAI-compatible streaming chat completion messages and returns raw JSON action text.

**Tech Stack:** Python 3.11+, Pydantic v2, pytest, official OpenAI Python SDK v1, existing `AgentLoop`, `ArtifactWriter`, `EventRecorder`, `FilesystemTools`, `CommandTools`, `verify_event_stream`, and `build_evidence_summary`.

---

## Current Context

`atomic-agent`（原子智能体）当前处于 P2: Evidence Mapping and Integration Gates（证据映射与集成门禁）阶段。P0/P1 已完成最小 runtime（运行时）、permission policy（权限策略）、network policy（网络策略）、fake provider loop（假模型供应商循环）和 Boardroom `AgentRuntimePort` adapter（Boardroom 智能体运行时端口适配器）。P2-001 已完成 event stream / evidence mapping（事件流 / 证据映射）和 artifact hash（产物哈希）硬化。

P2-002 是当前 backlog（待办）中唯一 pending（待处理）的非 deferred（延后）P2 任务。它必须作为 manual/nightly integration gate（手动 / 夜间集成门禁）实现，默认不进入 base CI（基础持续集成）的联网路径。

Authoritative inputs（权威输入）：

- `docs/04-implementation-spec/P2-002-real-provider-minimal-integration-gate-spec.md`
- `docs/04-implementation-backlog/backlog.md`
- `docs/05-testing/testing-strategy.md`
- `docs/03-contracts/agent-action-protocol.md`
- `docs/04-implementation-acceptance/mvp-acceptance.md`
- `docs/06-roadmap/roadmap.md`
- `docs/09-adr/0002-use-provider-agnostic-action-protocol.md`
- `docs/09-adr/0003-use-fail-closed-permission-model.md`
- `docs/09-adr/0004-keep-boardroom-os-as-governance-source.md`

---

## File Structure

### Create

- `src/atomic_agent/providers/__init__.py`  
  Provider adapter package（供应商适配器包）入口。首版只导出 OpenAI-compatible provider（OpenAI 兼容供应商）。

- `src/atomic_agent/providers/openai_compatible.py`  
  Implements `OpenAICompatibleProviderOptions`（OpenAI 兼容供应商配置）、`OpenAICompatibleProviderAdapter`（OpenAI 兼容供应商适配器）、`OpenAICompatibleProviderError`（OpenAI 兼容供应商错误）、streaming extraction（流式内容提取）、idle timeout（空闲超时）和 total timeout（总超时）检查。

- `src/atomic_agent/examples/minimal_real_provider_loop.py`  
  Standalone CLI（独立命令入口），用于手动/夜间运行真实 provider gate（供应商门禁）。

- `tests/test_openai_compatible_provider.py`  
  不联网 unit tests（单元测试）。使用 injected fake OpenAI client（注入式假 OpenAI 客户端）验证 adapter 请求参数、streaming 行为、错误传播和超时语义。

- `tests/test_minimal_real_provider_loop_example.py`  
  不联网 CLI tests（命令行入口测试）。验证路径保护、参数校验、API key 不泄露、runtime 失败关闭结果写出。

- `tests/test_real_provider_integration.py`  
  默认 skip（跳过）的真实 provider integration gate（集成门禁）。仅在 `ATOMIC_AGENT_RUN_REAL_PROVIDER=1` 时运行。

### Modify

- `pyproject.toml`  
  Add `real-provider` optional dependency（可选依赖） and `real_provider` pytest marker（pytest 标记）。

- `README.md`  
  真实 gate 验证后新增 OpenAI-compatible real provider gate 的 manual/nightly 说明。

- `docs/05-testing/testing-strategy.md`  
  真实 gate 验证后记录 marker、启用变量、配置变量、streaming timeout（流式超时）和 optional dependency（可选依赖）安装方式。

- `docs/04-implementation-backlog/backlog.md`  
  全部验证通过后将 P2-002 标记 completed。

- `docs/04-implementation-spec/INDEX.md`  
  完成后把 P2-002 spec（规格）从 active draft（活跃草案）移到 completed / archived（完成 / 归档）记录。

- `docs/04-implementation-plan/INDEX.md`  
  当前已登记本 plan 为 draft。完成后移到 completed / archived。

- `docs/INDEX.md`  
  完成后同步全局 active document pointer（当前活跃文档指针）。

---

## Task 1: Add Project Metadata for Real Provider Gate

**Files:**

- Modify: `pyproject.toml`

### Step 1: Add a failing metadata test by inspecting `pyproject.toml`

Do not add a test file for this metadata-only change. Use Python to assert the expected metadata before editing.

Run:

```bash
python - <<'PY'
from pathlib import Path
text = Path('pyproject.toml').read_text(encoding='utf-8')
assert 'real-provider = [' in text
assert 'openai>=1.0,<2.0' in text
assert 'real_provider: OpenAI-compatible real provider integration tests; skipped unless ATOMIC_AGENT_RUN_REAL_PROVIDER=1' in text
PY
```

Expected before implementation:

- FAIL with `AssertionError`.

### Step 2: Modify optional dependencies and pytest marker

Edit `pyproject.toml` so the relevant sections contain exactly these entries while preserving existing entries:

```toml
[project.optional-dependencies]
test = [
  "pytest>=8.0,<9.0",
]
real-provider = [
  "openai>=1.0,<2.0",
]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
markers = [
  "permission_negative: fail-closed permission and security boundary tests",
  "real_provider: OpenAI-compatible real provider integration tests; skipped unless ATOMIC_AGENT_RUN_REAL_PROVIDER=1",
]
```

### Step 3: Verify metadata

Run:

```bash
python - <<'PY'
from pathlib import Path
text = Path('pyproject.toml').read_text(encoding='utf-8')
assert 'real-provider = [' in text
assert 'openai>=1.0,<2.0' in text
assert 'real_provider: OpenAI-compatible real provider integration tests; skipped unless ATOMIC_AGENT_RUN_REAL_PROVIDER=1' in text
PY
```

Expected:

- PASS with no output.

### Step 4: Verify base tests still avoid real provider

Run:

```bash
python -m pytest -q
```

Expected:

- PASS.
- No OpenAI-compatible provider credentials are required.
- No real provider network call is made.

### Step 5: Commit only if the user explicitly requested commits

Do not commit by default. If the user explicitly asks to commit, use:

```bash
git add pyproject.toml
git commit -m "chore: 添加真实供应商测试元数据"
```

---

## Task 2: Write OpenAI-Compatible Provider Adapter Unit Tests

**Files:**

- Create: `tests/test_openai_compatible_provider.py`
- Later implementation: `src/atomic_agent/providers/openai_compatible.py`

### Step 1: Create the failing unit test file

Create `tests/test_openai_compatible_provider.py` with this content:

```python
import json
from types import SimpleNamespace

import pytest

from atomic_agent.agent_loop import ProviderContext
from atomic_agent.models import AgentInvocation
from atomic_agent.providers.openai_compatible import (
    OpenAICompatibleProviderAdapter,
    OpenAICompatibleProviderError,
    OpenAICompatibleProviderOptions,
)


VALID_ACTION_TEXT = json.dumps(
    {
        "action_id": "step-0001",
        "action": "submit_result",
        "reason_summary": "Return a valid result.",
        "input": {"summary": "ok", "produced_paths": [], "evidence_refs": []},
    },
    sort_keys=True,
)


class FakeClock:
    def __init__(self, readings):
        self.readings = list(readings)
        self.last = self.readings[-1] if self.readings else 0.0

    def __call__(self):
        if self.readings:
            self.last = self.readings.pop(0)
        return self.last


class FakeDelta:
    def __init__(self, content):
        self.content = content


class FakeChoice:
    def __init__(self, content=None, finish_reason=None, has_delta=True):
        self.finish_reason = finish_reason
        if has_delta:
            self.delta = FakeDelta(content)


class FakeChunk:
    def __init__(self, choices):
        self.choices = choices


class FakeCompletions:
    def __init__(self, owner):
        self.owner = owner

    def create(self, **kwargs):
        self.owner.requests.append(kwargs)
        if self.owner.error is not None:
            raise self.owner.error
        return iter(self.owner.chunks)


class FakeChat:
    def __init__(self, owner):
        self.completions = FakeCompletions(owner)


class FakeOpenAIClient:
    def __init__(self, chunks=None, error=None):
        self.chunks = chunks or []
        self.error = error
        self.requests = []
        self.chat = FakeChat(self)


def chunk(content=None, finish_reason=None, has_delta=True):
    return FakeChunk([FakeChoice(content=content, finish_reason=finish_reason, has_delta=has_delta)])


def empty_choices_chunk():
    return FakeChunk([])


def options(**overrides):
    values = {
        "base_url": "https://provider.example/v1",
        "api_key": "secret-key",
        "model": "provider-model",
        "context_window_tokens": 400000,
        "max_output_tokens": 8192,
        "stream_idle_timeout_seconds": 30.0,
        "total_timeout_seconds": 3600.0,
        "temperature": None,
        "provider_label": "test-provider",
    }
    values.update(overrides)
    return OpenAICompatibleProviderOptions(**values)


def invocation(task="Create work/real-provider-output.txt, then submit the result."):
    return AgentInvocation(
        invocation_id="inv-real-provider-test",
        task=task,
        workspace_root="/tmp/atomic-agent-test/workspace",
        allowed_write_set=["work/"],
        tools=["write_file", "submit_result"],
        permission_policy={"policy_ref": "policy://tests/real-provider"},
        provider_profile={"provider": "openai-compatible", "model": "provider-model"},
        budgets={
            "max_steps": 4,
            "max_parse_failures": 1,
            "max_observation_chars": 10000,
            "max_wall_seconds": 3605.0,
        },
        output_requirements={"summary": True, "event_stream": True, "artifacts": True},
    )


def provider_context(task="Create work/real-provider-output.txt, then submit the result.", observations=()):
    return ProviderContext(invocation=invocation(task), step=1, observations=tuple(observations))


def adapter(client, clock=None, opts=None):
    return OpenAICompatibleProviderAdapter(
        options=opts or options(),
        client=client,
        clock=clock or FakeClock([0.0, 0.1, 0.2, 0.3]),
    )


def test_adapter_sends_streaming_chat_completion_request_without_temperature_when_none():
    client = FakeOpenAIClient(chunks=[chunk(VALID_ACTION_TEXT)])

    output = adapter(client).complete(provider_context())

    assert json.loads(output)["action"] == "submit_result"
    assert len(client.requests) == 1
    request = client.requests[0]
    assert request["stream"] is True
    assert request["model"] == "provider-model"
    assert request["max_tokens"] == 8192
    assert "temperature" not in request
    assert "messages" in request
    assert "secret-key" not in json.dumps(request["messages"], sort_keys=True)


def test_adapter_sends_temperature_when_configured():
    client = FakeOpenAIClient(chunks=[chunk(VALID_ACTION_TEXT)])
    opts = options(temperature=0.2)

    adapter(client, opts=opts).complete(provider_context())

    assert client.requests[0]["temperature"] == 0.2


def test_adapter_accumulates_streaming_delta_content():
    client = FakeOpenAIClient(chunks=[chunk(VALID_ACTION_TEXT[:20]), chunk(None), chunk(VALID_ACTION_TEXT[20:])])

    output = adapter(client).complete(provider_context())

    assert output == VALID_ACTION_TEXT


def test_adapter_prompt_is_task_agnostic_and_uses_invocation_task():
    client = FakeOpenAIClient(chunks=[chunk(VALID_ACTION_TEXT)])
    task = "Use write_file to create work/custom-from-task.txt, then submit_result."

    adapter(client).complete(provider_context(task=task))

    messages = client.requests[0]["messages"]
    serialized = json.dumps(messages, sort_keys=True)
    assert task in serialized
    assert "work/custom-from-task.txt" in serialized
    assert "work/real-provider-output.txt" not in serialized


def test_adapter_includes_observations_without_api_key():
    client = FakeOpenAIClient(chunks=[chunk(VALID_ACTION_TEXT)])
    observations = (
        {"step": 1, "tool": "write_file", "ok": True, "visible": "created", "artifact_ref": "artifact://obs"},
    )

    adapter(client).complete(provider_context(observations=observations))

    messages = client.requests[0]["messages"]
    serialized = json.dumps(messages, sort_keys=True)
    assert "created" in serialized
    assert "artifact://obs" in serialized
    assert "secret-key" not in serialized


def test_adapter_rejects_empty_choices_chunk():
    client = FakeOpenAIClient(chunks=[empty_choices_chunk()])

    with pytest.raises(OpenAICompatibleProviderError, match="stream chunk choices must not be empty"):
        adapter(client).complete(provider_context())


def test_adapter_rejects_missing_delta():
    client = FakeOpenAIClient(chunks=[chunk("ignored", has_delta=False)])

    with pytest.raises(OpenAICompatibleProviderError, match="stream chunk choice delta is required"):
        adapter(client).complete(provider_context())


def test_adapter_rejects_empty_stream_content():
    client = FakeOpenAIClient(chunks=[chunk(None)])

    with pytest.raises(OpenAICompatibleProviderError, match="provider stream completed without content"):
        adapter(client).complete(provider_context())


def test_adapter_rejects_length_finish_reason():
    client = FakeOpenAIClient(chunks=[chunk(VALID_ACTION_TEXT[:10], finish_reason="length")])

    with pytest.raises(OpenAICompatibleProviderError, match="provider response truncated by max_output_tokens"):
        adapter(client).complete(provider_context())


def test_adapter_wraps_sdk_exceptions_without_leaking_api_key():
    client = FakeOpenAIClient(error=RuntimeError("upstream exploded"))

    with pytest.raises(OpenAICompatibleProviderError) as raised:
        adapter(client).complete(provider_context())

    message = str(raised.value)
    assert "provider SDK call failed" in message
    assert "upstream exploded" in message
    assert "secret-key" not in message


def test_adapter_rejects_idle_timeout_between_chunks():
    client = FakeOpenAIClient(chunks=[chunk("{"), chunk("}")])
    clock = FakeClock([0.0, 0.1, 31.0])

    with pytest.raises(OpenAICompatibleProviderError, match="provider stream idle timeout exceeded"):
        adapter(client, clock=clock).complete(provider_context())


def test_adapter_rejects_total_timeout():
    client = FakeOpenAIClient(chunks=[chunk("{"), chunk("}")])
    clock = FakeClock([0.0, 0.1, 3601.0])

    with pytest.raises(OpenAICompatibleProviderError, match="provider total timeout exceeded"):
        adapter(client, clock=clock).complete(provider_context())


def test_options_reject_invalid_values():
    with pytest.raises(ValueError, match="max_output_tokens must be a positive integer"):
        OpenAICompatibleProviderOptions(
            base_url="https://provider.example/v1",
            api_key="secret-key",
            model="provider-model",
            context_window_tokens=400000,
            max_output_tokens=0,
            stream_idle_timeout_seconds=30.0,
            total_timeout_seconds=3600.0,
        )
```

### Step 2: Run the new tests to verify they fail

Run:

```bash
python -m pytest tests/test_openai_compatible_provider.py -q
```

Expected before implementation:

- FAIL with `ModuleNotFoundError: No module named 'atomic_agent.providers'` or equivalent import error.

### Step 3: Do not edit production code yet

Stop after confirming the tests fail for the expected missing implementation reason.

---

## Task 3: Implement OpenAI-Compatible Provider Adapter

**Files:**

- Create: `src/atomic_agent/providers/__init__.py`
- Create: `src/atomic_agent/providers/openai_compatible.py`
- Test: `tests/test_openai_compatible_provider.py`

### Step 1: Create provider package exports

Create `src/atomic_agent/providers/__init__.py`:

```python
from atomic_agent.providers.openai_compatible import (
    OpenAICompatibleProviderAdapter,
    OpenAICompatibleProviderError,
    OpenAICompatibleProviderOptions,
)

__all__ = [
    "OpenAICompatibleProviderAdapter",
    "OpenAICompatibleProviderError",
    "OpenAICompatibleProviderOptions",
]
```

### Step 2: Create the adapter implementation

Create `src/atomic_agent/providers/openai_compatible.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
import json
import math
import time
from typing import Any, Callable

from atomic_agent.agent_loop import ProviderContext


class OpenAICompatibleProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class OpenAICompatibleProviderOptions:
    base_url: str
    api_key: str
    model: str
    context_window_tokens: int
    max_output_tokens: int
    stream_idle_timeout_seconds: float
    total_timeout_seconds: float
    temperature: float | None = None
    provider_label: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty_string(self.base_url, "base_url")
        _require_non_empty_string(self.api_key, "api_key")
        _require_non_empty_string(self.model, "model")
        _require_positive_int(self.context_window_tokens, "context_window_tokens")
        _require_positive_int(self.max_output_tokens, "max_output_tokens")
        _require_positive_number(self.stream_idle_timeout_seconds, "stream_idle_timeout_seconds")
        _require_positive_number(self.total_timeout_seconds, "total_timeout_seconds")
        if self.stream_idle_timeout_seconds > self.total_timeout_seconds:
            raise ValueError("stream_idle_timeout_seconds must be less than or equal to total_timeout_seconds")
        if self.temperature is not None:
            _require_finite_number(self.temperature, "temperature")
        if self.provider_label is not None:
            _require_non_empty_string(self.provider_label, "provider_label")


class OpenAICompatibleProviderAdapter:
    def __init__(
        self,
        options: OpenAICompatibleProviderOptions,
        client: Any | None = None,
        clock: Callable[[], float] | None = None,
    ):
        self.options = options
        self._client = client
        self._clock = clock or time.monotonic

    def complete(self, context: ProviderContext) -> str:
        started_at = self._read_clock("before provider request")
        last_chunk_at = started_at
        request = self._request_payload(context)
        try:
            stream = self._client_or_create().chat.completions.create(**request)
        except Exception as error:
            raise OpenAICompatibleProviderError(f"provider SDK call failed: {_safe_error_message(error)}") from error

        parts: list[str] = []
        try:
            for chunk in stream:
                now = self._read_clock("while reading provider stream")
                self._check_total_timeout(started_at, now)
                self._check_idle_timeout(last_chunk_at, now)
                last_chunk_at = now
                parts.append(self._content_from_chunk(chunk))
        except OpenAICompatibleProviderError:
            raise
        except Exception as error:
            raise OpenAICompatibleProviderError(f"provider stream read failed: {_safe_error_message(error)}") from error

        output = "".join(parts)
        if output == "":
            raise OpenAICompatibleProviderError("provider stream completed without content")
        return output

    def _client_or_create(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            from openai import OpenAI
        except ImportError as error:
            raise OpenAICompatibleProviderError(
                "openai package is required for OpenAICompatibleProviderAdapter; install with `python -m pip install \".[real-provider]\"`"
            ) from error
        return OpenAI(base_url=self.options.base_url, api_key=self.options.api_key, timeout=self.options.total_timeout_seconds)

    def _request_payload(self, context: ProviderContext) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.options.model,
            "messages": self._messages(context),
            "stream": True,
            "max_tokens": self.options.max_output_tokens,
        }
        if self.options.temperature is not None:
            payload["temperature"] = self.options.temperature
        return payload

    def _messages(self, context: ProviderContext) -> list[dict[str, str]]:
        invocation = context.invocation
        protocol = {
            "action_envelope": {
                "action_id": "stable unique string",
                "action": "one enabled tool name",
                "reason_summary": "short reason",
                "input": "tool-specific object",
            },
            "rules": [
                "Return exactly one JSON object and no markdown.",
                "Do not wrap the JSON in code fences.",
                "Do not return shell command strings.",
                "Use run_command only with command_id.",
                "Only request tools listed in invocation.tools.",
                "Use submit_result when the task is complete.",
            ],
        }
        task_payload = {
            "task": invocation.task,
            "step": context.step,
            "tools": invocation.tools,
            "allowed_write_set": invocation.allowed_write_set,
            "output_requirements": invocation.output_requirements,
            "provider_capabilities": {
                "provider": "openai-compatible",
                "provider_label": self.options.provider_label,
                "model": self.options.model,
                "context_window_tokens": self.options.context_window_tokens,
                "max_output_tokens": self.options.max_output_tokens,
            },
            "previous_observations": list(context.observations),
        }
        return [
            {"role": "system", "content": json.dumps(protocol, sort_keys=True, ensure_ascii=False)},
            {"role": "user", "content": json.dumps(task_payload, sort_keys=True, ensure_ascii=False)},
        ]

    def _content_from_chunk(self, chunk: Any) -> str:
        choices = getattr(chunk, "choices", None)
        if not isinstance(choices, list) or not choices:
            raise OpenAICompatibleProviderError("stream chunk choices must not be empty")
        choice = choices[0]
        finish_reason = getattr(choice, "finish_reason", None)
        if finish_reason == "length":
            raise OpenAICompatibleProviderError("provider response truncated by max_output_tokens")
        delta = getattr(choice, "delta", None)
        if delta is None:
            raise OpenAICompatibleProviderError("stream chunk choice delta is required")
        content = getattr(delta, "content", None)
        if content is None:
            return ""
        if not isinstance(content, str):
            raise OpenAICompatibleProviderError("stream chunk delta content must be a string or None")
        return content

    def _read_clock(self, context: str) -> float:
        try:
            reading = self._clock()
        except Exception as error:
            raise OpenAICompatibleProviderError(f"provider timeout clock failed {context}: {_safe_error_message(error)}") from error
        if not isinstance(reading, int | float) or isinstance(reading, bool) or not math.isfinite(reading):
            raise OpenAICompatibleProviderError("provider timeout clock must return a finite number")
        return float(reading)

    def _check_idle_timeout(self, previous_at: float, now: float) -> None:
        if now < previous_at:
            raise OpenAICompatibleProviderError("provider timeout clock must be monotonic")
        if now - previous_at > self.options.stream_idle_timeout_seconds:
            raise OpenAICompatibleProviderError("provider stream idle timeout exceeded")

    def _check_total_timeout(self, started_at: float, now: float) -> None:
        if now < started_at:
            raise OpenAICompatibleProviderError("provider timeout clock must be monotonic")
        if now - started_at > self.options.total_timeout_seconds:
            raise OpenAICompatibleProviderError("provider total timeout exceeded")


def _require_non_empty_string(value: object, field_name: str) -> None:
    if not isinstance(value, str) or value == "":
        raise ValueError(f"{field_name} must be a non-empty string")


def _require_positive_int(value: object, field_name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer")


def _require_positive_number(value: object, field_name: str) -> None:
    _require_finite_number(value, field_name)
    if float(value) <= 0:
        raise ValueError(f"{field_name} must be a positive number")


def _require_finite_number(value: object, field_name: str) -> None:
    if not isinstance(value, int | float) or isinstance(value, bool) or not math.isfinite(value):
        raise ValueError(f"{field_name} must be a finite number")


def _safe_error_message(error: Exception) -> str:
    message = str(error) or error.__class__.__name__
    return message.replace("\n", " ")
```

### Step 3: Run adapter unit tests

Run:

```bash
python -m pytest tests/test_openai_compatible_provider.py -q
```

Expected:

- PASS.
- No network.
- No credentials required.

### Step 4: Run base tests

Run:

```bash
python -m pytest -q
```

Expected:

- PASS.
- No real provider network call.

### Step 5: Commit only if the user explicitly requested commits

Do not commit by default. If the user explicitly asks to commit, use:

```bash
git add src/atomic_agent/providers tests/test_openai_compatible_provider.py
git commit -m "feat: 实现OpenAI兼容供应商适配器"
```

---

## Task 4: Write Minimal Real Provider Loop CLI Tests

**Files:**

- Create: `tests/test_minimal_real_provider_loop_example.py`
- Later implementation: `src/atomic_agent/examples/minimal_real_provider_loop.py`

### Step 1: Create the failing CLI test file

Create `tests/test_minimal_real_provider_loop_example.py` with this content:

```python
import json
import os
from pathlib import Path
import subprocess
import sys


PYTHON = Path(sys.executable).resolve()
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
SECRET = "test-secret-key-should-not-leak"


def make_paths(tmp_path):
    base = tmp_path / "real-provider-example"
    return {
        "workspace": base / "workspace",
        "event_stream": base / "events" / "events.jsonl",
        "artifact_root": base / "artifacts",
        "result": base / "result.json",
    }


def run_example(paths, env_overrides=None, extra_args=None):
    env = dict(os.environ)
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(SRC_ROOT) if not existing_pythonpath else f"{SRC_ROOT}{os.pathsep}{existing_pythonpath}"
    if env_overrides:
        env.update(env_overrides)
    args = [
        str(PYTHON),
        "-m",
        "atomic_agent.examples.minimal_real_provider_loop",
        "--run-id",
        "real_provider_example",
        "--workspace",
        str(paths["workspace"]),
        "--event-stream",
        str(paths["event_stream"]),
        "--artifact-root",
        str(paths["artifact_root"]),
        "--result",
        str(paths["result"]),
        "--base-url",
        "https://provider.example/v1",
        "--api-key-env",
        "ATOMIC_AGENT_TEST_REAL_PROVIDER_API_KEY",
        "--model",
        "provider-model",
        "--context-window-tokens",
        "400000",
        "--max-output-tokens",
        "8192",
        "--stream-idle-timeout-seconds",
        "30",
        "--total-timeout-seconds",
        "3600",
        "--max-steps",
        "4",
    ]
    if extra_args:
        args.extend(extra_args)
    return subprocess.run(args, cwd=PROJECT_ROOT, env=env, text=True, capture_output=True, check=False)


def test_minimal_real_provider_loop_refuses_existing_result_file(tmp_path):
    paths = make_paths(tmp_path)
    paths["result"].parent.mkdir(parents=True)
    paths["result"].write_text("keep", encoding="utf-8")

    completed = run_example(paths, env_overrides={"ATOMIC_AGENT_TEST_REAL_PROVIDER_API_KEY": SECRET})

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert paths["result"].read_text(encoding="utf-8") == "keep"
    assert SECRET not in completed.stderr
    error_payload = json.loads(completed.stderr)
    assert error_payload["status"] == "failed"
    assert "result path already exists" in error_payload["error"]


def test_minimal_real_provider_loop_refuses_non_empty_artifact_root(tmp_path):
    paths = make_paths(tmp_path)
    paths["artifact_root"].mkdir(parents=True)
    (paths["artifact_root"] / "old.txt").write_text("old", encoding="utf-8")

    completed = run_example(paths, env_overrides={"ATOMIC_AGENT_TEST_REAL_PROVIDER_API_KEY": SECRET})

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert (paths["artifact_root"] / "old.txt").read_text(encoding="utf-8") == "old"
    assert SECRET not in completed.stderr
    error_payload = json.loads(completed.stderr)
    assert error_payload["status"] == "failed"
    assert "artifact root must be empty" in error_payload["error"]


def test_minimal_real_provider_loop_refuses_existing_workspace_output(tmp_path):
    paths = make_paths(tmp_path)
    output_path = paths["workspace"] / "work" / "real-provider-output.txt"
    output_path.parent.mkdir(parents=True)
    output_path.write_text("keep", encoding="utf-8")

    completed = run_example(paths, env_overrides={"ATOMIC_AGENT_TEST_REAL_PROVIDER_API_KEY": SECRET})

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert output_path.read_text(encoding="utf-8") == "keep"
    assert SECRET not in completed.stderr
    error_payload = json.loads(completed.stderr)
    assert error_payload["status"] == "failed"
    assert "workspace output path already exists" in error_payload["error"]


def test_minimal_real_provider_loop_requires_named_api_key_env(tmp_path):
    paths = make_paths(tmp_path)

    completed = run_example(paths, env_overrides={"ATOMIC_AGENT_TEST_REAL_PROVIDER_API_KEY": ""})

    assert completed.returncode == 2
    assert completed.stdout == ""
    error_payload = json.loads(completed.stderr)
    assert error_payload["status"] == "failed"
    assert "environment variable ATOMIC_AGENT_TEST_REAL_PROVIDER_API_KEY must be set" in error_payload["error"]


def test_minimal_real_provider_loop_writes_failed_result_without_leaking_api_key(tmp_path):
    paths = make_paths(tmp_path)

    completed = run_example(paths, env_overrides={"ATOMIC_AGENT_TEST_REAL_PROVIDER_API_KEY": SECRET})

    assert completed.returncode == 1
    assert SECRET not in completed.stdout
    assert SECRET not in completed.stderr
    assert paths["result"].exists()
    payload = json.loads(paths["result"].read_text(encoding="utf-8"))
    assert payload["status"] == "failed"
    assert SECRET not in json.dumps(payload, sort_keys=True)
```

### Step 2: Run the CLI tests to verify they fail for missing module

Run:

```bash
python -m pytest tests/test_minimal_real_provider_loop_example.py -q
```

Expected before implementation:

- FAIL because `atomic_agent.examples.minimal_real_provider_loop` does not exist.

### Step 3: Do not implement CLI yet

Stop after confirming the tests fail for the expected missing entrypoint reason.

---

## Task 5: Implement Minimal Real Provider Loop CLI

**Files:**

- Create: `src/atomic_agent/examples/minimal_real_provider_loop.py`
- Test: `tests/test_minimal_real_provider_loop_example.py`

### Step 1: Create the CLI implementation

Create `src/atomic_agent/examples/minimal_real_provider_loop.py` with this content:

```python
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import sys
import time
from typing import Sequence

from atomic_agent.agent_loop import AgentLoop, AgentLoopConfig, AgentLoopDependencies
from atomic_agent.artifacts import ArtifactWriter, ArtifactWriterConfig
from atomic_agent.command_tools import CommandPolicy, CommandToolConfig, CommandTools
from atomic_agent.event_recorder import EventRecorder, EventRecorderConfig
from atomic_agent.filesystem_tools import FilesystemToolConfig, FilesystemTools
from atomic_agent.models import AgentInvocation, AgentRunResult, AgentRunStatus
from atomic_agent.path_guard import WorkspacePathGuard
from atomic_agent.providers.openai_compatible import OpenAICompatibleProviderAdapter, OpenAICompatibleProviderOptions


WORKSPACE_OUTPUT_PATH = "work/real-provider-output.txt"


class ExampleInputError(ValueError):
    pass


@dataclass(frozen=True)
class ExamplePaths:
    workspace: Path
    event_stream: Path
    artifact_root: Path
    result: Path


@dataclass(frozen=True)
class CliProviderConfig:
    base_url: str
    api_key: str
    model: str
    context_window_tokens: int
    max_output_tokens: int
    stream_idle_timeout_seconds: float
    total_timeout_seconds: float
    max_steps: int
    temperature: float | None
    provider_label: str | None


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        paths = ExamplePaths(
            workspace=resolve_cli_path(args.workspace),
            event_stream=resolve_cli_path(args.event_stream),
            artifact_root=resolve_cli_path(args.artifact_root),
            result=resolve_cli_path(args.result),
        )
        provider_config = provider_config_from_args(args)
        prepare_paths(paths)
    except ExampleInputError as error:
        print_failure(str(error))
        return 2

    result = run_example(args.run_id, paths, provider_config)
    write_result(paths.result, result)
    print_success(paths, result)
    return 0 if result.status == AgentRunStatus.COMPLETED else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the atomic-agent minimal OpenAI-compatible real provider loop gate.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--event-stream", required=True)
    parser.add_argument("--artifact-root", required=True)
    parser.add_argument("--result", required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--api-key-env", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--context-window-tokens", required=True, type=parse_positive_int)
    parser.add_argument("--max-output-tokens", required=True, type=parse_positive_int)
    parser.add_argument("--stream-idle-timeout-seconds", required=True, type=parse_positive_float)
    parser.add_argument("--total-timeout-seconds", required=True, type=parse_positive_float)
    parser.add_argument("--max-steps", required=True, type=parse_positive_int)
    parser.add_argument("--temperature", type=parse_float_or_none, default=None)
    parser.add_argument("--provider-label", default=None)
    return parser


def parse_positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be a positive integer") from error
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def parse_positive_float(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be a positive number") from error
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive number")
    return parsed


def parse_float_or_none(value: str) -> float | None:
    if value == "":
        return None
    try:
        return float(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be a number or empty string") from error


def resolve_cli_path(value: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ExampleInputError("path arguments must be non-empty strings")
    return Path(value).expanduser().absolute()


def provider_config_from_args(args: argparse.Namespace) -> CliProviderConfig:
    api_key_env = args.api_key_env
    if not isinstance(api_key_env, str) or api_key_env == "":
        raise ExampleInputError("api key environment variable name must be a non-empty string")
    api_key = os.environ.get(api_key_env)
    if not api_key:
        raise ExampleInputError(f"environment variable {api_key_env} must be set")
    if args.provider_label is not None and args.provider_label == "":
        raise ExampleInputError("provider label must be non-empty when provided")
    return CliProviderConfig(
        base_url=args.base_url,
        api_key=api_key,
        model=args.model,
        context_window_tokens=args.context_window_tokens,
        max_output_tokens=args.max_output_tokens,
        stream_idle_timeout_seconds=args.stream_idle_timeout_seconds,
        total_timeout_seconds=args.total_timeout_seconds,
        max_steps=args.max_steps,
        temperature=args.temperature,
        provider_label=args.provider_label,
    )


def prepare_paths(paths: ExamplePaths) -> None:
    workspace_output = paths.workspace / WORKSPACE_OUTPUT_PATH
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


def run_example(run_id: str, paths: ExamplePaths, provider_config: CliProviderConfig) -> AgentRunResult:
    invocation = build_invocation(paths, provider_config)
    loop = build_loop(run_id, paths, provider_config)
    return loop.run(invocation)


def build_invocation(paths: ExamplePaths, provider_config: CliProviderConfig) -> AgentInvocation:
    provider_profile = {
        "provider": "openai-compatible",
        "model": provider_config.model,
        "context_window_tokens": provider_config.context_window_tokens,
        "max_output_tokens": provider_config.max_output_tokens,
        "stream_idle_timeout_seconds": provider_config.stream_idle_timeout_seconds,
        "total_timeout_seconds": provider_config.total_timeout_seconds,
    }
    if provider_config.provider_label is not None:
        provider_profile["provider_label"] = provider_config.provider_label
    else:
        provider_profile["base_url"] = provider_config.base_url
    return AgentInvocation(
        invocation_id="inv_minimal_real_provider_example",
        task=(
            f"Use write_file to create {WORKSPACE_OUTPUT_PATH} with a short confirmation that the real provider gate ran. "
            f"After the write succeeds, call submit_result with produced_paths containing exactly {WORKSPACE_OUTPUT_PATH}."
        ),
        workspace_root=str(paths.workspace),
        allowed_write_set=["work/"],
        tools=["write_file", "submit_result"],
        permission_policy={"policy_ref": "policy://examples/minimal-real-provider-loop"},
        provider_profile=provider_profile,
        budgets={
            "max_steps": provider_config.max_steps,
            "max_parse_failures": 1,
            "max_observation_chars": 10000,
            "max_wall_seconds": provider_config.total_timeout_seconds + 5.0,
        },
        output_requirements={"summary": True, "event_stream": True, "artifacts": True},
        metadata={"example": "minimal_real_provider_loop"},
    )


def build_loop(run_id: str, paths: ExamplePaths, provider_config: CliProviderConfig) -> AgentLoop:
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
        CommandPolicy({}),
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
    provider = OpenAICompatibleProviderAdapter(
        options=OpenAICompatibleProviderOptions(
            base_url=provider_config.base_url,
            api_key=provider_config.api_key,
            model=provider_config.model,
            context_window_tokens=provider_config.context_window_tokens,
            max_output_tokens=provider_config.max_output_tokens,
            stream_idle_timeout_seconds=provider_config.stream_idle_timeout_seconds,
            total_timeout_seconds=provider_config.total_timeout_seconds,
            temperature=provider_config.temperature,
            provider_label=provider_config.provider_label,
        )
    )
    return AgentLoop(
        AgentLoopConfig(run_id=run_id),
        AgentLoopDependencies(
            provider=provider,
            filesystem_tools=filesystem_tools,
            command_tools=command_tools,
            event_recorder=recorder,
            artifact_writer=artifact_writer,
            runtime_clock=time.monotonic,
        ),
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

### Step 2: Run CLI unit tests

Run:

```bash
python -m pytest tests/test_minimal_real_provider_loop_example.py -q
```

Expected:

- PASS.
- No credential value appears in stdout, stderr, or result JSON.
- No existing result/artifact/workspace output is overwritten.

### Step 3: Run adapter tests again

Run:

```bash
python -m pytest tests/test_openai_compatible_provider.py -q
```

Expected:

- PASS.

### Step 4: Run base tests

Run:

```bash
python -m pytest -q
```

Expected:

- PASS.
- No real provider network call.

### Step 5: Commit only if the user explicitly requested commits

Do not commit by default. If the user explicitly asks to commit, use:

```bash
git add src/atomic_agent/examples/minimal_real_provider_loop.py tests/test_minimal_real_provider_loop_example.py
git commit -m "feat: 添加真实供应商最小循环入口"
```

---

## Task 6: Write Default-Skipped Real Provider Integration Gate

**Files:**

- Create: `tests/test_real_provider_integration.py`

### Step 1: Create the integration test

Create `tests/test_real_provider_integration.py` with this content:

```python
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from atomic_agent.evidence import build_evidence_summary, verify_event_stream
from atomic_agent.models import AgentRunResult


PYTHON = Path(sys.executable).resolve()
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
REQUIRED_ENV = (
    "ATOMIC_AGENT_REAL_PROVIDER_BASE_URL",
    "ATOMIC_AGENT_REAL_PROVIDER_API_KEY",
    "ATOMIC_AGENT_REAL_PROVIDER_MODEL",
)


def require_real_provider_enabled():
    if os.environ.get("ATOMIC_AGENT_RUN_REAL_PROVIDER") != "1":
        pytest.skip("set ATOMIC_AGENT_RUN_REAL_PROVIDER=1 to run real provider gate")
    missing = [name for name in REQUIRED_ENV if not os.environ.get(name)]
    if missing:
        pytest.fail("missing required real provider test configuration: " + ", ".join(missing))


def env_value(name, default):
    return os.environ.get(name, default)


def run_real_provider_gate(tmp_path):
    base = tmp_path / "real-provider-gate"
    workspace = base / "workspace"
    event_stream = base / "events" / "events.jsonl"
    artifact_root = base / "artifacts"
    result = base / "result.json"
    env = dict(os.environ)
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(SRC_ROOT) if not existing_pythonpath else f"{SRC_ROOT}{os.pathsep}{existing_pythonpath}"
    env["ATOMIC_AGENT_REAL_PROVIDER_GATE_API_KEY"] = env["ATOMIC_AGENT_REAL_PROVIDER_API_KEY"]
    args = [
        str(PYTHON),
        "-m",
        "atomic_agent.examples.minimal_real_provider_loop",
        "--run-id",
        "real_provider_gate",
        "--workspace",
        str(workspace),
        "--event-stream",
        str(event_stream),
        "--artifact-root",
        str(artifact_root),
        "--result",
        str(result),
        "--base-url",
        env["ATOMIC_AGENT_REAL_PROVIDER_BASE_URL"],
        "--api-key-env",
        "ATOMIC_AGENT_REAL_PROVIDER_GATE_API_KEY",
        "--model",
        env["ATOMIC_AGENT_REAL_PROVIDER_MODEL"],
        "--context-window-tokens",
        env_value("ATOMIC_AGENT_REAL_PROVIDER_CONTEXT_WINDOW_TOKENS", "400000"),
        "--max-output-tokens",
        env_value("ATOMIC_AGENT_REAL_PROVIDER_MAX_OUTPUT_TOKENS", "8192"),
        "--stream-idle-timeout-seconds",
        env_value("ATOMIC_AGENT_REAL_PROVIDER_STREAM_IDLE_TIMEOUT_SECONDS", "30"),
        "--total-timeout-seconds",
        env_value("ATOMIC_AGENT_REAL_PROVIDER_TOTAL_TIMEOUT_SECONDS", "3600"),
        "--max-steps",
        env_value("ATOMIC_AGENT_REAL_PROVIDER_MAX_STEPS", "4"),
    ]
    temperature = os.environ.get("ATOMIC_AGENT_REAL_PROVIDER_TEMPERATURE")
    if temperature is not None:
        args.extend(["--temperature", temperature])
    provider_label = os.environ.get("ATOMIC_AGENT_REAL_PROVIDER_LABEL")
    if provider_label:
        args.extend(["--provider-label", provider_label])
    completed = subprocess.run(args, cwd=PROJECT_ROOT, env=env, text=True, capture_output=True, check=False)
    return completed, result, event_stream


def read_events(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def event_types(events):
    return [event["type"] for event in events]


def failure_text(completed, result):
    pieces = [completed.stdout, completed.stderr]
    if result.exists():
        pieces.append(result.read_text(encoding="utf-8"))
    return "\n".join(pieces)


def assert_not_environment_or_harness_failure(completed, result):
    text = failure_text(completed, result).lower()
    rejected_fragments = (
        "environment variable",
        "api key",
        "apikey",
        "auth",
        "unauthorized",
        "forbidden",
        "dns",
        "connection",
        "connectivity",
        "network",
        "base url",
        "idle timeout",
        "total timeout",
    )
    matches = [fragment for fragment in rejected_fragments if fragment in text]
    assert not matches, "environment/provider availability failure cannot pass real provider gate: " + ", ".join(matches)


@pytest.mark.real_provider
def test_real_provider_minimal_integration_gate(tmp_path):
    require_real_provider_enabled()

    completed, result_path, event_stream_path = run_real_provider_gate(tmp_path)

    assert result_path.exists(), completed.stderr
    assert event_stream_path.exists(), completed.stderr
    result_payload = json.loads(result_path.read_text(encoding="utf-8"))
    result = AgentRunResult.model_validate(result_payload)
    integrity = verify_event_stream(event_stream_path, expected_events_hash=result.events_hash)
    assert integrity["ok"] is True, integrity
    events = read_events(event_stream_path)
    types = event_types(events)
    assert types[-1] in {"run.completed", "run.failed"}

    if "provider.turn.completed" in types and "action.parsed" in types:
        if result.status.value == "completed":
            summary = build_evidence_summary(result, event_stream_path)
            assert summary["event_stream"]["integrity"]["ok"] is True
            assert summary["provider_attempts"]
            assert completed.returncode == 0
            lineage = summary["source_inventory_lineage"]
            if lineage:
                assert lineage[0]["lineage_status"] in {"traceable", "missing_workspace_mutation"}
            return

        assert result.status.value == "failed"
        assert completed.returncode == 1
        assert_not_environment_or_harness_failure(completed, result_path)
        return

    if "provider.turn.failed" in types or "action.rejected" in types:
        assert result.status.value == "failed"
        assert completed.returncode == 1
        assert_not_environment_or_harness_failure(completed, result_path)
        text = failure_text(completed, result_path).lower()
        accepted_fragments = (
            "provider response",
            "provider stream completed without content",
            "stream chunk",
            "truncated by max_output_tokens",
            "action parse",
            "invalid json",
            "action_parse_failed",
        )
        assert any(fragment in text for fragment in accepted_fragments), text
        return

    pytest.fail("real provider gate did not reach an accepted Outcome A, B, or C")
```

### Step 2: Run integration test without enabling env var

Run:

```bash
python -m pytest tests/test_real_provider_integration.py -q
```

Expected:

- SKIPPED with message requiring `ATOMIC_AGENT_RUN_REAL_PROVIDER=1`.

### Step 3: Run base tests

Run:

```bash
python -m pytest -q
```

Expected:

- PASS.
- The real provider integration test remains skipped unless explicitly enabled.

### Step 4: Commit only if the user explicitly requested commits

Do not commit by default. If the user explicitly asks to commit, use:

```bash
git add tests/test_real_provider_integration.py
git commit -m "test: 添加真实供应商集成门禁"
```

---

## Task 7: Run the Real Provider Gate Manually or Nightly

**Files:**

- Local only: `.env.real-provider-test-p2-002-task7`
- Uses: `tests/test_real_provider_integration.py`

### Step 1: Install optional dependencies if needed

Run:

```bash
python -m pip install ".[test,real-provider]"
```

Expected:

- `pytest` and `openai` are installed in the active environment.

### Step 2: Prepare the local ignored provider config file

Use `.env.real-provider-test-p2-002-task7` for this task's manual provider config. This file is local-only and must not become the project-level provider configuration contract; future production invocation should pass provider information explicitly through the caller.

The repository already ignores `.env.*`, so `.env.real-provider-test-p2-002-task7` must remain untracked. Verify before writing any secret:

```bash
git check-ignore .env.real-provider-test-p2-002-task7
```

Expected:

- Output includes `.env.real-provider-test-p2-002-task7`.

Create the file locally with shell-compatible `KEY=value` lines. Do not commit this file and do not paste the real API key into tracked docs:

```bash
cat > .env.real-provider-test-p2-002-task7 <<'EOF'
ATOMIC_AGENT_REAL_PROVIDER_BASE_URL=<provider-base-url>
ATOMIC_AGENT_REAL_PROVIDER_API_KEY=<real-api-key>
ATOMIC_AGENT_REAL_PROVIDER_MODEL=<provider-model>

# Optional config（可选配置）
ATOMIC_AGENT_REAL_PROVIDER_CONTEXT_WINDOW_TOKENS=400000
ATOMIC_AGENT_REAL_PROVIDER_MAX_OUTPUT_TOKENS=128000
ATOMIC_AGENT_REAL_PROVIDER_STREAM_IDLE_TIMEOUT_SECONDS=30
ATOMIC_AGENT_REAL_PROVIDER_TOTAL_TIMEOUT_SECONDS=3600
ATOMIC_AGENT_REAL_PROVIDER_MAX_STEPS=100
ATOMIC_AGENT_REAL_PROVIDER_TEMPERATURE=0.7
#ATOMIC_AGENT_REAL_PROVIDER_LABEL=openai-gpt4o-mini
EOF
```

Expected:

- File exists locally.
- File is ignored by git.
- No secret is written to tracked files, stdout, stderr, artifacts, or docs.

### Step 3: Run explicit real provider gate with local config

Run with the local ignored provider config:

```bash
set -a
source .env.real-provider-test-p2-002-task7
set +a
ATOMIC_AGENT_RUN_REAL_PROVIDER=1 python -m pytest tests/test_real_provider_integration.py -m real_provider -q
```

Expected with valid provider config:

- PASS for one accepted outcome:
  - Outcome A: full action-loop success（完整动作循环成功）
  - Outcome B: valid provider action but task behavior varies（供应商动作合法但模型行为偏离）
  - Outcome C: provider response fail-closed（供应商响应失败关闭）

Expected rejected outcomes:

- Authentication failure（认证失败）: FAIL.
- Missing API key（缺失密钥）: FAIL.
- DNS/connectivity/base URL failure（DNS / 连接 / 基础 URL 失败）: FAIL.
- Stream idle timeout（流空闲超时）: FAIL.
- Total timeout（总超时）: FAIL.
- Harness misconfiguration（测试驱动配置错误）: FAIL.

### Step 4: Record manual verification result in the final response

Do not write a project log unless the user requests one or a P-stage exit review is being performed. Report:

- exact command shape run, without printing secret values,
- whether it passed, skipped, or failed,
- accepted outcome category,
- event stream path if available,
- result path if available.

---

## Task 8: Update README After Verification

**Files:**

- Modify: `README.md`

### Preconditions

Do this only after:

```bash
python -m pytest -q
```

passes, and:

```bash
python -m pytest tests/test_real_provider_integration.py -q
```

skips by default, and the explicit real provider gate has either passed in the local/manual environment or is clearly documented as manual/nightly with strict enablement requirements.

### Step 1: Add a README section after the fake provider minimal example section

Add:

```markdown
## 4. 如何运行真实 provider gate（手动/夜间）

除 deterministic fake provider loop（确定性假模型供应商循环）外，本仓库还提供默认禁用的 OpenAI-compatible real provider gate（OpenAI 兼容真实模型供应商门禁）。它用于验证真实 provider streaming（流式响应）、provider-agnostic `AgentAction`（供应商无关智能体动作）、受控工具执行、JSONL event stream（JSONL 事件流）和 evidence summary（证据摘要）链路。

该门禁不同于 fake provider minimal example（假供应商最小示例）：

- fake provider example 默认本地运行、确定性、无网络。
- real provider gate 必须显式提供 OpenAI-compatible provider（OpenAI 兼容供应商）配置和 API key。
- real provider gate 不进入默认 base CI（基础持续集成）联网路径。
- provider output（模型输出）不能单独作为 implementation evidence（实现证据）；必须结合 tool attempt（工具尝试）、workspace mutation（工作区变更）、event stream integrity（事件流完整性）和 artifact hash（产物哈希）判断。

安装可选依赖：

```bash
python -m pip install ".[test,real-provider]"
```

手动运行 standalone loop（独立循环）：

```bash
rm -rf /tmp/atomic-agent-real-provider
export ATOMIC_AGENT_REAL_PROVIDER_API_KEY="replace-with-real-key"
PYTHONPATH=src python -m atomic_agent.examples.minimal_real_provider_loop \
  --run-id real_provider_example \
  --workspace /tmp/atomic-agent-real-provider/workspace \
  --event-stream /tmp/atomic-agent-real-provider/events/events.jsonl \
  --artifact-root /tmp/atomic-agent-real-provider/artifacts \
  --result /tmp/atomic-agent-real-provider/result.json \
  --base-url https://provider.example/v1 \
  --api-key-env ATOMIC_AGENT_REAL_PROVIDER_API_KEY \
  --model provider-model \
  --context-window-tokens 400000 \
  --max-output-tokens 8192 \
  --stream-idle-timeout-seconds 30 \
  --total-timeout-seconds 3600 \
  --max-steps 4
```

成功时 stdout（标准输出）是 JSON，包含：

```json
{"artifact_root":"/tmp/atomic-agent-real-provider/artifacts","event_stream_path":"/tmp/atomic-agent-real-provider/events/events.jsonl","result_path":"/tmp/atomic-agent-real-provider/result.json","status":"completed","workspace_output_path":"/tmp/atomic-agent-real-provider/workspace/work/real-provider-output.txt"}
```

运行 pytest integration gate（集成门禁）：

```bash
ATOMIC_AGENT_RUN_REAL_PROVIDER=1 \
ATOMIC_AGENT_REAL_PROVIDER_BASE_URL="https://provider.example/v1" \
ATOMIC_AGENT_REAL_PROVIDER_API_KEY="replace-with-real-key" \
ATOMIC_AGENT_REAL_PROVIDER_MODEL="provider-model" \
python -m pytest tests/test_real_provider_integration.py -m real_provider -q
```

未设置 `ATOMIC_AGENT_RUN_REAL_PROVIDER=1` 时，该测试必须 skip（跳过）。认证失败、缺失凭据、网络连接失败、base URL 错误、stream idle timeout（流空闲超时）或 total timeout（总超时）不能算作 gate pass（门禁通过）。
```

### Step 2: Renumber the existing documentation-entry section if needed

If README currently has `## 4. 文档入口在哪里`, renumber it to `## 5. 文档入口在哪里` after inserting the new section.

### Step 3: Run README command sanity check without real provider credentials

Do not run the real provider command unless credentials are provided. Verify only the default test behavior:

```bash
python -m pytest tests/test_real_provider_integration.py -q
```

Expected:

- SKIPPED unless explicitly enabled.

---

## Task 9: Update Testing Strategy After Verification

**Files:**

- Modify: `docs/05-testing/testing-strategy.md`

### Step 1: Locate the existing integration / gate section

Read `docs/05-testing/testing-strategy.md` and add the real provider gate details near existing integration or acceptance testing guidance.

### Step 2: Add this content

```markdown
### Real provider integration gate（真实供应商集成门禁）

P2-002 adds a default-disabled OpenAI-compatible real provider gate（OpenAI 兼容真实供应商门禁）。它只验证最小真实 provider action loop（供应商动作循环），不要求模型完成大型项目。

默认命令：

```bash
python -m pytest tests/test_real_provider_integration.py -q
```

默认结果必须是 skip（跳过），因为未设置：

```text
ATOMIC_AGENT_RUN_REAL_PROVIDER=1
```

显式启用命令：

```bash
ATOMIC_AGENT_RUN_REAL_PROVIDER=1 \
ATOMIC_AGENT_REAL_PROVIDER_BASE_URL="https://provider.example/v1" \
ATOMIC_AGENT_REAL_PROVIDER_API_KEY="replace-with-real-key" \
ATOMIC_AGENT_REAL_PROVIDER_MODEL="provider-model" \
python -m pytest tests/test_real_provider_integration.py -m real_provider -q
```

Required env vars（必需环境变量）：

```text
ATOMIC_AGENT_RUN_REAL_PROVIDER=1
ATOMIC_AGENT_REAL_PROVIDER_BASE_URL
ATOMIC_AGENT_REAL_PROVIDER_API_KEY
ATOMIC_AGENT_REAL_PROVIDER_MODEL
```

Optional env vars（可选环境变量）：

```text
ATOMIC_AGENT_REAL_PROVIDER_CONTEXT_WINDOW_TOKENS=400000
ATOMIC_AGENT_REAL_PROVIDER_MAX_OUTPUT_TOKENS=8192
ATOMIC_AGENT_REAL_PROVIDER_STREAM_IDLE_TIMEOUT_SECONDS=30
ATOMIC_AGENT_REAL_PROVIDER_TOTAL_TIMEOUT_SECONDS=3600
ATOMIC_AGENT_REAL_PROVIDER_MAX_STEPS=4
ATOMIC_AGENT_REAL_PROVIDER_TEMPERATURE=
ATOMIC_AGENT_REAL_PROVIDER_LABEL=
```

Accepted outcomes（可接受结果）：

1. Outcome A：provider stream（供应商流）返回合法 JSON action（JSON 动作），runtime 执行至少一个工具，event stream（事件流）以 `run.completed` 结束，evidence summary（证据摘要）可构建。
2. Outcome B：provider 返回合法 action 但模型行为偏离；event stream integrity（事件流完整性）必须可验证，evidence summary 不得把缺失 lineage（谱系）伪装为 traceable（可追溯）。
3. Outcome C：provider SDK path（SDK 路径）已到达，但 response（响应）为空、截断、无法提取内容或无法解析为 action；runtime 必须 fail closed（失败关闭），event stream integrity 必须可验证。

Rejected outcomes（不可算通过）：

- missing credentials（缺失凭据）
- authentication failure（认证失败）
- DNS / connectivity / base URL failure（DNS / 连接 / 基础 URL 失败）
- stream idle timeout（流空闲超时）
- total timeout（总超时）
- test harness misconfiguration（测试驱动配置错误）

Base CI（基础持续集成）仍使用：

```bash
python -m pytest -q
```

该命令不得要求真实 provider credentials（真实供应商凭据），不得发起真实 provider 网络调用。
```

### Step 3: Run docs-adjacent verification

Run:

```bash
python -m pytest tests/test_real_provider_integration.py -q
```

Expected:

- SKIPPED by default.

---

## Task 10: Mark P2-002 Complete and Archive Active Pointers

**Files:**

- Modify: `docs/04-implementation-backlog/backlog.md`
- Modify: `docs/04-implementation-spec/INDEX.md`
- Modify: `docs/04-implementation-plan/INDEX.md`
- Modify: `docs/INDEX.md`

### Preconditions

Do this only after all applicable verification passes:

```bash
python -m pytest -q
python -m pytest tests/test_real_provider_integration.py -q
```

and explicit real provider gate status has been reported.

### Step 1: Update backlog status

In `docs/04-implementation-backlog/backlog.md`, change P2-002 status from `pending` to `completed`:

```markdown
| P2-002 | 建立 real provider minimal integration gate（真实模型供应商最小集成门禁） | completed | `P2-002-real-provider-minimal-integration-gate-spec.md`, `testing-strategy.md`, `agent-action-protocol.md`, `mvp-acceptance.md`, `roadmap.md` |
```

### Step 2: Update spec index

In `docs/04-implementation-spec/INDEX.md`:

- Remove P2-002 from `Current Active Documents`.
- Add this row to `Completed / Archived Documents` with the actual completion date:

```markdown
| `P2-002-real-provider-minimal-integration-gate-spec.md` | 2026-06-07 | 已实现 P2-002 real provider minimal integration gate（真实模型供应商最小集成门禁），保留为真实供应商集成门禁规格记录 |
```

If completion date differs, use that date.

### Step 3: Update plan index

In `docs/04-implementation-plan/INDEX.md`:

- Remove P2-002 from `Current Active Documents`.
- Add this row to `Completed / Archived Documents` with the actual completion date:

```markdown
| `P2-002-real-provider-minimal-integration-gate-plan.md` | 2026-06-07 | 已实施 P2-002 real provider minimal integration gate（真实模型供应商最小集成门禁），保留为 TDD 实施记录 |
```

If completion date differs, use that date.

### Step 4: Update global docs index

In `docs/INDEX.md`:

- Remove P2-002 spec and plan active draft pointers from the current active documents table after completion.
- Keep `docs/04-implementation-backlog/backlog.md`, `docs/05-testing/testing-strategy.md`, and `docs/06-roadmap/roadmap.md` active.
- If the P2 wave has no remaining non-deferred tasks after P2-002, leave P2 exit gate guidance in backlog as the next planning action rather than inventing new implementation work.

### Step 5: Run final base verification

Run:

```bash
python -m pytest -q
```

Expected:

- PASS.
- No real provider credentials required.
- Real provider integration remains skipped unless explicitly enabled.

### Step 6: Commit only if the user explicitly requested commits

Do not commit by default. If the user explicitly asks to commit, use:

```bash
git add README.md docs/05-testing/testing-strategy.md docs/04-implementation-backlog/backlog.md docs/04-implementation-spec/INDEX.md docs/04-implementation-plan/INDEX.md docs/INDEX.md
git commit -m "docs: 完成P2-002文档收尾"
```

---

## Task 11: Final Verification and Completion Report

**Files:**

- No new files.

### Step 1: Run base gate

Run:

```bash
python -m pytest -q
```

Expected:

- PASS.
- No network.
- No credentials required.

### Step 2: Run default real provider test behavior

Run:

```bash
python -m pytest tests/test_real_provider_integration.py -q
```

Expected:

- SKIPPED unless `ATOMIC_AGENT_RUN_REAL_PROVIDER=1`.

### Step 3: Run explicit real provider gate if credentials are available

Run only when valid config is available:

```bash
ATOMIC_AGENT_RUN_REAL_PROVIDER=1 \
ATOMIC_AGENT_REAL_PROVIDER_BASE_URL="https://provider.example/v1" \
ATOMIC_AGENT_REAL_PROVIDER_API_KEY="replace-with-real-key" \
ATOMIC_AGENT_REAL_PROVIDER_MODEL="provider-model" \
python -m pytest tests/test_real_provider_integration.py -m real_provider -q
```

Expected:

- PASS for Outcome A, B, or C.
- FAIL for auth/network/credential/config/timeout problems.

### Step 4: Report completion truthfully

Final report must include:

- files created/modified,
- commands run,
- exact pass/skip/fail outcomes,
- whether explicit real provider gate was run,
- accepted Outcome A/B/C if run,
- any skipped step and why.

Do not claim real provider capability is verified if only unit tests and default skip behavior were run.

---

## Risks and Mitigations

1. **Streaming idle timeout with sync SDK iterator**  
   The adapter can check idle gaps only between chunks it receives. The SDK/http transport timeout must still be configured with `total_timeout_seconds` to avoid indefinite blocking reads. Tests cover deterministic adapter-level timeout behavior with a fake clock.

2. **Credential leakage**  
   API key is accepted only by adapter constructor or CLI env lookup. It must never enter `AgentInvocation`, prompt messages, event payloads, artifacts, stdout, stderr, docs examples, or test assertion output.

3. **Outcome C boundary**  
   Provider response invalidity can pass as fail-closed only after SDK path was reached. Missing credentials, auth failures, connectivity failures, base URL failures, and timeouts cannot pass.

4. **No scope creep into P2-003**  
   Do not add external coding agent bridge（外部编码智能体桥接）、provider registry（供应商注册表）、multi-provider routing（多供应商路由）、Anthropic/Claude adapter（Anthropic/Claude 供应商适配器）, OpenAI native tool calling（OpenAI 原生工具调用）, Responses API（响应接口）, service runner（服务运行器）, HTTP probe（HTTP 探测）, or browser automation（浏览器自动化）.

5. **No silent fallback**  
   If optional dependency, provider config, stream content, action parsing, or evidence mapping fails, fail clearly. Do not fall back to fake provider, static provider output, non-streaming request, native tool calling, or mocked success.

---

## Self-Review

### Spec Coverage

- OpenAI-compatible only: covered by Tasks 2-7.
- Official OpenAI Python SDK v1 behavior: covered by Task 3.
- Streaming required: covered by Tasks 2-3 and Task 6.
- Explicit provider options: covered by Tasks 2, 3, 5, and 6.
- `temperature=None` omits field: covered by Task 2.
- Task-agnostic adapter: covered by Task 2 and Task 3.
- No native tool calling: covered by Task 3 message/request design.
- Standalone CLI: covered by Tasks 4-5.
- Default skip integration gate: covered by Task 6.
- Base CI unaffected: covered by Tasks 1, 6, and 11.
- Outcome A/B/C semantics: covered by Tasks 6-7.
- Documentation updates: covered by Tasks 8-10.
- No Boardroom governance completion claims: covered by boundaries and final report requirements.

### Placeholder Scan

This plan avoids `TBD`, `TODO`, `implement later`, vague “add tests”, and “similar to” shortcuts. Each code-changing task includes concrete file paths, code blocks, commands, and expected outcomes.

### Type Consistency

- `OpenAICompatibleProviderOptions` is used consistently in tests, adapter implementation, and CLI.
- `OpenAICompatibleProviderAdapter.complete(context: ProviderContext) -> str` matches the existing `ProviderAdapter` protocol.
- CLI uses `WORKSPACE_OUTPUT_PATH = "work/real-provider-output.txt"` consistently.
- Real provider test reads `AgentRunResult`, `verify_event_stream`, and `build_evidence_summary` from existing modules.

---

## Execution Handoff

Plan complete. Recommended execution modes:

1. **Subagent-Driven (recommended)** — use `subagent-driven-development`（子智能体驱动开发） and dispatch a fresh implementation agent per task with review between tasks.
2. **Inline Execution** — use `executing-plans`（执行计划） in this session with checkpoints after each task group.

Do not execute implementation until the user explicitly approves execution.
