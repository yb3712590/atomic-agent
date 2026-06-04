# atomic-agent 项目简述

## Status

active

## Purpose

`atomic-agent`（原子智能体）是一个小型、可审计、权限受控的通用 `agent runtime`（智能体运行时）。它面向“现实公司员工日常琐事”这一类任务：读写文件、搜索文件内容、访问网络、获取网络信息、执行受控命令，并根据 observation（观察结果）继续下一步。

本项目不追求一开始成为大型 multi-agent platform（多智能体平台），而是先实现一个可被上层治理系统信任的最小工作循环。

## Core Goal

第一阶段目标是提供一个真实可执行的 `AgentLoop`（智能体循环）：

```text
input task
  -> build runtime context
  -> provider turn
  -> parse AgentAction
  -> validate permission policy
  -> execute tool
  -> record event
  -> append observation
  -> repeat or submit
```

其中每一步都必须可审计、可失败、可被上层系统验证。

## First-Stage Capabilities

P0 能力：

- `list_files`（列出文件）：查看 workspace（工作区）内文件树。
- `read_file`（读取文件）：读取受权限限制的文件内容。
- `search_files`（搜索文件）：按文件名或内容搜索上下文。
- `write_file`（写入文件）：只写入允许路径。
- `apply_patch`（应用补丁）：对允许路径做局部变更。
- `run_command`（运行命令）：只运行策略允许的命令。
- `web_fetch`（获取网页）：按网络策略获取公开信息。
- `submit_result`（提交结果）：提交工作摘要、文件变更和事件引用。

P0 非能力：

- 不做长期记忆系统。
- 不做完整多智能体组织调度。
- 不让 agent 自行声明治理完成。
- 不提供自由 shell（自由命令行）。
- 不把外部 coding agent（编码智能体）作为事实源。

## Design Principles

1. fail closed（失败关闭）：权限不明确时拒绝执行。
2. no silent fallback（无静默降级）：降级必须显式、可观察、被批准。
3. no mocked success path（无模拟成功路径）：不能用假成功替代真实运行。
4. provider-agnostic（模型供应商无关）：核心协议不绑定 OpenAI、Anthropic、local model 或其它 provider（模型供应商）。
5. event-first（事件优先）：每次工具调用、命令执行、文件变更都必须进入事件流。
6. governance-friendly（治理友好）：输出必须能被 Boardroom OS（Boardroom 操作系统）等上层治理系统消费。

## Current Stage

当前阶段是 M0：文档与契约初始化。仓库尚未提供可运行 runtime（运行时）代码；README 中的 minimal example（最小示例）必须等真实实现完成后再更新。
