# P0 Exit Gate Roadmap Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the P0 Exit Gate `roadmap review`（路线图复审）, record the review as project log（项目日志）, and roll the next P1 execution wave（P1 执行波次） into coherent work packages.

**Architecture:** Treat the gate as a documentation and verification workflow, not as runtime feature implementation. The project log records review evidence and milestone classification; backlog remains the authoritative implementation queue; indexes remain the authoritative document navigation layer.

**Tech Stack:** Markdown（文档）, pytest（测试验证）, git status（工作区审计）, existing docs governance（现有文档治理）, Python test suite（Python 测试套件）.

**Status:** implemented

---

## Scope

This plan implements only P0 Exit Gate（P0 退出门禁） review and documentation updates.

In scope:

- Verify P0 completed state against backlog（待办）, specs（规格）, plans（计划）, tests（测试）, and implementation evidence（实现证据）.
- Run real verification commands, especially `pytest -v`.
- Create `docs/07-project-log/2026-06-05-P0-exit-review.md`（P0 退出复审日志）.
- Update `docs/07-project-log/INDEX.md`（项目日志索引）.
- Update `docs/04-implementation-backlog/backlog.md`（实现待办） with P0 Exit Gate conclusion and revised P1 work packages.
- Update `docs/04-implementation-spec/INDEX.md` and `docs/04-implementation-plan/INDEX.md` for this spec / plan lifecycle.
- Update `docs/INDEX.md` only if active document pointers or reading paths change.

Out of scope:

- No `web_fetch`（网络获取） implementation.
- No `NetworkPolicy`（网络策略） implementation.
- No Boardroom `AgentRuntimePort adapter`（智能体运行时端口适配器） implementation.
- No runtime code changes.
- No README minimal example（最小示例） command unless a real command is verified during review and explicitly accepted for docs update.
- No commit unless the user explicitly requests it.

## File Structure

- Create: `docs/07-project-log/2026-06-05-P0-exit-review.md`
  - Records review evidence, P0 completion facts, M1/M2/M3 milestone matrix（里程碑矩阵）, known gaps（已知缺口）, and P1 work package proposal（P1 工作包建议）.
- Modify: `docs/07-project-log/INDEX.md`
  - Adds the review log to Completed / Archived Documents（已完成 / 已归档文档） because project logs are audit records, not active implementation facts.
- Modify: `docs/04-implementation-backlog/backlog.md`
  - Adds P0 Exit Gate result and updates P1 task set/order/scope/basis/dependencies/acceptance.
- Modify: `docs/04-implementation-spec/P0-exit-gate-roadmap-review-spec.md`
  - Changes status from `draft` to `implemented` after review is complete.
- Modify: `docs/04-implementation-plan/P0-exit-gate-roadmap-review-plan.md`
  - Changes status from `draft` to `implemented` after review is complete.
- Modify: `docs/04-implementation-spec/INDEX.md`
  - Moves the P0 Exit Gate spec from Current Active Documents（当前活跃文档） to Completed / Archived Documents.
- Modify: `docs/04-implementation-plan/INDEX.md`
  - Moves this plan from Current Active Documents to Completed / Archived Documents.
- Modify if needed: `docs/INDEX.md`
  - Updates active pointers only if P0 Exit Gate spec / plan or P1 work package changes affect global reading guidance.

---

### Task 1: Verify gate prerequisites and collect raw evidence

**Files:**

- Read: `docs/04-implementation-backlog/backlog.md`
- Read: `docs/06-roadmap/roadmap.md`
- Read: `docs/04-implementation-spec/INDEX.md`
- Read: `docs/04-implementation-plan/INDEX.md`
- Read: `README.md`
- Verify: test suite and git status

- [ ] **Step 1: Confirm P0 backlog states**

Check `docs/04-implementation-backlog/backlog.md` contains these completed rows:

