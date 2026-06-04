# Event Recorder and JSONL Event Stream Specification

## Status

implemented

## Purpose

本文定义 P0-006 `event recorder`（事件记录器）和 JSONL event stream（JSONL 事件流）的实现规格。该能力负责把 runtime（运行时）产生的 `AgentEvent`（智能体事件）按协议写入 append-only（只追加）、ordered（有序）、hashable（可哈希）的 JSONL 文件，并为后续 `AgentLoop`（智能体循环）、fail-closed budget limits（失败关闭预算限制）和 Boardroom OS（Boardroom 操作系统）evidence（证据）映射提供可审计事实源。

## Scope

P0-006 覆盖以下能力：

- 新增 `EventRecorder`（事件记录器）作为事件写入、sequence（序号）分配、event hash（事件哈希）链和 event stream hash（事件流哈希）的唯一事实源。
- 复用现有 `AgentEvent`（智能体事件）和 `AgentEventType`（智能体事件类型）模型。
- 将每条事件写为一行 JSON object（JSON 对象），形成 JSONL event stream（JSONL 事件流）。
- 支持 `docs/03-contracts/event-stream-protocol.md` 中列出的 required event types（必需事件类型）。
- 对每个事件补齐 `event_id`、`run_id`、`sequence`、`timestamp`、`previous_event_hash` 和 `event_hash`。
- 对事件 payload（载荷）执行最小 required field validation（必填字段校验），避免写出不可审计事件。
- 提供 typed helper methods（类型化辅助方法），供后续 `AgentLoop` 调用。
- 提供 `event_stream_ref`（事件流引用）和 `events_hash`（事件流哈希），供 `AgentRunResult`（智能体运行结果）引用。
- 事件写入失败、payload 缺字段、事件顺序非法时 fail closed（失败关闭），不得返回伪成功。

不包含：

- 不实现 `AgentLoop`（智能体循环）provider 调用、工具调度、observation（观察结果）回传或重试逻辑。
- 不修改 filesystem tools（文件系统工具）或 command tools（命令工具）的执行语义。
- 不实现 artifact store（产物存储）；本任务只记录调用方提供的 artifact reference（产物引用）和 hash（哈希）。
- 不实现 `web_fetch`（网络获取）或 `NetworkPolicy`（网络策略）。
- 不实现 event replay（事件重放）执行器；本任务只保证事件流具备 replay-friendly（便于重放）字段。
- 不实现 secret scanner（密钥扫描器）；调用方如已脱敏，事件必须记录 redaction（脱敏）事实。
- 不直接产生 Boardroom governance completion（治理完成）事件。

这些能力分别由 P0-007、P0-008、P1-001、M4 和后续 roadmap（路线图）任务覆盖。

## Authoritative Inputs

本规格依据以下已索引文档：

- `docs/03-contracts/event-stream-protocol.md`（事件流协议）。
- `docs/02-architecture/event-and-evidence-architecture.md`（事件与证据架构）。
- `docs/04-implementation-spec/mvp-runtime-spec.md`（MVP 运行时规格）。
- `docs/04-implementation-acceptance/mvp-acceptance.md`（MVP 验收标准）。
- `docs/05-testing/testing-strategy.md`（测试策略）。
- `docs/09-adr/0003-use-fail-closed-permission-model.md`（失败关闭权限模型 ADR）。

## Public API

新增模块：

```text
src/atomic_agent/event_recorder.py
```

公开类型和函数：

| Symbol | 中文解释 | Contract |
|---|---|---|
| `EVENT_PROTOCOL_VERSION` | 事件协议版本 | `int` 常量，当前为 `1` |
| `EventRecorderConfig` | 事件记录器配置 | frozen dataclass，字段为 `event_stream_path: Path`、`event_stream_ref: str` |
| `EventRecorderError` | 事件记录器错误 | `RuntimeError` 子类，表示写入、校验或顺序错误 |
| `EventRecorderConfigError` | 事件记录器配置错误 | `ValueError` 子类，表示非法输出路径或引用配置 |
| `ArtifactReference` | 产物引用 | frozen dataclass，字段为 `artifact_ref: str`、`sha256: str`、`size_bytes: int`、`truncated_in_observation: bool` |
| `EventError` | 事件错误载荷 | frozen dataclass，字段为 `kind: str`、`message: str`、`retryable: bool`、`related_ref: str | None` |
| `EventRecorder` | 事件记录器 | 初始化接收 `run_id`、`EventRecorderConfig`、`clock`，并提供 `record_*` helper methods（辅助方法）和 `record` 通用方法 |

