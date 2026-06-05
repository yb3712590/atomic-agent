# Web Fetch and Network Policy Specification

## Status

implemented

## Purpose

本文定义 P1-001 `web_fetch`（网络获取）和 `NetworkPolicy`（网络策略）的实现规格。该能力负责让 `atomic-agent`（原子智能体）在受控网络边界内执行真实 HTTP GET（HTTP 获取）请求，并把网络访问结果纳入现有 permission decision（权限判定）、tool attempt（工具调用尝试）、artifact（产物）和 JSONL event stream（JSONL 事件流）。

P1-001 的目标不是提供通用浏览器、爬虫、任意 HTTP client（HTTP 客户端）或网络沙箱，而是补齐 MVP runtime（最小可行运行时）中 `web_fetch` 的最小可审计能力：默认拒绝、显式允许、真实获取、受限输出、失败关闭。

## Scope

P1-001 覆盖以下能力：

- 定义 `NetworkPolicy`（网络策略）作为 `web_fetch` 可访问目标的唯一 allowlist（允许列表）事实源。
- 定义 `NetworkAllowRule`（网络允许规则），支持按 scheme（协议）、host（主机）、port（端口）和 path prefix（路径前缀）做精确允许。
- 实现 `web_fetch`（网络获取）工具，只支持 HTTP GET（HTTP 获取）语义。
- 在工具层和 `AgentLoop`（智能体循环）权限层都执行网络策略检查，避免绕过分发器直接调用工具时访问未允许 URL。
- 在 `AgentLoopDependencies`（智能体循环依赖）中接入可选 `web_fetch_tools`（网络获取工具集合）依赖；缺失时对 `web_fetch` fail closed（失败关闭）并记录拒绝事件。
- 使用 explicit config（显式配置）控制 timeout（超时）和 max response bytes（最大响应字节数）。
- 把 response body（响应正文）作为 artifact（产物）记录，并通过 `network.fetch.completed`（网络获取完成）事件引用。
- 保留现有 `tool.attempt.started`、`tool.attempt.completed`、`tool.attempt.failed`、`permission.decided` 和 terminal event（终止事件）语义。
- 使用本地可控 HTTP server（HTTP 服务器）测试成功和失败路径，不依赖外部公网稳定性。

不包含：

- 不实现 POST、PUT、PATCH、DELETE 或自定义 method（方法）。
- 不实现 request body（请求正文）。
- 不实现自定义 request headers（请求头）、cookie（Cookie）、认证、代理或 TLS 配置。
- 不跟随 redirect（重定向）；P1-001 必须把重定向响应作为普通 HTTP response（HTTP 响应）事实处理，不能自动访问新目标。
- 不实现 robots.txt、爬虫调度、浏览器自动化或 HTML 解析。
- 不实现 DNS policy（DNS 策略）、IP range policy（IP 网段策略）或 OS-level network sandbox（操作系统级网络沙箱）。
- 不修改 `run_command`（运行声明命令）的 `allow_network=False` fail-closed 规则，不允许命令借 P1-001 获得网络能力。
- 不实现 Boardroom `AgentRuntimePort adapter`（Boardroom 智能体运行时端口适配器）。
- 不更新 README minimal example（最小示例）；P1-003 在真实 CLI command（命令行命令）稳定后处理。

## Authoritative Inputs

本规格依据以下已索引文档：

- `docs/04-implementation-backlog/backlog.md`（实现待办），其中 P1-001 为 pending（待执行）任务。
- `docs/04-implementation-spec/mvp-runtime-spec.md`（MVP 运行时规格），要求 `web_fetch` 受 network allowlist guard（网络允许列表守卫）约束。
- `docs/04-implementation-acceptance/mvp-acceptance.md`（MVP 验收标准），要求访问未允许网络目标必须 deny（拒绝）并记录失败事件。
- `docs/03-contracts/agent-action-protocol.md`（智能体动作协议），定义 `web_fetch` 动作。
- `docs/03-contracts/event-stream-protocol.md`（事件流协议），定义 `network.fetch.completed` 事件。
- `docs/05-testing/testing-strategy.md`（测试策略），要求覆盖网络拒绝负向场景。
- `docs/09-adr/0003-use-fail-closed-permission-model.md`（失败关闭权限模型 ADR）。

## Public API

### `AgentAction` input schema（动作输入模式）

P1-001 要求 `web_fetch` 的 `AgentAction.input`（智能体动作输入）满足：

```json
{
  "url": "https://example.com/docs",
  "method": "GET"
}
```

字段规则：

