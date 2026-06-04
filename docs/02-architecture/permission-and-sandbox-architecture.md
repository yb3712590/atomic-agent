# Permission and Sandbox Architecture

## Status

active

## Purpose

本文定义 `atomic-agent`（原子智能体）的权限与沙箱架构。目标是让 agent 能完成真实工作，同时不能获得未授权文件、命令或网络能力。

## Core Philosophy

权限模型采用 fail-closed（失败关闭）：

```text
unknown action -> deny
unknown path -> deny
unknown command -> deny
unknown network target -> deny
policy conflict -> choose stricter decision
```

不允许 silent fallback（静默降级）。如果 runtime 使用替代路径，必须有显式事件、原因和策略依据。

## Policy Layers

```text
AgentInvocation policy
  ∩ role/tool permissions
  ∩ workspace policy
  ∩ command policy
  ∩ network policy
  ∩ runtime hard limits
```

只有所有相关层都允许时，动作才可以执行。

## Filesystem Policy

文件路径必须满足：

- 使用 relative path（相对路径）。
- 规范化后仍位于 `WorkspaceRoot`（工作区根目录）内。
- 不包含 `..` 路径逃逸。
- 不穿越 symlink（符号链接）逃逸。
- 写入路径必须属于 `AllowedWriteSet`（允许写入集合）。
- 默认不能写 runtime metadata（运行时元数据）、policy file（策略文件）或上层 contract artifacts（契约产物），除非显式允许。

读路径和写路径应分开建模：读权限不自动授予写权限。

## Command Policy

`run_command`（运行命令）不接受任意 shell string（命令字符串）作为第一阶段接口。推荐输入是：

```json
{
  "action": "run_command",
  "command_id": "test-backend"
}
```

runtime 通过 `command_id`（命令标识）查找声明命令。命令策略必须记录：

- command id（命令标识）
- executable（可执行文件）
- args（参数）
- cwd（工作目录）
- env allowlist（环境变量允许列表）
- timeout（超时）
- network access（是否允许网络）

未声明命令必须拒绝。

## Network Policy

网络默认拒绝，除非 invocation（调用请求）显式授予：

- allowed domains（允许域名）
- allowed methods（允许方法）
- max response bytes（最大响应字节）
- private network access（私有网络访问）是否允许

第一阶段建议只允许 `GET` / `HEAD` 类型的信息获取动作。带副作用的 HTTP 方法必须进入后续审批模型。

## Approval Model

第一阶段可以先实现三类决策：

| Decision | 中文解释 | 行为 |
|---|---|---|
| `allow` | 允许 | 直接执行并记录事件 |
| `deny` | 拒绝 | 不执行，记录失败事件 |
| `requires_approval` | 需要审批 | 暂停并返回 pending approval（等待审批）状态 |

无交互环境下遇到 `requires_approval` 必须 fail closed，而不是自动允许。

## Hard Limits

runtime 必须支持：

- `max_steps`（最大步数）
- `max_wall_seconds`（最大运行秒数）
- `max_file_bytes`（单文件最大读取字节）
- `max_total_written_bytes`（总写入字节）
- `max_command_runs`（最大命令次数）
- `max_network_requests`（最大网络请求数）
- `max_observation_chars`（最大观察结果字符数）

超限必须记录事件并返回失败或受控停止。

## Audit Requirements

每次权限决策必须能审计：

- requested action（请求动作）
- normalized target（规范化目标）
- matched policy（命中策略）
- decision（决策）
- reason summary（简短原因）