`EventRecorder`（事件记录器）必须接收显式 `EventRecorderConfig`（事件记录器配置）。runtime code（运行时代码）不得硬编码输出路径、artifact URI（产物 URI）、run id（运行标识）或 clock（时钟）。

## Event Stream Output

### JSONL shape（JSONL 形态）

每次 `record` 成功调用必须向 `event_stream_path` 追加一行 UTF-8 JSON：

```json
{"event_id":"evt_000001","run_id":"run_001","sequence":1,"type":"run.started","timestamp":"2026-06-05T00:00:00Z","payload":{"event_protocol_version":1,"invocation_id":"inv_001"},"previous_event_hash":null,"event_hash":"sha256:<hex>"}
```

规则：

- 每行必须是独立可解析 JSON object（JSON 对象）。
- 输出文件必须使用 UTF-8。
- 写入必须 append-only（只追加）；不得重写已有事件行。
- 事件行必须按 sequence（序号）升序写入。
- 事件 JSON 必须使用 stable serialization（稳定序列化）：`sort_keys=True`、紧凑分隔符、`ensure_ascii=False`。
- JSONL 文件末尾每条事件后必须有 newline（换行），便于逐行解析。

### `event_id`（事件标识）

P0-006 使用 deterministic event id（确定性事件标识）：

```text
evt_000001
evt_000002
evt_000003
```

`event_id` 由 recorder（记录器）根据 sequence 分配，调用方不得传入或覆盖。

### `sequence`（序号）

`sequence` 必须从 `1` 开始，每成功写入一条事件递增 `1`。

如果事件写入失败，该失败事件不得计入成功序列；下一次成功写入继续使用失败前的下一序号。失败原因必须通过 `EventRecorderError` 暴露给调用方。

### `timestamp`（时间戳）

`timestamp` 由构造时传入的 `clock: Callable[[], str]` 提供。

规则：

- `clock()` 必须返回非空 ISO 8601 string（ISO 8601 字符串）。
- 测试必须使用 deterministic clock（确定性时钟）。
- runtime 可以在入口层注入真实 UTC clock（UTC 时钟），但 recorder 不得读取 `.env`、local config（本地配置）或 process defaults（进程默认值）来推导时间策略。

## Hash Semantics

### Event hash（事件哈希）

`event_hash` 必须对 canonical event hash input（规范事件哈希输入）计算：

```json
{
  "event_id": "evt_000001",
  "run_id": "run_001",
  "sequence": 1,
  "type": "run.started",
  "timestamp": "2026-06-05T00:00:00Z",
  "payload": {"event_protocol_version": 1, "invocation_id": "inv_001"},
  "previous_event_hash": null
}
```

规则：

- hash input 不包含 `event_hash` 自身。
- hash input 必须使用 stable serialization：`json.dumps(..., sort_keys=True, separators=(",", ":"), ensure_ascii=False)`。
- `event_hash` 格式必须为 `sha256:<64 lowercase hex chars>`。

### Hash chain（哈希链）

- 第一条事件的 `previous_event_hash` 必须为 `null`。
- 第 N 条事件的 `previous_event_hash` 必须等于第 N-1 条事件的 `event_hash`。
- recorder（记录器）必须维护 last event hash（上一事件哈希），调用方不得覆盖。

### Event stream hash（事件流哈希）

`EventRecorder.events_hash()` 必须返回完整 JSONL 文件 bytes（字节）的 SHA-256：

```text
sha256:<64 lowercase hex chars>
```

如果事件流文件不存在、不可读或读取失败，必须抛出 `EventRecorderError`，不得返回空 hash 或伪 hash。

## Required Event Types and Payload Rules

P0-006 必须支持以下事件类型。所有 helper methods（辅助方法）必须通过同一个 `record` 写入路径，不得绕过 hash chain（哈希链）或 sequence（序号）分配。

