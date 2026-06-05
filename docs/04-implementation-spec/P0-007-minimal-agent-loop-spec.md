# Minimal AgentLoop Specification

## Status

implemented

## Purpose

本文定义 P0-007 minimal `AgentLoop`（最小智能体循环）的实现规格。该能力负责把已有 `AgentInvocation`（智能体调用请求）、provider output（模型输出）、`AgentAction`（智能体动作）、permission decision（权限判定）、filesystem / command tools（文件系统 / 命令工具）、observation（观察结果）、`EventRecorder`（事件记录器）和 `AgentRunResult`（智能体运行结果）组合成一个真实、可审计、fail closed（失败关闭）的最小运行闭环。

P0-007 的目标不是实现完整 agent framework（智能体框架），而是证明 MVP runtime（最小可行运行时）可以执行确定性的多步 fake provider loop（假模型供应商循环），并为 P0-008 budget limits（预算限制）、P1 network / Boardroom integration（网络 / Boardroom 集成）提供运行时骨架。

## Scope

P0-007 覆盖以下能力：

- 新增 `AgentLoop`（智能体循环）作为一次运行内短期状态、provider turn（模型轮次）、action parsing（动作解析）、permission decision（权限判定）、tool execution（工具执行）、observation feedback（观察反馈）、terminal result（终止结果）的编排器。
- 新增最小 `ProviderAdapter`（模型供应商适配器）协议，测试中使用 deterministic fake provider（确定性假模型供应商）证明 loop semantics（循环语义）。
- 新增 `ArtifactWriter`（产物写入器），把 provider output、observation、diff、stdout/stderr 和 result submission（结果提交）写入显式配置的 artifact directory（产物目录），并返回真实 hash（哈希）和 artifact reference（产物引用）。
- 复用现有 `parse_agent_action`（解析智能体动作），不得在 loop 中实现第二套 JSON parser（JSON 解析器）。
- 复用现有 `WorkspacePathGuard`（工作区路径守卫）、`FilesystemTools`（文件系统工具）、`CommandPolicy`（命令策略）和 `CommandTools`（命令工具）。
- 复用现有 `EventRecorder`（事件记录器）写出 JSONL event stream（JSONL 事件流）。
- 支持 `list_files`、`read_file`、`search_files`、`write_file`、`apply_patch`、`run_command` 和 `submit_result`。
- 对 provider invalid JSON（无效 JSON）、未知 / 未启用工具、越权路径、未声明命令、工具失败、provider failure（模型失败）和 `max_steps`（最大步数）耗尽执行 fail closed。
- 构造 `AgentRunResult`，包含 event stream reference（事件流引用）、event hash（事件哈希）、tool attempts（工具调用尝试）、workspace mutations（工作区变更）、artifacts（产物）和摘要 / 失败详情。

不包含：

- 不实现 `web_fetch`（网络获取）或 `NetworkPolicy`（网络策略）；`web_fetch` 在 P0-007 中必须 fail closed，P1-001 覆盖实现。
- 不实现 real provider integration（真实模型供应商集成）；真实 provider 测试属于后续 integration profile（集成配置）。
- 不实现 Boardroom `AgentRuntimePort` adapter（Boardroom 智能体运行时端口适配器）；P1-002 覆盖。
- 不实现 native tool calling（原生工具调用）；ADR-0002 将其列为后续扩展。
- 不实现 long-running service runner（长运行服务运行器）、browser automation（浏览器自动化）或 external coding agent bridge（外部编码智能体桥接）。
- 不实现完整 `max_wall_seconds`（最大运行秒数）或全局 resource budget（资源预算）体系；P0-007 只实现 loop 所需的 `max_steps` 和 invalid JSON retry limit（无效 JSON 重试限制），P0-008 继续硬化预算。
- 不更新 README minimal example（最小示例）；只有 P0/P0-008 相关验收命令真实稳定后才更新 README。

## Authoritative Inputs

本规格依据以下已索引文档：

