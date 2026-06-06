# P1 Exit Gate Roadmap Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the P1 Exit Gate `roadmap review`（路线图复审）, close P1 documentation governance（文档治理）, record the review as project log（项目日志）, and roll the next P2 execution wave（P2 执行波次） into coherent work packages without implementing any P2 task（P2 任务）.

**Architecture:** Treat the gate as a documentation, verification, and planning workflow, not as runtime feature implementation. The project log records review evidence and milestone classification（里程碑判定）; backlog（待办） remains the authoritative implementation queue; indexes（索引） remain the authoritative document navigation layer.

**Tech Stack:** Markdown（文档）, pytest（测试验证）, git status（工作区审计）, existing docs governance（现有文档治理）, Python test suite（Python 测试套件）.

**Status:** implemented

---

## Scope

This plan implements only P1 Exit Gate（P1 退出门禁） review and documentation updates.

In scope:

- Verify P1 completed state against backlog（待办）, specs（规格）, plans（计划）, tests（测试）, README（说明文档）, Boardroom adapter（Boardroom 适配器） and implementation evidence（实现证据）.
- Run real verification commands:
  - `python -m pytest -q`
  - `python -m pytest -m permission_negative -q`
  - `python -m pytest /Users/bill/projects/atomic-agent/tests/test_runtime_port.py -q`
  - README minimal example（最小示例） command.
  - Event stream content check（事件流内容检查） for the README minimal example output.
- Create `docs/07-project-log/2026-06-07-P1-exit-review.md`（P1 退出复审日志）.
- Update `docs/07-project-log/INDEX.md`（项目日志索引）.
- Update `docs/04-implementation-backlog/backlog.md`（实现待办） with P1 Exit Gate conclusion and revised P2 work packages.
- Update `docs/04-implementation-spec/INDEX.md` and `docs/04-implementation-plan/INDEX.md` for this spec / plan lifecycle.
- Update `docs/INDEX.md` only if active document pointers（当前活跃文档指针） or reading paths（阅读路径） change.

Out of scope:

- No event stream / evidence mapping hardening（事件流 / 证据映射硬化） implementation.
- No real provider integration tests（真实模型供应商集成测试） implementation.
- No external coding agent bridge（外部编码智能体桥接） implementation.
- No runtime code changes.
- No provider credential（模型供应商凭据） changes.
- No commit unless the user explicitly requests it.

## File Structure

- Create: `docs/07-project-log/2026-06-07-P1-exit-review.md`
  - Records review evidence, P1 completion facts, M1/M2/M3/M4/M5 milestone matrix（里程碑矩阵）, known gaps（已知缺口）, real provider integration（真实模型供应商集成） decision, and P2 work package proposal（P2 工作包建议）.
- Modify: `docs/07-project-log/INDEX.md`
  - Adds the review log to Completed / Archived Documents（已完成 / 已归档文档） because project logs（项目日志） are audit records, not active implementation fact sources.
- Modify: `docs/04-implementation-backlog/backlog.md`
  - Adds P1 Exit Gate result and updates P2 task set/order/scope/basis/dependencies/acceptance.
- Modify: `docs/04-implementation-spec/P1-exit-gate-roadmap-review-spec.md`
  - Changes status from `draft` to `implemented` after review is complete.
- Modify: `docs/04-implementation-plan/P1-exit-gate-roadmap-review-plan.md`
  - Changes status from `draft` to `implemented` after review is complete.
- Modify: `docs/04-implementation-spec/INDEX.md`
  - Adds this spec as active draft before review; moves it to Completed / Archived Documents after review.
- Modify: `docs/04-implementation-plan/INDEX.md`
  - Adds this plan as active draft before review; moves it to Completed / Archived Documents after review.
- Modify if needed: `docs/INDEX.md`
  - Updates active pointers only if P1 Exit Gate spec / plan or P2 work package changes affect global reading guidance.

---

### Task 1: Register P1 exit gate spec and plan as active drafts

**Files:**

