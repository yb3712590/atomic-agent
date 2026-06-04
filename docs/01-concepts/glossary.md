# Glossary

## Status

active

## Purpose

本文是 `atomic-agent`（原子智能体）的核心术语表。新增文档应优先复用这里的术语，避免产生第二套概念。

## Terms

| Term | 中文解释 | 定义 |
|---|---|---|
| `AtomicAgent` | 原子智能体 | 执行单个受控任务的最小智能体单元。 |
| `AgentLoop` | 智能体循环 | provider turn -> action parse -> permission validate -> tool execute -> observation append 的循环。 |
| `AgentRuntime` | 智能体运行时 | 承载 `AgentLoop`、工具注册、权限策略和事件记录的运行模块。 |
| `AgentRuntimePort` | 智能体运行时端口 | 上层系统调用 runtime 的稳定接口。 |
| `AgentInvocation` | 智能体调用请求 | 一次运行的输入，包括任务、上下文、权限、工具和预算。 |
| `AgentRunResult` | 智能体运行结果 | 一次运行的输出，包括状态、事件、产物、错误和统计。 |
| `Provider` | 模型供应商 | OpenAI、Anthropic、local model 等模型调用后端。 |
| `ProviderTurn` | 模型调用轮次 | agent loop 中一次发送上下文并接收模型输出的过程。 |
| `AgentAction` | 智能体动作 | 模型输出并经解析后的标准动作，例如 `read_file` 或 `run_command`。 |
| `Tool` | 工具 | runtime 可执行的能力单元，例如文件读取、patch、命令、网络。 |
| `ToolAttempt` | 工具调用尝试记录 | 一次工具调用的审计事实，包含输入、权限决策、输出、错误和时间。 |
| `Observation` | 观察结果 | 工具调用后返回给下一轮模型的受限上下文。 |
| `Workspace` | 工作区 | agent 可访问的项目目录或临时执行目录。 |
| `WorkspaceRoot` | 工作区根目录 | 所有文件读写路径必须被限制在其中的根路径。 |
| `AllowedWriteSet` | 允许写入集合 | 允许 agent 创建、修改或删除的相对路径集合。 |
| `WorkspaceMutation` | 工作区变更 | 文件创建、修改、删除的事实记录，包含 before/after hash（前后哈希）和 diff（差异）。 |
| `PermissionPolicy` | 权限策略 | 决定某个 action 是否 allow（允许）、deny（拒绝）或 require approval（需要审批）的规则。 |
| `SandboxPolicy` | 沙箱策略 | 限制文件系统、命令和网络访问的执行环境策略。 |
| `CommandPolicy` | 命令策略 | 定义哪些命令可以运行、如何匹配、是否需要审批。 |
| `NetworkPolicy` | 网络策略 | 定义哪些网络访问被允许、拒绝或限制。 |
| `EventStream` | 事件流 | runtime 产生的 append-only（只追加）事件序列。 |
| `AgentEvent` | 智能体事件 | 事件流中的单条事件，如 `tool.attempt.started`。 |
| `Artifact` | 产物 | 运行过程中产生的文件、日志、diff、stdout/stderr 或结果摘要。 |
| `FailClosed` | 失败关闭 | 权限、解析、验证或执行不明确时拒绝继续并返回失败。 |
| `SilentFallback` | 静默降级 | 未显式记录和批准的替代路径；本项目禁止。 |
| `MockSuccessPath` | 模拟成功路径 | 用假结果伪装真实成功；本项目禁止作为验收依据。 |

## Naming Rules

- 代码标识符使用 English names（英文名称）。
- 文档首次出现关键英文术语时，应附中文解释。
- Boardroom OS 对接概念应保持与 Boardroom 文档同名，例如 `ExecutionPackage`（执行包）、`ProviderAttempt`（模型调用尝试记录）、`SourceInventory`（源码清单）。