- `docs/02-architecture/runtime-architecture.md`（运行时架构）。
- `docs/03-contracts/agent-action-protocol.md`（智能体动作协议）。
- `docs/03-contracts/agent-runtime-port.md`（智能体运行时端口契约）。
- `docs/03-contracts/event-stream-protocol.md`（事件流协议）。
- `docs/04-implementation-spec/mvp-runtime-spec.md`（MVP 运行时规格）。
- `docs/04-implementation-acceptance/mvp-acceptance.md`（MVP 验收标准）。
- `docs/05-testing/testing-strategy.md`（测试策略）。
- `docs/09-adr/0002-use-provider-agnostic-action-protocol.md`（模型供应商无关动作协议 ADR）。
- `docs/09-adr/0003-use-fail-closed-permission-model.md`（失败关闭权限模型 ADR）。

## Public API

### `src/atomic_agent/artifacts.py`

新增 artifact module（产物模块）：

| Symbol | 中文解释 | Contract |
|---|---|---|
| `ArtifactWriterConfig` | 产物写入器配置 | frozen dataclass，字段为 `artifact_root: Path`、`artifact_ref_prefix: str` |
| `ArtifactWriterError` | 产物写入错误 | `RuntimeError` 子类，用于配置、路径、序列化或 IO 失败 |
| `ArtifactWriter` | 产物写入器 | 初始化接收显式配置，通过 `write_text`、`write_json` 写真实文件并返回 `ArtifactReference.to_payload()` 形态的 dict |

`ArtifactWriter` 必须只写入 `artifact_root` 内路径。调用方传入的 artifact relative path（产物相对路径）必须是非空相对路径，不能包含 `..`，不能是 absolute path（绝对路径）。

### `src/atomic_agent/agent_loop.py`

新增 loop module（循环模块）：

| Symbol | 中文解释 | Contract |
|---|---|---|
| `ProviderContext` | 模型上下文 | frozen dataclass，字段为 `invocation: AgentInvocation`、`step: int`、`observations: tuple[dict[str, Any], ...]` |
| `ProviderAdapter` | 模型供应商适配器 | Protocol，定义 `complete(context: ProviderContext) -> str` |
| `AgentLoopConfig` | 智能体循环配置 | frozen dataclass，字段为 `run_id: str` |
| `AgentLoopDependencies` | 智能体循环依赖 | frozen dataclass，字段为 provider、filesystem tools、command tools、event recorder、artifact writer、clock_seconds |
| `PermissionDecision` | 权限判定 | frozen dataclass，字段为 `decision: Literal["allow", "deny"]`、`reason: str`、`policy_ref: str` |
| `AgentLoop` | 智能体循环 | 初始化接收 `AgentLoopConfig` 和 `AgentLoopDependencies`，通过 `run(invocation: AgentInvocation) -> AgentRunResult` 执行一次运行 |
| `AgentLoopError` | 智能体循环错误 | `RuntimeError` 子类，用于不可恢复的内部编排错误；对外应优先返回 failed `AgentRunResult` |

`AgentLoop` 不拥有长期状态。每次 `run` 只维护当前 invocation（调用）的 observation window（观察窗口）、tool attempt list（工具尝试列表）、workspace mutation list（工作区变更列表）、artifact list（产物列表）、parse failure count（解析失败计数）和 step counter（步数计数）。

## Invocation Requirements

P0-007 要求 `AgentInvocation`（智能体调用请求）显式提供以下语义字段。

### `tools`（工具集合）

成功运行至少需要启用：

```python
["write_file", "apply_patch", "run_command", "submit_result"]
```

可选启用：

```python
["list_files", "read_file", "search_files"]
```

规则：

- provider 请求的 action（动作）必须存在于 `invocation.tools`。
- 未启用的 action 必须记录 `permission.decided` 为 `deny`，并 fail closed。
- `web_fetch` 即使出现在 `invocation.tools` 中，P0-007 仍必须 deny，原因是 P1-001 尚未实现网络策略。

### `permission_policy`（权限策略）

P0-007 要求 `permission_policy` 包含：

```json
{
  "policy_ref": "policy://test/minimal-loop"
}
```

