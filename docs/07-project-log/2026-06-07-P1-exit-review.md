# P1 Exit Review

## Status

completed

## Purpose

本文记录 `atomic-agent`（原子智能体）P1 execution wave（P1 执行波次）退出复审。复审目标是确认 P1 completed（已完成）状态是否有真实测试、示例、集成和文档证据支撑，并滚动形成下一批 P2 cohesive work packages（内聚工作包）。

## Review Inputs

- `README.md`（项目入口说明）
- `AGENTS.md`（文档治理规则）
- `docs/INDEX.md`（文档总索引）
- `docs/04-implementation-backlog/backlog.md`（实现待办）
- `docs/04-implementation-spec/mvp-runtime-spec.md`（MVP 运行时规格）
- `docs/04-implementation-acceptance/mvp-acceptance.md`（MVP 验收标准）
- `docs/05-testing/testing-strategy.md`（测试策略）
- `docs/06-roadmap/roadmap.md`（路线图）
- `docs/03-contracts/agent-runtime-port.md`（智能体运行时端口契约）
- `docs/03-contracts/agent-action-protocol.md`（智能体动作协议）
- `docs/03-contracts/event-stream-protocol.md`（事件流协议）
- `docs/02-architecture/event-and-evidence-architecture.md`（事件与证据架构）
- Current tests under `tests/`（测试目录）
- Current runtime source under `src/atomic_agent/`（运行时源码目录）

## Verification Evidence

| Check | Result | Notes |
|---|---|---|
| P1 backlog states | passed | `docs/04-implementation-backlog/backlog.md` marks P1-001 through P1-004 as `completed`. |
| P1 spec / plan indexes | passed | `docs/04-implementation-spec/INDEX.md` and `docs/04-implementation-plan/INDEX.md` list P1-001 through P1-004 in completed / archived sections. |
| Full test suite | passed | `python -m pytest -q`: 310 passed in 11.63s. |
| Permission negative gate | passed | `python -m pytest -m permission_negative -q`: 50 passed, 260 deselected in 1.17s. |
| Boardroom adapter tests | passed | `python -m pytest /Users/bill/projects/atomic-agent/tests/test_runtime_port.py -q`: 7 passed in 0.15s. |
| README minimal example | passed | Documented command ran successfully and returned `status: completed`, result path, event stream path, artifact root and workspace output path. |
| Event stream content | passed | Minimal example event stream contains required event types and 35 events. |
| Workspace output | passed | `/tmp/atomic-agent-minimal-example/workspace/work/output.txt` final content is `fixed`. |
| Workspace mutation evidence | passed | Minimal example event stream contains 2 `workspace.mutation.recorded` events with hash and diff payloads. |
| Command artifact evidence | passed | Minimal example event stream contains 2 `command.completed` events with stdout/stderr artifact hashes. |
| Pre-update git status | passed | Only P1 exit gate spec / plan and their directory indexes were changed before final review documentation updates. |

## P1 Completed Scope

P1 completed integration and network hardening work:

- `web_fetch`（网络获取） and `NetworkPolicy`（网络策略）.
- Consolidated permission negative gate（权限负向门禁） covering path traversal（路径逃逸）, symlink escape（符号链接逃逸）, allowed write set（允许写入集合）, undeclared command（未声明命令）, free shell string（自由命令字符串）, network deny（网络拒绝）, missing network policy（缺失网络策略）, invalid provider JSON（无效模型 JSON）, unknown action（未知动作）, max steps（最大步数） and observation truncation（观察截断） scenarios.
- Fake provider loop acceptance（假模型供应商循环验收） and real README minimal example（最小示例） command path.
- Boardroom `AgentRuntimePort adapter`（Boardroom 智能体运行时端口适配器） that passes `AgentInvocation`（智能体调用请求） to the runner, returns `AgentRunResult`（智能体运行结果） unchanged, rejects invalid invocation / runner outputs, propagates runner exceptions, and does not add Boardroom governance completion（治理完成） fields.

## Milestone Matrix

