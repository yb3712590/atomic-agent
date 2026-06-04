# Action Parser Specification

## Status

implemented

## Purpose

本文定义 P0-002 `JSON action parser`（JSON 动作解析器）的实现规格。该解析器负责把 provider output（模型供应商输出）转换为经过严格校验的 `AgentAction`（智能体动作），为后续 permission policy（权限策略）、tool executor（工具执行器）和 AgentLoop（智能体循环）提供可信输入。

## Scope

P0-002 只覆盖 provider output（模型供应商输出）到 `AgentAction`（智能体动作）的解析边界。

包含：

- 解析 provider 输出的 JSON 文本。
- 拒绝无效 JSON。
- 拒绝非 JSON object（JSON 对象）的顶层值。
- 复用 `AgentAction` 作为 envelope schema（信封结构模式）事实源。
- 拒绝未知 action（动作类型）。
- 拒绝 envelope（信封结构）多余字段。
- 拒绝 `run_command`（运行命令）中的自由 shell string（自由命令字符串）。
- 返回结构化失败信息，供后续 `action.rejected` event（动作拒绝事件）使用。

不包含：

- workspace path guard（工作区路径守卫）。
- symlink escape guard（符号链接逃逸守卫）。
- allowed write set guard（允许写入集合守卫）。
- command policy（命令策略）执行。
- network policy（网络策略）执行。
- event recorder（事件记录器）。
- tool execution（工具执行）。
- observation retry loop（观察结果重试循环）。

这些能力分别由 P0-003、P0-004、P0-005、P0-006、P0-007 和 P1-001 覆盖。

## Authoritative Inputs

本规格依据以下已索引文档：

- `docs/03-contracts/agent-action-protocol.md`（智能体动作协议）。
- `docs/04-implementation-spec/mvp-runtime-spec.md`（MVP 运行时规格）。
- `docs/04-implementation-acceptance/mvp-acceptance.md`（MVP 验收标准）。
- `docs/05-testing/testing-strategy.md`（测试策略）。

## Public API

新增模块：

```text
src/atomic_agent/action_parser.py
```

公开函数：

```python
def parse_agent_action(provider_output: str) -> AgentAction:
    ...
```

失败类型：

```python
class ActionParseError(ValueError):
    kind: str
    message: str
```

`parse_agent_action`（解析智能体动作）成功时返回 `AgentAction`。失败时抛出 `ActionParseError`，不得返回 `None`、空 action（动作）或自动替代 action。

## Validation Rules

### JSON syntax（JSON 语法）

`provider_output` 必须是合法 JSON 文本。空字符串、截断 JSON、普通自然语言回答都必须失败。

失败语义：

```text
kind = "invalid_json"
```

### Top-level shape（顶层结构）

解析后的 JSON 顶层必须是 object（对象）。array（数组）、string（字符串）、number（数字）、boolean（布尔值）和 null 都必须失败。

失败语义：

```text
kind = "invalid_action"
```

### Envelope schema（信封结构模式）

顶层 object 必须符合 `AgentAction`（智能体动作）模型：

- `action_id` 必填。
- `action` 必填，且必须属于 `AgentActionType`（智能体动作类型）。
- `reason_summary` 必填。
- `input` 必填，且必须是 object（对象）。
- 多余 envelope 字段必须拒绝。

失败语义：

```text
kind = "schema_validation_failed"
```

### `run_command` command_id guard（运行命令标识守卫）

当 `action == "run_command"` 时，`input` 必须使用声明式 `command_id`（命令标识）：

```json
{"command_id": "test"}
```

以下字段必须拒绝：

- `command`
- `shell`
- `cmd`

这条规则只保证 parser boundary（解析边界）不会接受自由 shell string（自由命令字符串）。它不判断 `command_id` 是否已被 command policy（命令策略）声明；该判断属于 P0-005。

失败语义：

```text
kind = "schema_validation_failed"
```

### `reason_summary` minimal handling（原因摘要最小处理）

P0-002 只校验 `reason_summary` 存在且类型正确。它不尝试程序化判断文本是否包含 chain-of-thought（思维链），因为这会引入不可可靠验证的语义判断。

## Error Semantics

| Failure kind | 中文解释 | 触发条件 | 恢复语义 |
|---|---|---|---|
| `invalid_json` | 无效 JSON | provider 输出不是合法 JSON 文本 | 后续 AgentLoop 可以把简短错误作为 observation（观察结果）反馈给 provider |
| `invalid_action` | 无效动作形状 | JSON 顶层不是 object | 后续 AgentLoop 可以反馈格式错误 |
| `schema_validation_failed` | 模式校验失败 | 缺字段、未知 action、多余字段、非法 `run_command` input | 后续 AgentLoop 可以反馈具体 schema 边界 |

错误信息必须简短、面向调用方，不包含 chain-of-thought（思维链）。底层异常可以通过 exception chaining（异常链）保留给调试，但不能转换为成功结果。

## Security and No-Fallback Rules

- parser（解析器）不得读取 `.env`、environment variables（环境变量）、local config files（本地配置文件）或 process defaults（进程默认值）。
- parser 不得在 JSON 失败后从 Markdown code fence（Markdown 代码围栏）中猜测或提取替代 JSON。
- parser 不得把自然语言回答转换成 action。
- parser 不得把 `run_command` 的自由 shell string 自动映射为 `command_id`。
- parser 不得吞掉错误并返回默认 action。

## Acceptance Criteria

P0-002 完成时必须证明：

- 合法 `read_file` JSON action 可以解析为 `AgentAction`。
- 合法 `run_command` JSON action 必须使用 `command_id`。
- 无效 JSON 被拒绝，失败类型为 `invalid_json`。
- 非 object JSON 顶层被拒绝，失败类型为 `invalid_action`。
- 未知 action 被拒绝，失败类型为 `schema_validation_failed`。
- 多余 envelope 字段被拒绝，失败类型为 `schema_validation_failed`。
- `run_command` 使用 `command`、`shell` 或 `cmd` 时被拒绝，失败类型为 `schema_validation_failed`。
- 直接构造 `AgentAction` 时也不能绕过 `run_command` 的 `command_id` 约束。
- `pytest -v` 通过。

## Documentation Impact

评审通过并完成实现后，需要更新：

- `docs/04-implementation-backlog/backlog.md`：将 P0-002 标记为 `completed`。
- `docs/04-implementation-spec/INDEX.md`：将本规格从 draft（草案）调整为 active（当前有效）或 implemented（已实现），取决于评审决定。
- `docs/04-implementation-plan/INDEX.md`：将对应 plan（实施计划）移动到 completed / archived（已完成 / 已归档）区。

如果实现过程中发现 action protocol（动作协议）需要破坏性变更，必须先更新 ADR（架构决策记录）。
