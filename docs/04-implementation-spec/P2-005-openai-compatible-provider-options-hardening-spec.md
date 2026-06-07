# P2-005 OpenAI-compatible Provider Options Hardening Specification

## Status

draft

## Purpose

本文定义 P2-005 `OpenAI-compatible provider options hardening`（OpenAI 兼容供应商参数硬化）的功能规格。P2-002 已建立真实 provider streaming（供应商流式响应）接入路径，P2-004 已证明真实 provider 能成功驱动基础工具；但当前 `OpenAICompatibleProviderOptions`（OpenAI 兼容供应商选项）只暴露少量参数，不能显式配置 `reasoning_effort`（推理强度）等对 agentic task（智能体任务）质量、成本、延迟和兼容性影响较大的请求参数。

P2-005 的目标是把真实 OpenAI-compatible provider（OpenAI 兼容供应商）中重要、常用或影响重大的 request options（请求选项）提取为显式配置，并保持 fail-closed（失败关闭）、no silent fallback（不静默降级）和 no credential leakage（不泄露凭据）。

## Authoritative Inputs

本规格依据：

- OpenAI Chat Completions API reference（OpenAI 聊天补全接口参考）：`https://platform.openai.com/docs/api-reference/chat/create-chat-completion`。本文写作时该页面通过当前抓取工具返回 403，不能逐字段自动摘录；实现前应由工程师人工对照官方页面复核参数名称和模型支持范围。
- OpenAI reasoning models guide（OpenAI 推理模型指南）：`https://developers.openai.com/api/docs/guides/reasoning`。该指南建议 reasoning models（推理模型）优先使用 Responses API（响应接口），但说明 Chat Completions API（聊天补全接口）仍受支持；`reasoning.effort` / `reasoning_effort` 这类 effort（推理强度）配置会影响质量、延迟、成本和隐藏 reasoning tokens（推理 token）。
- `docs/09-adr/0002-use-provider-agnostic-action-protocol.md`：atomic-agent 保持 provider-agnostic `AgentAction`（供应商无关动作）协议，不改用 native tool calling（原生工具调用）。
- `docs/09-adr/0003-use-fail-closed-permission-model.md`：配置或 provider 请求失败必须清晰失败。
- `docs/04-implementation-spec/P2-002-real-provider-minimal-integration-gate-spec.md`：真实 provider 首版使用 OpenAI-compatible Chat Completions streaming（OpenAI 兼容聊天补全流式响应）。
- `docs/04-implementation-spec/P2-004-real-provider-tool-success-gate-spec.md`：真实 provider success gate（成功门禁）依赖真实工具执行、事件和证据，不接受 Outcome C（供应商响应失败关闭）作为通过。

## Implementation Preconditions

P2-005 实施前必须人工复核当前官方文档，不能只依赖本文写作时的网页抓取结果。复核清单：

1. 对照 OpenAI Chat Completions API reference（OpenAI 聊天补全接口参考）确认每个 request parameter（请求参数）的最终名称、类型、是否 deprecated（已废弃）以及 Chat Completions 路径是否仍支持。
2. 对照 OpenAI reasoning models guide（OpenAI 推理模型指南）确认 reasoning models（推理模型）在 Chat Completions 与 Responses API（响应接口）中的参数差异，尤其是 `reasoning_effort` 与 `reasoning.effort` 命名差异。当前人工复核结论（2026-06-08）：OpenAI Responses API 示例使用嵌套 `reasoning: {"effort": "medium"}`；P2-005 仍保持既有 OpenAI-compatible Chat Completions streaming（聊天补全流式）路径，不切换 Responses API。P2-005 runtime option（运行时选项）保留语义字段 `reasoning_effort`，本适配器路径将其映射到 Chat Completions request field（聊天补全请求字段）`reasoning_effort`；未来若切换 Responses API，必须另行修订 spec/plan 并映射为嵌套 `reasoning.effort`。
3. 确认 `reasoning_effort` 支持值及模型支持子集；本文建议值只作为候选集合，不替代官方文档。
4. 确认 `max_tokens`、`max_completion_tokens` 或其它 output cap（输出上限）字段在目标模型上的当前语义；如果官方文档要求更换字段，应先更新本规格或在实施计划中明确兼容策略。
5. 对照目标 OpenAI-compatible provider（OpenAI 兼容供应商）的文档确认其兼容字段；不支持的显式字段必须 fail closed（失败关闭），不得 silent retry（静默重试）移除该字段。

