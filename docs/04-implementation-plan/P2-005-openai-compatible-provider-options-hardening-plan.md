# P2-005 OpenAI-compatible Provider Options Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose high-impact OpenAI-compatible provider request options explicitly, keep runtime defaults fail-closed and unset by default, and provide a capability-first local/manual profile for Boardroom OS style autonomous agent teams.

**Architecture:** Extend `OpenAICompatibleProviderOptions`（OpenAI 兼容供应商选项） as the single runtime configuration object, map only explicitly configured optional fields into `OpenAICompatibleProviderAdapter._request_payload()`（请求载荷构建函数）, and centralize sanitized `provider_profile`（供应商画像） construction for audit/evidence. CLI/env parsing remains at the example and real-provider gate boundaries, while local `.env.*` files and tracked `.env.template` provide explicit operator profiles instead of hardcoded runtime defaults.

**Tech Stack:** Python 3.11+, dataclasses, argparse, pytest, official OpenAI Python SDK through the existing `OpenAICompatibleProviderAdapter`（OpenAI 兼容供应商适配器）, existing `AgentLoop`（智能体循环）, JSONL event stream（JSONL 事件流）, and project docs/index governance.

---

## Current Context

P2-002 established the default-disabled real provider minimal integration gate（真实供应商最小集成门禁）. P2-004 established the success-only real provider tool gate（真实供应商工具成功门禁）. P2-005 now hardens the provider option path before P2-006 complex real provider atomic task gate（复杂真实供应商原子任务门禁） depends on explicit `reasoning_effort=high`（高推理强度） and audited provider options.

The user-approved approach is **Approach A: capability-first profile + explicit fail-closed provider option path**:

- Runtime core（运行时核心） does not hardcode new provider option defaults.
- `None` means unset（未设置） and must not be sent to provider.
- Local/manual gate config files provide explicit capability-first defaults for Boardroom OS（Boardroom 操作系统） style autonomous agent teams（自治智能体团队）.
- Unsupported explicit provider parameters fail closed（失败关闭） through the existing provider failure path; the runtime must not silently retry after dropping parameters.

---

## File Structure

### Create

- `.env.template`  
  Tracked, sanitized environment template（环境变量模板） for real provider manual/nightly gates. It mirrors the local capability-first profile without real `base_url` or `api_key`.

- `docs/04-implementation-plan/P2-005-openai-compatible-provider-options-hardening-plan.md`  
  This implementation plan（实施计划）.

- `tests/test_minimal_real_provider_loop.py`  
  Focused unit tests（聚焦单元测试） for standalone real provider CLI/env parsing helpers. Create this file instead of adding parser tests to the broader provider adapter test module.

### Modify

- `.gitignore`  
  Keep `.env` and `.env.*` ignored, but explicitly unignore `.env.template` so the template can sync through git.

- `.env.real-provider-test-p2-002-task7`  
  Local git ignored provider config（本地被 Git 忽略的供应商配置）. Change `ATOMIC_AGENT_REAL_PROVIDER_TEMPERATURE` to `0.2` and append P2-005 capability-first defaults. Do not commit this file.

- `src/atomic_agent/providers/openai_compatible.py`  
  Extend `OpenAICompatibleProviderOptions`, validation helpers, sanitized provider profile helper, and request payload mapping.

- `src/atomic_agent/examples/minimal_real_provider_loop.py`  
  Add CLI arguments, parsing helpers, `CliProviderConfig` fields, invocation profile wiring, and provider options wiring.

- `tests/test_openai_compatible_provider.py`  
  Add unit tests for request payload mapping, unset semantics, invalid option validation, and sanitized provider profile behavior.

- `tests/test_real_provider_integration.py`  
  Forward optional P2-005 environment variables to the standalone CLI gate.

- `tests/test_real_provider_tool_success.py`  
  Parse optional P2-005 environment variables directly, build options with them, and use the shared sanitized provider profile helper.

- `README.md`  
  Document P2-005 real provider options and reference `.env.template`.

- `docs/05-testing/testing-strategy.md`  
  Document P2-005 optional env vars, capability-first profile, default skip semantics, fail-closed compatibility behavior, and secret safety.

- `docs/04-implementation-spec/P2-005-openai-compatible-provider-options-hardening-spec.md`  
  Already revised to include the approved capability-first local profile.

- `docs/04-implementation-plan/INDEX.md`  
  Add this plan to `Current Active Documents` while implementation is pending.

- `docs/04-implementation-backlog/backlog.md`  
  Mark P2-005 completed only after implementation and verification pass.

---

## Capability-first Profile

Use these explicit values in local/manual provider config for Boardroom OS style autonomous agent teams:

```dotenv
ATOMIC_AGENT_REAL_PROVIDER_TEMPERATURE=0.2
ATOMIC_AGENT_REAL_PROVIDER_REASONING_EFFORT=high
ATOMIC_AGENT_REAL_PROVIDER_TOP_P=1.0
ATOMIC_AGENT_REAL_PROVIDER_PRESENCE_PENALTY=0.0
ATOMIC_AGENT_REAL_PROVIDER_FREQUENCY_PENALTY=0.0
ATOMIC_AGENT_REAL_PROVIDER_SEED=20260608
ATOMIC_AGENT_REAL_PROVIDER_STOP=
ATOMIC_AGENT_REAL_PROVIDER_RESPONSE_FORMAT_JSON='{"type":"json_object"}'
ATOMIC_AGENT_REAL_PROVIDER_STREAM_OPTIONS_JSON='{"include_usage":true}'
ATOMIC_AGENT_REAL_PROVIDER_SERVICE_TIER=
ATOMIC_AGENT_REAL_PROVIDER_USER=atomic-agent-boardroom-os
ATOMIC_AGENT_REAL_PROVIDER_LABEL=boardroom-os-real-provider
```

