# P0 Exit Review

## Status

completed

## Purpose

本文记录 `atomic-agent`（原子智能体）P0 execution wave（P0 执行波次）退出复审。复审目标是确认 P0 completed（已完成）状态是否有真实测试、实现和文档证据支撑，并滚动形成下一批 P1 cohesive work packages（内聚工作包）。

## Review Inputs

- `README.md`（项目入口说明）
- `AGENTS.md`（文档治理规则）
- `docs/INDEX.md`（文档总索引）
- `docs/04-implementation-backlog/backlog.md`（实现待办）
- `docs/04-implementation-spec/mvp-runtime-spec.md`（MVP 运行时规格）
- `docs/04-implementation-acceptance/mvp-acceptance.md`（MVP 验收标准）
- `docs/05-testing/testing-strategy.md`（测试策略）
- `docs/06-roadmap/roadmap.md`（路线图）
- `docs/03-contracts/agent-action-protocol.md`（智能体动作协议）
- `docs/03-contracts/event-stream-protocol.md`（事件流协议）
- Current tests under `tests/`（测试目录）
- Current runtime source under `src/atomic_agent/`（运行时源码目录）

## Verification Evidence

| Check | Result | Notes |
|---|---|---|
| P0 backlog states | passed | P0-001 through P0-008 are marked `completed`. |
| P0 spec / plan indexes | passed | P0 implementation specs and plans are marked implemented / completed and removed from active implementation pointers. |
| Full test suite | passed | `pytest -v` completed successfully: 231 tests passed. |
| Negative test inventory | passed | Existing P0 tests cover most negative scenarios; P1-002 should consolidate the gate and add the network deny scenario after NetworkPolicy exists. |
| README minimal example | gap | README still describes no runnable minimal example; this must not be changed to a fake command. It should become a P1 docs / entrypoint work item only after a real CLI command is verified. |

## Negative Test Inventory

| Scenario | Current coverage | P1 action |
|---|---|---|
| `../outside.md` path escape（路径逃逸） | covered | Reuse existing path / filesystem tests in a consolidated gate. |
| symlink escape（符号链接逃逸） | covered | Reuse existing path / filesystem / artifact tests in a consolidated gate. |
| write outside allowed write set（写入允许集合外路径） | covered | Reuse existing path / filesystem / AgentLoop tests. |
| undeclared shell string / command（未声明 shell 字符串 / 命令） | covered | Reuse action parser, model, command policy and AgentLoop tests. |
| unallowed URL（未允许 URL） | gap | Implement after P1-001 `NetworkPolicy`（网络策略） exists, then add to P1-002 gate. |
| invalid JSON（无效 JSON） | covered | Reuse action parser and AgentLoop fail-closed tests. |
| unknown action（未知动作） | covered | Reuse action parser and model tests. |
| max steps exceeded（超过最大步数） | covered | Reuse AgentLoop budget tests. |
| observation truncation（观察截断） | covered | Reuse AgentLoop, artifact, command and filesystem truncation tests. |

## P0 Completed Scope

P0 completed the runtime foundation needed for a minimal auditable loop:

- Core data models（核心数据模型）: `AgentInvocation`（智能体调用请求）, `AgentRunResult`（智能体运行结果）, `AgentAction`（智能体动作）, `AgentEvent`（智能体事件）.
- JSON action parser（JSON 动作解析器） with strict schema validation（严格模式校验）.
- Workspace path guard（工作区路径守卫） including root and allowed write set（允许写入集合） boundaries.
- Filesystem tools（文件系统工具）: `list_files`, `read_file`, `search_files`, `write_file`, `apply_patch`.
- Command policy（命令策略） and `run_command` restricted to declared `command_id`（命令标识）.
- Event recorder（事件记录器） and JSONL event stream（JSONL 事件流）.
- Minimal `AgentLoop`（最小智能体循环） with fake provider（假模型供应商） semantics, tool observations（工具观察）, artifacts（产物）, workspace mutations（工作区变更）, and terminal result（终止结果）.
- Fail-closed budget limits（失败关闭预算限制）, including max steps（最大步数）, parse retry limit（解析重试限制）, observation truncation（观察截断） and max wall seconds（最大墙钟秒数）.

