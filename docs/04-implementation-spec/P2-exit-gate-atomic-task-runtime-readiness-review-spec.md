# P2 Exit Gate Atomic Task Runtime Readiness Review Specification

## Status

implemented

## Purpose

本文定义 P2 Exit Gate（P2 退出门禁）`atomic task runtime readiness review`（原子任务运行时就绪复审）的规格。该 gate（门禁）在 P2 `Evidence Mapping and Integration Gates`（证据映射与集成门禁）所有非 deferred（延后）任务完成后触发，用于判断 `atomic-agent`（原子智能体）是否已经达到当前边界内的可用状态：接收 Boardroom OS（Boardroom 操作系统）编译后的完整 `AgentInvocation`（智能体调用请求），执行一个受权限约束的 atomic task（原子任务），并返回可审计 `AgentRunResult`（智能体运行结果）。

本规格明确：external coding agent bridge（外部编码智能体桥接）是 optional deferred extension（可选延后扩展）和备用方案，不是当前 atomic task runtime readiness（原子任务运行时就绪）的必选前置条件。若当前能力已达标，本轮 P2 Exit Gate 不开启 P3 execution wave（P3 执行波次）。

## Scope

本规格覆盖：

- 审查 `docs/04-implementation-backlog/backlog.md`（实现待办）中 P2 非 deferred（未延后）任务的 completed（完成）状态是否有代码、测试、规格、计划和文档证据支撑。
- 判断 Boardroom OS 编译后的 ticket package（工单包）是否能在当前边界内映射为完整 `AgentInvocation` 并交给 `AgentRuntimePort`（智能体运行时端口）执行。
- 对照 `docs/06-roadmap/roadmap.md`（路线图）逐项判断 M4 event stream / evidence mapping（事件流 / 证据映射）是否满足。
- 判断 M5 external coding agent bridge（外部编码智能体桥接）是否继续保持 deferred optional（延后可选），以及是否需要开启 P3。
- 记录 P2 exit review（P2 退出复审）为 project log（项目日志）。
- 更新 backlog（待办）中的 P2 Exit Gate 状态、P2-003 deferred optional 说明和必要索引。
- 判断是否需要 ADR（架构决策记录）；如仅确认当前边界并继续延期 external bridge，则不需要 ADR。

本规格不覆盖：

- 不实现 runtime source code（运行时源码）变更。
- 不实现 Boardroom `ExecutionPackage -> AgentInvocation`（执行包到智能体调用请求）编译器；该编译职责属于 Boardroom OS 或上层编排系统。
- 不实现 Boardroom EvidenceVerifier（证据验证器）、CloseoutGate（收尾门禁）或 governance event（治理事件）。
- 不实现 external coding agent bridge（外部编码智能体桥接）、`external_agent_run`（外部智能体运行）动作、CLI runner（命令行运行器）或外部 agent evidence importer（外部智能体证据导入器）。
- 不新增 P3 backlog（P3 待办）或 P3 implementation plan（P3 实施计划），除非复审发现当前 atomic task runtime readiness 不达标且缺口必须通过扩边解决。
- 不把 real provider（真实模型供应商）历史门禁的文本记录当作新的实时通过证据；如本次复审没有真实凭据或未显式运行真实供应商门禁，只能声称 base runtime readiness（基础运行时就绪）和已有 gate artifact（门禁产物）存在，不能声称本次重新验证了真实供应商。
- 不用 provider summary（模型摘要）、mock success path（模拟成功路径）或未验证文字替代真实 event stream（事件流）、artifact hash（产物哈希）、workspace mutation（工作区变更）或测试证据。

## Authoritative Inputs

P2 Exit Gate（P2 退出门禁）必须只依据已索引 authoritative documents（权威文档）和当前代码 / 测试证据：

