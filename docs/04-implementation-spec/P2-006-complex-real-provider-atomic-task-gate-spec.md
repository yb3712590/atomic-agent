# P2-006 Complex Real Provider Atomic Task Gate Specification

## Status

draft

## Purpose

本文定义 P2-006 `complex real provider atomic task gate`（复杂真实供应商原子任务门禁）的功能规格。P2-004 已用六个独立小 case 证明真实 provider（真实供应商）能成功驱动基础工具；P2-006 进一步验证真实 provider 能在一个稍复杂但仍原子化的任务中，组合多种基础能力，基于 command observation（命令观察）迭代修复，并输出可审计 evidence（证据）。

P2-006 不证明模型能完成大型软件项目，也不替代 future external coding agent bridge（未来外部编码智能体桥接）。它是 manual/nightly/soak gate（手动/夜间/浸泡门禁），用于验证 runtime（运行时）、provider adapter（供应商适配器）、tool execution（工具执行）、event stream（事件流）和 evidence mapping（证据映射）在更长真实任务中的稳定性。

## Scope

P2-006 采用 evidence repair task（证据修复任务）方案：测试夹具预置一个小型 broken Python project（破损 Python 小项目），真实 provider 必须阅读说明、运行声明测试、定位失败、修复源码或报告生成逻辑、再次运行验证命令，并提交结果。

覆盖工具：

- `list_files`（列文件）
- `read_file`（读文件）
- `search_files`（搜索文件）
- `apply_patch`（应用补丁）
- `write_file`（写文件）
- `run_command`（运行声明命令）
- `submit_result`（提交结果）

不包含：

- 不接入外部 coding agent（编码智能体）。
- 不实现 service runner（服务运行器）或 HTTP probe（HTTP 探测）。
- 不要求 100 steps 必须被消耗完；100 是 budget ceiling（预算上限）。
- 不把 provider summary（供应商摘要）单独作为通过依据。
- 不允许修改测试 fixture 来伪造通过，除非 fixture 明确属于待修复源码范围。
- 不进入默认 base CI（基础持续集成）。

## Required Environment

新增 pytest marker（pytest 标记）：

```text
real_provider_complex_task
```

显式启用变量：

```text
ATOMIC_AGENT_RUN_REAL_PROVIDER_COMPLEX_TASK=1
```

该 gate 可复用 P2-005/P2-004 的 provider config（供应商配置）变量：

```text
ATOMIC_AGENT_REAL_PROVIDER_BASE_URL
ATOMIC_AGENT_REAL_PROVIDER_API_KEY
ATOMIC_AGENT_REAL_PROVIDER_MODEL
ATOMIC_AGENT_REAL_PROVIDER_CONTEXT_WINDOW_TOKENS
ATOMIC_AGENT_REAL_PROVIDER_MAX_OUTPUT_TOKENS
ATOMIC_AGENT_REAL_PROVIDER_STREAM_IDLE_TIMEOUT_SECONDS
ATOMIC_AGENT_REAL_PROVIDER_TOTAL_TIMEOUT_SECONDS
ATOMIC_AGENT_REAL_PROVIDER_MAX_STEPS
ATOMIC_AGENT_REAL_PROVIDER_TEMPERATURE
ATOMIC_AGENT_REAL_PROVIDER_LABEL
ATOMIC_AGENT_REAL_PROVIDER_REASONING_EFFORT
```

Recommended defaults（建议默认值）：

```text
ATOMIC_AGENT_REAL_PROVIDER_MAX_STEPS=100
ATOMIC_AGENT_REAL_PROVIDER_TOTAL_TIMEOUT_SECONDS=600
ATOMIC_AGENT_REAL_PROVIDER_STREAM_IDLE_TIMEOUT_SECONDS=30
ATOMIC_AGENT_REAL_PROVIDER_REASONING_EFFORT=high
```

这些默认值只应在 integration harness（集成测试驱动）中作为显式默认配置，不得在 runtime core（运行时核心）中硬编码。