`policy_ref` 用于 `permission.decided` 事件。缺失或非空字符串校验失败时，runtime 必须在 `run.started` 后记录 `run.failed`，返回 failed `AgentRunResult`，不得使用硬编码默认 policy ref（策略引用）。

### `budgets`（预算）

P0-007 要求 `budgets` 包含：

```json
{
  "max_steps": 8,
  "max_parse_failures": 2,
  "max_observation_chars": 4000
}
```

规则：

- `max_steps` 必须是正整数，表示 provider/action loop iteration（循环迭代）上限。
- `max_parse_failures` 必须是非负整数，表示 invalid JSON / schema validation failure（无效 JSON / 模式校验失败）可反馈给 provider 的次数。
- `max_observation_chars` 必须是正整数，表示传回 provider context（模型上下文）的单条 observation JSON 字符串最大长度。
- 缺失或非法 budget（预算）必须 fail closed，不得使用 runtime 默认值。
- `max_wall_seconds` 留给 P0-008；P0-007 不得宣称已完整实现时间预算。

### `provider_profile`（模型供应商配置）

P0-007 不直接调用真实模型 API，但必须把完整 `provider_profile` 保留在 `ProviderContext` 中供 `ProviderAdapter` 使用。AgentLoop 不得读取 `.env`、environment variables（环境变量）或 local config（本地配置）来补全 provider profile（模型配置）。

## Main Loop Semantics

`AgentLoop.run(invocation)` 必须按以下顺序执行。

### 1. Validate invocation-level runtime requirements（校验调用级运行时要求）

- 验证 `permission_policy.policy_ref`。
- 验证 `budgets.max_steps`、`budgets.max_parse_failures`、`budgets.max_observation_chars`。
- 验证 `submit_result` 是否出现在 `invocation.tools`；缺失时可以开始运行并在 provider 请求 submit 时 deny，也可以在 `run.started` 后直接 fail closed。P0-007 采用前置 fail closed，避免运行无法成功提交的 invocation。

### 2. Record run start（记录运行开始）

第一条事件必须是：

```text
run.started
```

payload 中必须包含 `event_protocol_version` 和 `invocation_id`，由 `EventRecorder.record_run_started` 负责。

### 3. Repeat provider/action loop（重复模型 / 动作循环）

对 `step` 从 `1` 到 `max_steps`：

1. 记录 `provider.turn.started`。
2. 调用 `provider.complete(ProviderContext(...))`。
3. 将 provider raw output（模型原始输出）写为 artifact（产物），记录 `provider.turn.completed`。
4. 调用既有 `parse_agent_action(provider_output)`。
5. 如果解析失败：
   - 记录 `action.rejected`。
   - 将简短 parse error observation（解析错误观察）加入 observation window。
   - 如果 parse failure count（解析失败计数）超过 `max_parse_failures`，记录 `run.failed` 并返回 failed `AgentRunResult`。
   - 否则进入下一轮 provider call。
6. 如果解析成功：
   - 记录 `action.parsed`。
   - 执行 permission decision（权限判定）。
   - 记录 `permission.decided`。
   - 如果 deny，记录 `run.failed` 并返回 failed `AgentRunResult`。
   - 如果 action 是 `submit_result`，记录 `result.submitted`、`run.completed` 并返回 completed `AgentRunResult`。
   - 否则执行对应工具。
   - 记录 tool attempt（工具尝试）、workspace mutation（工作区变更）或 command completed（命令完成）事件。
   - 将工具 observation（工具观察结果）加入 observation window，进入下一轮。

### 4. Exhaust max steps（耗尽最大步数）

如果 `max_steps` 次迭代后仍未 `submit_result`，必须：

- 记录 `run.failed`。
- 返回 `AgentRunResult(status=FAILED, failure_kind="max_steps_exceeded")`。

不得在未收到 `submit_result` 的情况下伪造 completed result（完成结果）。

## Permission Decision Semantics

P0-007 的 minimal permission decision（最小权限判定）只做已实现工具边界，不替代工具内部 guard（守卫）。

通用规则：

