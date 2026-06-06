# P2-001 Evidence Mapping and Artifact Hash Hardening Specification

## Status

implemented

## Purpose

本文定义 P2-001 `event stream / evidence mapping`（事件流 / 证据映射）和 `artifact hash`（产物哈希）硬化的实现规格。该能力把现有 `AgentRunResult`（智能体运行结果）、JSONL `event stream`（事件流）和 artifact references（产物引用）派生为可供 Boardroom OS（Boardroom 操作系统）消费的 evidence summary（证据摘要），并显式校验事件哈希链、命令产物哈希、workspace mutation（工作区变更）谱系和 replay status（重放状态）。

P2-001 的目标不是实现 Boardroom OS 的 EvidenceVerifier（证据验证器），也不是让 `atomic-agent`（原子智能体）直接声明 ticket completed（工单完成）或 closeout committed（收尾提交）。`atomic-agent` 只输出可审计事实和候选映射；治理判断仍属于 Boardroom OS。

## Scope

P2-001 覆盖以下能力：

- 新增 `evidence` module（证据模块），从 `AgentRunResult`、JSONL event stream 和 artifact references 派生 Boardroom evidence input（Boardroom 证据输入候选）。
- 校验 event stream integrity（事件流完整性）：JSONL 可解析、sequence（序号）连续、`previous_event_hash`（前序事件哈希）链正确、每条 `event_hash`（事件哈希）可重算、整体 `events_hash`（事件流哈希）匹配。
- 将 `provider.turn.completed`（模型轮次完成）映射为 provider attempt evidence（模型调用尝试证据候选）。
- 将 `tool.attempt.*`（工具调用尝试事件）映射为 tool attempt evidence（工具尝试证据候选）。
- 将 `workspace.mutation.recorded`（工作区变更记录事件）映射为 workspace mutation evidence（工作区变更证据候选），必须保留 before hash（变更前哈希）、after hash（变更后哈希）和 diff artifact reference（差异产物引用）。
- 将 `command.completed`（命令完成事件）映射为 command evidence（命令证据候选），必须保留 exit code（退出码）、stdout artifact hash（标准输出产物哈希）和 stderr artifact hash（标准错误产物哈希）。
- 将 `network.fetch.completed`（网络获取完成事件）映射为 network fetch evidence（网络获取证据候选），保留 response artifact hash（响应产物哈希）。
- 为 submitted produced paths（已提交产出路径）派生 `SourceInventory` lineage（源码清单谱系），把 source file（源码文件）追溯到 provider turn（模型轮次）、action（动作）、tool attempt（工具调用尝试）和 workspace mutation（工作区变更）。
- 显式描述 replay status（重放状态）：如果当前事件流缺少 invocation snapshot（调用快照）、policy snapshot（策略快照）或 tool versions（工具版本），必须返回 `not_replayable`（不可重放）和具体原因。
- 新增 unit / integration tests（单元 / 集成测试），使用真实 event stream 和 artifact references 验证映射，不使用 mock success path（模拟成功路径）。

不包含：

- 不修改 `AgentRuntimePort`（智能体运行时端口）契约字段，除非后续 ADR（架构决策记录）明确要求。
- 不把 evidence summary（证据摘要）写回 `AgentRunResult` 的必需字段，避免破坏已实现的 M3 端口兼容性。
- 不实现 Boardroom OS 的 EvidenceVerifier、closeout gate（收尾门禁）、`SourceInventory` acceptance（源码清单验收）或 governance event（治理事件）。
- 不实现 full replay engine（完整重放引擎）。当前只校验事件完整性并显式说明是否可重放。
- 不新增 provider（模型供应商）能力、tool（工具）能力、permission policy（权限策略）或 network policy（网络策略）。
- 不新增 real provider integration gate（真实模型供应商集成门禁）；该项属于 P2-002。
- 不设计或实现 external coding agent bridge（外部编码智能体桥接）；该项保持 deferred（延后）到 P2-003 设计阶段。
- 不读取 `.env`、environment variables（环境变量）、local config files（本地配置文件）或 process defaults（进程默认值）补齐证据字段。
- 不提交 git commit（提交），除非用户另行明确要求。

## Authoritative Inputs

本规格依据以下已索引 authoritative documents（权威文档）：

