# Command Policy and Run Command Specification

## Status

implemented

## Purpose

本文定义 P0-005 `command policy`（命令策略）和 `run_command`（运行声明命令）的实现规格。该能力负责把 `AgentAction`（智能体动作）中的 `command_id`（命令标识）解析为显式声明的命令，在受控 cwd（工作目录）、env（环境变量）、timeout（超时）和 output limit（输出限制）下真实执行，并返回结构化 command result（命令结果），为后续 event recorder（事件记录器）和 AgentLoop（智能体循环）提供可审计事实。

## Scope

P0-005 覆盖以下能力：

- 定义 `CommandPolicy`（命令策略）作为 `command_id` 到 `CommandSpec`（命令声明）的唯一事实源。
- 实现 `run_command`（运行声明命令），只执行 policy（策略）中声明的命令。
- 拒绝未知 `command_id`，且不得执行任何进程。
- 使用 argv list（参数数组）和 `shell=False`，不接受自由 shell string（自由命令字符串）。
- 使用 `WorkspacePathGuard`（工作区路径守卫）约束命令 cwd（工作目录）。
- 使用显式 `env` mapping（环境变量映射），不隐式继承 process environment（进程环境）。
- 使用显式 timeout（超时）和 output limit（输出限制）。
- 返回 stdout/stderr（标准输出/标准错误）的 hash（哈希）、size（字节数）、truncation（截断）和 decode（解码）事实。
- 区分 command completed（命令已完成）与 tool failure（工具失败）：非零 exit code（退出码）是已完成命令结果，不等于工具执行失败。

不包含：

- event recorder（事件记录器）或 JSONL event stream（JSONL 事件流）输出。
- AgentLoop（智能体循环）重试逻辑。
- budget limits（预算限制）的全局计数，例如 max command runs（最大命令次数）。
- network policy（网络策略）或 `web_fetch`（网络获取）。
- OS-level sandbox（操作系统级沙箱）或进程级网络隔离。
- service runner（服务运行器）或 long-running process manager（长运行进程管理器）。
- shell command parser（shell 命令解析器）。

这些能力分别由 P0-006、P0-007、P0-008、P1-001 和后续 roadmap（路线图）任务覆盖。

## Authoritative Inputs

本规格依据以下已索引文档：

- `docs/04-implementation-spec/mvp-runtime-spec.md`（MVP 运行时规格）。
- `docs/04-implementation-acceptance/mvp-acceptance.md`（MVP 验收标准）。
- `docs/03-contracts/agent-action-protocol.md`（智能体动作协议）。
- `docs/02-architecture/permission-and-sandbox-architecture.md`（权限与沙箱架构）。
- `docs/02-architecture/runtime-architecture.md`（运行时架构）。
- `docs/09-adr/0003-use-fail-closed-permission-model.md`（失败关闭权限模型 ADR）。

## Public API

新增模块：

```text
src/atomic_agent/command_tools.py
```

公开类型和函数：

| Symbol | 中文解释 | Contract |
|---|---|---|
| `CommandSpec` | 命令声明 | frozen dataclass，字段为 `argv: tuple[str, ...]`、`cwd: str | None`、`timeout_seconds: float | None`、`env: dict[str, str] | None`、`allow_network: bool` |
| `CommandToolConfig` | 命令工具配置 | frozen dataclass，字段为 `default_timeout_seconds: float`、`max_timeout_seconds: float`、`max_output_bytes: int` |
| `CommandToolResult` | 命令工具结果 | frozen dataclass，字段为 `ok: bool`、`tool: str`、`command_id: str | None`、`data: dict[str, Any]`、`error_kind: str | None`、`error_message: str | None` |
| `CommandToolConfigError` | 命令工具配置错误 | `ValueError` 子类，用于非法 policy/config（策略/配置） |
| `CommandPolicy` | 命令策略 | 初始化接收 `commands: dict[str, CommandSpec]`，并通过 `resolve(command_id: str) -> CommandSpec | None` 查询声明命令 |
| `CommandTools` | 命令工具集合 | 初始化接收 `WorkspacePathGuard`（工作区路径守卫）、`CommandPolicy` 和 `CommandToolConfig`，并通过 `run_command(command_id: str) -> CommandToolResult` 执行声明命令 |
| `execute_command_action` | 执行命令动作 | 接收 `AgentAction` 和 `CommandTools`，只分发 `RUN_COMMAND` |

`CommandTools`（命令工具集合）必须接收显式 `CommandPolicy` 和 `CommandToolConfig`（命令工具配置）。runtime code（运行时代码）不得在工具实现中硬编码 command list（命令列表）、timeout（超时）、output limit（输出限制）或 env（环境变量）。

## Command Policy Semantics

### `command_id`（命令标识）

`command_id` 必须是非空字符串，并符合以下模式：

```text
^[A-Za-z0-9_.:-]+$
```

该限制让 command id（命令标识）稳定、可审计，并避免把用户输入误当作 shell 片段。`command_id` 不参与 shell 拼接；它只用于查找 `CommandPolicy`。