- action 名称必须在 `invocation.tools` 中。
- `policy_ref` 必须来自 `invocation.permission_policy["policy_ref"]`。
- 每个 parsed action（已解析动作）必须记录一次 `permission.decided`。

动作规则：

| Action | Permission rule（权限规则） |
|---|---|
| `list_files` | `path` 缺省时允许；提供 `path` 时必须通过 `WorkspacePathGuard.resolve_read_path` |
| `read_file` | `path` 必须通过 `WorkspacePathGuard.resolve_read_path` |
| `search_files` | `path` 缺省时允许；提供 `path` 时必须通过 `WorkspacePathGuard.resolve_read_path` |
| `write_file` | `path` 必须通过 `WorkspacePathGuard.resolve_write_path` |
| `apply_patch` | `path` 必须通过 `WorkspacePathGuard.resolve_write_path` |
| `run_command` | `command_id` 必须格式合法并存在于 `CommandPolicy` |
| `submit_result` | `summary` 必须为非空字符串，`produced_paths` 必须为字符串列表，`evidence_refs` 如存在必须为字符串列表 |
| `web_fetch` | P0-007 中始终 deny，原因 `web_fetch_not_implemented` |

工具自身仍必须保留执行边界校验。即使 loop permission decision（循环权限判定）允许，工具层如果发现非法输入也必须返回失败；AgentLoop 必须把该失败转为 fail closed 结果。

## Tool Execution Semantics

### Filesystem actions（文件系统动作）

`AgentLoop` 必须通过 `execute_filesystem_action(action, filesystem_tools)` 执行：

- `list_files`
- `read_file`
- `search_files`
- `write_file`
- `apply_patch`

成功时：

- 记录 `tool.attempt.started`。
- 执行工具。
- 将完整 `FileToolResult`（文件工具结果）序列化为 observation artifact（观察产物）。
- 记录 `tool.attempt.completed`。
- 对 `write_file` 和 `apply_patch` 成功结果，必须把 `diff` 写入 diff artifact（差异产物），记录 `workspace.mutation.recorded`。
- 把可传给 provider 的 observation 加入 observation window。

失败时：

- 记录 `tool.attempt.failed`。
- 记录 `run.failed`。
- 返回 failed `AgentRunResult`。

### Command action（命令动作）

`AgentLoop` 必须通过 `execute_command_action(action, command_tools)` 执行 `run_command`。

成功工具结果（`CommandToolResult.ok is True`）表示命令真实启动并完成，即使 `exit_code != 0`：

- 记录 `tool.attempt.started`。
- 执行命令。
- 将 visible stdout/stderr（可见标准输出 / 标准错误）写为 artifact，并在 artifact payload 中设置 `truncated_in_observation` 为 `stdout_truncated` / `stderr_truncated`。
- 记录 `command.completed`，包含 exit code（退出码）和 stdout/stderr artifact references（标准输出 / 标准错误产物引用）。
- 将完整 command result data（命令结果数据，包括原始 stdout_hash/stderr_hash）写为 observation artifact。
- 记录 `tool.attempt.completed`。
- 将 observation 加入 observation window。

工具失败（例如未知命令、timeout、启动失败）时：

- 记录 `tool.attempt.failed`。
- 记录 `run.failed`。
- 返回 failed `AgentRunResult`。

P0-007 不重新实现 subprocess（子进程）执行，也不解析 shell string（命令字符串）。

### `submit_result` action（提交结果动作）

`submit_result` 不调用外部工具，但必须形成可审计事件和结果：

- input 必须包含非空 `summary`。
- input 必须包含 `produced_paths: list[str]`；可为空列表，但字段必须存在。
- input 可以包含 `evidence_refs: list[str]`，用于引用前序事件、tool attempt 或 artifact ref。
- AgentLoop 必须把完整 submit input 写为 result submission artifact（结果提交产物）。
- `EventRecorder.record_result_submitted` 的 `artifact_refs` 至少包含 result submission artifact。
- 记录 `run.completed`。
- 返回 `AgentRunResult(status=COMPLETED)`。

`submit_result` 只代表 runtime completed（运行时完成），不代表 Boardroom ticket completed（工单完成）。

## Observation Semantics