- `docs/04-implementation-backlog/backlog.md`（实现待办），其中 P2-001 是第一个 P2 work package（工作包）。
- `docs/06-roadmap/roadmap.md`（路线图），其中 M4 要求 event stream / evidence mapping（事件流 / 证据映射）、artifact hash（产物哈希）和 `SourceInventory` lineage（源码清单谱系）。
- `docs/02-architecture/event-and-evidence-architecture.md`（事件与证据架构），定义事件流是审计事实源，`atomic-agent` 只提供事实。
- `docs/03-contracts/event-stream-protocol.md`（事件流协议），定义 event envelope（事件信封）、hash chain（哈希链）、artifact references（产物引用）和事件顺序规则。
- `docs/03-contracts/agent-runtime-port.md`（智能体运行时端口契约），定义 `AgentRunResult` 字段和 Boardroom evidence input（Boardroom 证据输入）边界。
- `docs/04-implementation-acceptance/mvp-acceptance.md`（MVP 验收标准），要求 source file（源码文件）可追溯到 tool attempt（工具调用尝试）和 workspace mutation（工作区变更），command evidence（命令证据）包含 stdout/stderr artifact hash。
- `docs/05-testing/testing-strategy.md`（测试策略），要求 fake provider loop（假模型供应商循环）包含事件流和 artifact hash（产物哈希），real provider tests（真实模型供应商测试）不进入基础 CI（持续集成）必跑路径。
- `docs/09-adr/0004-keep-boardroom-os-as-governance-source.md`（保持 Boardroom OS 为治理事实源 ADR），要求 `atomic-agent` 不直接产生治理完成结论。

## Current Implementation Baseline

当前代码已提供以下基础能力：

- `EventRecorder`（事件记录器）会写出 JSONL event stream，包含 sequence（序号）、`previous_event_hash` 和 `event_hash`。
- `ArtifactWriter`（产物写入器）会为 artifact（产物）计算 `sha256:<64 hex>` 哈希、字节大小和 observation truncation（观察截断）状态。
- `AgentLoop`（智能体循环）会记录 provider output artifact（模型输出产物）、tool observation artifact（工具观察产物）、workspace mutation diff artifact（工作区变更差异产物）、command stdout/stderr artifacts（命令标准输出/错误产物）和 result artifact（结果产物）。
- `BoardroomAgentRuntimePortAdapter`（Boardroom 智能体运行时端口适配器）已原样透传 `AgentRunResult`，不添加 Boardroom governance fields（治理字段）。
- minimal fake loop（最小假模型循环）已真实运行 write -> command fail -> patch -> command pass -> submit 路径，并输出 result.json、events.jsonl 和 artifacts。

当前缺口：

- 缺少独立 evidence mapping（证据映射）模块，把事件和产物派生为 Boardroom evidence input（Boardroom 证据输入候选）。
- 缺少可复用 event stream integrity verifier（事件流完整性校验器）。
- 缺少显式 replay status（重放状态）描述；当前不能假装 fully replayable（完全可重放）。
- 缺少 `SourceInventory` lineage（源码清单谱系）派生函数，无法直接按 produced path（产出路径）聚合 provider/tool/workspace 事实。
- 当前 `AgentRunResult.tool_attempts` 不直接包含 command stdout/stderr artifact refs；这些事实存在于 `command.completed` 事件中，需要由 evidence mapper（证据映射器）读取 event stream。

## Review Decisions for Implementation

根据 P2-001 文档评审，实施时采用以下明确语义：

1. replay snapshot（重放快照）字段只读取 `run.started.payload` 的直接字段。`invocation_snapshot` 与 `invocation_snapshot_ref` 等价；`policy_snapshot` 与 `policy_snapshot_ref` 等价；`tool_versions` 与 `tool_versions_ref` 等价。
2. `provider_turn_id`（模型轮次标识）以 `action.parsed`（动作解析）发生时关联的 provider turn（模型轮次）为准。若 action 无法关联到 provider turn，则字段为 `null`，不得 fallback（兜底）到后续或最近的无关模型轮次。
3. `tool_attempts`（工具调用尝试）在 evidence summary（证据摘要）中以 event stream（事件流）为事实源派生。`AgentRunResult.tool_attempts` 保留为 runtime result summary（运行结果摘要）和向后兼容字段，不作为 evidence mapping 的事实源。
4. 同一 path（路径）的多次 workspace mutation（工作区变更）必须保持 hash chain（哈希链）：后一条 mutation 的 `before_hash` 必须等于同一路径前一条 mutation 的 `after_hash`。不匹配时 evidence mapping 必须 fail closed，failure kind 为 `workspace_mutation_hash_chain_mismatch`。
5. event stream verifier（事件流校验器）的错误信息必须包含可定位信息，例如 line number（行号）、sequence（序号）或 event id（事件标识）。本轮不新增日志系统；错误通过 structured failure（结构化失败）返回。
6. 本轮一次性读取 event stream 到内存。streaming verifier（流式校验器）和 event stream size limit（事件流大小限制）记录为后续技术债，不阻塞 P2-001。