| Milestone criterion | Status | Evidence / gap |
|---|---|---|
| M1: fake provider loop（假模型供应商循环） | satisfied | README minimal example ran a real multistep fake provider loop and produced result, event stream, artifacts and workspace output. |
| M1: filesystem tools（文件系统工具） | satisfied | Minimal example exercised `write_file` and `apply_patch`; P0/P1 test suite remains passing. |
| M1: AgentAction JSON schema validation（JSON 模式校验） | satisfied | Full test suite and permission negative gate passed, including invalid provider JSON / unknown action coverage. |
| M1: JSONL event stream（JSONL 事件流） | satisfied | Minimal example produced `events.jsonl`; event stream content check found required run, provider, action, permission, tool, mutation, command, result and terminal events. |
| M1: workspace root and allowed write set guard（工作区根目录和允许写入集合守卫） | satisfied | Permission negative gate passed path traversal, symlink and allowed write set denial scenarios. |
| M2: run_command only accepts command_id（只接受命令标识） | satisfied | Permission negative gate passed undeclared command and free shell string denial scenarios; minimal example executed declared `check-output` command. |
| M2: web_fetch with NetworkPolicy（网络策略） | satisfied | P1-001 is completed and permission negative gate passed network deny and missing network policy scenarios. |
| M2: permission negative tests（权限负向测试） | satisfied | `python -m pytest -m permission_negative -q` passed with 50 tests. |
| M2: budgets and invalid actions fail closed（预算和无效动作失败关闭） | satisfied | Full suite and permission negative gate passed max steps, invalid provider JSON, unknown action and observation truncation scenarios. |
| M3: AgentRuntimePort adapter（智能体运行时端口适配器） | satisfied | `tests/test_runtime_port.py` passed; adapter accepts `AgentInvocation`, returns completed / failed `AgentRunResult` unchanged, rejects invalid types and avoids governance completion fields. |
| M4: event stream replayability（事件流可重放性） | partially_satisfied | Event stream has ordered events, sequence numbers and hashes; replayability or explicit non-replay rationale is not yet specified as a completed M4 contract. |
| M4: workspace mutation hash / diff（工作区变更哈希 / 差异） | partially_satisfied | Minimal example contains mutation events with hash and diff payloads; P2 should harden before/after hash semantics and Boardroom evidence mapping. |
| M4: command stdout/stderr artifact hash（命令输出产物哈希） | partially_satisfied | Minimal example command events include stdout/stderr artifact hashes; P2 should verify mapping requirements against Boardroom evidence inputs. |
| M4: SourceInventory lineage（源码清单谱系） | not_satisfied | Boardroom `SourceInventory`（源码清单） traceability to provider/tool/workspace lineage is not yet implemented or accepted. |
| M5: external coding agent bridge（外部编码智能体桥接） | not_started | No external coding agent bridge should start before M4 evidence mapping is hardened. |

## Real Provider Integration Decision

Real provider integration tests（真实模型供应商集成测试） should enter P2 as a minimal integration gate after event/evidence hardening begins. They should be manual/nightly or integration-profile tests, not base CI requirements, because provider availability and model output variance should not destabilize the minimum CI gate（最小持续集成门禁）.

The P2 real provider gate should only prove that a real provider can emit at least one legal `AgentAction`（智能体动作）, that runtime executes or rejects it under permission policy（权限策略）, and that events and errors are recorded with fail-closed（失败关闭） behavior. It must not require the model to produce a complete project in one response.

## Existing Deferred P2 Item Handling

| Existing item | Decision | Rationale |
|---|---|---|
| native tool calling adapter（原生工具调用适配器） | keep outside immediate P2 batch | ADR-0002 keeps native tool calling adapter as a later provider adapter option; it is not removed from roadmap-level possibilities but is not the next cohesive work package. |
| service runner / HTTP probe（服务运行与 HTTP 探测） | keep outside immediate P2 batch | It remains a later extension idea and is lower priority than M4 evidence mapping. |
| external coding agent bridge（外部编码智能体桥接） | keep deferred with clearer next output | P2 should first produce a design spec（设计规格） or ADR（架构决策记录） for evidence import protocol（证据导入协议） and permission boundary（权限边界） before any bridge implementation. |

## ADR Requirement Check

No ADR is required for this exit gate. The review does not change the planned endpoint, Boardroom governance source-of-truth boundary, event/evidence model principles or permission model principles. It only reorganizes near-term P2 work packages under the existing roadmap and accepted ADRs.

## Known Gaps

1. M4 event stream / evidence mapping（事件流 / 证据映射） needs hardening around replayability, before/after hashes, command artifact hashes and `SourceInventory`（源码清单） lineage.
2. Real provider integration（真实模型供应商集成） is not part of base CI and should be introduced as a minimal optional integration gate.
3. External coding agent bridge（外部编码智能体桥接） remains deferred until evidence import and permission boundaries are explicit.

## P2 Work Package Proposal

| ID | Task | Dependencies | Acceptance |
|---|---|---|---|
| P2-001 | 完善 event stream / evidence mapping（事件流 / 证据映射）和 artifact hash（产物哈希）硬化 | P1 event stream, artifacts, command tool, filesystem mutation and Boardroom adapter | Workspace mutations include traceable before/after hash and diff references; command evidence exposes stdout/stderr artifact hashes; Boardroom evidence input can trace source files to provider/tool/workspace lineage. |
| P2-002 | 建立 real provider minimal integration gate（真实模型供应商最小集成门禁） | P2-001 evidence expectations; existing provider-agnostic action protocol（供应商无关动作协议） | A real provider emits at least one legal `AgentAction`; runtime executes or rejects it under policy; events and errors are recorded; gate is manual/nightly or integration-profile, not base CI. |
| P2-003 | 设计 external coding agent bridge（外部编码智能体桥接）的证据导入协议和权限边界 | P2-001 evidence hardening; P2-002 integration findings; ADR-0002 and roadmap M5 | Produces a design spec or ADR before implementation; bridge remains deferred until external agent diffs, logs and command results can be imported without bypassing permission policy. |

## Review Conclusion

P1 Exit Gate is completed. M1, M2 and M3 are satisfied. M4 is partially satisfied and should drive the next P2 work package ordering. M5 remains not started and deferred until M4 evidence mapping is hardened.