未知 `command_id` 必须拒绝：

```text
ok = False
error_kind = "permission_denied"
error_message = "command_id is not declared in command policy"
```

拒绝时不得启动进程、不得 fallback（兜底）到默认命令、不得尝试把 `command_id` 当作可执行文件名。

### `CommandSpec.argv`（参数数组）

`argv` 必须是非空字符串序列：

```python
CommandSpec(argv=("/absolute/path/to/python", "-m", "pytest", "-q"))
```

规则：

- `argv[0]` 是 executable（可执行文件）。
- `argv[0]` 必须是 absolute path（绝对路径），避免 PATH lookup（PATH 查找）或 process default（进程默认值）影响。
- 每个 argv item（参数项）必须是非空字符串。
- 执行时必须使用 `shell=False`。
- 不得支持单个 shell string（命令字符串），例如 `"pytest -q"`。
- 不得用 `sh -c`、`bash -lc` 或平台 shell 作为隐式 fallback。

如果 policy 中声明的 executable 不存在或无法执行，`run_command` 返回结构化失败，不得替换为其它 executable。

### `CommandSpec.cwd`（工作目录）

`cwd` 可省略或为 `None`。省略时命令在 workspace root（工作区根目录）执行。

如果提供 `cwd`：

- 必须是 workspace root 内的 relative path（相对路径）。
- 必须通过 `WorkspacePathGuard.resolve_read_path`。
- 必须指向已存在 directory（目录）。
- 不得穿越 symlink escape（符号链接逃逸）。

非法 cwd 是 invocation configuration defect（调用配置缺陷），必须在 `CommandTools` 初始化时抛出 `CommandToolConfigError`，不得在执行命令时静默改用 workspace root。

### `CommandSpec.env`（环境变量映射）

P0-005 使用 explicit env mapping（显式环境变量映射）：

- `env = None` 表示空环境 `{}`，不是继承当前进程环境。
- `env` 中所有 key 和 value 必须是字符串。
- env key 必须非空。
- runtime 不得读取 `os.environ`、`.env`、local config files（本地配置文件）或 process defaults（进程默认值）来补全环境变量。

Standalone entrypoint（独立入口）未来可以从 `.env` 构造完整 `AgentInvocation`（智能体调用请求）和 `CommandPolicy`；构造完成后，runtime 执行过程中仍只能使用显式 policy input（策略输入）。

### `CommandSpec.timeout_seconds`（命令超时）

`timeout_seconds` 可省略。省略时使用 `CommandToolConfig.default_timeout_seconds`。

规则：

- timeout 必须 `> 0`。
- timeout 必须 `<= CommandToolConfig.max_timeout_seconds`。
- 超时后必须终止进程，并返回结构化失败：

```text
ok = False
error_kind = "timeout"
```

超时不得记录为成功命令结果。

### `CommandSpec.allow_network`（是否允许网络）

P0-005 不实现 OS-level network sandbox（操作系统级网络沙箱），因此不能真实阻止进程访问网络。为避免 mock success path（模拟成功路径），P0-005 采用 fail-closed 规则：

- `allow_network` 必须为 `False`。
- 如果 command policy 声明 `allow_network=True`，`CommandPolicy` 初始化必须抛出 `CommandToolConfigError`。
- P0-005 不得声称已实现进程级网络隔离。

后续如需要 network-enabled command（允许网络的命令），必须先通过 roadmap review（路线图复审）或 ADR（架构决策记录）明确隔离与审计策略。

## Configuration Rules

`CommandToolConfig` 字段语义：

| Field | 中文解释 | 约束 |
|---|---|---|
| `default_timeout_seconds` | 默认命令超时秒数 | `> 0` 且 `<= max_timeout_seconds` |
| `max_timeout_seconds` | 单个命令最大超时秒数 | `> 0` |
| `max_output_bytes` | stdout/stderr 单路最大返回字节数 | `> 0` |

非法配置必须在 `CommandTools` 初始化时失败，不得 fallback 为默认值。

## Result Contract

所有命令工具调用必须返回 `CommandToolResult`（命令工具结果）。

成功工具结果表示命令进程真实启动并完成，即使 exit code（退出码）非零：

```text
ok = True
error_kind = None
error_message = None
data = <command result data>
```

失败工具结果表示工具未能安全完成命令执行，例如未知命令、配置错误、超时、启动失败：

```text
ok = False
error_kind = <stable machine-readable kind>
error_message = <short human-readable message>
data = {}
```

### Successful command data（成功命令数据）

成功结果 `data` 必须包含：

```json
{
  "command_id": "test",
  "argv": ["/absolute/path/to/python", "-m", "pytest", "-q"],
  "cwd": "/absolute/workspace/path",
  "exit_code": 0,
  "stdout": "...",
  "stderr": "...",
  "stdout_hash": "sha256:<hex>",
  "stderr_hash": "sha256:<hex>",
  "stdout_size_bytes": 123,
  "stderr_size_bytes": 45,
  "stdout_truncated": false,
  "stderr_truncated": false,
  "stdout_decoded_with_replacement": false,
  "stderr_decoded_with_replacement": false,
  "timeout_seconds": 10.0
}
```

