# Web Fetch and Network Policy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement P1-001 `web_fetch`（网络获取） and `NetworkPolicy`（网络策略） so the runtime can fetch only explicitly allowed HTTP(S) URLs and record auditable network evidence.

**Architecture:** Add a focused `web_fetch_tools`（网络获取工具） module that owns URL policy validation, real HTTP GET execution, timeout（超时）, response hashing（响应哈希）, and response truncation（响应截断）. Keep the existing lightweight dispatcher（分发器） architecture: `AgentLoop`（智能体循环） decides permission through `NetworkPolicy`（网络策略）, executes `WebFetchTools`（网络获取工具集合）, stores body artifacts（响应正文产物）, and records the existing `network.fetch.completed`（网络获取完成） event without creating a second event source.

**Tech Stack:** Python 3.11+, `dataclasses`（轻量数据结构）, `urllib.parse`（URL 解析）, `urllib.request`（HTTP 请求）, `urllib.error`（网络错误）, `hashlib`（哈希）, `http.server`（本地测试服务器）, pytest（测试）, existing `AgentLoop` / `EventRecorder` / `ArtifactWriter` / Pydantic models（现有智能体循环、事件记录器、产物写入器、Pydantic 模型）.

**Status:** implemented

---

## Scope

This plan implements P1-001 only.

In scope:

- Create `src/atomic_agent/web_fetch_tools.py`（网络获取工具模块）.
- Create `tests/test_web_fetch_tools.py`（网络获取工具测试）.
- Modify `src/atomic_agent/models.py`（核心模型） to validate `web_fetch` action input（动作输入）.
- Modify `src/atomic_agent/agent_loop.py`（智能体循环） to accept optional `web_fetch_tools` dependency（网络获取工具依赖）, decide network permission, execute `web_fetch`, and record `network.fetch.completed`.
- Modify `tests/test_models.py`（模型测试）, `tests/test_action_parser.py`（动作解析器测试）, and `tests/test_agent_loop.py`（智能体循环测试）.
- Use a local HTTP server（本地 HTTP 服务器） in tests; do not depend on public internet.
- Update P1-001 docs/index/backlog only after implementation and tests pass.

Out of scope:

- No POST/PUT/PATCH/DELETE methods（HTTP 写方法）.
- No request body（请求正文）.
- No custom headers（自定义请求头）, cookies（Cookie）, auth（认证）, proxy（代理）, or TLS configuration（TLS 配置）.
- No automatic redirect following（自动跟随重定向）.
- No DNS policy（DNS 策略）, IP range policy（IP 网段策略）, or OS-level network sandbox（操作系统级网络沙箱）.
- No network-enabled command（允许网络的命令）; `CommandSpec.allow_network=True` remains rejected.
- No Boardroom `AgentRuntimePort adapter`（Boardroom 智能体运行时端口适配器）.
- No README minimal example（最小示例） update.
- No commit unless the user explicitly requests it.

## File Structure

- Modify: `src/atomic_agent/models.py`
  - Add `web_fetch` input validation to `AgentAction`（智能体动作）.
  - Require `url`, allow optional `method="GET"`, and reject unknown input keys.
- Create: `src/atomic_agent/web_fetch_tools.py`
  - Define `NetworkAllowRule`（网络允许规则）, `NetworkDecision`（网络策略判定）, `NetworkPolicy`（网络策略）, `WebFetchToolConfig`（网络获取工具配置）, `WebFetchToolResult`（网络获取工具结果）, `WebFetchToolConfigError`（网络工具配置错误）, `WebFetchTools`（网络获取工具集合）, and `execute_web_fetch_action`（执行网络获取动作）.
- Modify: `src/atomic_agent/agent_loop.py`
  - Import web fetch tool types.
  - Add `web_fetch_tools: WebFetchTools | None = None` to `AgentLoopDependencies`（智能体循环依赖）.
  - Replace the existing hard-coded `web_fetch is not implemented in P0-007` denial with real network policy decision.
  - Dispatch `WEB_FETCH` to `execute_web_fetch_action`.
  - Record response body artifact and `network.fetch.completed` on successful fetch.
- Modify: `tests/test_models.py`
  - Add model-level `web_fetch` schema tests.
- Modify: `tests/test_action_parser.py`
  - Add parser-level `web_fetch` schema tests.
- Create: `tests/test_web_fetch_tools.py`
  - Cover NetworkPolicy validation, URL decisions, real local HTTP fetch, truncation, decode, timeout, connection failure, permission denial, and dispatcher behavior.
- Modify: `tests/test_agent_loop.py`
  - Add local web fetch tools factory.
  - Replace the old `web_fetch_not_implemented` expectation with configured/unconfigured network policy behavior.
  - Add successful `web_fetch` loop event assertions.
- Modify after implementation passes: `docs/04-implementation-backlog/backlog.md`
  - Mark P1-001 completed only after tests pass and user accepts implementation.
- Modify after implementation passes: `docs/04-implementation-spec/P1-001-web-fetch-network-policy-spec.md`
  - Change status from `draft` to `implemented`.
- Modify after implementation passes: `docs/04-implementation-plan/P1-001-web-fetch-network-policy-plan.md`
  - Change status from `draft` to `implemented`.
- Modify after implementation passes: `docs/04-implementation-spec/INDEX.md`
  - Move P1-001 spec from Current Active Documents（当前活跃文档） to Completed / Archived Documents（已完成 / 已归档文档）.
- Modify after implementation passes: `docs/04-implementation-plan/INDEX.md`
  - Move this plan from Current Active Documents to Completed / Archived Documents.

---

### Task 1: Add `web_fetch` action schema validation

**Files:**

- Modify: `tests/test_models.py`
- Modify: `tests/test_action_parser.py`
- Modify: `src/atomic_agent/models.py`

- [ ] **Step 1: Add model tests for valid and invalid `web_fetch` input**

Append to `tests/test_models.py`:

```python


def test_agent_action_accepts_web_fetch_with_url_only():
    action = AgentAction(
        action_id="step-web",
        action="web_fetch",
        reason_summary="Fetch allowed documentation.",
        input={"url": "https://example.com/docs"},
    )

    assert action.action == AgentActionType.WEB_FETCH
    assert action.input == {"url": "https://example.com/docs"}



def test_agent_action_accepts_web_fetch_with_get_method():
    action = AgentAction(
        action_id="step-web",
        action="web_fetch",
        reason_summary="Fetch allowed documentation.",
        input={"url": "https://example.com/docs", "method": "GET"},
    )

    assert action.input == {"url": "https://example.com/docs", "method": "GET"}


@pytest.mark.parametrize(
    "input_payload",
    [
        {},
        {"url": ""},
        {"url": 123},
        {"url": "https://example.com/docs", "method": "POST"},
        {"url": "https://example.com/docs", "method": 123},
        {"url": "https://example.com/docs", "headers": {"Accept": "text/plain"}},
        {"url": "https://example.com/docs", "body": "payload"},
        {"url": "https://example.com/docs", "timeout": 1},
    ],
)
def test_agent_action_rejects_invalid_web_fetch_input(input_payload):
    with pytest.raises(ValidationError):
        AgentAction(
            action_id="step-web",
            action="web_fetch",
            reason_summary="Fetch documentation.",
            input=input_payload,
        )
```

- [ ] **Step 2: Add parser tests for `web_fetch` input**

Append to `tests/test_action_parser.py`:

