# Event Stream Protocol

## Status

active

## Purpose

本文定义 `AgentEvent`（智能体事件）协议。事件流是 `atomic-agent`（原子智能体）的审计事实源，用于重放、验证和与 Boardroom OS（Boardroom 操作系统）对接。

## Event Envelope

每条事件为一个 JSON object（JSON 对象）：

```json
{
  "event_id": "evt_000001",
  "run_id": "run_000001",
  "sequence": 1,
  "type": "run.started",
  "timestamp": "2026-06-04T00:00:00Z",
  "payload": {},
  "previous_event_hash": null,
  "event_hash": "sha256:..."
}
```

字段：

| Field | 中文解释 | 要求 |
|---|---|---|
| `event_id` | 事件标识 | 单条事件唯一。 |
| `run_id` | 运行标识 | 关联一次 AgentRun。 |
| `sequence` | 序号 | 从 1 开始递增。 |
| `type` | 事件类型 | 使用受控枚举。 |
| `timestamp` | 时间戳 | ISO 8601；测试可使用 deterministic clock（确定性时钟）。 |
| `payload` | 载荷 | 事件类型专属内容。 |
| `previous_event_hash` | 前序事件哈希 | 第一条为 null。 |
| `event_hash` | 当前事件哈希 | 对规范化事件计算得到。 |

## Required Event Types

P0 runtime 必须支持：

```text
run.started
run.completed
run.failed
provider.turn.started
provider.turn.completed
provider.turn.failed
action.parsed
action.rejected
permission.decided
tool.attempt.started
tool.attempt.completed
tool.attempt.failed
workspace.mutation.recorded
command.completed
network.fetch.completed
result.submitted
```

## Ordering Rules

- `run.started` 必须是第一条事件。
- `run.completed` 或 `run.failed` 必须是最后一条终止事件之一。
- `tool.attempt.completed` 之前必须有对应 `tool.attempt.started`。
- `workspace.mutation.recorded` 必须引用造成变更的 `tool_attempt_id`。
- `command.completed` 必须引用对应 `tool_attempt_id`。
- `result.submitted` 不能出现在 `run.started` 之前，也不能出现在终止事件之后。

## Payload References

事件 payload（载荷）不应内联大文件或完整 stdout/stderr。应使用 artifact reference（产物引用）：

```json
{
  "artifact_ref": "artifact://run_000001/stdout/test.txt",
  "sha256": "...",
  "size_bytes": 1234,
  "truncated_in_observation": true
}
```

## Error Events

错误事件必须包含：

- error kind（错误类型）
- message（简短说明）
- retryable（是否可重试）
- related action/tool/provider reference（相关引用）

错误事件不得吞掉真实失败，也不得转成成功事件。

## Redaction

如果 payload 涉及 secret（密钥）或敏感内容，事件必须记录 redaction（脱敏）事实：

```json
{
  "redacted": true,
  "redaction_reason": "secret-pattern"
}
```

脱敏不能破坏审计：必须保留长度、哈希或替代引用等可验证信息。

## Versioning

事件协议必须包含版本信息。可以在 `run.started` payload 中记录：

```json
{"event_protocol_version": 1}
```

破坏性变更必须写 ADR（架构决策记录）。