每条 observation（观察结果）必须同时满足：

- 有完整 observation artifact（观察产物），保存真实 JSON。
- 有传给 provider 的 visible observation（可见观察），长度不超过 `budgets.max_observation_chars`。
- 如果 visible observation 被截断，必须设置 `truncated=True`，并保留 observation artifact ref（观察产物引用）。

ProviderContext（模型上下文）中的 observation entry（观察条目）形态：

```json
{
  "step": 2,
  "action_id": "step-0002",
  "tool": "run_command",
  "ok": true,
  "visible": "{... possibly truncated JSON ...}",
  "truncated": false,
  "artifact": {
    "artifact_ref": "artifact://run_001/observations/tool_000002.json",
    "sha256": "sha256:<hex>",
    "size_bytes": 123,
    "truncated_in_observation": false
  }
}
```

Invalid JSON parse observation（无效 JSON 解析观察）也必须进入 observation window，使 fake provider 可以基于错误修复下一轮输出。

## Artifact Semantics

`ArtifactWriter`（产物写入器）必须：

- 接收显式 `artifact_root` 和 `artifact_ref_prefix`。
- 拒绝不存在的 parent（父目录）或非法 root（根目录）配置。
- 创建 artifact subdirectories（产物子目录）。
- 写入 UTF-8 文本或稳定 JSON。
- 返回真实 `ArtifactReference.to_payload()` 形态。
- 计算真实 file bytes（文件字节）的 SHA-256。
- 不 fallback 到临时目录、当前工作目录或内存 buffer。
- 不接受 absolute artifact path（绝对产物路径）或包含 `..` 的相对路径。

`artifact_ref_prefix` 示例：

```text
artifact://run_001
```

写入 `observations/tool_000001.json` 后返回：

```text
artifact://run_001/observations/tool_000001.json
```

## Event Semantics

成功或失败运行都必须产生 terminal event（终止事件）：

- 成功：`result.submitted` 后写 `run.completed`。
- 失败：写 `run.failed`。

P0-007 成功路径必须至少产生：

```text
run.started
provider.turn.started
provider.turn.completed
action.parsed
permission.decided
tool.attempt.started
tool.attempt.completed
workspace.mutation.recorded
command.completed
result.submitted
run.completed
```

失败路径必须尽量保留失败前事实，例如：

- invalid JSON：`provider.turn.completed` + `action.rejected` + `run.failed`。
- permission denied：`action.parsed` + `permission.decided` + `run.failed`。
- tool failure：`tool.attempt.started` + `tool.attempt.failed` + `run.failed`。

如果 `EventRecorder` 自身写入失败，AgentLoop 不得构造伪成功结果；必须向调用方抛出 `AgentLoopError` 或返回失败结果，具体实现计划采用抛出 `AgentLoopError`，因为事件流不可写时无法生成可信 `AgentRunResult.events_hash`。

## Result Contract

### Completed result（完成结果）

`AgentRunResult(status=COMPLETED)` 必须包含：

- `run_id` 来自 `AgentLoopConfig.run_id`。
- `event_stream_ref` 来自 `EventRecorder.event_stream_ref`。
- `events_hash` 来自 `EventRecorder.events_hash()`。
- `tool_attempts` 包含每次工具尝试摘要。
- `workspace_mutations` 包含每次文件变更摘要。
- `artifacts` 包含本次运行创建的 artifact payloads（产物载荷）。
- `summary` 来自 `submit_result.input["summary"]`。
- 不包含 failure fields（失败字段）。

### Failed result（失败结果）

`AgentRunResult(status=FAILED)` 必须包含：

- `failure_kind`：稳定机器可读类型。
- `failure_message`：简短人类可读说明。
- `failed_action_ref`：如失败与某个 action 相关，填 `action.action_id`；否则可为 `None`。
- `summary`：说明运行 fail closed。
- `event_stream_ref` 和 `events_hash`，除非 event recorder 本身不可用并抛出 `AgentLoopError`。

P0-007 使用以下 failure kind（失败类型）：

