# P2-003 External Coding Agent Bridge Design Specification

## Status

archived design reference

> Archive note（归档说明，2026-06-08）：P2-003 runtime implementation（运行时实现）已按用户决定延期；本文仅作为 future external coding agent bridge（未来外部编码智能体桥接）设计参考，不作为当前 P2 exit gate（P2 退出门禁）的活跃依赖。

## Purpose

本文定义 P2-003 `external coding agent bridge`（外部编码智能体桥接）的简化设计规格，采用 **CLI single-request black-box execution**（CLI 单一请求黑盒执行）方案。当前阶段只计划接入已经部署好并且能正常使用的 CLI 版 Codex（Codex 命令行工具）或 Claude Code（Claude Code 命令行工具）。

本方案中，`atomic-agent`（原子智能体）不解析外部 agent 的内部 provider output（模型输出）、tool call（工具调用）或多轮动作；它只负责：

1. 构造一个完整 task string（任务描述字符串）。
2. 创建 isolated worktree（隔离工作树）或 isolated copy（隔离副本）。
3. 按声明的 CLI profile（命令行配置画像）执行一个外部 agent CLI 进程。
4. 捕获 CLI exit code（退出码）、stdout transcript（标准输出会话记录）和 stderr（标准错误）。
5. 扫描隔离工作区 diff（差异）和 workspace mutations（工作区变更）。
6. 按 allowed write set（允许写入集合）和 hash（哈希）校验导入 evidence package（证据包）。

P2-003 的交付物是设计规格和实施计划；它不实现真实 CLI runner（CLI 运行器），不新增 `external_agent_run` 代码路径，不声明 M5 exit criteria（M5 退出标准）已满足。

## Scope

P2-003 覆盖：

- 定义 future `external_agent_run`（外部智能体运行）动作的简化 action input（动作输入）。
- 定义 `ExternalAgentCliProfile`（外部智能体 CLI 配置画像）所需字段：`cli_executable`（CLI 可执行文件）、`cli_args_template`（CLI 参数模板）、`working_directory_mode`（工作目录模式）、`allow_network`（是否允许网络）、`max_wall_seconds`（最大运行秒数）和 `max_output_bytes`（最大输出字节）。
- 定义 CLI black-box evidence package（CLI 黑盒证据包）：`exit_code`、`transcript`、`stderr`、`workspace_mutations`、`network_fetches`。
- 定义 CLI execution failure semantics（CLI 执行失败语义）：CLI 不存在、超时、非零退出码、输出截断和 secret leak（密钥泄漏）。
- 定义 CLI argument injection prevention（CLI 参数注入防护）：provider output 不得提供 `cli_args`、`cli_env`、`cli_stdin` 或 `cli_working_dir`。
- 定义 stdout/stderr transcript redaction（标准输出/错误会话记录脱敏）规则。
- 定义 evidence import（证据导入）时对 workspace mutation path（工作区变更路径）、after hash（变更后哈希）、allowed write set 和 governance fields（治理字段）的 fail-closed 校验。

P2-003 不覆盖：

- 不解析外部 CLI 内部 tool calls（工具调用）。
- 不把外部 CLI 内部命令执行映射为 `command.completed`。
- 不要求外部 CLI 返回 structured command results（结构化命令结果）。
- 不实现 fine-grained network policy reference（细粒度网络策略引用）；第一阶段只使用 `allow_network: false` 或 `allow_network: true` 的粗粒度开关。
- 不实现 `max_external_steps`；单一 CLI 请求没有外部步骤概念。
- 不实现 output contract（输出契约）中的 required artifact list（必需产物列表）；CLI 输出格式由 bridge 固定采集。
- 不接入自由 shell（自由命令行）或 provider 自定义 executable（可执行文件）。
- 不实现 Boardroom EvidenceVerifier（证据验证器）、CloseoutGate（收尾门禁）或 governance event（治理事件）。

## Authoritative Inputs