- Modify: `docs/04-implementation-spec/INDEX.md`
- Modify: `docs/04-implementation-plan/INDEX.md`

- [ ] **Step 1: Add active spec entry before executing the gate**

In `docs/04-implementation-spec/INDEX.md`, add to Current Active Documents（当前活跃文档）:

```markdown
| `P1-exit-gate-roadmap-review-spec.md` | draft | 定义 P1 Exit Gate（P1 退出门禁）路线图复审、里程碑判定和 P2 工作包滚动更新规则 | 执行 P1 Exit Gate 前 |
```

Expected: this entry is present before the gate writes final review outputs.

- [ ] **Step 2: Add active plan entry before executing the gate**

In `docs/04-implementation-plan/INDEX.md`, add to Current Active Documents（当前活跃文档）:

```markdown
| `P1-exit-gate-roadmap-review-plan.md` | draft | 实施 P1 Exit Gate（P1 退出门禁）路线图复审、文档治理收尾和 P2 工作包滚动更新的文档计划 | 执行 P1 Exit Gate 时 |
```

Expected: this entry is present before the gate writes final review outputs.

---

### Task 2: Verify gate prerequisites and collect raw evidence

**Files:**

- Read: `docs/04-implementation-backlog/backlog.md`
- Read: `docs/06-roadmap/roadmap.md`
- Read: `docs/04-implementation-spec/INDEX.md`
- Read: `docs/04-implementation-plan/INDEX.md`
- Read: `README.md`
- Verify: test suite, permission negative gate, minimal example command, event stream content, Boardroom adapter tests, deferred P2 inventory, ADR-level changes and git status

- [ ] **Step 1: Confirm P1 backlog states**

Check `docs/04-implementation-backlog/backlog.md` contains these completed rows:

```markdown
| P1-001 | 实现 `web_fetch` 和 NetworkPolicy（网络策略） | completed | `P1-001-web-fetch-network-policy-spec.md`, `mvp-runtime-spec.md`, `agent-action-protocol.md`, `event-stream-protocol.md` |
| P1-002 | 整合现有 permission negative tests（权限负向测试）为单一门禁，并补齐网络拒绝场景 | completed | `P1-002-permission-negative-gate-spec.md`, `testing-strategy.md`, `mvp-acceptance.md`, `0003-use-fail-closed-permission-model.md` |
| P1-003 | 固化 fake provider loop acceptance（假模型供应商循环验收）并建立真实 minimal example（最小示例）文档路径 | completed | `P1-003-fake-provider-loop-minimal-example-spec.md`, `testing-strategy.md`, `mvp-acceptance.md`, `README.md` |
| P1-004 | 实现 Boardroom AgentRuntimePort adapter（Boardroom 智能体运行时端口适配器） | completed | `agent-runtime-port.md`, `boardroom-os-integration-summary.md`, `0004-keep-boardroom-os-as-governance-source.md` |
```

Expected: all P1 rows are completed. If any P1 row is not completed, stop and write blocked review instead of updating P2 work packages as accepted.

- [ ] **Step 2: Confirm P1 specs and plans are archived / implemented**

Check `docs/04-implementation-spec/INDEX.md` contains completed rows for P1-001 through P1-004, including:

```markdown
| `P1-004-boardroom-agent-runtime-port-adapter-spec.md` | 2026-06-06 | 已实现 P1-004 Boardroom AgentRuntimePort adapter（Boardroom 智能体运行时端口适配器），保留为端口适配器规格记录 |
```

Check `docs/04-implementation-plan/INDEX.md` contains completed rows for P1-001 through P1-004, including:

```markdown
| `P1-004-boardroom-agent-runtime-port-adapter-plan.md` | 2026-06-06 | 已实施 P1-004 Boardroom AgentRuntimePort adapter（Boardroom 智能体运行时端口适配器），保留为 TDD 实施记录 |
```

Expected: no completed P1 implementation spec / plan remains in Current Active Documents（当前活跃文档）.

- [ ] **Step 3: Run full test suite**