## Evidence Summary Boundary

P2-001 必须新增独立 mapper（映射器），推荐入口：

```text
build_evidence_summary(result: AgentRunResult, event_stream_path: Path) -> dict[str, Any]
```

语义：

1. `result` 必须是 `AgentRunResult`（智能体运行结果）。非该类型必须清晰失败。
2. `event_stream_path` 必须指向真实 JSONL event stream。文件缺失、JSON 无效、hash chain 错误、sequence gap（序号断裂）或 `events_hash` 不匹配时，mapper 必须 fail closed（失败关闭），不得返回部分成功 summary。
3. evidence summary 是派生事实，不是新的事实源。它不得修改 event stream、artifact store（产物存储）、workspace（工作区）或 `AgentRunResult`。
4. evidence summary 不得包含 Boardroom governance fields（治理字段），包括：
   - `ticket_completed`
   - `closeout_committed`
   - `governance_status`
   - `evidence_verified`
   - `source_inventory_accepted`
5. evidence summary 可以作为 Boardroom EvidenceVerifier（Boardroom 证据验证器）的输入候选，但不能替代 Boardroom 的验证结论。

## Required Evidence Summary Shape

P2-001 的 evidence summary（证据摘要）必须包含以下顶层字段：

```json
{
  "run_id": "run_001",
  "status": "completed",
  "event_stream": {
    "event_stream_ref": "artifact://run_001/events.jsonl",
    "events_hash": "sha256:...",
    "integrity": {
      "ok": true,
      "event_count": 10,
      "terminal_event_type": "run.completed"
    }
  },
  "provider_attempts": [],
  "tool_attempts": [],
  "workspace_mutations": [],
  "command_results": [],
  "network_fetches": [],
  "source_inventory_lineage": [],
  "artifacts": [],
  "replay": {
    "status": "not_replayable",
    "reasons": ["missing_invocation_snapshot", "missing_policy_snapshot", "missing_tool_versions"]
  }
}
```

字段要求：

- `run_id`、`status`、`event_stream_ref`、`events_hash` 必须来自 `AgentRunResult`，不能从本地默认值推断。
- `provider_attempts` 必须来自 `provider.turn.completed` events（模型轮次完成事件）。
- `tool_attempts` 必须来自 `tool.attempt.started/completed/failed` events（工具调用尝试开始/完成/失败事件），并可与 `AgentRunResult.tool_attempts` 交叉引用。
- `workspace_mutations` 必须来自 `workspace.mutation.recorded` events（工作区变更记录事件），并补齐 action/provider lineage（动作/模型轮次谱系）。
- `command_results` 必须来自 `command.completed` events（命令完成事件）。
- `network_fetches` 必须来自 `network.fetch.completed` events（网络获取完成事件）。
- `source_inventory_lineage` 必须按 submitted produced paths（已提交产出路径）聚合 workspace mutations。
- `artifacts` 必须来自 `AgentRunResult.artifacts`，作为已有产物清单引用；mapper 不重新写入产物。
- `replay` 必须显式说明当前是否可重放及原因。

## Event Stream Integrity Requirements

新增 event stream integrity verifier（事件流完整性校验器）必须满足：

