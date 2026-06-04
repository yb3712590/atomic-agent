# ADR-0003: Use Fail-Closed Permission Model

## Status

Accepted

## Context

atomic-agent（原子智能体）需要读写文件、执行命令和访问网络。这些能力如果默认开放，会带来路径逃逸、未授权命令、网络泄露和供应链风险。

## Decision

采用 fail-closed（失败关闭）权限模型。未知路径、未知命令、未知网络目标、未知动作和策略冲突都默认拒绝。

## Consequences

正面影响：

- 降低越权执行风险。
- 使审计记录更可信。
- 与 Boardroom OS 的 evidence-first（证据优先）和 fail-closed 治理风格一致。

代价：

- 初期配置更严格，可能需要更多显式策略。
- agent 可能因缺少权限而停止，需要上层明确授权。
- 需要实现详尽 negative tests（负向测试）。

## Alternatives Considered

1. 默认允许，失败后再收紧。
   - 拒绝原因：违反安全边界，容易产生不可审计副作用。
2. 允许自由 shell，但记录日志。
   - 拒绝原因：日志不等于权限控制，也不等于证据可信。

## Links

- `docs/02-architecture/permission-and-sandbox-architecture.md`
- `docs/04-implementation-acceptance/mvp-acceptance.md`