Rationale（理由）:

- `temperature=0.2` improves JSON action（JSON 动作） stability without making cost the optimization target.
- `reasoning_effort=high` prioritizes task execution ability for autonomous agent teams.
- `top_p=1.0` avoids unnecessary sampling restriction while keeping the knob explicit.
- penalties remain `0.0` to avoid unexpected behavior in strict action JSON output.
- `seed=20260608` provides best-effort reproducibility for manual/nightly comparison.
- `stop=` stays unset because stop sequences can truncate action JSON.
- `response_format={"type":"json_object"}` asks for JSON object output but does not replace `AgentAction` schema validation.
- `stream_options={"include_usage":true}` requests usage accounting when provider supports it; usage is audit context, not success evidence.
- blank `service_tier` remains unset to avoid provider-specific assumptions.
- `user=atomic-agent-boardroom-os` is a non-secret operator label.

---

## Task 0: Verify Official Documentation Review

**Files:**

- Modify if needed: `docs/04-implementation-spec/P2-005-openai-compatible-provider-options-hardening-spec.md`
- Modify if needed: `docs/04-implementation-plan/P2-005-openai-compatible-provider-options-hardening-plan.md`

**Precondition:** Before implementation, the engineer must manually review the current official OpenAI documentation. This satisfies the P2-005 spec（规格） implementation precondition and prevents implementing stale request parameter names.

- [ ] **Step 1: Confirm Chat Completions API parameter names**

Visit `https://platform.openai.com/docs/api-reference/chat/create` and verify:

- `reasoning_effort` field name for Chat Completions（聊天补全） requests.
- Supported `reasoning_effort` values.
- Whether `max_tokens` remains valid for the target Chat Completions models or whether `max_completion_tokens` is required.
- Whether these P2-005 request options are still accepted by Chat Completions: `top_p`, `presence_penalty`, `frequency_penalty`, `seed`, `stop`, `response_format`, `stream_options`, `service_tier`, and `user`.

Expected:

- If the official parameter name differs from the spec, update the spec before implementation.
- If `max_completion_tokens` is now required for the target model family, update the spec and this plan before changing code.
- Do not implement a model-name guess or compatibility fallback.

- [ ] **Step 2: Confirm reasoning models guide**

Visit `https://platform.openai.com/docs/guides/reasoning` and verify:

- Chat Completions uses `reasoning_effort` while Responses API（响应接口） may use `reasoning.effort`, or document the current naming if it changed.
- Hidden reasoning tokens（隐藏推理 token） behavior and how it affects output caps.
- Model support matrix（模型支持矩阵） for reasoning effort.

Expected:

- P2-005 keeps the Chat Completions streaming path unless an explicit spec update says otherwise.
- If the official guide requires `reasoning.effort` instead of `reasoning_effort` for Chat Completions, stop and revise the spec first.

- [ ] **Step 3: Record review completion in implementation notes**

Add an implementation note near this task before coding:

```markdown
Official documentation review completed on 2026-06-08.

Findings:
- Chat Completions reasoning effort field: `<verified-name>`.
- Output cap field for target model: `<verified-name>`.
- P2-005 optional fields still supported in Chat Completions: `<yes/no with exceptions>`.
- Spec changes required before implementation: `<none or list>`.
```

Expected:

- The note contains no API key, real base URL, account identifier, or provider-private URL.
- Any spec-changing finding is reflected in `docs/04-implementation-spec/P2-005-openai-compatible-provider-options-hardening-spec.md` before runtime code changes.

Implementation note recorded on 2026-06-08:

```markdown
Official documentation review completed on 2026-06-08.

Findings:
- User-provided current OpenAI Responses API（响应接口） example uses nested `reasoning: {"effort": "medium"}`.
- P2-005 keeps the existing OpenAI-compatible Chat Completions streaming（聊天补全流式） path and does not switch to Responses API.
- Runtime option remains semantic `reasoning_effort`（推理强度）. The current implementation maps it to Chat Completions request field `reasoning_effort` only for this adapter path.
- If a future task switches to Responses API, that task must map the same semantic option to nested `reasoning.effort` and update spec/plan first.
- Output cap field for this P2-005 implementation remains `max_tokens`; if target provider/model requires `max_completion_tokens`, stop and revise spec/plan before changing runtime code.
- Spec changes required before implementation: document the Responses API naming difference and keep P2-005 scoped to Chat Completions.
```

---

## Task 1: Lock Spec and Plan Metadata

**Files:**

- Modify: `docs/04-implementation-spec/P2-005-openai-compatible-provider-options-hardening-spec.md`
- Create: `docs/04-implementation-plan/P2-005-openai-compatible-provider-options-hardening-plan.md`
- Modify: `docs/04-implementation-plan/INDEX.md`

- [ ] **Step 1: Verify the P2-005 spec includes the capability-first profile**

Run:

```bash
python - <<'PY'
from pathlib import Path
text = Path('docs/04-implementation-spec/P2-005-openai-compatible-provider-options-hardening-spec.md').read_text(encoding='utf-8')
assert '## Capability-first Local Profile' in text
assert 'ATOMIC_AGENT_REAL_PROVIDER_REASONING_EFFORT=high' in text
assert 'ATOMIC_AGENT_REAL_PROVIDER_TEMPERATURE=0.2' in text
assert 'ATOMIC_AGENT_REAL_PROVIDER_STOP=' in text
PY
```

Expected:

- PASS with no output.

- [ ] **Step 2: Verify this plan is indexed as active**

Run:

```bash
python - <<'PY'
from pathlib import Path
index = Path('docs/04-implementation-plan/INDEX.md').read_text(encoding='utf-8')
assert 'P2-005-openai-compatible-provider-options-hardening-plan.md' in index
assert 'OpenAI-compatible provider options hardening' in index
PY
```

Expected:

- PASS with no output.

---

## Task 2: Add Sanitized Env Template and Local Profile

**Files:**

- Modify: `.gitignore`
- Modify: `.env.real-provider-test-p2-002-task7`
- Create: `.env.template`

- [ ] **Step 1: Update `.gitignore` to allow `.env.template`**

Add this line after `!.env.example`:

```gitignore
!.env.template
```

Expected local check:

```bash
python - <<'PY'
from pathlib import Path
text = Path('.gitignore').read_text(encoding='utf-8')
assert '.env.*' in text
assert '!.env.template' in text
PY
```

- [ ] **Step 2: Update local ignored provider config**

In `.env.real-provider-test-p2-002-task7`, set:

```dotenv
ATOMIC_AGENT_REAL_PROVIDER_TEMPERATURE=0.2
```

Append this block:

```dotenv

# P2-005 OpenAI-compatible provider options
# Capability-first profile for boardroom-os style autonomous agent teams.
ATOMIC_AGENT_REAL_PROVIDER_REASONING_EFFORT=high
ATOMIC_AGENT_REAL_PROVIDER_TOP_P=1.0
ATOMIC_AGENT_REAL_PROVIDER_PRESENCE_PENALTY=0.0
ATOMIC_AGENT_REAL_PROVIDER_FREQUENCY_PENALTY=0.0
ATOMIC_AGENT_REAL_PROVIDER_SEED=20260608
ATOMIC_AGENT_REAL_PROVIDER_STOP=
ATOMIC_AGENT_REAL_PROVIDER_RESPONSE_FORMAT_JSON='{"type":"json_object"}'
ATOMIC_AGENT_REAL_PROVIDER_STREAM_OPTIONS_JSON='{"include_usage":true}'
ATOMIC_AGENT_REAL_PROVIDER_SERVICE_TIER=
ATOMIC_AGENT_REAL_PROVIDER_USER=atomic-agent-boardroom-os
ATOMIC_AGENT_REAL_PROVIDER_LABEL=boardroom-os-real-provider
```

Do not stage or commit `.env.real-provider-test-p2-002-task7` because it contains local secrets.

- [ ] **Step 3: Create `.env.template` with sanitized values**

Create `.env.template` with:

```dotenv
# atomic-agent real provider manual/nightly gate template
# Copy this file to a local git ignored .env.* file and replace placeholders.

ATOMIC_AGENT_REAL_PROVIDER_BASE_URL=https://provider.example/v1
ATOMIC_AGENT_REAL_PROVIDER_API_KEY=replace-with-real-key
ATOMIC_AGENT_REAL_PROVIDER_MODEL=provider-model

# Capability-first defaults for boardroom-os style autonomous agent teams.
ATOMIC_AGENT_REAL_PROVIDER_CONTEXT_WINDOW_TOKENS=400000
ATOMIC_AGENT_REAL_PROVIDER_MAX_OUTPUT_TOKENS=128000
ATOMIC_AGENT_REAL_PROVIDER_STREAM_IDLE_TIMEOUT_SECONDS=30
ATOMIC_AGENT_REAL_PROVIDER_TOTAL_TIMEOUT_SECONDS=3600
ATOMIC_AGENT_REAL_PROVIDER_MAX_STEPS=100
ATOMIC_AGENT_REAL_PROVIDER_TEMPERATURE=0.2
ATOMIC_AGENT_REAL_PROVIDER_REASONING_EFFORT=high
ATOMIC_AGENT_REAL_PROVIDER_TOP_P=1.0
ATOMIC_AGENT_REAL_PROVIDER_PRESENCE_PENALTY=0.0
ATOMIC_AGENT_REAL_PROVIDER_FREQUENCY_PENALTY=0.0
ATOMIC_AGENT_REAL_PROVIDER_SEED=20260608
ATOMIC_AGENT_REAL_PROVIDER_STOP=
ATOMIC_AGENT_REAL_PROVIDER_RESPONSE_FORMAT_JSON='{"type":"json_object"}'
ATOMIC_AGENT_REAL_PROVIDER_STREAM_OPTIONS_JSON='{"include_usage":true}'
ATOMIC_AGENT_REAL_PROVIDER_SERVICE_TIER=
ATOMIC_AGENT_REAL_PROVIDER_USER=atomic-agent-boardroom-os
ATOMIC_AGENT_REAL_PROVIDER_LABEL=boardroom-os-real-provider

# Enable gates explicitly when needed.
ATOMIC_AGENT_RUN_REAL_PROVIDER=
ATOMIC_AGENT_RUN_REAL_PROVIDER_TOOL_SUCCESS=
ATOMIC_AGENT_RUN_REAL_PROVIDER_COMPLEX_TASK=
```

- [ ] **Step 4: Verify template does not contain local secrets**

Run:

```bash
python - <<'PY'
from pathlib import Path
local = Path('.env.real-provider-test-p2-002-task7').read_text(encoding='utf-8')
template = Path('.env.template').read_text(encoding='utf-8')
for key in ['ATOMIC_AGENT_REAL_PROVIDER_BASE_URL', 'ATOMIC_AGENT_REAL_PROVIDER_API_KEY']:
    local_value = ''
    for line in local.splitlines():
        if line.startswith(key + '='):
            local_value = line.split('=', 1)[1]
    assert local_value
    assert local_value not in template
assert 'https://provider.example/v1' in template
assert 'replace-with-real-key' in template
PY
```

Expected:

- PASS with no output.

---

## Task 3: Extend Provider Options and Request Payload

**Files:**