```python


def test_parse_agent_action_accepts_web_fetch_with_url():
    action = parse_agent_action(
        """
        {
          "action_id": "step-web",
          "action": "web_fetch",
          "reason_summary": "Fetch allowed documentation.",
          "input": {"url": "https://example.com/docs", "method": "GET"}
        }
        """
    )

    assert action.action == AgentActionType.WEB_FETCH
    assert action.input == {"url": "https://example.com/docs", "method": "GET"}


@pytest.mark.parametrize("input_payload", ["{}", "{\"url\": \"\"}", "{\"url\": \"https://example.com\", \"method\": \"POST\"}"])
def test_parse_agent_action_rejects_invalid_web_fetch_input(input_payload):
    with pytest.raises(ActionParseError) as error:
        parse_agent_action(
            f"""
            {{
              "action_id": "step-web",
              "action": "web_fetch",
              "reason_summary": "Fetch documentation.",
              "input": {input_payload}
            }}
            """
        )

    assert error.value.kind == "schema_validation_failed"
```

- [ ] **Step 3: Run schema tests and confirm they fail before implementation**

Run:

```bash
pytest tests/test_models.py::test_agent_action_accepts_web_fetch_with_url_only tests/test_models.py::test_agent_action_accepts_web_fetch_with_get_method tests/test_models.py::test_agent_action_rejects_invalid_web_fetch_input tests/test_action_parser.py::test_parse_agent_action_accepts_web_fetch_with_url tests/test_action_parser.py::test_parse_agent_action_rejects_invalid_web_fetch_input -v
```

Expected before implementation:

```text
FAILED tests/test_models.py::test_agent_action_rejects_invalid_web_fetch_input
FAILED tests/test_action_parser.py::test_parse_agent_action_rejects_invalid_web_fetch_input
```

The valid cases may already pass because `WEB_FETCH`（网络获取） exists in `AgentActionType`（智能体动作类型）.

- [ ] **Step 4: Add `web_fetch` validation to `AgentAction`**

In `src/atomic_agent/models.py`, add this method inside `AgentAction` after `run_command_uses_command_id`:

```python
    @model_validator(mode="after")
    def web_fetch_uses_url_and_get(self):
        if self.action != AgentActionType.WEB_FETCH:
            return self
        allowed_keys = {"url", "method"}
        extra_keys = set(self.input) - allowed_keys
        if extra_keys:
            raise ValueError("web_fetch input only supports url and method")
        url = self.input.get("url")
        if not isinstance(url, str) or url == "":
            raise ValueError("web_fetch input requires a non-empty url")
        method = self.input.get("method", "GET")
        if method != "GET":
            raise ValueError("web_fetch input only supports method GET")
        return self
```

- [ ] **Step 5: Run schema tests and confirm they pass**

Run:

```bash
pytest tests/test_models.py::test_agent_action_accepts_web_fetch_with_url_only tests/test_models.py::test_agent_action_accepts_web_fetch_with_get_method tests/test_models.py::test_agent_action_rejects_invalid_web_fetch_input tests/test_action_parser.py::test_parse_agent_action_accepts_web_fetch_with_url tests/test_action_parser.py::test_parse_agent_action_rejects_invalid_web_fetch_input -v
```

Expected:

```text
PASSED
```

---

### Task 2: Add NetworkPolicy boundary tests and implementation

**Files:**

- Create: `tests/test_web_fetch_tools.py`
- Create: `src/atomic_agent/web_fetch_tools.py`

- [ ] **Step 1: Write failing tests for result shape, config validation, rule validation, and URL decisions**

Write `tests/test_web_fetch_tools.py`:

```python
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hashlib
import socket
import threading

import pytest

from atomic_agent.models import AgentAction, AgentActionType
from atomic_agent.web_fetch_tools import (
    NetworkAllowRule,
    NetworkPolicy,
    WebFetchToolConfig,
    WebFetchToolConfigError,
    WebFetchToolResult,
    WebFetchTools,
    execute_web_fetch_action,
)


class RecordingHandler(BaseHTTPRequestHandler):
    response_status = 200
    response_reason = "OK"
    response_body = b"ok"
    response_content_type = "text/plain; charset=utf-8"
    response_headers = {}
    delay_seconds = 0.0
    request_paths = []

    def do_GET(self):
        if self.delay_seconds:
            import time

            time.sleep(self.delay_seconds)
        self.__class__.request_paths.append(self.path)
        self.send_response(self.response_status, self.response_reason)
        if self.response_content_type is not None:
            self.send_header("Content-Type", self.response_content_type)
        for name, value in self.response_headers.items():
            self.send_header(name, value)
        self.end_headers()
        try:
            self.wfile.write(self.response_body)
        except BrokenPipeError:
            pass

    def log_message(self, format, *args):
        return


@pytest.fixture
def local_http_server():
    class Handler(RecordingHandler):
        response_status = 200
        response_reason = "OK"
        response_body = b"ok"
        response_content_type = "text/plain; charset=utf-8"
        delay_seconds = 0.0
        request_paths = []

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server, Handler
    finally:
        server.shutdown()
        thread.join(timeout=2.0)
        server.server_close()


def unused_local_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def allow_rule(port, path_prefix="/"):
    return NetworkAllowRule(
        rule_id="local-test",
        scheme="http",
        host="127.0.0.1",
        port=port,
        path_prefix=path_prefix,
    )


def make_tools(port, max_response_bytes=4096, timeout_seconds=2.0, path_prefix="/"):
    return WebFetchTools(
        NetworkPolicy((allow_rule(port, path_prefix=path_prefix),)),
        WebFetchToolConfig(timeout_seconds=timeout_seconds, max_response_bytes=max_response_bytes),
    )


def test_web_fetch_tool_result_success_has_no_error_fields():
    result = WebFetchToolResult(
        ok=True,
        tool="web_fetch",
        url="https://example.com/docs",
        data={"status_code": 200},
    )

    assert result.error_kind is None
    assert result.error_message is None


def test_web_fetch_tool_result_success_rejects_error_fields():
    with pytest.raises(ValueError):
        WebFetchToolResult(
            ok=True,
            tool="web_fetch",
            url="https://example.com/docs",
            data={"status_code": 200},
            error_kind="permission_denied",
            error_message="denied",
        )


def test_web_fetch_tool_result_failure_requires_error_fields():
    with pytest.raises(ValueError):
        WebFetchToolResult(ok=False, tool="web_fetch", url="https://example.com/docs", data={})


@pytest.mark.parametrize(
    "config",
    [
        WebFetchToolConfig(timeout_seconds=0.0, max_response_bytes=100),
        WebFetchToolConfig(timeout_seconds=-1.0, max_response_bytes=100),
        WebFetchToolConfig(timeout_seconds=True, max_response_bytes=100),
        WebFetchToolConfig(timeout_seconds=1.0, max_response_bytes=0),
        WebFetchToolConfig(timeout_seconds=1.0, max_response_bytes=True),
    ],
)
def test_web_fetch_tools_rejects_invalid_config(config):
    with pytest.raises(WebFetchToolConfigError):
        WebFetchTools(NetworkPolicy(()), config)


@pytest.mark.parametrize(
    "rule",
    [
        NetworkAllowRule(rule_id="", scheme="http", host="example.com", port=None, path_prefix="/"),
        NetworkAllowRule(rule_id="bad id", scheme="http", host="example.com", port=None, path_prefix="/"),
        NetworkAllowRule(rule_id="rule", scheme="ftp", host="example.com", port=None, path_prefix="/"),
        NetworkAllowRule(rule_id="rule", scheme="http", host="", port=None, path_prefix="/"),
        NetworkAllowRule(rule_id="rule", scheme="http", host="example.com", port=0, path_prefix="/"),
        NetworkAllowRule(rule_id="rule", scheme="http", host="example.com", port=65536, path_prefix="/"),
        NetworkAllowRule(rule_id="rule", scheme="http", host="example.com", port=True, path_prefix="/"),
        NetworkAllowRule(rule_id="rule", scheme="http", host="example.com", port=None, path_prefix="docs"),
    ],
)
def test_network_policy_rejects_invalid_rules(rule):
    with pytest.raises(WebFetchToolConfigError):
        NetworkPolicy((rule,))


def test_network_policy_allows_matching_url():
    policy = NetworkPolicy((NetworkAllowRule("docs", "https", "Example.COM", None, "/docs"),))

    decision = policy.decide("https://example.com/docs/index.html?x=1")

    assert decision.decision == "allow"
    assert decision.matched_rule_id == "docs"
    assert decision.reason == "network target allowed by rule docs"


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
    policy = NetworkPolicy((NetworkAllowRule("docs", "https", "example.com", None, "/docs"),))

    decision = policy.decide(url)

    assert decision.decision == "deny"
    assert decision.matched_rule_id is None
    assert decision.reason


def test_network_policy_empty_rules_denies_all():
    decision = NetworkPolicy(()).decide("https://example.com/docs")

    assert decision.decision == "deny"
    assert decision.reason == "network target is not allowed by network policy"
```