| Field | 中文解释 | 约束 | 失败语义 |
|---|---|---|---|
| `url` | 网络目标 URL | 必填，非空字符串 | `schema_validation_failed` |
| `method` | HTTP 方法 | 可省略；如提供，必须等于 `GET` | `schema_validation_failed` |

规则：

- `input` 只能包含 `url` 和可选 `method`。
- `method` 省略时按 `GET` 处理，但这不是隐藏 fallback（兜底）：P1-001 只定义一种方法，省略字段等价于协议默认 GET。
- URL 的 scheme / host / port / path 是否允许由 `NetworkPolicy`（网络策略）判定，不在 Pydantic model（Pydantic 模型）层访问网络或解析 DNS。
- `web_fetch` 不接受 `headers`、`body`、`command`、`shell`、`timeout`、`max_response_bytes` 等字段；timeout 和 response size limit（响应大小限制）来自 `WebFetchToolConfig`（网络获取工具配置）。

### 新增模块

新增模块：

```text
src/atomic_agent/web_fetch_tools.py
```

公开类型和函数：

| Symbol | 中文解释 | Contract |
|---|---|---|
| `NetworkAllowRule` | 网络允许规则 | frozen dataclass，字段为 `rule_id: str`、`scheme: str`、`host: str`、`port: int | None`、`path_prefix: str` |
| `NetworkDecision` | 网络策略判定 | frozen dataclass，字段为 `decision: Literal["allow", "deny"]`、`reason: str`、`matched_rule_id: str | None` |
| `NetworkPolicy` | 网络策略 | 初始化接收 `rules: tuple[NetworkAllowRule, ...]`，通过 `decide(url: str) -> NetworkDecision` 判定目标 |
| `WebFetchToolConfig` | 网络获取工具配置 | frozen dataclass，字段为 `timeout_seconds: float`、`max_response_bytes: int` |
| `WebFetchToolResult` | 网络获取工具结果 | frozen dataclass，字段为 `ok: bool`、`tool: str`、`url: str | None`、`data: dict[str, Any]`、`error_kind: str | None`、`error_message: str | None` |
| `WebFetchToolConfigError` | 网络工具配置错误 | `ValueError` 子类，用于非法 policy/config（策略/配置） |
| `WebFetchTools` | 网络获取工具集合 | 初始化接收 `NetworkPolicy` 和 `WebFetchToolConfig`，并通过 `fetch_url(url: str, method: str = "GET") -> WebFetchToolResult` 执行获取 |
| `execute_web_fetch_action` | 执行网络获取动作 | 接收 `AgentAction` 和 `WebFetchTools`，只分发 `WEB_FETCH` |

`WebFetchTools`（网络获取工具集合）必须接收显式 `NetworkPolicy` 和 `WebFetchToolConfig`。runtime code（运行时代码）不得在工具实现中硬编码 allowlist（允许列表）、timeout（超时）、response size limit（响应大小限制）或网络目标。

### `AgentLoopDependencies.web_fetch_tools`

P1-001 修改 `src/atomic_agent/agent_loop.py` 中的 `AgentLoopDependencies`（智能体循环依赖）：

| Field | 中文解释 | Contract |
|---|---|---|
| `web_fetch_tools` | 网络获取工具集合 | `WebFetchTools | None = None` |

规则：

- `web_fetch_tools is None` 表示 runtime 没有配置网络策略和网络工具。
- 当 provider（模型供应商）请求 `web_fetch` 且 `web_fetch_tools is None` 时，`AgentLoop` 必须 deny（拒绝）并记录 `permission.decided`、`action.rejected` 和 `run.failed`。
- `AgentLoop` 不得在 `web_fetch_tools` 缺失时创建默认 allowlist、读取环境变量、访问 `.env` 或用任何默认 URL policy（URL 策略）补齐。
- 现有测试和调用方未配置 `web_fetch_tools` 时，非 `web_fetch` 行为不得改变。

## NetworkPolicy Semantics

### Rule validation（规则校验）

`NetworkAllowRule` 字段规则：

| Field | 中文解释 | 约束 |
|---|---|---|
| `rule_id` | 规则标识 | 非空稳定字符串，模式 `^[A-Za-z0-9_.:-]+$` |
| `scheme` | 协议 | 必须是 `http` 或 `https` |
| `host` | 主机 | 非空字符串，按 lowercase（小写）精确匹配 |
| `port` | 端口 | `None` 或 `1..65535` 的整数；`bool` 不合法 |
| `path_prefix` | 路径前缀 | 必须以 `/` 开头 |

