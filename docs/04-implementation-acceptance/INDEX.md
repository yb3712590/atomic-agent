# Implementation Acceptance Index

## 1. Directory Purpose

维护验收标准、完成定义、安全门禁和 Boardroom 集成完成条件。

## 2. When to Update

完成标准、安全要求、测试门禁或 Boardroom 对接要求变化时更新。

## 3. Current Active Documents

| 文档 | 状态 | 用途 | 何时读取 |
|---|---|---|---|
| `INDEX.md` | active | 本目录索引和文档治理规则 | 进入本目录前 |
| `mvp-acceptance.md` | active | 定义 MVP 功能、安全、事件、Boardroom 集成和文档验收 | 判断 MVP 或相关实现是否完成前 |

## 4. Completed / Archived Documents

| 文档 | 完成时间 | 保留原因 |
|---|---|---|
| _None_ | - | 当前没有已完成或归档文档 |

## 5. Update Rules

- acceptance（验收）必须真实可验证；不得用 mock success path（模拟成功路径）代替。
- 修改验收标准必须同步检查 testing（测试）和 backlog（待办）。
- 安全门禁变化通常需要 ADR。
- 未被本索引列出的 acceptance 文档不是权威验收标准。

## 6. AI Reading Guidance

acceptance 必须真实可验证；不得用 mock success path 代替。
