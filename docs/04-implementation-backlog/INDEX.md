# Implementation Backlog Index

## 1. Directory Purpose

维护待办、阻塞项、优先级和实现任务入口。

## 2. When to Update

新增任务、任务完成、任务阻塞、任务取消或优先级变化时更新。

## 3. Current Active Documents

| 文档 | 状态 | 用途 | 何时读取 |
|---|---|---|---|
| `INDEX.md` | active | 本目录索引和文档治理规则 | 进入本目录前 |
| `backlog.md` | active | 维护 P0/P1/P2 实现任务、依赖和阻塞项 | 领取、调整或完成实现任务前 |

## 4. Completed / Archived Documents

| 文档 | 完成时间 | 保留原因 |
|---|---|---|
| _None_ | - | 当前没有已完成或归档文档 |

## 5. Update Rules

- P0/P1 backlog（待办）必须链接对应 spec（规格）、ADR（架构决策记录）或 acceptance（验收）。
- P0/P1/P2 表示 execution wave（执行波次），不是 roadmap milestone（路线图里程碑）。
- 完成一个 P wave 后，必须先执行 roadmap review（路线图复审），再编制或重组下一个 P wave。
- roadmap review 不作为普通 backlog task（待办任务）编号；应记录为 P-stage exit gate（P 阶段退出门禁）。
- 完成任务后更新 `backlog.md`，必要时同步更新 `docs/INDEX.md`。
- 阻塞任务必须写清 blocker（阻塞原因）。
- 未被本索引列出的 backlog 文档不是权威任务入口。

## 6. AI Reading Guidance

P0/P1 backlog 必须链接对应 spec、ADR 或 acceptance。