```markdown
| P0-001 | 定义核心数据模型：AgentInvocation、AgentRunResult、AgentAction、AgentEvent | completed | `docs/03-contracts/` |
| P0-002 | 实现 JSON action parser（JSON 动作解析器）和严格 schema validation（模式校验） | completed | `agent-action-protocol.md` |
| P0-003 | 实现 workspace path guard（工作区路径守卫） | completed | `P0-003-workspace-path-guard-spec.md`, `permission-and-sandbox-architecture.md` |
| P0-004 | 实现 filesystem tools（文件系统工具）：list/read/search/write/patch | completed | `P0-004-filesystem-tools-spec.md`, `mvp-runtime-spec.md` |
| P0-005 | 实现 command policy（命令策略）和 run_command | completed | `P0-005-command-policy-run-command-spec.md`, `mvp-runtime-spec.md` |
| P0-006 | 实现 event recorder（事件记录器）和 JSONL 输出 | completed | `P0-006-event-recorder-jsonl-spec.md`, `event-stream-protocol.md` |
| P0-007 | 实现最小 AgentLoop（智能体循环） | completed | `P0-007-minimal-agent-loop-spec.md`, `runtime-architecture.md` |
| P0-008 | 实现 fail-closed budget limits（失败关闭预算限制） | completed | `P0-008-fail-closed-budget-limits-spec.md`, `mvp-acceptance.md` |
```

Expected: all P0 rows are completed. If any P0 row is not completed, stop and write blocked review instead of updating P1.

- [ ] **Step 2: Confirm P0 specs and plans are archived / implemented**

Check `docs/04-implementation-spec/INDEX.md` contains completed rows for P0-002 through P0-008, including:

```markdown
| `P0-008-fail-closed-budget-limits-spec.md` | 2026-06-05 | 已实现 P0-008 fail-closed budget limits（失败关闭预算限制），保留为预算语义规格记录 |
```

Check `docs/04-implementation-plan/INDEX.md` contains completed rows for P0-001 through P0-008, including:

```markdown
| `P0-008-fail-closed-budget-limits-plan.md` | 2026-06-05 | 已实施 P0-008 fail-closed budget limits（失败关闭预算限制），保留为 TDD 实施记录 |
```

Expected: no completed P0 implementation spec / plan remains in Current Active Documents（当前活跃文档）.

- [ ] **Step 3: Record README minimal example gap**

Check `README.md` section 3 contains:

```markdown
当前仓库处于 M0 文档与契约初始化阶段，尚未实现可运行的 minimal example（最小示例）。因此现在没有真实的示例命令可以运行；不要用 mock success path（模拟成功路径）或伪命令表示示例已可用。
```

Expected review interpretation: this statement is stale or at least requires review because P0 runtime code now exists, but a real standalone minimal example command may still be absent. Record as a P1 docs / entrypoint（文档 / 入口） gap unless a verified command exists.

- [ ] **Step 4: Inventory existing negative test coverage**

Inspect the current tests under `tests/` and record coverage for the negative scenarios listed in `docs/05-testing/testing-strategy.md`:

```text
../outside.md path escape
symlink escape
write outside allowed write set
undeclared shell string / command
unallowed URL
invalid JSON
unknown action
max steps exceeded
observation truncation
```

Expected review interpretation: mark already-covered scenarios as existing coverage and define P1-002 as consolidation plus gap filling, not a rewrite of all negative tests.

- [ ] **Step 5: Run full tests**

Run:

```bash
pytest -v
```

Expected:

```text
PASSED
```

If tests fail, stop and create the project log with `P0 Exit Gate: blocked` status. Do not update P1 work packages as accepted.

- [ ] **Step 6: Capture working tree status before documentation changes**

Run:

```bash
git status --short
```

Expected at this planning stage may include only the newly created P0 Exit Gate spec / plan / index changes. During implementation, record exact output in the project log.

---

### Task 2: Create P0 exit review project log

**Files:**

- Create: `docs/07-project-log/2026-06-05-P0-exit-review.md`

- [ ] **Step 1: Create project log with status and evidence summary**

Create `docs/07-project-log/2026-06-05-P0-exit-review.md`:

```markdown
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
| Full test suite | passed | `pytest -v` completed successfully during review. |
| Negative test inventory | passed | Existing P0 tests cover most negative scenarios; P1-002 should consolidate the gate and add the network deny scenario after NetworkPolicy exists. |
| README minimal example | gap | README still describes no runnable minimal example; this must not be changed to a fake command. It should become a P1 docs / entrypoint work item only after a real CLI command is verified. |

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
| M2: permission negative tests（权限负向测试） | partially_satisfied | Existing tests cover several denials; P1 must consolidate full negative matrix including network deny and observation truncation. |
| M2: budgets and invalid actions fail closed（预算和无效动作失败关闭） | satisfied | P0-008 tests cover invalid budgets, max steps, invalid JSON retry exhaustion, and max wall seconds. |
| M3: AgentRuntimePort adapter（智能体运行时端口适配器） | not_started | Contract exists, but adapter implementation and Boardroom mapping tests are not implemented. |

## Known Gaps

1. `web_fetch`（网络获取） and `NetworkPolicy`（网络策略） are not implemented.
2. Permission negative tests（权限负向测试） need a single P1 gate covering all required MVP negative scenarios, including network deny（网络拒绝）.
3. README minimal example（最小示例） is stale relative to P0 implementation progress, but must only be updated after a real stable command exists.
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

P0 Exit Gate is completed if the verification evidence above remains true after final documentation updates. The next implementation work should start from P1-001 unless the user chooses to prioritize the README / minimal example work package first.
```