- [ ] **Step 2: Run new boundary tests and confirm module is missing**

Run:

```bash
pytest tests/test_web_fetch_tools.py::test_web_fetch_tool_result_success_has_no_error_fields tests/test_web_fetch_tools.py::test_web_fetch_tools_rejects_invalid_config tests/test_web_fetch_tools.py::test_network_policy_allows_matching_url tests/test_web_fetch_tools.py::test_network_policy_denies_unmatched_or_invalid_url -v
```

Expected:

```text
ModuleNotFoundError: No module named 'atomic_agent.web_fetch_tools'
```

- [ ] **Step 3: Add initial `web_fetch_tools` module with result, config, and policy logic**

Write `src/atomic_agent/web_fetch_tools.py`:

```python
from dataclasses import dataclass
import hashlib
import re
from typing import Any, Literal
from urllib.parse import SplitResult, urlsplit

from atomic_agent.models import AgentAction, AgentActionType


_RULE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.:-]+$")
_ALLOWED_SCHEMES = {"http", "https"}
_DEFAULT_PORTS = {"http": 80, "https": 443}


@dataclass(frozen=True)
class NetworkAllowRule:
    rule_id: str
    scheme: str
    host: str
    port: int | None
    path_prefix: str


@dataclass(frozen=True)
class NetworkDecision:
    decision: Literal["allow", "deny"]
    reason: str
    matched_rule_id: str | None = None


@dataclass(frozen=True)
class WebFetchToolConfig:
    timeout_seconds: float
    max_response_bytes: int


@dataclass(frozen=True)
class WebFetchToolResult:
    ok: bool
    tool: str
    url: str | None
    data: dict[str, Any]
    error_kind: str | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        if self.ok and (self.error_kind is not None or self.error_message is not None):
            raise ValueError("successful WebFetchToolResult must not include error fields")
        if not self.ok and (not self.error_kind or not self.error_message):
            raise ValueError("failed WebFetchToolResult requires error_kind and error_message")


class WebFetchToolConfigError(ValueError):
    pass


class NetworkPolicy:
    def __init__(self, rules: tuple[NetworkAllowRule, ...]):
        if not isinstance(rules, tuple):
            raise WebFetchToolConfigError("network policy rules must be a tuple")
        self.rules = tuple(self._normalize_rule(rule) for rule in rules)

    def decide(self, url: str) -> NetworkDecision:
        split_or_error = self._split_url(url)
        if isinstance(split_or_error, str):
            return NetworkDecision("deny", split_or_error)
        split = split_or_error
        scheme = split.scheme.lower()
        host = split.hostname.lower() if split.hostname is not None else ""
        try:
            port = split.port if split.port is not None else _DEFAULT_PORTS[scheme]
        except ValueError:
            return NetworkDecision("deny", "url port is invalid")
        path = split.path or "/"
        for rule in self.rules:
            rule_port = rule.port if rule.port is not None else _DEFAULT_PORTS[rule.scheme]
            if scheme == rule.scheme and host == rule.host and port == rule_port and path.startswith(rule.path_prefix):
                return NetworkDecision(
                    "allow",
                    f"network target allowed by rule {rule.rule_id}",
                    matched_rule_id=rule.rule_id,
                )
        return NetworkDecision("deny", "network target is not allowed by network policy")

    def _split_url(self, url: str) -> SplitResult | str:
        if not isinstance(url, str) or url == "":
            return "url must be a non-empty string"
        split = urlsplit(url)
        scheme = split.scheme.lower()
        if scheme not in _ALLOWED_SCHEMES:
            return "url scheme must be http or https"
        if split.hostname is None or split.hostname == "":
            return "url host is required"
        if split.username is not None or split.password is not None:
            return "url must not include userinfo"
        if split.fragment:
            return "url fragment is not allowed"
        try:
            split.port
        except ValueError:
            return "url port is invalid"
        return split

    def _normalize_rule(self, rule: NetworkAllowRule) -> NetworkAllowRule:
        if not isinstance(rule, NetworkAllowRule):
            raise WebFetchToolConfigError("network allow rule must be a NetworkAllowRule")
        if not isinstance(rule.rule_id, str) or not _RULE_ID_PATTERN.fullmatch(rule.rule_id):
            raise WebFetchToolConfigError("network rule_id must be a non-empty stable identifier")
        if not isinstance(rule.scheme, str) or rule.scheme.lower() not in _ALLOWED_SCHEMES:
            raise WebFetchToolConfigError("network rule scheme must be http or https")
        if not isinstance(rule.host, str) or rule.host == "":
            raise WebFetchToolConfigError("network rule host must be a non-empty string")
        if rule.port is not None:
            if not isinstance(rule.port, int) or isinstance(rule.port, bool) or rule.port < 1 or rule.port > 65535:
                raise WebFetchToolConfigError("network rule port must be between 1 and 65535")
        if not isinstance(rule.path_prefix, str) or not rule.path_prefix.startswith("/"):
            raise WebFetchToolConfigError("network rule path_prefix must start with /")
        return NetworkAllowRule(
            rule_id=rule.rule_id,
            scheme=rule.scheme.lower(),
            host=rule.host.lower(),
            port=rule.port,
            path_prefix=rule.path_prefix,
        )


class WebFetchTools:
    def __init__(self, policy: NetworkPolicy, config: WebFetchToolConfig):
        if not isinstance(policy, NetworkPolicy):
            raise WebFetchToolConfigError("policy must be a NetworkPolicy")
        self.policy = policy
        self.config = config
        self._validate_config()

    def _validate_config(self) -> None:
        if not self._is_positive_number(self.config.timeout_seconds):
            raise WebFetchToolConfigError("timeout_seconds must be positive")
        if not isinstance(self.config.max_response_bytes, int) or isinstance(self.config.max_response_bytes, bool) or self.config.max_response_bytes <= 0:
            raise WebFetchToolConfigError("max_response_bytes must be a positive integer")

    def _is_positive_number(self, value: object) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0

    def fetch_url(self, url: str, method: str = "GET") -> WebFetchToolResult:
        return WebFetchToolResult(
            ok=False,
            tool="web_fetch",
            url=url if isinstance(url, str) else None,
            data={},
            error_kind="fetch_failed",
            error_message="web_fetch execution is not implemented yet",
        )


def execute_web_fetch_action(action: AgentAction, tools: WebFetchTools) -> WebFetchToolResult:
    if action.action != AgentActionType.WEB_FETCH:
        return WebFetchToolResult(
            ok=False,
            tool=action.action.value,
            url=None,
            data={},
            error_kind="unsupported_action",
            error_message="Unsupported web fetch action.",
        )
    return tools.fetch_url(url=action.input["url"], method=action.input.get("method", "GET"))
```

- [ ] **Step 4: Run boundary tests and confirm they pass**

Run:

```bash
pytest tests/test_web_fetch_tools.py::test_web_fetch_tool_result_success_has_no_error_fields tests/test_web_fetch_tools.py::test_web_fetch_tool_result_success_rejects_error_fields tests/test_web_fetch_tools.py::test_web_fetch_tool_result_failure_requires_error_fields tests/test_web_fetch_tools.py::test_web_fetch_tools_rejects_invalid_config tests/test_web_fetch_tools.py::test_network_policy_rejects_invalid_rules tests/test_web_fetch_tools.py::test_network_policy_allows_matching_url tests/test_web_fetch_tools.py::test_network_policy_denies_unmatched_or_invalid_url tests/test_web_fetch_tools.py::test_network_policy_empty_rules_denies_all -v
```

Expected:

```text
PASSED
```

---

### Task 3: Implement real `web_fetch` execution

**Files:**

- Modify: `tests/test_web_fetch_tools.py`
- Modify: `src/atomic_agent/web_fetch_tools.py`

- [ ] **Step 1: Add failing tests for real local HTTP behavior**

Append to `tests/test_web_fetch_tools.py`:

```python


def test_fetch_url_gets_allowed_local_http_response(local_http_server):
    server, handler = local_http_server
    handler.response_body = "hello".encode("utf-8")
    handler.response_content_type = "text/plain; charset=utf-8"
    tools = make_tools(server.server_port)

    result = tools.fetch_url(f"http://127.0.0.1:{server.server_port}/docs?x=1")

    assert result.ok is True
    assert result.tool == "web_fetch"
    assert result.url == f"http://127.0.0.1:{server.server_port}/docs?x=1"
    assert result.data["url"] == result.url
    assert result.data["method"] == "GET"
    assert result.data["status_code"] == 200
    assert result.data["reason"] == "OK"
    assert result.data["content_type"] == "text/plain; charset=utf-8"
    assert result.data["body"] == "hello"
    assert result.data["body_sha256"] == "sha256:" + hashlib.sha256(b"hello").hexdigest()
    assert result.data["body_size_bytes"] == 5
    assert result.data["body_truncated"] is False
    assert result.data["body_decoded_with_replacement"] is False
    assert result.data["matched_rule_id"] == "local-test"
    assert result.data["timeout_seconds"] == 2.0
    assert result.data["max_response_bytes"] == 4096
    assert handler.request_paths == ["/docs?x=1"]


@pytest.mark.parametrize("status_code", [301, 404, 500])
def test_fetch_url_treats_http_status_as_completed_response(local_http_server, status_code):
    server, handler = local_http_server
    handler.response_status = status_code
    handler.response_reason = "Status"
    handler.response_body = f"status {status_code}".encode("utf-8")
    tools = make_tools(server.server_port)

    result = tools.fetch_url(f"http://127.0.0.1:{server.server_port}/status")

    assert result.ok is True
    assert result.data["status_code"] == status_code
    assert result.data["body"] == f"status {status_code}"
    assert handler.request_paths == ["/status"]


def test_fetch_url_truncates_body_and_hashes_stored_bytes(local_http_server):
    server, handler = local_http_server
    handler.response_body = b"abcdef"
    tools = make_tools(server.server_port, max_response_bytes=4)

    result = tools.fetch_url(f"http://127.0.0.1:{server.server_port}/large")

    assert result.ok is True
    assert result.data["body"] == "abcd"
    assert result.data["body_size_bytes"] == 4
    assert result.data["body_sha256"] == "sha256:" + hashlib.sha256(b"abcd").hexdigest()
    assert result.data["body_truncated"] is True


def test_fetch_url_records_decode_replacement_for_non_utf8_body(local_http_server):
    server, handler = local_http_server
    handler.response_body = b"\xff"
    tools = make_tools(server.server_port)

    result = tools.fetch_url(f"http://127.0.0.1:{server.server_port}/binary")

    assert result.ok is True
    assert result.data["body"] == "�"
    assert result.data["body_decoded_with_replacement"] is True


def test_fetch_url_denies_unallowed_url_without_request(local_http_server):
    server, handler = local_http_server
    tools = WebFetchTools(
        NetworkPolicy((NetworkAllowRule("other", "http", "127.0.0.1", server.server_port, "/allowed"),)),
        WebFetchToolConfig(timeout_seconds=2.0, max_response_bytes=4096),
    )

    result = tools.fetch_url(f"http://127.0.0.1:{server.server_port}/denied")

    assert result.ok is False
    assert result.error_kind == "permission_denied"
    assert result.data == {}
    assert handler.request_paths == []


@pytest.mark.parametrize("method", ["POST", "", 123])
def test_fetch_url_rejects_unsupported_method(local_http_server, method):
    server, handler = local_http_server
    tools = make_tools(server.server_port)

    result = tools.fetch_url(f"http://127.0.0.1:{server.server_port}/docs", method=method)

    assert result.ok is False
    assert result.error_kind == "invalid_input"
    assert result.data == {}
    assert handler.request_paths == []


def test_fetch_url_returns_connection_failure_for_allowed_unreachable_port():
    port = unused_local_port()
    tools = make_tools(port, timeout_seconds=0.2)

    result = tools.fetch_url(f"http://127.0.0.1:{port}/docs")

    assert result.ok is False
    assert result.error_kind == "fetch_failed"
    assert result.data == {}


def test_fetch_url_times_out(local_http_server):
    server, handler = local_http_server
    handler.delay_seconds = 0.3
    tools = make_tools(server.server_port, timeout_seconds=0.05)

    result = tools.fetch_url(f"http://127.0.0.1:{server.server_port}/slow")

    assert result.ok is False
    assert result.error_kind == "timeout"
    assert result.data == {}


def test_fetch_url_does_not_follow_redirect(local_http_server):
    server, handler = local_http_server
    handler.response_status = 301
    handler.response_reason = "Moved Permanently"
    handler.response_headers = {"Location": "/redirect-target"}
    handler.response_body = b"redirect"
    tools = make_tools(server.server_port)

    result = tools.fetch_url(f"http://127.0.0.1:{server.server_port}/redirect-source")

    assert result.ok is True
    assert result.data["status_code"] == 301
    assert result.data["body"] == "redirect"
    assert handler.request_paths == ["/redirect-source"]


def test_fetch_url_records_none_for_missing_content_type_and_reason(local_http_server):
    server, handler = local_http_server
    handler.response_status = 200
    handler.response_reason = None
    handler.response_content_type = None
    handler.response_body = b"no metadata"
    tools = make_tools(server.server_port)

    result = tools.fetch_url(f"http://127.0.0.1:{server.server_port}/metadata")

    assert result.ok is True
    assert result.data["content_type"] is None
    assert result.data["reason"] is None
```

- [ ] **Step 2: Run behavior tests and confirm fetch is not implemented**

Run:

```bash
pytest tests/test_web_fetch_tools.py::test_fetch_url_gets_allowed_local_http_response tests/test_web_fetch_tools.py::test_fetch_url_treats_http_status_as_completed_response tests/test_web_fetch_tools.py::test_fetch_url_truncates_body_and_hashes_stored_bytes tests/test_web_fetch_tools.py::test_fetch_url_records_decode_replacement_for_non_utf8_body tests/test_web_fetch_tools.py::test_fetch_url_denies_unallowed_url_without_request tests/test_web_fetch_tools.py::test_fetch_url_rejects_unsupported_method tests/test_web_fetch_tools.py::test_fetch_url_returns_connection_failure_for_allowed_unreachable_port tests/test_web_fetch_tools.py::test_fetch_url_times_out tests/test_web_fetch_tools.py::test_fetch_url_does_not_follow_redirect tests/test_web_fetch_tools.py::test_fetch_url_records_none_for_missing_content_type_and_reason -v
```