1. 读取完整 JSONL 文件；空文件必须失败。
2. 每一行必须是 JSON object（JSON 对象）；解析失败必须返回显式失败。
3. 每个 event（事件）必须包含 `sequence`、`event_hash` 和 `previous_event_hash` 字段。
4. `sequence` 必须从 1 开始连续递增。
5. 第一条事件的 `previous_event_hash` 必须为 `null`。
6. 第 N 条事件的 `previous_event_hash` 必须等于第 N-1 条事件的 `event_hash`。
7. 每条 `event_hash` 必须按 `event-stream-protocol.md` 的 canonical JSON（规范化 JSON）重新计算并匹配。
8. 整体 `events_hash` 必须对 event stream 文件原始 bytes（字节）计算，并与 `AgentRunResult.events_hash` 匹配。
9. 最后一条事件必须是 `run.completed` 或 `run.failed`；否则 integrity verifier 必须返回 explicit failure（显式失败）。
10. verifier 可以返回 structured failure（结构化失败），但 `build_evidence_summary` 不得在 integrity failure（完整性失败）时继续构造成功 summary。
11. verifier 的 failure message（失败信息）必须包含可定位信息：文件读取失败说明 path（路径），JSON 解析失败说明 line number（行号），hash / sequence 错误说明 sequence（序号）或 event id（事件标识）。
12. verifier 必须覆盖文件不存在、空文件、非 UTF-8、JSON 解析失败、非 JSON object（非 JSON 对象）、sequence gap（序号断裂）、previous hash mismatch（前序哈希不匹配）、event hash mismatch（事件哈希不匹配）、events hash mismatch（事件流哈希不匹配）和 missing terminal event（缺少终止事件）。

推荐 failure kinds（失败类型）：

- `event_stream_missing`
- `event_stream_unreadable`
- `event_stream_empty`
- `event_json_invalid`
- `event_schema_invalid`
- `event_sequence_gap`
- `event_previous_hash_mismatch`
- `event_hash_mismatch`
- `events_hash_mismatch`
- `event_terminal_missing`

## Replay Status Requirements

P2-001 不实现 full replay engine（完整重放引擎），但必须满足 roadmap（路线图）中“可重放或明确说明不可重放原因”的要求。

当前 replay status（重放状态）规则：

- 如果 event stream 只有 `run.started` 中的 `event_protocol_version` 和 `invocation_id`，但缺少完整 invocation snapshot（调用快照）、policy snapshot（策略快照）和 tool versions（工具版本），必须返回：

```json
{
  "status": "not_replayable",
  "reasons": ["missing_invocation_snapshot", "missing_policy_snapshot", "missing_tool_versions"]
}
```

- 如果 future event protocol（未来事件协议）新增 snapshot events（快照事件）或在 `run.started.payload` 中加入直接 snapshot 字段 / snapshot refs（快照引用），可以扩展为 `replayable`，但必须先更新 event stream protocol（事件流协议）或新增 ADR（架构决策记录）说明兼容性。
- replay status 只检查 `run.started.payload` 的直接字段，不读取嵌套 payload。有效字段组合是：`invocation_snapshot` 或 `invocation_snapshot_ref`，`policy_snapshot` 或 `policy_snapshot_ref`，`tool_versions` 或 `tool_versions_ref`。
- 如果只存在部分 snapshot 信息，`reasons` 必须只列出仍缺失的类别。例如只有 `invocation_snapshot_ref` 时，返回 `missing_policy_snapshot` 和 `missing_tool_versions`。
- 不得返回空 reasons（原因列表）或模糊值来掩盖不可重放状态。

## Workspace Mutation Evidence Requirements

每条 workspace mutation evidence（工作区变更证据候选）必须包含：

- `event_id`（事件标识）
- `tool_attempt_id`（工具调用尝试标识）
- `action_id`（动作标识）
- `tool`（工具名）
- `provider_turn_id`（模型轮次标识，如可从事件顺序派生）
- `path`（工作区相对路径）
- `before_hash`（变更前哈希，可为 null）
- `after_hash`（变更后哈希）
- `diff` artifact reference（差异产物引用）

要求：

- `after_hash` 必须是 `sha256:<64 lowercase hex>`。
- `before_hash` 非 null 时也必须是 `sha256:<64 lowercase hex>`。
- `diff` 必须是合法 artifact payload（产物载荷），包含 artifact ref、sha256、size bytes 和 truncated flag（截断标记）。
- 如果无法把 mutation（变更）关联到已开始的 tool attempt（工具调用尝试），mapper 必须显式失败或在 integrity 阶段暴露不一致，不得静默丢弃。
- 同一路径多次 mutation 必须保持 hash chain（哈希链）：后一条 mutation 的 `before_hash` 必须等于同一路径前一条 mutation 的 `after_hash`；否则 `build_evidence_summary` 必须以 `workspace_mutation_hash_chain_mismatch` 失败。
- mutation 顺序以 event stream sequence（事件流序号）为准，不按 path 字典序、artifact 名称或 result summary（结果摘要）重排。