## Test Fixture Shape

建议测试文件：

```text
tests/test_real_provider_complex_task.py
```

测试应在 `tmp_path` 中生成 workspace（工作区），不依赖仓库外状态。建议 fixture：

```text
work/
  README.md
  data/
    orders.json
    users.json
  src/
    report.py
    validator.py
  tests/
    test_report.py
  expected/
    report.txt
```

### Fixture Complexity Guidelines

测试夹具应足够小，可以在一个开发会话中人工审查；也要足够复杂，迫使 provider 组合使用多种工具，而不是直接猜答案。建议范围：

- source code（源码）总量：50-150 行，不包含 tests/data。
- related bugs（相关缺陷）：1-3 个，必须服务同一个 report-generation goal（报告生成目标），不要设计成互不相关的十个小 bug。
- failing tests（失败测试）：3-5 个 deterministic assertions（确定性断言）。
- data files（数据文件）：小型 JSON fixture（测试夹具），单文件建议保持在几 KB 以内。
- expected provider path（预期供应商路径）：`list/read/search -> failing command -> patch/write -> passing command -> submit`。
- expected provider turns（预期供应商轮次）：约 20-50 轮；`max_steps=100` 只作为余量。

如果真实 provider 在少于 10 轮内稳定完成，fixture 可能太简单；如果 high reasoning effort（高推理强度）下仍频繁接近 100 轮失败，fixture 可能太难或 prompt/validation（提示/验证）设计不清。

### Broken Behavior

`work/src/report.py` 初始存在一个真实 bug（真实缺陷），例如：

- 漏掉 cancelled orders（取消订单）过滤。
- 金额聚合使用字符串拼接而非数值求和。
- user id 到 user name 映射错误。
- 输出排序不稳定。

`work/tests/test_report.py` 或 `work/src/validator.py` 必须 deterministic（确定性），能通过声明命令发现失败。

### Allowed Mutation Boundary

`allowed_write_set` 应限制为：

```text
work/src/
work/output/
```

不建议允许写入 `work/tests/` 或 `work/expected/`，避免 provider 通过改测试或 expected output（期望输出）伪造成功。

如果需要 provider 写 summary file（摘要文件），允许：

```text
work/output/repair-summary.md
work/output/report.txt
```

## Command Policy

至少声明两个 command_id（命令标识）：

| command_id | 目的 | 期望 |
|---|---|---|
| `run-tests` | 运行 deterministic unit tests（确定性单元测试）或 validator（验证器） | 初始失败，修复后成功 |
| `validate-report` | 验证最终 report 内容和 schema（模式） | 修复后 exit code 0 |

命令必须：

- 使用固定 absolute Python executable（绝对 Python 可执行文件）。
- `shell=False`。
- 不允许网络。
- cwd 限制在 workspace root。
- stdout/stderr 必须进入 artifacts，并带 sha256。

## Task Prompt Requirements

Prompt（提示）必须强约束目标和协议，但不能写成 guided script（引导脚本）。允许说明：

- 你可以使用 `list_files`、`read_file`、`search_files` 理解项目。
- 必须至少运行一次 `run-tests` 观察失败。
- 修复后必须再次运行 `run-tests`，并运行 `validate-report`。
- 必须只修改 `work/src/` 和 `work/output/`。
- 最终 `submit_result.produced_paths` 必须包含：
  - `work/src/report.py`
  - `work/output/report.txt`
  - `work/output/repair-summary.md`

不允许：

- 固定每一轮必须调用哪个工具。
- 预先告诉 provider bug 的精确行号。
- 让 provider 只输出最终 JSON 文件而不执行工具。

## Success Criteria

P2-006 完成必须满足：

