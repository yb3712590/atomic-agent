# Event and Evidence Architecture

## Status

active

## Purpose

本文定义 `atomic-agent`（原子智能体）的 event stream（事件流）与 evidence（证据）架构。事件流是 runtime 的可审计事实，不是调试日志。

## Event Stream Shape

事件流推荐使用 JSONL（每行一个 JSON 对象）：

```json
{"event_id":"evt_001","run_id":"run_001","type":"run.started","sequence":1}
{"event_id":"evt_002","run_id":"run_001","type":"tool.attempt.completed","sequence":2}
```

基本要求：

- append-only（只追加）
- ordered（有序）
- typed（有类型）
- hashable（可哈希）
- replay-friendly（可重放）

## Core Event Types

| Event Type | 中文解释 | 用途 |
|---|---|---|
| `run.started` | 运行开始 | 标记一次 invocation 开始 |
| `run.completed` | 运行完成 | 标记正常完成 |
| `run.failed` | 运行失败 | 标记 fail closed 或不可恢复错误 |
| `provider.turn.started` | 模型轮次开始 | 记录一次 provider 调用开始 |
| `provider.turn.completed` | 模型轮次完成 | 记录模型输出和 artifact 引用 |
| `provider.turn.failed` | 模型轮次失败 | 记录模型调用失败 |
| `action.parsed` | 动作已解析 | 记录标准化 AgentAction |
| `action.rejected` | 动作被拒绝 | 记录 schema 或权限拒绝 |
| `permission.decided` | 权限已决策 | 记录策略命中与决策 |
| `tool.attempt.started` | 工具调用开始 | 标记工具执行开始 |
| `tool.attempt.completed` | 工具调用完成 | 记录工具输出或 observation |
| `tool.attempt.failed` | 工具调用失败 | 记录工具错误 |
| `workspace.mutation.recorded` | 工作区变更已记录 | 记录文件 before/after hash 和 diff |
| `command.completed` | 命令完成 | 记录 exit code、stdout/stderr artifact |
| `result.submitted` | 结果已提交 | 记录 agent 提交摘要和产物引用 |

## Evidence Objects

事件可以引用这些证据对象：

- `ToolAttempt`（工具调用尝试记录）
- `WorkspaceMutation`（工作区变更）
- `CommandResult`（命令结果）
- `NetworkFetchResult`（网络获取结果）
- `ProviderTurnArtifact`（模型轮次产物）
- `DiffArtifact`（差异产物）
- `ObservationArtifact`（观察结果产物）

## Boardroom Evidence Mapping

与 Boardroom OS（Boardroom 操作系统）集成时，映射关系建议为：

| atomic-agent | Boardroom OS |
|---|---|
| `provider.turn.completed` | `ProviderAttempt`（模型调用尝试记录）或 provider turn evidence |
| `tool.attempt.completed` | `ToolAttempt`（工具调用尝试记录） |
| `workspace.mutation.recorded` | `WorkspaceMutation`（工作区变更）与 `SourceInventory`（源码清单）lineage |
| `command.completed` | `VerificationRun`（验证运行） |
| `result.submitted` | `WorkProductSubmission`（工作产物提交）候选输入 |

`atomic-agent` 只提供事实，不生成 Boardroom 治理完成事件。

## Redaction and Observation

完整 stdout/stderr、网页响应和文件内容可以进入 artifact store（产物存储），但返回给模型的 observation（观察结果）必须受限：

- 截断过长输出。
- 避免泄露 secret（密钥）。
- 标明内容是否被截断。
- 保留 artifact reference（产物引用）以供审计。

## Replay Requirements

重放至少需要：

- invocation snapshot（调用快照）
- policy snapshot（策略快照）
- event stream（事件流）
- artifact hashes（产物哈希）
- tool versions（工具版本）

如果无法重放，必须显式标记原因，不能假装可重放。
