# Roadmap

## Status

active

## Purpose

本文定义 `atomic-agent`（原子智能体）的阶段路线，防止项目过早扩张为大型 agent framework（智能体框架）。

## Milestones

| Milestone | 中文解释 | 目标 |
|---|---|---|
| M0 | 文档与契约初始化 | 建立 README、AGENTS、docs 索引、首批权威文档。 |
| M1 | 最小 AgentLoop + filesystem tools | 实现 JSON action loop、文件读写、搜索、patch、事件记录。 |
| M2 | command / web tools + permission policy | 实现受控命令、网络获取、权限策略和负向测试。 |
| M3 | Boardroom AgentRuntimePort 对接 | 提供 Boardroom OS 可调用的端口和结果映射。 |
| M4 | event stream / evidence 映射 | 完善事件流、artifact hash、workspace mutation 与 evidence 对接。 |
| M5 | external coding agent bridge | 将 Codex、Claude Code 或其它 coding agent 作为受控外部工具接入。 |

## M0 Exit Criteria

- `README.md` 说明项目定位、Boardroom 关系、最小示例状态和文档入口。
- `AGENTS.md` 说明文档治理规则。
- `docs/INDEX.md` 和子目录 `INDEX.md` 完整。
- 首批 ADR、architecture、contracts、acceptance、testing、roadmap 文档完成。

## M1 Exit Criteria

- 可运行 fake provider loop（假模型供应商循环）。
- 支持 `list_files`、`read_file`、`search_files`、`write_file`、`apply_patch`。
- 支持 `AgentAction` JSON schema validation（JSON 模式校验）。
- 支持 JSONL event stream（JSONL 事件流）。
- 支持 workspace root 和 allowed write set 守卫。

## M2 Exit Criteria

- 支持 `run_command`，且只接受 command_id（命令标识）。
- 支持 `web_fetch`，且受 network policy（网络策略）限制。
- 权限负向测试覆盖 P0 安全边界。
- 预算超限和无效动作都 fail closed（失败关闭）。

## M3 Exit Criteria

- 定义并实现 `AgentRuntimePort`（智能体运行时端口）。
- Boardroom OS 能构造 `AgentInvocation`（智能体调用请求）。
- `AgentRunResult`（智能体运行结果）可映射为 Boardroom evidence（证据）输入。
- atomic-agent 不产生 Boardroom 治理完成事件。

## M4 Exit Criteria

- 事件流可重放或明确说明不可重放原因。
- workspace mutation（工作区变更）包含 before/after hash 和 diff。
- command result（命令结果）包含 stdout/stderr artifact hash。
- Boardroom `SourceInventory`（源码清单）可追溯到 provider/tool/workspace lineage（谱系）。

## M5 Exit Criteria

- 外部 coding agent（编码智能体）只能作为 tool（工具）运行。
- 外部 agent 的 diff、日志、命令结果必须导入事件和证据模型。
- 外部 agent 不能绕过 permission policy（权限策略）。

## Non-Roadmap Items

当前不规划：

- 独立 SaaS 平台。
- 大型多租户任务调度。
- 长期记忆系统。
- 直接替代 Boardroom OS 治理链路。