复核结果必须记录在 P2-005 implementation plan（实施计划）或 implementation notes（实施备注）中，至少包含复核日期、Chat Completions（聊天补全）中的 reasoning effort（推理强度）字段名、output cap（输出上限）字段名和是否需要修订本文。如果官方文档显示 `reasoning_effort`、`max_tokens` 或其它 P2-005 字段名称/语义已变化，必须先修订本文和对应 plan，再实施 runtime code（运行时代码）。

## Scope

P2-005 覆盖：

1. 扩展 `OpenAICompatibleProviderOptions`，显式表达重要 provider request options。
2. 扩展 standalone real provider example（独立真实供应商示例）CLI 参数和 pytest integration harness（集成测试驱动）环境变量读取。
3. 将非密钥 provider options 写入 `AgentInvocation.provider_profile`（供应商画像）用于 audit（审计）。
4. 在 `_request_payload()` 中仅发送显式配置的可选参数；未配置时不发送，避免硬编码 provider 默认值。
5. 增加不联网 unit tests（单元测试）验证参数映射、空值语义、非法值拒绝和 API key redaction（接口密钥脱敏）。
6. 更新 README / testing strategy（测试策略）中真实 provider 配置说明。

不包含：

- 不切换到 OpenAI Responses API。
- 不实现 Anthropic/Claude provider adapter。
- 不实现 provider registry（供应商注册表）或 multi-provider routing（多供应商路由）。
- 不实现 OpenAI native tool calling、tools、tool_choice 或 parallel_tool_calls 作为本阶段能力。
- 不自动检测 provider 是否支持某个参数后 silent retry（静默重试）移除该参数。
- 不把 API key、真实 base URL 或其他 secret 写入事件、产物、文档或失败输出。

## Required Provider Options

P2-005 必须优先暴露以下字段：

| Option | 类型 | 默认/空值语义 | 发送到请求 | 记录到 provider_profile | 说明 |
|---|---|---|---|---|---|
| `reasoning_effort` | `str | None` | `None` 不发送；空字符串视为 unset（未设置）或被 config parser 转为 `None` | 非空时发送 | 非空时记录 | 推理强度；影响质量、延迟、成本和 hidden reasoning tokens（隐藏推理 token） |
| `top_p` | `float | None` | `None` 不发送 | 非空时发送 | 非空时记录 | nucleus sampling（核采样）；通常不建议和 `temperature` 同时调优，但 runtime 不替用户做策略判断 |
| `presence_penalty` | `float | None` | `None` 不发送 | 非空时发送 | 非空时记录 | 影响重复和话题拓展 |
| `frequency_penalty` | `float | None` | `None` 不发送 | 非空时发送 | 非空时记录 | 影响重复 token 惩罚 |
| `seed` | `int | None` | `None` 不发送 | 非空时发送 | 非空时记录 | 尽力确定性；provider 可能不保证完全复现 |
| `stop` | `tuple[str, ...] | None` | `None` 不发送；空列表/空 tuple 视为 invalid（无效） | 非空时发送 list | 非空时记录 | 停止序列；可能破坏 JSON action 输出，默认不建议配置 |
| `response_format` | `dict | None` | `None` 不发送 | 非空时发送 | 记录 sanitized value | 可用于 JSON object/schema 模式；必须保持 provider-agnostic action schema（动作模式）一致 |
| `stream_options` | `dict | None` | `None` 不发送 | 非空时发送 | 记录 sanitized value | 例如 usage accounting（用量统计）；不得依赖它作为成功证据 |
| `service_tier` | `str | None` | `None` 不发送 | 非空时发送 | 非空时记录 | 延迟/服务层配置；provider-specific（供应商特定） |
| `user` | `str | None` | `None` 不发送 | 非空时发送 | 非空时记录 | 终端用户标识；不得包含 secret 或个人敏感数据 |

现有字段继续保留：

- `base_url`
- `api_key`
- `model`
- `context_window_tokens`
- `max_output_tokens`
- `stream_idle_timeout_seconds`
- `total_timeout_seconds`
- `temperature`
- `provider_label`

## Reasoning Effort Requirements

1. `reasoning_effort` 必须是显式配置，不得按 model name（模型名）猜测。
2. 支持值应按官方文档和 provider 实际兼容范围保守处理。实现应允许一组明确字符串，建议包括：
   - `none`
   - `minimal`
   - `low`
   - `medium`
   - `high`
   - `xhigh`
3. 如果 provider 只支持子集，用户显式传入不支持值时应由 provider/API 返回错误并 fail closed，不得捕获错误后静默移除参数重试。
4. `reasoning_effort` 非空时必须同时：
   - 写入 OpenAI-compatible request payload（请求载荷）。
   - 写入 `provider_profile`，供 evidence/audit 使用。
