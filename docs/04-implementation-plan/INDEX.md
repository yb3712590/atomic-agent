# Implementation Plan Index

## 1. Directory Purpose

维护逐步实施计划，供 agent（智能体）或工程师按任务执行。

## 2. When to Update

准备执行具体功能、计划完成、计划取消或计划被替代时更新。

## 3. Current Active Documents

| 文档 | 状态 | 用途 | 何时读取 |
|---|---|---|---|
| `INDEX.md` | active | 本目录索引和文档治理规则 | 进入本目录前 |

## 4. Completed / Archived Documents

| 文档 | 完成时间 | 保留原因 |
|---|---|---|
| `action-parser-plan.md` | 2026-06-04 | 已实施 P0-002 JSON action parser，保留为 TDD 实施记录 |
| `configuration-source-semantics-plan.md` | 2026-06-04 | 已实施配置来源语义和 P0-001 核心模型，保留为实施记录 |
| `workspace-path-guard-plan.md` | 2026-06-04 | 已实施 P0-003 workspace path guard，保留为 TDD 实施记录 |

## 5. Update Rules

- 新增本目录文档时，必须把文档加入 `Current Active Documents`、`Completed / Archived Documents` 或明确的 superseded（已替代）/ abandoned（已放弃）记录。
- 修改本目录内任何权威文档时，必须同步更新本 `INDEX.md`。
- 如果变更影响全局阅读路径、当前活跃指针或权威文档集合，必须同步更新 `docs/INDEX.md`。
- 未被本索引列出的文档不是本目录 authoritative document（权威文档）。

## 6. AI Reading Guidance

plan（计划）说明“怎么做”；完成后必须退出 active pointer（当前指针）。