- [ ] **Step 2: If tests failed, use blocked variant instead**

If `pytest -v` failed in Task 1, create the same file with this status and conclusion instead:

```markdown
## Status

blocked

## Review Conclusion

P0 Exit Gate is blocked because `pytest -v` failed. P1 work packages must not be accepted until the failing evidence is fixed and the gate is rerun.

## Recovery Path

1. Fix the failing tests, contradictory evidence, or documentation index issue.
2. Rerun P0 Exit Gate verification, including real `pytest -v`.
3. If the gate remains blocked, record the issue as a project blocker and escalate for human decision; do not lower the acceptance standard silently.
```

Also include the failing command output summary under `Verification Evidence`.

---

### Task 3: Update project log index

**Files:**

- Modify: `docs/07-project-log/INDEX.md`

- [ ] **Step 1: Replace empty completed row with P0 exit review row**

Change:

```markdown
| _None_ | - | 当前没有已完成或归档文档 |
```

To:

```markdown
| `2026-06-05-P0-exit-review.md` | 2026-06-05 | 记录 P0 Exit Gate（P0 退出门禁）复审、里程碑判定和 P1 工作包滚动更新依据 |
```

- [ ] **Step 2: Keep Current Active Documents unchanged**

Ensure `docs/07-project-log/INDEX.md` keeps only `INDEX.md` in Current Active Documents:

```markdown
| `INDEX.md` | active | 本目录索引和文档治理规则 | 进入本目录前 |
```

Project log（项目日志） is an audit record, not an active implementation fact source.

---

### Task 4: Update backlog with P0 gate conclusion and revised P1 packages

**Files:**

- Modify: `docs/04-implementation-backlog/backlog.md`

- [ ] **Step 1: Update P0 Exit Gate section with completed review result**

Replace the current P0 Exit Gate required outputs block:

```markdown
### P0 Exit Gate: Roadmap Review

Trigger（触发条件）：

- P0 表中所有非 deferred（延后）任务均为 completed。
- P0 相关 tests（测试）、acceptance（验收）和 docs（文档）已验证。

Required outputs（必需产物）：

1. 对照 `docs/06-roadmap/roadmap.md` 的 milestone exit criteria（里程碑退出标准），判断 M1/M2 哪些条目已满足、部分满足或失效。
2. 记录当前 P0 完成项是否改变下一阶段优先级。
3. 编制或重组 P1 execution wave（执行波次）。
4. 如长期路线、项目边界或架构原则变化，先新增或更新 ADR。
5. 必要时写入 `docs/07-project-log/`（项目日志）。
```

With:

```markdown
### P0 Exit Gate: Roadmap Review

Status（状态）：completed

Review record（复审记录）：`docs/07-project-log/2026-06-05-P0-exit-review.md`

Conclusion（结论）：

- M1 exit criteria（M1 退出标准）已满足。
- M2 已部分满足：`run_command`（运行声明命令）、预算和无效动作 fail closed（失败关闭）已完成；`web_fetch`（网络获取）、NetworkPolicy（网络策略）和完整 permission negative tests（权限负向测试）仍需进入 P1。
- M3 尚未开始：Boardroom `AgentRuntimePort adapter`（智能体运行时端口适配器）仍需进入 P1 后段。
- README minimal example（最小示例）仍需在真实可运行入口稳定后更新；不得用伪命令或 mock success path（模拟成功路径）替代。
```

- [ ] **Step 2: Replace P1 table with revised work packages**

Replace:

```markdown
| P1-001 | 实现 web_fetch 和 NetworkPolicy（网络策略） | pending | `mvp-runtime-spec.md` |
| P1-002 | 实现 Boardroom AgentRuntimePort adapter（Boardroom 智能体运行时端口适配器） | pending | `agent-runtime-port.md` |
| P1-003 | 实现 fake provider loop tests（假模型供应商循环测试） | pending | `testing-strategy.md` |
| P1-004 | 实现 permission negative tests（权限负向测试） | pending | `testing-strategy.md` |
```