5. `reasoning_effort` 不属于 `AgentInvocation.budgets`。`budgets` 继续只表达 runtime（运行时）资源限制，例如 `max_steps`、`max_wall_seconds`、`max_observation_chars`。
6. P2-006 complex gate（复杂门禁）可默认使用 `high`，但 P2-005 本身不应硬编码默认值。

## Capability-first Local Profile

P2-005 必须区分 runtime core（运行时核心）默认值和 local/manual gate profile（本地/手动门禁配置画像）：

1. `OpenAICompatibleProviderOptions`（OpenAI 兼容供应商选项）和 `OpenAICompatibleProviderAdapter`（OpenAI 兼容供应商适配器）不得硬编码 P2-005 新增参数默认值；`None` 继续表示 unset（未设置）并且不发送到 provider。
2. 本地 git ignored（被 Git 忽略）配置文件 `.env.real-provider-test-p2-002-task7` 可以保存面向 Boardroom OS（Boardroom 操作系统）自治 agent team（自治智能体团队）的显式 capability-first profile（能力优先配置画像）。
3. tracked（被 Git 跟踪）模板 `.env.template` 必须使用脱敏 placeholder（占位符）表达同一套 profile，不得包含真实 `base_url`、`api_key` 或供应商私有地址。
4. capability-first profile 的推荐值为：

