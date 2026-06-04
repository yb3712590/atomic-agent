# ADR-0002: Use Provider-Agnostic Action Protocol

## Status

Accepted

## Context

不同 provider（模型供应商）的 tool calling（工具调用）接口差异很大。若 runtime 一开始绑定某个 provider 的原生工具调用，会削弱可移植性，也会让 Boardroom OS 对接协议依赖特定模型产品。

## Decision

第一阶段采用 provider-agnostic JSON action protocol（模型供应商无关 JSON 动作协议）。模型输出标准 `AgentAction`（智能体动作），runtime 负责解析、校验、权限判断和工具执行。

## Consequences

正面影响：

- 支持 OpenAI-compatible、Anthropic-compatible、local model 等 provider。
- runtime 拥有 tool dispatch（工具调度）和 state handling（状态处理）。
- 事件和证据语义由 atomic-agent 控制。

代价：

- 模型可能输出无效 JSON。
- schema 约束不如原生 tool calling 强。
- 需要实现 parser retry（解析重试）和 fail-closed 行为。

## Alternatives Considered

1. 直接使用 OpenAI/Anthropic native tool calling。
   - 优点：schema enforcement（模式约束）更强。
   - 缺点：provider 耦合。
2. 让模型一次性返回完整文件集合。
   - 优点：实现最简单。
   - 缺点：不是 agent work loop，缺少 observation-repair 和 tool evidence。

## Links

- `docs/03-contracts/agent-action-protocol.md`
- `docs/02-architecture/runtime-architecture.md`
