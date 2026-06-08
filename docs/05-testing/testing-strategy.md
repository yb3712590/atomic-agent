# Testing Strategy

## Status

active

## Purpose

本文定义 `atomic-agent`（原子智能体）的测试策略。测试目标不是证明模型总能一次成功，而是证明 runtime（运行时）语义、权限边界、事件记录和失败关闭行为可靠。

## Test Layers

| Layer | 中文解释 | 目标 |
|---|---|---|
| unit tests | 单元测试 | 验证 parser（解析器）、policy（策略）、path guard（路径守卫）等纯逻辑。 |
| tool tests | 工具测试 | 验证 filesystem、command、network 工具行为。 |
| contract tests | 契约测试 | 验证 `AgentInvocation`、`AgentAction`、`AgentEvent`、`AgentRunResult` schema。 |
| permission negative tests | 权限负向测试 | 验证越权写入、未声明命令、网络拒绝等 fail closed。 |
| fake provider loop tests | 假模型供应商循环测试 | 使用确定性 provider 证明 agent loop 语义。 |
| real provider integration tests | 真实模型供应商集成测试 | 验证最小真实 provider action loop。 |

## Fake Provider Tests

fake provider（假模型供应商）只能用于证明 runtime semantics（运行时语义），不能伪装真实模型能力。

推荐场景：

```text
turn 1 -> write_file allowed path
turn 2 -> run_command declared command -> fail
turn 3 -> read_file or apply_patch
turn 4 -> run_command -> pass
turn 5 -> submit_result
```

验收重点：

- 每一步都有事件。
- 文件变更有 hash 和 diff。
- 命令失败进入 observation。
- 后续动作可以基于 observation 修复。
- 最终结果不绕过 evidence（证据）。

## Negative Tests

必须覆盖：

- `../outside.md` 路径逃逸。
- symlink escape（符号链接逃逸）。
- 写入 allowed write set（允许写入集合）之外路径。
- 运行 `rm -rf .` 这种未声明 shell 字符串。
- 访问未允许 URL。
- provider 输出无效 JSON。
- provider 输出未知 action。
- 超过 max steps。
- observation 超长截断。

## Permission Negative Gate

P1-002 defines a focused permission negative gate（权限负向门禁）：

```bash
python -m pytest -m permission_negative -q
```

This gate covers fail-closed（失败关闭） behavior for path traversal（路径逃逸）、symlink escape（符号链接逃逸）、AllowedWriteSet（允许写入集合）、undeclared command（未声明命令）、free shell string（自由命令字符串）、network deny（网络拒绝）、missing network policy（缺失网络策略）、invalid provider JSON（无效模型 JSON）、unknown action（未知动作）、max steps（最大步数） and observation truncation（观察结果截断）.

The gate is not a replacement for the full suite:

```bash
python -m pytest -q
```

## Real Provider Tests

真实 provider（模型供应商）集成测试只验证最小路径，不要求模型完成大型项目。

最小要求：

- provider 至少输出一个合法 `AgentAction`（智能体动作）。
- runtime 执行动作并记录事件。
- 如果模型输出错误，runtime 能记录错误并 fail closed 或受限 retry。

P2-002 adds a default-disabled OpenAI-compatible real provider gate（OpenAI 兼容真实供应商门禁）。它只验证最小真实 provider action loop（供应商动作循环），不要求模型完成大型项目。

默认命令：

```bash
python -m pytest tests/test_real_provider_integration.py -q
```

默认结果必须是 skip（跳过），因为未设置：

```text
ATOMIC_AGENT_RUN_REAL_PROVIDER=1
```

显式启用命令：

```bash
ATOMIC_AGENT_RUN_REAL_PROVIDER=1 \
ATOMIC_AGENT_REAL_PROVIDER_BASE_URL="https://provider.example/v1" \
ATOMIC_AGENT_REAL_PROVIDER_API_KEY="replace-with-real-key" \
ATOMIC_AGENT_REAL_PROVIDER_MODEL="provider-model" \
python -m pytest tests/test_real_provider_integration.py -m real_provider -q
```

Required env vars（必需环境变量）：

```text
ATOMIC_AGENT_RUN_REAL_PROVIDER=1
ATOMIC_AGENT_REAL_PROVIDER_BASE_URL
ATOMIC_AGENT_REAL_PROVIDER_API_KEY
ATOMIC_AGENT_REAL_PROVIDER_MODEL
```

Optional env vars（可选环境变量）：

