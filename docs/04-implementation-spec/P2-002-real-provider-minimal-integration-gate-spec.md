# P2-002 Real Provider Minimal Integration Gate Specification

## Status

implemented

## Purpose

本文定义 P2-002 `real provider minimal integration gate`（真实模型供应商最小集成门禁）的功能规格。该门禁用于证明 `atomic-agent`（原子智能体）的现有 `AgentLoop`（智能体循环）可以接收真实 OpenAI-compatible provider（OpenAI 兼容模型供应商）的流式输出，解析为 provider-agnostic `AgentAction`（供应商无关智能体动作），执行受权限约束的工具，记录 event stream（事件流），并把产物映射为 evidence summary（证据摘要）。

P2-002 的目标不是证明模型总会按提示完成任务，也不是引入 external coding agent bridge（外部编码智能体桥接）。它建立一个默认禁用、显式启用的 manual/nightly integration gate（手动/夜间集成门禁），验证真实 provider 接入路径、流式响应处理、超时控制、事件记录和 fail-closed（失败关闭）语义，避免真实 provider 波动影响 base CI（基础持续集成）。

## Scope

P2-002 覆盖以下能力：

- 新增 task-agnostic `OpenAICompatibleProviderAdapter`（任务无关 OpenAI 兼容供应商适配器），实现现有 `ProviderAdapter.complete(context) -> str` 协议。
- 使用官方 OpenAI Python SDK（OpenAI Python 软件开发包）的 v1 client 行为接入 OpenAI-compatible Chat Completions（OpenAI 兼容聊天补全）接口。
- 必须使用 streaming（流式响应）；不允许首版真实 provider gate 使用非流式 Chat Completions 作为主路径。
- 支持显式 `base_url`（兼容供应商基础 URL）、`api_key`（接口密钥）、`model`（模型）、`context_window_tokens`（上下文窗口 token 数）、`max_output_tokens`（最大输出 token 数）、`stream_idle_timeout_seconds`（流空闲超时秒数）、`total_timeout_seconds`（总超时秒数）、`temperature`（温度）等 provider options（供应商选项）。
- 将 `max_output_tokens` 视为单次 provider response truncation guard（响应截断防护），不把它作为 agent 成本目标；agent 成本和工作量主要由 `AgentInvocation.budgets.max_steps` 控制。
- 首版 provider 方向只覆盖 OpenAI-compatible provider，不默认接入 Anthropic/Claude provider。
- 保持现有 provider-agnostic JSON action protocol（供应商无关 JSON 动作协议），不改用 OpenAI native tool calling（OpenAI 原生工具调用）。
- 新增 standalone minimal real provider loop（独立最小真实供应商循环）入口，用于手动运行真实 provider gate。
- 新增 `real_provider` pytest marker（真实供应商 pytest 标记）和 `ATOMIC_AGENT_RUN_REAL_PROVIDER=1` 显式启用门禁。
- 新增不联网 unit tests（单元测试）验证 provider adapter 的请求参数、流式响应提取、超时控制、OpenAI SDK 兼容行为和错误传播。
- 新增默认跳过的 integration test（集成测试）验证真实 provider 接入路径和 event stream / evidence mapping（事件流 / 证据映射）。

不包含：

- 不实现 P2-003 `external coding agent bridge`（外部编码智能体桥接）。
- 不接入 Claude Code、Codex 或其它外部 coding agent（编码智能体）。
- 不实现 Anthropic/Claude provider adapter（Anthropic/Claude 供应商适配器）。
- 不实现 provider registry（供应商注册表）或 multi-provider routing（多供应商路由）。
- 不实现 OpenAI native tool calling（OpenAI 原生工具调用）或 Responses API（响应接口）专项适配。
- 不新增 action type（动作类型）或修改 `AgentAction` schema（动作模式）。
- 不让真实 provider test 进入默认 `python -m pytest -q` 必须联网路径。
- 不把 provider output（模型输出）单独当作 implementation evidence（实现证据）。
- 不让 `atomic-agent` 直接声明 Boardroom ticket completed（工单完成）、closeout committed（收尾提交）或 evidence accepted（证据接受）。

## Authoritative Inputs

本规格依据以下已索引 authoritative documents（权威文档）和本轮用户更正：

