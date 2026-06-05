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

真实 provider 测试不得要求一次性返回完整项目文件 JSON；这种模式已经被判定为 source delivery（源码交付）而不是 agent work（智能体工作）。

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
