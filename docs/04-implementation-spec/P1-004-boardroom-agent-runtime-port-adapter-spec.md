# Boardroom AgentRuntimePort Adapter Specification

## Status

implemented

## Purpose

本文定义 P1-004 `Boardroom AgentRuntimePort adapter`（Boardroom 智能体运行时端口适配器）的实现规格。该能力负责把现有 `AgentLoop`（智能体循环）暴露为稳定的 `AgentRuntimePort`（智能体运行时端口）边界，使 Boardroom OS（Boardroom 操作系统）等上层系统可以传入完整 `AgentInvocation`（智能体调用请求）并获得原样的 `AgentRunResult`（智能体运行结果）。

P1-004 的目标不是实现 Boardroom OS，也不是把 `ExecutionPackage`（执行包）映射逻辑迁入 `atomic-agent`（原子智能体）。Boardroom OS 仍是 governance（治理）、evidence（证据）和 closeout gate（收尾门禁）的事实源；`atomic-agent` 只负责受控执行并返回可审计事实。

## Scope

P1-004 覆盖以下能力：

- 新增 `AgentRuntimePort`（智能体运行时端口）协议，语义为 `invoke(invocation: AgentInvocation) -> AgentRunResult`。
- 新增 `AgentRuntimeRunner`（智能体运行时执行器）协议，语义为 `run(invocation: AgentInvocation) -> AgentRunResult`，用于适配现有 `AgentLoop`。
- 新增 `BoardroomAgentRuntimePortAdapter`（Boardroom 智能体运行时端口适配器），通过组合 runner（执行器）调用现有 runtime（运行时），不得复制 `AgentLoop` 逻辑。
- adapter（适配器）必须要求调用方传入已经构造完成且通过模型校验的 `AgentInvocation`（智能体调用请求）。
- adapter 必须把 `AgentRunResult`（智能体运行结果）原样返回给调用方，不得把 runtime success（运行时成功）转换为 Boardroom ticket completed（工单完成）。
- adapter 必须保留失败结果中的 `failure_kind`（失败类型）、`failure_message`（失败说明）和 `failed_action_ref`（失败动作引用）。
- adapter 必须在收到非 `AgentInvocation` 输入或 runner 返回非 `AgentRunResult` 时清晰失败，不能返回伪成功结果。
- 新增 contract tests（契约测试）覆盖成功透传、失败透传、输入类型拒绝、runner 返回类型拒绝，以及无 Boardroom governance fields（治理字段）泄漏。

不包含：

- 不实现 Boardroom OS 侧 `ExecutionPackage`（执行包）、`RolePromptHook`（角色提示词钩子）、`SkillBinding`（技能绑定）或 `ModelExecutionProfile`（模型执行配置）的数据模型。
- 不实现 `ExecutionPackage -> AgentInvocation`（执行包到智能体调用请求）的映射；该映射由 Boardroom OS 或上层调用方负责。
- 不新增 standalone `.env` loader（独立环境加载器）或本地配置加载逻辑。
- 不读取 `.env`、environment variables（环境变量）、local config files（本地配置文件）或 process defaults（进程默认值）来补齐缺失字段。
- 不新增 provider（模型供应商）能力、tool（工具）能力、permission policy（权限策略）或 event type（事件类型）。
- 不新增 Boardroom governance events（治理事件），尤其不能生成 `TICKET_COMPLETED`（工单完成）或 `CLOSEOUT_COMMITTED`（收尾提交）。
- 不修改 `AgentLoop`（智能体循环）执行语义。
- 不提交 git commit（提交），除非用户另行明确要求。

## Authoritative Inputs

本规格依据以下已索引文档：

- `docs/04-implementation-backlog/backlog.md`（实现待办），其中 P1-004 为 pending（待处理）任务。
- `docs/03-contracts/agent-runtime-port.md`（智能体运行时端口契约），定义 `AgentRuntimePort.invoke(invocation: AgentInvocation) -> AgentRunResult`。
- `docs/00-overview/boardroom-os-integration-summary.md`（Boardroom OS 集成摘要），定义 Boardroom OS 与 `atomic-agent` 的职责边界。
- `docs/09-adr/0004-keep-boardroom-os-as-governance-source.md`（保持 Boardroom OS 为治理事实源 ADR）。
- `docs/04-implementation-acceptance/mvp-acceptance.md`（MVP 验收标准），要求 `AgentRunResult` 不能直接声明 Boardroom ticket completed（工单完成）。
- `docs/02-architecture/runtime-architecture.md`（运行时架构），定义 runtime（运行时）只拥有一次运行短期状态，不拥有长期治理状态。
- `docs/02-architecture/event-and-evidence-architecture.md`（事件与证据架构），定义 `atomic-agent` 只提供事实，不生成 Boardroom 治理完成事件。

## Port Contract

P1-004 必须提供以下 Python-level contract（Python 层契约）：

