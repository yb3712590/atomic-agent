# Runtime Architecture

## Status

active

## Purpose

本文定义 `atomic-agent runtime`（原子智能体运行时）的核心模块边界。runtime 的职责是执行受控 agent loop（智能体循环），而不是替代上层治理系统。

## High-Level Components

```text
AgentRuntime
├── InvocationLoader
├── PromptContextBuilder
├── ProviderAdapter
├── ActionParser
├── PermissionEngine
├── ToolRegistry
├── ToolExecutor
├── EventRecorder
└── ResultBuilder
```

| Component | 中文解释 | 职责 |
|---|---|---|
| `InvocationLoader` | 调用加载器 | 校验 `AgentInvocation`（智能体调用请求）。 |
| `PromptContextBuilder` | 提示上下文构建器 | 组合任务、角色、工具协议、权限和观察结果。 |
| `ProviderAdapter` | 模型供应商适配器 | 调用 provider（模型供应商）并返回 raw output（原始输出）。 |
| `ActionParser` | 动作解析器 | 将模型输出解析为 `AgentAction`（智能体动作）。 |
| `PermissionEngine` | 权限引擎 | 根据策略判断动作是否允许执行。 |
| `ToolRegistry` | 工具注册表 | 暴露可用工具和 schema（模式）。 |
| `ToolExecutor` | 工具执行器 | 执行工具并生成 `Observation`（观察结果）。 |
| `EventRecorder` | 事件记录器 | 记录 provider、tool、mutation、command 等事件。 |
| `ResultBuilder` | 结果构建器 | 生成 `AgentRunResult`（智能体运行结果）。 |

## Main Loop

```text
1. validate invocation
2. build initial context
3. record run.started
4. repeat until stop condition:
   a. call provider
   b. record provider.turn.completed or failed
   c. parse AgentAction
   d. validate permission
   e. execute tool
   f. record ToolAttempt / WorkspaceMutation / CommandResult
   g. append observation
   h. stop on submit_result or fail_closed
5. build AgentRunResult
6. record run.completed or run.failed
```

## Stop Conditions

runtime 必须在以下条件停止：

- `submit_result`（提交结果）动作通过最小证据检查。
- `max_steps`（最大步数）耗尽。
- `max_wall_seconds`（最大运行秒数）耗尽。
- provider（模型供应商）持续失败并超过策略限制。
- action parse（动作解析）持续失败并超过策略限制。
- permission denied（权限拒绝）且策略要求 fail closed。
- tool execution（工具执行）出现不可恢复错误。

## Provider-Agnostic Design

runtime 不依赖 provider 原生 tool calling（工具调用）。第一阶段使用 provider-agnostic JSON action protocol（模型供应商无关 JSON 动作协议）。未来 OpenAI/Anthropic/native tool calls 可以在 `ProviderAdapter` 层归一化为同一个 `AgentAction`。

## State Ownership

runtime 内部只拥有一次运行的短期状态：

- conversation state（对话状态）
- observation window（观察窗口）
- tool attempt list（工具调用记录列表）
- event stream cursor（事件流游标）
- budget counters（预算计数器）

长期治理状态、ticket 状态、closeout 状态不属于 runtime。

## Failure Semantics

runtime 失败时必须返回结构化失败结果，而不是空成功或伪成功。失败结果必须包含：

- failure kind（失败类型）
- failed action（失败动作，如有）
- policy decision（权限决策，如有）
- event stream reference（事件流引用）
- resumability hint（是否可恢复的提示）
