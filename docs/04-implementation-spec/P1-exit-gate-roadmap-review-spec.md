# P1 Exit Gate Roadmap Review Specification

## Status

implemented

## Purpose

本文定义 P1 Exit Gate `roadmap review`（路线图复审）的规格。该 gate（门禁）在 P1 execution wave（P1 执行波次）所有非 deferred（延后）任务完成后触发，用于完成 P1 收尾、文档治理、roadmap milestone（路线图里程碑）复审，并滚动编制下一批 P2 cohesive work packages（内聚工作包）。

该规格的目标不是实现 P2 功能，也不是启动 event stream / evidence mapping（事件流 / 证据映射）、real provider integration（真实模型供应商集成）或 external coding agent bridge（外部编码智能体桥接）。它只定义 review（复审）必须如何收集证据、输出结论、更新 backlog（待办）、维护索引、记录 project log（项目日志），并规划 P2 阶段工作包。

## Scope

本规格覆盖：

- 审查 `docs/04-implementation-backlog/backlog.md`（实现待办）中 P1-001 到 P1-004 的 completed（已完成）状态是否有证据支撑。
- 对照 `docs/06-roadmap/roadmap.md`（路线图）判断 M1、M2、M3、M4、M5 相关 exit criteria（退出标准）的满足状态。
- 核对 P1 相关 integration（集成）、permission negative gate（权限负向门禁）、minimal example（最小示例）、Boardroom adapter（Boardroom 适配器）和 docs（文档）是否足以触发 P1 Exit Gate。
- 记录 P1 exit review（P1 退出复审）为 project log（项目日志）。
- 滚动更新 P2 execution wave（P2 执行波次）的工作包、顺序、依据、依赖和验收标准。
- 判断 real provider integration tests（真实模型供应商集成测试）是否进入 P2，并明确其 gate（门禁）属性。
- 按文档治理规则同步更新相关 `INDEX.md`（目录索引）和必要的 `docs/INDEX.md`（文档总索引）。

本规格不覆盖：

- 不实现任何 P2 task（P2 任务）。
- 不实现 event stream / evidence mapping hardening（事件流 / 证据映射硬化）。
- 不实现 real provider integration tests（真实模型供应商集成测试）。
- 不实现 external coding agent bridge（外部编码智能体桥接）。
- 不修改 runtime source code（运行时源码）。
- 不新增 provider API key（模型供应商密钥）配置或真实外部调用。
- 不把 P1 Exit Gate（P1 退出门禁）编号为 `P1-005` 或普通 implementation task（实现任务）。
- 不修改长期路线、治理边界或架构原则；如 review（复审）发现必须改变长期路线、Boardroom boundary（Boardroom 边界）或 evidence model（证据模型）原则，应先提出 ADR（架构决策记录）需求，并停止普通 P2 backlog（待办）更新。
- 不用 fake success path（模拟成功路径）、mock evidence（模拟证据）或未验证文本替代测试、事件流、artifact（产物）或文档证据。

## Authoritative Inputs

P1 Exit Gate（P1 退出门禁）必须只依据已索引 authoritative documents（权威文档）和当前代码 / 测试证据：

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
- `docs/02-architecture/event-and-evidence-architecture.md`（事件与证据架构）。
- `docs/02-architecture/permission-and-sandbox-architecture.md`（权限与沙箱架构）。
- `docs/00-overview/boardroom-os-integration-summary.md`（Boardroom 集成边界）。
- `docs/09-adr/0002-use-provider-agnostic-action-protocol.md`（provider agnostic action protocol，供应商无关动作协议 ADR）。
- `docs/09-adr/0003-use-fail-closed-permission-model.md`（失败关闭权限模型 ADR）。
- `docs/09-adr/0004-keep-boardroom-os-as-governance-source.md`（保持 Boardroom OS 为治理事实源 ADR）。

## Trigger Conditions

P1 Exit Gate（P1 退出门禁）可以启动的条件：

1. `backlog.md` 中 P1 表内所有非 deferred（延后）任务均为 `completed`。
2. P1 相关实现文件、测试文件、README minimal example（最小示例）和 Boardroom adapter（Boardroom 适配器）文档存在，并能被真实验证命令验证。
3. P1 相关 spec（规格）和 plan（实施计划）已从 active pointer（当前指针）退出，或明确标记为 implemented（已实现）并在对应目录索引中归档。
4. P1 permission negative gate（权限负向门禁）存在，并能通过真实命令运行。
5. 当前没有 blocked items（阻塞项）阻止 review（复审）。

