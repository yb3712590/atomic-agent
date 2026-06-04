# Roadmap

## Status

active

## Purpose

本文定义 `atomic-agent`（原子智能体）的阶段路线，防止项目过早扩张为大型 agent framework（智能体框架）。

## Planning Model

`M0/M1/M2...` 表示 milestone（能力里程碑），用于描述项目在产品能力、架构能力和集成能力上的阶段目标。

`P0/P1/P2...` 表示 execution wave（滚动执行波次），用于组织当前和近端实现任务。P 阶段不是 milestone（里程碑）的完整镜像，也不是项目终点编号。

一个 P wave（执行波次）可以服务多个 milestone；一个 milestone 也可以跨多个 P wave 完成。backlog（待办）不预先穷尽所有未来 milestone 的任务。远期能力保持在 roadmap（路线图）中，只有在 P-stage exit review（P 阶段退出复审）后，才把下一组 cohesive work package（内聚工作包）编入下一个 P wave。

## Roadmap Review Protocol

roadmap review（路线图复审）只在 P-stage exit（P 阶段退出）时触发，除非出现影响长期路线的 blocker（阻塞）或 ADR（架构决策记录）级决策。

每次 P-stage exit review 必须完成：

1. 对照 milestone exit criteria（里程碑退出标准），判断哪些 M 条目已满足、部分满足或失效。
2. 检查当前 P wave 的完成项是否改变下一阶段优先级。
3. 识别新增、删除或重组的 cohesive work package。
4. 更新 backlog 中下一个 P wave 的任务集合。
5. 如长期路线、项目边界或架构原则变化，先写 ADR。
6. 如产生阶段复盘价值，写入 project log（项目日志）。

## Current Planned Endpoint

当前规划终点是 M5：external coding agent bridge（外部编码智能体桥接）。M5 完成后是否继续扩展，必须在后续 roadmap review 中重新评估。

M5 之前，`atomic-agent` 应保持为 Boardroom OS（Boardroom 操作系统）可调用、受权限约束、可审计的 runtime（运行时），而不是独立 SaaS（软件即服务）、大型多租户调度系统或 Boardroom OS 替代品。

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