With:

```markdown
| P1-001 | 实现 `web_fetch` 和 NetworkPolicy（网络策略） | pending | `mvp-runtime-spec.md`, `agent-action-protocol.md`, `event-stream-protocol.md` |
| P1-002 | 整合现有 permission negative tests（权限负向测试）为单一门禁，并补齐网络拒绝场景 | pending | `testing-strategy.md`, `mvp-acceptance.md`, `0003-use-fail-closed-permission-model.md` |
| P1-003 | 固化 fake provider loop acceptance（假模型供应商循环验收）并建立真实 minimal example（最小示例）文档路径 | pending | `testing-strategy.md`, `mvp-acceptance.md`, `README.md` |
| P1-004 | 实现 Boardroom AgentRuntimePort adapter（Boardroom 智能体运行时端口适配器） | pending | `agent-runtime-port.md`, `boardroom-os-integration-summary.md`, `0004-keep-boardroom-os-as-governance-source.md` |
```

- [ ] **Step 3: Add P1 dependency notes below the P1 table**

Add this after the P1 table:

```markdown
Dependency notes（依赖说明）：

- P1-002 depends on P1-001 for network deny（网络拒绝） coverage; it should inventory and consolidate existing P0 negative tests instead of rewriting already-covered scenarios.
- P1-003 depends on the existing P0 AgentLoop（智能体循环） and may expose an entrypoint/docs gap; it must not publish a README command until a real CLI command runs successfully, produces JSONL event stream（JSONL 事件流）, and demonstrates at least one successful fake provider loop（假模型供应商循环）.
- P1-004 should run after P1-001 to P1-003 stabilize runtime evidence semantics（运行时证据语义）.
```

---

### Task 5: Update spec and plan indexes for active draft documents

**Files:**

- Modify: `docs/04-implementation-spec/INDEX.md`
- Modify: `docs/04-implementation-plan/INDEX.md`

- [ ] **Step 1: Add active spec entry before execution completes**

In `docs/04-implementation-spec/INDEX.md`, add to Current Active Documents:

```markdown
| `P0-exit-gate-roadmap-review-spec.md` | draft | 定义 P0 Exit Gate（P0 退出门禁）路线图复审、里程碑判定和 P1 工作包滚动更新规则 | 执行 P0 Exit Gate 前 |
```

- [ ] **Step 2: Add active plan entry before execution completes**

In `docs/04-implementation-plan/INDEX.md`, add to Current Active Documents:

```markdown
| `P0-exit-gate-roadmap-review-plan.md` | draft | 实施 P0 Exit Gate（P0 退出门禁）路线图复审和 P1 工作包滚动更新的文档计划 | 执行 P0 Exit Gate 时 |
```

- [ ] **Step 3: After review implementation completes, move spec index entry to completed**

Remove the active spec row added above and add to Completed / Archived Documents:

```markdown
| `P0-exit-gate-roadmap-review-spec.md` | 2026-06-05 | 已完成 P0 Exit Gate（P0 退出门禁）路线图复审规格，保留为阶段门禁规格记录 |
```

- [ ] **Step 4: After review implementation completes, move plan index entry to completed**

Remove the active plan row added above and add to Completed / Archived Documents:

```markdown
| `P0-exit-gate-roadmap-review-plan.md` | 2026-06-05 | 已实施 P0 Exit Gate（P0 退出门禁）路线图复审和 P1 工作包滚动更新，保留为阶段门禁实施记录 |
```

---

### Task 6: Mark spec and plan implemented after review outputs exist

**Files:**

- Modify: `docs/04-implementation-spec/P0-exit-gate-roadmap-review-spec.md`
- Modify: `docs/04-implementation-plan/P0-exit-gate-roadmap-review-plan.md`

- [ ] **Step 1: Mark spec implemented**

Change `docs/04-implementation-spec/P0-exit-gate-roadmap-review-spec.md` from:

```markdown
## Status

draft
```

To:

```markdown
## Status

implemented
```

- [ ] **Step 2: Mark plan implemented**

Change this plan from:

```markdown
**Status:** draft
```

To:

```markdown
**Status:** implemented
```

---

### Task 7: Update docs index if global pointers changed

**Files:**

- Modify if needed: `docs/INDEX.md`

- [ ] **Step 1: Decide whether `docs/INDEX.md` needs a new or updated active pointer**