```text
AgentRuntimePort.invoke(invocation: AgentInvocation) -> AgentRunResult
```

最小对象关系：

```text
Boardroom OS or caller（调用方）
  -> complete AgentInvocation（完整智能体调用请求）
  -> BoardroomAgentRuntimePortAdapter.invoke(...)
  -> AgentRuntimeRunner.run(...)
  -> existing AgentLoop.run(...)
  -> AgentRunResult（智能体运行结果）
```

`AgentRuntimeRunner`（智能体运行时执行器）必须是协议而不是具体基类，使现有 `AgentLoop`（智能体循环）可以直接作为 runner 使用。只要对象提供 `run(invocation: AgentInvocation) -> AgentRunResult`，就可以被 adapter 组合。

## Adapter Behavior

`BoardroomAgentRuntimePortAdapter`（Boardroom 智能体运行时端口适配器）必须满足：

1. 构造时接收一个 runner（执行器）依赖。
2. `invoke()` 收到非 `AgentInvocation`（智能体调用请求）实例时，抛出 `TypeError`，并且不得调用 runner。
3. `invoke()` 收到合法 `AgentInvocation` 时，调用 `runner.run(invocation)`，并传入同一个 invocation 对象。
4. 如果 runner 返回 `AgentRunResult`，adapter 必须返回同一个结果对象，不得复制、裁剪、转换或补字段。
5. 如果 runner 返回非 `AgentRunResult`，adapter 必须抛出 `TypeError`。
6. 如果 runner 抛出异常，adapter 不得伪造 `AgentRunResult`。adapter 不捕获任何 runner exception（执行器异常），所有异常原样传播给调用方，因为 adapter 没有 event stream（事件流）和 artifact（产物）上下文来构造真实失败结果。
7. adapter 不得读取环境变量、`.env`、本地配置文件或全局默认值。
8. adapter 不得修改 `invocation`、`result.status`、`event_stream_ref`、`events_hash`、`tool_attempts`、`workspace_mutations`、`artifacts` 或 failure fields（失败字段）。
9. adapter 本身只持有 runner 引用，不维护运行状态、缓存、计数器或 event cursor（事件游标）。并发调用是否安全取决于传入 runner 及其依赖；并发控制由调用方或 Boardroom OS 调度层负责。

异常传播规则的原因：如果 adapter 在没有真实 event stream（事件流）和 artifact refs（产物引用）的情况下合成 failed `AgentRunResult`（失败运行结果），会制造第二事实源或 mock failure path（模拟失败路径）。P1-004 因此要求 runner 层负责真实运行失败的结构化结果；adapter 层只在接口类型错误时清晰失败。

并发责任边界的原因：`BoardroomAgentRuntimePortAdapter`（Boardroom 智能体运行时端口适配器）是无运行状态的边界对象，但现有 runner 可能组合 `EventRecorder`（事件记录器）、`ArtifactWriter`（产物写入器）等具有输出路径状态的依赖。adapter 不声明跨调用并发安全；上层必须为每次运行提供隔离的 runner 或调度串行访问。

## Invocation Requirements

调用方必须提供完整 `AgentInvocation`（智能体调用请求），包括：

- `invocation_id`（调用标识）
- `task`（任务）
- `workspace_root`（工作区根目录）
- `allowed_write_set`（允许写入集合）
- `tools`（工具集合）
- `permission_policy`（权限策略）
- `provider_profile`（模型供应商配置）
- `budgets`（预算限制）
- `output_requirements`（输出要求）

adapter 不得补齐缺失字段。缺失字段应由 `AgentInvocation`（智能体调用请求）模型校验或调用方构造过程暴露，不得在 adapter 中用默认值掩盖。

## Result and Governance Boundary

adapter 返回的 `AgentRunResult`（智能体运行结果）只能表示 runtime（运行时）事实，不能表示 Boardroom OS（Boardroom 操作系统）治理完成。必须保留：

- `run_id`（运行标识）
- `status`（运行状态）
- `event_stream_ref`（事件流引用）
- `events_hash`（事件哈希）
- `tool_attempts`（工具调用尝试记录）
- `workspace_mutations`（工作区变更）
- `artifacts`（产物）
- `summary`（摘要）
- failed result（失败结果）中的 `failure_kind`、`failure_message`、`failed_action_ref`

adapter 不得添加以下 Boardroom governance（治理）字段或等价字段：

- `ticket_completed`
- `closeout_committed`
- `governance_status`
- `evidence_verified`
- `source_inventory_accepted`

这些字段属于 Boardroom OS 的 evidence verifier（证据验证器）和 closeout gate（收尾门禁）职责，不属于 `atomic-agent` runtime port（原子智能体运行时端口）。

## Security and No-Fallback Rules

