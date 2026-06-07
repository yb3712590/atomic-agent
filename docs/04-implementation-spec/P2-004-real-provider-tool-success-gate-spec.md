# P2-004 Real Provider Tool Success Gate Specification

## Status

draft

## Purpose

本文定义 P2-004 `real provider tool success gate`（真实供应商工具成功门禁）的功能规格。P2-002 `real provider minimal integration gate`（真实供应商最小集成门禁）已经证明 OpenAI-compatible provider（OpenAI 兼容供应商）接入路径、streaming（流式响应）、event stream（事件流）和 fail-closed（失败关闭）语义可审计；但 P2-002 允许 Outcome C（供应商响应失败关闭）作为通过结果，不能证明真实 provider 能成功驱动 `AgentLoop`（智能体循环）完成基础工具能力。

P2-004 的目标是新增一批默认禁用、显式启用的真实 provider success tests（成功型真实供应商测试），验证 provider 在独立小任务中能自主规划并成功输出 provider-agnostic `AgentAction`（供应商无关智能体动作），由 runtime（运行时）执行基础工具并最终 `run.completed`（运行完成）。

## Scope

P2-004 覆盖以下能力：

- 新增 `real_provider_tool_success` pytest marker（真实供应商工具成功 pytest 标记）。
- 新增显式启用变量 `ATOMIC_AGENT_RUN_REAL_PROVIDER_TOOL_SUCCESS=1`，避免与 P2-002 的 fail-closed gate（失败关闭门禁）混淆。
- 允许复用 P2-002 Task 7 的本地 ignored config（被 Git 忽略的本地配置）文件 `.env.real-provider-test-p2-002-task7` 中的 provider config（供应商配置）变量；该文件仍不得进入 git。
- 新增独立 pytest case（独立测试用例），覆盖：
  - `write_file`（写文件）
  - `read_file`（读文件）
  - `list_files`（列文件）
  - `apply_patch`（应用补丁）
  - `run_command`（运行声明命令）
  - `submit_result`（提交结果）
- 每个 case 使用独立 `AgentInvocation`（智能体调用请求）、workspace fixture（工作区夹具）、event stream path（事件流路径）和 artifact root（产物根目录）。
- 每个 case 允许 provider 自主规划动作顺序；test prompt（测试提示）只能强约束目标和协议，不采用 guided two-turn（引导式两轮）固定脚本。
- 每个 case 必须成功终止为 `run.completed`，不得把空输出、parse failure（解析失败）、provider failure（供应商失败）、permission denied（权限拒绝）、tool failure（工具失败）或 Outcome C 计为通过。
- 每个 case 必须验证 event stream integrity（事件流完整性）和 evidence summary（证据摘要）可构建。

不包含：

- 不修改 P2-002 的 Outcome A/B/C 语义。
- 不把 success gate 加入默认 `python -m pytest -q` 的联网路径。
- 不实现 provider registry（供应商注册表）、multi-provider routing（多供应商路由）或 native tool calling（原生工具调用）。
- 不实现 Anthropic/Claude provider adapter（Anthropic/Claude 供应商适配器）。
- 不要求 provider 完成端到端 mini project（小项目）或大型 coding task（编码任务）。
- 不把 provider output（模型输出）单独作为 implementation evidence（实现证据）。
- 不改变 Boardroom OS（Boardroom 操作系统）治理事实源边界。

## Test Shape

P2-004 应采用 hybrid explicit tests + shared runner（显式测试函数 + 共享运行器）设计：

- 每个工具能力有独立测试函数，便于单独运行和定位失败。
- 共享 `RealProviderToolCase`（真实供应商工具用例）描述 case 的 fixture、enabled tools（启用工具）、command policy（命令策略）、required events（必需事件）和 success assertions（成功断言）。
- 共享 runner 负责读取显式环境变量、构造 `AgentInvocation`、运行 `AgentLoop`、验证 `AgentRunResult`、event stream 和 evidence summary。

建议测试文件：

- `tests/test_real_provider_tool_success.py`