1. `python -m pytest tests/test_real_provider_complex_task.py -q` 默认 skip，不联网。
2. 显式启用后，真实 provider gate 必须以 `run.completed` 结束。
3. event stream integrity（事件流完整性）必须通过，且 `AgentRunResult.events_hash` 一致。
4. 至少出现一个 `provider.turn.completed`。
5. 至少出现以下工具的 `tool.attempt.completed`：
   - `list_files`
   - `read_file`
   - `run_command`
   - `submit_result` 通过 `result.submitted` 验证
6. 至少出现 `search_files`、`apply_patch`、`write_file` 中的两个工具成功事件。
7. `run-tests` 必须至少执行两次：
   - 至少一次 exit code 非 0。
   - 最后一次 exit code 为 0。
8. `validate-report` 最后一次 exit code 必须为 0。
9. 至少一个 workspace mutation（工作区变更）必须记录 before/after hash 和 diff artifact。
10. produced paths（产出路径）必须包含：
    - `work/src/report.py`
    - `work/output/report.txt`
    - `work/output/repair-summary.md`
11. produced paths 的 source inventory lineage（源码清单谱系）必须为 `traceable`。
12. command stdout/stderr artifacts 必须带 sha256。
13. 不得修改 `work/tests/`、`work/expected/` 或 `work/data/`。
14. provider failure、parse failure、permission denied、tool failure 或 Outcome C 都不能算通过。

## Step and Time Semantics

P2-006 目标是更复杂、更长链路的真实任务，但验收不应要求“恰好 100 步”或“必须运行 10 分钟”。合理语义：

- `max_steps=100` 是上限，不是通过条件。
- `total_timeout_seconds=600` 或更高是单 provider turn（供应商轮次）超时上限，不是必须耗满的时长。
- 如果 provider 用 15 步真实完成所有验证，应判定通过。
- 如果 provider 消耗很多步但没有满足 evidence / command / mutation 验收，应判定失败。

## Evidence Requirements

P2-006 的最终报告必须包含：

- event stream path（事件流路径）。
- result path（结果路径）。
- artifact root（产物根目录）。
- workspace output paths（工作区产物路径）。
- per-command exit code history（每个命令的退出码历史）。
- completed tools summary（已完成工具摘要）。
- source inventory lineage summary（源码清单谱系摘要）。
- provider config summary（供应商配置摘要），包括 `reasoning_effort`，但不包含 API key。

## Failure Semantics

P2-006 是 success-only complex gate（成功型复杂门禁）：

- 默认未启用：skip。
- 启用但缺 provider config：fail。
- provider 不支持 `reasoning_effort` 且用户显式配置：fail closed，不自动删除参数重试。
- provider 输出无效 action：fail。
- provider 试图写 `work/tests/`、`work/expected/`、`work/data/`：permission denied 并 fail。
- provider 修改测试或 expected output 不能算通过。
- command 失败后未修复并提交：fail。
- event stream / evidence summary invalid：fail。

## Relationship to P2-005

P2-006 应在 P2-005 后执行，原因：

- P2-006 需要 `reasoning_effort=high` 作为可配置 provider option。
- P2-006 的 provider config summary 需要记录 P2-005 暴露的高影响 provider options。
- 如果 `reasoning_effort` 或其他参数导致 provider 兼容性问题，应在 P2-005 的参数映射和 fail-closed 语义中先解决。

## Cost and Time Estimation

P2-006 预计显著高于 P2-004 的成本和耗时。由于 provider、model、pricing（定价）、`reasoning_effort` 支持和 hidden reasoning tokens（隐藏推理 token）都会变化，本规格不写死美元金额；实施和运行前应按以下维度估算：

- provider turns（供应商轮次）：预期 20-50，最大 100。
- prompt growth（提示增长）：每轮会携带 previous observations（前序观察），长 stdout/stderr 或文件内容会增加输入 token。
- output tokens（输出 token）：每轮通常只输出一个 action JSON，但 reasoning models 可能消耗 hidden reasoning tokens。
- command runtime（命令运行时间）：`run-tests` 和 `validate-report` 应保持秒级，避免把 gate 变成命令性能测试。
- provider latency（供应商延迟）：`reasoning_effort=high` 可能显著增加单轮延迟。