| Event Type | Helper | Required payload fields（必填载荷字段） |
|---|---|---|
| `run.started` | `record_run_started` | `event_protocol_version`, `invocation_id` |
| `run.completed` | `record_run_completed` | `summary` |
| `run.failed` | `record_run_failed` | `error` |
| `provider.turn.started` | `record_provider_turn_started` | `provider_turn_id` |
| `provider.turn.completed` | `record_provider_turn_completed` | `provider_turn_id`, `output` |
| `provider.turn.failed` | `record_provider_turn_failed` | `provider_turn_id`, `error` |
| `action.parsed` | `record_action_parsed` | `action` |
| `action.rejected` | `record_action_rejected` | `error` |
| `permission.decided` | `record_permission_decided` | `action_id`, `decision`, `policy_ref`, `reason` |
| `tool.attempt.started` | `record_tool_attempt_started` | `tool_attempt_id`, `action_id`, `tool` |
| `tool.attempt.completed` | `record_tool_attempt_completed` | `tool_attempt_id`, `action_id`, `tool`, `observation` |
| `tool.attempt.failed` | `record_tool_attempt_failed` | `tool_attempt_id`, `action_id`, `tool`, `error` |
| `workspace.mutation.recorded` | `record_workspace_mutation_recorded` | `tool_attempt_id`, `path`, `before_hash`, `after_hash`, `diff` |
| `command.completed` | `record_command_completed` | `tool_attempt_id`, `command_id`, `exit_code`, `stdout`, `stderr` |
| `network.fetch.completed` | `record_network_fetch_completed` | `tool_attempt_id`, `url`, `status_code`, `response` |
| `result.submitted` | `record_result_submitted` | `summary`, `produced_paths`, `artifact_refs` |

### Error payload（错误载荷）

所有错误事件的 `error` payload 必须包含：

```json
{
  "kind": "permission_denied",
  "message": "command_id is not declared in command policy",
  "retryable": false,
  "related_ref": "act_000001"
}
```

字段规则：

- `kind` 必须是非空字符串。
- `message` 必须是非空字符串。
- `retryable` 必须是 boolean（布尔值）。
- `related_ref` 可为 string（字符串）或 `null`。

### Artifact reference payload（产物引用载荷）

`output`、`observation`、`diff`、`stdout`、`stderr`、`response` 等可能较大的内容必须使用 artifact reference（产物引用）结构：

```json
{
  "artifact_ref": "artifact://run_001/stdout/test.txt",
  "sha256": "sha256:<64 lowercase hex chars>",
  "size_bytes": 1234,
  "truncated_in_observation": true
}
```

字段规则：

- `artifact_ref` 必须是非空字符串。
- `sha256` 必须是 `sha256:<hex>` 格式。
- `size_bytes` 必须是 `>= 0` 的 integer（整数）。
- `truncated_in_observation` 必须是 boolean（布尔值）。

P0-006 不创建 artifact（产物）；它只验证并记录调用方传入的 artifact reference。

### Redaction payload（脱敏载荷）

如果调用方传入的 artifact reference 或 event payload 包含 redaction（脱敏）事实，recorder 必须保留以下字段，不得删除：

```json
{
  "redacted": true,
  "redaction_reason": "secret-pattern"
}
```

P0-006 不负责发现 secret（密钥），但不得破坏调用方提供的 redaction metadata（脱敏元数据）。

## Ordering Rules

`EventRecorder` 必须强制以下顺序：

- 第一条事件必须是 `run.started`。
- `run.completed` 或 `run.failed` 是 terminal event（终止事件）。
- terminal event 写入后不得再写入任何事件。
- `tool.attempt.completed` 和 `tool.attempt.failed` 必须引用已经 started（已开始）的 `tool_attempt_id`。
- `workspace.mutation.recorded` 必须引用已经 started 的 `tool_attempt_id`。
- `command.completed` 必须引用已经 started 的 `tool_attempt_id`。
- `result.submitted` 不得出现在 `run.started` 之前，也不得出现在 terminal event 之后。

违反顺序必须抛出 `EventRecorderError`，不得写出事件行。

P0-006 不要求检查 provider turn（模型轮次）完整生命周期；只要求 helper payload 字段完整。provider retry（模型重试）和 observation loop（观察循环）由 P0-007 处理。

