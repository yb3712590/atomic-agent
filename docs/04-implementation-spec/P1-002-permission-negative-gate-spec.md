# Permission Negative Gate Specification

## Status

implemented

## Purpose

本文定义 P1-002 `permission negative gate`（权限负向门禁）的实现规格。该能力负责把 `atomic-agent`（原子智能体）已经实现的 fail-closed permission model（失败关闭权限模型）收敛为一个可运行、可审计、不过度扩张的测试门禁，用于证明 filesystem（文件系统）、command（命令）、network（网络）、provider action parsing（模型动作解析）和 AgentLoop budget / observation（智能体循环预算 / 观察结果）边界不会被绕过。

P1-002 的目标不是新增一批重复测试，也不是把测试本身当成产品能力；目标是确认 atomic-agent 的核心受控执行能力已经可由一个稳定 gate（门禁）证明，并补齐少量只在 AgentLoop（智能体循环）层才能证明的安全事实：拒绝后没有 tool attempt（工具调用尝试）、没有 workspace mutation（工作区变更）、没有 network request（网络请求），并且最终产生真实 `run.failed` terminal event（终止事件）。

## Scope

P1-002 覆盖以下能力：

- 定义单一 permission negative gate（权限负向门禁）命令：`python -m pytest -m permission_negative -q`。
- 在 pytest（测试框架）配置中声明 `permission_negative` marker（权限负向测试标记）。
- 复用现有负向测试，按 acceptance scenario（验收场景）选择性标记，不批量标记所有低层防御测试。
- 使用 `pytest.param(..., marks=pytest.mark.permission_negative)` 标记现有 parameterized tests（参数化测试）中的相关 case（用例），避免扩大门禁运行面。
- 新增少量 AgentLoop capability tests（智能体循环能力测试），只补齐现有测试没有证明的运行时事件语义。
- 在 testing strategy（测试策略）中记录 gate command（门禁命令）和覆盖矩阵。
- 在 backlog（待办）中保持 P1-002 的依据链接可追溯到本规格。

不包含：

- 不实现新的 permission policy engine（权限策略引擎）。
- 不新增第二套 runtime（运行时）或第二套事件系统。
- 不新增新的 action type（动作类型）、tool type（工具类型）或 Boardroom adapter（Boardroom 适配器）。
- 不修改 README minimal example（最小示例）；该范围属于 P1-003。
- 不把所有 unit tests（单元测试）都纳入 `permission_negative` marker，避免门禁臃肿。
- 不用 mocked success path（模拟成功路径）证明权限能力；fake provider（假模型供应商）只能用于确定性触发真实 AgentLoop 语义。
- 不允许任何隐式 fallback（兜底），包括默认放行、环境变量补齐、自由 shell 改写为 command_id、URL 自动改写或网络请求失败伪成功。

## Authoritative Inputs

本规格依据以下已索引文档：

- `docs/04-implementation-backlog/backlog.md`（实现待办），其中 P1-002 为 pending（待执行）任务。
- `docs/05-testing/testing-strategy.md`（测试策略），定义 permission negative tests（权限负向测试）必需覆盖的场景。
- `docs/04-implementation-acceptance/mvp-acceptance.md`（MVP 验收标准），定义安全验收、事件验收和禁止成功条件。
- `docs/04-implementation-spec/mvp-runtime-spec.md`（MVP 运行时规格），定义 workspace、command、network 和 budget 策略。
- `docs/03-contracts/agent-action-protocol.md`（智能体动作协议），定义合法动作和 invalid actions（无效动作）。
- `docs/03-contracts/event-stream-protocol.md`（事件流协议），定义 `permission.decided`、`action.rejected`、`tool.attempt.*`、`network.fetch.completed` 和 terminal events（终止事件）。
- `docs/09-adr/0003-use-fail-closed-permission-model.md`（失败关闭权限模型 ADR）。

## Gate Command

P1-002 完成后，仓库必须支持：

```bash
python -m pytest -m permission_negative -q
```

语义：

- 只运行被明确标记为 permission negative（权限负向）的测试。
- 该 gate（门禁）必须覆盖 P1-002 acceptance matrix（验收矩阵）中列出的安全边界。
- 该 gate 不替代全量测试；实现完成仍必须运行 `python -m pytest -q`。
- marker（标记）选择必须可审查：每个被标记测试都应能映射到一个明确安全能力或验收场景。

## Acceptance Matrix

