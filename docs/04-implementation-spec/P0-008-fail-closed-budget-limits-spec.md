# Fail-Closed Budget Limits Specification

## Status

implemented

## Purpose

本文定义 P0-008 `fail-closed budget limits`（失败关闭预算限制）的实现规格。该能力负责把 P0-007 `AgentLoop`（智能体循环）中的基础 step budget（步数预算）和 parse retry budget（解析重试预算）硬化为完整、显式、可测试的 runtime budget（运行时预算）语义，并补齐 `max_wall_seconds`（最大墙钟秒数）限制。

P0-008 的目标不是扩展 agent framework（智能体框架），而是确保 MVP runtime（最小可行运行时）在预算缺失、预算非法、step budget 耗尽、parse retry budget 耗尽或 wall-time budget（墙钟时间预算）耗尽时都 fail closed（失败关闭），并产出真实 `run.failed` terminal event（终止事件）和 failed `AgentRunResult`（失败运行结果）。

## Scope

P0-008 覆盖以下能力：

- 复用现有 `AgentLoop`（智能体循环）、`EventRecorder`（事件记录器）、`ArtifactWriter`（产物写入器）、`parse_agent_action`（解析智能体动作）、filesystem tools（文件系统工具）和 command tools（命令工具）。
- 将 `AgentInvocation.budgets`（智能体调用请求预算）作为唯一 budget source（预算事实源）。
- 继续要求并验证：
  - `max_steps`（最大步数）。
  - `max_parse_failures`（最大解析失败次数）。
  - `max_observation_chars`（最大观察字符数）。
- 新增要求并验证：
  - `max_wall_seconds`（最大墙钟秒数）。
- 在 `AgentLoopDependencies`（智能体循环依赖）中新增显式 `runtime_clock`（运行时时钟）依赖，用于可测试的 wall-time budget 检查。
- 在 provider call（模型调用）前、provider output（模型输出）记录后、tool execution（工具执行）前和 tool result（工具结果）记录后检查 wall-time budget。
- 对超过 wall-time budget 的运行返回 `failure_kind="max_wall_seconds_exceeded"`。
- 对缺失或非法 budget 返回 `failure_kind="invalid_invocation"`。
- 保留 P0-007 已有 `max_steps_exceeded` 和 `action_parse_failed` 语义，并补齐回归测试，避免后续改动破坏 fail-closed 行为。

不包含：

- 不实现 token budget（token 预算）、cost budget（成本预算）、memory budget（内存预算）或 artifact size budget（产物大小预算）。
- 不实现 provider API timeout（模型供应商 API 超时）或取消运行中的 provider call；P0-008 只在 provider call 返回后检查 wall-time budget。
- 不实现 command process kill（命令进程强制终止）；command tools（命令工具）已有独立 command timeout（命令超时）语义，P0-008 只在工具返回后检查整体 wall-time budget。
- 不实现 network budget（网络预算）或 `web_fetch`（网络获取）；P1-001 覆盖 `NetworkPolicy`（网络策略）和网络工具。
- 不实现 Boardroom `AgentRuntimePort` adapter（Boardroom 智能体运行时端口适配器）。
- 不更新 README minimal example（最小示例），除非后续 P0 exit review（P 阶段退出复审）证明真实最小示例已经稳定可运行。

## Authoritative Inputs

本规格依据以下已索引文档：

- `docs/04-implementation-backlog/backlog.md`（实现待办），其中 P0-008 已标记为 completed（已完成）任务。
- `docs/04-implementation-spec/mvp-runtime-spec.md`（MVP 运行时规格）。
- `docs/04-implementation-acceptance/mvp-acceptance.md`（MVP 验收标准）。
- `docs/05-testing/testing-strategy.md`（测试策略）。
- `docs/04-implementation-spec/P0-007-minimal-agent-loop-spec.md`（最小智能体循环规格）。
- `docs/09-adr/0003-use-fail-closed-permission-model.md`（失败关闭权限模型 ADR）。

## Public API

### `AgentInvocation.budgets`（调用预算）

P0-008 要求 `AgentInvocation.budgets` 显式包含：

```json
{
  "max_steps": 8,
  "max_parse_failures": 2,
  "max_observation_chars": 4000,
  "max_wall_seconds": 30.0
}
```

字段规则：

