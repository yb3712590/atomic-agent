# atomic-agent

## 1. atomic-agent 是什么

`atomic-agent`（原子智能体）是一个小型、可审计、权限受控的通用 agent runtime（智能体运行时）项目。它的目标不是做大型多智能体平台，而是提供最小但真实的工作循环：读取上下文、执行受控工具、观察结果、修复输出、记录事件，并在失败时 fail closed（失败关闭）。

第一阶段重点能力包括：

- filesystem tools（文件系统工具）：受 workspace root（工作区根目录）和 allowed write set（允许写入集合）约束的读写与 patch（补丁）操作。
- command tools（命令工具）：只执行 policy（策略）允许的命令，不提供自由 shell（自由命令行）。
- web tools（网络工具）：按 allowlist（允许列表）或显式权限访问网络。
- event stream（事件流）：记录 provider turn（模型调用轮次）、tool attempt（工具调用尝试记录）、workspace mutation（工作区变更）、command result（命令结果）等事实。
- permission policy（权限策略）：所有高风险动作必须经过明确策略，不依赖隐式 fallback（降级）。

## 2. 它和 boardroom-os 的关系

`boardroom-os`（Boardroom 操作系统）负责 governance（治理）、contract（契约）、evidence（证据）、reducer（归约器）和 closeout gate（收尾门禁）。`atomic-agent`（原子智能体）负责在受控边界内执行实际工作，并把过程事实以标准事件和结果返回。

推荐边界是：

```text
boardroom-os
  -> AgentRuntimePort（智能体运行时端口）
  -> AgentInvocation（智能体调用请求）
  -> atomic-agent runtime（原子智能体运行时）
  -> AgentRunResult（智能体运行结果）
  -> boardroom-os evidence / closeout（证据与收尾门禁）
```

原则：

- `boardroom-os` 是治理事实源，不被 `atomic-agent` 替代。
- `atomic-agent` 不直接宣布 ticket completed（工单完成）或 closeout committed（收尾提交）。
- `atomic-agent` 只提交可审计的 work result（工作结果）、event stream（事件流）和 artifact references（产物引用）。
- 所有外部 coding agent（编码智能体）或开源 agent framework（智能体框架）都必须被包在权限、事件和证据边界内。

## 3. 如何运行最小示例

当前仓库处于 M0 文档与契约初始化阶段，尚未实现可运行的 minimal example（最小示例）。因此现在没有真实的示例命令可以运行；不要用 mock success path（模拟成功路径）或伪命令表示示例已可用。

当前可执行的仓库健康检查只有：

```bash
git status --short
```

当 minimal example（最小示例）实现后，本节必须更新为真实命令，并同步更新：

- `docs/INDEX.md`（文档总索引）
- `docs/04-implementation-acceptance/INDEX.md`（实现验收索引）
- `docs/05-testing/INDEX.md`（测试索引）

未来示例命令必须满足：真实执行、真实退出码、真实事件输出；不得以静态文本、模拟结果或 silent fallback（静默降级）伪装成功。

## 4. 文档入口在哪里

文档入口是：

- `docs/INDEX.md`（文档总索引）

阅读规则：

1. 新会话先读 `AGENTS.md`（智能体协作规则）。
2. 再读 `docs/INDEX.md`（文档总索引）。
3. 只读取 `docs/INDEX.md` 和相关子目录 `INDEX.md` 明确列出的 authoritative documents（权威文档）。
4. 没有被必要 `INDEX.md` 列出的文档，不是当前权威文档。
