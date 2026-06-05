# P0 Exit Gate Roadmap Review Specification

## Status

implemented

## Purpose

本文定义 P0 Exit Gate `roadmap review`（路线图复审）的规格。该 gate（门禁）在 P0 execution wave（P0 执行波次）所有非 deferred（延后）任务完成后触发，用于审查 P0 完成事实、对照 roadmap milestone exit criteria（路线图里程碑退出标准），并滚动编制下一批次 `cohesive work package`（内聚工作包）。

该规格的目标不是实现 P1 功能，也不是把 roadmap review（路线图复审）编号为普通 backlog task（待办任务）。它只定义 review（复审）必须怎样收集证据、输出结论、更新 backlog（待办）和记录项目日志。

## Scope

本规格覆盖：

- 审查 `docs/04-implementation-backlog/backlog.md`（实现待办）中 P0-001 到 P0-008 的 completed（已完成）状态是否有证据支撑。
- 对照 `docs/06-roadmap/roadmap.md`（路线图）判断 M1、M2、M3 相关 exit criteria（退出标准）的满足状态。
- 核对 P0 相关 tests（测试）、acceptance（验收）和 docs（文档）是否足以触发 P0 Exit Gate（P0 退出门禁）。
- 记录 P0 exit review（P0 退出复审）为 project log（项目日志）。
- 滚动更新 P1 execution wave（P1 执行波次）的工作包、顺序、依据、依赖和验收标准。
- 按文档治理规则同步更新相关 `INDEX.md`（目录索引）和必要的 `docs/INDEX.md`（文档总索引）。

本规格不覆盖：

- 不实现 `web_fetch`（网络获取）或 `NetworkPolicy`（网络策略）。
- 不实现 Boardroom `AgentRuntimePort adapter`（Boardroom 智能体运行时端口适配器）。
- 不新增真实 provider integration（真实模型供应商集成）。
- 不把 P0 Exit Gate（P0 退出门禁）编号为 `P0-009` 或普通 implementation task（实现任务）。
- 不修改长期路线或项目边界；如 review（复审）发现必须改变长期路线、治理边界或架构原则，应先提出 ADR（架构决策记录）需求并停止普通 backlog 更新。
- 不用 fake success path（模拟成功路径）替代测试、事件流或文档证据。

## Authoritative Inputs

P0 Exit Gate（P0 退出门禁）必须只依据已索引 authoritative documents（权威文档）和当前代码 / 测试证据：

- `README.md`（项目入口说明）。
- `AGENTS.md`（智能体协作和文档治理规则）。
- `docs/INDEX.md`（文档总索引）。
- `docs/04-implementation-backlog/backlog.md`（实现待办）。
- `docs/04-implementation-spec/mvp-runtime-spec.md`（MVP 运行时规格）。
- `docs/04-implementation-acceptance/mvp-acceptance.md`（MVP 验收标准）。
- `docs/05-testing/testing-strategy.md`（测试策略）。
- `docs/06-roadmap/roadmap.md`（路线图）。
- `docs/07-project-log/INDEX.md`（项目日志索引）。
- `docs/03-contracts/agent-runtime-port.md`（智能体运行时端口契约）。
- `docs/03-contracts/agent-action-protocol.md`（智能体动作协议）。
- `docs/03-contracts/event-stream-protocol.md`（事件流协议）。
- `docs/09-adr/0003-use-fail-closed-permission-model.md`（失败关闭权限模型 ADR）。

## Trigger Conditions

P0 Exit Gate（P0 退出门禁）可以启动的条件：

1. `backlog.md` 中 P0 表内所有非 deferred（延后）任务均为 `completed`。
2. P0 相关实现文件和测试文件存在，并能被真实测试命令验证。
3. P0 相关 spec（规格）和 plan（实施计划）已从 active pointer（当前指针）退出或明确标记为 implemented（已实现）。
4. 当前没有 blocked items（阻塞项）阻止 review（复审）。

如果任一条件不满足，P0 Exit Gate（P0 退出门禁）必须输出 blocked（阻塞）结论，而不是滚动更新 P1 work package（P1 工作包）。

## Required Evidence

复审必须收集并记录以下证据：

| Evidence | 中文解释 | Required outcome |
|---|---|---|
| `git status --short` | 工作区状态 | 说明 review 前后有哪些文档变更；不得隐藏无关代码变更。 |
| `pytest -v` | 全量测试 | 必须真实运行；如果失败，P0 Exit Gate 不得标记 completed。 |
| P0 backlog table | P0 待办表 | P0-001 到 P0-008 的状态必须全部为 completed。 |
| Spec / plan indexes | 规格 / 计划索引 | P0 已完成规格和计划应位于 completed / archived 区。 |
| README minimal example section | README 最小示例章节 | 如仍声称没有 minimal example（最小示例），review 必须明确这是下一波次文档 / entrypoint（入口）缺口，不能伪造命令。 |
| Event / runtime tests | 事件 / 运行时测试 | 必须说明 fake provider loop（假模型供应商循环）、JSONL event stream（JSONL 事件流）和 fail-closed（失败关闭）测试覆盖情况。 |
| Negative test inventory | 负向测试盘点 | 必须盘点现有 permission negative tests（权限负向测试）覆盖情况，P1-002 只整合已有覆盖并补齐缺口，避免重复实现。 |

