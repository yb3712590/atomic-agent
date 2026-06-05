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

Trigger（触发条件）：

- P0 表中所有非 deferred（延后）任务均为 completed。
- P0 相关 tests（测试）、acceptance（验收）和 docs（文档）已验证。

Required outputs（必需产物）：

1. 对照 `docs/06-roadmap/roadmap.md` 的 milestone exit criteria（里程碑退出标准），判断 M1/M2 哪些条目已满足、部分满足或失效。
2. 记录当前 P0 完成项是否改变下一阶段优先级。
3. 编制或重组 P1 execution wave（执行波次）。
4. 如长期路线、项目边界或架构原则变化，先新增或更新 ADR。
5. 必要时写入 `docs/07-project-log/`（项目日志）。

## P1: Integration and Network

| ID | Task | 状态 | 依据 |
|---|---|---|---|
| P1-001 | 实现 web_fetch 和 NetworkPolicy（网络策略） | pending | `mvp-runtime-spec.md` |
| P1-002 | 实现 Boardroom AgentRuntimePort adapter（Boardroom 智能体运行时端口适配器） | pending | `agent-runtime-port.md` |
| P1-003 | 实现 fake provider loop tests（假模型供应商循环测试） | pending | `testing-strategy.md` |
| P1-004 | 实现 permission negative tests（权限负向测试） | pending | `testing-strategy.md` |

### P1 Exit Gate: Roadmap Review

Trigger（触发条件）：

- P1 表中所有非 deferred（延后）任务均为 completed。
- P1 相关 integration（集成）、negative tests（负向测试）和 docs（文档）已验证。

Required outputs（必需产物）：

1. 对照 `docs/06-roadmap/roadmap.md`，判断 M1/M2/M3 哪些条目已满足、部分满足或失效。
2. 明确 real provider integration tests（真实模型供应商集成测试）是否需要进入下一 P wave。
3. 编制或重组 P2 execution wave（执行波次）。
4. 如 Boardroom OS（Boardroom 操作系统）对接边界或 evidence（证据）模型变化，先新增或更新 ADR。
5. 必要时写入 `docs/07-project-log/`。

## P2: Later Extensions

| ID | Task | 状态 | 依据 |
|---|---|---|---|
| P2-001 | native tool calling adapter（原生工具调用适配器） | deferred | ADR-0002 |
| P2-002 | service runner / http probe（服务运行与 HTTP 探测） | deferred | roadmap |
| P2-003 | external coding agent bridge（外部编码智能体桥接） | deferred | roadmap |

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