```text
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

5. `temperature=0.2` 用于提高 JSON `AgentAction`（智能体动作）输出稳定性；这不是成本优化，也不是 runtime core 默认值。
6. `stop` 默认必须保持空字符串，解析为 unset（未设置），避免截断 JSON action。
7. `response_format={"type":"json_object"}` 和 `stream_options={"include_usage":true}` 是能力/审计优先 profile 的显式配置；如果目标 provider 不支持这些参数，必须 fail closed（失败关闭），不得 silent retry（静默重试）移除参数。
8. 如果用户为了兼容特定 provider 调整 profile，应通过 env/template 明确修改配置，而不是由 runtime 根据 provider/model 猜测。

## CLI and Environment Variables

Standalone real provider example（独立真实供应商示例）应新增 CLI 参数：

```text
--reasoning-effort
--top-p
--presence-penalty
--frequency-penalty
--seed
--stop
--response-format-json
--stream-options-json
--service-tier
--user
```

P2-004 / future real provider pytest harness（测试驱动）应读取对应环境变量：

```text
ATOMIC_AGENT_REAL_PROVIDER_REASONING_EFFORT
ATOMIC_AGENT_REAL_PROVIDER_TOP_P
ATOMIC_AGENT_REAL_PROVIDER_PRESENCE_PENALTY
ATOMIC_AGENT_REAL_PROVIDER_FREQUENCY_PENALTY
ATOMIC_AGENT_REAL_PROVIDER_SEED
ATOMIC_AGENT_REAL_PROVIDER_STOP
ATOMIC_AGENT_REAL_PROVIDER_RESPONSE_FORMAT_JSON
ATOMIC_AGENT_REAL_PROVIDER_STREAM_OPTIONS_JSON
ATOMIC_AGENT_REAL_PROVIDER_SERVICE_TIER
ATOMIC_AGENT_REAL_PROVIDER_USER
```

Parsing rules（解析规则）：

- 空字符串表示 unset（未设置），不会发送到 provider。
- JSON 字段必须是合法 JSON object（对象），否则 test harness / CLI fail closed。
- `stop` 可用 JSON array（数组）表达；不得接受逗号分隔的隐式格式，避免 escaping ambiguity（转义歧义）。
- numeric fields（数值字段）必须验证有限数值。
- `seed` 必须是 integer（整数）。

## Request Payload Requirements

`OpenAICompatibleProviderAdapter._request_payload()` 必须：

1. 始终发送：
   - `model`
   - `messages`
   - `stream=True`
   - `max_tokens`
2. 仅当非 `None` 时发送可选参数。
3. 不发送 API key。
4. 不把 unsupported parameter（不支持参数）吞掉或自动重试删除。
5. 对 request payload 的单元测试必须使用 fake OpenAI client（假 OpenAI 客户端），不得联网。

## Stop Sequences Risk

`stop`（停止序列）对 atomic-agent 风险较高，因为 runtime（运行时）要求 provider 输出完整 provider-agnostic `AgentAction` JSON object（供应商无关动作 JSON 对象）。如果 `stop` 命中 JSON 输出中间位置，可能导致：

- provider request（供应商请求）本身成功，但返回内容被截断。
- `action_parse_failed`（动作解析失败）。
- `run.failed`（运行失败）。
- 失败原因看似是 provider 行为或 parser（解析器）问题，实际根因是 request option（请求选项）。

因此：

1. 默认不应配置 `stop`。
2. 如显式配置，调用方必须确认 stop sequences 不会匹配 JSON structural characters（结构字符）、quoted strings（字符串内容）、action fields（动作字段）或预期文件内容。
3. runtime 不得在解析失败后自动移除 `stop` 并重试；这会构成 silent fallback（静默降级）。
4. 因 `stop` 导致的 invalid JSON（无效 JSON）应通过现有 `action.rejected` / `run.failed` 路径清晰暴露。

## Response Format Constraints

`response_format`（响应格式）只能作为 provider request option（供应商请求选项）传递，不能替代 atomic-agent 的 `AgentAction` schema validation（动作模式校验）。如果配置 `response_format`：

1. provider 输出仍必须是完整的 provider-agnostic `AgentAction` JSON object。
2. `response_format={"type":"json_object"}` 只能要求 JSON object，不能证明该 object 符合 `AgentAction`。
3. 如果使用 JSON schema（JSON 模式），该 schema 必须与 `AgentAction` 兼容，不得定义冲突字段或遗漏必需字段。
4. runtime 不会根据 `response_format` 自动改写 prompt（提示）、放宽 schema validation 或把 provider-native JSON mode（供应商原生 JSON 模式）当作成功证据。
5. 如果 response 能解析为 JSON 但无法通过 `AgentAction` 校验，必须 fail closed。

推荐：除非明确测试 provider JSON mode（供应商 JSON 模式）兼容性，否则不要配置 `response_format`。

## Evidence and Secret Safety

1. `provider_profile` 可记录非密钥配置，包括 `reasoning_effort`、sampling options（采样选项）和 `provider_label`。
2. `api_key` 不得进入：
   - `AgentInvocation`
   - prompt messages（提示消息）
   - event payload（事件载荷）
   - artifacts（产物）
   - stdout/stderr（标准输出/错误）
   - test failure output（测试失败输出）
3. 对 `base_url`：
   - 如果用户配置 `provider_label`，`provider_profile` 应优先记录 `provider_label` 而不是真实 `base_url`。
   - 文档示例只能使用 placeholder URL（占位 URL）。

## Acceptance Criteria

P2-005 完成必须满足：

1. `python -m pytest -q` 不联网且通过。
2. `tests/test_openai_compatible_provider.py` 覆盖新增参数映射。
3. `reasoning_effort=None` 时 request payload 不包含该字段。
4. `reasoning_effort="high"` 时 request payload 包含该字段，且 `provider_profile` 可记录该值。
5. `top_p`、`presence_penalty`、`frequency_penalty`、`seed`、`stop`、`response_format`、`stream_options`、`service_tier`、`user` 至少有 request payload 映射单元测试。
6. CLI 和 env parser 对空字符串、非法 JSON、非法数值 fail closed。
7. 显式配置 provider 不支持的参数时，不做 silent fallback；provider 错误应通过现有 `provider.turn.failed` / `run.failed` 记录。
8. README 和 testing strategy 记录新增配置项、默认 unset 语义和兼容性风险。
9. 不泄露真实 API key 或真实 provider URL。

## Known Limitations

- OpenAI-compatible providers（OpenAI 兼容供应商）并不保证支持所有 OpenAI 参数。
- 官方推荐 reasoning models 优先使用 Responses API；P2-005 仍保持 Chat Completions streaming 路径，是为了延续 P2-002/P2-004 已验证边界。
- `reasoning_effort` 会影响 hidden reasoning tokens（隐藏推理 token），可能导致 `max_output_tokens` 或 context window（上下文窗口）不足；P2-005 只暴露配置，不自动调优 token budget。
- `response_format` 与 provider-agnostic `AgentAction` JSON schema 的关系必须谨慎处理；本阶段不引入 native structured outputs（原生结构化输出）作为依赖。

## Self-Review

- **Coverage（覆盖）**：本规格覆盖 reasoning_effort 和常见高影响 provider request options、CLI/env、request payload、provider_profile、测试和文档。
- **No placeholders（无占位）**：本文不含待填占位；官方参数最终名称要求实现前人工复核 API reference，是明确验收前置要求。
- **Boundary（边界）**：不切换 Responses API，不引入 native tool calling，不改变 Boardroom OS 治理边界。
- **Safety（安全）**：显式配置、无静默降级、密钥不泄露、provider 不支持时 fail closed。