## Milestone Classification Rules

复审必须对 roadmap（路线图）中的相关 milestone（里程碑）给出以下状态之一：

- `satisfied`（已满足）：当前实现、测试和文档证据均满足该条 exit criterion（退出标准）。
- `partially_satisfied`（部分满足）：核心实现存在，但测试、文档、入口、负向场景或集成证据不足。
- `not_satisfied`（未满足）：当前实现不存在或缺少关键安全边界。
- `not_started`（未开始）：后续里程碑尚未进入实现。
- `blocked`（阻塞）：有明确缺陷或失败测试阻止判断为通过。

### M1 Classification Required Items

M1（最小 AgentLoop + filesystem tools）必须逐项判断：

1. 可运行 fake provider loop（假模型供应商循环）。
2. 支持 `list_files`、`read_file`、`search_files`、`write_file`、`apply_patch`。
3. 支持 `AgentAction` JSON schema validation（JSON 模式校验）。
4. 支持 JSONL event stream（JSONL 事件流）。
5. 支持 workspace root（工作区根目录）和 allowed write set（允许写入集合）守卫。

### M2 Classification Required Items

M2（command / web tools + permission policy）必须逐项判断：

1. 支持 `run_command`，且只接受 `command_id`（命令标识）。
2. 支持 `web_fetch`，且受 network policy（网络策略）限制。
3. 权限负向测试覆盖 P0 安全边界。
4. 预算超限和无效动作都 fail closed（失败关闭）。

### M3 Classification Required Items

M3（Boardroom AgentRuntimePort 对接）在本 gate（门禁）中通常应标记为 `not_started` 或 `partially_satisfied`，除非已有明确 adapter（适配器）实现和映射测试。复审不得把 `AgentRunResult`（智能体运行结果）模型存在误判为 Boardroom adapter（Boardroom 适配器）已实现。

## P1 Work Package Rules

滚动更新 P1 execution wave（P1 执行波次）时必须遵守：

1. 每个 P1 task（任务）必须链接 spec（规格）、contract（契约）、acceptance（验收）、testing（测试）或 ADR（架构决策记录）依据。
2. 不保留已经被 P0 证据满足的 pending task（待处理任务）；必须标记为 completed（已完成）或重新定义剩余缺口。
3. 不把大型跨阶段能力塞进一个任务；每个 work package（工作包）必须能独立实现、测试和验收。
4. 优先补齐安全边界和可审计性，再做上层 Boardroom integration（Boardroom 集成）。
5. 如果 README minimal example（最小示例）仍不真实可运行，应把它作为明确的 docs / entrypoint（文档 / 入口）缺口，而不是在 README 中写伪命令。
6. P1 顺序必须解释依赖关系；例如 permission negative tests（权限负向测试）中的 network deny（网络拒绝）依赖 `NetworkPolicy`（网络策略）。

推荐的 P1 work package（P1 工作包）基线如下，最终以 review（复审）证据为准：

| ID | Task | Rationale |
|---|---|---|
| P1-001 | 实现 `web_fetch` 和 `NetworkPolicy`（网络策略） | 补齐 M2 中缺失的网络能力和 allowlist（允许列表）守卫。 |
| P1-002 | 整合现有 permission negative tests（权限负向测试）为单一门禁，并补齐网络拒绝场景 | 盘点并复用 P0 已有越权路径、symlink escape（符号链接逃逸）、未声明命令、未知动作、无效 JSON、max steps（最大步数）和 observation truncation（观察截断）覆盖；只新增缺口，尤其是 unallowed URL（未允许 URL）拒绝。 |
| P1-003 | 固化 fake provider loop acceptance（假模型供应商循环验收）并建立真实 minimal example（最小示例）文档路径 | 避免 README（说明文档）继续声称无示例或用伪命令替代真实运行；只有真实 CLI entrypoint（命令行入口）可运行、能产生 JSONL event stream（JSONL 事件流）、并能演示至少一个成功 fake provider loop 后，才允许更新 README。 |
| P1-004 | 实现 Boardroom `AgentRuntimePort adapter`（智能体运行时端口适配器） | 在 M1/M2 运行时语义和安全测试更稳定后进入 M3 对接。 |

## Required Outputs

P0 Exit Gate（P0 退出门禁）完成后必须产生：