| failure_kind | 中文解释 | 触发条件 |
|---|---|---|
| `invalid_invocation` | 调用非法 | 必需 budget / policy / submit_result 工具缺失或非法 |
| `provider_failed` | 模型失败 | provider adapter 抛出异常 |
| `action_parse_failed` | 动作解析失败 | invalid JSON / schema failure 超过 `max_parse_failures` |
| `policy_denied` | 权限拒绝 | action 未启用、路径越权、命令未声明、web_fetch 未实现 |
| `tool_failed` | 工具失败 | filesystem / command tool 返回 `ok=False` |
| `max_steps_exceeded` | 最大步数耗尽 | 未收到 submit_result 且达到 `max_steps` |

## Security and No-Fallback Rules

- AgentLoop 不得读取 `.env`、environment variables（环境变量）、local config files（本地配置文件）或 process defaults（进程默认值）。
- AgentLoop 不得硬编码 provider、model、workspace root、allowed write set、tools、permission policy、command policy、budgets、timeouts、artifact root 或 output requirements。
- AgentLoop 不得重新实现 JSON action parser；必须调用 `parse_agent_action`。
- AgentLoop 不得重新实现 path guard（路径守卫）或 command execution（命令执行）。
- AgentLoop 不得在权限拒绝后自动改用其它路径、命令或工具。
- AgentLoop 不得把 provider output（模型输出）单独当作 implementation evidence（实现证据）。
- AgentLoop 不得在未收到 `submit_result` 时构造 completed result。
- ArtifactWriter 不得在写入失败时改写到其它路径。
- Fake provider tests（假模型供应商测试）只能证明 runtime semantics（运行时语义），不能宣称真实模型能力。

## Acceptance Criteria

P0-007 完成时必须证明：

- `ArtifactWriter` 写出真实文件，并返回真实 SHA-256 artifact payload。
- `AgentLoop` 可以执行一个多步 deterministic fake provider loop：写文件、运行声明命令失败、应用 patch 修复、再次运行命令成功、提交结果。
- command failure by non-zero exit code（非零退出码命令失败）作为 observation 进入下一轮，而不是 tool failure（工具失败）。
- 成功运行产生 `AgentRunResult(status=COMPLETED)`。
- 成功运行产生 JSONL event stream，包含 provider、action、permission、tool、workspace mutation、command、result 和 terminal events。
- 文件变更有 `workspace.mutation.recorded`，包含 before/after hash 和 diff artifact。
- 命令执行有 `command.completed`，包含 exit code 和 stdout/stderr artifact references。
- provider invalid JSON 会记录 `action.rejected`，在未超过限制时反馈 observation，超过限制后 fail closed。
- 未启用工具、越权写入、未声明命令和 `web_fetch` 请求都会 fail closed，并记录 `permission.decided` deny。
- 超过 `max_steps` 会 fail closed，不伪造成功。
- failed `AgentRunResult` 包含 failure kind/message 和 event stream hash。
- runtime source 不包含 `.env`、`os.environ`、`getenv`、`dotenv`、`shell=True` 等 fallback / shell patterns。
- `pytest -v` 通过。

## Documentation Impact

评审通过并完成实现后，需要更新：

- `docs/04-implementation-backlog/backlog.md`：将 P0-007 标记为 `completed`。
- `docs/04-implementation-spec/P0-007-minimal-agent-loop-spec.md`：将状态从 `draft` 改为 `implemented`。
- `docs/04-implementation-plan/P0-007-minimal-agent-loop-plan.md`：将状态从 `draft` 改为 `implemented`。
- `docs/04-implementation-spec/INDEX.md`：将本规格从 Current Active Documents（当前活跃文档）移动到 Completed / Archived Documents（已完成 / 已归档文档）。
- `docs/04-implementation-plan/INDEX.md`：将对应 plan（实施计划）从 Current Active Documents 移动到 Completed / Archived Documents。

如果实现过程中发现 action protocol（动作协议）、event protocol（事件协议）或 AgentRuntimePort（智能体运行时端口）需要破坏性语义变更，必须先更新规格；如果影响长期架构原则，必须先新增或更新 ADR（架构决策记录）。
