# Atomic Agent Docs Index

`docs/INDEX.md`（文档总索引）是 `atomic-agent`（原子智能体）仓库的文档入口和全局导航事实源。新会话必须先读取根目录 `AGENTS.md`（智能体协作规则），再读取本文件，并按任务需要读取相关子目录 `INDEX.md`（目录索引）。

## 1. 文档使用原则

- 本仓库只使用 `docs/`（文档目录），不使用 `doc/`。
- 每个文档目录必须有 `INDEX.md`。
- 当前权威文档必须被 `docs/INDEX.md` 或对应子目录 `INDEX.md` 列出。
- 没有被索引列出的文档不是 authoritative document（权威文档）。
- 长期决策和重要架构决策必须先进入 `09-adr/`（架构决策记录）。
- reference（参考资料）不能直接作为实现依据；被采纳内容必须进入 ADR、architecture（架构）、contract（契约）或 acceptance（验收）。

## 2. 推荐阅读路径

| 场景 | 阅读顺序 |
|---|---|
| 理解项目定位 | `AGENTS.md` -> `docs/INDEX.md` -> `docs/00-overview/INDEX.md` -> `docs/00-overview/project-brief.md` |
| 理解 Boardroom 关系 | `docs/INDEX.md` -> `docs/00-overview/boardroom-os-integration-summary.md` -> `docs/09-adr/0004-keep-boardroom-os-as-governance-source.md` |
| 理解核心概念 | `docs/INDEX.md` -> `docs/01-concepts/INDEX.md` -> `docs/01-concepts/glossary.md` |
| 设计运行时架构 | `docs/INDEX.md` -> `docs/02-architecture/INDEX.md` -> `docs/02-architecture/runtime-architecture.md` |
| 设计权限与沙箱 | `docs/INDEX.md` -> `docs/02-architecture/permission-and-sandbox-architecture.md` -> `docs/09-adr/0003-use-fail-closed-permission-model.md` |
| 设计事件与证据 | `docs/INDEX.md` -> `docs/02-architecture/event-and-evidence-architecture.md` -> `docs/03-contracts/event-stream-protocol.md` |
| 设计 Boardroom 接口 | `docs/INDEX.md` -> `docs/03-contracts/INDEX.md` -> `docs/03-contracts/agent-runtime-port.md` |
| 设计动作协议 | `docs/INDEX.md` -> `docs/03-contracts/agent-action-protocol.md` -> `docs/09-adr/0002-use-provider-agnostic-action-protocol.md` |
| 执行实现任务 | `docs/INDEX.md` -> `docs/04-implementation-backlog/backlog.md` -> `docs/04-implementation-spec/mvp-runtime-spec.md` |
| 结束 P 阶段并规划下一波次 | `docs/INDEX.md` -> `docs/04-implementation-backlog/backlog.md` -> `docs/06-roadmap/roadmap.md` -> `docs/04-implementation-backlog/backlog.md` |
| 判断是否完成 | `docs/INDEX.md` -> `docs/04-implementation-acceptance/mvp-acceptance.md` -> `docs/05-testing/testing-strategy.md` |
| 查路线图 | `docs/INDEX.md` -> `docs/06-roadmap/roadmap.md` |
| 查外部参考 | `docs/INDEX.md` -> `docs/08-reference/genericagent-and-codex-reference.md` |
| 做长期决策 | `docs/INDEX.md` -> `docs/09-adr/INDEX.md` |

## 3. 当前活跃文档指针