- Modify: `src/atomic_agent/providers/openai_compatible.py`
- Test: `tests/test_openai_compatible_provider.py`

- [ ] **Step 1: Write failing request payload tests**

Add these tests to `tests/test_openai_compatible_provider.py`:

```python
def test_adapter_sends_all_explicit_provider_options():
    client = FakeOpenAIClient(chunks=[chunk(VALID_ACTION_TEXT)])
    opts = options(
        reasoning_effort='high',
        top_p=1.0,
        presence_penalty=0.0,
        frequency_penalty=0.0,
        seed=20260608,
        stop=('END_ACTION',),
        response_format={'type': 'json_object'},
        stream_options={'include_usage': True},
        service_tier='default',
        user='atomic-agent-boardroom-os',
    )

    adapter(client, opts=opts).complete(provider_context())

    request = client.requests[0]
    assert request['reasoning_effort'] == 'high'
    assert request['top_p'] == 1.0
    assert request['presence_penalty'] == 0.0
    assert request['frequency_penalty'] == 0.0
    assert request['seed'] == 20260608
    assert request['stop'] == ['END_ACTION']
    assert request['response_format'] == {'type': 'json_object'}
    assert request['stream_options'] == {'include_usage': True}
    assert request['service_tier'] == 'default'
    assert request['user'] == 'atomic-agent-boardroom-os'


def test_adapter_omits_unset_provider_options():
    client = FakeOpenAIClient(chunks=[chunk(VALID_ACTION_TEXT)])

    adapter(client).complete(provider_context())

    request = client.requests[0]
    for key in [
        'reasoning_effort',
        'top_p',
        'presence_penalty',
        'frequency_penalty',
        'seed',
        'stop',
        'response_format',
        'stream_options',
        'service_tier',
        'user',
    ]:
        assert key not in request
```

Run:

```bash
python -m pytest tests/test_openai_compatible_provider.py::test_adapter_sends_all_explicit_provider_options tests/test_openai_compatible_provider.py::test_adapter_omits_unset_provider_options -q
```

Expected before implementation:

- FAIL because `OpenAICompatibleProviderOptions` does not accept the new keyword arguments.

- [ ] **Step 2: Extend `OpenAICompatibleProviderOptions`**

In `src/atomic_agent/providers/openai_compatible.py`, extend the dataclass:

```python
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
    reasoning_effort: str | None = None
    top_p: float | None = None
    presence_penalty: float | None = None
    frequency_penalty: float | None = None
    seed: int | None = None
    stop: tuple[str, ...] | None = None
    response_format: dict[str, Any] | None = None
    stream_options: dict[str, Any] | None = None
    service_tier: str | None = None
    user: str | None = None
```

Add validation in `__post_init__`:

```python
        if self.reasoning_effort is not None:
            _require_reasoning_effort(self.reasoning_effort)
        if self.top_p is not None:
            _require_finite_number(self.top_p, 'top_p')
        if self.presence_penalty is not None:
            _require_finite_number(self.presence_penalty, 'presence_penalty')
        if self.frequency_penalty is not None:
            _require_finite_number(self.frequency_penalty, 'frequency_penalty')
        if self.seed is not None:
            _require_int(self.seed, 'seed')
        if self.stop is not None:
            _require_stop_sequences(self.stop)
        if self.response_format is not None:
            _require_dict(self.response_format, 'response_format')
        if self.stream_options is not None:
            _require_dict(self.stream_options, 'stream_options')
        if self.service_tier is not None:
            _require_non_empty_string(self.service_tier, 'service_tier')
        if self.user is not None:
            _require_non_empty_string(self.user, 'user')
```

Add only the missing helper functions and reuse the existing `_require_finite_number()`（有限数值校验） and `_require_non_empty_string()`（非空字符串校验） helpers already present in `openai_compatible.py`:

```python
_REASONING_EFFORT_VALUES = {'none', 'minimal', 'low', 'medium', 'high', 'xhigh'}


def _require_reasoning_effort(value: object) -> None:
    if not isinstance(value, str) or value not in _REASONING_EFFORT_VALUES:
        allowed = ', '.join(sorted(_REASONING_EFFORT_VALUES))
        raise ValueError(f'reasoning_effort must be one of: {allowed}')


def _require_int(value: object, field_name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f'{field_name} must be an integer')


def _require_stop_sequences(value: object) -> None:
    if not isinstance(value, tuple) or not value:
        raise ValueError('stop must be a non-empty tuple of non-empty strings')
    for item in value:
        _require_non_empty_string(item, 'stop item')


def _require_dict(value: object, field_name: str) -> None:
    if not isinstance(value, dict):
        raise ValueError(f'{field_name} must be a JSON object')
```

Keep these existing helpers unchanged unless a later test proves they need adjustment:

```python
def _require_non_empty_string(value: object, field_name: str) -> None:
    if not isinstance(value, str) or value == '':
        raise ValueError(f'{field_name} must be a non-empty string')


def _require_finite_number(value: object, field_name: str) -> None:
    if not isinstance(value, int | float) or isinstance(value, bool) or not math.isfinite(value):
        raise ValueError(f'{field_name} must be a finite number')
```

- [ ] **Step 3: Map optional options into request payload**

Update `_request_payload()`:

```python
        optional_fields = {
            # Existing optional field（现有可选字段）: keep mapping temperature exactly as before.
            'temperature': self.options.temperature,
            # P2-005 explicit provider options（显式供应商参数）.
            'reasoning_effort': self.options.reasoning_effort,
            'top_p': self.options.top_p,
            'presence_penalty': self.options.presence_penalty,
            'frequency_penalty': self.options.frequency_penalty,
            'seed': self.options.seed,
            'response_format': self.options.response_format,
            'stream_options': self.options.stream_options,
            'service_tier': self.options.service_tier,
            'user': self.options.user,
        }
        for key, value in optional_fields.items():
            if value is not None:
                payload[key] = value
        if self.options.stop is not None:
            payload['stop'] = list(self.options.stop)
```

