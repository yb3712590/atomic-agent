# ADR-0001: Use Standalone atomic-agent Runtime

## Status

Accepted

## Context

Boardroom OS（Boardroom 操作系统）已经拥有 governance（治理）、contract（契约）、evidence（证据）、reducer（归约器）和 closeout gate（收尾门禁）地基，但缺少真正执行工作的 agent loop（智能体循环）。一种方案是在 Boardroom OS 内部直接实现所有 runtime 能力；另一种方案是把通用执行循环抽象为独立 `atomic-agent`（原子智能体）项目。

## Decision

采用独立 `atomic-agent runtime`（原子智能体运行时）项目。Boardroom OS 通过 `AgentRuntimePort`（智能体运行时端口）调用它。

## Consequences

正面影响：

- Boardroom OS 保持治理事实源，不被通用工具循环污染。
- atomic-agent 可以独立演进 provider（模型供应商）、tool（工具）、sandbox（沙箱）和 event stream（事件流）。
- 其它项目也可以复用同一个小型 runtime。

代价：

- 需要定义清晰的调用契约。
- 需要维护独立仓库、文档和版本兼容性。
- 需要避免 Boardroom 与 atomic-agent 出现第二套事实源。

## Alternatives Considered

1. 在 Boardroom OS 内直接实现全部 AgentWorkExecutor（智能体工作执行器）。
   - 优点：集成快。
   - 缺点：通用执行能力会和治理模型耦合。
2. 直接嵌入 Codex、Claude Code 或 GenericAgent。
   - 优点：短期能获得工具能力。
   - 缺点：权限、事件和证据语义不受 Boardroom 控制。

## Links

- `docs/00-overview/boardroom-os-integration-summary.md`
- `docs/03-contracts/agent-runtime-port.md`