## Command Evidence Requirements

每条 command result evidence（命令结果证据候选）必须包含：

- `event_id`
- `tool_attempt_id`
- `command_id`
- `exit_code`
- `stdout` artifact payload
- `stderr` artifact payload

要求：

- `command_id` 必须是非空稳定标识，不能是 shell string（自由命令字符串）。
- `exit_code` 必须是 integer（整数）。
- stdout/stderr artifact payload 必须包含 `sha256`，并且哈希格式合法。
- 命令失败的非零 exit code 仍是有效 command evidence；不能把非零 exit code 静默转换为成功或丢弃。

## Network Fetch Evidence Requirements

每条 network fetch evidence（网络获取证据候选）必须包含：

- `event_id`
- `tool_attempt_id`
- `url`
- `status_code`
- `response` artifact payload

要求：

- 只映射已经通过 NetworkPolicy（网络策略）并真实执行的 `network.fetch.completed` 事件。
- 网络拒绝场景不会有 `network.fetch.completed` 事件；拒绝事实应保留在 `permission.decided` 和 `action.rejected` 事件中。
- response artifact payload 必须包含 `sha256`。

## SourceInventory Lineage Requirements

`source_inventory_lineage`（源码清单谱系）必须从 `result.submitted` event（结果提交事件）的 `produced_paths`（产出路径）派生。

每个 produced path 必须生成一个 lineage entry（谱系条目）：

```json
{
  "path": "work/output.txt",
  "lineage_status": "traceable",
  "latest_after_hash": "sha256:...",
  "mutation_refs": [
    {
      "event_id": "evt_000008",
      "tool_attempt_id": "tool_attempt_000001",
      "action_id": "step-0001",
      "tool": "write_file",
      "provider_turn_id": "provider_turn_000001",
      "before_hash": null,
      "after_hash": "sha256:...",
      "diff": {"artifact_ref": "artifact://run_001/diffs/tool_attempt_000001.diff", "sha256": "sha256:..."}
    }
  ],
  "diff_artifact_refs": [
    {"artifact_ref": "artifact://run_001/diffs/tool_attempt_000001.diff", "sha256": "sha256:..."}
  ]
}
```

如果 produced path 没有对应 workspace mutation（工作区变更），必须生成：

```json
{
  "path": "work/output.txt",
  "lineage_status": "missing_workspace_mutation",
  "latest_after_hash": null,
  "mutation_refs": [],
  "diff_artifact_refs": []
}
```

不得静默删除 missing lineage（缺失谱系）条目，因为这会让 Boardroom OS 无法区分“没有源码产物”和“源码产物缺少证据”。

## Security and No-Fallback Rules

- 不得用 provider output（模型输出）或 human-readable summary（人类可读摘要）单独作为 implementation evidence（实现证据）。
- 不得在 event stream integrity failure（事件流完整性失败）时构造成功 evidence summary。
- 不得补造 artifact hash（产物哈希）；只能使用真实 artifact payload 中已有 hash，或对 event stream bytes 真实计算整体 hash。
- 不得从 `.env`、environment variables（环境变量）或本地配置补齐 policy、provider、tool、workspace 或 evidence 字段。
- 不得引入 default allow-all（默认全允许）或默认 replayable（默认可重放）。
- 不得吞掉 JSON 解析、hash mismatch（哈希不匹配）、sequence gap 或 missing terminal event（缺少终止事件）。
- 不得添加 Boardroom governance fields（治理字段）或把 runtime `completed`（运行完成）解释为 Boardroom closeout（Boardroom 收尾）成功。

## Documentation Requirements

创建本规格和对应实施计划时，必须更新：

- `docs/04-implementation-spec/INDEX.md`：加入本 draft spec（草案规格）。
- `docs/04-implementation-plan/INDEX.md`：加入对应 draft plan（草案计划）。
- `docs/04-implementation-backlog/backlog.md`：P2-001 的依据中加入本规格。
- `docs/INDEX.md`：如将本规格 / 计划作为当前活跃评审或实施入口，加入 Current Active Documents（当前活跃文档指针）。

