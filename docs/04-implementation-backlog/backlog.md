# Implementation Backlog

## Status

active

## Purpose

本文维护 `atomic-agent`（原子智能体）当前实现待办。P0/P1 任务必须能追溯到 spec（规格）、contract（契约）、acceptance（验收）或 ADR（架构决策记录）。

## P0: MVP Runtime Foundation

| ID | Task | 状态 | 依据 |
|---|---|---|---|
| P0-001 | 定义核心数据模型：AgentInvocation、AgentRunResult、AgentAction、AgentEvent | completed | `docs/03-contracts/` |
| P0-002 | 实现 JSON action parser（JSON 动作解析器）和严格 schema validation（模式校验） | pending | `agent-action-protocol.md` |
| P0-003 | 实现 workspace path guard（工作区路径守卫） | pending | `permission-and-sandbox-architecture.md` |
| P0-004 | 实现 filesystem tools（文件系统工具）：list/read/search/write/patch | pending | `mvp-runtime-spec.md` |
| P0-005 | 实现 command policy（命令策略）和 run_command | pending | `mvp-runtime-spec.md` |
| P0-006 | 实现 event recorder（事件记录器）和 JSONL 输出 | pending | `event-stream-protocol.md` |
| P0-007 | 实现最小 AgentLoop（智能体循环） | pending | `runtime-architecture.md` |
| P0-008 | 实现 fail-closed budget limits（失败关闭预算限制） | pending | `mvp-acceptance.md` |

## P1: Integration and Network

| ID | Task | 状态 | 依据 |
|---|---|---|---|
| P1-001 | 实现 web_fetch 和 NetworkPolicy（网络策略） | pending | `mvp-runtime-spec.md` |
| P1-002 | 实现 Boardroom AgentRuntimePort adapter（Boardroom 智能体运行时端口适配器） | pending | `agent-runtime-port.md` |
| P1-003 | 实现 fake provider loop tests（假模型供应商循环测试） | pending | `testing-strategy.md` |
| P1-004 | 实现 permission negative tests（权限负向测试） | pending | `testing-strategy.md` |

## P2: Later Extensions

| ID | Task | 状态 | 依据 |
|---|---|---|---|
| P2-001 | native tool calling adapter（原生工具调用适配器） | deferred | ADR-0002 |
| P2-002 | service runner / http probe（服务运行与 HTTP 探测） | deferred | roadmap |
| P2-003 | external coding agent bridge（外部编码智能体桥接） | deferred | roadmap |

## Blocked Items

当前没有 blocked（阻塞）任务。

## Update Rules

- 新增 P0/P1 任务必须链接依据文档。
- 完成任务后更新状态，并在必要时更新 acceptance（验收）或 testing（测试）文档。
- 如果任务产生长期架构影响，先写 ADR。
