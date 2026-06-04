# Testing Index

## 1. Directory Purpose

维护测试策略、fixture（测试夹具）、golden path（黄金路径）、negative tests（负向测试）和测试命令。

## 2. When to Update

新增测试层级、修改测试命令、发现 flaky test（不稳定测试）或调整验证策略时更新。

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

测试文档必须区分 fake provider（假模型供应商）语义测试和 real provider（真实模型供应商）集成测试。