本规格依据以下已索引 authoritative documents（权威文档）：

- `docs/04-implementation-backlog/backlog.md`（实现待办）：P2-003 任务要求设计 external coding agent bridge 的证据导入协议和权限边界。
- `docs/06-roadmap/roadmap.md`（路线图）：M5 要求外部 coding agent 只能作为 tool（工具）运行，diff（差异）、日志和命令结果必须导入事件和证据模型，且不能绕过 permission policy（权限策略）。在本简化方案中，CLI 进程本身的 exit code/stdout/stderr 是可导入事实；CLI 内部命令不拆成 `command.completed`。
- `docs/00-overview/boardroom-os-integration-summary.md`（Boardroom OS 集成摘要）：外部 agent framework（智能体框架）必须通过 tool boundary（工具边界）导入事实，不能绕过证据模型。
- `docs/02-architecture/permission-and-sandbox-architecture.md`（权限与沙箱架构）：未知动作、路径、命令、网络目标和策略冲突默认 deny（拒绝）。
- `docs/02-architecture/event-and-evidence-architecture.md`（事件与证据架构）：event stream（事件流）是审计事实源，不是调试日志。
- `docs/03-contracts/agent-action-protocol.md`（动作协议）：future extension（未来扩展）列出 `external_agent_run`，新增动作必须先更新协议和索引。
- `docs/03-contracts/event-stream-protocol.md`（事件流协议）：事件必须有序、可哈希、引用 artifact（产物）而不内联大文件。
- `docs/09-adr/0002-use-provider-agnostic-action-protocol.md`（供应商无关动作协议 ADR）：runtime 不绑定 provider 原生工具协议。
- `docs/09-adr/0003-use-fail-closed-permission-model.md`（失败关闭权限模型 ADR）：权限必须默认关闭。
- `docs/09-adr/0004-keep-boardroom-os-as-governance-source.md`（Boardroom 治理事实源 ADR）：`atomic-agent` 不声明 Boardroom completion（Boardroom 完成结论）。

## Current Baseline

当前代码与文档基线：

- `AgentActionType`（智能体动作类型）尚无 `external_agent_run`。
- `AgentEventType`（智能体事件类型）尚无 external agent 专属事件。
- `EventRecorder`（事件记录器）已经能记录 hash chained JSONL event stream（带哈希链的 JSONL 事件流）。
- `ArtifactWriter`（产物写入器）和 `evidence.py`（证据模块）已经为 artifact payload（产物载荷）、workspace mutation（工作区变更）和 SourceInventory lineage（源码清单谱系）提供基础能力。
- 现有 P2 real provider gates（真实供应商门禁）验证的是 `atomic-agent` 自身 action loop（动作循环），不接入外部 CLI agent。
- P2-003 当前是设计批次；真正实现前需要用户评审确认。

## Design Principles

1. **External agent as CLI tool（外部智能体作为 CLI 工具）**：外部 agent 只通过声明的 CLI executable（命令行可执行文件）运行一次，不能替代 `AgentLoop`（智能体循环）或 Boardroom OS（Boardroom 操作系统）。
2. **Single request only（仅单一请求）**：`atomic-agent` 发送完整 task string，并等待 CLI 退出；不解析外部 agent 的中间动作。
3. **Black-box transcript（黑盒会话记录）**：stdout 作为 transcript artifact（会话记录产物），stderr 作为 stderr artifact（标准错误产物）；两者必须哈希、限流、脱敏检查。
4. **Diff is the work product（差异是工作产物）**：真正的实现证据来自隔离工作区 diff、workspace mutations 和 hash，而不是 CLI summary（摘要）。
5. **Fail closed before and after CLI execution（CLI 执行前后都失败关闭）**：profile、参数模板、隔离工作区、输出大小、变更路径和 hash 任一不符合策略都失败。
6. **No provider-controlled CLI shape（禁止模型控制 CLI 形态）**：provider output 只能提供 task 和 allowed write subset（允许写入子集）；不能提供 CLI 可执行文件、参数、环境变量、stdin 或工作目录。
7. **No governance conclusion（不产生治理结论）**：CLI 成功退出不等于 Boardroom 工单完成；`atomic-agent` 只导入事实。