`NetworkPolicy` 可以接收空规则集合。空规则集合不是 fallback，它表示显式 deny-all policy（全部拒绝策略）。

非法规则必须在 `NetworkPolicy` 初始化时抛出 `WebFetchToolConfigError`，不得在执行请求时静默忽略。

### URL validation（URL 校验）

`NetworkPolicy.decide(url)` 必须 fail closed（失败关闭）处理：

- `url` 必须是非空字符串。
- scheme 必须是 `http` 或 `https`。
- URL 必须包含 host。
- URL 不得包含 username/password userinfo（用户信息）。
- URL 不得包含 fragment（片段），避免记录和比较语义不一致。
- URL port（端口）如非法，必须 deny。
- 如果 rule（规则）未声明 port：
  - `http` 只匹配有效端口 `80`。
  - `https` 只匹配有效端口 `443`。
- 如果 rule 声明 port，则 URL effective port（有效端口）必须完全相等。
- path（路径）必须以对应 rule 的 `path_prefix` 开头。
- query string（查询字符串）允许存在，但不参与 path prefix 匹配。

匹配成功返回：

```text
decision = "allow"
reason = "network target allowed by rule <rule_id>"
matched_rule_id = "<rule_id>"
```

匹配失败返回：

```text
decision = "deny"
reason = <stable human-readable reason>
matched_rule_id = None
```

### Default deny（默认拒绝）

所有未被规则显式允许的 URL 都必须 deny（拒绝）。不得进行以下 fallback（兜底）：

- 不得把 unknown host（未知主机）改写为 allowed host（允许主机）。
- 不得忽略 port（端口）。
- 不得把 `http` 自动升级为 `https` 或反向降级。
- 不得跟随 redirect 后再判定新 URL。
- 不得对 IP、DNS CNAME（规范名）或本机网络做隐式放行。

## Web Fetch Semantics

### Request behavior（请求行为）

`WebFetchTools.fetch_url(url, method="GET")` 必须：

1. 校验 `method == "GET"`。
2. 调用 `NetworkPolicy.decide(url)`。
3. 如果 policy deny（策略拒绝），返回 `ok=False` 和 `error_kind="permission_denied"`，不得发起网络请求。
4. 使用 `WebFetchToolConfig.timeout_seconds` 作为 HTTP request timeout（HTTP 请求超时）。
5. 最多读取 `WebFetchToolConfig.max_response_bytes + 1` bytes（字节），用于判断是否截断。
6. 将最多 `max_response_bytes` bytes 解码为 UTF-8 text（UTF-8 文本）；无法解码时使用 replacement character（替换字符），并记录 `body_decoded_with_replacement=True`。
7. 对 HTTP status code（HTTP 状态码）不做成功/失败语义映射；只要真实收到 HTTP response（HTTP 响应），包括 3xx/4xx/5xx，都返回 `ok=True`。
8. 对 timeout、DNS failure（DNS 失败）、connection refused（连接拒绝）、TLS failure（TLS 失败）或 socket error（套接字错误）返回 `ok=False`，不得伪装为 HTTP response。

P1-001 不自动跟随 redirect（重定向）。如果服务器返回 301/302/307/308，工具应记录该 HTTP status code 和响应正文；不得访问 `Location` 指向的新 URL。

### Successful result data（成功结果数据）

成功 `WebFetchToolResult.data` 必须包含：

```json
{
  "url": "http://127.0.0.1:8080/docs",
  "method": "GET",
  "status_code": 200,
  "reason": "OK",
  "content_type": "text/plain; charset=utf-8",
  "body": "response text",
  "body_sha256": "sha256:<hex>",
  "body_size_bytes": 13,
  "body_truncated": false,
  "body_decoded_with_replacement": false,
  "matched_rule_id": "local-docs",
  "timeout_seconds": 2.0,
  "max_response_bytes": 4096
}
```

规则：

- `body_sha256` 基于 stored body bytes（已存储响应字节）计算；如果响应被截断，不得声称这是完整远端响应的 hash（哈希）。
- `body_size_bytes` 是 stored body bytes（已存储响应字节）长度，不是远端完整 content length（内容长度）。
- `body_truncated=True` 表示工具读取到超过 `max_response_bytes` 的内容，并只保留前 `max_response_bytes` bytes。
- `content_type` 缺失时为 `None`，不得伪造默认类型。
- `reason` 缺失时为 `None`，不得伪造默认原因短语。

### Failure result data（失败结果数据）

失败 `WebFetchToolResult` 必须满足：