如果任一条件不满足，P1 Exit Gate（P1 退出门禁）必须输出 blocked（阻塞）结论，而不是滚动确认 P2 work package（P2 工作包）。

## Required Evidence

复审必须收集并记录以下证据：

| Evidence | 中文解释 | Required outcome |
|---|---|---|
| `git status --short` | 工作区状态 | 说明 review 前后有哪些文档变更；不得隐藏无关代码变更。 |
| `python -m pytest -q` | 全量测试 | 必须真实运行；如果失败，P1 Exit Gate 不得标记 completed。 |
| `python -m pytest -m permission_negative -q` | 权限负向门禁 | 必须真实运行；如果失败，P1 Exit Gate 不得标记 completed。 |
| Minimal example command | README 最小示例命令 | 必须真实运行，产生 JSONL event stream（JSONL 事件流）、artifact（产物）和 `AgentRunResult`（智能体运行结果）。 |
| P1 backlog table | P1 待办表 | P1-001 到 P1-004 的状态必须全部为 completed。 |
| Spec / plan indexes | 规格 / 计划索引 | P1 已完成规格和计划应位于 completed / archived（已完成 / 已归档）区。 |
| Event stream output | 事件流输出 | 必须解析 minimal example（最小示例）生成的 JSONL，确认至少包含 `run.started`、provider turn（模型轮次）、`action.parsed`、`permission.decided`、tool attempt（工具调用尝试）和 terminal（终止）事件；只验证文件存在不算通过。 |
| Boardroom adapter tests | Boardroom 适配器测试 | 必须运行 adapter 测试，证明 adapter 接受 `AgentInvocation`（智能体调用请求）、原样透传 `AgentRunResult`（智能体运行结果）、拒绝非法输入 / 输出，并且不产生 Boardroom governance completion（治理完成）字段。 |
| Documentation indexes | 文档索引 | 新增或归档文档必须同步对应 `INDEX.md`；不得形成第二事实源。 |

## Milestone Classification Rules

复审必须对 roadmap（路线图）中的相关 milestone（里程碑）给出以下状态之一：

- `satisfied`（已满足）：当前实现、测试和文档证据均满足该条 exit criterion（退出标准）。
- `partially_satisfied`（部分满足）：核心实现存在，但测试、文档、入口、负向场景或集成证据不足。
- `not_satisfied`（未满足）：当前实现不存在或缺少关键安全边界。
- `not_started`（未开始）：后续里程碑尚未进入实现。
- `blocked`（阻塞）：有明确缺陷、失败测试或证据矛盾阻止判断为通过。

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
3. 权限负向测试覆盖 P0/P1 安全边界。
4. 预算超限和无效动作都 fail closed（失败关闭）。

### M3 Classification Required Items

M3（Boardroom AgentRuntimePort 对接）必须逐项判断：

1. 定义并实现 `AgentRuntimePort`（智能体运行时端口）。
2. Boardroom OS（Boardroom 操作系统）能构造 `AgentInvocation`（智能体调用请求）。
3. `AgentRunResult`（智能体运行结果）可映射为 Boardroom evidence（证据）输入。
4. atomic-agent（原子智能体）不产生 Boardroom governance completion（治理完成）事件。

复审不得把普通 runtime result（运行时结果）存在误判为 Boardroom evidence mapping（Boardroom 证据映射）完整；必须检查 adapter（适配器）边界和测试证据。

### M4 Classification Required Items

M4（event stream / evidence 映射）必须逐项判断：

1. event stream（事件流）可重放，或明确说明不可重放原因。
2. workspace mutation（工作区变更）包含 before/after hash（变更前后哈希）和 diff（差异）。
3. command result（命令结果）包含 stdout/stderr artifact hash（标准输出 / 标准错误产物哈希）。
4. Boardroom `SourceInventory`（源码清单）可追溯到 provider/tool/workspace lineage（模型供应商 / 工具 / 工作区谱系）。

P1 Exit Gate 通常只应把 M4 标记为 `partially_satisfied`、`not_satisfied` 或 `not_started`，除非已有明确 evidence mapping（证据映射）实现与测试。不得用 P1 的 Boardroom adapter（Boardroom 适配器）完成状态替代 M4 证据谱系验收。

M4 判定边界：