If `docs/04-implementation-backlog/backlog.md` remains the primary active implementation entry and the P0 Exit Gate spec / plan are moved to completed immediately, no new global pointer is needed.

If the review introduces a new active P1 spec or acceptance document, update `docs/INDEX.md` Current Active Documents accordingly.

Expected for this plan:

```text
No docs/INDEX.md change is required unless the P1 work package update adds or removes active authoritative documents beyond backlog/spec/plan indexes.
```

- [ ] **Step 2: If changing `docs/INDEX.md`, keep reading path semantics consistent**

Do not add project log（项目日志） as an active implementation fact source. It can remain accessible through `docs/07-project-log/INDEX.md`.

---

### Task 8: Final verification and self-review

**Files:**

- Verify: all changed docs
- Verify: test suite

- [ ] **Step 1: Run full tests again after documentation updates**

Run:

```bash
pytest -v
```

Expected:

```text
PASSED
```

- [ ] **Step 2: Check changed files**

Run:

```bash
git status --short
```

Expected changed files:

```text
 M docs/04-implementation-backlog/backlog.md
 M docs/04-implementation-plan/INDEX.md
 M docs/04-implementation-spec/INDEX.md
 M docs/07-project-log/INDEX.md
?? docs/04-implementation-plan/P0-exit-gate-roadmap-review-plan.md
?? docs/04-implementation-spec/P0-exit-gate-roadmap-review-spec.md
?? docs/07-project-log/2026-06-05-P0-exit-review.md
```

`docs/INDEX.md` may appear only if Task 7 found a real global pointer change.

- [ ] **Step 3: Self-review project log against spec**

Check that `docs/07-project-log/2026-06-05-P0-exit-review.md` includes:

```text
Review Inputs
Verification Evidence
P0 Completed Scope
Milestone Matrix
Known Gaps
P1 Work Package Proposal
Review Conclusion
```

Expected: all sections exist and no section contains placeholder wording.

- [ ] **Step 4: Self-review backlog P1 packages**

Check that each P1 row has:

```text
ID
Task
Status
Basis
```

And dependency notes cover:

```text
P1-002 depends on P1-001
P1-003 cannot publish fake README command
P1-004 follows stabilized runtime evidence semantics
```

Expected: all requirements are present.

- [ ] **Step 5: Placeholder scan**

Run the repository placeholder scan command maintained by the project, or use this local equivalent that builds the searched terms without embedding them directly in prose:

```bash
python - <<'PY'
from pathlib import Path
paths = [
    Path('docs/04-implementation-spec/P0-exit-gate-roadmap-review-spec.md'),
    Path('docs/04-implementation-plan/P0-exit-gate-roadmap-review-plan.md'),
    Path('docs/07-project-log/2026-06-05-P0-exit-review.md'),
    Path('docs/04-implementation-backlog/backlog.md'),
]
needles = [
    ''.join(['T', 'B', 'D']),
    ''.join(['T', 'O', 'D', 'O']),
    ' '.join(['fill', 'in']),
    ' '.join(['implement', 'later']),
    ''.join(['待', '补', '充']),
]
for path in paths:
    text = path.read_text(encoding='utf-8')
    for needle in needles:
        if needle in text:
            print(f'{path}: contains placeholder marker')
PY
```

Expected:

```text

```

No output means no obvious placeholder remains.

---

## Self-Review Checklist

Before telling the user the spec / plan are ready for review:

- [ ] Spec coverage: `P0-exit-gate-roadmap-review-spec.md` covers trigger, evidence, negative test inventory, milestone classification, P1 package rules, required outputs, blocked semantics, recovery path, and documentation impact.
- [ ] Plan coverage: this plan includes steps to create the project log, update project log index, update backlog, update spec / plan indexes, mark spec / plan implemented, and verify tests.
- [ ] Placeholder scan: no placeholder markers, vague implementation markers, or fake evidence placeholders remain.
- [ ] Type / name consistency: file names, P1 IDs, milestone statuses, and Chinese / English terminology match across spec, plan, project log, and backlog.
- [ ] Scope check: no runtime code, `web_fetch`, `NetworkPolicy`, Boardroom adapter, real provider integration, or README fake command is included.
- [ ] Governance check: every new authoritative document is indexed in its directory index; project log remains an audit record, not a second implementation fact source.
- [ ] Fail-closed check: failed tests or contradictory P0 evidence block the gate and do not produce a completed P1 rollout.
- [ ] Verification check: `pytest -v`, `git status --short`, and placeholder scan results are recorded or reviewed before completion is claimed.
