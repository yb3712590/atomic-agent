# Fake Provider Loop Acceptance and Minimal Example Specification

## Status

implemented

## Purpose

本文定义 P1-003 `fake provider loop acceptance`（假模型供应商循环验收）和 `minimal example`（最小示例）的实现规格。该能力负责把现有库级 `AgentLoop`（智能体循环）能力固化为一个真实可运行、可审计、可文档化的 standalone example（独立示例）：使用 deterministic fake provider（确定性假模型供应商）触发真实工具调用、真实命令执行、真实事件流和真实产物输出。

P1-003 的目标不是证明真实模型能力，也不是新增通用 CLI framework（命令行框架）；目标是消除 README 中“尚无可运行 minimal example（最小示例）”的缺口，并在不使用 mock success path（模拟成功路径）的前提下证明 MVP runtime（最小可行运行时）的核心成功路径。

## Scope

P1-003 覆盖以下能力：

- 新增一个可通过 `python -m atomic_agent.examples.minimal_fake_loop` 运行的 example module（示例模块）。
- example（示例）必须构造完整 `AgentInvocation`（智能体调用请求），并把所有 runtime configuration（运行时配置）作为显式对象传给 `AgentLoop`（智能体循环）。
- example 必须使用 deterministic fake provider（确定性假模型供应商）输出固定 JSON `AgentAction`（智能体动作），用于证明 runtime semantics（运行时语义），不得声称是真实 provider（模型供应商）能力。
- example 必须真实执行 filesystem tools（文件系统工具）、`run_command`（声明命令执行）和 `submit_result`（提交结果）。
- example 必须产生真实 JSONL event stream（JSONL 事件流）、artifact files（产物文件）和 `AgentRunResult`（智能体运行结果）JSON。
- example 必须演示一次 command failure observation（命令失败观察）进入下一轮，并由后续 `apply_patch`（应用补丁）修复。
- README minimal example（最小示例）章节只能在该命令真实跑通后更新为真实命令和真实输出说明。
- 使用 subprocess（子进程）测试真实 CLI execution（命令行执行），不能只调用内部函数伪装成功。

不包含：

- 不实现 real provider integration（真实模型供应商集成）。
- 不实现 Boardroom `AgentRuntimePort adapter`（Boardroom 智能体运行时端口适配器）。
- 不新增长期配置系统、`.env` 读取、environment variables（环境变量）读取或默认配置 fallback（兜底）。
- 不新增任意 shell（自由命令行）能力；example 中命令必须通过 declared `command_id`（声明命令标识）执行。
- 不新增网络能力；P1-003 不修改 `web_fetch`（网络获取）语义。
- 不修改 runtime（运行时）完成语义让失败看起来成功。
- 不提交 git commit（提交），除非用户另行明确要求。

## Authoritative Inputs

本规格依据以下已索引文档：

- `docs/04-implementation-backlog/backlog.md`（实现待办），其中 P1-003 为 pending（待处理）任务。
- `docs/04-implementation-spec/mvp-runtime-spec.md`（MVP 运行时规格），要求受控 `AgentLoop` 能接收结构化任务、调用 provider、执行工具、反馈 observation（观察结果）、记录 event stream（事件流）并提交结果或 fail closed（失败关闭）。
- `docs/04-implementation-acceptance/mvp-acceptance.md`（MVP 验收标准），要求至少一个多步 `AgentLoop`、读取/写入/运行声明命令、输出 `AgentRunResult` 和真实事件流。
- `docs/05-testing/testing-strategy.md`（测试策略），定义 fake provider loop tests（假模型供应商循环测试）推荐场景。
- `README.md`（项目入口），当前声明尚无真实 minimal example（最小示例），并禁止 mock success path（模拟成功路径）。
- `docs/03-contracts/agent-action-protocol.md`（智能体动作协议），定义 JSON `AgentAction`（智能体动作）协议。
- `docs/03-contracts/event-stream-protocol.md`（事件流协议），定义 runtime event（运行时事件）语义。
- `docs/09-adr/0003-use-fail-closed-permission-model.md`（失败关闭权限模型 ADR）。

## CLI Contract

P1-003 完成后，仓库必须支持以下源码树真实命令形态：

```bash
PYTHONPATH=src python -m atomic_agent.examples.minimal_fake_loop \
  --run-id minimal_example \
  --workspace /tmp/atomic-agent-minimal/workspace \
  --event-stream /tmp/atomic-agent-minimal/events/events.jsonl \
  --artifact-root /tmp/atomic-agent-minimal/artifacts \
  --result /tmp/atomic-agent-minimal/result.json
```

字段语义：