`temperature`（温度） remains the existing optional field and must continue to be sent only when explicitly configured.

Keep `max_tokens` unchanged in P2-005 unless Task 0 official docs review requires a spec update.

- [ ] **Step 4: Run focused payload tests**

Run:

```bash
python -m pytest tests/test_openai_compatible_provider.py::test_adapter_sends_all_explicit_provider_options tests/test_openai_compatible_provider.py::test_adapter_omits_unset_provider_options -q
```

Expected:

- PASS.

---

## Task 4: Add Sanitized Provider Profile Helper

**Files:**

- Modify: `src/atomic_agent/providers/openai_compatible.py`
- Modify: `src/atomic_agent/examples/minimal_real_provider_loop.py`
- Modify: `tests/test_real_provider_tool_success.py`
- Test: `tests/test_openai_compatible_provider.py`

- [ ] **Step 1: Write failing provider profile tests**

Add to `tests/test_openai_compatible_provider.py`:

```python
def test_provider_profile_records_explicit_non_secret_options_without_base_url_when_label_is_set():
    profile = options(
        base_url='https://secret-provider.example/v1',
        api_key='secret-key',
        provider_label='boardroom-os-real-provider',
        reasoning_effort='high',
        top_p=1.0,
        presence_penalty=0.0,
        frequency_penalty=0.0,
        seed=20260608,
        stop=('END_ACTION',),
        response_format={'type': 'json_object'},
        stream_options={'include_usage': True},
        service_tier='default',
        user='atomic-agent-boardroom-os',
    ).to_provider_profile()

    assert profile['provider'] == 'openai-compatible'
    assert profile['provider_label'] == 'boardroom-os-real-provider'
    assert profile['reasoning_effort'] == 'high'
    assert profile['response_format'] == {'type': 'json_object'}
    assert profile['stream_options'] == {'include_usage': True}
    serialized = json.dumps(profile, sort_keys=True)
    assert 'secret-key' not in serialized
    assert 'secret-provider.example' not in serialized
    assert 'base_url' not in profile


def test_provider_profile_records_base_url_only_without_provider_label():
    profile = options(provider_label=None).to_provider_profile()

    assert profile['base_url'] == 'https://provider.example/v1'
    assert 'provider_label' not in profile
```

Run:

```bash
python -m pytest tests/test_openai_compatible_provider.py::test_provider_profile_records_explicit_non_secret_options_without_base_url_when_label_is_set tests/test_openai_compatible_provider.py::test_provider_profile_records_base_url_only_without_provider_label -q
```

Expected before implementation:

- FAIL because `to_provider_profile()` does not exist.

- [ ] **Step 2: Implement `to_provider_profile()`**

Add this method to `OpenAICompatibleProviderOptions`:

```python
    def to_provider_profile(self) -> dict[str, Any]:
        profile: dict[str, Any] = {
            'provider': 'openai-compatible',
            'model': self.model,
            'context_window_tokens': self.context_window_tokens,
            'max_output_tokens': self.max_output_tokens,
            'stream_idle_timeout_seconds': self.stream_idle_timeout_seconds,
            'total_timeout_seconds': self.total_timeout_seconds,
        }
        if self.provider_label is not None:
            profile['provider_label'] = self.provider_label
        else:
            profile['base_url'] = self.base_url
        optional_fields = {
            'temperature': self.temperature,
            'reasoning_effort': self.reasoning_effort,
            'top_p': self.top_p,
            'presence_penalty': self.presence_penalty,
            'frequency_penalty': self.frequency_penalty,
            'seed': self.seed,
            'response_format': self.response_format,
            'stream_options': self.stream_options,
            'service_tier': self.service_tier,
            'user': self.user,
        }
        for key, value in optional_fields.items():
            if value is not None:
                profile[key] = value
        if self.stop is not None:
            profile['stop'] = list(self.stop)
        return profile
```

- [ ] **Step 3: Reuse the helper in invocation builders**

In `src/atomic_agent/examples/minimal_real_provider_loop.py`, replace manual `provider_profile` construction with:

```python
provider_profile = provider_config.to_provider_options().to_provider_profile()
```

Add `to_provider_options()` to `CliProviderConfig`:

```python
    def to_provider_options(self) -> OpenAICompatibleProviderOptions:
        return OpenAICompatibleProviderOptions(
            base_url=self.base_url,
            api_key=self.api_key,
            model=self.model,
            context_window_tokens=self.context_window_tokens,
            max_output_tokens=self.max_output_tokens,
            stream_idle_timeout_seconds=self.stream_idle_timeout_seconds,
            total_timeout_seconds=self.total_timeout_seconds,
            temperature=self.temperature,
            provider_label=self.provider_label,
            reasoning_effort=self.reasoning_effort,
            top_p=self.top_p,
            presence_penalty=self.presence_penalty,
            frequency_penalty=self.frequency_penalty,
            seed=self.seed,
            stop=self.stop,
            response_format=self.response_format,
            stream_options=self.stream_options,
            service_tier=self.service_tier,
            user=self.user,
        )
```

In `tests/test_real_provider_tool_success.py`, replace the hand-built provider profile with:

```python
provider_profile=options.to_provider_profile(),
```

- [ ] **Step 4: Run focused profile tests**

Run:

```bash
python -m pytest tests/test_openai_compatible_provider.py::test_provider_profile_records_explicit_non_secret_options_without_base_url_when_label_is_set tests/test_openai_compatible_provider.py::test_provider_profile_records_base_url_only_without_provider_label -q
```