```text
ok = False
data = {}
error_kind = <stable machine-readable kind>
error_message = <short human-readable message>
```

`error_kind` 取值：

| error_kind | 中文解释 | 触发条件 |
|---|---|---|
| `invalid_input` | 非法输入 | URL 或 method 类型/值非法 |
| `permission_denied` | 权限拒绝 | URL 未被 NetworkPolicy 允许 |
| `timeout` | 请求超时 | HTTP 请求超过 timeout |
| `fetch_failed` | 获取失败 | DNS、连接、TLS、socket 或其它网络错误 |
| `unsupported_action` | 不支持动作 | dispatcher 收到非 `web_fetch` action |

所有失败都必须 fail closed（失败关闭）：不得请求未允许 URL，不得用其它 URL 替代，不得把网络异常记录为成功响应。

## AgentLoop Integration Semantics

### Permission decision（权限判定）

`AgentLoop._decide_permission`（智能体循环权限判定）处理 `WEB_FETCH` 时必须：

1. 先确认 `web_fetch` 出现在 `AgentInvocation.tools`（调用工具列表）中。
2. 如果 `web_fetch_tools is None`，返回 deny，reason 为 `network policy is not configured`。
3. 调用 `web_fetch_tools.policy.decide(action.input["url"])`。
4. 如果 deny，返回 deny，reason 使用 policy decision reason（策略判定原因）。
5. 如果 allow，返回 allow，reason 包含 matched rule id（匹配规则标识）。

permission event（权限事件）继续使用 `permission_policy.policy_ref` 作为 `policy_ref` 字段，避免新增第二套事件字段。network rule id（网络规则标识）放在 reason（原因）中，并在 tool result data（工具结果数据）中保留 `matched_rule_id`。

### Tool execution（工具执行）

`AgentLoop._execute_tool_action`（智能体循环工具执行）必须把 `AgentActionType.WEB_FETCH` 分发给 `execute_web_fetch_action`（执行网络获取动作）。

如果由于代码错误导致未配置 `web_fetch_tools` 却进入执行阶段，runtime 必须返回 failed `WebFetchToolResult`，不得抛出后继续执行其它 fallback。

### Event recording（事件记录）

`web_fetch` 成功路径事件顺序必须包含：

```text
run.started
provider.turn.started
provider.turn.completed
action.parsed
permission.decided
tool.attempt.started
tool.attempt.completed
network.fetch.completed
...
result.submitted
run.completed
```

规则：

- `tool.attempt.completed` 的 `observation` 字段引用 observation artifact（观察产物）。
- `network.fetch.completed` 的 `response` 字段引用 response body artifact（响应正文产物）。
- `network.fetch.completed.payload.status_code` 必须等于真实 HTTP status code。
- `network.fetch.completed.payload.url` 必须是实际请求 URL。
- 只有 `WebFetchToolResult.ok=True` 才记录 `network.fetch.completed`。
- policy deny（策略拒绝）时不得记录 `tool.attempt.started`，因为工具没有被允许执行。
- fetch failure（获取失败）时记录 `tool.attempt.started` 和 `tool.attempt.failed`，最后 fail closed。

## Security and No-Fallback Rules

- `web_fetch` 不得读取 `.env`、environment variables（环境变量）、local config files（本地配置文件）或 process defaults（进程默认值）来补齐 network policy（网络策略）或 timeout（超时）。
- `web_fetch` 不得访问未被 `NetworkPolicy` 显式允许的 URL。
- `web_fetch` 不得自动跟随 redirect（重定向）。
- `web_fetch` 不得自动更换 scheme（协议）、host（主机）、port（端口）或 path（路径）。
- `web_fetch` 不得接受 request body、headers、cookie、auth 或 proxy 配置。
- `web_fetch` 不得在 response 超过限制时继续无限读取。
- `web_fetch` 不得把 timeout、DNS failure、connection failure 或 TLS failure 伪装为 HTTP success（HTTP 成功）。
- `run_command` 的 `allow_network=True` 仍必须被拒绝；P1-001 不提供 command network escape hatch（命令网络逃逸口）。
- 测试不得依赖公网 URL；必须使用本地可控 HTTP server 或纯策略单元测试。

## Acceptance Criteria

P1-001 完成时必须证明：