1. `docs/07-project-log/2026-06-05-P0-exit-review.md`（P0 退出复审日志），记录证据、里程碑矩阵、已知缺口和 P1 proposal（P1 建议）。
2. 更新 `docs/07-project-log/INDEX.md`，把该日志加入 completed / archived（已完成 / 已归档）记录。
3. 更新 `docs/04-implementation-backlog/backlog.md`，明确 P0 Exit Gate 状态，并滚动更新 P1 work package（P1 工作包）。
4. 如新增或完成本规格 / 计划文档，更新 `docs/04-implementation-spec/INDEX.md` 和 `docs/04-implementation-plan/INDEX.md`。
5. 如全局 active pointer（当前指针）变化，更新 `docs/INDEX.md`。

## Failure / Blocked Semantics

以下情况必须停止并报告 blocked（阻塞），不得继续滚动更新 P1：

- `pytest -v` 失败。
- P0 task（P0 任务）状态与实现证据矛盾。
- P0 spec / plan index（规格 / 计划索引）显示仍有应完成但未完成的 P0 active implementation document（活跃实现文档）。
- 发现需要 ADR（架构决策记录）级别的长期路线、治理边界或契约语义变化。
- review（复审）需要外部 Boardroom OS（Boardroom 操作系统）事实，但当前仓库没有可验证依据。

Blocked output（阻塞输出）必须记录：

- blocker（阻塞原因）。
- failed evidence（失败证据）。
- recommended next action（建议下一动作）。
- recovery path（恢复路径）。
- 不得把 gate（门禁）标为 completed。

Blocked recovery path（阻塞恢复路径）必须包含：

1. 修复失败测试、证据矛盾或索引治理问题。
2. 重新运行 P0 Exit Gate（P0 退出门禁）验证，包括真实 `pytest -v`。
3. 如果再次 blocked（阻塞），将问题记录为 project blocker（项目阻塞），并升级给人工决策；不得静默降低验收标准。

## Acceptance Criteria

本规格完成时必须证明：

- P0 Exit Gate（P0 退出门禁）有明确 trigger（触发条件）、输入、输出和 blocked semantics（阻塞语义）。
- review（复审）不会直接实现 P1 功能。
- review（复审）不会把 P0 Exit Gate 编号为普通 P0 task。
- M1/M2/M3 milestone criteria（里程碑标准）有逐项判定规则。
- P1 work package（P1 工作包）滚动更新规则明确，并避免保留已被证据满足的 pending task。
- P1-002 明确为整合现有负向测试覆盖并补齐缺口，不重复实现已覆盖场景。
- P1-003 明确 README minimal example（最小示例）只有在真实 CLI command（命令行命令）可运行、产生 JSONL event stream（JSONL 事件流）且演示成功 fake provider loop 后才更新。
- 文档更新路径遵守 `AGENTS.md` 和 `docs/INDEX.md` 的索引规则。
- 没有 silent fallback（静默降级）、mock success path（模拟成功路径）或第二套事实源。

## Documentation Impact

创建本规格时需要更新：

- `docs/04-implementation-spec/INDEX.md`：加入本 draft spec（草案规格）。
- `docs/INDEX.md`：如当前活跃实现指针需要显式暴露 P0 Exit Gate（P0 退出门禁），加入本规格指针。

执行本规格并完成 P0 Exit Gate 后，需要更新：

- `docs/07-project-log/2026-06-05-P0-exit-review.md`。
- `docs/07-project-log/INDEX.md`。
- `docs/04-implementation-backlog/backlog.md`。
- `docs/04-implementation-spec/P0-exit-gate-roadmap-review-spec.md`：状态改为 `implemented`。
- `docs/04-implementation-plan/P0-exit-gate-roadmap-review-plan.md`：状态改为 `implemented`。
- `docs/04-implementation-spec/INDEX.md` 和 `docs/04-implementation-plan/INDEX.md`：将本规格 / 计划从 active（当前活跃）移动到 completed / archived（已完成 / 已归档）。
- `docs/INDEX.md`：移除或更新 P0 Exit Gate active pointer（当前指针）。

## Self-Review Result

- Spec coverage（规格覆盖）：已覆盖 backlog 中 P0 Exit Gate 的 trigger、required outputs、roadmap review protocol、P1 work package 滚动更新要求、负向测试盘点和 blocked 恢复路径。
- Placeholder scan（占位符扫描）：未使用占位标记、空章节或未定义任务。
- Internal consistency（内部一致性）：P0 Exit Gate 明确不是普通 backlog task；P1 work package 只在 review 完成后更新。
- Scope check（范围检查）：未包含 `web_fetch`、Boardroom adapter、真实 provider 或任何 P1 功能实现。
- No-fallback check（无兜底检查）：测试失败、证据矛盾或 ADR 级变化都会 blocked，不会伪造 completed gate。