Expected:

- PASS.

---

## Task 5: Extend CLI and Env Parsing

### Create

- `tests/test_minimal_real_provider_loop.py`  
  Focused parser tests（聚焦解析测试） for `minimal_real_provider_loop` CLI helpers. This file does not exist yet; create it to keep CLI parsing tests separate from provider adapter tests.

### Modify

- `src/atomic_agent/examples/minimal_real_provider_loop.py`
- `tests/test_real_provider_integration.py`
- `tests/test_real_provider_tool_success.py`

- [ ] **Step 1: Add parsing helper tests for CLI module**

Create `tests/test_minimal_real_provider_loop.py` with these cases:

```python
import argparse

import pytest

from atomic_agent.examples.minimal_real_provider_loop import (
    parse_float_or_none,
    parse_int_or_none,
    parse_json_object_or_none,
    parse_stop_or_none,
)


def test_parse_float_or_none_accepts_empty_string_as_unset():
    assert parse_float_or_none('') is None


def test_parse_float_or_none_accepts_finite_float():
    assert parse_float_or_none('0.2') == 0.2


def test_parse_float_or_none_rejects_infinity():
    with pytest.raises(argparse.ArgumentTypeError, match='must be a finite number or empty string'):
        parse_float_or_none('inf')


def test_parse_json_object_or_none_accepts_empty_string_as_unset():
    assert parse_json_object_or_none('') is None


def test_parse_json_object_or_none_accepts_object():
    assert parse_json_object_or_none('{"type":"json_object"}') == {'type': 'json_object'}


def test_parse_json_object_or_none_rejects_array():
    with pytest.raises(argparse.ArgumentTypeError, match='must be a JSON object or empty string'):
        parse_json_object_or_none('[]')


def test_parse_json_object_or_none_rejects_null():
    with pytest.raises(argparse.ArgumentTypeError, match='must be a JSON object or empty string'):
        parse_json_object_or_none('null')


def test_parse_stop_or_none_accepts_empty_string_as_unset():
    assert parse_stop_or_none('') is None


def test_parse_stop_or_none_accepts_json_array():
    assert parse_stop_or_none('["END_ACTION"]') == ('END_ACTION',)


def test_parse_stop_or_none_rejects_empty_array():
    with pytest.raises(argparse.ArgumentTypeError, match='must be a non-empty JSON array'):
        parse_stop_or_none('[]')


def test_parse_stop_or_none_rejects_non_string_item():
    with pytest.raises(argparse.ArgumentTypeError, match='must be a non-empty JSON array'):
        parse_stop_or_none('[1]')


def test_parse_int_or_none_accepts_empty_string_as_unset():
    assert parse_int_or_none('') is None


def test_parse_int_or_none_accepts_integer():
    assert parse_int_or_none('20260608') == 20260608


def test_parse_int_or_none_rejects_float_string():
    with pytest.raises(argparse.ArgumentTypeError, match='must be an integer or empty string'):
        parse_int_or_none('1.5')
```

Run:

```bash
python -m pytest tests/test_minimal_real_provider_loop.py -q
```

Expected before implementation:

- FAIL because `parse_int_or_none`, `parse_json_object_or_none`, and `parse_stop_or_none` do not exist yet.


- [ ] **Step 2: Extend `CliProviderConfig`**

Add fields:

```python
    reasoning_effort: str | None
    top_p: float | None
    presence_penalty: float | None
    frequency_penalty: float | None
    seed: int | None
    stop: tuple[str, ...] | None
    response_format: dict[str, object] | None
    stream_options: dict[str, object] | None
    service_tier: str | None
    user: str | None
```

- [ ] **Step 3: Add CLI arguments**

In `build_parser()` add:

```python
    parser.add_argument('--reasoning-effort', default=None)
    parser.add_argument('--top-p', type=parse_float_or_none, default=None)
    parser.add_argument('--presence-penalty', type=parse_float_or_none, default=None)
    parser.add_argument('--frequency-penalty', type=parse_float_or_none, default=None)
    parser.add_argument('--seed', type=parse_int_or_none, default=None)
    parser.add_argument('--stop', type=parse_stop_or_none, default=None)
    parser.add_argument('--response-format-json', type=parse_json_object_or_none, default=None)
    parser.add_argument('--stream-options-json', type=parse_json_object_or_none, default=None)
    parser.add_argument('--service-tier', default=None)
    parser.add_argument('--user', default=None)
```

- [ ] **Step 4: Add parsing helpers**

Add these helpers. `parse_float_or_none()` already exists for `temperature`; keep it available and use it for `top_p`, `presence_penalty`, and `frequency_penalty` too. If it is missing or has drifted, use this exact implementation:

```python
def parse_float_or_none(value: str) -> float | None:
    if value == '':
        return None
    try:
        parsed = float(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError('must be a finite number or empty string') from error
    if not math.isfinite(parsed):
        raise argparse.ArgumentTypeError('must be a finite number or empty string')
    return parsed


def parse_int_or_none(value: str) -> int | None:
    if value == '':
        return None
    try:
        parsed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError('must be an integer or empty string') from error
    return parsed


def parse_json_object_or_none(value: str) -> dict[str, object] | None:
    if value == '':
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as error:
        raise argparse.ArgumentTypeError('must be a JSON object or empty string') from error
    if not isinstance(parsed, dict):
        raise argparse.ArgumentTypeError('must be a JSON object or empty string')
    return parsed


def parse_stop_or_none(value: str) -> tuple[str, ...] | None:
    if value == '':
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as error:
        raise argparse.ArgumentTypeError('must be a non-empty JSON array of non-empty strings or empty string') from error
    if not isinstance(parsed, list) or not parsed:
        raise argparse.ArgumentTypeError('must be a non-empty JSON array of non-empty strings or empty string')
    if any(not isinstance(item, str) or item == '' for item in parsed):
        raise argparse.ArgumentTypeError('must be a non-empty JSON array of non-empty strings or empty string')
    return tuple(parsed)
```