- `README.md`（项目入口说明）。
- `AGENTS.md`（文档治理规则）。
- `docs/INDEX.md`（文档总索引）。
- `docs/00-overview/boardroom-os-integration-summary.md`（Boardroom OS 集成摘要）。
- `docs/02-architecture/runtime-architecture.md`（运行时架构）。
- `docs/02-architecture/event-and-evidence-architecture.md`（事件与证据架构）。
- `docs/02-architecture/permission-and-sandbox-architecture.md`（权限与沙箱架构）。
- `docs/03-contracts/agent-runtime-port.md`（智能体运行时端口契约）。
- `docs/03-contracts/agent-action-protocol.md`（智能体动作协议）。
- `docs/03-contracts/event-stream-protocol.md`（事件流协议）。
- `docs/04-implementation-backlog/backlog.md`（实现待办）。
- `docs/04-implementation-spec/mvp-runtime-spec.md`（MVP 运行时规格）。
- `docs/04-implementation-acceptance/mvp-acceptance.md`（MVP 验收标准）。
- `docs/05-testing/testing-strategy.md`（测试策略）。
- `docs/06-roadmap/roadmap.md`（路线图）。
- `docs/07-project-log/INDEX.md`（项目日志索引）。
- P2 completed specs / plans（P2 已完成规格 / 计划），尤其是：
  - `P2-001-evidence-mapping-artifact-hash-hardening-spec.md`。
  - `P2-002-real-provider-minimal-integration-gate-spec.md`。
  - `P2-004-real-provider-tool-success-gate-spec.md`。
  - `P2-005-openai-compatible-provider-options-hardening-spec.md`。
  - `P2-006-complex-real-provider-atomic-task-gate-spec.md`。
- `docs/09-adr/0002-use-provider-agnostic-action-protocol.md`（供应商无关动作协议 ADR）。
- `docs/09-adr/0003-use-fail-closed-permission-model.md`（失败关闭权限模型 ADR）。
- `docs/09-adr/0004-keep-boardroom-os-as-governance-source.md`（保持 Boardroom OS 为治理事实源 ADR）。
- Current runtime source under `src/atomic_agent/`（当前运行时源码目录）。
- Current tests under `tests/`（当前测试目录）。

## Trigger Conditions

P2 Exit Gate（P2 退出门禁）可以启动的条件：

1. `docs/04-implementation-backlog/backlog.md` 中 P2 表内所有非 deferred（未延后）任务均为 `completed`。
2. `P2-003` 若仍为 deferred（延后），必须明确说明它是 optional extension（可选扩展）或备用方案，不阻塞当前 runtime readiness（运行时就绪）判断。
3. P2 相关 spec（规格）和 plan（实施计划）已从 active pointer（当前指针）退出，或明确标记为 implemented（已实现）并在对应目录索引中归档。
4. 当前没有 blocked items（阻塞项）阻止 review（复审）。
5. 本规格和对应实施计划已通过用户评审；未评审前不得实施本 gate。

如果任一条件不满足，P2 Exit Gate 必须输出 blocked（阻塞）结论，不能把 gate 标记为 completed（完成），也不能用新增 P3 任务掩盖当前 P2 证据缺口。

## Capability Boundary

P2 Exit Gate 必须使用以下边界判断：

```text
Boardroom ExecutionPackage（执行包）
  -> Boardroom OS compiles package into AgentInvocation（Boardroom 编译为智能体调用请求）
  -> AgentRuntimePort.invoke(AgentInvocation)
  -> atomic-agent AgentLoop（原子智能体循环）
  -> controlled tools + event stream + artifacts（受控工具 + 事件流 + 产物）
  -> AgentRunResult（智能体运行结果）
  -> Boardroom EvidenceVerifier / CloseoutGate（Boardroom 证据验证器 / 收尾门禁）
```

本 gate 中“Boardroom OS 编译好的 ticket package（工单包）”必须解释为：Boardroom OS 或上层系统已经把 contract（契约）、role/profile/skill（角色 / 配置画像 / 技能）、workspace（工作区）、allowed write set（允许写入集合）、command policy（命令策略）、network policy（网络策略）、budgets（预算）和 output requirements（输出要求）编译成完整 `AgentInvocation`。

如果调用方要求 `atomic-agent` 直接接收 Boardroom 原生 `ExecutionPackage` 并在本仓库内完成编译，则该需求属于 out_of_scope_boardroom_mapping（Boardroom 映射职责越界），不能作为当前 P2 readiness（P2 就绪）失败项。是否要新增该 mapper（映射器）必须另行设计，且不能自动归入 P3 external agent bridge（外部智能体桥接）。

## Required Evidence

复审必须收集并记录以下证据：