- `satisfied`（已满足）：上述 4 项均有实现、测试和文档证据。
- `partially_satisfied`（部分满足）：event stream（事件流）、artifact（产物）或 mutation（变更）基础能力存在，但 replayability（可重放性）、before/after hash（变更前后哈希）、diff（差异）、command artifact hash（命令产物哈希）或 lineage（谱系）中至少一项缺少明确验证。
- `not_satisfied`（未满足）：event stream 不支持 replayability 且没有明确不可重放原因，或证据链缺少关键事件 / artifact / mutation 事实。
- `blocked`（阻塞）：现有事件、产物或 adapter 证据互相矛盾，导致无法可靠判断 M4 状态。

### M5 Classification Required Items

M5（external coding agent bridge，外部编码智能体桥接）必须逐项判断：

1. 外部 coding agent（编码智能体）只能作为 tool（工具）运行。
2. 外部 agent 的 diff（差异）、日志、命令结果必须导入事件和证据模型。
3. 外部 agent 不能绕过 permission policy（权限策略）。

P1 Exit Gate 不应把 M5 标记为 satisfied（已满足），除非已有明确外部 agent bridge（外部智能体桥接）实现、安全边界和证据导入测试。

## P2 Work Package Rules

滚动更新 P2 execution wave（P2 执行波次）时必须遵守：

1. 每个 P2 task（任务）必须链接 spec（规格）、contract（契约）、acceptance（验收）、testing（测试）、architecture（架构）、roadmap（路线图）或 ADR（架构决策记录）依据。
2. 不保留已经被 P1 证据满足的 pending task（待处理任务）；必须标记为 completed（已完成）、deferred（延后）或重新定义剩余缺口。
3. 不把大型跨阶段能力塞进一个任务；每个 work package（工作包）必须能独立实现、测试和验收。
4. 优先补齐 event/evidence traceability（事件 / 证据可追溯性）和 Boardroom evidence mapping（Boardroom 证据映射），再进入 external coding agent bridge（外部编码智能体桥接）。
5. real provider integration tests（真实模型供应商集成测试）如进入 P2，必须明确为 manual/nightly gate（手动 / 夜间门禁）或 integration profile（集成配置），不得阻塞基础 CI（持续集成）稳定性。
6. P2 顺序必须解释依赖关系；例如 external coding agent bridge（外部编码智能体桥接）依赖 M4 evidence mapping（证据映射）稳定。
7. 既有 deferred（延后）扩展项可以在 review 中重组、保留或移出当前 P2，但必须说明原因，避免形成第二套 backlog（待办）。

推荐的 P2 work package（P2 工作包）基线如下，最终以 P1 review（复审）证据为准：

| ID | Task | Rationale |
|---|---|---|
| P2-001 | 完善 event stream / evidence mapping（事件流 / 证据映射）和 artifact hash（产物哈希）硬化 | 服务 M4；确保 workspace mutation（工作区变更）、command result（命令结果）和 SourceInventory（源码清单）可追溯。 |
| P2-002 | 建立 real provider minimal integration gate（真实模型供应商最小集成门禁） | 验证真实 provider 至少能输出合法 `AgentAction`（智能体动作），并由 runtime（运行时）真实执行和记录；建议 manual/nightly，不进入基础 CI 必跑。 |
| P2-003 | 设计 external coding agent bridge（外部编码智能体桥接）的证据导入协议和权限边界 | 服务 M5；保持 deferred（延后），但下一步输出必须是 design spec（设计规格）或 ADR（架构决策记录）草案，不能只做不可验收的“重新评估”。 |

## Required Outputs

P1 Exit Gate（P1 退出门禁）完成后必须产生：

1. `docs/07-project-log/2026-06-07-P1-exit-review.md`（P1 退出复审日志），记录证据、里程碑矩阵、已知缺口、real provider integration（真实模型供应商集成）判断和 P2 proposal（P2 建议）。
2. 更新 `docs/07-project-log/INDEX.md`，把该日志加入 completed / archived（已完成 / 已归档）记录。
3. 更新 `docs/04-implementation-backlog/backlog.md`，明确 P1 Exit Gate 状态，并滚动更新 P2 work package（P2 工作包）。
4. 如新增或完成本规格 / 计划文档，更新 `docs/04-implementation-spec/INDEX.md` 和 `docs/04-implementation-plan/INDEX.md`。
5. 如全局 active pointer（当前指针）或 reading path（阅读路径）变化，更新 `docs/INDEX.md`。
6. 如 review（复审）发现长期路线、项目边界或架构原则变化，先新增或更新 `docs/09-adr/`（架构决策记录），并暂停普通 P2 backlog 更新。

## Failure / Blocked Semantics