## Execution Flow

```text
atomic-agent AgentLoop
  -> parse AgentAction(action="external_agent_run")
  -> validate action input and ExternalAgentCliProfile
  -> create isolated worktree or isolated copy
  -> render CLI args from cli_args_template using {workspace} and {task}
  -> execute CLI process with env allowlist and timeout
  -> capture exit_code, stdout, stderr
  -> write stdout/stderr artifacts with sha256 and truncation flags
  -> scan isolated worktree diff
  -> derive workspace_mutations and recompute hashes
  -> validate mutations against allowed_write_set
  -> build ExternalAgentCliEvidencePackage
  -> record external_agent.run.completed or failed
  -> import workspace.mutation.recorded events
  -> return truncated observation with artifact refs
```

The CLI process is black-box（黑盒）. `atomic-agent` does not inspect whether Claude Code, Codex or another CLI used internal shell commands, tool calls or model turns. Permission enforcement happens through sandbox isolation, CLI profile declaration, process timeout/output limits, network mode and post-run diff import validation.

## Future AgentAction Extension

后续实现前，必须把 `external_agent_run` 加入 `docs/03-contracts/agent-action-protocol.md` 和 `AgentActionType`（智能体动作类型）。简化后的 action envelope（动作信封）如下：

```json
{
  "action_id": "step-0007",
  "action": "external_agent_run",
  "reason_summary": "Run a declared CLI coding agent once to produce a bounded workspace diff.",
  "input": {
    "agent_profile_id": "claude-code-default",
    "task": "Fix the report generator bug and produce valid output.",
    "allowed_write_set": ["work/src/", "work/output/"]
  }
}
```

字段要求：

- `agent_profile_id` 必须引用 invocation policy（调用策略）中已声明的 `ExternalAgentCliProfile`。
- `task` 是传给 CLI 的完整任务字符串。它可以包含目标路径、验证建议和输出要求，但不能覆盖 runtime permission policy（运行时权限策略）。
- `allowed_write_set` 必须是 invocation `allowed_write_set` 的子集。

禁止字段：

```text
cli_executable
cli_args
cli_args_template
cli_env
cli_stdin
cli_working_dir
executable
shell
cmd
command
env
secrets
allow_all
skip_policy
approve_all
ticket_completed
closeout_committed
evidence_verified
source_inventory_accepted
```

出现以上字段时，parser（解析器）或 permission layer（权限层）必须拒绝动作。

## ExternalAgentCliProfile Requirements

`ExternalAgentCliProfile`（外部智能体 CLI 配置画像）必须由 invocation policy 或本地受控配置声明。provider output 只能引用 `agent_profile_id`，不能定义新 profile。

建议最小结构：

```json
{
  "agent_profile_id": "claude-code-default",
  "runner_kind": "claude_code_cli",
  "cli_executable": "/usr/local/bin/claude",
  "cli_args_template": ["--workspace", "{workspace}", "{task}"],
  "working_directory_mode": "isolated_worktree",
  "allow_network": false,
  "env_allowlist": ["PATH", "PYTHONPATH"],
  "max_wall_seconds": 900,
  "max_output_bytes": 5000000
}
```

字段要求：