| Evidence | 中文解释 | Required outcome |
|---|---|---|
| `git status --short` | 工作区状态 | 记录 review 前后文档变更；不得隐藏无关代码变更。 |
| P2 backlog table | P2 待办表 | 所有非 deferred P2 tasks（P2 任务）必须为 `completed`。 |
| P2 spec / plan indexes | P2 规格 / 计划索引 | P2 已完成规格和计划必须位于 completed / archived（已完成 / 已归档）区。 |
| `PYTHONPATH=src python -m pytest -q` | 全量基础测试 | 必须真实运行；失败时 gate 不得 completed。 |
| `PYTHONPATH=src python -m pytest -m permission_negative -q` | 权限负向门禁 | 必须真实运行；失败时 gate 不得 completed。 |
| `PYTHONPATH=src python -m pytest tests/test_runtime_port.py tests/test_evidence.py tests/test_real_provider_complex_task.py -q` | focused readiness tests（聚焦就绪测试） | 必须通过；真实 provider complex task（复杂真实供应商任务）默认应 skip（跳过）而不联网。 |
| README minimal example command | README 最小示例命令 | 必须真实运行并输出 completed result、JSONL event stream、artifact root 和 workspace output。 |
| Evidence summary check | 证据摘要检查 | 必须用真实 event stream 和 `AgentRunResult` 调用 `build_evidence_summary`，确认 command hashes（命令哈希）、workspace lineage（工作区谱系）和 replay status（重放状态）。 |
| Source scan | 源码扫描 | 不得新增 Boardroom governance completion（治理完成）字段或 default allow-all（默认全允许）语义。 |
| ADR requirement check | ADR 需求检查 | 如改变长期路线、治理边界、事件协议或权限原则，必须先进入 ADR。 |

Real provider（真实模型供应商）重新运行规则：

- 默认 P2 Exit Gate 不要求重新运行外部真实 provider gate（真实供应商门禁），因为这些门禁是 manual/nightly（手动 / 夜间）或 integration-profile（集成配置）性质。
- 若本次复审声明“真实 provider 当前仍通过”，必须显式运行对应真实 provider 命令并记录输出。
- 若没有凭据或未运行真实 provider gate，复审只能声明：相关 gate 已实现、默认禁用、base CI-safe（基础持续集成安全），不能声明本次实时 provider success（供应商成功）。

## Readiness Classification Rules

复审必须对每项能力给出以下状态之一：

- `satisfied`（已满足）：当前实现、测试和文档证据均满足该能力。
- `partially_satisfied`（部分满足）：核心能力存在，但验证、文档、门禁或边界说明不足。
- `not_satisfied`（未满足）：能力不存在或缺少关键安全边界。
- `blocked`（阻塞）：测试失败、证据矛盾或索引治理问题阻止判断。
- `out_of_scope`（范围外）：能力不属于 `atomic-agent` 当前职责。
- `deferred_optional`（延后可选）：能力是未来可选扩展，不阻塞当前 readiness。

### Atomic Task Runtime Readiness Required Items

必须逐项判断：

1. `AgentInvocation` input boundary（智能体调用请求输入边界）：`atomic-agent` 能接收完整 `AgentInvocation`，且不依赖 `.env`、环境变量或本地配置补齐 runtime core 字段。
2. `AgentRuntimePort.invoke` boundary（智能体运行时端口调用边界）：上层通过端口调用 runtime，返回 `AgentRunResult`。
3. Controlled `AgentLoop`（受控智能体循环）：provider output（模型输出）必须解析为 `AgentAction`，并经过 permission decision（权限决策）和 tool execution（工具执行）。
4. Filesystem / command / web tool boundaries（文件系统 / 命令 / 网络工具边界）：路径、allowed write set、command_id 和 network allowlist 均 fail closed。
5. Event stream and artifacts（事件流与产物）：成功和失败运行都产生可解析 event stream、artifact references 和 hash。
6. Evidence mapping（证据映射）：`build_evidence_summary` 能从 `AgentRunResult` 和 event stream 派生 provider/tool/workspace/command/source lineage（供应商 / 工具 / 工作区 / 命令 / 源码谱系）候选。
7. Atomic repair task gate（原子修复任务门禁）：complex real provider atomic task gate（复杂真实供应商原子任务门禁）已作为 default-disabled success-only integration gate（默认禁用且只接受成功的集成门禁）存在；本次未显式运行时不得声称实时 provider success。
8. Boardroom governance boundary（Boardroom 治理边界）：`atomic-agent` 不发出 `TICKET_COMPLETED`、`CLOSEOUT_COMMITTED`、`evidence_verified` 或 `source_inventory_accepted` 等治理结论。
9. Boardroom package compiler boundary（Boardroom 包编译边界）：`ExecutionPackage -> AgentInvocation` 属于 Boardroom OS 或上层职责；不属于当前 runtime readiness 缺口。