- [ ] **Step 5: Normalize empty optional strings**

In `provider_config_from_args()`, convert `reasoning_effort`, `service_tier`, and `user` empty strings to `None`. Keep the existing `provider_label` behavior: an explicitly provided empty string is rejected because `provider_label`（供应商标签） controls whether `provider_profile` records a safe label or a real `base_url`.

```python
# provider_label empty string is rejected earlier by existing validation.
# These optional strings use empty string as unset to match env/template semantics.
reasoning_effort = args.reasoning_effort or None
service_tier = args.service_tier or None
user = args.user or None
```

Then pass all new values into `CliProviderConfig`.

- [ ] **Step 6: Forward env vars in `tests/test_real_provider_integration.py`**

Add this helper:

```python
def extend_optional_arg(args, env_name, cli_name):
    value = os.environ.get(env_name)
    if value is not None:
        args.extend([cli_name, value])
```

After temperature/provider-label handling, forward:

```python
for env_name, cli_name in [
    ('ATOMIC_AGENT_REAL_PROVIDER_REASONING_EFFORT', '--reasoning-effort'),
    ('ATOMIC_AGENT_REAL_PROVIDER_TOP_P', '--top-p'),
    ('ATOMIC_AGENT_REAL_PROVIDER_PRESENCE_PENALTY', '--presence-penalty'),
    ('ATOMIC_AGENT_REAL_PROVIDER_FREQUENCY_PENALTY', '--frequency-penalty'),
    ('ATOMIC_AGENT_REAL_PROVIDER_SEED', '--seed'),
    ('ATOMIC_AGENT_REAL_PROVIDER_STOP', '--stop'),
    ('ATOMIC_AGENT_REAL_PROVIDER_RESPONSE_FORMAT_JSON', '--response-format-json'),
    ('ATOMIC_AGENT_REAL_PROVIDER_STREAM_OPTIONS_JSON', '--stream-options-json'),
    ('ATOMIC_AGENT_REAL_PROVIDER_SERVICE_TIER', '--service-tier'),
    ('ATOMIC_AGENT_REAL_PROVIDER_USER', '--user'),
]:
    extend_optional_arg(args, env_name, cli_name)
```

- [ ] **Step 7: Parse env vars in `tests/test_real_provider_tool_success.py`**

Add helpers equivalent to the CLI semantics:

```python
def env_int_or_none(name, default):
    raw = os.environ.get(name, default)
    if raw in (None, ''):
        return None
    return int(raw)


def env_json_object_or_none(name, default):
    raw = os.environ.get(name, default)
    if raw in (None, ''):
        return None
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError(f'{name} must be a JSON object or empty string')
    return parsed


def env_stop_or_none(name, default):
    raw = os.environ.get(name, default)
    if raw in (None, ''):
        return None
    parsed = json.loads(raw)
    if not isinstance(parsed, list) or not parsed or any(not isinstance(item, str) or item == '' for item in parsed):
        raise ValueError(f'{name} must be a non-empty JSON array of non-empty strings or empty string')
    return tuple(parsed)
```

Pass new fields into `OpenAICompatibleProviderOptions` inside `provider_options()`.

- [ ] **Step 8: Run parser tests**

Run:

```bash
python -m pytest tests/test_minimal_real_provider_loop.py -q
```

If the tests were placed in `tests/test_openai_compatible_provider.py`, run the exact new test names instead.

Expected:

- PASS.

---

## Task 6: Update Real Provider Docs

**Files:**

- Modify: `README.md`
- Modify: `docs/05-testing/testing-strategy.md`

- [ ] **Step 1: Update README standalone example**

In `README.md`, extend the standalone CLI example with:

```bash
  --temperature 0.2 \
  --reasoning-effort high \
  --top-p 1.0 \
  --presence-penalty 0.0 \
  --frequency-penalty 0.0 \
  --seed 20260608 \
  --stop '' \
  --response-format-json '{"type":"json_object"}' \
  --stream-options-json '{"include_usage":true}' \
  --service-tier '' \
  --user atomic-agent-boardroom-os
```

Keep base URL and API key placeholders only.

- [ ] **Step 2: Update README pytest env example**

Add optional env vars after model:

```bash
ATOMIC_AGENT_REAL_PROVIDER_TEMPERATURE=0.2 \
ATOMIC_AGENT_REAL_PROVIDER_REASONING_EFFORT=high \
ATOMIC_AGENT_REAL_PROVIDER_TOP_P=1.0 \
ATOMIC_AGENT_REAL_PROVIDER_RESPONSE_FORMAT_JSON='{"type":"json_object"}' \
ATOMIC_AGENT_REAL_PROVIDER_STREAM_OPTIONS_JSON='{"include_usage":true}' \
```

Explain that `.env.template` is the tracked sanitized template and `.env.real-provider-test-p2-002-task7` is local ignored config.

- [ ] **Step 3: Update testing strategy optional env vars**

In `docs/05-testing/testing-strategy.md`, extend Optional env vars with:

```text
ATOMIC_AGENT_REAL_PROVIDER_REASONING_EFFORT=high
ATOMIC_AGENT_REAL_PROVIDER_TOP_P=1.0
ATOMIC_AGENT_REAL_PROVIDER_PRESENCE_PENALTY=0.0
ATOMIC_AGENT_REAL_PROVIDER_FREQUENCY_PENALTY=0.0
ATOMIC_AGENT_REAL_PROVIDER_SEED=20260608
ATOMIC_AGENT_REAL_PROVIDER_STOP=
ATOMIC_AGENT_REAL_PROVIDER_RESPONSE_FORMAT_JSON='{"type":"json_object"}'
ATOMIC_AGENT_REAL_PROVIDER_STREAM_OPTIONS_JSON='{"include_usage":true}'
ATOMIC_AGENT_REAL_PROVIDER_SERVICE_TIER=
ATOMIC_AGENT_REAL_PROVIDER_USER=atomic-agent-boardroom-os
```

