# Concepts Index

## 1. Directory Purpose

维护核心概念、术语表和语义边界，例如 `AgentLoop`（智能体循环）、`AgentAction`（智能体动作）、`ToolAttempt`（工具调用尝试记录）和 `WorkspaceMutation`（工作区变更）。

## 2. When to Update

新增核心概念、改名概念或调整语义边界时更新。

## 3. Current Active Documents

| 文档 | 状态 | 用途 | 何时读取 |
|---|---|---|---|
| `INDEX.md` | active | 本目录索引和文档治理规则 | 进入本目录前 |
| `glossary.md` | active | 定义核心术语与命名规则 | 新增术语或撰写契约/架构文档前 |

## 4. Completed / Archived Documents

| 文档 | 完成时间 | 保留原因 |
|---|---|---|
| _None_ | - | 当前没有已完成或归档文档 |

## 5. Update Rules

- 新增术语必须优先更新 `glossary.md`。
- 如果术语影响接口或长期架构，必须同步更新 contracts（契约）或 ADR（架构决策记录）。
- 未被本索引列出的 concepts（概念）文档不是权威定义。

## 6. AI Reading Guidance

实现或评审前若涉及新术语，先在这里确认是否已有定义。