- `runner_kind` 必须属于受控枚举，例如 `claude_code_cli` 或 `codex_cli`。未知 runner 必须拒绝。
- `cli_executable` 必须是 profile 声明的绝对路径，且运行前必须存在、可执行、不是目录。
- `cli_args_template` 必须由 profile 声明，只允许 `{workspace}` 和 `{task}` 两个占位符。占位符替换后必须作为 argv list（参数数组）执行，不经 shell 拼接。
- `working_directory_mode` 第一阶段只允许 `isolated_worktree` 或 `isolated_copy`。
- `allow_network` 是粗粒度布尔值。`false` 表示外层 sandbox 必须尽力禁用网络；如果当前平台无法提供等价限制，profile 必须拒绝或标记为 unsupported（不支持）。
- `env_allowlist` 是 profile 侧声明，不是 action input。默认应为空或最小化。
- `max_wall_seconds` 是 CLI 进程总超时。
- `max_output_bytes` 同时约束 stdout 和 stderr 采集大小；超出时 artifact 必须标记 `truncated_in_observation: true`，并按策略 fail closed 或返回明确失败。

不再建模的字段：

- 不建模 `allowed_tools`，因为 CLI 内部工具不可由本层可靠控制。
- 不建模 `command_policy_ref`，因为 CLI 内部命令不拆成 atomic-agent declared command（声明命令）。
- 不建模 `network_policy_ref`，第一阶段只使用 `allow_network`。
- 不建模 `transcript_policy`，因为 stdout/stderr 总是捕获为 artifact，并统一走 output limit 和 redaction policy（脱敏策略）。

## CLI Argument Injection Prevention

Provider output（模型输出）不得控制 CLI 执行形态。以下数据只能来自 profile，不得来自 action input：

```text
cli_executable
cli_args_template
env_allowlist
working_directory_mode
allow_network
max_wall_seconds
max_output_bytes
```

Action input 中出现以下字段必须拒绝：

```text
cli_args
cli_env
cli_stdin
cli_working_dir
executable
shell
cmd
command
env
```

执行要求：

- CLI 必须通过 argv list 调用，不能通过 shell string 调用。
- `{task}` 替换后作为单个 argv 元素传入；不得拼接到 shell 命令中。
- `{workspace}` 必须是 runtime 创建的隔离目录，不接受 provider 指定路径。
- stdin（标准输入）第一阶段固定为空或关闭，不允许 provider 提供。
- cwd（当前工作目录）由 profile 和 sandbox 决定，不接受 action input。

## ExternalAgentCliEvidencePackage

CLI runner 完成后必须生成 `ExternalAgentCliEvidencePackage`（外部智能体 CLI 证据包）。该包是导入候选，不是已接受事实。

```json
{
  "schema_version": 1,
  "external_run_id": "ext_run_000001",
  "tool_attempt_id": "tool_attempt_000007",
  "agent_profile_id": "claude-code-default",
  "runner_kind": "claude_code_cli",
  "status": "completed",
  "exit_code": 0,
  "started_at": "2026-06-08T10:00:00Z",
  "completed_at": "2026-06-08T10:05:00Z",
  "transcript": {
    "artifact_ref": "artifact://run_001/external/ext_run_000001/stdout.txt",
    "sha256": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "size_bytes": 12345,
    "truncated_in_observation": false,
    "redacted": false
  },
  "stderr": {
    "artifact_ref": "artifact://run_001/external/ext_run_000001/stderr.txt",
    "sha256": "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "size_bytes": 456,
    "truncated_in_observation": false,
    "redacted": false
  },
  "workspace_mutations": [
    {
      "path": "work/src/report.py",
      "before_hash": "sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
      "after_hash": "sha256:dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",
      "diff": {
        "artifact_ref": "artifact://run_001/external/ext_run_000001/work-src-report.diff",
        "sha256": "sha256:eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
        "size_bytes": 789,
        "truncated_in_observation": false
      }
    }
  ],
  "network_fetches": []
}
```

字段要求：

- `exit_code` 是 CLI 进程退出码。
- `status` 映射规则：`exit_code == 0` 且 evidence import validation（证据导入校验）通过时可为 `completed`；timeout（超时）、CLI 缺失、非零退出码、输出超限、secret leak 或 mutation 校验失败必须为 `failed`。
- `transcript` 是 CLI stdout artifact（标准输出产物）。
- `stderr` 是 CLI stderr artifact（标准错误产物）。
- `workspace_mutations` 来自隔离工作区 diff scan（差异扫描），不是 CLI 自报。
- `network_fetches` 第一阶段通常为空；当 `allow_network=false` 时必须为空。

