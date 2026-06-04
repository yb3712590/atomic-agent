# MVP Runtime Specification

## Status

active

## Purpose

本文定义 `atomic-agent`（原子智能体）MVP runtime（最小可行运行时）的功能规格。它说明第一版要实现什么，不说明具体代码步骤。

## MVP Goal

MVP 必须证明一个受控 agent loop（智能体循环）可以：

1. 接收结构化任务。
2. 调用 provider（模型供应商）获得 `AgentAction`（智能体动作）。
3. 执行受权限约束的工具。
4. 将 observation（观察结果）反馈给下一轮。
5. 记录完整 event stream（事件流）。
6. 成功提交结果或 fail closed（失败关闭）。

## Required Tools

| Tool | 中文解释 | P0 行为 |
|---|---|---|
| `list_files` | 列出文件 | 列出 workspace root 内文件。 |
| `read_file` | 读取文件 | 分片读取文件，限制最大字节。 |
| `search_files` | 搜索文件 | 搜索文件名或内容，限制匹配数量。 |
| `write_file` | 写入文件 | 完整写入 allowed write set 内路径。 |
| `apply_patch` | 应用补丁 | 局部修改 allowed write set 内路径并记录 diff。 |
| `run_command` | 运行命令 | 只运行 command policy 声明的 command_id。 |
| `web_fetch` | 网络获取 | 只按 network policy 获取允许 URL。 |
| `submit_result` | 提交结果 | 生成结构化结果摘要和证据引用。 |

## Required Policies

MVP 必须实现：

- workspace root guard（工作区根目录守卫）
- symlink escape guard（符号链接逃逸守卫）
- allowed write set guard（允许写入集合守卫）
- command id guard（命令标识守卫）
- network allowlist guard（网络允许列表守卫）
- max steps / max wall time（最大步数 / 最大运行时间）

## Required Events

MVP 必须记录：

- run started / completed / failed
- provider turn completed / failed
- action parsed / rejected
- permission decided
- tool attempt completed / failed
- workspace mutation recorded
- command completed
- result submitted

## Provider Requirements

第一阶段 provider 可以只支持普通 text completion（文本补全）或 chat（聊天）。runtime 通过 prompt 要求 provider 输出 JSON action（JSON 动作）。

provider 输出无效 JSON 时：

1. 记录 `action.rejected`。
2. 将简短错误作为 observation 返回给下一轮。
3. 超过限制后 fail closed。

## Output Requirements

成功结果必须包含：

- human-readable summary（人类可读摘要）
- event stream reference（事件流引用）
- produced paths（产出路径）
- workspace mutation refs（工作区变更引用）
- command result refs（命令结果引用，如有）

## Non-Goals

MVP 不做：

- 多 agent 协作。
- 长期记忆。
- 分布式执行。
- 任意 shell。
- 浏览器自动化。
- 外部 coding agent bridge（外部编码智能体桥接）。
- 由 runtime 直接判定 Boardroom ticket 完成。
