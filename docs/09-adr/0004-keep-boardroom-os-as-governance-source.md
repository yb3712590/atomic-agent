# ADR-0004: Keep Boardroom OS as Governance Source

## Status

Accepted

## Context

Boardroom OS（Boardroom 操作系统）的核心价值是 governance（治理）、evidence（证据）、contract（契约）、reducer（归约器）和 closeout gate（收尾门禁）。atomic-agent（原子智能体）会产生大量执行事实，但不能替代治理决策。

## Decision

Boardroom OS 保持治理事实源。atomic-agent 只返回 `AgentRunResult`（智能体运行结果）、event stream（事件流）、tool attempts（工具调用尝试记录）、workspace mutations（工作区变更）和 artifacts（产物）。它不发出 ticket completed（工单完成）或 closeout committed（收尾提交）事件。

## Consequences

正面影响：

- 避免两套治理状态机。
- Boardroom closeout gate 仍然是完成判定入口。
- atomic-agent 可以被替换，而不改变治理模型。

代价：

- 需要明确映射 atomic-agent 事件到 Boardroom evidence。
- runtime 成功不等于业务完成，需要上层 gate 验证。

## Alternatives Considered

1. atomic-agent 直接声明任务完成。
   - 拒绝原因：会绕过 Boardroom governance。
2. 外部 coding agent 结果直接作为完成结果。
   - 拒绝原因：缺少 Boardroom evidence lineage（证据谱系）。

## Links

- `docs/00-overview/boardroom-os-integration-summary.md`
- `docs/02-architecture/event-and-evidence-architecture.md`
- `docs/03-contracts/agent-runtime-port.md`
