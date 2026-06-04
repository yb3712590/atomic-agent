# Agent Runtime Port Contract

## Status

active

## Purpose

本文定义 `AgentRuntimePort`（智能体运行时端口）契约。它是 Boardroom OS（Boardroom 操作系统）等上层系统调用 `atomic-agent runtime`（原子智能体运行时）的稳定边界。

## Port Shape

最小接口语义：

```text
AgentRuntimePort.invoke(invocation: AgentInvocation) -> AgentRunResult
```

实现语言可以变化，但语义必须保持稳定。

## AgentInvocation

`AgentInvocation`（智能体调用请求）描述一次独立运行。

必需字段：

| Field | 中文解释 | 说明 |
|---|---|---|
| `invocation_id` | 调用标识 | 全局唯一或调用方域内唯一。 |
| `task` | 任务 | 用户或上层系统交给 agent 的工作说明。 |
| `workspace_root` | 工作区根目录 | 文件工具的根目录边界。 |
| `allowed_write_set` | 允许写入集合 | 可创建、修改或删除的相对路径集合。 |
| `tools` | 工具集合 | 本次允许启用的工具能力。 |
| `permission_policy` | 权限策略 | 文件、命令、网络和审批策略。 |
| `provider_profile` | 模型供应商配置 | provider、model、reasoning、temperature 等。 |
| `budgets` | 预算限制 | max steps、wall time、tokens、command runs 等。 |
| `output_requirements` | 输出要求 | 期望产物、事件、摘要和证据要求。 |

可选字段：

| Field | 中文解释 | 说明 |
|---|---|---|
| `role_context` | 角色上下文 | Boardroom 的 RolePromptHook（角色提示词钩子）等渲染内容。 |
| `skill_context` | 技能上下文 | SkillBinding（技能绑定）解析后的 prompt/tool/MCP 信息。 |
| `initial_files` | 初始文件提示 | 文件清单或重点文件引用。 |
| `metadata` | 元数据 | 调用方、项目、ticket、trace 等引用。 |

## AgentRunResult

`AgentRunResult`（智能体运行结果）描述一次运行的事实输出。

必需字段：

| Field | 中文解释 | 说明 |
|---|---|---|
| `run_id` | 运行标识 | runtime 分配的运行 ID。 |
| `status` | 状态 | `completed`、`failed`、`interrupted`、`requires_approval`。 |
| `event_stream_ref` | 事件流引用 | JSONL event stream（事件流）位置或 artifact 引用。 |
| `events_hash` | 事件哈希 | 事件流内容哈希。 |
| `tool_attempts` | 工具调用尝试记录 | 工具调用事实摘要或引用。 |
| `workspace_mutations` | 工作区变更 | 文件变更事实摘要或引用。 |
| `artifacts` | 产物 | 产出文件、日志、diff、stdout/stderr 等引用。 |
| `summary` | 摘要 | 非 chain-of-thought（非思维链）的工作摘要。 |

失败时必须包含：

| Field | 中文解释 | 说明 |
|---|---|---|
| `failure_kind` | 失败类型 | `policy_denied`、`provider_failed`、`tool_failed`、`budget_exceeded` 等。 |
| `failure_message` | 失败说明 | 面向调用方的简短失败原因。 |
| `failed_action_ref` | 失败动作引用 | 如有，指向相关 AgentAction 或事件。 |

## Status Semantics

| Status | 中文解释 | 语义 |
|---|---|---|
| `completed` | 完成 | runtime 已提交结果，但不代表 Boardroom ticket 完成。 |
| `failed` | 失败 | runtime fail closed 或不可恢复失败。 |
| `interrupted` | 中断 | 外部中断或用户取消。 |
| `requires_approval` | 需要审批 | 动作需要审批且当前环境不能自动继续。 |

## Boardroom Mapping

Boardroom OS 调用时：

- `ExecutionPackage`（执行包）映射到 `task`、`workspace_root`、`allowed_write_set`、`output_requirements`。
- `ModelExecutionProfile`（模型执行配置）映射到 `provider_profile`。
- `RolePromptHook`（角色提示词钩子）和 `SkillBinding`（技能绑定）映射到 `role_context` 和 `skill_context`。
- `AgentRunResult` 不直接成为 closeout（收尾）成功，只作为 Boardroom EvidenceVerifier（证据验证器）的输入。

## Compatibility Rules

- 新增字段必须有默认缺省语义或版本升级说明。
- 删除字段必须通过新版本契约实现，不能静默破坏旧调用方。
- 字段含义变化必须写 ADR（架构决策记录）。
