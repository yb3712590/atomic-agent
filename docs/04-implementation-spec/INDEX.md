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
| `P0-004-filesystem-tools-spec.md` | 2026-06-05 | 已实现 P0-004 filesystem tools（文件系统工具），保留为工具规格记录 |
| `P0-005-command-policy-run-command-spec.md` | 2026-06-05 | 已实现 P0-005 command policy（命令策略）和 run_command（运行声明命令），保留为命令执行规格记录 |
| `P0-006-event-recorder-jsonl-spec.md` | 2026-06-05 | 已实现 P0-006 event recorder（事件记录器）和 JSONL event stream（JSONL 事件流），保留为事件流规格记录 |
| `P0-007-minimal-agent-loop-spec.md` | 2026-06-05 | 已实现 P0-007 minimal AgentLoop（最小智能体循环），保留为循环规格记录 |
| `P0-008-fail-closed-budget-limits-spec.md` | 2026-06-05 | 已实现 P0-008 fail-closed budget limits（失败关闭预算限制），保留为预算语义规格记录 |
| `P0-exit-gate-roadmap-review-spec.md` | 2026-06-05 | 已完成 P0 Exit Gate（P0 退出门禁）路线图复审规格，保留为阶段门禁规格记录 |
| `P1-001-web-fetch-network-policy-spec.md` | 2026-06-06 | 已实现 P1-001 web_fetch（网络获取）和 NetworkPolicy（网络策略），保留为网络工具规格记录 |
| `P1-002-permission-negative-gate-spec.md` | 2026-06-06 | 已实现 P1-002 permission negative gate（权限负向门禁），保留为负向门禁规格记录 |

## 5. Update Rules

- spec（规格）说明“做什么”，不要写成逐步任务计划。
- 功能规格变化必须同步检查 acceptance（验收）和 backlog（待办）。
- 长期范围变化必须写 ADR。
- 未被本索引列出的 spec 文档不是权威规格。

## 6. AI Reading Guidance

spec（规格）说明“做什么”，不要写成逐步任务计划。