建议核心 helper（测试辅助函数 / 类型）：

- `RealProviderToolCase`
- `require_real_provider_tool_success_enabled()`
- `provider_config_from_env()`
- `run_real_provider_tool_case(case, tmp_path)`
- `assert_real_provider_tool_success(case, result, event_stream_path, workspace)`

## Required Environment

默认命令必须 skip（跳过）：

```bash
python -m pytest tests/test_real_provider_tool_success.py -q
```

显式启用命令：

```bash
set -a
source .env.real-provider-test-p2-002-task7
set +a
ATOMIC_AGENT_RUN_REAL_PROVIDER_TOOL_SUCCESS=1 \
python -m pytest tests/test_real_provider_tool_success.py -m real_provider_tool_success -q
```

Required env vars（必需环境变量）：

```text
ATOMIC_AGENT_RUN_REAL_PROVIDER_TOOL_SUCCESS=1
ATOMIC_AGENT_REAL_PROVIDER_BASE_URL
ATOMIC_AGENT_REAL_PROVIDER_API_KEY
ATOMIC_AGENT_REAL_PROVIDER_MODEL
```

Optional env vars（可选环境变量，复用 P2-002 Task 7）：

```text
ATOMIC_AGENT_REAL_PROVIDER_CONTEXT_WINDOW_TOKENS=400000
ATOMIC_AGENT_REAL_PROVIDER_MAX_OUTPUT_TOKENS=128000
ATOMIC_AGENT_REAL_PROVIDER_STREAM_IDLE_TIMEOUT_SECONDS=30
ATOMIC_AGENT_REAL_PROVIDER_TOTAL_TIMEOUT_SECONDS=3600
ATOMIC_AGENT_REAL_PROVIDER_MAX_STEPS=100
ATOMIC_AGENT_REAL_PROVIDER_TEMPERATURE=0.7
ATOMIC_AGENT_REAL_PROVIDER_LABEL=
```

P2-004 implementation（实现）不得把真实 API key（接口密钥）或真实 base URL（基础 URL）写入 tracked docs（被 Git 跟踪的文档）、events（事件）、artifacts（产物）、stdout/stderr（标准输出/错误）或 test failure output（测试失败输出）。README / docs 只能使用 placeholder（占位符）示例。

## Tool Cases

### write_file success

- Workspace fixture：空 `work/` 目录。
- Enabled tools：`write_file`, `submit_result`。
- Task：要求 provider 自主使用 `write_file` 创建 `work/write-success.txt`，内容包含稳定短语 `real provider write success`，然后 `submit_result`。
- Required outcome：
  - `tool.attempt.completed` with tool `write_file`
  - `workspace.mutation.recorded`
  - produced path lineage（产出路径谱系）为 `traceable`
  - `run.completed`

### read_file success

- Workspace fixture：预置 `work/read-input.txt`，内容包含稳定短语 `read fixture token`。
- Enabled tools：`read_file`, `submit_result`。
- Task：要求 provider 自主使用 `read_file` 读取该文件，再 `submit_result`，summary（摘要）必须提到读取到的稳定短语。
- Required outcome：
  - `tool.attempt.completed` with tool `read_file`
  - observation artifact（观察产物）包含文件内容或其可见片段
  - `run.completed`

### list_files success

- Workspace fixture：预置 `work/list-a.txt` 和 `work/nested/list-b.txt`。
- Enabled tools：`list_files`, `submit_result`。
- Task：要求 provider 自主使用 `list_files` 列出 `work/`，再 `submit_result`，summary 必须提到至少一个预置文件。
- Required outcome：
  - `tool.attempt.completed` with tool `list_files`
  - observation artifact 包含预置路径
  - `run.completed`

### apply_patch success

- Workspace fixture：预置 `work/patch-target.txt`，内容为 `before patch`。
- Enabled tools：`apply_patch`, `submit_result`。
- Task：要求 provider 自主使用 `apply_patch` 把 `before patch` 改为 `after patch`，再 `submit_result`。
- Required outcome：
  - `tool.attempt.completed` with tool `apply_patch`
  - `workspace.mutation.recorded`
  - 文件最终内容为 `after patch`
  - produced path lineage 为 `traceable`
  - `run.completed`