| Argument | 中文解释 | 约束 |
|---|---|---|
| `--run-id` | 运行标识 | 必填，非空字符串；用于 `AgentLoopConfig`（智能体循环配置）、`EventRecorder`（事件记录器）和 artifact ref prefix（产物引用前缀）。 |
| `--workspace` | 工作区根目录 | 必填；可以不存在，example 会创建；`work/output.txt` 如果已存在必须 fail closed，避免覆盖用户内容。 |
| `--event-stream` | JSONL 事件流路径 | 必填；父目录可以不存在，example 会创建；文件如存在必须为空或不存在，避免追加到旧事件流。 |
| `--artifact-root` | 产物根目录 | 必填；可以不存在，example 会创建；目录如存在必须为空，避免覆盖旧产物。 |
| `--result` | `AgentRunResult` JSON 输出路径 | 必填；父目录可以不存在，example 会创建；文件如已存在必须 fail closed，避免覆盖用户内容。 |

CLI 成功时：

- process exit code（进程退出码）必须为 `0`。
- stdout（标准输出）必须是单个 JSON object（JSON 对象），至少包含：

```json
{
  "status": "completed",
  "result_path": "/tmp/atomic-agent-minimal/result.json",
  "event_stream_path": "/tmp/atomic-agent-minimal/events/events.jsonl",
  "artifact_root": "/tmp/atomic-agent-minimal/artifacts",
  "workspace_output_path": "/tmp/atomic-agent-minimal/workspace/work/output.txt"
}
```

CLI 输入校验失败时：

- process exit code 必须为 `2`。
- stderr（标准错误）必须是单个 JSON object，包含 `status="failed"` 和 `error` 字段。
- 不得创建 misleading success output（误导性成功输出）。

CLI 运行时如果 `AgentLoop` 返回 failed `AgentRunResult`（失败运行结果）：

- 必须写出真实 `AgentRunResult` JSON。
- process exit code 必须为 `1`。
- stdout 必须标记 `status="failed"`。
- 不得把 failed result（失败结果）改写为 completed（完成）。

## Example Scenario

P1-003 的 deterministic fake provider（确定性假模型供应商）必须输出以下动作序列：

| Step | Action | 中文解释 | 期望事实 |
|---|---|---|---|
| 1 | `write_file` | 写入初始文件 | 在 allowed write set（允许写入集合）内写 `work/output.txt`，内容为 `draft`，记录 workspace mutation（工作区变更）。 |
| 2 | `run_command` | 运行声明命令 | 执行 `command_id="check-output"`；真实命令读取 `work/output.txt`，因内容不是 `fixed` 而返回 exit code `3`；该失败作为 observation 反馈给 provider context（模型上下文）。 |
| 3 | `apply_patch` | 修复文件 | 将 `draft` 改为 `fixed`，记录第二个 workspace mutation。 |
| 4 | `run_command` | 再次运行声明命令 | 同一个 `command_id="check-output"` 返回 exit code `0`，证明修复后命令真实通过。 |
| 5 | `submit_result` | 提交结果 | 返回 summary（摘要）、produced paths（产出路径）和 evidence refs（证据引用），记录 `result.submitted` 与 `run.completed`。 |

命令策略要求：

- `check-output` 必须通过 `CommandPolicy`（命令策略）声明。
- `CommandSpec.argv`（命令参数）第一个元素必须是当前 Python executable（Python 可执行文件）的绝对路径。
- 不得使用 `shell=True`、`command`、`cmd` 或 `shell` 字段。
- 命令必须在 workspace root（工作区根目录）内运行，并读取相对路径 `work/output.txt`。

## Output and Evidence Requirements

成功运行必须产生：

- `AgentRunResult` JSON，字段至少包含：
  - `run_id`
  - `status="completed"`
  - `event_stream_ref`
  - `events_hash`
  - `tool_attempts`
  - `workspace_mutations`
  - `artifacts`
  - `summary`
- JSONL event stream（JSONL 事件流），至少包含：
  - `run.started`
  - `provider.turn.started`
  - `provider.turn.completed`
  - `action.parsed`
  - `permission.decided`
  - `tool.attempt.started`
  - `tool.attempt.completed`
  - `workspace.mutation.recorded`
  - `command.completed`
  - `result.submitted`
  - `run.completed`
- artifact files（产物文件），至少包含：
  - provider outputs（模型输出产物）
  - observations（观察结果产物）
  - diffs（差异产物）
  - command stdout/stderr artifacts（命令标准输出/错误产物）
  - result artifact（结果产物）
- workspace file（工作区文件）：
  - `work/output.txt` 内容必须为 `fixed`。

事件验收细节：

- `command.completed` 事件的 exit code 序列必须是 `[3, 0]`。
- 每个 event（事件）的 `sequence` 必须连续递增。
- 每个 event（事件）必须包含 `event_hash`，并通过 `previous_event_hash` 串联。
- 如果发生文件变更，必须记录 `workspace.mutation.recorded`，并包含 before/after hash（变更前后哈希）和 diff artifact（差异产物）。

## Documentation Requirements

P1-003 实现完成且真实验证通过后，必须更新：