- 本轮用户更正：项目首版真实 provider 只打算接入 OpenAI-compatible provider，并采用 OpenAI SDK behavior（OpenAI 软件开发包行为）、流式响应、较大的输出 token 能力、流空闲超时和较大的总超时；成本目标更适合通过 `max_steps` 表达。
- `README.md`：当前 minimal example（最小示例）只证明 deterministic fake provider loop（确定性假供应商循环），不得用静态文本、模拟结果或 silent fallback（静默降级）伪装成功。
- `docs/04-implementation-backlog/backlog.md`：P2-002 为当前 P2 中唯一 pending（待处理）的非 deferred（延后）任务，且必须作为 manual/nightly 或 integration-profile gate（集成配置门禁），不能 destabilize base CI（破坏基础持续集成）。
- `docs/05-testing/testing-strategy.md`：real provider tests（真实供应商测试）只验证最小真实 provider action loop（供应商动作循环），不要求模型完成大型项目。
- `docs/04-implementation-spec/mvp-runtime-spec.md`：runtime（运行时）只能接收显式 `AgentInvocation`（智能体调用请求），不得读取 `.env`、environment variables（环境变量）、local config files（本地配置文件）或 process defaults（进程默认值）补齐 invocation 字段。
- `docs/04-implementation-acceptance/mvp-acceptance.md`：source file（源码文件）必须能追溯到 tool attempt（工具调用尝试）和 workspace mutation（工作区变更）；provider output 不能单独作为 implementation evidence。
- `docs/06-roadmap/roadmap.md`：M4 要求 event stream / evidence mapping（事件流 / 证据映射）、artifact hash（产物哈希）和 `SourceInventory` lineage（源码清单谱系）；M5 external coding agent bridge 仍是后续能力。
- `docs/09-adr/0002-use-provider-agnostic-action-protocol.md`：保持供应商无关动作协议；OpenAI-compatible、Anthropic-compatible、local model 都只是可支持 provider 类型，不代表本任务默认接 Anthropic。
- `docs/09-adr/0003-use-fail-closed-permission-model.md`：权限失败必须 fail closed（失败关闭）。
- `docs/09-adr/0004-keep-boardroom-os-as-governance-source.md`：Boardroom OS（Boardroom 操作系统）仍是治理事实源。

## Current Implementation Baseline

当前代码已具备：

- `src/atomic_agent/agent_loop.py` 中的 `ProviderAdapter`（供应商适配器协议）和 `ProviderContext`（供应商上下文）。
- `AgentLoop.run()`（智能体循环运行）中的 provider turn（模型轮次）、action parse（动作解析）、permission decision（权限判定）、tool attempt（工具尝试）、workspace mutation（工作区变更）和 fail-closed 事件记录。
- `src/atomic_agent/models.py` 中的 `AgentInvocation`、`AgentAction`、`AgentRunResult`，以及 `run_command` 只能使用 `command_id` 的现有校验。
- `src/atomic_agent/examples/minimal_fake_loop.py` 中的 standalone CLI（独立命令入口）组装模式。
- `src/atomic_agent/evidence.py` 中的 `verify_event_stream()`（验证事件流）和 `build_evidence_summary()`（构建证据摘要）。
- `tests/test_minimal_fake_loop_example.py` 中通过 subprocess（子进程）真实执行 module entrypoint（模块入口）的测试模式。

当前缺口：

- 没有 OpenAI-compatible provider adapter（OpenAI 兼容供应商适配器）。
- 没有 streaming provider response handling（流式供应商响应处理）。
- 没有流空闲超时和大总超时的分离控制。
- 没有默认禁用、显式启用的 real provider integration pytest gate（真实供应商 pytest 集成门禁）。
- `pyproject.toml` 当前没有 `openai` optional dependency（可选依赖），pytest marker 也只有 `permission_negative`。
- README 只说明 fake provider loop，不说明真实 provider gate 的手动/夜间运行方式。

## Provider Adapter Requirements

新增 real provider adapter 必须满足：