不包含：

- 不包含 `command_results`，因为 CLI 内部命令不是 atomic-agent declared command。
- 不包含 structured tool attempts（结构化工具尝试），因为 CLI 内部工具调用不解析。
- 不包含 required artifact contract（必需产物契约）；stdout/stderr/diff 是固定采集产物。

## Evidence Package Validation

`EvidenceImporter`（证据导入器）必须按以下顺序校验：

1. 验证 JSON schema（JSON 模式）和 `schema_version`。
2. 验证 `tool_attempt_id` 对应当前 `external_agent_run` tool attempt（工具尝试）。
3. 验证 `agent_profile_id` 与已授权 CLI profile 一致。
4. 验证 `runner_kind` 与 profile 一致。
5. 验证 `exit_code` 是 integer（整数）。
6. 验证 `transcript` 和 `stderr` artifact payload 包含 `artifact_ref`、`sha256`、`size_bytes`、`truncated_in_observation`，且 hash 格式合法。
7. 验证 stdout/stderr artifact 已经过 transcript redaction scan（会话记录脱敏扫描）。
8. 验证 `workspace_mutations[*].path` 是 workspace relative path（工作区相对路径），规范化后仍在 workspace root（工作区根目录）内。
9. 验证每个 mutation path（变更路径）属于 action `allowed_write_set` 和 invocation `allowed_write_set` 的交集。
10. 重新读取隔离 worktree 中对应文件，计算 after hash，必须等于 package 中的 `after_hash`。
11. 对同一路径多次 mutation，验证 before/after hash chain（变更前后哈希链）。
12. 如果 profile `allow_network=false`，验证 `network_fetches` 为空。
13. 验证 package 不包含 governance fields（治理字段）。
14. `exit_code != 0` 时，导入失败状态和 stderr artifact，但不能构造成功 evidence summary（证据摘要）。

任何校验失败都必须返回 `tool.attempt.failed` 或 future `external_agent.run.failed`（外部智能体运行失败）事件，并让 run fail closed 或进入 `requires_approval`，不得导入部分成功事实。

## Event Mapping

本简化方案只需要少量 external agent 事件，并复用现有 workspace mutation 事件。

建议事件序列：

```text
provider.turn.completed
action.parsed              action=external_agent_run
permission.decided         decision=allow
tool.attempt.started       tool=external_agent_run
external_agent.run.started
external_agent.run.completed or external_agent.run.failed
workspace.mutation.recorded path=...      only after completed import validation
tool.attempt.completed or tool.attempt.failed
```

建议新增事件类型：

| Event Type | 中文解释 | 用途 |
|---|---|---|
| `external_agent.run.started` | 外部智能体运行开始 | 记录 external run id、profile id、runner kind、sandbox ref。 |
| `external_agent.run.completed` | 外部智能体运行完成 | 记录 status、exit code、transcript artifact、stderr artifact、duration。 |
| `external_agent.run.failed` | 外部智能体运行失败 | 记录 failure kind、exit code（如有）、stderr artifact（如有）和 transcript artifact（如有）。 |

不新增：

- 不新增 per-artifact `external_agent.artifact.imported`；stdout/stderr artifact refs 放在 `external_agent.run.completed/failed` payload 中。
- 不记录带外部来源标记的 `command.completed`；CLI 内部命令不可拆解为 atomic-agent command evidence。

兼容要求：

- `workspace.mutation.recorded` 仍是 SourceInventory lineage（源码清单谱系）的 canonical source（规范事实源）。
- `tool.attempt.completed` observation（观察结果）只能返回截断摘要、exit code 和 artifact refs，不能内联完整 transcript。
- 新增事件类型前必须更新 `event-stream-protocol.md` 和 `AgentEventType`。