Expected before implementation:

```text
FAILED tests/test_web_fetch_tools.py::test_fetch_url_gets_allowed_local_http_response
FAILED tests/test_web_fetch_tools.py::test_fetch_url_treats_http_status_as_completed_response
FAILED tests/test_web_fetch_tools.py::test_fetch_url_truncates_body_and_hashes_stored_bytes
FAILED tests/test_web_fetch_tools.py::test_fetch_url_records_decode_replacement_for_non_utf8_body
FAILED tests/test_web_fetch_tools.py::test_fetch_url_denies_unallowed_url_without_request
FAILED tests/test_web_fetch_tools.py::test_fetch_url_rejects_unsupported_method
FAILED tests/test_web_fetch_tools.py::test_fetch_url_returns_connection_failure_for_allowed_unreachable_port
FAILED tests/test_web_fetch_tools.py::test_fetch_url_times_out
FAILED tests/test_web_fetch_tools.py::test_fetch_url_does_not_follow_redirect
FAILED tests/test_web_fetch_tools.py::test_fetch_url_records_none_for_missing_content_type_and_reason
```

- [ ] **Step 3: Add HTTP execution imports and no-redirect handler**

In `src/atomic_agent/web_fetch_tools.py`, add these imports near the top:

```python
from http.client import HTTPResponse
import socket
import urllib.error
import urllib.request
```

Add this class after constants:

```python
class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None
```

- [ ] **Step 4: Replace `fetch_url` stub with real execution**

Replace `WebFetchTools.fetch_url` and add helper methods inside `WebFetchTools`:

```python
    def fetch_url(self, url: str, method: str = "GET") -> WebFetchToolResult:
        if method != "GET":
            return self._failure(
                url if isinstance(url, str) else None,
                "invalid_input",
                "web_fetch only supports method GET",
            )
        decision = self.policy.decide(url)
        if decision.decision == "deny":
            return self._failure(
                url if isinstance(url, str) else None,
                "permission_denied",
                decision.reason,
            )

        request = urllib.request.Request(url=url, method="GET")
        opener = urllib.request.build_opener(_NoRedirectHandler)
        try:
            response = opener.open(request, timeout=self.config.timeout_seconds)
            return self._success_from_response(url, response, decision)
        except urllib.error.HTTPError as error:
            return self._success_from_response(url, error, decision)
        except TimeoutError:
            return self._failure(url, "timeout", "web_fetch exceeded timeout_seconds")
        except socket.timeout:
            return self._failure(url, "timeout", "web_fetch exceeded timeout_seconds")
        except urllib.error.URLError as error:
            reason = error.reason
            if isinstance(reason, TimeoutError) or isinstance(reason, socket.timeout):
                return self._failure(url, "timeout", "web_fetch exceeded timeout_seconds")
            return self._failure(url, "fetch_failed", str(reason) or error.__class__.__name__)
        except OSError as error:
            return self._failure(url, "fetch_failed", str(error) or error.__class__.__name__)

    def _success_from_response(
        self,
        url: str,
        response: HTTPResponse | urllib.error.HTTPError,
        decision: NetworkDecision,
    ) -> WebFetchToolResult:
        raw = response.read(self.config.max_response_bytes + 1)
        truncated = len(raw) > self.config.max_response_bytes
        stored = raw[: self.config.max_response_bytes]
        body, decoded_with_replacement = self._decode_body(stored)
        status_code = response.status if isinstance(response, HTTPResponse) else response.code
        reason = getattr(response, "reason", None)
        if reason is None:
            reason = getattr(response, "msg", None)
        content_type = response.headers.get("Content-Type") if response.headers is not None else None
        return WebFetchToolResult(
            ok=True,
            tool="web_fetch",
            url=url,
            data={
                "url": url,
                "method": "GET",
                "status_code": status_code,
                "reason": str(reason) if reason is not None else None,
                "content_type": content_type,
                "body": body,
                "body_sha256": self._sha256(stored),
                "body_size_bytes": len(stored),
                "body_truncated": truncated,
                "body_decoded_with_replacement": decoded_with_replacement,
                "matched_rule_id": decision.matched_rule_id,
                "timeout_seconds": self.config.timeout_seconds,
                "max_response_bytes": self.config.max_response_bytes,
            },
        )

    def _decode_body(self, content: bytes) -> tuple[str, bool]:
        try:
            return content.decode("utf-8"), False
        except UnicodeDecodeError:
            return content.decode("utf-8", errors="replace"), True

    def _sha256(self, content: bytes) -> str:
        return f"sha256:{hashlib.sha256(content).hexdigest()}"

    def _failure(self, url: str | None, error_kind: str, error_message: str) -> WebFetchToolResult:
        return WebFetchToolResult(
            ok=False,
            tool="web_fetch",
            url=url,
            data={},
            error_kind=error_kind,
            error_message=error_message,
        )
```

- [ ] **Step 5: Run web fetch tool tests and confirm they pass**

Run:

```bash
pytest tests/test_web_fetch_tools.py -v
```

Expected:

```text
PASSED
```

If timeout tests leave a `BrokenPipeError` in server logs, keep `RecordingHandler.log_message` disabled and verify pytest output remains passing; do not weaken timeout assertions.

---

### Task 4: Add dispatcher tests and complete `execute_web_fetch_action`

**Files:**

- Modify: `tests/test_web_fetch_tools.py`
- Verify: `src/atomic_agent/web_fetch_tools.py`

- [ ] **Step 1: Add dispatcher tests**

Append to `tests/test_web_fetch_tools.py`:

```python


def test_execute_web_fetch_action_dispatches_web_fetch(local_http_server):
    server, handler = local_http_server
    handler.response_body = b"dispatch"
    tools = make_tools(server.server_port)
    action = AgentAction(
        action_id="step-web",
        action=AgentActionType.WEB_FETCH,
        reason_summary="Fetch allowed URL.",
        input={"url": f"http://127.0.0.1:{server.server_port}/dispatch"},
    )

    result = execute_web_fetch_action(action, tools)

    assert result.ok is True
    assert result.tool == "web_fetch"
    assert result.data["body"] == "dispatch"
    assert handler.request_paths == ["/dispatch"]


def test_execute_web_fetch_action_rejects_non_web_fetch_action(local_http_server):
    server, handler = local_http_server
    tools = make_tools(server.server_port)
    action = AgentAction(
        action_id="step-read",
        action=AgentActionType.READ_FILE,
        reason_summary="Read a file.",
        input={"path": "README.md"},
    )

    result = execute_web_fetch_action(action, tools)

    assert result.ok is False
    assert result.tool == "read_file"
    assert result.url is None
    assert result.error_kind == "unsupported_action"
    assert result.data == {}
    assert handler.request_paths == []
```

- [ ] **Step 2: Run dispatcher tests**

Run:

```bash
pytest tests/test_web_fetch_tools.py::test_execute_web_fetch_action_dispatches_web_fetch tests/test_web_fetch_tools.py::test_execute_web_fetch_action_rejects_non_web_fetch_action -v
```

Expected:

```text
PASSED
```

The initial dispatcher from Task 2 should already pass after Task 3 implements `fetch_url`.

---

### Task 5: Integrate `web_fetch` into AgentLoop

**Files:**

- Modify: `tests/test_agent_loop.py`
- Modify: `src/atomic_agent/agent_loop.py`

- [ ] **Step 1: Add imports and helper factory to `tests/test_agent_loop.py`**

Add this import near the existing command/filesystem imports:

```python
from atomic_agent.web_fetch_tools import NetworkAllowRule, NetworkPolicy, WebFetchToolConfig, WebFetchTools
```

Add this helper after `make_loop` or before tests:

```python

def make_web_fetch_tools(port, path_prefix="/"):
    return WebFetchTools(
        NetworkPolicy(
            (
                NetworkAllowRule(
                    rule_id="local-agent-loop",
                    scheme="http",
                    host="127.0.0.1",
                    port=port,
                    path_prefix=path_prefix,
                ),
            )
        ),
        WebFetchToolConfig(timeout_seconds=2.0, max_response_bytes=4096),
    )
```

- [ ] **Step 2: Update `make_loop` to accept `web_fetch_tools`**

Change the function signature from:

```python
def make_loop(tmp_path, provider, runtime_clock=None):
```

To:

```python
def make_loop(tmp_path, provider, runtime_clock=None, web_fetch_tools=None):
```

Add `web_fetch_tools=web_fetch_tools` to `AgentLoopDependencies`:

```python
        AgentLoopDependencies(
            provider=provider,
            filesystem_tools=filesystem_tools,
            command_tools=command_tools,
            event_recorder=recorder,
            artifact_writer=artifact_writer,
            runtime_clock=runtime_clock,
            web_fetch_tools=web_fetch_tools,
        ),
```

- [ ] **Step 3: Replace old `web_fetch_not_implemented` runtime error case**

In `test_agent_loop_fails_closed_for_runtime_errors`, replace the old parameter entry:

```python
        (
            "web_fetch_not_implemented",
            [action("step-web", "web_fetch", {"url": "https://example.com"})],
            {"tools": ["web_fetch", "submit_result"]},
            "policy_denied",
            "step-web",
            "permission.decided",
        ),
```

With:

```python
        (
            "web_fetch_without_network_policy",
            [action("step-web", "web_fetch", {"url": "http://127.0.0.1:1/docs"})],
            {"tools": ["web_fetch", "submit_result"]},
            "policy_denied",
            "step-web",
            "permission.decided",
        ),
```

- [ ] **Step 4: Add local HTTP server helper to `tests/test_agent_loop.py`**

Add these imports near the top:

```python
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
```

Add this handler and fixture after `FakeRuntimeClock`:

```python
class AgentLoopWebHandler(BaseHTTPRequestHandler):
    response_body = b"loop body"
    request_paths = []

    def do_GET(self):
        self.__class__.request_paths.append(self.path)
        self.send_response(200, "OK")
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(self.response_body)

    def log_message(self, format, *args):
        return


@pytest.fixture
def agent_loop_http_server():
    class Handler(AgentLoopWebHandler):
        response_body = b"loop body"
        request_paths = []

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server, Handler
    finally:
        server.shutdown()
        thread.join(timeout=2.0)
        server.server_close()
```

- [ ] **Step 5: Add AgentLoop web fetch tests**

Append to `tests/test_agent_loop.py`:

```python


def test_agent_loop_fails_closed_when_web_fetch_policy_is_not_configured(tmp_path):
    provider = ScriptedProvider([action("step-web", "web_fetch", {"url": "http://127.0.0.1:1/docs"})])
    loop, event_stream_path = make_loop(tmp_path, provider)
    invocation = make_invocation(tmp_path, tools=["web_fetch", "submit_result"])

    result = loop.run(invocation)

    assert result.status == AgentRunStatus.FAILED
    assert result.failure_kind == "policy_denied"
    assert result.failed_action_ref == "step-web"
    assert "network policy is not configured" in result.failure_message
    event_types = [event["type"] for event in read_jsonl(event_stream_path)]
    assert "permission.decided" in event_types
    assert "tool.attempt.started" not in event_types
    assert event_types[-1] == "run.failed"



def test_agent_loop_fails_closed_when_web_fetch_url_is_not_allowed(tmp_path, agent_loop_http_server):
    server, handler = agent_loop_http_server
    provider = ScriptedProvider([action("step-web", "web_fetch", {"url": f"http://127.0.0.1:{server.server_port}/denied"})])
    loop, event_stream_path = make_loop(
        tmp_path,
        provider,
        web_fetch_tools=make_web_fetch_tools(server.server_port, path_prefix="/allowed"),
    )
    invocation = make_invocation(tmp_path, tools=["web_fetch", "submit_result"])

    result = loop.run(invocation)

    assert result.status == AgentRunStatus.FAILED
    assert result.failure_kind == "policy_denied"
    assert result.failed_action_ref == "step-web"
    assert handler.request_paths == []
    event_types = [event["type"] for event in read_jsonl(event_stream_path)]
    assert "permission.decided" in event_types
    assert "tool.attempt.started" not in event_types
    assert event_types[-1] == "run.failed"



def test_agent_loop_executes_web_fetch_and_records_network_event(tmp_path, agent_loop_http_server):
    server, handler = agent_loop_http_server
    handler.response_body = b"loop body"
    provider = ScriptedProvider(
        [
            action("step-web", "web_fetch", {"url": f"http://127.0.0.1:{server.server_port}/allowed"}),
            action(
                "step-submit",
                "submit_result",
                {
                    "summary": "Fetched allowed URL.",
                    "produced_paths": [],
                    "evidence_refs": ["step-web"],
                },
            ),
        ]
    )
    loop, event_stream_path = make_loop(
        tmp_path,
        provider,
        web_fetch_tools=make_web_fetch_tools(server.server_port, path_prefix="/allowed"),
    )
    invocation = make_invocation(tmp_path, tools=["web_fetch", "submit_result"])

    result = loop.run(invocation)

    assert result.status == AgentRunStatus.COMPLETED
    assert result.summary == "Fetched allowed URL."
    assert handler.request_paths == ["/allowed"]
    assert len(result.tool_attempts) == 1
    assert result.tool_attempts[0]["tool"] == "web_fetch"
    assert any(artifact["artifact_ref"].endswith("network/tool_attempt_000001.response.txt") for artifact in result.artifacts)
    event_types = [event["type"] for event in read_jsonl(event_stream_path)]
    assert event_types == [
        "run.started",
        "provider.turn.started",
        "provider.turn.completed",
        "action.parsed",
        "permission.decided",
        "tool.attempt.started",
        "tool.attempt.completed",
        "network.fetch.completed",
        "provider.turn.started",
        "provider.turn.completed",
        "action.parsed",
        "permission.decided",
        "result.submitted",
        "run.completed",
    ]
    network_events = [event for event in read_jsonl(event_stream_path) if event["type"] == "network.fetch.completed"]
    assert len(network_events) == 1
    assert network_events[0]["payload"]["url"] == f"http://127.0.0.1:{server.server_port}/allowed"
    assert network_events[0]["payload"]["status_code"] == 200
    assert network_events[0]["payload"]["response"]["artifact_ref"].endswith("network/tool_attempt_000001.response.txt")


def test_agent_loop_records_tool_attempt_failed_when_web_fetch_times_out(tmp_path, agent_loop_http_server):
    server, handler = agent_loop_http_server
    handler.delay_seconds = 0.3
    provider = ScriptedProvider([action("step-web", "web_fetch", {"url": f"http://127.0.0.1:{server.server_port}/slow"})])
    slow_tools = WebFetchTools(
        NetworkPolicy((NetworkAllowRule("local-slow", "http", "127.0.0.1", server.server_port, "/slow"),)),
        WebFetchToolConfig(timeout_seconds=0.05, max_response_bytes=4096),
    )
    loop, event_stream_path = make_loop(tmp_path, provider, web_fetch_tools=slow_tools)
    invocation = make_invocation(tmp_path, tools=["web_fetch", "submit_result"])

    result = loop.run(invocation)

    assert result.status == AgentRunStatus.FAILED
    assert result.failure_kind == "tool_failed"
    assert result.failed_action_ref == "step-web"
    assert "timeout" in result.failure_message
    event_types = [event["type"] for event in read_jsonl(event_stream_path)]
    assert event_types[-3:] == ["tool.attempt.started", "tool.attempt.failed", "run.failed"]
    assert "network.fetch.completed" not in event_types
```