1. 命名为 `OpenAICompatibleProviderAdapter`（OpenAI 兼容供应商适配器），实现现有 `ProviderAdapter.complete(context: ProviderContext) -> str` 协议。
2. Provider adapter 必须 task-agnostic（任务无关）。它只能把 `AgentInvocation.task`、enabled tools（启用工具）、allowed write set（允许写入集合）、output requirements（输出要求）和 previous observations（前序观察）传给 provider，不得硬编码具体任务路径、工具顺序或任务成功条件。
3. 任务细节必须由 standalone entrypoint 或上游系统写入 `AgentInvocation.task`，避免 adapter 和 invocation 形成 second source of truth（第二真相源）。
4. 返回值必须是 provider-agnostic JSON `AgentAction` 文本，由现有 `parse_agent_action()` 继续解析。
5. 不使用 OpenAI native tool calling（OpenAI 原生工具调用）；工具执行仍由 `AgentLoop` 通过现有 permission policy（权限策略）和 tool modules（工具模块）完成。
6. provider adapter 不得直接执行文件、命令、网络或提交结果。
7. provider adapter 不得吞掉 SDK/API 异常；异常应传播到 `AgentLoop`，由现有 `provider.turn.failed` 和 `run.failed` fail-closed 路径记录。
8. provider adapter 的 system prompt（系统提示）只描述 `AgentAction` JSON envelope（动作 JSON 信封）和禁止 markdown / shell string（命令字符串）等协议规则，不包含具体任务路径。
9. provider adapter 单元测试必须使用 injected fake OpenAI client（注入的假 OpenAI 客户端），不得联网。

## OpenAI-compatible Streaming Requirements

首版真实 provider 采用 OpenAI-compatible Chat Completions streaming（OpenAI 兼容聊天补全流式响应）：

1. 必须使用官方 `openai` Python SDK 包，不得使用 Anthropic SDK 或 provider-specific SDK。
2. 推荐 client 形态为 OpenAI SDK v1 style：`OpenAI(base_url=..., api_key=..., timeout=...)`，并调用 `client.chat.completions.create(..., stream=True)`。
3. `base_url`、`api_key`、`model`、`context_window_tokens`、`max_output_tokens`、`stream_idle_timeout_seconds`、`total_timeout_seconds` 必须来自 standalone entrypoint 参数、显式 adapter constructor（适配器构造参数）或 integration harness（集成测试驱动），不得在 runtime 执行中从隐式 fallback 补齐。
4. `api_key` 不得写入 `AgentInvocation`、prompt、event payload、artifact、README 或测试输出。
5. `base_url` 可以进入 `provider_profile` 作为非密钥配置；如不希望记录供应商 URL，entrypoint 必须允许用 opaque provider label（不透明供应商标签）替代。
6. `context_window_tokens` 必须作为 provider capability（供应商能力）显式传入或记录，例如 400000、1000000 等；adapter 不根据模型名称猜测上下文窗口。
7. `max_output_tokens` 必须作为 provider output cap（输出上限）显式传入并映射到 Chat Completions 请求的 `max_tokens`。它用于避免单次响应过早截断，不作为 agent 成本目标。
8. `AgentInvocation.budgets.max_steps` 是 agent loop 工作量和成本的主要控制项；高难度原子编码任务可以由 invocation 显式提供 100+ step budget（步数预算）。
9. 必须支持 `temperature=None`，此时请求不得发送 `temperature` 字段；兼容供应商不支持 temperature 时应通过显式配置禁用发送，而不是捕获错误后 silent fallback。
10. streaming chunks（流式块）必须按 OpenAI SDK chat completion streaming behavior（聊天补全流式行为）读取 `chunk.choices[0].delta.content` 并累积文本。
11. 如果任一 chunk 的 `finish_reason` 为 `length`，provider adapter 必须清晰失败，不得把截断 JSON 当作成功。
12. 如果 stream 完成后没有累积任何文本，provider adapter 必须清晰失败。
13. 如果 chunk 结构缺失 choices/message delta/content 等必要字段，provider adapter 必须清晰失败或跳过明确允许的空心跳；本首版不使用 usage-only stream chunk（仅用量统计流式块），因此空 choices 视为错误。
14. `stream_idle_timeout_seconds` 用于判断相邻 stream chunks（流式块）之间的最长允许间隔。
15. `total_timeout_seconds` 用于限制一次 provider turn（供应商轮次）的最长总耗时，默认应显著大于普通 HTTP request timeout（请求超时），例如 3600 秒量级。
16. 非流式 request timeout 不能作为首版主路径；过去非流式超时后丢弃已完成进度的问题必须通过 streaming 规避。