## Permission Boundary

### Invocation-Time Checks（调用时校验）

- `external_agent_run` 必须存在于 invocation `tools`（工具集合）中。
- `agent_profile_id` 必须在 invocation policy 中声明。
- action `allowed_write_set` 必须是 invocation `allowed_write_set` 的子集。
- action input 不得包含 CLI 执行形态字段：`cli_args`、`cli_env`、`cli_stdin`、`cli_working_dir`、`executable`、`shell`、`cmd`、`command`、`env`。
- `task` 必须是非空字符串，并受 max task chars（最大任务字符数）限制。
- CLI profile 的 `cli_executable` 必须存在且可执行。
- CLI profile 的 `cli_args_template` 只能包含 `{workspace}` 和 `{task}` 占位符。
- CLI profile budgets（配置画像预算）不能超过 invocation budgets 和 runtime hard limits。

### Execution-Time Checks（执行时校验）

- CLI 必须在 isolated worktree 或 isolated copy 中运行。
- 不能把宿主仓库根目录、用户 home（主目录）或全局凭据目录作为可写目录暴露给 CLI。
- CLI 必须通过 argv list 执行，不能通过 shell string。
- stdin 固定为空或关闭。
- 环境变量只来自 profile `env_allowlist`。
- `allow_network=false` 时必须使用可用 sandbox 机制禁用网络；无法保证时该 profile 不可用。
- stdout/stderr 必须受 `max_output_bytes` 限制，写入 artifact store 并计算 sha256。
- CLI 超时必须终止进程树并记录 timeout failure（超时失败）。

### Import-Time Checks（导入时校验）

- 扫描 isolated worktree diff，而不是信任 CLI 自报文件列表。
- 重新检查所有 changed paths（变更路径）是否在 allowed write set 内。
- 重新计算 after hash，不能信任 CLI summary。
- 为每个 mutation 生成 diff artifact（差异产物）。
- 验证 stdout/stderr artifact 不包含未脱敏 secret。
- 如果 `allow_network=false`，`network_fetches` 必须为空。
- 验证不含 Boardroom governance fields。

## Transcript Redaction

CLI stdout/stderr 可能包含 API key（接口密钥）、token（令牌）、绝对路径或其它敏感信息。导入前必须执行 transcript redaction scan（会话记录脱敏扫描）。

规则：

- stdout 和 stderr 都必须扫描。
- 如果检测到 secret pattern（密钥模式）且无法生成已脱敏 artifact，则整个导入失败。
- 如果生成 redacted transcript（已脱敏会话记录），artifact payload 必须标记：

```json
{
  "redacted": true,
  "redaction_reason": "secret-pattern"
}
```

- 脱敏不能破坏审计：必须保留 redacted artifact 的 sha256、size_bytes 和 truncated flag。
- event payload 和 observation 不得内联 secret 原文。
- 绝对路径是否脱敏由 profile policy（配置画像策略）决定；默认不应暴露用户 home 或凭据目录路径。

## Failure Semantics

