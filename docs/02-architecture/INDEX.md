# Architecture Index

## 1. Directory Purpose

维护 runtime（运行时）、tool registry（工具注册表）、provider adapter（模型供应商适配器）、permission policy（权限策略）和 event stream（事件流）架构。

## 2. When to Update

模块职责、边界、依赖方向或长期结构变化时更新。

## 3. Current Active Documents

| 文档 | 状态 | 用途 | 何时读取 |
|---|---|---|---|
| `INDEX.md` | active | 本目录索引和文档治理规则 | 进入本目录前 |
| `runtime-architecture.md` | active | 定义 runtime 组件、主循环、状态所有权和失败语义 | 设计 agent loop 或 runtime 模块前 |
| `permission-and-sandbox-architecture.md` | active | 定义 fail-closed 权限模型、文件/命令/网络策略和沙箱边界 | 修改工具权限或 sandbox 行为前 |
| `event-and-evidence-architecture.md` | active | 定义事件流、证据对象和 Boardroom evidence 映射 | 修改事件、证据或重放语义前 |

## 4. Completed / Archived Documents

| 文档 | 完成时间 | 保留原因 |
|---|---|---|
| _None_ | - | 当前没有已完成或归档文档 |

## 5. Update Rules

- 架构文档只描述结构和边界，不承载 backlog（待办）或验收清单。
- 长期架构取舍必须先写 ADR，再更新相关架构文档。
- 修改架构边界时必须同步检查 contracts（契约）和 acceptance（验收）。
- 未被本索引列出的 architecture 文档不是权威架构。

## 6. AI Reading Guidance

架构文档只描述结构和边界，不承载 backlog（待办）或验收清单。
