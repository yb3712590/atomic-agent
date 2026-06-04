# GenericAgent and Codex Reference

## Status

active

## Purpose

本文记录 GenericAgent（通用智能体）和 Codex（编码智能体）调研结论。本文是 reference（参考资料），不是 authoritative architecture（权威架构）。被采纳的长期决策已进入 ADR。

## GenericAgent Observations

GenericAgent 的核心吸引力：

- 约 3000 行 seed code（种子代码）实现最小 agent 能力。
- 约 100 行 agent loop（智能体循环）表达 provider -> tool -> observation 的闭环。
- 9 个 atomic tools（原子工具）：`code_run`、`file_read`、`file_write`、`file_patch`、`web_scan`、`web_execute_js`、`ask_user`、`update_working_checkpoint`、`start_long_term_update`。
- handler / dispatch（处理器 / 调度）模型简单，适合作为小核心参考。

GenericAgent 不适合直接作为 atomic-agent 核心的原因：

- 系统提示词采用 “Physical-Level Omnipotent Executor”（物理级全能执行器）哲学，权限过大。
- 文件路径守卫不足，不满足 workspace root（工作区根目录）、allowed write set（允许写入集合）、symlink guard（符号链接守卫）要求。
- 命令执行更接近自由代码运行，不满足 command_id（命令标识）策略。
- trace/log（跟踪/日志）不等价于 Boardroom OS 所需 governance evidence（治理证据）。

可借鉴部分：

- 小型 loop 不必复杂。
- 工具集合应保持原子化。
- observation（观察结果）驱动下一轮修复。
- handler dispatch 可作为实现形态参考。

## Codex Observations

Codex 值得借鉴的设计：

- SQ/EQ（Submission Queue / Event Queue，提交队列 / 事件队列）分离输入与事件输出。
- JSONL event stream（JSONL 事件流）表达 turn、command、file change、error 等事实。
- sandbox policy（沙箱策略）默认限制文件系统和网络。
- approval policy（审批策略）明确区分 allow、prompt、deny。
- execpolicy（命令执行策略）用规则匹配命令并采用更严格决策。
- network proxy（网络代理）采用 allowlist-first（允许列表优先）与 deny-wins（拒绝优先）。

Codex 不适合作为 atomic-agent 核心的原因：

- 产品和模型耦合较强。
- trace 语义不等价于 Boardroom evidence model（证据模型）。
- 直接嵌入会形成第二套 runtime state machine（运行时状态机）。

可借鉴部分：

- 事件协议风格。
- 权限和沙箱哲学。
- 命令审批和网络 allowlist。
- 外部 coding agent bridge（外部编码智能体桥接）的导入方式。

## Adopted Decisions

相关已采纳决策：

- `docs/09-adr/0001-use-standalone-atomic-agent-runtime.md`
- `docs/09-adr/0002-use-provider-agnostic-action-protocol.md`
- `docs/09-adr/0003-use-fail-closed-permission-model.md`
- `docs/09-adr/0004-keep-boardroom-os-as-governance-source.md`

## Reference Rule

本文件不能单独作为实现依据。如果某个参考结论影响实现，必须进入 architecture（架构）、contract（契约）、acceptance（验收）或 ADR（架构决策记录）。