| Failure Kind | 中文解释 | 行为 |
|---|---|---|
| `external_agent_profile_denied` | 外部 CLI 配置画像未授权 | 拒绝动作，记录 `action.rejected` 或 `tool.attempt.failed`。 |
| `external_agent_cli_not_found` | CLI 可执行文件不存在或不可执行 | fail closed。 |
| `external_agent_sandbox_unavailable` | 无可用隔离工作区或网络限制能力 | fail closed，不降级到宿主目录运行。 |
| `external_agent_cli_timeout` | CLI 执行超时 | 终止进程树，记录 timeout failure 和已有 stdout/stderr artifacts。 |
| `external_agent_cli_nonzero_exit` | CLI 退出码非 0 | 记录 exit code、stdout/stderr artifacts，status 为 failed，不导入成功 evidence。 |
| `external_agent_cli_output_truncated` | stdout 或 stderr 超出输出上限 | artifact 标记截断；按 policy fail closed 或返回明确失败。 |
| `external_agent_evidence_schema_invalid` | CLI 证据包模式无效 | 拒绝导入，不构造成功 summary。 |
| `external_agent_mutation_denied` | 变更路径越权 | fail closed，保留 diff artifact 供审计但不接受 mutation。 |
| `external_agent_network_denied` | `allow_network=false` 时出现网络事实 | fail closed。 |
| `external_agent_artifact_hash_mismatch` | 产物或文件 hash 不匹配 | fail closed。 |
| `external_agent_secret_leak_detected` | stdout/stderr 检测到未脱敏密钥 | fail closed 或只导入已脱敏 artifact，并记录 redaction fact。 |
| `external_agent_governance_field_forbidden` | 出现治理字段 | fail closed。 |

不得出现以下 fallback（降级）：

- CLI 不存在时尝试其它 executable。
- 沙箱不可用时改为在真实 workspace root（工作区根目录）运行。
- CLI 退出码非 0 时只采信 stdout summary 并提交成功。
- stdout/stderr 超限时丢弃输出并继续成功。
- 网络禁用不可执行时让 CLI 自行联网。
- hash 不匹配时只采信 CLI summary。
- secret scan 失败时导入未脱敏 transcript。

## Evidence Summary Extension

未来 `build_evidence_summary`（构造证据摘要）可以增加 external agent section（外部智能体区段）：

```json
{
  "external_agent_runs": [
    {
      "external_run_id": "ext_run_000001",
      "tool_attempt_id": "tool_attempt_000007",
      "agent_profile_id": "claude-code-default",
      "runner_kind": "claude_code_cli",
      "status": "completed",
      "exit_code": 0,
      "transcript": {
        "artifact_ref": "artifact://run_001/external/ext_run_000001/stdout.txt",
        "sha256": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "size_bytes": 12345,
        "truncated_in_observation": false
      },
      "stderr": {
        "artifact_ref": "artifact://run_001/external/ext_run_000001/stderr.txt",
        "sha256": "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        "size_bytes": 456,
        "truncated_in_observation": false
      },
      "workspace_mutation_refs": ["evt_000021"]
    }
  ]
}
```

要求：

- `external_agent_runs` 是派生字段，不是第二事实源。
- `workspace_mutation_refs` 必须指向已导入的 `workspace.mutation.recorded` 事件。
- CLI `exit_code == 0` 只能说明 CLI 进程成功，不等于 Boardroom closeout success（Boardroom 收尾成功）。
- 缺失 workspace mutation 的 produced path（产出路径）仍必须在 `source_inventory_lineage` 中标记 `missing_workspace_mutation`。
- 不能加入 `evidence_verified`、`source_inventory_accepted` 或 closeout 结论。

## Testing and Acceptance Criteria

P2-003 design acceptance（设计验收）要求：

- 本规格写入 `docs/04-implementation-spec/P2-003-external-coding-agent-bridge-design-spec.md`。
- 对应计划写入 `docs/04-implementation-plan/P2-003-external-coding-agent-bridge-design-plan.md`。
- `docs/04-implementation-spec/INDEX.md` 加入本 draft spec（草案规格）。
- `docs/04-implementation-plan/INDEX.md` 加入本 draft plan（草案计划）。
- `docs/04-implementation-backlog/backlog.md` 将 P2-003 标记为 `draft`，并引用本规格。
- `docs/INDEX.md` 加入 P2-003 当前活跃文档指针。
- 自审确认 spec 不含过度设计字段 `command_ids`、`command_results`、`allowed_tools`、`command_policy_ref`、`network_policy_ref`、`target_paths`、`output_contract`、`max_external_steps`。
- 自审确认 spec 含 CLI 必需字段 `cli_executable`、`cli_args_template`、`exit_code`、`stderr`、`allow_network`、`max_wall_seconds`、`max_output_bytes`。