以下情况必须停止并报告 blocked（阻塞），不得继续确认 P2 work package（P2 工作包）：

- `python -m pytest -q` 失败。
- `python -m pytest -m permission_negative -q` 失败。
- README minimal example（最小示例）命令不能真实运行，但 P1-003 被标记为 completed 且无合理解释。
- P1 task（P1 任务）状态与实现、测试或文档证据矛盾。
- P1 spec / plan index（规格 / 计划索引）显示仍有应完成但未完成的 P1 active implementation document（活跃实现文档）。
- Boardroom adapter（Boardroom 适配器）证据不足，但 M3 被声称 satisfied（已满足）。
- 发现需要 ADR（架构决策记录）级别的长期路线、治理边界或契约语义变化。
- review（复审）需要外部 Boardroom OS（Boardroom 操作系统）事实，但当前仓库没有可验证依据。

Blocked output（阻塞输出）必须记录：

- blocker（阻塞原因）。
- failed evidence（失败证据）。
- recommended next action（建议下一动作）。
- recovery path（恢复路径）。
- 不得把 gate（门禁）标为 completed。

Blocked recovery path（阻塞恢复路径）必须包含：

1. 修复失败测试、证据矛盾、README 示例问题或索引治理问题。
2. 重新运行 P1 Exit Gate（P1 退出门禁）验证，包括真实 full test suite（全量测试）、permission negative gate（权限负向门禁）和 minimal example（最小示例）命令。
3. 如果再次 blocked（阻塞），将问题记录为 project blocker（项目阻塞），并升级给人工决策；不得静默降低验收标准。

## Acceptance Criteria

本规格完成时必须证明：

- P1 Exit Gate（P1 退出门禁）有明确 trigger（触发条件）、输入、输出和 blocked semantics（阻塞语义）。
- review（复审）不会直接实现 P2 功能。
- review（复审）不会把 P1 Exit Gate 编号为普通 P1 task。
- M1/M2/M3/M4/M5 milestone criteria（里程碑标准）有逐项判定规则。
- P2 work package（P2 工作包）滚动更新规则明确，并避免保留已被证据满足的 pending task。
- real provider integration tests（真实模型供应商集成测试）是否进入 P2 有明确判断，并区分 base CI（基础持续集成）与 manual/nightly gate（手动 / 夜间门禁）。
- external coding agent bridge（外部编码智能体桥接）不得早于 evidence mapping（证据映射）硬化。
- 文档更新路径遵守 `AGENTS.md` 和 `docs/INDEX.md` 的索引规则。
- 没有 silent fallback（静默降级）、mock success path（模拟成功路径）或第二套事实源。

## Documentation Impact

创建本规格时需要更新：

- `docs/04-implementation-spec/INDEX.md`：加入本 draft spec（草案规格）。

执行本规格并完成 P1 Exit Gate 后，需要更新：

- `docs/07-project-log/2026-06-07-P1-exit-review.md`。
- `docs/07-project-log/INDEX.md`。
- `docs/04-implementation-backlog/backlog.md`。
- `docs/04-implementation-spec/P1-exit-gate-roadmap-review-spec.md`：状态改为 `implemented`。
- `docs/04-implementation-plan/P1-exit-gate-roadmap-review-plan.md`：状态改为 `implemented`。
- `docs/04-implementation-spec/INDEX.md` 和 `docs/04-implementation-plan/INDEX.md`：将本规格 / 计划从 active（当前活跃）移动到 completed / archived（已完成 / 已归档）。
- `docs/INDEX.md`：仅当全局 active pointer（当前指针）或 reading path（阅读路径）变化时更新。

## Self-Review Result

- Spec coverage（规格覆盖）：已覆盖 backlog 中 P1 Exit Gate 的 trigger、required outputs、roadmap review protocol（路线图复审协议）、P2 work package（P2 工作包）滚动更新要求、real provider integration（真实模型供应商集成）判断、blocked 恢复路径和文档治理要求。
- Placeholder scan（占位符扫描）：未使用空白占位、未定义任务或模糊成功条件。
- Internal consistency（内部一致性）：P1 Exit Gate 明确不是普通 backlog task（待办任务）；P2 work package 只在 review 完成后更新。
- Scope check（范围检查）：未包含 event/evidence 实现、真实 provider 调用、外部 coding agent bridge 或任何 P2 功能实现。
- No-fallback check（无兜底检查）：测试失败、证据矛盾、README 示例不可运行或 ADR 级变化都会 blocked，不会伪造 completed gate。