## Standalone Invocation Requirements

新增 minimal real provider loop entrypoint（最小真实供应商循环入口）必须：

1. 接收显式 CLI 参数：`--run-id`、`--workspace`、`--event-stream`、`--artifact-root`、`--result`、`--base-url`、`--api-key-env`、`--model`、`--context-window-tokens`、`--max-output-tokens`、`--stream-idle-timeout-seconds`、`--total-timeout-seconds`、`--max-steps`。
2. `--api-key-env` 只指定环境变量名称；entrypoint 读取该环境变量构造 OpenAI SDK client，但不得把 key 值写入 invocation、event、artifact 或 stdout/stderr。
3. 构造完整 `AgentInvocation`，包括 `workspace_root`、`allowed_write_set`、`tools`、`permission_policy`、`provider_profile`、`budgets` 和 `output_requirements`。
4. 构造后将完整 `AgentInvocation` 传给 `AgentLoop.run()`；`AgentLoop` 执行中不得再读取本地配置作为 fallback。
5. 任务细节必须写入 `AgentInvocation.task`，例如要求真实 provider 使用 `write_file` 创建 `work/real-provider-output.txt`，收到成功 observation 后再用 `submit_result`。
6. 默认只启用 P2-002 最小门禁所需工具：`write_file` 和 `submit_result`。如后续需要 command evidence（命令证据），应另开任务或在 spec 更新后扩展。
7. 默认 produced path（产出路径）为 `work/real-provider-output.txt`，位于 `allowed_write_set` 内。
8. 成功时 stdout（标准输出）输出 JSON，包含 `status`、`result_path`、`event_stream_path`、`artifact_root` 和 `workspace_output_path`。
9. 失败时必须输出结构化失败结果，不能覆盖已有 result path（结果路径）、event stream path（事件流路径）或 artifact root（产物根目录）中的既有内容。

## Real Provider Gate Outcomes

P2-002 的真实 provider gate 验证接入路径和 fail-closed 语义，不把模型完全按预期写文件作为唯一成功条件。显式启用真实 provider gate 后，以下任一 outcome（结果类别）可作为 gate pass（门禁通过），但 authentication failure（认证失败）、network connectivity failure（网络连接失败）、missing credentials（缺失凭据）或 test harness misconfiguration（测试驱动配置错误）不算通过。

### Outcome A: Full action-loop success（完整动作循环成功）

要求：

1. provider stream 正常完成并返回 JSON 文本。
2. runtime 记录 `provider.turn.completed` 和 `action.parsed`。
3. 至少一个 tool action 执行成功并记录 `tool.attempt.completed`。
4. 如果 action 是 `write_file`，记录 `workspace.mutation.recorded`。
5. provider 后续返回 `submit_result`。
6. run terminal event（运行终止事件）为 `run.completed`。
7. `build_evidence_summary()` 映射成功；如有 produced path，对应 lineage 为 `traceable`。

### Outcome B: Valid provider action but task behavior varies（供应商动作合法但模型行为偏离）

要求：

1. provider stream 正常完成并返回 JSON 文本。
2. runtime 至少记录 `provider.turn.completed` 和 `action.parsed`。
3. 该 action 可能被 permission denied（权限拒绝）、tool failed（工具失败），或模型直接 `submit_result` 导致没有 workspace mutation。
4. event stream 必须以 `run.completed` 或 `run.failed` 终止。
5. `verify_event_stream()` 必须通过；如调用 `build_evidence_summary()`，必须能准确反映 missing lineage（缺失谱系）或失败原因，不得伪造成 traceable。

### Outcome C: Provider response fail-closed（供应商响应失败关闭）

要求：

1. provider call 已经到达 OpenAI-compatible SDK path（SDK 路径），并返回了空内容、截断内容、无法提取内容或非 JSON action 文本。
2. runtime 记录 `provider.turn.failed` 或 `action.rejected`，并最终 `run.failed`。
3. event stream integrity（事件流完整性）可验证。
4. 失败信息清晰说明是 provider response invalid（供应商响应无效）、finish_reason length（长度截断）或 action parse failed（动作解析失败）。

不属于 Outcome C 的情况：认证失败、API key 缺失、base URL 错误、DNS/连接失败、stream idle timeout（流空闲超时）或 total timeout（总超时）。这些是环境或 provider 可用性问题，应让 gate fail（失败）或 skip（跳过），不能算通过。

