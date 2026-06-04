# Testing Index

## 1. Directory Purpose

维护测试策略、fixture（测试夹具）、golden path（黄金路径）、negative tests（负向测试）和测试命令。

## 2. When to Update

新增测试层级、修改测试命令、发现 flaky test（不稳定测试）或调整验证策略时更新。

## 3. Current Active Documents

| 文档 | 状态 | 用途 | 何时读取 |
|---|---|---|---|
| `INDEX.md` | active | 本目录索引和文档治理规则 | 进入本目录前 |
| `testing-strategy.md` | active | 定义单元、工具、契约、权限负向、fake provider 和 real provider 测试策略 | 增加测试、修改测试门禁或实现 MVP 验收前 |

## 4. Completed / Archived Documents

| 文档 | 完成时间 | 保留原因 |
|---|---|---|
| _None_ | - | 当前没有已完成或归档文档 |

## 5. Update Rules

- 测试文档必须区分 fake provider（假模型供应商）语义测试和 real provider（真实模型供应商）集成测试。
- 修改测试门禁必须同步检查 acceptance（验收）。
- 新增长期测试策略变化应写 ADR 或 architecture 文档。
- 未被本索引列出的 testing 文档不是权威测试策略。

## 6. AI Reading Guidance

测试文档必须区分 fake provider 语义测试和 real provider 集成测试。