Recommended operating envelope（建议运行边界）：

```text
provider_turns_expected=20-50
provider_turns_max=100
wall_time_expected=3-10 minutes
base_ci=false
manual_or_nightly=true
```

如果 provider 支持 usage accounting（用量统计）并通过 P2-005 `stream_options` 暴露，测试报告可以记录实际 usage，但不得依赖 usage 字段作为成功证据。

## Known Limitations

- 复杂 gate 更像 soak/integration test（浸泡/集成测试），成本高、时间长、provider 波动大，不适合作为 base CI。
- 该 gate 证明 atomic-agent runtime 能承载复杂原子任务，不证明任意模型都能稳定完成任意编码任务。
- provider 可能少步完成任务；这不降低 gate 价值，只要 evidence criteria（证据标准）满足。
- provider 也可能因模型能力不足失败；失败应保留事件和证据，用于分析 provider/task 适配性，而不是在 atomic-agent 内部自动重试。

## Failure Diagnosis Guidelines

如果 P2-006 失败，应按以下顺序诊断，不要先改测试或放宽验收：

1. 检查 terminal status（终止状态）：
   - `provider_failed` 通常指向 provider/API/config（供应商/接口/配置）问题。
   - `action_parse_failed` 通常指向 invalid JSON、response truncation（响应截断）或不兼容 request options。
   - `policy_denied` 通常表示 provider 试图写入禁区，例如 `work/tests/`、`work/expected/` 或 `work/data/`。
2. 检查 command history（命令历史）：
   - `run-tests` 是否至少运行过一次并暴露初始失败？
   - `run-tests` 最后一次 exit code 是否为 0？
   - `validate-report` 是否运行，最后一次 exit code 是否为 0？
   - stdout/stderr 应通过 artifact path（产物路径）和 sha256 检查，不依赖 provider summary。
3. 检查 workspace mutations（工作区变更）：
   - 修改了哪些文件？
   - 是否只修改 `work/src/` 和 `work/output/`？
   - diff 是否对应 report-generation goal？
   - 是否存在 before/after hash 和 diff artifact？
4. 检查 provider loop behavior（供应商循环行为）：
   - 如果接近 `max_steps=100`，provider 可能陷入循环或 fixture 太难。
   - 如果很少轮次就失败，优先怀疑配置、prompt、parser 或 permission setup（权限设置）。
5. 检查 provider options（供应商参数）：
   - 如果显式配置 `reasoning_effort=high` 后 provider 不支持，应 fail closed，这是配置/兼容性问题。
   - 如果使用较低 effort 导致任务失败，是否重试更高 effort 应由 operator/scheduler（操作方/调度器）决定，不应由 atomic-agent 静默降级或自动重试。

## Documentation Requirements

实现通过后必须同步更新：

- `docs/05-testing/testing-strategy.md`：记录 `real_provider_complex_task` marker、启用变量、默认 skip、success-only 语义和成本/波动风险。
- `docs/04-implementation-backlog/backlog.md`：P2-006 验证通过后标记 completed。
- `docs/04-implementation-spec/INDEX.md` 和 `docs/INDEX.md`：按文档状态维护 active / completed 指针。
- README 可选更新：如果该 gate 成为推荐手动/夜间命令，再加入 README；否则仅放 testing strategy。

## Self-Review

- **Coverage（覆盖）**：本规格覆盖复杂真实 provider 原子任务、workspace fixture、权限边界、命令策略、事件/证据验收、失败语义和 P2-005 依赖。
- **No placeholders（无占位）**：测试 fixture、工具覆盖、命令和验收标准均已具体化。
- **Boundary（边界）**：不进入 external coding agent bridge，不要求 100 步作为硬通过条件，不进入 base CI。
- **Safety（安全）**：禁止改测试/expected/data 伪造成功，所有高风险行为通过 permission policy 和 evidence 验证。