### M4 Classification Required Items

M4（event stream / evidence 映射）必须逐项判断：

1. event stream（事件流）可重放，或明确说明不可重放原因。
2. workspace mutation（工作区变更）包含 before/after hash（变更前后哈希）和 diff（差异）。
3. command result（命令结果）包含 stdout/stderr artifact hash（标准输出 / 标准错误产物哈希）。
4. Boardroom `SourceInventory`（源码清单）可追溯到 provider/tool/workspace lineage（模型供应商 / 工具 / 工作区谱系）候选。

M4 可以判定为 `satisfied`（已满足）的条件：上述 4 项均有实现、测试和文档证据，并且 evidence summary（证据摘要）明确不等于 Boardroom EvidenceVerifier（证据验证器）通过结论。

### M5 Classification Required Items

M5（external coding agent bridge，外部编码智能体桥接）必须逐项判断：

1. 外部 coding agent（编码智能体）只能作为 tool（工具）运行。
2. 外部 agent 的 diff（差异）、日志、命令结果必须导入事件和证据模型。
3. 外部 agent 不能绕过 permission policy（权限策略）。

本 P2 Exit Gate 的默认预期是：M5 为 `deferred_optional` 或 `not_started`。M5 未实现不能阻塞当前 atomic task runtime readiness，因为当前可用边界是 `AgentInvocation` 驱动的内建受控工具循环。只有用户明确决定扩边到外部 CLI agent（命令行智能体）或黑盒 agent bridge（智能体桥接）时，才需要重新激活 M5 设计/实现。

## P3 Decision Rules

P2 Exit Gate 不应自动创建 P3。只有同时满足以下条件时，才可以建议下一 P wave（下一执行波次）：

1. 当前 atomic task runtime readiness 未达标。
2. 缺口不能通过修复 P2 内部 evidence / permission / port / docs 问题解决。
3. 缺口确实需要新增外部 agent bridge、ExecutionPackage compiler（执行包编译器）或其它边界扩展。
4. 该扩展已有用户明确授权或 ADR 级别决策。

如果 readiness 已达标，则 gate 应记录“不开启 P3；external bridge 继续 deferred optional”。

## Required Outputs

P2 Exit Gate 完成后必须产生：

1. `docs/07-project-log/2026-06-08-P2-exit-review.md`（P2 退出复审日志），记录证据、能力矩阵、M4/M5 判定、ADR requirement check（ADR 需求检查）和 P3 decision（P3 决策）。
2. 更新 `docs/07-project-log/INDEX.md`，把 P2 exit review 加入 completed / archived（已完成 / 已归档）记录。
3. 更新 `docs/04-implementation-backlog/backlog.md`，将 P2 Exit Gate 标记为 completed 或 blocked，并明确 P2-003 external bridge 继续 deferred optional（延后可选）。
4. 执行完成后，将本规格状态从 `draft` 改为 `implemented`。
5. 执行完成后，将对应 implementation plan（实施计划）状态从 `draft` 改为 `implemented`。
6. 更新 `docs/04-implementation-spec/INDEX.md` 和 `docs/04-implementation-plan/INDEX.md`，将本规格 / 计划从 Current Active Documents（当前活跃文档）移动到 Completed / Archived Documents（已完成 / 已归档文档）。
7. 更新 `docs/INDEX.md`：移除本规格 / 计划的 active pointer（当前指针）；如果不打开 P3，不新增新的 P3 active pointer。
8. 如复审发现长期路线、治理边界或架构原则变化，先新增或更新 `docs/09-adr/`，并暂停普通 backlog 更新。

## Failure / Blocked Semantics

以下情况必须停止并报告 blocked（阻塞），不得把 P2 Exit Gate 标记为 completed：

- `PYTHONPATH=src python -m pytest -q` 失败。
- `PYTHONPATH=src python -m pytest -m permission_negative -q` 失败。
- focused readiness tests（聚焦就绪测试）失败。
- README minimal example（最小示例）命令无法真实运行。
- evidence summary（证据摘要）无法从真实 event stream 和 `AgentRunResult` 构造。
- P2 backlog completed 状态与 spec / plan / tests / source evidence（源码证据）矛盾。
- P2 completed spec / plan 仍在 active pointer（当前指针）且无合理说明。
- 发现 runtime code（运行时代码）产生 Boardroom governance completion（治理完成）字段。
- 复审必须依赖外部 Boardroom OS 私有事实，但当前仓库没有可验证依据。
- 用户要求 atomic-agent 直接接收原生 `ExecutionPackage` 并把该缺口作为 current readiness blocker（当前就绪阻塞）；此时应暂停并请求边界决策，而不是静默把 mapper 加入本 gate。
- 发现需要 ADR 级别改变路线、治理边界、事件协议或权限模型。

