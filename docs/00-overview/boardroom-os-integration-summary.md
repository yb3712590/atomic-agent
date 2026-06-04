# Boardroom OS 集成摘要

## Status

active

## Purpose

本文定义 `atomic-agent`（原子智能体）与 `boardroom-os`（Boardroom 操作系统）的职责边界。核心原则是：`boardroom-os` 继续作为 governance/evidence/closeout（治理、证据、收尾门禁）的事实源，`atomic-agent` 只负责受控执行实际工作并返回可审计事实。

## Responsibility Split

| 系统 | 职责 | 不负责 |
|---|---|---|
| `boardroom-os` | contract（契约）、role/profile/skill 渲染、governance（治理）、evidence verifier（证据验证器）、closeout gate（收尾门禁） | 不直接实现通用工具循环 |
| `atomic-agent` | agent loop（智能体循环）、tool dispatch（工具调度）、permission policy（权限策略）、event stream（事件流）、workspace mutation（工作区变更） | 不宣布 ticket completed（工单完成），不绕过 Boardroom 证据链 |

## Integration Shape

推荐对接形态：

```text
Boardroom ExecutionPackage（执行包）
  + RolePromptHook（角色提示词钩子）
  + SkillBinding（技能绑定）
  + ModelExecutionProfile（模型执行配置）
  + allowed_write_set（允许写入集合）
  + command policy（命令策略）
    -> AgentRuntimePort.invoke(AgentInvocation)
      -> atomic-agent runtime
        -> AgentRunResult
          -> Boardroom EvidenceVerifier / CloseoutGate
```

## Contract Boundary

`boardroom-os` 应通过 `AgentRuntimePort`（智能体运行时端口）调用 `atomic-agent`。输入是 `AgentInvocation`（智能体调用请求），输出是 `AgentRunResult`（智能体运行结果）。

`AgentRunResult` 必须包含：

- run status（运行状态）
- event stream reference（事件流引用）
- tool attempts（工具调用尝试记录）
- workspace mutations（工作区变更）
- command results（命令结果）
- produced artifacts（产出产物）
- failure reason（失败原因，如有）

## Non-Negotiable Rules

- `atomic-agent` 不能发出 `TICKET_COMPLETED`（工单完成）或 `CLOSEOUT_COMMITTED`（收尾提交）等治理事件。
- `atomic-agent` 不能把 provider text（模型文本输出）单独当作 implementation evidence（实现证据）。
- `atomic-agent` 的文件写入必须受 `allowed_write_set`（允许写入集合）约束。
- `atomic-agent` 的命令执行必须受 command policy（命令策略）约束。
- 所有外部 agent framework（智能体框架）必须通过 tool boundary（工具边界）导入事实，不能绕过证据模型。

## Why Standalone

独立项目化的价值是降低耦合：Boardroom OS 保留治理和事实归约，atomic-agent 专注可替换的执行循环。这样未来可以替换 provider（模型供应商）、工具后端、sandbox（沙箱）和事件存储，而不改变 Boardroom 的治理模型。