### run_command success

- Workspace fixture：预置 `work/command-input.txt`，内容为 `command ok`。
- Enabled tools：`run_command`, `submit_result`。
- Command policy：声明 command_id `check-command-input`，执行固定 Python command，读取 `work/command-input.txt`，内容等于 `command ok` 时 exit code `0`。
- Task：要求 provider 自主使用 `run_command` with `command_id=check-command-input`，再 `submit_result`。
- Required outcome：
  - `tool.attempt.completed` with tool `run_command`
  - `command.completed` with exit code `0`
  - stdout/stderr artifact hash（命令输出产物哈希）存在
  - `run.completed`

### submit_result success

- Workspace fixture：空 workspace。
- Enabled tools：`submit_result`。
- Task：要求 provider 在无需其它工具时直接 `submit_result`，summary 必须为非空字符串。
- Required outcome：
  - `result.submitted`
  - `run.completed`
  - no `tool.attempt.started`

## Success Criteria

P2-004 完成必须满足：

1. `python -m pytest -q` 不要求真实 provider credentials（真实供应商凭据），不发起真实 provider 网络调用。
2. `python -m pytest tests/test_real_provider_tool_success.py -q` 在未启用 `ATOMIC_AGENT_RUN_REAL_PROVIDER_TOOL_SUCCESS=1` 时 skip。
3. 显式启用后，每个独立 tool success case 必须 `run.completed`；任何 Outcome C、空响应、parse failure、permission/tool failure 都必须 fail。
4. 每个 case 必须验证 event stream integrity 和 `AgentRunResult.events_hash` 一致。
5. 每个涉及 produced path（产出路径）的 case 必须验证 evidence summary 中 source inventory lineage（源码清单谱系）为 `traceable`。
6. `run_command` case 必须验证 `command.completed` exit code 为 `0`，并验证 stdout/stderr artifacts（命令输出产物）带 sha256。
7. 测试和文档不得泄露 API key 或真实 provider URL。
8. P2-004 不改变 P2-002 fail-closed gate 的验收语义。

## Failure Semantics

P2-004 是 success gate（成功门禁）：

- missing credentials（缺失凭据）或 test config missing（测试配置缺失）：启用后必须 fail，默认未启用时 skip。
- provider empty output（供应商空输出）：fail。
- provider non-JSON / invalid action（非 JSON / 无效动作）：fail。
- provider directly submits result while target tool was required（需要目标工具时直接提交）：fail。
- permission denied / tool failed（权限拒绝 / 工具失败）：fail。
- event stream invalid（事件流无效）：fail。
- evidence summary invalid（证据摘要无效）：fail。

## Documentation Requirements

实现通过后必须同步更新：

- `docs/05-testing/testing-strategy.md`：记录 `real_provider_tool_success` marker、启用变量、复用 P2-002 Task 7 provider config、success-only 语义和默认 skip 行为。
- `docs/04-implementation-backlog/backlog.md`：P2-004 验证通过后标记 completed。
- `docs/04-implementation-spec/INDEX.md`、`docs/04-implementation-plan/INDEX.md` 和 `docs/INDEX.md`：按文档状态维护 active / completed 指针。

## Self-Review

- **Coverage（覆盖）**：本规格覆盖完整基础工具成功门禁、独立测试用例、自主 provider planning（供应商自主规划）、默认 skip、显式成功语义和文档收尾。
- **No placeholders（无占位）**：本文不含待填占位符或未定义验收项。
- **Boundary（边界）**：本文不改变 P2-002，不引入 P2-003 外部编码智能体桥接，不引入 native tool calling 或 provider registry。
- **Safety（安全）**：本文要求 no credential leakage（不泄露凭据）、no mock success path（不模拟成功路径）、no silent fallback（不静默降级）。
