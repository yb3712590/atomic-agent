# Implementation Backlog Index

## 1. Directory Purpose

维护待办、阻塞项、优先级和实现任务入口。

## 2. When to Update

新增任务、任务完成、任务阻塞、任务取消或优先级变化时更新。

## 3. Current Active Documents

| 文档 | 状态 | 用途 | 何时读取 |
|---|---|---|---|
| `INDEX.md` | active | 本目录索引和文档治理规则 | 进入本目录前 |

## 4. Completed / Archived Documents

| 文档 | 完成时间 | 保留原因 |
|---|---|---|
| _None_ | - | 当前没有已完成或归档文档 |

## 5. Update Rules

- 新增本目录文档时，必须把文档加入 `Current Active Documents`、`Completed / Archived Documents` 或明确的 superseded（已替代）/ abandoned（已放弃）记录。
- 修改本目录内任何权威文档时，必须同步更新本 `INDEX.md`。
- 如果变更影响全局阅读路径、当前活跃指针或权威文档集合，必须同步更新 `docs/INDEX.md`。
- 未被本索引列出的文档不是本目录 authoritative document（权威文档）。

## 6. AI Reading Guidance

P0/P1 backlog（待办）必须链接对应 spec（规格）、ADR（架构决策记录）或 acceptance（验收）。
