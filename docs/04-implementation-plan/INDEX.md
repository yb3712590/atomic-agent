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
| `P0-001-configuration-source-semantics-plan.md` | 2026-06-04 | 已实施配置来源语义和 P0-001 核心模型，保留为实施记录 |
| `P0-002-json-action-parser-plan.md` | 2026-06-04 | 已实施 P0-002 JSON action parser，保留为 TDD 实施记录 |
| `P0-003-workspace-path-guard-plan.md` | 2026-06-04 | 已实施 P0-003 workspace path guard，保留为 TDD 实施记录 |
| `P0-004-filesystem-tools-plan.md` | 2026-06-05 | 已实施 P0-004 filesystem tools（文件系统工具），保留为 TDD 实施记录 |
| `P0-005-command-policy-run-command-plan.md` | 2026-06-05 | 已实施 P0-005 command policy（命令策略）和 run_command（运行声明命令），保留为 TDD 实施记录 |
| `P0-006-event-recorder-jsonl-plan.md` | 2026-06-05 | 已实施 P0-006 event recorder（事件记录器）和 JSONL event stream（JSONL 事件流），保留为 TDD 实施记录 |
| `P0-007-minimal-agent-loop-plan.md` | 2026-06-05 | 已实施 P0-007 minimal AgentLoop（最小智能体循环），保留为 TDD 实施记录 |
| `P0-008-fail-closed-budget-limits-plan.md` | 2026-06-05 | 已实施 P0-008 fail-closed budget limits（失败关闭预算限制），保留为 TDD 实施记录 |

## 5. Update Rules

- 新增本目录文档时，必须把文档加入 `Current Active Documents`、`Completed / Archived Documents` 或明确的 superseded（已替代）/ abandoned（已放弃）记录。
- 修改本目录内任何权威文档时，必须同步更新本 `INDEX.md`。
- 如果变更影响全局阅读路径、当前活跃指针或权威文档集合，必须同步更新 `docs/INDEX.md`。
- 未被本索引列出的文档不是本目录 authoritative document（权威文档）。

## 6. AI Reading Guidance

plan（计划）说明“怎么做”；完成后必须退出 active pointer（当前指针）。
