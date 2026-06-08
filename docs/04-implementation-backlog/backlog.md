# Implementation Backlog

## Status

active

## Purpose

本文维护 `atomic-agent`（原子智能体）当前实现待办。P0/P1 任务必须能追溯到 spec（规格）、contract（契约）、acceptance（验收）或 ADR（架构决策记录）。

## Planning Semantics

`P0/P1/P2` 表示 rolling execution waves（滚动执行波次），不是 roadmap milestone（路线图里程碑），也不是项目终点编号。

每个 P wave（执行波次）只承诺当前和近端可执行任务。远期能力保持在 `docs/06-roadmap/roadmap.md`（路线图）中，不在 backlog（待办）里提前细拆。

P wave 完成后，必须先完成 roadmap review（路线图复审），再编制或重组下一个 P wave。roadmap review 是 P-stage exit gate（P 阶段退出门禁），不是普通 backlog task（待办任务），不得编号为 `P0-009`、`P1-999` 等常规实现项。

## P0: MVP Runtime Foundation

| ID | Task | 状态 | 依据 |
|---|---|---|---|
| P0-001 | 定义核心数据模型：AgentInvocation、AgentRunResult、AgentAction、AgentEvent | completed | `docs/03-contracts/` |
| P0-002 | 实现 JSON action parser（JSON 动作解析器）和严格 schema validation（模式校验） | completed | `agent-action-protocol.md` |
| P0-003 | 实现 workspace path guard（工作区路径守卫） | completed | `P0-003-workspace-path-guard-spec.md`, `permission-and-sandbox-architecture.md` |
| P0-004 | 实现 filesystem tools（文件系统工具）：list/read/search/write/patch | completed | `P0-004-filesystem-tools-spec.md`, `mvp-runtime-spec.md` |
| P0-005 | 实现 command policy（命令策略）和 run_command | completed | `P0-005-command-policy-run-command-spec.md`, `mvp-runtime-spec.md` |
| P0-006 | 实现 event recorder（事件记录器）和 JSONL 输出 | completed | `P0-006-event-recorder-jsonl-spec.md`, `event-stream-protocol.md` |
| P0-007 | 实现最小 AgentLoop（智能体循环） | completed | `P0-007-minimal-agent-loop-spec.md`, `runtime-architecture.md` |
| P0-008 | 实现 fail-closed budget limits（失败关闭预算限制） | completed | `P0-008-fail-closed-budget-limits-spec.md`, `mvp-acceptance.md` |

### P0 Exit Gate: Roadmap Review

Status（状态）：completed

Review record（复审记录）：`docs/07-project-log/2026-06-05-P0-exit-review.md`

Conclusion（结论）：

- M1 exit criteria（M1 退出标准）已满足。
- M2 已部分满足：`run_command`（运行声明命令）、预算和无效动作 fail closed（失败关闭）已完成；`web_fetch`（网络获取）、NetworkPolicy（网络策略）和完整 permission negative tests（权限负向测试）仍需进入 P1。
- M3 尚未开始：Boardroom `AgentRuntimePort adapter`（智能体运行时端口适配器）仍需进入 P1 后段。
- README minimal example（最小示例）仍需在真实 CLI command（命令行命令）可运行、产生 JSONL event stream（JSONL 事件流）且演示成功 fake provider loop（假模型供应商循环）后更新；不得用伪命令或 mock success path（模拟成功路径）替代。

## P1: Integration and Network

| ID | Task | 状态 | 依据 |
|---|---|---|---|
| P1-001 | 实现 `web_fetch` 和 NetworkPolicy（网络策略） | completed | `P1-001-web-fetch-network-policy-spec.md`, `mvp-runtime-spec.md`, `agent-action-protocol.md`, `event-stream-protocol.md` |
| P1-002 | 整合现有 permission negative tests（权限负向测试）为单一门禁，并补齐网络拒绝场景 | completed | `P1-002-permission-negative-gate-spec.md`, `testing-strategy.md`, `mvp-acceptance.md`, `0003-use-fail-closed-permission-model.md` |
| P1-003 | 固化 fake provider loop acceptance（假模型供应商循环验收）并建立真实 minimal example（最小示例）文档路径 | completed | `P1-003-fake-provider-loop-minimal-example-spec.md`, `testing-strategy.md`, `mvp-acceptance.md`, `README.md` |
| P1-004 | 实现 Boardroom AgentRuntimePort adapter（Boardroom 智能体运行时端口适配器） | completed | `agent-runtime-port.md`, `boardroom-os-integration-summary.md`, `0004-keep-boardroom-os-as-governance-source.md` |

Dependency notes（依赖说明）：

- P1-002 depends on P1-001 for network deny（网络拒绝） coverage; it should inventory and consolidate existing P0 negative tests instead of rewriting already-covered scenarios.
- P1-003 depends on the existing P0 AgentLoop（智能体循环） and may expose an entrypoint/docs gap; it must not publish a README command until a real CLI command runs successfully, produces JSONL event stream（JSONL 事件流）, and demonstrates at least one successful fake provider loop（假模型供应商循环）.
- P1-004 should run after P1-001 to P1-003 stabilize runtime evidence semantics（运行时证据语义）.

### P1 Exit Gate: Roadmap Review

Status（状态）：completed

Review record（复审记录）：`docs/07-project-log/2026-06-07-P1-exit-review.md`

Conclusion（结论）：