| Capability | 中文解释 | Required proof |
|---|---|---|
| Path traversal deny | 路径逃逸拒绝 | AgentLoop 收到 `../` 写入请求时记录 `permission.decided`、`action.rejected`、`run.failed`，不记录 `tool.attempt.started`，不写 workspace root 外文件。 |
| Symlink escape deny | 符号链接逃逸拒绝 | AgentLoop 收到指向 workspace 外部 symlink（符号链接）的写入请求时 fail closed，不写外部目标。 |
| AllowedWriteSet deny | 允许写入集合外拒绝 | 写入未允许路径时 fail closed，不执行 filesystem tool（文件系统工具）。 |
| Undeclared command deny | 未声明命令拒绝 | provider 请求未知 `command_id` 时 fail closed，不执行 process（进程）。 |
| Free shell string reject | 自由 shell 字符串拒绝 | `run_command` 使用 `command` / `shell` / `cmd` 字段时 schema validation（模式校验）失败。 |
| Network deny | 网络目标拒绝 | 未允许 URL 在 AgentLoop 权限阶段拒绝；本地 HTTP server（HTTP 服务器）未收到请求；不记录 `network.fetch.completed`。 |
| Missing network policy deny | 缺失网络策略拒绝 | 启用 `web_fetch` 但未配置 `web_fetch_tools` 时 fail closed，不创建默认 allowlist（允许列表）。 |
| Invalid JSON retry limit | 无效 JSON 重试限制 | provider 输出无效 JSON 时记录 `action.rejected`；超过 `max_parse_failures` 后 `run.failed`。 |
| Unknown action reject | 未知动作拒绝 | provider 输出未知 action 时 schema validation 失败并进入 fail-closed 路径。 |
| Max steps fail closed | 最大步数失败关闭 | 达到 `max_steps` 后未 `submit_result` 时 `run.failed`，不伪造 completed result（完成结果）。 |
| Observation truncation | 观察结果截断 | visible observation（可见观察）超过 `max_observation_chars` 时显式 `truncated=True`，artifact（产物）引用保留。 |

## Minimal Test Selection Rules

为避免不必要的测试，P1-002 使用以下选择规则：

1. 优先标记现有测试，尤其是已经验证 atomic-agent runtime capability（运行时能力）的 AgentLoop 测试。
2. 如果现有低层测试只证明 helper（辅助组件）行为，但不能证明事件和终止语义，则只新增一个聚焦 AgentLoop 测试。
3. 不重复测试同一 boundary（边界）的所有输入变体；参数化测试中只把对应验收场景纳入 marker。
4. 不把普通 happy path（成功路径）纳入 permission negative gate，除非它证明负向场景的对照条件。
5. 不通过测试改写运行时语义；如果 gate 暴露真实 capability gap（能力缺口），应修 runtime source（运行时代码），而不是放宽断言或增加 fallback。

## Expected Code-Level Changes

P1-002 预期只需要以下代码级变更：

- `pyproject.toml`：声明 `permission_negative` pytest marker。
- `tests/test_*.py`：对少量现有测试或参数化 case 增加 marker。
- `tests/test_agent_loop.py`：新增少量 AgentLoop capability tests，用于补齐 path traversal（路径逃逸）、symlink escape（符号链接逃逸）、unknown action（未知动作）和 observation truncation（观察结果截断）的运行时证明。

如果上述测试显示现有 atomic-agent capability 不满足规格，则实现阶段必须修复对应 runtime/tool/parser 代码；不得通过以下方式让 gate 通过：

- 删除或弱化断言。
- 把失败记录成成功。
- 在测试里绕过真实 AgentLoop。
- 添加默认 allowlist、默认 command policy、默认 write permission 或默认 budget。
- 把未允许输入转换成允许输入。

## Event Semantics

AgentLoop 层负向场景必须遵守：

- `run.started` 是第一条事件。
- 权限拒绝场景必须记录 `permission.decided`，随后记录 `action.rejected` 和 `run.failed`。
- 权限拒绝场景不得记录 `tool.attempt.started`，因为工具没有被允许执行。
- 网络拒绝场景不得记录 `network.fetch.completed`。
- parse failure（解析失败）场景必须记录 `provider.turn.completed` 和 `action.rejected`。
- 所有失败运行必须返回 failed `AgentRunResult`（失败运行结果），并包含 `failure_kind`、`failure_message` 和 `events_hash`。

## Documentation Impact

评审通过并完成实现后，需要更新：

- `docs/05-testing/testing-strategy.md`：增加 `permission_negative` gate command（门禁命令）和覆盖说明。
- `docs/04-implementation-backlog/backlog.md`：P1-002 完成后标记为 `completed`。
- `docs/04-implementation-spec/P1-002-permission-negative-gate-spec.md`：实现完成后状态从 `draft` 改为 `implemented`。
- `docs/04-implementation-plan/P1-002-permission-negative-gate-plan.md`：实现完成后状态从 `draft` 改为 `implemented`。
- `docs/04-implementation-spec/INDEX.md` 和 `docs/04-implementation-plan/INDEX.md`：实现完成后将 P1-002 规格和计划移入 completed / archived（已完成 / 已归档）区。
- 如当前活跃文档指针变化，更新 `docs/INDEX.md`。

P1-002 不更新 README minimal example（最小示例），因为真实 minimal example 属于 P1-003。

## Self-Review Result

- Spec coverage（规格覆盖）：已覆盖 backlog P1-002、testing strategy 中的 permission negative scenarios（权限负向场景）、MVP acceptance 的安全与事件要求，并明确 P1-003/P1-004 不在范围内。
- Placeholder scan（占位符扫描）：未使用占位式标记、占位实现或“稍后补充”措辞。
- Minimality check（最小性检查）：规格要求复用现有测试，新增测试仅限 AgentLoop 层缺口，不要求大规模新建测试套件。
- Type / naming consistency（类型与命名一致性）：`permission_negative`、`AgentLoop`、`AgentRunResult`、`permission.decided`、`action.rejected`、`tool.attempt.started`、`network.fetch.completed` 命名与现有代码和协议一致。
- Scope check（范围检查）：未纳入新工具、新动作、Boardroom adapter、README 示例、真实 provider 集成或外部 agent bridge。
- No-fallback check（无兜底检查）：明确禁止默认放行、环境读取补齐、输入改写、网络错误伪成功、自由 shell fallback 和 mocked success path。