## Configuration Rules

`EventRecorderConfig` 字段语义：

| Field | 中文解释 | 约束 |
|---|---|---|
| `event_stream_path` | JSONL 输出路径 | 必须是 `Path`，父目录必须已存在，目标不存在或为空文件；不得是目录 |
| `event_stream_ref` | 事件流引用 | 必须是非空字符串，通常为 `artifact://.../events.jsonl` |

非法配置必须在 `EventRecorder` 初始化时失败，不得 fallback（兜底）到当前目录、临时目录或内存 buffer（内存缓冲）。

`EventRecorder` 初始化时如果目标文件已存在且非空，必须抛出 `EventRecorderConfigError`，避免多个运行混写同一 event stream（事件流）。

## Result Contract

每个成功 helper method 必须返回已写入的 `AgentEvent`（智能体事件）。返回对象字段必须与 JSONL 中对应行完全一致。

失败时必须抛出：

- `EventRecorderConfigError`：配置错误，例如输出路径非法。
- `EventRecorderError`：事件 payload 缺字段、顺序非法、clock 返回非法值、JSONL 写入失败、事件流读取失败。

失败不得：

- 返回伪 `AgentEvent`。
- 跳过失败事件并递增 sequence。
- 改写输出路径。
- 降级为内存记录。
- 将错误事件转成成功事件。

## Security and No-Fallback Rules

- event recorder 不得读取 `.env`、environment variables（环境变量）、local config files（本地配置文件）或 process defaults（进程默认值）。
- event recorder 不得硬编码 event stream output path（事件流输出路径）或 artifact URI（产物 URI）。
- event recorder 不得在输出路径不可写时改写到其它路径。
- event recorder 不得吞掉 JSON serialization（JSON 序列化）或 file IO（文件 IO）失败。
- event recorder 不得接受调用方传入的 `sequence`、`event_id`、`previous_event_hash` 或 `event_hash` 覆盖内部事实。
- event recorder 不得把 provider output（模型输出）单独标记为 implementation evidence（实现证据）；只能记录为 provider turn artifact（模型轮次产物）或 result submission candidate（工作产物提交候选）。

## Acceptance Criteria

P0-006 完成时必须证明：

- `EventRecorder` 可以创建 JSONL event stream（JSONL 事件流）。
- `record_run_started` 写出的第一条事件包含 `event_protocol_version = 1`。
- 每条 JSONL 行都可以被 JSON parser（JSON 解析器）解析。
- `event_id` 从 `evt_000001` 开始递增。
- `sequence` 从 `1` 开始递增。
- 第一条事件的 `previous_event_hash = None`。
- 后续事件的 `previous_event_hash` 等于上一条事件的 `event_hash`。
- 每条 `event_hash` 都是规范事件哈希输入的真实 SHA-256。
- `events_hash()` 返回完整 JSONL bytes 的真实 SHA-256。
- 所有 required event types（必需事件类型）都能通过 helper method 写入。
- 缺少 required payload field（必填载荷字段）时抛出 `EventRecorderError`，且不写出事件行。
- `tool.attempt.completed` 未对应 started attempt（已开始尝试）时抛出 `EventRecorderError`。
- terminal event（终止事件）之后继续写入事件会抛出 `EventRecorderError`。
- JSONL 输出路径不可写或 writer 失败时抛出 `EventRecorderError`，且不返回成功事件。
- `AgentRunResult` 可以使用 recorder 提供的 `event_stream_ref` 和 `events_hash` 构造结果。
- `pytest -v` 通过。

## Documentation Impact

评审通过并完成实现后，需要更新：

- `docs/04-implementation-backlog/backlog.md`：将 P0-006 标记为 `completed`。
- `docs/04-implementation-spec/INDEX.md`：将本规格从 Current Active Documents（当前活跃文档）移动到 Completed / Archived Documents（已完成 / 已归档文档）。
- `docs/04-implementation-plan/INDEX.md`：将对应 plan（实施计划）移动到 Completed / Archived Documents。

如果实现过程中发现 event protocol（事件协议）需要破坏性语义变更，必须先更新本规格；如果影响长期架构原则，必须先新增或更新 ADR（架构决策记录）。