- M1 exit criteria（M1 退出标准）已满足。
- M2 exit criteria（M2 退出标准）已满足：`run_command`（运行声明命令）、`web_fetch`（网络获取）、NetworkPolicy（网络策略）、permission negative gate（权限负向门禁）、预算和无效动作 fail closed（失败关闭）均已有验证路径。
- M3 exit criteria（M3 退出标准）已满足：Boardroom `AgentRuntimePort adapter`（智能体运行时端口适配器）已实现，并保持 atomic-agent 不声明 Boardroom governance completion（治理完成）的边界。
- M4 尚未完成：event stream / evidence mapping（事件流 / 证据映射）、artifact hash（产物哈希）和 SourceInventory（源码清单） lineage（谱系）应成为 P2 优先工作包。
- M5 尚未开始：external coding agent bridge（外部编码智能体桥接）继续 deferred（延后），直到 M4 证据导入路径稳定。

## P2: Evidence Mapping and Integration Gates

| ID | Task | 状态 | 依据 |
|---|---|---|---|
| P2-001 | 完善 event stream / evidence mapping（事件流 / 证据映射）和 artifact hash（产物哈希）硬化 | completed | `P2-001-evidence-mapping-artifact-hash-hardening-spec.md`, `event-stream-protocol.md`, `event-and-evidence-architecture.md`, `agent-runtime-port.md`, `mvp-acceptance.md`, `roadmap.md` |
| P2-002 | 建立 real provider minimal integration gate（真实模型供应商最小集成门禁） | completed | `P2-002-real-provider-minimal-integration-gate-spec.md`, `testing-strategy.md`, `agent-action-protocol.md`, `mvp-acceptance.md`, `roadmap.md` |
| P2-003 | 设计 external coding agent bridge（外部编码智能体桥接）的证据导入协议和权限边界 | deferred | `roadmap.md`, `0002-use-provider-agnostic-action-protocol.md`, `0003-use-fail-closed-permission-model.md` |
| P2-004 | 建立 real provider tool success gate（真实供应商工具成功门禁） | completed | `P2-004-real-provider-tool-success-gate-spec.md`, `testing-strategy.md`, `agent-action-protocol.md`, `mvp-acceptance.md`, `roadmap.md` |
| P2-005 | 强化 OpenAI-compatible provider options（OpenAI 兼容供应商参数）显式配置 | completed | `P2-005-openai-compatible-provider-options-hardening-spec.md`, `testing-strategy.md`, `agent-action-protocol.md`, `mvp-acceptance.md`, `roadmap.md` |
| P2-006 | 建立 complex real provider atomic task gate（复杂真实供应商原子任务门禁） | completed | `P2-006-complex-real-provider-atomic-task-gate-spec.md`, `P2-005-openai-compatible-provider-options-hardening-spec.md`, `testing-strategy.md`, `mvp-acceptance.md`, `roadmap.md` |

Dependency notes（依赖说明）：

- P2-001 is the first P2 work package because M4 evidence mapping（证据映射） must be hardened before expanding to external coding agent bridge（外部编码智能体桥接）.
- P2-002 should run after or alongside P2-001 only as a manual/nightly or integration-profile gate（集成配置门禁）; it must not destabilize base CI（基础持续集成）.
- P2-003 remains deferred; it should produce a design spec（设计规格） or ADR（架构决策记录） for evidence import protocol（证据导入协议） and permission boundary（权限边界） before any bridge implementation.
- P2-004 should run after P2-002 because it tightens real provider validation from fail-closed acceptance（失败关闭验收） to success-only tool coverage（成功型工具覆盖）; it must remain manual/nightly and must not enter base CI（基础持续集成）.
- P2-005 should run after P2-004 because the next real provider gates need explicit high-impact provider options（高影响供应商参数）, especially `reasoning_effort`（推理强度）, without hardcoded configurable options（硬编码可配置项） or silent fallback（静默降级）.
- P2-006 should run after P2-005 because the complex real provider atomic task gate（复杂真实供应商原子任务门禁） should use the explicit provider option path, including `reasoning_effort=high`, and record those options in evidence/audit（证据/审计） context.
- Earlier deferred ideas such as native tool calling adapter（原生工具调用适配器） and service runner / HTTP probe（服务运行与 HTTP 探测） are not removed from the roadmap; they are not part of the immediate P2 batch unless a later roadmap review re-prioritizes them.

### P2 Exit Gate: Roadmap Review

Trigger（触发条件）：

- P2 表中所有非 deferred（延后）任务均为 completed，或 deferred 项经 roadmap review 明确继续延期。
- P2 相关 extension（扩展）、security boundary（安全边界）和 evidence（证据）导入路径已验证。

Required outputs（必需产物）：

1. 对照 `docs/06-roadmap/roadmap.md`，判断 M4/M5 哪些条目已满足、部分满足或失效。
2. 判断 M5 是否仍是 current planned endpoint（当前规划终点）。
3. 如继续扩展，编制新的 P wave；如不继续扩展，记录项目当前完成边界。
4. 如长期路线、项目边界或架构原则变化，先新增或更新 ADR。
5. 必要时写入 `docs/07-project-log/`。

## Blocked Items

当前没有 blocked（阻塞）任务。

## Update Rules

- 新增 P0/P1 任务必须链接依据文档。
- 完成任务后更新状态，并在必要时更新 acceptance（验收）或 testing（测试）文档。
- 如果任务产生长期架构影响，先写 ADR。