Add notes:

- These are explicit local/manual profile values, not runtime core defaults.
- Provider incompatibility must fail closed.
- Usage data is audit context, not success evidence.
- API key and real base URL must not appear in tracked docs or templates.

---

## Task 7: Verify No Secret Leakage and Base Tests

**Files:**

- All changed files.

- [ ] **Step 1: Check git status before tests**

Run:

```bash
git status --short
```

Expected:

- `.env.real-provider-test-p2-002-task7` may be absent from status because it is ignored.
- `.env.template` should appear as untracked or staged only after `.gitignore` allows it.
- No unexpected generated artifacts.

- [ ] **Step 2: Run focused unit tests**

Run:

```bash
python -m pytest tests/test_openai_compatible_provider.py -q
```

Expected:

- PASS.

- [ ] **Step 3: Run default-skip real provider tests without network**

Run:

```bash
python -m pytest tests/test_real_provider_integration.py -q
python -m pytest tests/test_real_provider_tool_success.py -q
```

Expected:

- Tests skip unless explicit enable env vars are set.
- No real provider network call occurs.

- [ ] **Step 4: Run full base suite**

Run:

```bash
python -m pytest -q
```

Expected:

- PASS.
- No required real provider credentials.
- No real provider network call.

- [ ] **Step 5: Search changed tracked files for local secret values**

Run:

```bash
python - <<'PY'
from pathlib import Path
local = Path('.env.real-provider-test-p2-002-task7').read_text(encoding='utf-8')
secret_values = []
for key in ['ATOMIC_AGENT_REAL_PROVIDER_BASE_URL', 'ATOMIC_AGENT_REAL_PROVIDER_API_KEY']:
    for line in local.splitlines():
        if line.startswith(key + '='):
            secret_values.append(line.split('=', 1)[1])
tracked_candidates = [
    Path('.env.template'),
    Path('README.md'),
    Path('docs/05-testing/testing-strategy.md'),
    Path('docs/04-implementation-spec/P2-005-openai-compatible-provider-options-hardening-spec.md'),
    Path('docs/04-implementation-plan/P2-005-openai-compatible-provider-options-hardening-plan.md'),
]
for path in tracked_candidates:
    text = path.read_text(encoding='utf-8')
    for value in secret_values:
        assert value not in text, f'{path} leaks a local provider secret'
PY
```

Expected:

- PASS with no output.

---

## Task 8: Finish Documentation State After Implementation

**Files:**

- Modify: `docs/04-implementation-backlog/backlog.md`
- Modify: `docs/04-implementation-plan/INDEX.md`
- Modify: `docs/04-implementation-spec/INDEX.md`
- Modify: `docs/INDEX.md`

- [ ] **Step 1: Mark backlog completed only after tests pass**

In `docs/04-implementation-backlog/backlog.md`, update P2-005 from `pending` to `completed` only after Task 7 passes.

- [ ] **Step 2: Move this plan from active to completed**

In `docs/04-implementation-plan/INDEX.md`, move `P2-005-openai-compatible-provider-options-hardening-plan.md` from `Current Active Documents` to `Completed / Archived Documents` with completion date `2026-06-08`.

- [ ] **Step 3: Move spec if implementation is complete**

In `docs/04-implementation-spec/INDEX.md`, move `P2-005-openai-compatible-provider-options-hardening-spec.md` from active draft to completed/archived with completion date `2026-06-08`.

- [ ] **Step 4: Update global docs index**

In `docs/INDEX.md`, remove P2-005 from active pointers only after implementation and verification pass. Keep P2-006 active because it remains pending and depends on P2-005.

- [ ] **Step 5: Do not commit unless explicitly requested**

The project may use frequent commit checkpoints, but this session must not run `git commit` unless the user explicitly asks for a commit.

---

## Manual Real Provider Gate Commands

Do not run these without explicit user approval because they call a real provider.

Minimal integration gate:

```bash
set -a
source .env.real-provider-test-p2-002-task7
set +a
ATOMIC_AGENT_RUN_REAL_PROVIDER=1 \
python -m pytest tests/test_real_provider_integration.py -m real_provider -q
```

Success-only tool gate:

```bash
set -a
source .env.real-provider-test-p2-002-task7
set +a
ATOMIC_AGENT_RUN_REAL_PROVIDER_TOOL_SUCCESS=1 \
python -m pytest tests/test_real_provider_tool_success.py -m real_provider_tool_success -q
```

P2-006 complex gate should be added and run only after P2-005 implementation is verified.

---

## Self-Review Checklist

- [ ] Runtime core does not hardcode capability-first defaults.
- [ ] `None` options are omitted from provider request payload.
- [ ] Explicit provider options are sent as configured and never silently dropped.
- [ ] `provider_profile` records non-secret options and avoids real `base_url` when `provider_label` is set.
- [ ] `api_key` never enters invocation, prompt messages, event payloads, artifacts, stdout/stderr, or tracked docs.
- [ ] `.env.template` contains only placeholders for base URL and API key.
- [ ] `.env.real-provider-test-p2-002-task7` remains git ignored and is not committed.
- [ ] `stop` stays unset in the default profile.
- [ ] `response_format` does not replace `AgentAction` schema validation.
- [ ] Base pytest suite remains non-networked.