Run:

```bash
python -m pytest -q
```

Expected:

```text
all tests pass
```

If tests fail, stop and create the project log with `P1 Exit Gate: blocked` status. Do not update P2 work packages as accepted.

- [ ] **Step 4: Run permission negative gate**

Run:

```bash
python -m pytest -m permission_negative -q
```

Expected:

```text
all permission_negative tests pass
```

If this gate fails, stop and create the project log with `P1 Exit Gate: blocked` status.

- [ ] **Step 5: Run README minimal example command**

Run the minimal example command documented in `README.md`:

```bash
rm -rf /tmp/atomic-agent-minimal-example
PYTHONPATH=src python -m atomic_agent.examples.minimal_fake_loop \
  --run-id minimal_example \
  --workspace /tmp/atomic-agent-minimal-example/workspace \
  --event-stream /tmp/atomic-agent-minimal-example/events/events.jsonl \
  --artifact-root /tmp/atomic-agent-minimal-example/artifacts \
  --result /tmp/atomic-agent-minimal-example/result.json
```

Expected stdout shape:

```json
{"artifact_root": "/tmp/atomic-agent-minimal-example/artifacts", "event_stream_path": "/tmp/atomic-agent-minimal-example/events/events.jsonl", "result_path": "/tmp/atomic-agent-minimal-example/result.json", "status": "completed", "workspace_output_path": "/tmp/atomic-agent-minimal-example/workspace/work/output.txt"}
```

Expected filesystem outputs:

```text
/tmp/atomic-agent-minimal-example/result.json
/tmp/atomic-agent-minimal-example/events/events.jsonl
/tmp/atomic-agent-minimal-example/artifacts/
/tmp/atomic-agent-minimal-example/workspace/work/output.txt
```

Expected final workspace output:

```text
fixed
```

If the command fails, stop and create the project log with `P1 Exit Gate: blocked` status; do not silently rewrite the README command.

- [ ] **Step 6: Verify README minimal example event stream content**

Run:

```bash
python - <<'PY'
import json
from pathlib import Path

event_path = Path('/tmp/atomic-agent-minimal-example/events/events.jsonl')
events = [json.loads(line) for line in event_path.read_text(encoding='utf-8').splitlines()]
event_types = {event['type'] for event in events}
required = {
    'run.started',
    'provider.turn.started',
    'provider.turn.completed',
    'action.parsed',
    'permission.decided',
    'tool.attempt.started',
    'tool.attempt.completed',
    'workspace.mutation.recorded',
    'command.completed',
    'result.submitted',
    'run.completed',
}
missing = sorted(required - event_types)
if missing:
    print(f'Missing event types: {missing}')
    raise SystemExit(1)
print('Event stream contains required event types')
PY
```

Expected:

```text
Event stream contains required event types
```

If required event types are missing, stop and create the project log with `P1 Exit Gate: blocked` status.

- [ ] **Step 7: Verify Boardroom adapter test coverage**

Run:

```bash
python -m pytest /Users/bill/projects/atomic-agent/tests/test_runtime_port.py -q
```

Expected: tests pass and demonstrate:

```text
AgentInvocation is passed to the runner without reconstruction.
AgentRunResult is returned unchanged for completed and failed runs.
Invalid invocation and invalid runner results are rejected.
Runner exceptions are not converted into fake results.
Returned results do not contain Boardroom governance completion fields.
```

If adapter tests fail, stop and create the project log with `P1 Exit Gate: blocked` status.

- [ ] **Step 8: Review existing deferred P2 items**

Check the current P2 table in `docs/04-implementation-backlog/backlog.md` and classify each existing deferred item:

```text
native tool calling adapter（原生工具调用适配器）: keep outside immediate P2 batch unless later roadmap review prioritizes it.
service runner / HTTP probe（服务运行与 HTTP 探测）: keep outside immediate P2 batch unless later roadmap review prioritizes it.
external coding agent bridge（外部编码智能体桥接）: keep deferred, but redefine the next output as a design spec or ADR for evidence import protocol and permission boundary.
```