Future implementation acceptance（未来实现验收）至少应覆盖：

1. `external_agent_run` 未启用时 parser 拒绝未知动作。
2. 启用后 action schema 拒绝 provider 提供 CLI 执行形态字段。
3. 未声明 `agent_profile_id` 时 fail closed。
4. action allowed write set 不是 invocation allowed write set 子集时拒绝。
5. `cli_executable` 不存在或不可执行时 fail closed。
6. `cli_args_template` 包含非法占位符或需要 shell 拼接时拒绝。
7. 沙箱不可用时拒绝，不降级到宿主 workspace。
8. CLI timeout 时终止并记录 `external_agent_cli_timeout`。
9. CLI 非零退出码时记录 stdout/stderr，但不导入成功 evidence。
10. stdout/stderr 超出 `max_output_bytes` 时标记截断并按策略失败。
11. stdout/stderr 检测到未脱敏 secret 时拒绝导入。
12. mutation path 越权时拒绝导入。
13. after hash 与实际隔离工作区文件不一致时拒绝导入。
14. imported workspace mutations 进入 `workspace.mutation.recorded`，并能被 SourceInventory lineage 追溯。
15. base CI 默认不启动真实外部 CLI agent。

## Documentation Requirements for Future Implementation

真正实现 CLI external coding agent bridge 前，必须同步更新：

- `docs/03-contracts/agent-action-protocol.md`：加入简化后的 `external_agent_run` action schema（动作模式）。
- `docs/03-contracts/event-stream-protocol.md`：加入 `external_agent.run.started/completed/failed` 事件类型。
- `docs/02-architecture/permission-and-sandbox-architecture.md`：加入 CLI sandbox（CLI 沙箱）、argv template（参数模板）、network boolean（网络布尔策略）和 import-time validation（导入时校验）。
- `docs/02-architecture/event-and-evidence-architecture.md`：加入 CLI external agent evidence import（CLI 外部智能体证据导入）映射。
- `docs/05-testing/testing-strategy.md`：加入 default-disabled external CLI agent gate（默认禁用外部 CLI 智能体门禁）。
- `docs/09-adr/`：如果选择特定 sandbox isolation（沙箱隔离）策略、允许真实外部 CLI 后端或改变事件协议语义，必须先写 ADR。

## Self-Review Result

- **Spec coverage（规格覆盖）**：已覆盖 P2-003 backlog 要求的 evidence import protocol（证据导入协议）和 permission boundary（权限边界），并收敛到 CLI 单一请求黑盒执行方案。
- **Over-design removal（过度设计移除）**：已移除 action input 中的 target paths（目标路径）、command ids（命令标识）、network policy reference（网络策略引用）、external step budget（外部步数预算）和 output contract（输出契约）；已移除 profile 中的 allowed tools（允许工具）、command policy reference（命令策略引用）和 transcript policy（会话记录策略）；已移除 evidence package 中的 command results（命令结果）。
- **CLI-specific additions（CLI 特定补充）**：已加入 `cli_executable`、`cli_args_template`、`allow_network`、`exit_code`、`stderr`、CLI 参数注入防护、CLI 超时/非零退出/输出截断失败语义，以及 stdout/stderr 脱敏规则。
- **Boundary check（边界检查）**：本规格不实现外部 CLI runner，不新增代码，不改变当前 `AgentRuntimePort`，不声明 M5 exit criteria 已满足。
- **No-fallback check（无降级检查）**：明确禁止 CLI 缺失时换可执行文件、沙箱不可用时在真实 workspace 运行、非零退出码伪成功、输出超限丢弃后继续成功、网络禁用不可执行时放行、hash 不匹配采信摘要、secret scan 失败仍导入。
- **Governance check（治理边界检查）**：明确禁止 `ticket_completed`、`closeout_committed`、`evidence_verified`、`source_inventory_accepted` 等治理字段。