| Field | 中文解释 | 约束 | 失败语义 |
|---|---|---|---|
| `max_steps` | 最大 provider/action loop iteration（模型 / 动作循环迭代）次数 | positive integer（正整数），`bool` 不合法 | `invalid_invocation` |
| `max_parse_failures` | 可反馈给 provider 的 invalid JSON / schema failure（无效 JSON / 模式失败）次数 | non-negative integer（非负整数），`bool` 不合法 | `invalid_invocation` |
| `max_observation_chars` | 单条 visible observation（可见观察）最大字符数 | positive integer，`bool` 不合法 | `invalid_invocation` |
| `max_wall_seconds` | 一次 `AgentLoop.run` 允许的最大 elapsed wall time（已用墙钟时间） | finite positive number（有限正数），`bool`、`NaN`、`inf` 不合法 | `invalid_invocation` |

规则：

- 所有字段都必须来自显式 `AgentInvocation.budgets`。
- runtime code（运行时代码）不得提供 hidden default（隐藏默认值）。
- 缺失字段必须 fail closed，不得 fallback（兜底）到 P0-007 旧行为。
- `max_wall_seconds` 可以是 `int` 或 `float`，内部规范化为 `float`。
- `max_wall_seconds` 的单位固定为 seconds（秒），不得混用 milliseconds（毫秒）字段名。

### `AgentLoopDependencies.runtime_clock`

P0-008 修改 `src/atomic_agent/agent_loop.py` 中的 `AgentLoopDependencies`（智能体循环依赖）：

| Symbol / Field | 中文解释 | Contract |
|---|---|---|
| `runtime_clock` | 运行时时钟 | `Callable[[], float]`，返回 monotonic seconds（单调秒数） |

`runtime_clock` 规则：

- 必须由调用方显式注入。
- 返回值必须是 finite number（有限数字），`bool` 不合法。
- 返回值必须 monotonic（单调不倒退）。如果后续读数小于 run start reading（运行开始读数），runtime 必须 fail closed。
- 测试必须使用 deterministic fake clock（确定性假时钟）。
- `AgentLoop` 不得在内部调用 `time.time()`、`time.monotonic()` 或读取环境变量作为 fallback。
- standalone entrypoint（独立入口）如果后续存在，可以在构造 dependencies（依赖）时注入真实 `time.monotonic`，但这不属于 P0-008 范围。

## Runtime Budget Semantics

### Run start（运行开始）

`AgentLoop.run(invocation)` 必须：

1. 创建 per-run state（单次运行状态）。
2. 记录 `run.started`。
3. 校验 `AgentInvocation.budgets`。
4. 读取 `runtime_clock()` 作为 `started_at`。
5. 进入 provider/action loop（模型 / 动作循环）。

如果 budget 校验失败：

- 不调用 provider（模型供应商）。
- 不执行工具。
- 记录 `run.failed`。
- 返回 `AgentRunResult(status=FAILED, failure_kind="invalid_invocation")`。

如果 `runtime_clock()` 返回非法值或倒退：

- 记录 `run.failed`。
- 返回 `AgentRunResult(status=FAILED, failure_kind="invalid_invocation")`。

### Step budget（步数预算）

`max_steps` 表示 provider/action loop iteration（模型 / 动作循环迭代）的最大次数。

规则：

- 每次调用 provider 计为一个 step（步）。
- `max_steps` 次 provider call 后，如果没有收到有效 `submit_result`，必须记录 `run.failed` 并返回 `failure_kind="max_steps_exceeded"`。
- 未收到 `submit_result` 时不得构造 completed `AgentRunResult`。
- `max_steps_exceeded` 的 `failed_action_ref` 必须为 `None`，因为失败不是某个单一 action 触发。

### Parse retry budget（解析重试预算）

`max_parse_failures` 表示可以反馈给 provider 并继续下一轮的 parse failure（解析失败）次数。

规则：

- provider output 无法通过 `parse_agent_action` 时，记录 `action.rejected`。
- 当 `parse_failures <= max_parse_failures` 时，`action.rejected.error.retryable` 为 `true`，并把简短 parse observation（解析观察）加入 observation window（观察窗口）。
- 当 `parse_failures > max_parse_failures` 时，`action.rejected.error.retryable` 为 `false`，随后记录 `run.failed`，返回 `failure_kind="action_parse_failed"`。
- 不得把 provider raw text（模型原始文本）转换为成功结果。
- 不得在 parser 失败后使用第二套 parser 或自由文本 fallback。