Expected: no deferred idea silently disappears; backlog dependency notes explain what was kept outside the immediate P2 batch.

- [ ] **Step 9: Check for ADR-level changes**

Review collected evidence for signals that require ADR（架构决策记录） before updating P2 packages:

```text
Long-term roadmap endpoint changes.
Boardroom governance source-of-truth boundary changes.
Event/evidence model principle changes.
Permission model principle changes.
```

Expected: if none are found, record that no ADR is required for this exit gate because the update only reorganizes near-term P2 work packages under existing roadmap / ADR boundaries.

If an ADR-level change is found, stop normal backlog updates and create or request an ADR draft first.

- [ ] **Step 10: Capture working tree status before final documentation changes**

Run:

```bash
git status --short
```

Expected: record exact output in the project log. Unexpected runtime source changes should be called out and not hidden.

---

### Task 3: Create P1 exit review project log

**Files:**

- Create: `docs/07-project-log/2026-06-07-P1-exit-review.md`

- [ ] **Step 1: Create project log from collected evidence**

Create `docs/07-project-log/2026-06-07-P1-exit-review.md` only after Task 2 evidence has been collected. Do not copy milestone statuses from examples or expectations; derive every status and evidence note from the actual commands, current backlog, current indexes and current docs reviewed in Task 2.

The project log must contain these sections:

```markdown
# P1 Exit Review

## Status

completed

## Purpose

## Review Inputs

## Verification Evidence

## P1 Completed Scope

## Milestone Matrix

## Real Provider Integration Decision

## Existing Deferred P2 Item Handling

## ADR Requirement Check

## Known Gaps

## P2 Work Package Proposal

## Review Conclusion
```

Milestone Matrix（里程碑矩阵） requirements:

- Include every M1, M2, M3, M4 and M5 criterion listed in `docs/06-roadmap/roadmap.md`.
- Use only these statuses: `satisfied`, `partially_satisfied`, `not_satisfied`, `not_started`, `blocked`.
- For each row, include concrete evidence from Task 2 or a concrete gap.
- If the full suite, permission gate, minimal example, event stream check or Boardroom adapter test fails, mark the overall log as `blocked` and do not accept P2 work packages.

P2 Work Package Proposal（P2 工作包建议） requirements:

```markdown
| ID | Task | Dependencies | Acceptance |
|---|---|---|---|
| P2-001 | 完善 event stream / evidence mapping（事件流 / 证据映射）和 artifact hash（产物哈希）硬化 | P1 event stream, artifacts, command tool, filesystem mutation and Boardroom adapter | Workspace mutations include traceable before/after hash and diff references; command evidence exposes stdout/stderr artifact hashes; Boardroom evidence input can trace source files to provider/tool/workspace lineage. |
| P2-002 | 建立 real provider minimal integration gate（真实模型供应商最小集成门禁） | P2-001 evidence expectations; existing provider-agnostic action protocol（供应商无关动作协议） | A real provider emits at least one legal `AgentAction`; runtime executes or rejects it under policy; events and errors are recorded; gate is manual/nightly or integration-profile, not base CI. |
| P2-003 | 设计 external coding agent bridge（外部编码智能体桥接）的证据导入协议和权限边界 | P2-001 evidence hardening; P2-002 integration findings; ADR-0002 and roadmap M5 | Produces a design spec or ADR before implementation; bridge remains deferred until external agent diffs, logs and command results can be imported without bypassing permission policy. |
```

- [ ] **Step 2: If evidence fails, create blocked variant instead**

If any verification in Task 2 fails, create the same file with this status and conclusion instead:

```markdown
## Status

blocked

## Review Conclusion

P1 Exit Gate is blocked because required verification evidence failed or contradicted the P1 completed state. P2 work packages must not be accepted until the failed evidence is fixed and the gate is rerun.

## Recovery Path

1. Fix the failing tests, minimal example command, contradictory evidence, or documentation index issue.
2. Rerun P1 Exit Gate verification, including `python -m pytest -q`, `python -m pytest -m permission_negative -q`, `python -m pytest /Users/bill/projects/atomic-agent/tests/test_runtime_port.py -q`, the README minimal example command and the event stream content check.
3. If the gate remains blocked, record the issue as a project blocker and escalate for human decision; do not lower the acceptance standard silently.
```

Also include the failing command output summary under `Verification Evidence`.

---

### Task 4: Update project log index

**Files:**

- Modify: `docs/07-project-log/INDEX.md`

- [ ] **Step 1: Add P1 exit review row**

Add this row to Completed / Archived Documents（已完成 / 已归档文档）:

```markdown
| `2026-06-07-P1-exit-review.md` | 2026-06-07 | 记录 P1 Exit Gate（P1 退出门禁）复审、里程碑判定、真实 provider 集成判断和 P2 工作包滚动更新依据 |
```

- [ ] **Step 2: Keep Current Active Documents unchanged**

Ensure `docs/07-project-log/INDEX.md` keeps only `INDEX.md` in Current Active Documents（当前活跃文档）:

```markdown
| `INDEX.md` | active | 本目录索引和文档治理规则 | 进入本目录前 |
```

Project log（项目日志） is an audit record, not an active implementation fact source.

---

### Task 5: Update backlog with P1 gate conclusion and revised P2 packages

**Files:**

- Modify: `docs/04-implementation-backlog/backlog.md`

- [ ] **Step 1: Replace P1 Exit Gate trigger block with completed review result**

Replace the current P1 Exit Gate trigger / required outputs block with:

```markdown
### P1 Exit Gate: Roadmap Review

Status（状态）：completed

Review record（复审记录）：`docs/07-project-log/2026-06-07-P1-exit-review.md`

Conclusion（结论）：

- M1 exit criteria（M1 退出标准）已满足。
- M2 exit criteria（M2 退出标准）已满足：`run_command`（运行声明命令）、`web_fetch`（网络获取）、NetworkPolicy（网络策略）、permission negative gate（权限负向门禁）、预算和无效动作 fail closed（失败关闭）均已有验证路径。
- M3 exit criteria（M3 退出标准）已满足：Boardroom `AgentRuntimePort adapter`（智能体运行时端口适配器）已实现，并保持 atomic-agent 不声明 Boardroom governance completion（治理完成）的边界。
- M4 尚未完成：event stream / evidence mapping（事件流 / 证据映射）、artifact hash（产物哈希）和 SourceInventory（源码清单） lineage（谱系）应成为 P2 优先工作包。
- M5 尚未开始：external coding agent bridge（外部编码智能体桥接）继续 deferred（延后），直到 M4 证据导入路径稳定。
```

If the gate is blocked, use this block instead:

```markdown
### P1 Exit Gate: Roadmap Review

Status（状态）：blocked

Review record（复审记录）：`docs/07-project-log/2026-06-07-P1-exit-review.md`

Blocker（阻塞原因）：见 P1 exit review（P1 退出复审）日志。

Recovery（恢复路径）：修复失败测试、最小示例、证据矛盾或文档索引问题后，重新执行 P1 Exit Gate；不得在 blocked 状态下确认 P2 工作包。
```

- [ ] **Step 2: Replace old P2 deferred table with revised P2 work packages**

Replace the current P2 table:

```markdown
| P2-001 | native tool calling adapter（原生工具调用适配器） | deferred | ADR-0002 |
| P2-002 | service runner / http probe（服务运行与 HTTP 探测） | deferred | roadmap |
| P2-003 | external coding agent bridge（外部编码智能体桥接） | deferred | roadmap |
```

With:

```markdown
| P2-001 | 完善 event stream / evidence mapping（事件流 / 证据映射）和 artifact hash（产物哈希）硬化 | pending | `event-stream-protocol.md`, `event-and-evidence-architecture.md`, `agent-runtime-port.md`, `mvp-acceptance.md`, `roadmap.md` |
| P2-002 | 建立 real provider minimal integration gate（真实模型供应商最小集成门禁） | pending | `testing-strategy.md`, `agent-action-protocol.md`, `mvp-acceptance.md`, `roadmap.md` |
| P2-003 | 设计 external coding agent bridge（外部编码智能体桥接）的证据导入协议和权限边界 | deferred | `roadmap.md`, `0002-use-provider-agnostic-action-protocol.md`, `0003-use-fail-closed-permission-model.md` |
```

If the gate is blocked, do not replace the P2 table with pending work packages. Instead, keep existing P2 entries and add a note that P2 reorganization is blocked until the gate passes.

- [ ] **Step 3: Add P2 dependency notes below the P2 table**

Add this after the P2 table when the gate completes:

```markdown
Dependency notes（依赖说明）：

- P2-001 is the first P2 work package because M4 evidence mapping（证据映射） must be hardened before expanding to external coding agent bridge（外部编码智能体桥接）.
- P2-002 should run after or alongside P2-001 only as a manual/nightly or integration-profile gate（集成配置门禁）; it must not destabilize base CI（基础持续集成）.
- P2-003 remains deferred; it should produce a design spec（设计规格） or ADR（架构决策记录） for evidence import protocol（证据导入协议） and permission boundary（权限边界） before any bridge implementation.
- Earlier deferred ideas such as native tool calling adapter（原生工具调用适配器） and service runner / HTTP probe（服务运行与 HTTP 探测） are not removed from the roadmap; they are not part of the immediate P2 batch unless a later roadmap review re-prioritizes them.
```

---

### Task 6: Mark spec and plan implemented after review outputs exist

**Files:**

- Modify: `docs/04-implementation-spec/P1-exit-gate-roadmap-review-spec.md`
- Modify: `docs/04-implementation-plan/P1-exit-gate-roadmap-review-plan.md`

- [ ] **Step 1: Mark spec implemented**

Change `docs/04-implementation-spec/P1-exit-gate-roadmap-review-spec.md` from:

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

### Task 7: Move spec and plan index entries to completed

**Files:**

- Modify: `docs/04-implementation-spec/INDEX.md`
- Modify: `docs/04-implementation-plan/INDEX.md`

- [ ] **Step 1: Move spec index entry to completed**

Remove the active spec row added in Task 1 and add to Completed / Archived Documents（已完成 / 已归档文档）:

```markdown
| `P1-exit-gate-roadmap-review-spec.md` | 2026-06-07 | 已完成 P1 Exit Gate（P1 退出门禁）路线图复审规格，保留为阶段门禁规格记录 |
```

- [ ] **Step 2: Move plan index entry to completed**

Remove the active plan row added in Task 1 and add to Completed / Archived Documents（已完成 / 已归档文档）:

```markdown
| `P1-exit-gate-roadmap-review-plan.md` | 2026-06-07 | 已实施 P1 Exit Gate（P1 退出门禁）路线图复审、文档治理收尾和 P2 工作包滚动更新，保留为阶段门禁实施记录 |
```

---

### Task 8: Update docs index if global pointers changed

**Files:**

- Modify if needed: `docs/INDEX.md`

- [ ] **Step 1: Decide whether `docs/INDEX.md` needs a new or updated active pointer**

If `docs/04-implementation-backlog/backlog.md` remains the primary active implementation entry and the P1 Exit Gate spec / plan are moved to completed immediately, no new global pointer is needed.

If the P2 work package update adds a new active spec, acceptance document, testing document or ADR, update `docs/INDEX.md` Current Active Documents accordingly.

Expected for this plan:

```text
No docs/INDEX.md change is required unless the P2 work package update adds or removes active authoritative documents beyond backlog/spec/plan indexes.
```

- [ ] **Step 2: If changing `docs/INDEX.md`, keep reading path semantics consistent**

Do not add project log（项目日志） as an active implementation fact source. It can remain accessible through `docs/07-project-log/INDEX.md`.

---