## Test Data Rules

- fake provider fixture（假供应商夹具）只能用于不联网单元测试，不得作为真实完成证据。
- real provider integration test（真实供应商集成测试）必须清楚标记为 `real_provider`。
- golden output（黄金输出）必须包含 event stream 和 artifact hash（产物哈希），不得只断言文本摘要。
- 默认测试命令 `python -m pytest -q` 不应要求 OpenAI-compatible provider credentials（OpenAI 兼容供应商凭据）或网络。

## Documentation Requirements

实现通过后必须同步更新：

- `README.md`：新增 OpenAI-compatible real provider gate 的 manual/nightly 说明和命令，明确它不同于 fake provider minimal example。
- `docs/05-testing/testing-strategy.md`：记录 `real_provider` marker、`ATOMIC_AGENT_RUN_REAL_PROVIDER=1`、OpenAI-compatible provider config（OpenAI 兼容供应商配置）、streaming timeout（流式超时）和 optional dependency（可选依赖）安装方式。
- `docs/04-implementation-backlog/backlog.md`：所有验证通过后将 P2-002 标记 completed。
- `docs/04-implementation-spec/INDEX.md`、`docs/04-implementation-plan/INDEX.md` 和 `docs/INDEX.md`：按文档状态从 active draft（活跃草案）移动到 completed / archived（完成 / 归档）记录。

## Acceptance Criteria

P2-002 完成必须满足：

1. P2-002 spec 和 plan 已修正为 OpenAI-compatible streaming 首版方向、索引、自审并经用户确认。
2. provider adapter 使用官方 OpenAI Python SDK，且可以通过 fake OpenAI client 做不联网测试。
3. provider adapter task-agnostic，只传递 `AgentInvocation.task` 和 runtime context，不硬编码具体文件路径、工具顺序或测试任务。
4. provider adapter 请求参数符合 OpenAI-compatible Chat Completions streaming 约束：`stream=True`、显式 `model`、显式 `max_tokens`、可配置 `base_url`、可配置 `api_key` 来源、可配置 stream idle timeout 和 total timeout。
5. provider adapter 不使用 Anthropic SDK、Claude 模型默认值或 native tool calling。
6. provider adapter 能清晰处理 SDK 异常、空 choices、缺失 content、finish_reason length、temperature=None 和 stream timeout。
7. `python -m pytest -q` 不需要真实 provider 凭据，不发起真实 provider 网络调用。
8. `python -m pytest tests/test_real_provider_integration.py -q` 在未启用环境变量时 skip。
9. `ATOMIC_AGENT_RUN_REAL_PROVIDER=1 python -m pytest tests/test_real_provider_integration.py -m real_provider -q` 在具备有效 OpenAI-compatible provider 配置时运行真实 provider gate。
10. 真实 provider gate 出现 Outcome A、B 或 C 中任一有效 outcome，且事件流完整可审计时可通过；认证、网络、凭据或测试配置失败不可算通过。
11. README 和 testing strategy 只在真实 gate 和 base gates 通过后声明该能力。

## Non-Goals

- 不证明任何模型能完成完整软件开发任务。
- 不比较模型质量、价格、速度或 provider 能力。
- 不把 real provider gate 作为 release blocker（发布阻塞）加入 base CI。
- 不新增 service runner（服务运行器）、HTTP probe（HTTP 探测）或 browser automation（浏览器自动化）。
- 不变更 Boardroom OS 的 governance contract（治理契约）。
- 不提交 git commit，除非用户另行明确要求。

## Self-Review

- **Coverage（覆盖）**：本规格覆盖 P2-002 的 OpenAI-compatible streaming provider adapter、manual/nightly gate、默认跳过策略、event/evidence 验收、OpenAI SDK 行为、stream timeout 语义和文档收尾。
- **No placeholders（无占位）**：本文不含待填占位、未定义步骤或“稍后实现”要求。
- **Boundary（边界）**：本文明确排除 P2-003、native tool calling、provider registry、Managed Agents 和 Anthropic/Claude 默认实现，避免范围膨胀。
- **Safety（安全）**：本文要求 no silent fallback、no mock success path、no credential leakage、fail closed。