P2-001 实现完成且验证通过后，必须更新：

- `docs/04-implementation-backlog/backlog.md`：将 P2-001 标记为 `completed`。
- 本规格状态从 `draft` 改为 `implemented`。
- 对应 plan（实施计划）状态从 `draft` 改为 `implemented`。
- `docs/04-implementation-spec/INDEX.md` 和 `docs/04-implementation-plan/INDEX.md`：将本规格 / 计划移入 Completed / Archived Documents（已完成 / 已归档文档）。
- `docs/INDEX.md`：移除本规格 / 计划的 active pointers（当前活跃指针），除非仍有未完成评审事项。

## Acceptance Criteria

P2-001 完成时必须证明：

- `src/atomic_agent/evidence.py` 存在，并提供 event stream integrity verification（事件流完整性校验）和 evidence summary mapping（证据摘要映射）入口。
- 有效 JSONL event stream 能通过完整性校验，并返回 event count（事件数量）、terminal event type（终止事件类型）和 `events_hash`。
- 篡改 sequence（序号）、`previous_event_hash`、`event_hash` 或整体 `events_hash` 时，校验器显式失败。
- 文件不存在、空文件、非 UTF-8、JSON 解析失败和非 JSON object 输入均有显式失败测试。
- replay status 覆盖全部缺失、部分 snapshot 存在、`*_snapshot_ref` 等价字段存在和全部 replay metadata 存在的边界场景。
- 同一路径三次以上 workspace mutation 保持事件顺序，且 before/after hash chain 断裂时显式失败。
- `build_evidence_summary(result, event_stream_path)` 在 event stream 完整且 hash 匹配时返回 provider attempts、tool attempts、workspace mutations、command results、network fetches、source inventory lineage、artifacts 和 replay status。
- `build_evidence_summary` 在 event stream integrity failure 时 fail closed，不返回误导性成功 summary。
- workspace mutation evidence 保留 before/after hash 和 diff artifact hash。
- command evidence 保留 exit code、stdout artifact hash 和 stderr artifact hash。
- produced path 能追溯到 provider turn、action、tool attempt 和 workspace mutation。
- missing produced path mutation（产出路径缺少变更）被显式标记为 `missing_workspace_mutation`，不得静默丢弃。
- replay status 在当前 snapshot 缺失时明确为 `not_replayable` 并列出原因。
- evidence summary 不包含 Boardroom governance fields（治理字段）。
- minimal fake loop（最小假模型循环）集成测试证明真实运行输出可被 evidence mapper 映射。
- `PYTHONPATH=src python -m pytest tests/test_evidence.py -q` 通过。
- `PYTHONPATH=src python -m pytest tests/test_minimal_fake_loop_example.py -q` 通过。
- `PYTHONPATH=src python -m pytest -m permission_negative -q` 通过。
- `PYTHONPATH=src python -m pytest -q` 通过。

## Self-Review Result

- Spec coverage（规格覆盖）：已覆盖 backlog P2-001、M4 exit criteria（M4 退出标准）、event stream integrity（事件流完整性）、artifact hash（产物哈希）、workspace mutation（工作区变更）、command result（命令结果）、network fetch（网络获取）、SourceInventory lineage（源码清单谱系）、replay status（重放状态）、文档更新和测试验收。
- Placeholder scan（占位符扫描）：未使用占位标记、空泛“稍后补充”或不可验证成功条件；每项输出和失败语义均给出具体字段或 failure kind（失败类型）。
- Type / naming consistency（类型与命名一致性）：`AgentRunResult`、`EventRecorder`、`ArtifactWriter`、`workspace.mutation.recorded`、`command.completed`、`network.fetch.completed`、`SourceInventory` 等命名与现有代码和权威文档一致。
- Scope check（范围检查）：未纳入 Boardroom EvidenceVerifier、closeout gate、real provider integration、external coding agent bridge、完整重放引擎、新工具、新权限策略或契约破坏性变更。
- No-fallback check（无兜底检查）：明确禁止事件完整性失败后继续成功映射、补造 hash、默认可重放、环境配置补齐、治理字段和第二事实源。