```text
ATOMIC_AGENT_REAL_PROVIDER_CONTEXT_WINDOW_TOKENS=400000
ATOMIC_AGENT_REAL_PROVIDER_MAX_OUTPUT_TOKENS=128000
ATOMIC_AGENT_REAL_PROVIDER_STREAM_IDLE_TIMEOUT_SECONDS=30
ATOMIC_AGENT_REAL_PROVIDER_TOTAL_TIMEOUT_SECONDS=3600
ATOMIC_AGENT_REAL_PROVIDER_MAX_STEPS=4
ATOMIC_AGENT_REAL_PROVIDER_TEMPERATURE=0.2
ATOMIC_AGENT_REAL_PROVIDER_LABEL=boardroom-os-real-provider
ATOMIC_AGENT_REAL_PROVIDER_REASONING_EFFORT=high
ATOMIC_AGENT_REAL_PROVIDER_TOP_P=1.0
ATOMIC_AGENT_REAL_PROVIDER_PRESENCE_PENALTY=0.0
ATOMIC_AGENT_REAL_PROVIDER_FREQUENCY_PENALTY=0.0
ATOMIC_AGENT_REAL_PROVIDER_SEED=20260608
ATOMIC_AGENT_REAL_PROVIDER_STOP=
ATOMIC_AGENT_REAL_PROVIDER_RESPONSE_FORMAT_JSON='{"type":"json_object"}'
ATOMIC_AGENT_REAL_PROVIDER_STREAM_OPTIONS_JSON='{"include_usage":true}'
ATOMIC_AGENT_REAL_PROVIDER_SERVICE_TIER=
ATOMIC_AGENT_REAL_PROVIDER_USER=atomic-agent-boardroom-os
```

这些 P2-005 provider options（供应商参数）是 explicit local/manual profile（显式本地/手动配置画像），不是 runtime core default（运行时核心默认值）。如果目标 OpenAI-compatible provider（OpenAI 兼容供应商）不支持显式参数，gate 必须 fail closed（失败关闭），不得 silent retry（静默重试）移除参数。`stream_options={"include_usage":true}` 只提供 usage accounting（用量统计）审计上下文，不是成功证据。真实 API key（接口密钥）和真实 base URL（基础地址）不得进入 tracked docs（被 Git 跟踪文档）、`.env.template`、event stream（事件流）或 artifacts（产物）。

Accepted outcomes（可接受结果）：

1. Outcome A：provider stream（供应商流）返回合法 JSON action（JSON 动作），runtime 执行至少一个工具，event stream（事件流）以 `run.completed` 结束，evidence summary（证据摘要）可构建。
2. Outcome B：provider 返回合法 action 但模型行为偏离；event stream integrity（事件流完整性）必须可验证，evidence summary 不得把缺失 lineage（谱系）伪装为 traceable（可追溯）。
3. Outcome C：provider SDK path（SDK 路径）已到达，但 response（响应）为空、截断、无法提取内容或无法解析为 action；runtime 必须 fail closed（失败关闭），event stream integrity 必须可验证。

Rejected outcomes（不可算通过）：

- missing credentials（缺失凭据）
- authentication failure（认证失败）
- DNS / connectivity / base URL failure（DNS / 连接 / 基础 URL 失败）
- stream idle timeout（流空闲超时）
- total timeout（总超时）
- test harness misconfiguration（测试驱动配置错误）

Base CI（基础持续集成）仍使用：

```bash
python -m pytest -q
```

该命令不得要求真实 provider credentials（真实供应商凭据），不得发起真实 provider 网络调用。

真实 provider 测试不得要求一次性返回完整项目文件 JSON；这种模式已经被判定为 source delivery（源码交付）而不是 agent work（智能体工作）。

P2-004 adds a separate default-disabled `real_provider_tool_success` marker（真实供应商工具成功标记）. It is stricter than P2-002: every case must end in `run.completed`（运行完成）, and provider empty output（供应商空输出）、invalid JSON（无效 JSON）、provider failure（供应商失败）、permission denied（权限拒绝）或 tool failure（工具失败）都不能算通过。

默认命令：

```bash
python -m pytest tests/test_real_provider_tool_success.py -q
```

默认结果必须是 skip（跳过），因为未设置：

```text
ATOMIC_AGENT_RUN_REAL_PROVIDER_TOOL_SUCCESS=1
```

显式启用命令可复用 P2-002 Task 7 的本地 git ignored provider config（被 Git 忽略的供应商配置）：

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