- `AgentAction` 接受合法 `web_fetch` 输入，并拒绝缺失 `url`、空 `url`、非字符串 `url`、非 `GET` method 和多余字段。
- `NetworkPolicy` 接受合法 allow rules（允许规则），拒绝非法 rule id、scheme、host、port 和 path prefix。
- `NetworkPolicy` 对未匹配 host、scheme、port、path prefix、userinfo、fragment、畸形 URL 都 deny。
- `NetworkPolicy` 空规则集合显式 deny all（拒绝全部）。
- `WebFetchTools.fetch_url` 对允许 URL 发起真实 HTTP GET，并返回真实 status code、content type、body、hash、size、truncation 和 decode facts（解码事实）。
- HTTP 404 / 500 等响应是 `ok=True` 的 completed fetch（已完成获取），不是工具失败。
- timeout、连接失败或 DNS 失败是 `ok=False` 的工具失败。
- 未允许 URL 返回 `permission_denied`，且测试证明没有 HTTP server request（HTTP 服务器请求）发生。
- redirect（重定向）响应不被自动跟随；本地测试必须证明 301 response（301 响应）返回 `ok=True`、`status_code=301`，且 HTTP server 只收到原始路径请求，不收到 `Location` 目标路径请求。
- 当 HTTP response（HTTP 响应）缺失 `Content-Type` header（内容类型响应头）或 reason phrase（原因短语）时，`content_type` 和 `reason` 字段必须为 `None`，不得伪造默认值。
- `execute_web_fetch_action` 只分发 `WEB_FETCH`，并拒绝非网络动作。
- `AgentLoop` 在 `web_fetch_tools is None` 时 deny 并 fail closed。
- `AgentLoop` 在 URL 未被允许时 deny 并 fail closed，且不记录 `tool.attempt.started`。
- `AgentLoop` 在允许 URL 发生 timeout（超时）或 connection failure（连接失败）时记录 `tool.attempt.started`、`tool.attempt.failed` 和 `run.failed`，不得记录 `network.fetch.completed`。
- `AgentLoop` 成功执行 `web_fetch` 后记录 `tool.attempt.completed` 和 `network.fetch.completed`。
- response body artifact（响应正文产物）可由 `network.fetch.completed.payload.response` 追踪。
- observation（观察结果）受 `max_observation_chars` 限制，超长时显式 truncation（截断）。
- 现有 filesystem tools（文件系统工具）、command tools（命令工具）、budget fail-closed（预算失败关闭）和 event recorder（事件记录器）测试不回退。
- `pytest -v` 通过。
- runtime source 不包含网络策略 fallback 模式：`.env`、`os.environ`、`getenv`、`dotenv`、默认 allowlist、自动 redirect 或 command network enablement（命令网络启用）。

## Documentation Impact

评审通过并完成实现后，需要更新：

- `docs/04-implementation-backlog/backlog.md`：将 P1-001 标记为 `completed`。
- `docs/04-implementation-spec/P1-001-web-fetch-network-policy-spec.md`：将状态从 `draft` 改为 `implemented`。
- `docs/04-implementation-plan/P1-001-web-fetch-network-policy-plan.md`：将状态从 `draft` 改为 `implemented`。
- `docs/04-implementation-spec/INDEX.md`：将本规格从 Current Active Documents（当前活跃文档）移动到 Completed / Archived Documents（已完成 / 已归档文档）。
- `docs/04-implementation-plan/INDEX.md`：将对应 plan（实施计划）从 Current Active Documents 移动到 Completed / Archived Documents。

P1-001 不更新 README minimal example（最小示例）。README 更新属于 P1-003，且必须等真实 CLI command（命令行命令）可运行、产生 JSONL event stream（JSONL 事件流）并演示成功 fake provider loop（假模型供应商循环）之后进行。

## Self-Review Result

- Spec coverage（规格覆盖）：已覆盖 backlog P1-001、MVP `web_fetch` 和 network allowlist guard（网络允许列表守卫）、MVP acceptance 中未允许网络目标拒绝场景、事件协议中的 `network.fetch.completed`，并明确 P1-002/P1-003/P1-004 不在本任务范围。
- Placeholder scan（占位符扫描）：未使用占位标记、未完成提示或未定义要求。
- Internal consistency（内部一致性）：`NetworkPolicy`、`NetworkAllowRule`、`WebFetchTools`、`WebFetchToolResult`、`web_fetch_tools`、`network.fetch.completed` 命名在 public API、运行时语义、事件语义和验收标准中一致。
- Scope check（范围检查）：未纳入 POST、headers、redirect follow、DNS policy、OS-level network sandbox、network-enabled command、Boardroom adapter 或 README minimal example。
- No-fallback check（无兜底检查）：明确禁止默认 allowlist、环境读取、URL 改写、自动 redirect、网络错误伪成功和命令网络逃逸。