- `README.md`：将当前“尚未实现可运行 minimal example”的描述替换为真实可运行命令、输出路径说明和 fake provider（假模型供应商）边界说明。
- `docs/04-implementation-backlog/backlog.md`：将 P1-003 标记为 `completed`。
- `docs/04-implementation-spec/P1-003-fake-provider-loop-minimal-example-spec.md`：状态从 `draft` 改为 `implemented`。
- `docs/04-implementation-plan/P1-003-fake-provider-loop-minimal-example-plan.md`：状态从 `draft` 改为 `implemented`。
- `docs/04-implementation-spec/INDEX.md`：实现完成后将本规格移入 Completed / Archived Documents（已完成 / 已归档文档）。
- `docs/04-implementation-plan/INDEX.md`：实现完成后将对应 plan（实施计划）移入 Completed / Archived Documents。
- `docs/INDEX.md`：如果本规格或计划作为全局 active pointer（当前活跃指针）加入，则实现完成后必须移除对应 draft pointer（草案指针）。

P1-003 不更新 `docs/05-testing/testing-strategy.md`，除非实现过程中发现 fake provider loop acceptance（假模型供应商循环验收）定义需要长期调整。现有 testing strategy（测试策略）已包含推荐场景。

## Security and No-Fallback Rules

- example 不得读取 `.env`、environment variables（环境变量）、local config files（本地配置文件）或 process defaults（进程默认值）来补齐 `AgentInvocation`（智能体调用请求）。
- example 必须显式构造 `AgentInvocation`，并将完整配置传入 runtime（运行时）。
- example 不得把 provider 输出文本直接当作完成证据；必须通过 tool attempt（工具调用尝试）、workspace mutation（工作区变更）、command result（命令结果）和 artifact refs（产物引用）证明。
- example 不得在 command failure（命令失败）后伪造成功；必须让失败进入 observation（观察结果），再由后续 action（动作）修复。
- example 不得自动放宽 allowed write set（允许写入集合）。
- example 不得在 `--result` 已存在、`--artifact-root` 非空或 `work/output.txt` 已存在时覆盖用户文件。
- example 不得使用 free shell string（自由 shell 字符串）、`shell=True` 或未声明命令。
- README 不得把 deterministic fake provider（确定性假模型供应商）描述为 real provider（真实模型供应商）能力。
- 测试不得只调用内部 Python 函数证明成功；必须用 subprocess 执行真实 module command（模块命令）。

## Acceptance Criteria

P1-003 完成时必须证明：

- `PYTHONPATH=src python -m atomic_agent.examples.minimal_fake_loop --run-id ... --workspace ... --event-stream ... --artifact-root ... --result ...` 真实执行并返回 exit code `0`。
- CLI stdout 是可解析 JSON，并包含真实输出路径。
- `--result` 指向的 `AgentRunResult` JSON 可解析，且 `status == "completed"`。
- workspace 中 `work/output.txt` 内容为 `fixed`。
- JSONL event stream 可逐行解析。
- event stream 包含 provider turn、action、permission、tool attempt、workspace mutation、command result、result submission 和 terminal completion events（终止完成事件）。
- `command.completed` exit code 序列为 `[3, 0]`。
- result JSON 的 `events_hash` 使用 `sha256:<64 hex>` 格式。
- result JSON 的 `workspace_mutations` 至少包含两条针对 `work/output.txt` 的 mutation（变更）。
- artifact root 中存在 provider、observations、diffs、commands 和 results 相关产物。
- CLI 在 `--result` 已存在时返回 exit code `2`，并且不覆盖原文件。
- CLI 在 `--artifact-root` 非空时返回 exit code `2`，并且不覆盖旧产物。
- CLI 在 workspace 已存在 `work/output.txt` 时返回 exit code `2`，并且不覆盖原文件。
- `python -m pytest tests/test_minimal_fake_loop_example.py -q` 通过。
- `python -m pytest -m permission_negative -q` 通过。
- `python -m pytest -q` 通过。
- README minimal example（最小示例）命令与真实验证命令一致。
- runtime source（运行时代码）没有新增 `.env`、`os.environ`、`getenv`、`dotenv`、`shell=True` 或默认 allow-all（默认全允许）模式。

## Self-Review Result

- Spec coverage（规格覆盖）：已覆盖 backlog P1-003、README minimal example 缺口、MVP acceptance 中多步 AgentLoop/真实工具/真实命令/真实结果要求、testing strategy 的 fake provider loop 推荐场景，以及文档更新要求。
- Placeholder scan（占位符扫描）：未使用占位标记、未完成提示或“稍后补充”措辞；每项验收均给出可验证事实。
- Type / naming consistency（类型与命名一致性）：`AgentInvocation`、`AgentRunResult`、`AgentLoop`、`AgentAction`、`EventRecorder`、`ArtifactWriter`、`CommandPolicy`、`CommandSpec`、`tool.attempt.completed`、`workspace.mutation.recorded`、`command.completed` 命名与现有代码和契约一致。
- Scope check（范围检查）：未纳入 real provider integration、Boardroom adapter、新权限系统、新工具类型、网络扩展或任意 shell。
- No-fallback check（无兜底检查）：明确禁止环境读取补齐、默认 allow-all、覆盖用户文件、命令失败伪成功、provider 文本伪证据和 README 伪命令。
