# Contracts Index

## 1. Directory Purpose

维护对接契约和协议，例如 `AgentRuntimePort`（智能体运行时端口）、`AgentInvocation`（智能体调用请求）、`AgentRunResult`（智能体运行结果）、`AgentAction`（智能体动作）和 `AgentEvent`（智能体事件）。

## 2. When to Update

Boardroom OS 对接字段、事件格式、权限契约或工具能力契约变化时更新。

## 3. Current Active Documents

| 文档 | 状态 | 用途 | 何时读取 |
|---|---|---|---|
| `INDEX.md` | active | 本目录索引和文档治理规则 | 进入本目录前 |
| `agent-runtime-port.md` | active | 定义 AgentRuntimePort、AgentInvocation 和 AgentRunResult | 设计上层调用边界或 Boardroom 对接前 |
| `agent-action-protocol.md` | active | 定义 provider-agnostic AgentAction JSON 协议 | 修改工具动作集合或 provider 输出协议前 |
| `event-stream-protocol.md` | active | 定义 AgentEvent JSONL 事件协议 | 修改事件类型、顺序、载荷或哈希规则前 |

## 4. Completed / Archived Documents

| 文档 | 完成时间 | 保留原因 |
|---|---|---|
| _None_ | - | 当前没有已完成或归档文档 |

## 5. Update Rules

- 契约文档是实现和集成的关键依据；未索引契约不是权威协议。
- 破坏性契约变更必须写 ADR。
- 修改契约时必须同步检查 architecture、acceptance 和 testing 文档。
- 不能在契约中引入 silent fallback（静默降级）或第二事实源。

## 6. AI Reading Guidance

契约文档是实现和集成的关键依据；未索引契约不是权威协议。