### Wall-time budget（墙钟时间预算）

`max_wall_seconds` 表示从 `started_at` 到当前 `runtime_clock()` 的最大允许 elapsed seconds（已用秒数）。

P0-008 必须在以下位置检查 wall-time budget：

1. 每个 provider turn（模型轮次）开始前。
2. provider output artifact（模型输出产物）和 `provider.turn.completed` 记录后，action parsing（动作解析）前。
3. permission decision（权限判定）允许后，tool execution（工具执行）或 `submit_result` 处理前。
4. tool result observation（工具结果观察）、workspace mutation（工作区变更）和 command completed（命令完成）事件记录后，下一轮 provider call 前。

检查规则：

- 如果 `elapsed_seconds > max_wall_seconds`，必须 fail closed。
- 如果 `elapsed_seconds < 0`，说明 `runtime_clock` 不单调，必须 fail closed，`failure_kind="invalid_invocation"`。
- 当 wall-time budget 在 provider call 返回后才耗尽，runtime 可以记录已完成的 provider turn，但不得继续 parse / execute action。
- 当 wall-time budget 在 tool execution 返回后才耗尽，runtime 可以记录真实 tool result、observation、workspace mutation 或 command completed 事件，但不得继续下一轮 provider call，也不得提交成功结果。
- P0-008 不负责中断已经运行中的 provider call 或 command process；它只保证每个边界点检查后不继续执行下一步。

### Failure result（失败结果）

P0-008 失败结果必须遵守 P0-007 `AgentRunResult` contract（运行结果契约）：

```python
AgentRunResult(
    status=AgentRunStatus.FAILED,
    failure_kind="max_wall_seconds_exceeded",
    failure_message="max_wall_seconds exceeded before next provider turn",
    failed_action_ref=None,
    event_stream_ref="artifact://run_001/events.jsonl",
    events_hash="sha256:<hex>",
    ...
)
```

`failure_kind` 取值：

| failure_kind | 中文解释 | 触发条件 |
|---|---|---|
| `invalid_invocation` | 调用非法 | budget 缺失、budget 类型非法、`runtime_clock` 非法或倒退 |
| `action_parse_failed` | 动作解析失败 | invalid JSON / schema failure 超过 `max_parse_failures` |
| `max_steps_exceeded` | 最大步数耗尽 | 达到 `max_steps` 后仍未 `submit_result` |
| `max_wall_seconds_exceeded` | 最大墙钟时间耗尽 | elapsed wall time 超过 `max_wall_seconds` |

P0-008 不改变 P0-007 已有 `provider_failed`、`policy_denied`、`tool_failed` 等 failure kind（失败类型）。

## Event Semantics

P0-008 不新增 event type（事件类型）。预算失败通过已有 `run.failed` 表示。

预算失败事件规则：

- budget validation failure（预算校验失败）：事件顺序为 `run.started` -> `run.failed`。
- max steps exceeded（最大步数耗尽）：失败前保留所有真实 provider/action/tool events，最后写 `run.failed`。
- parse retry exceeded（解析重试耗尽）：失败前记录最后一次 `provider.turn.completed` 和 `action.rejected`，最后写 `run.failed`。
- wall time exceeded before provider（模型轮次前超时）：事件顺序为 `run.started` -> `run.failed`，不记录 provider turn。
- wall time exceeded after provider（模型轮次后超时）：保留 `provider.turn.started` 和 `provider.turn.completed`，最后写 `run.failed`，不记录 `action.parsed`。
- wall time exceeded after tool（工具后超时）：保留真实 `tool.attempt.completed`、`workspace.mutation.recorded` 或 `command.completed`，最后写 `run.failed`，不继续下一轮 provider call。

`run.failed.payload.error` 必须包含：

```json
{
  "kind": "max_wall_seconds_exceeded",
  "message": "max_wall_seconds exceeded after tool execution",
  "retryable": false,
  "related_ref": "step-0001"
}
```

`related_ref` 规则：

- 与具体 action（动作）相关的 wall-time failure，使用 `action.action_id`。
- 发生在 provider turn 前且无当前 action 时，使用 `null`。
- 发生在 provider output 后但 action 尚未解析时，使用 `provider_turn_id`。

## Security and No-Fallback Rules