### Task 9: Final verification and self-review

**Files:**

- Verify: all changed docs
- Verify: test suite and permission gate

- [ ] **Step 1: Run full tests again after documentation updates**

Run:

```bash
python -m pytest -q
```

Expected:

```text
all tests pass
```

- [ ] **Step 2: Run permission negative gate again**

Run:

```bash
python -m pytest -m permission_negative -q
```

Expected:

```text
all permission_negative tests pass
```

- [ ] **Step 3: Check changed files**

Run:

```bash
git status --short
```

Expected changed files when gate completes:

```text
 M docs/04-implementation-backlog/backlog.md
 M docs/04-implementation-plan/INDEX.md
 M docs/04-implementation-spec/INDEX.md
 M docs/07-project-log/INDEX.md
?? docs/04-implementation-plan/P1-exit-gate-roadmap-review-plan.md
?? docs/04-implementation-spec/P1-exit-gate-roadmap-review-spec.md
?? docs/07-project-log/2026-06-07-P1-exit-review.md
```

`docs/INDEX.md` may appear only if Task 8 found a real global pointer change.

- [ ] **Step 4: Self-review project log against spec**

Check that `docs/07-project-log/2026-06-07-P1-exit-review.md` includes:

```text
Review Inputs
Verification Evidence
P1 Completed Scope
Milestone Matrix
Real Provider Integration Decision
Existing Deferred P2 Item Handling
ADR Requirement Check
Known Gaps
P2 Work Package Proposal
Review Conclusion
```

Expected: all sections exist and no section contains placeholder wording.

- [ ] **Step 5: Self-review backlog P2 packages**

Check that each P2 row has:

```text
ID
Task
Status
Basis
```

And dependency notes cover:

```text
P2-001 before external coding agent bridge
P2-002 as manual/nightly or integration-profile gate
P2-003 as design spec or ADR before implementation
native tool calling adapter and service runner not removed from roadmap
```

Expected: all requirements are present.

- [ ] **Step 6: Placeholder scan**

Run:

```bash
python - <<'PY'
from pathlib import Path
paths = [
    Path('docs/04-implementation-spec/P1-exit-gate-roadmap-review-spec.md'),
    Path('docs/04-implementation-plan/P1-exit-gate-roadmap-review-plan.md'),
    Path('docs/07-project-log/2026-06-07-P1-exit-review.md'),
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
    if not path.exists():
        continue
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

Before telling the user the P1 Exit Gate documents are ready for review:

- [ ] Spec coverage: `P1-exit-gate-roadmap-review-spec.md` covers trigger, evidence, milestone classification, M4 judgment boundaries, P2 package rules, real provider integration decision, required outputs, blocked semantics, recovery path and documentation impact.
- [ ] Plan coverage: this plan includes steps to register active drafts, verify prerequisites, verify event stream content, verify Boardroom adapter tests, review existing deferred P2 items, check ADR-level changes, create project log, update project log index, update backlog, update spec / plan indexes, mark spec / plan implemented and verify tests.
- [ ] Placeholder scan: no placeholder markers, vague implementation markers or fake evidence placeholders remain.
- [ ] Type / name consistency: file names, P2 IDs, milestone statuses and Chinese / English terminology match across spec, plan, project log and backlog.
- [ ] Scope check: no runtime code, P2 implementation, real provider API call, external coding agent bridge or provider credential work is included.
- [ ] Governance check: every new authoritative document is indexed in its directory index; project log remains an audit record, not a second implementation fact source.
- [ ] Fail-closed check: failed tests, minimal example failure, missing event stream content, Boardroom adapter test failure, contradictory P1 evidence or ADR-level change block the gate and do not produce a completed P2 rollout.
- [ ] Verification check: `python -m pytest -q`, `python -m pytest -m permission_negative -q`, `python -m pytest /Users/bill/projects/atomic-agent/tests/test_runtime_port.py -q`, minimal example command, event stream content check, `git status --short` and placeholder scan results are recorded or reviewed before completion is claimed.