- [ ] **Step 6: Run AgentLoop web fetch tests and confirm integration is missing**

Run:

```bash
pytest tests/test_agent_loop.py::test_agent_loop_fails_closed_when_web_fetch_policy_is_not_configured tests/test_agent_loop.py::test_agent_loop_fails_closed_when_web_fetch_url_is_not_allowed tests/test_agent_loop.py::test_agent_loop_executes_web_fetch_and_records_network_event tests/test_agent_loop.py::test_agent_loop_records_tool_attempt_failed_when_web_fetch_times_out -v
```

Expected before implementation:

```text
TypeError: AgentLoopDependencies.__init__() got an unexpected keyword argument 'web_fetch_tools'
```

- [ ] **Step 7: Add web fetch imports and dependency to `agent_loop.py`**

In `src/atomic_agent/agent_loop.py`, add this import:

```python
from atomic_agent.web_fetch_tools import WebFetchToolResult, WebFetchTools, execute_web_fetch_action
```

Change `AgentLoopDependencies` from:

```python
@dataclass(frozen=True)
class AgentLoopDependencies:
    provider: ProviderAdapter
    filesystem_tools: FilesystemTools
    command_tools: CommandTools
    event_recorder: EventRecorder
    artifact_writer: ArtifactWriter
    runtime_clock: Callable[[], float]
```

To:

```python
@dataclass(frozen=True)
class AgentLoopDependencies:
    provider: ProviderAdapter
    filesystem_tools: FilesystemTools
    command_tools: CommandTools
    event_recorder: EventRecorder
    artifact_writer: ArtifactWriter
    runtime_clock: Callable[[], float]
    web_fetch_tools: WebFetchTools | None = None
```

- [ ] **Step 8: Replace hard-coded web fetch denial with NetworkPolicy decision**

Replace this block in `_decide_permission`:

```python
        if action.action == AgentActionType.WEB_FETCH:
            return PermissionDecision("deny", "web_fetch is not implemented in P0-007", requirements.policy_ref)
```

With:

```python
        if action.action == AgentActionType.WEB_FETCH:
            if self.dependencies.web_fetch_tools is None:
                return PermissionDecision("deny", "network policy is not configured", requirements.policy_ref)
            decision = self.dependencies.web_fetch_tools.policy.decide(action.input.get("url"))
            if decision.decision == "deny":
                return PermissionDecision("deny", decision.reason, requirements.policy_ref)
            return PermissionDecision("allow", decision.reason, requirements.policy_ref)
```

- [ ] **Step 9: Dispatch `WEB_FETCH` to the new tool**

Change `_execute_tool_action` signature from:

```python
    def _execute_tool_action(self, action: AgentAction) -> FileToolResult | CommandToolResult:
```

To:

```python
    def _execute_tool_action(self, action: AgentAction) -> FileToolResult | CommandToolResult | WebFetchToolResult:
```

Add this branch before the final `raise`:

```python
        if action.action == AgentActionType.WEB_FETCH:
            if self.dependencies.web_fetch_tools is None:
                return WebFetchToolResult(
                    ok=False,
                    tool="web_fetch",
                    url=action.input.get("url") if isinstance(action.input.get("url"), str) else None,
                    data={},
                    error_kind="permission_denied",
                    error_message="network policy is not configured",
                )
            return execute_web_fetch_action(action, self.dependencies.web_fetch_tools)
```

- [ ] **Step 10: Update type unions and result payloads**

Change `_record_tool_result`, `_record_workspace_mutation_if_needed`, `_record_command_completed_if_needed`, and `_tool_result_payload` result type annotations from:

```python
FileToolResult | CommandToolResult
```

To:

```python
FileToolResult | CommandToolResult | WebFetchToolResult
```

In `_tool_result_payload`, add this branch after the command branch:

```python
        if isinstance(result, WebFetchToolResult):
            payload["url"] = result.url
```

- [ ] **Step 11: Record network response artifact and event**

In `_record_tool_result`, after:

```python
            self._record_workspace_mutation_if_needed(state, action, tool_attempt_id, result)
            self._record_command_completed_if_needed(state, tool_attempt_id, result)
```

Add:

```python
            self._record_network_fetch_completed_if_needed(state, tool_attempt_id, result)
```

Add this method after `_record_command_completed_if_needed`:

```python
    def _record_network_fetch_completed_if_needed(
        self,
        state: _RunState,
        tool_attempt_id: str,
        result: FileToolResult | CommandToolResult | WebFetchToolResult,
    ) -> None:
        if not isinstance(result, WebFetchToolResult):
            return
        response_artifact = self.dependencies.artifact_writer.write_text(
            f"network/{tool_attempt_id}.response.txt",
            result.data["body"],
            truncated_in_observation=result.data["body_truncated"],
        )
        state.artifacts.append(response_artifact)
        self.dependencies.event_recorder.record_network_fetch_completed(
            tool_attempt_id,
            result.url or "",
            result.data["status_code"],
            response_artifact,
        )
```

- [ ] **Step 12: Run AgentLoop web fetch tests and confirm they pass**

Run:

```bash
pytest tests/test_agent_loop.py::test_agent_loop_fails_closed_when_web_fetch_policy_is_not_configured tests/test_agent_loop.py::test_agent_loop_fails_closed_when_web_fetch_url_is_not_allowed tests/test_agent_loop.py::test_agent_loop_executes_web_fetch_and_records_network_event tests/test_agent_loop.py::test_agent_loop_records_tool_attempt_failed_when_web_fetch_times_out -v
```

Expected:

```text
PASSED
```

---

### Task 6: Preserve existing runtime behavior and run focused verification

**Files:**

- Verify: `src/atomic_agent/models.py`
- Verify: `src/atomic_agent/web_fetch_tools.py`
- Verify: `src/atomic_agent/agent_loop.py`
- Verify: related tests

- [ ] **Step 1: Run model and parser tests**

Run:

```bash
pytest tests/test_models.py tests/test_action_parser.py -v
```

Expected:

```text
PASSED
```

- [ ] **Step 2: Run web fetch tool tests**

Run:

```bash
pytest tests/test_web_fetch_tools.py -v
```

Expected:

```text
PASSED
```

- [ ] **Step 3: Run AgentLoop tests**

Run:

```bash
pytest tests/test_agent_loop.py -v
```

Expected:

```text
PASSED
```

- [ ] **Step 4: Run event recorder tests**

Run:

```bash
pytest tests/test_event_recorder.py -v
```

Expected:

```text
PASSED
```

- [ ] **Step 5: Run command tests to confirm network-enabled commands remain rejected**

Run:

```bash
pytest tests/test_command_tools.py::test_command_policy_rejects_invalid_command_spec -v
```

Expected:

```text
PASSED
```

The parameter case with `CommandSpec(..., allow_network=True)` must still fail closed during policy construction.

---

### Task 7: Run full verification and safety scans

**Files:**

- Verify: all implementation and docs touched by P1-001

- [ ] **Step 1: Run full test suite**

Run:

```bash
pytest -v
```

Expected:

```text
PASSED
```

- [ ] **Step 2: Check runtime source for environment fallback reads**

Run:

```bash
python - <<'PY'
from pathlib import Path
for path in Path('src/atomic_agent').rglob('*.py'):
    text = path.read_text(encoding='utf-8')
    for needle in ('os.environ', 'getenv', 'dotenv', '.env'):
        if needle in text:
            print(f'{path}: contains {needle}')
PY
```

Expected:

```text

```

No output means runtime source does not read environment fallback. If output appears in executable runtime code, remove that fallback and pass configuration explicitly.

- [ ] **Step 3: Check web fetch source for forbidden network fallback patterns**

Run:

```bash
python - <<'PY'
from pathlib import Path
text = Path('src/atomic_agent/web_fetch_tools.py').read_text(encoding='utf-8')
for forbidden in ('HTTPRedirectHandler.redirect_request(req', 'default_allow', 'allow_all', 'headers=', 'data=', 'method="POST"', 'method="PUT"'):
    if forbidden in text:
        print(f'forbidden web_fetch pattern: {forbidden}')
PY
```

Expected:

```text

```

No output means the web fetch implementation does not advertise default allow, request body, custom headers, or non-GET methods. The `_NoRedirectHandler` class name is allowed; the forbidden scan targets redirect follow behavior rather than class declaration.

- [ ] **Step 4: Check command network escape hatch remains closed**

Run:

```bash
python - <<'PY'
from pathlib import Path
text = Path('src/atomic_agent/command_tools.py').read_text(encoding='utf-8')
if 'P0-005 does not support network-enabled commands' not in text:
    print('command_tools.py no longer rejects allow_network=True')
PY
```

Expected:

```text

```

No output means command network enablement remains fail-closed.

- [ ] **Step 5: Check working tree scope**

Run:

```bash
git status --short
```

Expected before docs completion updates:

```text
 M docs/INDEX.md
 M docs/04-implementation-plan/INDEX.md
 M docs/04-implementation-spec/INDEX.md
 M src/atomic_agent/agent_loop.py
 M src/atomic_agent/models.py
 M tests/test_action_parser.py
 M tests/test_agent_loop.py
 M tests/test_models.py
?? docs/04-implementation-plan/P1-001-web-fetch-network-policy-plan.md
?? docs/04-implementation-spec/P1-001-web-fetch-network-policy-spec.md
?? src/atomic_agent/web_fetch_tools.py
?? tests/test_web_fetch_tools.py
```

If `git status --short` shows unrelated files, inspect them before continuing and do not include unrelated changes in this task.

---

### Task 8: Update docs after implementation passes

**Files:**

- Modify: `docs/04-implementation-backlog/backlog.md`
- Modify: `docs/04-implementation-spec/P1-001-web-fetch-network-policy-spec.md`
- Modify: `docs/04-implementation-plan/P1-001-web-fetch-network-policy-plan.md`
- Modify: `docs/04-implementation-spec/INDEX.md`
- Modify: `docs/04-implementation-plan/INDEX.md`
- Modify: `docs/INDEX.md`

- [ ] **Step 1: Mark P1-001 completed only after tests pass**

Change `docs/04-implementation-backlog/backlog.md` from:

```markdown
| P1-001 | 实现 `web_fetch` 和 NetworkPolicy（网络策略） | pending | `mvp-runtime-spec.md`, `agent-action-protocol.md`, `event-stream-protocol.md` |
```

To:

```markdown
| P1-001 | 实现 `web_fetch` 和 NetworkPolicy（网络策略） | completed | `P1-001-web-fetch-network-policy-spec.md`, `mvp-runtime-spec.md`, `agent-action-protocol.md`, `event-stream-protocol.md` |
```

- [ ] **Step 2: Mark spec implemented**

Change `docs/04-implementation-spec/P1-001-web-fetch-network-policy-spec.md` from:

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

Change `docs/04-implementation-plan/P1-001-web-fetch-network-policy-plan.md` from:

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
| `P1-001-web-fetch-network-policy-spec.md` | draft | 定义 P1-001 web_fetch（网络获取）和 NetworkPolicy（网络策略）的输入、输出、权限边界、事件和失败语义 | 实现 P1-001 前 |
```

Add this completed row:

```markdown
| `P1-001-web-fetch-network-policy-spec.md` | 2026-06-06 | 已实现 P1-001 web_fetch（网络获取）和 NetworkPolicy（网络策略），保留为网络工具规格记录 |
```

- [ ] **Step 5: Move plan index entry to completed / archived**

Remove this active row from `docs/04-implementation-plan/INDEX.md`:

```markdown
| `P1-001-web-fetch-network-policy-plan.md` | draft | 实施 P1-001 web_fetch（网络获取）和 NetworkPolicy（网络策略）的 TDD 计划 | 执行 P1-001 时 |
```

Add this completed row:

```markdown
| `P1-001-web-fetch-network-policy-plan.md` | 2026-06-06 | 已实施 P1-001 web_fetch（网络获取）和 NetworkPolicy（网络策略），保留为 TDD 实施记录 |
```

- [ ] **Step 6: Remove P1-001 draft pointers from global active documents after completion**

Remove the P1-001 spec and plan rows from `docs/INDEX.md` Current Active Documents（当前活跃文档指针） after they move to completed sections in their subdirectory indexes.

- [ ] **Step 7: Run final verification after docs updates**

Run:

```bash
pytest -v
git status --short
```

Expected:

```text
PASSED
```

`git status --short` should show only P1-001 implementation, tests, and required docs/index/backlog updates.

---

## Self-Review Checklist

Before implementation is considered ready for user review:

- [ ] Spec coverage: Every requirement in `docs/04-implementation-spec/P1-001-web-fetch-network-policy-spec.md` is covered by a task, test, or explicit out-of-scope statement, including AgentLoop network failure events（智能体循环网络失败事件）、redirect no-follow（不跟随重定向） and missing `content_type` / `reason` values（缺失内容类型 / 原因短语值）。
- [ ] Placeholder scan: This plan contains no placeholder markers, no deferred behavior inside P1-001 scope, no mock success path, and no silent fallback.
- [ ] Type consistency: `NetworkAllowRule`, `NetworkDecision`, `NetworkPolicy`, `WebFetchToolConfig`, `WebFetchToolResult`, `WebFetchToolConfigError`, `WebFetchTools`, `execute_web_fetch_action`, `web_fetch_tools`, and `network.fetch.completed` names match across tests, implementation steps, and spec.
- [ ] Scope check: No POST/body/header/auth/proxy/redirect-follow/DNS policy/OS sandbox/network-enabled command/Boardroom adapter/README minimal example is included.
- [ ] Reuse check: The plan reuses existing `AgentAction`, `AgentLoop`, `EventRecorder`, `ArtifactWriter`, `AgentRunResult`, and dispatcher patterns instead of creating a second runtime or event system.
- [ ] Fail-closed check: Missing network policy, denied URL, invalid URL, unsupported method, timeout, connection failure, and unconfigured `web_fetch_tools` all return failed results or denied decisions with terminal events where applicable.
- [ ] Evidence check: Successful network fetch stores response body as an artifact and records `network.fetch.completed`; large response content does not get embedded directly in the event stream.
- [ ] Verification check: `pytest -v`, environment fallback scan, forbidden web fetch pattern scan, and command network escape hatch scan pass before any completion claim.

## Self-Review Result

- Spec coverage（规格覆盖）：计划任务覆盖 `web_fetch` input schema（输入模式）、NetworkPolicy（网络策略）、WebFetchTools（网络获取工具集合）、AgentLoop（智能体循环）权限/执行/事件接入、安全扫描和文档完成更新；P1-002/P1-003/P1-004 均明确不在范围内。
- Placeholder scan（占位符扫描）：未使用占位标记、未完成提示、空泛“补充错误处理”或未定义测试要求。
- Type consistency（类型一致性）：规格与计划中的公开符号、字段、错误类型和事件名称保持一致。
- Scope check（范围检查）：未纳入非 GET 方法、请求正文、自定义 headers、自动 redirect、DNS/IP 策略、OS-level network sandbox、允许网络命令、Boardroom adapter 或 README minimal example。
- No-fallback check（无兜底检查）：计划要求显式 NetworkPolicy、显式 WebFetchToolConfig、未配置即拒绝、未允许 URL 不发请求、网络异常不伪成功、命令网络仍关闭。