规则：

- `stdout_hash` 和 `stderr_hash` 必须基于完整 bytes（字节）计算，而不是基于截断文本。
- `stdout` 和 `stderr` 字段可以按 `max_output_bytes` 截断。
- 截断必须通过 `stdout_truncated` / `stderr_truncated` 显式记录。
- 非 UTF-8 输出可以用 replacement character（替换字符）解码，但必须通过 `*_decoded_with_replacement = True` 记录。
- `argv` 返回 policy 中实际执行的参数数组，便于后续 event recorder（事件记录器）生成可审计事件。
- `cwd` 返回实际工作目录绝对路径。

## Error Semantics

| `error_kind` | 中文解释 | 触发条件 |
|---|---|---|
| `invalid_input` | 非法工具输入 | `command_id` 缺失、类型错误、空字符串或格式非法 |
| `permission_denied` | 权限拒绝 | `command_id` 未在 `CommandPolicy` 声明 |
| `timeout` | 命令超时 | 命令超过 timeout 并被终止 |
| `execution_failed` | 执行失败 | executable 不存在、权限不足或 subprocess 启动失败 |
| `unsupported_action` | 不支持动作 | dispatcher 收到非 `run_command` action |

所有失败都必须 fail closed（失败关闭）：不得执行未声明命令、不得替换 executable、不得继承环境变量作为 fallback、不得把失败记录为成功。

## Dispatcher Semantics

`execute_command_action`（执行命令动作）只分发：

- `AgentActionType.RUN_COMMAND`

其他 action 必须失败：

```text
ok = False
error_kind = "unsupported_action"
```

该函数不得执行 filesystem action（文件系统动作）、`web_fetch`（网络获取）或 `submit_result`（提交结果）。

`AgentAction` 模型已在 P0-002 中拒绝 `run_command` 的自由 shell string（自由命令字符串）。P0-005 仍必须在工具层校验 `command_id` 类型和 policy membership（策略成员关系），因为工具层是执行边界。

## Security and No-Fallback Rules

- command tools 不得读取 `.env`、environment variables（环境变量）、local config files（本地配置文件）或 process defaults（进程默认值）。
- command tools 不得继承当前进程环境；`env=None` 必须解释为空环境 `{}`。
- command tools 不得使用 `shell=True`。
- command tools 不得接受自由 shell string（自由命令字符串）。
- command tools 不得通过 PATH lookup（PATH 查找）寻找 executable；`argv[0]` 必须是绝对路径。
- command tools 不得在未知 `command_id` 时尝试同名 executable。
- command tools 不得在 cwd 非法时改用 workspace root。
- command tools 不得声称实现了 OS-level network sandbox（操作系统级网络沙箱）。
- command tools 不得把 timeout、启动失败或权限拒绝伪装成成功命令结果。

## Acceptance Criteria

P0-005 完成时必须证明：

- `CommandToolResult` 成功结果不含 error fields（错误字段）。
- `CommandToolResult` 失败结果必须包含 `error_kind` 和 `error_message`。
- `CommandToolConfig` 拒绝非法 timeout 和 output limit 配置。
- `CommandPolicy` 拒绝空 policy（策略）、空 `command_id`、非法 `command_id`、空 argv、非绝对 executable、非字符串 env、`allow_network=True`。
- `run_command` 可以执行 policy 中声明的真实命令。
- `run_command` 对未知 `command_id` 返回 `permission_denied`，且不启动进程。
- `run_command` 对非零 exit code 返回 `ok=True`，并保留真实 `exit_code`。
- `run_command` 对 timeout 返回 `ok=False` 和 `error_kind="timeout"`。
- `run_command` 对 stdout/stderr 计算完整 bytes hash，并显式记录截断。
- `run_command` 使用显式 env，不继承 `os.environ`。
- `run_command` 使用 workspace root 或通过 path guard（路径守卫）的 cwd。
- `run_command` 拒绝 cwd symlink escape（符号链接逃逸）。
- `execute_command_action` 分发 `RUN_COMMAND`，并拒绝非 command action（命令动作）。
- 现有 action parser（动作解析器）仍拒绝自由 shell string。
- `pytest -v` 通过。

## Documentation Impact

评审通过并完成实现后，需要更新：

- `docs/04-implementation-backlog/backlog.md`：将 P0-005 标记为 `completed`。
- `docs/04-implementation-spec/INDEX.md`：将本规格从 Current Active Documents（当前活跃文档）移动到 Completed / Archived Documents（已完成 / 已归档文档）。
- `docs/04-implementation-plan/INDEX.md`：将对应 plan（实施计划）移动到 Completed / Archived Documents。

如果实现过程中发现 command policy（命令策略）需要破坏性语义变更，必须先更新本规格；如果影响长期架构原则，必须先新增或更新 ADR（架构决策记录）。
