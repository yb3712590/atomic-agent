# Implementation Spec Index

## 1. Directory Purpose

维护可实现功能规格，说明功能输入、输出、错误行为、权限边界和非目标。

## 2. When to Update

功能范围明确、规格变化或实现依据变化时更新。

## 3. Current Active Documents

| 文档 | 状态 | 用途 | 何时读取 |
|---|---|---|---|
| `INDEX.md` | active | 本目录索引和文档治理规则 | 进入本目录前 |
| `mvp-runtime-spec.md` | active | 定义 MVP runtime 的工具、策略、事件、provider、配置来源和输出要求 | 实现或调整 MVP 范围前 |

## 4. Completed / Archived Documents

| 文档 | 完成时间 | 保留原因 |
|---|---|---|
| `P0-002-json-action-parser-spec.md` | 2026-06-04 | 已实现 P0-002 JSON action parser，保留为实现规格记录 |
| `P0-003-workspace-path-guard-spec.md` | 2026-06-04 | 已实现 P0-003 workspace path guard，保留为路径权限规格记录 |

## 5. Update Rules

- spec（规格）说明“做什么”，不要写成逐步任务计划。
- 功能规格变化必须同步检查 acceptance（验收）和 backlog（待办）。
- 长期范围变化必须写 ADR。
- 未被本索引列出的 spec 文档不是权威规格。

## 6. AI Reading Guidance

spec（规格）说明“做什么”，不要写成逐步任务计划。