## Milestone Matrix

| Milestone criterion | Status | Evidence / gap |
|---|---|---|
| M1: fake provider loop（假模型供应商循环） | satisfied | `tests/test_agent_loop.py` covers multistep deterministic fake provider loop. |
| M1: filesystem tools（文件系统工具） | satisfied | Filesystem tool tests and AgentLoop tests cover list/read/search/write/patch behavior. |
| M1: AgentAction JSON schema validation（JSON 模式校验） | satisfied | Action parser and model tests cover strict parsing and invalid action rejection. |
| M1: JSONL event stream（JSONL 事件流） | satisfied | Event recorder tests and AgentLoop event assertions cover event hash chain and terminal events. |
| M1: workspace root and allowed write set guard（工作区根目录和允许写入集合守卫） | satisfied | Path guard and filesystem tests cover root / write boundary behavior. |
| M2: run_command only accepts command_id（只接受命令标识） | satisfied | Command policy / command tool tests and action model validation reject free shell command fields. |
| M2: web_fetch with NetworkPolicy（网络策略） | not_satisfied | `web_fetch` currently exists as action type but AgentLoop denies it because P1 network policy is not implemented. |
| M2: permission negative tests（权限负向测试） | partially_satisfied | Existing tests cover most denials; P1 must consolidate a single negative gate and add network deny after P1-001. |
| M2: budgets and invalid actions fail closed（预算和无效动作失败关闭） | satisfied | P0-008 tests cover invalid budgets, max steps, invalid JSON retry exhaustion, and max wall seconds. |
| M3: AgentRuntimePort adapter（智能体运行时端口适配器） | not_started | Contract exists, but adapter implementation and Boardroom mapping tests are not implemented. |

## Known Gaps

1. `web_fetch`（网络获取） and `NetworkPolicy`（网络策略） are not implemented.
2. Permission negative tests（权限负向测试） need a single P1 gate that inventories existing coverage, reuses covered scenarios, and adds network deny（网络拒绝） after NetworkPolicy exists.
3. README minimal example（最小示例） is stale relative to P0 implementation progress, but must only be updated after a real CLI command exists, runs successfully, produces a JSONL event stream（JSONL 事件流）, and demonstrates at least one successful fake provider loop（假模型供应商循环）.
4. Boardroom `AgentRuntimePort adapter`（智能体运行时端口适配器） is not started.
5. Real provider integration tests（真实模型供应商集成测试） remain out of base CI and should be considered in a later P wave or integration profile.

## P1 Work Package Proposal

| ID | Task | Dependencies | Acceptance |
|---|---|---|---|
| P1-001 | 实现 `web_fetch` 和 `NetworkPolicy`（网络策略） | Existing action protocol（动作协议）, event recorder（事件记录器）, AgentLoop（智能体循环） | Allowed URLs fetch successfully; unallowed URLs deny and record events; no silent network fallback. |
| P1-002 | 整合现有 permission negative tests（权限负向测试）为单一门禁，并补齐网络拒绝场景 | P1-001 for network deny; existing path / command / parser / budget behavior | Negative matrix in `testing-strategy.md` is inventoried, existing coverage is reused, and only gaps are added; unallowed URL denial is covered after NetworkPolicy exists. |
| P1-003 | 固化 fake provider loop acceptance（假模型供应商循环验收）并建立真实 minimal example（最小示例）文档路径 | Existing AgentLoop tests; stable invocation construction | README and docs list a real command only after a CLI entrypoint runs successfully, produces a real JSONL event stream, and demonstrates at least one successful fake provider loop. |
| P1-004 | 实现 Boardroom `AgentRuntimePort adapter`（智能体运行时端口适配器） | Stable runtime result / evidence semantics from P1-001 to P1-003 | Boardroom invocation maps to `AgentInvocation`; result maps to evidence input; runtime does not declare ticket completion. |

## Review Conclusion

P0 Exit Gate is completed. M1 is satisfied, M2 is partially satisfied with explicit P1 follow-up work, and M3 remains not started. The next implementation work should start from P1-001 unless the user chooses to prioritize the README / minimal example work package first.