- 不得用 silent fallback（静默降级）补齐 runner、invocation、policy、provider、budget 或 output requirements（输出要求）。
- 不得把 provider output（模型输出）或 summary（摘要）单独包装成 implementation evidence（实现证据）。
- 不得在 adapter 内创建第二套 event stream（事件流）或 artifact store（产物存储）。
- 不得吞掉 runner exception（执行器异常）并返回 misleading success（误导性成功）或缺少事件证据的 failed result（失败结果）；adapter 不捕获任何 runner exception，异常由调用方处理。
- 不得修改 `AgentRunStatus.COMPLETED`（运行完成）语义；completed 只表示 runtime 已提交结果，不表示 Boardroom 工单完成。
- 不得为 Boardroom 集成引入 hardcoded configurable options（硬编码可配置选项）。
- 不得在 adapter 中新增除 `runner` 以外的可变运行状态；并发控制和 runner 隔离由调用方负责。

## Documentation Requirements

P1-004 实现完成且验证通过后，必须更新：

- `docs/04-implementation-backlog/backlog.md`：将 P1-004 标记为 `completed`。
- `docs/04-implementation-spec/P1-004-boardroom-agent-runtime-port-adapter-spec.md`：状态从 `draft` 改为 `implemented`。
- `docs/04-implementation-plan/P1-004-boardroom-agent-runtime-port-adapter-plan.md`：状态从 `draft` 改为 `implemented`。
- `docs/04-implementation-spec/INDEX.md`：实现完成后将本规格移入 Completed / Archived Documents（已完成 / 已归档文档）。
- `docs/04-implementation-plan/INDEX.md`：实现完成后将对应 plan（实施计划）移入 Completed / Archived Documents。
- `docs/INDEX.md`：实现完成后移除 P1-004 draft active pointers（草案活跃指针），除非仍有未完成的 P1-004 文档评审事项。

P1-004 不更新 `docs/03-contracts/agent-runtime-port.md`，因为现有契约已经定义端口形态。只有字段语义变化或破坏性契约变化才需要修改该契约并先写 ADR（架构决策记录）。

## Acceptance Criteria

P1-004 完成时必须证明：

- `src/atomic_agent/runtime_port.py` 存在，并定义 `AgentRuntimePort`、`AgentRuntimeRunner` 和 `BoardroomAgentRuntimePortAdapter`。
- `BoardroomAgentRuntimePortAdapter.invoke()` 接收 `AgentInvocation` 并调用 runner 的 `run()` 方法。
- 成功 `AgentRunResult(status="completed")` 被原样返回，`event_stream_ref`、`events_hash`、`tool_attempts`、`workspace_mutations`、`artifacts` 和 `summary` 不被修改。
- 失败 `AgentRunResult(status="failed")` 被原样返回，`failure_kind`、`failure_message` 和 `failed_action_ref` 不被修改。
- 非 `AgentInvocation` 输入被拒绝，并且 runner 不被调用。
- runner 返回非 `AgentRunResult` 时被拒绝，不能被包装成成功结果。
- runner 抛出的异常由 adapter 原样传播，adapter 不捕获、不包装、不合成 failed `AgentRunResult`。
- adapter 只持有 `runner` 依赖，不引入额外可变运行状态；并发控制由调用方负责。
- 返回结果中不存在 Boardroom governance fields（治理字段），包括 `ticket_completed`、`closeout_committed`、`governance_status`、`evidence_verified` 和 `source_inventory_accepted`。
- `src/atomic_agent/__init__.py` 导出新增端口类型，方便上层集成导入。
- `python -m pytest tests/test_runtime_port.py -q` 通过。
- `python -m pytest -m permission_negative -q` 通过。
- `python -m pytest -q` 通过。
- runtime source（运行时代码）没有新增 `.env`、`os.environ`、`getenv`、`dotenv`、`TICKET_COMPLETED`、`CLOSEOUT_COMMITTED` 或默认 allow-all（默认全允许）模式。

## Self-Review Result

- Spec coverage（规格覆盖）：已覆盖 backlog P1-004、`AgentRuntimePort` 契约、Boardroom OS 职责边界、成功/失败结果透传、无治理事件、无静默兜底、文档更新和测试验收。
- Placeholder scan（占位符扫描）：未使用占位标记、未完成提示或“稍后补充”措辞；每项验收均给出可验证事实。
- Type / naming consistency（类型与命名一致性）：`AgentRuntimePort`、`AgentRuntimeRunner`、`BoardroomAgentRuntimePortAdapter`、`AgentInvocation`、`AgentRunResult`、`AgentRunStatus` 命名与现有契约和代码一致。
- Scope check（范围检查）：未纳入 Boardroom OS 数据模型、ExecutionPackage 映射、真实 provider 集成、新工具、新权限系统、新事件类型或长期配置系统。
- No-fallback check（无兜底检查）：明确禁止环境读取补齐、默认配置补齐、异常吞掉、伪造失败结果、运行时成功转治理完成和新增第二事实源。