| 优先级 | 文档 | 状态 | 何时读取 |
|---|---|---|---|
| P0 | `docs/00-overview/project-brief.md` | active | 理解 atomic-agent（原子智能体）定位、目标和非目标时 |
| P0 | `docs/00-overview/boardroom-os-integration-summary.md` | active | 处理 Boardroom OS（Boardroom 操作系统）集成边界时 |
| P0 | `docs/01-concepts/glossary.md` | active | 使用或新增核心术语前 |
| P0 | `docs/02-architecture/runtime-architecture.md` | active | 设计 runtime（运行时）和 agent loop（智能体循环）前 |
| P0 | `docs/02-architecture/permission-and-sandbox-architecture.md` | active | 设计文件、命令、网络权限前 |
| P0 | `docs/02-architecture/event-and-evidence-architecture.md` | active | 设计 event stream（事件流）或 evidence（证据）映射前 |
| P0 | `docs/03-contracts/agent-runtime-port.md` | active | 设计上层系统调用 atomic-agent 的端口前 |
| P0 | `docs/03-contracts/agent-action-protocol.md` | active | 修改动作协议或工具集合前 |
| P0 | `docs/03-contracts/event-stream-protocol.md` | active | 修改事件协议前 |
| P0 | `docs/04-implementation-spec/mvp-runtime-spec.md` | active | 定义 MVP runtime（最小可行运行时）实现范围时 |
| P2 | `docs/04-implementation-spec/P2-006-complex-real-provider-atomic-task-gate-spec.md` | draft | 细化或实施 P2-006 complex real provider atomic task gate（复杂真实供应商原子任务门禁）前 |
| P0 | `docs/04-implementation-backlog/backlog.md` | active | 领取或调整实现任务前 |
| P0 | `docs/04-implementation-acceptance/mvp-acceptance.md` | active | 判断 MVP 是否完成前 |
| P1 | `docs/05-testing/testing-strategy.md` | active | 增加或修改测试策略前 |
| P1 | `docs/06-roadmap/roadmap.md` | active | 调整阶段路线前 |
| P1 | `docs/09-adr/INDEX.md` | active | 做长期架构决策前 |
| P1 | `docs/09-adr/0001-use-standalone-atomic-agent-runtime.md` | accepted | 讨论项目边界或仓库独立性时 |
| P1 | `docs/09-adr/0002-use-provider-agnostic-action-protocol.md` | accepted | 讨论 tool calling（工具调用）或动作协议时 |
| P1 | `docs/09-adr/0003-use-fail-closed-permission-model.md` | accepted | 讨论权限、安全或 sandbox（沙箱）时 |
| P1 | `docs/09-adr/0004-keep-boardroom-os-as-governance-source.md` | accepted | 讨论 Boardroom OS 治理事实源边界时 |
| P2 | `docs/08-reference/genericagent-and-codex-reference.md` | active | 查 GenericAgent（通用智能体）或 Codex（编码智能体）参考结论时 |

## 4. 目录规范

| 目录 | 用途 | 何时更新 |
|---|---|---|
| `00-overview/` | 项目总览、范围、非目标 | 项目定位或 Boardroom 边界变化时 |
| `01-concepts/` | 核心概念、术语表、语义边界 | 新增或修改核心概念时 |
| `02-architecture/` | runtime、tool registry、provider adapter、permission、event 架构 | 模块边界变化时 |
| `03-contracts/` | AgentRuntimePort、AgentInvocation、AgentRunResult、AgentAction、AgentEvent 等契约 | 接口协议变化时 |
| `04-implementation-spec/` | 可实现功能规格 | 功能输入、输出、错误行为或范围明确时 |
| `04-implementation-plan/` | 逐步实施计划 | 准备执行具体功能时 |
| `04-implementation-backlog/` | 待办、阻塞项、优先级 | 任务状态或优先级变化时 |
| `04-implementation-acceptance/` | 验收标准、完成定义、门禁 | 完成标准或安全要求变化时 |
| `05-testing/` | 测试策略、fixture、golden path、negative tests | 测试层级或命令变化时 |
| `06-roadmap/` | 里程碑和版本路线 | 阶段目标变化时 |
| `07-project-log/` | 项目日志、复盘、调研摘要 | 阶段完成或关键偏差发生时 |
| `08-reference/` | 外部参考和调研材料 | 新增外部依据或资料过期时 |
| `09-adr/` | 长期架构决策记录 | 重要决策产生、替代或废弃时 |

## 5. 文档状态

| 状态 | 含义 |
|---|---|
| draft | 草案，不能作为唯一实现依据 |
| active | 当前有效，新会话可优先读取 |
| accepted | 已接受的长期决策，主要用于 ADR |
| implemented | 已实现，保留为历史依据 |
| superseded | 已被替代，必须指向替代文档 |
| archived | 已归档，仅按需读取 |
| abandoned | 已放弃，必须说明原因 |

## 6. 已完成文档退出当前指针规则

文档满足以下任一条件时，应从 active pointer（当前指针）退出：

1. 对应功能已实现并通过 acceptance（验收）。
2. 对应计划已完成。
3. 对应设计被 ADR（架构决策记录）替代。
4. 对应调研只剩历史价值。
5. 内容已合并进更权威的 architecture（架构）、contract（契约）或 acceptance（验收）文档。
6. 当前阶段没有 P0/P1 任务引用它。

退出时必须：

- 从 `Current Active Documents` 移除。
- 加入对应子目录 `INDEX.md` 的 completed、archived、superseded 或 abandoned 区。
- 如影响全局阅读路径，同步更新本文件。

## 7. AI 新会话读取策略

AI 新会话应遵循：

1. 先读根目录 `AGENTS.md`。
2. 再读本文件。
3. 按任务读取相关子目录 `INDEX.md`。
4. 只读取索引明确列出的 authoritative documents（权威文档）。
5. 不主动扫描全部 docs，也不把未索引文档当作当前事实源。