Blocked output（阻塞输出）必须记录：

- blocker（阻塞原因）。
- failed evidence（失败证据）。
- recommended next action（建议下一动作）。
- recovery path（恢复路径）。
- 明确说明 gate 未完成，且不打开 P3 作为掩盖性替代方案。

## Acceptance Criteria

本规格完成时必须证明：

- P2 Exit Gate 有明确 trigger（触发条件）、输入、输出、blocked semantics（阻塞语义）和 recovery path（恢复路径）。
- 当前 runtime readiness（运行时就绪）以完整 `AgentInvocation` 为输入边界，不把 Boardroom 原生 `ExecutionPackage` 编译器下沉到 atomic-agent。
- M4 exit criteria（M4 退出标准）有逐项判定规则。
- M5 external coding agent bridge（外部编码智能体桥接）被明确标记为 deferred optional（延后可选），不阻塞当前 readiness。
- P3 只有在明确扩边需求和用户授权后才可打开；达标时不新增 P3。
- review 不实现 runtime code、不新增 provider capability（供应商能力）、不运行外部 agent CLI（外部智能体命令行）和不产生治理结论。
- 文档更新路径遵守 `AGENTS.md` 和 `docs/INDEX.md` 的索引规则。
- 没有 silent fallback（静默降级）、mock success path（模拟成功路径）、第二事实源或 governance leakage（治理泄漏）。

## Documentation Impact

创建本规格和对应计划时需要更新：

- `docs/04-implementation-spec/INDEX.md`：加入本 draft spec（草案规格）。
- `docs/04-implementation-plan/INDEX.md`：加入对应 draft plan（草案计划）。
- `docs/INDEX.md`：加入本规格 / 计划作为当前活跃文档指针，直到用户评审并执行 gate。

执行本规格并完成 P2 Exit Gate 后，需要更新：

- `docs/07-project-log/2026-06-08-P2-exit-review.md`。
- `docs/07-project-log/INDEX.md`。
- `docs/04-implementation-backlog/backlog.md`。
- `docs/04-implementation-spec/P2-exit-gate-atomic-task-runtime-readiness-review-spec.md`：状态改为 `implemented`。
- `docs/04-implementation-plan/P2-exit-gate-atomic-task-runtime-readiness-review-plan.md`：状态改为 `implemented`。
- `docs/04-implementation-spec/INDEX.md` 和 `docs/04-implementation-plan/INDEX.md`：将本规格 / 计划从 active（当前活跃）移动到 completed / archived（已完成 / 已归档）。
- `docs/INDEX.md`：移除本规格 / 计划 active pointers（当前指针）；如不进入 P3，不新增 P3 指针。

## Self-Review Result

- Spec coverage（规格覆盖）：已覆盖 P2 Exit Gate 的 trigger、authoritative inputs（权威输入）、capability boundary（能力边界）、required evidence（必需证据）、atomic task readiness（原子任务就绪）、M4/M5 判定、P3 decision rules（P3 决策规则）、required outputs（必需产物）、blocked semantics（阻塞语义）、acceptance criteria（验收标准）和 documentation impact（文档影响）。
- Placeholder scan（占位符扫描）：未使用空白占位、未定义任务、模糊成功条件或未说明的后续补充。
- Boundary consistency（边界一致性）：明确 Boardroom OS 负责编译原生 `ExecutionPackage`，`atomic-agent` 的输入边界是完整 `AgentInvocation`。
- Scope check（范围检查）：未纳入 runtime code、外部 CLI runner、Boardroom EvidenceVerifier、P3 backlog、真实 provider 重新运行或 external agent bridge 实现。
- No-fallback check（无兜底检查）：测试失败、证据矛盾、README 示例失败、证据摘要失败、治理字段泄漏或 ADR 级变化都会 blocked，不会伪造 completed gate。
- Governance check（治理检查）：明确禁止 `ticket_completed`、`closeout_committed`、`evidence_verified`、`source_inventory_accepted` 等 Boardroom governance completion 字段。