P2-004 success-only cases（成功型用例）覆盖：

- `write_file`（写文件）
- `read_file`（读文件）
- `list_files`（列文件）
- `apply_patch`（应用补丁）
- `run_command`（运行声明命令）
- `submit_result`（提交结果）

每个 case 必须验证 event stream integrity（事件流完整性）和 evidence summary（证据摘要）；涉及 produced path（产出路径）的 case 必须验证 source inventory lineage（源码清单谱系）为 `traceable`（可追溯）。`run_command` case 必须验证 `command.completed` exit code（退出码）为 `0`，且 stdout/stderr artifacts（标准输出/错误产物）带 sha256。

P2-006 adds a separate default-disabled `real_provider_complex_task` marker（复杂真实供应商原子任务标记）. It is a success-only manual/nightly gate（只接受成功的手动/夜间门禁） that asks a real provider（真实供应商） to repair one small broken Python report project（破损 Python 报告项目）, run declared commands（声明命令）, produce workspace outputs（工作区产物）, and submit auditable evidence（可审计证据）.

默认命令：

```bash
python -m pytest tests/test_real_provider_complex_task.py -q
```

默认结果必须 skip（跳过）the real provider integration test（真实供应商集成测试）and must not make a provider network call（供应商网络调用）, because it is not enabled unless:

```text
ATOMIC_AGENT_RUN_REAL_PROVIDER_COMPLEX_TASK=1
```

显式启用命令可复用 P2-005 provider options（供应商参数）：

```bash
ATOMIC_AGENT_RUN_REAL_PROVIDER_COMPLEX_TASK=1 \
ATOMIC_AGENT_REAL_PROVIDER_BASE_URL="https://provider.example/v1" \
ATOMIC_AGENT_REAL_PROVIDER_API_KEY="replace-with-real-key" \
ATOMIC_AGENT_REAL_PROVIDER_MODEL="provider-model" \
ATOMIC_AGENT_REAL_PROVIDER_REASONING_EFFORT=high \
python -m pytest tests/test_real_provider_complex_task.py -m real_provider_complex_task -q
```

Required env vars（必需环境变量）：

```text
ATOMIC_AGENT_RUN_REAL_PROVIDER_COMPLEX_TASK=1
ATOMIC_AGENT_REAL_PROVIDER_BASE_URL
ATOMIC_AGENT_REAL_PROVIDER_API_KEY
ATOMIC_AGENT_REAL_PROVIDER_MODEL
```

Recommended explicit defaults（建议显式默认值）：

```text
ATOMIC_AGENT_REAL_PROVIDER_MAX_STEPS=100
ATOMIC_AGENT_REAL_PROVIDER_TOTAL_TIMEOUT_SECONDS=600
ATOMIC_AGENT_REAL_PROVIDER_STREAM_IDLE_TIMEOUT_SECONDS=30
ATOMIC_AGENT_REAL_PROVIDER_REASONING_EFFORT=high
```

Success requires `run.completed`（运行完成）, event stream integrity（事件流完整性）, at least one provider turn（供应商轮次）, required tool coverage（工具覆盖）, `run-tests` failing then passing, `validate-report` passing, traceable produced paths（可追溯产出路径）, command stdout/stderr artifact sha256（命令输出产物哈希）, and no mutation under `work/tests/`, `work/expected/`, or `work/data/`.

Provider failure（供应商失败）, parse failure（解析失败）, permission denied（权限拒绝）, tool failure（工具失败）, missing credentials（缺失凭据）, auth/network failure（认证/网络失败）, or unsupported explicit provider options（不支持显式供应商参数） cannot pass this gate. The gate is costlier and more variable than P2-004, so it remains manual/nightly and must not enter base CI（基础持续集成）. If only the default skip and local harness tests pass, P2-006 gate scaffold（门禁脚手架） is ready but the backlog（待办） must remain pending（待处理） until the explicit real provider gate passes.

## Test Data Rules

- 测试 fixture（测试夹具）必须清晰标记 fake 或 real。
- fake fixture 不能作为真实完成证据。
- golden output（黄金输出）必须包含事件流和 artifact hash（产物哈希）。
- 涉及网络的测试默认禁用，除非明确启用 integration profile（集成配置）。

## Minimum CI Gate

MVP 最小 CI gate（持续集成门禁）建议包含：

```text
unit tests
contract schema tests
permission negative tests
fake provider loop test
```

real provider integration tests 可作为手动或 nightly（夜间）门禁，避免受 provider 波动影响基础 CI。