- `AgentLoop` 不得读取 `.env`、environment variables（环境变量）、local config files（本地配置文件）或 process defaults（进程默认值）来补齐预算。
- `AgentLoop` 不得对缺失 budget 使用 hardcoded default（硬编码默认值）。
- `AgentLoop` 不得在 budget failure 后继续调用 provider、执行工具或提交结果。
- `AgentLoop` 不得用 retry loop（重试循环）绕过 `max_steps` 或 `max_parse_failures`。
- `AgentLoop` 不得因 wall-time budget 失败而删除、改写或隐藏已经真实发生的 tool events（工具事件）或 workspace mutation events（工作区变更事件）。
- `AgentLoop` 不得为通过测试而使用 fake success path（模拟成功路径）；fake provider（假模型供应商）只能用于证明 runtime semantics（运行时语义）。
- `runtime_clock` 不得 fallback 到 `time.monotonic()`；真实时钟只能由调用方显式注入。

## Acceptance Criteria

P0-008 完成时必须证明：

- 缺失 `max_wall_seconds` 会 fail closed，返回 `failure_kind="invalid_invocation"`。
- 非法 `max_wall_seconds` 值（`0`、负数、`bool`、`NaN`、`inf`、字符串）会 fail closed。
- `max_steps`、`max_parse_failures`、`max_observation_chars` 的既有非法值校验仍然有效。
- wall-time budget 在第一个 provider turn 前耗尽时，不调用 provider，不执行工具，事件只有 `run.started` 和 `run.failed`。
- wall-time budget 在 provider output 记录后耗尽时，不解析 action，不执行工具，事件包含 provider completed 和 terminal failure。
- wall-time budget 在 tool result 记录后耗尽时，不继续下一轮 provider call，不提交成功结果，事件保留真实 tool attempt 和 mutation / command facts。
- invalid JSON retry exhaustion（无效 JSON 重试耗尽）仍记录 `action.rejected` 并 fail closed。
- max steps exhaustion（最大步数耗尽）仍 fail closed，不伪造成功。
- 所有失败运行都产生 parseable JSONL event stream（可解析 JSONL 事件流）和 failed `AgentRunResult`。
- `runtime_clock` 使用 deterministic fake clock 测试，不使用真实 sleep（睡眠）。
- `pytest -v` 通过。
- runtime source 不包含预算 fallback 模式：`.env`、`os.environ`、`getenv`、`dotenv`、内部 `time.monotonic()` fallback 或硬编码预算默认值。

## Documentation Impact

评审通过并完成实现后，需要更新：

- `docs/04-implementation-backlog/backlog.md`：将 P0-008 标记为 `completed`。
- `docs/04-implementation-spec/P0-008-fail-closed-budget-limits-spec.md`：将状态从 `draft` 改为 `implemented`。
- `docs/04-implementation-plan/P0-008-fail-closed-budget-limits-plan.md`：将状态从 `draft` 改为 `implemented`。
- `docs/04-implementation-spec/INDEX.md`：将本规格从 Current Active Documents（当前活跃文档）移动到 Completed / Archived Documents（已完成 / 已归档文档）。
- `docs/04-implementation-plan/INDEX.md`：将对应 plan（实施计划）从 Current Active Documents 移动到 Completed / Archived Documents。

P0-008 完成后，P0 表中所有非 deferred（延后）任务应为 completed（已完成），下一步应触发 P0 Exit Gate roadmap review（路线图复审），但 roadmap review 不属于 P0-008 实现范围。

## Self-Review Result

- Spec coverage（规格覆盖）：已覆盖 backlog P0-008、MVP `max steps / max wall time` 策略、MVP acceptance 中的 `max steps` 与 invalid JSON retry fail-closed 场景，并明确 P0-007 已有语义的回归要求。
- Placeholder scan（占位符扫描）：未使用占位标记、未完成提示或未定义要求。
- Internal consistency（内部一致性）：`max_wall_seconds` 使用 seconds（秒）作为唯一单位，`runtime_clock` 使用 monotonic seconds（单调秒），失败类型与现有 `AgentRunResult` 字段一致。
- Scope check（范围检查）：未纳入 token/cost/network/provider timeout/Boardroom adapter/external agent bridge 等非 P0-008 能力。
- No-fallback check（无兜底检查）：明确禁止 hidden default、环境读取、内部真实时钟 fallback 和预算失败后的继续执行。
