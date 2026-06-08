# P2 Exit Gate Atomic Task Runtime Readiness Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the P2 Exit Gate `atomic task runtime readiness review`（原子任务运行时就绪复审）, determine whether `atomic-agent`（原子智能体） is ready to execute Boardroom-compiled `AgentInvocation`（智能体调用请求） atomic tasks, and close P2 without opening P3 if current bounded readiness is satisfied.

**Architecture:** Treat the gate as a documentation, verification, and boundary-review workflow, not as runtime feature implementation. The project log（项目日志） records evidence and capability classification（能力判定）; backlog（待办） remains the authoritative execution queue; indexes（索引） remain the authoritative document navigation layer. Boardroom OS（Boardroom 操作系统） owns `ExecutionPackage -> AgentInvocation`（执行包到智能体调用请求） compilation, while `atomic-agent` owns controlled execution and auditable facts.

**Tech Stack:** Markdown（文档）, pytest（测试验证）, git status（工作区审计）, existing Python runtime（现有 Python 运行时）, JSONL event stream（JSONL 事件流）, evidence mapper（证据映射器）, docs governance（文档治理）.

**Status:** implemented

---

## Scope

This plan implements only the P2 Exit Gate（P2 退出门禁）review after user approval.

In scope after approval:

- Verify P2 completed state against backlog（待办）, specs（规格）, plans（计划）, tests（测试）, README minimal example（最小示例）, runtime port（运行时端口）, AgentLoop（智能体循环） and evidence mapper（证据映射器）.
- Run real base verification commands:
  - `PYTHONPATH=src python -m pytest -q`
  - `PYTHONPATH=src python -m pytest -m permission_negative -q`
  - `PYTHONPATH=src python -m pytest tests/test_runtime_port.py tests/test_evidence.py tests/test_real_provider_complex_task.py -q`
  - README minimal fake loop command（README 最小假模型循环命令）.
  - Evidence summary check（证据摘要检查） against real event stream and `AgentRunResult`.
- Create `docs/07-project-log/2026-06-08-P2-exit-review.md`（P2 退出复审日志）.
- Update `docs/07-project-log/INDEX.md`（项目日志索引）.
- Update `docs/04-implementation-backlog/backlog.md`（实现待办） with P2 Exit Gate conclusion and P2-003 deferred optional（延后可选） status.
- Mark this spec / plan implemented only after the review completes.
- Move this spec / plan from active draft（活跃草案） to completed / archived（已完成 / 已归档） sections after implementation.
- Update `docs/INDEX.md` active pointers（当前活跃文档指针） accordingly.

Out of scope:

- No runtime source code changes.
- No Boardroom `ExecutionPackage -> AgentInvocation` compiler（执行包到智能体调用请求编译器）.
- No Boardroom EvidenceVerifier（证据验证器） or CloseoutGate（收尾门禁）.
- No external coding agent bridge（外部编码智能体桥接） implementation.
- No `external_agent_run` action implementation.
- No external CLI agent execution.
- No P3 backlog creation if atomic task runtime readiness（原子任务运行时就绪） is satisfied.
- No real provider gate re-run unless user explicitly provides config and asks to verify current provider success.
- No git commit unless the user explicitly requests it.

## File Structure

### Created now for user review

- `docs/04-implementation-spec/P2-exit-gate-atomic-task-runtime-readiness-review-spec.md`
  - Draft spec（草案规格） defining the P2 Exit Gate trigger, capability boundary, evidence requirements, M4/M5 classification, P3 decision rules, blocked semantics and documentation impact.

- `docs/04-implementation-plan/P2-exit-gate-atomic-task-runtime-readiness-review-plan.md`
  - This draft implementation plan（草案实施计划）. It is not the gate result and must remain draft until user review approves execution.

### Modified now for user review

- `docs/04-implementation-spec/INDEX.md`
  - Registers the draft spec in Current Active Documents（当前活跃文档）.

- `docs/04-implementation-plan/INDEX.md`
  - Registers this draft plan in Current Active Documents.

- `docs/INDEX.md`
  - Registers global active pointers for the draft spec and plan.

### Modified only after approval and execution

- `docs/07-project-log/2026-06-08-P2-exit-review.md`
  - New project log recording review evidence, capability matrix, M4/M5 status and P3 decision.

- `docs/07-project-log/INDEX.md`
  - Adds the P2 exit review log to completed / archived records.

- `docs/04-implementation-backlog/backlog.md`
  - Marks P2 Exit Gate completed or blocked, clarifies P2-003 deferred optional status, and does not add P3 when readiness is satisfied.

- `docs/04-implementation-spec/P2-exit-gate-atomic-task-runtime-readiness-review-spec.md`
  - Changes status from `draft` to `implemented` after the gate is complete.

- `docs/04-implementation-plan/P2-exit-gate-atomic-task-runtime-readiness-review-plan.md`
  - Changes status from `draft` to `implemented` after the gate is complete.

- `docs/04-implementation-spec/INDEX.md`
  - Moves the spec from Current Active Documents to Completed / Archived Documents after completion.

- `docs/04-implementation-plan/INDEX.md`
  - Moves this plan from Current Active Documents to Completed / Archived Documents after completion.

- `docs/INDEX.md`
  - Removes draft active pointers after completion; does not add P3 active pointers unless explicitly approved.

---

## Task 1: Register draft spec and plan for review

**Files:**

- Modify: `docs/04-implementation-spec/INDEX.md`
- Modify: `docs/04-implementation-plan/INDEX.md`
- Modify: `docs/INDEX.md`

- [ ] **Step 1: Register the draft spec in implementation spec index**

Add this row under `## 3. Current Active Documents` in `docs/04-implementation-spec/INDEX.md`:

```markdown
| `P2-exit-gate-atomic-task-runtime-readiness-review-spec.md` | draft | 定义 P2 Exit Gate（P2 退出门禁）原子任务运行时就绪复审、能力边界、M4/M5 判定和 P3 决策规则 | 评审或执行 P2 Exit Gate 前 |
```

Expected: the spec appears in Current Active Documents while awaiting review.

- [ ] **Step 2: Register the draft plan in implementation plan index**

Add this row under `## 3. Current Active Documents` in `docs/04-implementation-plan/INDEX.md`:

```markdown
| `P2-exit-gate-atomic-task-runtime-readiness-review-plan.md` | draft | 实施 P2 Exit Gate（P2 退出门禁）原子任务运行时就绪复审、文档治理收尾和不进入 P3 的边界判断计划 | 执行或评审 P2 Exit Gate 时 |
```

Expected: the plan appears in Current Active Documents while awaiting review.

- [ ] **Step 3: Register global active pointers**

Add these rows under `## 3. 当前活跃文档指针` in `docs/INDEX.md`:

```markdown
| P0 | `docs/04-implementation-spec/P2-exit-gate-atomic-task-runtime-readiness-review-spec.md` | draft | 评审或执行 P2 Exit Gate（P2 退出门禁）原子任务运行时就绪复审前 |
| P0 | `docs/04-implementation-plan/P2-exit-gate-atomic-task-runtime-readiness-review-plan.md` | draft | 评审或执行 P2 Exit Gate（P2 退出门禁）原子任务运行时就绪复审计划时 |
```

Expected: new sessions can discover the active draft spec and plan from the global docs index.

---

## Task 2: Verify gate prerequisites and collect raw evidence after approval

**Files:**

- Read: `README.md`
- Read: `docs/04-implementation-backlog/backlog.md`
- Read: `docs/04-implementation-spec/INDEX.md`
- Read: `docs/04-implementation-plan/INDEX.md`
- Read: `docs/06-roadmap/roadmap.md`
- Read: `docs/03-contracts/agent-runtime-port.md`
- Read: `docs/00-overview/boardroom-os-integration-summary.md`
- Verify: source and test suite

- [ ] **Step 1: Confirm P2 backlog state**

Check `docs/04-implementation-backlog/backlog.md` contains these P2 rows:

```markdown
| P2-001 | 完善 event stream / evidence mapping（事件流 / 证据映射）和 artifact hash（产物哈希）硬化 | completed | `P2-001-evidence-mapping-artifact-hash-hardening-spec.md`, `event-stream-protocol.md`, `event-and-evidence-architecture.md`, `agent-runtime-port.md`, `mvp-acceptance.md`, `roadmap.md` |
| P2-002 | 建立 real provider minimal integration gate（真实模型供应商最小集成门禁） | completed | `P2-002-real-provider-minimal-integration-gate-spec.md`, `testing-strategy.md`, `agent-action-protocol.md`, `mvp-acceptance.md`, `roadmap.md` |
| P2-003 | 设计 external coding agent bridge（外部编码智能体桥接）的证据导入协议和权限边界 | deferred | `roadmap.md`, `0002-use-provider-agnostic-action-protocol.md`, `0003-use-fail-closed-permission-model.md` |
| P2-004 | 建立 real provider tool success gate（真实供应商工具成功门禁） | completed | `P2-004-real-provider-tool-success-gate-spec.md`, `testing-strategy.md`, `agent-action-protocol.md`, `mvp-acceptance.md`, `roadmap.md` |
| P2-005 | 强化 OpenAI-compatible provider options（OpenAI 兼容供应商参数）显式配置 | completed | `P2-005-openai-compatible-provider-options-hardening-spec.md`, `testing-strategy.md`, `agent-action-protocol.md`, `mvp-acceptance.md`, `roadmap.md` |
| P2-006 | 建立 complex real provider atomic task gate（复杂真实供应商原子任务门禁） | completed | `P2-006-complex-real-provider-atomic-task-gate-spec.md`, `P2-005-openai-compatible-provider-options-hardening-spec.md`, `testing-strategy.md`, `mvp-acceptance.md`, `roadmap.md` |
```

Expected: all non-deferred P2 rows are completed. If any non-deferred P2 row is not completed, stop and create a blocked review instead of closing P2.

- [ ] **Step 2: Confirm P2 specs and plans are archived / implemented**

Check `docs/04-implementation-spec/INDEX.md` contains completed rows for P2-001, P2-002, P2-004, P2-005 and P2-006, including:

```markdown
| `P2-006-complex-real-provider-atomic-task-gate-spec.md` | 2026-06-08 | 已实现 P2-006 complex real provider atomic task gate（复杂真实供应商原子任务门禁），保留为真实供应商复杂原子任务门禁规格记录 |
```

Check `docs/04-implementation-plan/INDEX.md` contains completed rows for P2-001, P2-002, P2-004, P2-005 and P2-006, including:

```markdown
| `P2-006-complex-real-provider-atomic-task-gate-plan.md` | 2026-06-08 | 已实施 P2-006 complex real provider atomic task gate（复杂真实供应商原子任务门禁），保留为 TDD 实施记录 |
```

Expected: no completed non-deferred P2 implementation spec / plan remains in Current Active Documents.

- [ ] **Step 3: Run full base test suite**

Run:

```bash
PYTHONPATH=src python -m pytest -q
```

Expected:

```text
all tests pass
```

If tests fail, stop and create the P2 exit review with `blocked` status. Do not mark P2 Exit Gate completed.

- [ ] **Step 4: Run permission negative gate**

Run:

```bash
PYTHONPATH=src python -m pytest -m permission_negative -q
```

Expected:

```text
all permission_negative tests pass
```

If this gate fails, stop and create the P2 exit review with `blocked` status.

- [ ] **Step 5: Run focused readiness tests**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_runtime_port.py tests/test_evidence.py tests/test_real_provider_complex_task.py -q
```

Expected:

```text
runtime port tests pass; evidence tests pass; local complex task tests pass; real provider complex task test skips by default unless explicitly enabled
```

If focused tests fail, stop and create the P2 exit review with `blocked` status.

- [ ] **Step 6: Run README minimal fake loop command**

Run:

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

Expected final workspace output:

```text
fixed
```

If the command fails or output is not real, stop and create the P2 exit review with `blocked` status.

- [ ] **Step 7: Verify evidence summary on README minimal example output**

Run:

```bash
PYTHONPATH=src python - <<'PY'
import json
from pathlib import Path

from atomic_agent.evidence import build_evidence_summary
from atomic_agent.models import AgentRunResult

base = Path('/tmp/atomic-agent-minimal-example')
result = AgentRunResult.model_validate_json((base / 'result.json').read_text(encoding='utf-8'))
summary = build_evidence_summary(result, base / 'events' / 'events.jsonl')

assert summary['event_stream']['integrity']['ok'] is True
assert [command['exit_code'] for command in summary['command_results']] == [3, 0]
assert all(command['stdout']['sha256'].startswith('sha256:') for command in summary['command_results'])
assert all(command['stderr']['sha256'].startswith('sha256:') for command in summary['command_results'])
assert summary['source_inventory_lineage'][0]['path'] == 'work/output.txt'
assert summary['source_inventory_lineage'][0]['lineage_status'] == 'traceable'
assert summary['replay']['status'] in {'not_replayable', 'replayable'}
print(json.dumps({
    'integrity': summary['event_stream']['integrity']['ok'],
    'command_exit_codes': [command['exit_code'] for command in summary['command_results']],
    'lineage_status': summary['source_inventory_lineage'][0]['lineage_status'],
    'replay_status': summary['replay']['status'],
}, ensure_ascii=False, sort_keys=True))
PY
```

Expected output shape:

```json
{"command_exit_codes": [3, 0], "integrity": true, "lineage_status": "traceable", "replay_status": "not_replayable"}
```

If evidence summary fails, stop and create the P2 exit review with `blocked` status.

- [ ] **Step 8: Scan for forbidden governance / fallback runtime semantics**

Run:

```bash
python - <<'PY'
from pathlib import Path
needles = (
    'TICKET_COMPLETED',
    'CLOSEOUT_COMMITTED',
    'ticket_completed',
    'closeout_committed',
    'governance_status',
    'evidence_verified',
    'source_inventory_accepted',
    'allow_all',
    'default_allow',
)
for path in Path('src/atomic_agent').rglob('*.py'):
    text = path.read_text(encoding='utf-8')
    for needle in needles:
        if needle in text:
            print(f'{path}: contains {needle}')
PY
```

Expected output:

```text
```

If output appears, inspect it. A banned field list used only to reject governance output may be acceptable; executable code that creates governance completion semantics is a blocker.

- [ ] **Step 9: Check for ADR-level changes**

Review collected evidence for signals that require ADR（架构决策记录） before updating backlog:

```text
Long-term roadmap endpoint changes.
Boardroom governance source-of-truth boundary changes.
Event/evidence model principle changes.
Permission model principle changes.
Decision to move ExecutionPackage compiler into atomic-agent.
Decision to reactivate external coding agent bridge as required P3 work.
```

Expected: if none are found, record that no ADR is required because this gate only confirms current bounded readiness and keeps external bridge deferred optional.

- [ ] **Step 10: Capture working tree status before final documentation changes**

Run:

```bash
git status --short
```

Expected: record exact output in the project log. Unexpected runtime source changes should be called out and not hidden.

---

## Task 3: Create P2 exit review project log after approval

**Files:**

- Create: `docs/07-project-log/2026-06-08-P2-exit-review.md`

- [ ] **Step 1: Create completed project log if evidence passes**

Create `docs/07-project-log/2026-06-08-P2-exit-review.md` only after Task 2 evidence has been collected and passed. The project log must contain these sections:

```markdown
# P2 Exit Review

## Status

completed

## Purpose

## Review Inputs

## Verification Evidence

## Capability Boundary

## Atomic Task Readiness Matrix

## M4 Review

## M5 Review

## P3 Decision

## P2-003 Deferred Optional Decision

## ADR Requirement Check

## Known Limitations

## Review Conclusion
```

`Capability Boundary`（能力边界） must include this exact semantic chain:

```text
Boardroom ExecutionPackage（执行包）
  -> Boardroom OS compiles package into AgentInvocation（Boardroom 编译为智能体调用请求）
  -> AgentRuntimePort.invoke(AgentInvocation)
  -> atomic-agent AgentLoop（原子智能体循环）
  -> controlled tools + event stream + artifacts（受控工具 + 事件流 + 产物）
  -> AgentRunResult（智能体运行结果）
  -> Boardroom EvidenceVerifier / CloseoutGate（Boardroom 证据验证器 / 收尾门禁）
```

`Atomic Task Readiness Matrix` must contain these rows with status and evidence:

```markdown
| Capability | Status | Evidence / boundary |
|---|---|---|
| `AgentInvocation` input boundary（智能体调用请求输入边界） | satisfied | ... |
| `AgentRuntimePort.invoke`（智能体运行时端口调用） | satisfied | ... |
| Controlled `AgentLoop`（受控智能体循环） | satisfied | ... |
| Filesystem / command / web boundaries（文件系统 / 命令 / 网络边界） | satisfied | ... |
| Event stream and artifacts（事件流与产物） | satisfied | ... |
| Evidence summary mapping（证据摘要映射） | satisfied | ... |
| Boardroom governance decision（Boardroom 治理决策） | out_of_scope | Boardroom OS owns EvidenceVerifier and CloseoutGate. |
| Boardroom `ExecutionPackage` compiler（Boardroom 执行包编译器） | out_of_scope | Boardroom OS compiles package into AgentInvocation. |
| External coding agent bridge（外部编码智能体桥接） | deferred_optional | Backup extension; not required for current atomic task runtime readiness. |
```

`P3 Decision` must say:

```markdown
No P3 execution wave（P3 执行波次） is opened by this review because current bounded atomic task runtime readiness is satisfied. External coding agent bridge（外部编码智能体桥接） remains deferred optional（延后可选） and can be reactivated only by a later explicit roadmap review or user decision.
```

- [ ] **Step 2: Create blocked project log if evidence fails**

If any verification in Task 2 fails, create the same file with this status and conclusion instead:

```markdown
## Status

blocked

## Review Conclusion

P2 Exit Gate is blocked because required verification evidence failed or contradicted the P2 completed state. The gate must not be marked completed, and P3 must not be opened as a substitute for fixing the failed readiness evidence.

## Recovery Path

1. Fix the failing tests, minimal example command, evidence summary issue, contradictory P2 status, or documentation index issue.
2. Rerun P2 Exit Gate verification, including full suite, permission negative gate, focused readiness tests, README minimal example command and evidence summary check.
3. If the gate remains blocked, record the issue as a project blocker and escalate for human decision; do not lower the acceptance standard silently.
```

Also include the failing command output summary under `Verification Evidence`.

---

## Task 4: Update project log index after approval

**Files:**

- Modify: `docs/07-project-log/INDEX.md`

- [ ] **Step 1: Add P2 exit review row**

Add this row to Completed / Archived Documents（已完成 / 已归档文档）:

```markdown
| `2026-06-08-P2-exit-review.md` | 2026-06-08 | 记录 P2 Exit Gate（P2 退出门禁）原子任务运行时就绪复审、M4/M5 判定和不进入 P3 的边界决策 |
```

- [ ] **Step 2: Keep Current Active Documents unchanged**

Ensure `docs/07-project-log/INDEX.md` keeps only `INDEX.md` in Current Active Documents（当前活跃文档）:

```markdown
| `INDEX.md` | active | 本目录索引和文档治理规则 | 进入本目录前 |
```

Project log（项目日志） is an audit record, not an active implementation fact source.

---

## Task 5: Update backlog after approval

**Files:**

- Modify: `docs/04-implementation-backlog/backlog.md`

- [ ] **Step 1: Replace P2 Exit Gate trigger block with completed review result if evidence passes**

Replace the current P2 Exit Gate trigger / required outputs block with:

```markdown
### P2 Exit Gate: Atomic Task Runtime Readiness Review

Status（状态）：completed

Review record（复审记录）：`docs/07-project-log/2026-06-08-P2-exit-review.md`

Conclusion（结论）：

- M4 exit criteria（M4 退出标准）已满足：event stream / evidence mapping（事件流 / 证据映射）、artifact hash（产物哈希）、workspace mutation lineage（工作区变更谱系）和 command artifact hash（命令产物哈希）已有验证路径。
- 当前 bounded runtime readiness（有界运行时就绪）已满足：Boardroom OS 可将 ticket package（工单包）编译为完整 `AgentInvocation`（智能体调用请求），atomic-agent 通过 `AgentRuntimePort`（智能体运行时端口）执行 atomic task（原子任务）并返回可审计 `AgentRunResult`（智能体运行结果）。
- `ExecutionPackage -> AgentInvocation`（执行包到智能体调用请求）编译职责属于 Boardroom OS 或上层编排系统，不下沉到 atomic-agent 当前边界。
- M5 external coding agent bridge（外部编码智能体桥接）继续 deferred optional（延后可选），作为备用扩展，不阻塞当前 readiness。
- 本复审不开启 P3 execution wave（P3 执行波次）。
```

If the gate is blocked, use this block instead:

```markdown
### P2 Exit Gate: Atomic Task Runtime Readiness Review

Status（状态）：blocked

Review record（复审记录）：`docs/07-project-log/2026-06-08-P2-exit-review.md`

Blocker（阻塞原因）：见 P2 exit review（P2 退出复审）日志。

Recovery（恢复路径）：修复失败测试、最小示例、证据摘要、P2 状态矛盾或文档索引问题后，重新执行 P2 Exit Gate；不得用 P3 或 external bridge（外部桥接）掩盖当前 readiness 失败。
```

- [ ] **Step 2: Clarify P2-003 remains deferred optional**

Keep the P2-003 row status as `deferred` and ensure the dependency notes contain this bullet:

```markdown
- P2-003 remains deferred optional（延后可选） after P2 Exit Gate. External coding agent bridge（外部编码智能体桥接） is a backup extension, not a prerequisite for current atomic task runtime readiness（原子任务运行时就绪）. It should be reactivated only by a later explicit roadmap review（路线图复审） or user decision.
```

- [ ] **Step 3: Do not add P3 backlog**

Confirm `docs/04-implementation-backlog/backlog.md` does not contain a new `## P3` section unless the user explicitly approved opening P3.

Expected:

```text
No P3 section exists after this gate when readiness is satisfied.
```

---

## Task 6: Mark spec and plan implemented after approval

**Files:**

- Modify: `docs/04-implementation-spec/P2-exit-gate-atomic-task-runtime-readiness-review-spec.md`
- Modify: `docs/04-implementation-plan/P2-exit-gate-atomic-task-runtime-readiness-review-plan.md`

- [ ] **Step 1: Mark spec implemented**

Change `docs/04-implementation-spec/P2-exit-gate-atomic-task-runtime-readiness-review-spec.md` from:

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

Only do this after the P2 exit review project log and backlog updates are complete.

---

## Task 7: Move spec and plan index entries to completed after approval

**Files:**

- Modify: `docs/04-implementation-spec/INDEX.md`
- Modify: `docs/04-implementation-plan/INDEX.md`

- [ ] **Step 1: Move spec index entry to completed**

Remove this active spec row:

```markdown
| `P2-exit-gate-atomic-task-runtime-readiness-review-spec.md` | draft | 定义 P2 Exit Gate（P2 退出门禁）原子任务运行时就绪复审、能力边界、M4/M5 判定和 P3 决策规则 | 评审或执行 P2 Exit Gate 前 |
```

Add this row to Completed / Archived Documents（已完成 / 已归档文档）:

```markdown
| `P2-exit-gate-atomic-task-runtime-readiness-review-spec.md` | 2026-06-08 | 已完成 P2 Exit Gate（P2 退出门禁）原子任务运行时就绪复审规格，保留为阶段门禁规格记录 |
```

- [ ] **Step 2: Move plan index entry to completed**

Remove this active plan row:

```markdown
| `P2-exit-gate-atomic-task-runtime-readiness-review-plan.md` | draft | 实施 P2 Exit Gate（P2 退出门禁）原子任务运行时就绪复审、文档治理收尾和不进入 P3 的边界判断计划 | 执行或评审 P2 Exit Gate 时 |
```

Add this row to Completed / Archived Documents（已完成 / 已归档文档）:

```markdown
| `P2-exit-gate-atomic-task-runtime-readiness-review-plan.md` | 2026-06-08 | 已实施 P2 Exit Gate（P2 退出门禁）原子任务运行时就绪复审、文档治理收尾和不进入 P3 的边界判断，保留为阶段门禁实施记录 |
```

---

## Task 8: Update global docs index after approval

**Files:**

- Modify: `docs/INDEX.md`

- [ ] **Step 1: Remove draft active pointers**

Remove these rows from `docs/INDEX.md` after the gate is completed:

```markdown
| P0 | `docs/04-implementation-spec/P2-exit-gate-atomic-task-runtime-readiness-review-spec.md` | draft | 评审或执行 P2 Exit Gate（P2 退出门禁）原子任务运行时就绪复审前 |
| P0 | `docs/04-implementation-plan/P2-exit-gate-atomic-task-runtime-readiness-review-plan.md` | draft | 评审或执行 P2 Exit Gate（P2 退出门禁）原子任务运行时就绪复审计划时 |
```

- [ ] **Step 2: Do not add P3 active pointers unless explicitly approved**

Expected when readiness is satisfied:

```text
No P3 spec, plan or backlog active pointer is added.
```

---

## Task 9: Final verification and self-review after approval

**Files:**

- Verify: all changed docs
- Verify: test suite and readiness commands

- [ ] **Step 1: Run final full test suite**

Run:

```bash
PYTHONPATH=src python -m pytest -q
```

Expected:

```text
all tests pass
```

- [ ] **Step 2: Run final permission negative gate**

Run:

```bash
PYTHONPATH=src python -m pytest -m permission_negative -q
```

Expected:

```text
all permission_negative tests pass
```

- [ ] **Step 3: Run markdown whitespace check**

Run:

```bash
git diff --check docs/
```

Expected: no output.

- [ ] **Step 4: Check changed files**

Run:

```bash
git status --short
```

Expected changed files after completed gate:

```text
 M docs/INDEX.md
 M docs/04-implementation-backlog/backlog.md
 M docs/04-implementation-plan/INDEX.md
 M docs/04-implementation-plan/P2-exit-gate-atomic-task-runtime-readiness-review-plan.md
 M docs/04-implementation-spec/INDEX.md
 M docs/04-implementation-spec/P2-exit-gate-atomic-task-runtime-readiness-review-spec.md
 M docs/07-project-log/INDEX.md
?? docs/07-project-log/2026-06-08-P2-exit-review.md
```

If additional runtime source or test files appear, inspect and explain before claiming completion.

- [ ] **Step 5: Self-review project log against spec**

Check that `docs/07-project-log/2026-06-08-P2-exit-review.md` includes:

```text
Review Inputs
Verification Evidence
Capability Boundary
Atomic Task Readiness Matrix
M4 Review
M5 Review
P3 Decision
P2-003 Deferred Optional Decision
ADR Requirement Check
Known Limitations
Review Conclusion
```

Expected: all sections exist and no section contains placeholder wording.

- [ ] **Step 6: Self-review backlog conclusion**

Check `docs/04-implementation-backlog/backlog.md` includes:

```text
P2 Exit Gate status completed or blocked
Review record path
P2-003 remains deferred optional
No P3 section when readiness is satisfied
ExecutionPackage -> AgentInvocation remains Boardroom / upper-layer responsibility
```

Expected: all boundary statements are present and consistent.

- [ ] **Step 7: Placeholder scan**

Run:

```bash
python - <<'PY'
from pathlib import Path
paths = [
    Path('docs/04-implementation-spec/P2-exit-gate-atomic-task-runtime-readiness-review-spec.md'),
    Path('docs/04-implementation-plan/P2-exit-gate-atomic-task-runtime-readiness-review-plan.md'),
    Path('docs/07-project-log/2026-06-08-P2-exit-review.md'),
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

## Task 10: User review gate before implementation

**Files:**

- No additional file changes.

- [ ] **Step 1: Stop after draft spec / plan self-review**

After the draft spec and plan are written, indexed and self-reviewed, stop and ask the user to review:

```text
P2 Exit Gate draft spec and plan are ready for review:
- docs/04-implementation-spec/P2-exit-gate-atomic-task-runtime-readiness-review-spec.md
- docs/04-implementation-plan/P2-exit-gate-atomic-task-runtime-readiness-review-plan.md

I have not implemented the gate, created the exit review log, marked the gate completed, or opened P3.
```

- [ ] **Step 2: Do not implement the gate before approval**

Do not modify these files until the user explicitly approves the spec / plan and asks to implement:

```text
docs/07-project-log/2026-06-08-P2-exit-review.md
docs/07-project-log/INDEX.md
docs/04-implementation-backlog/backlog.md
```

Do not modify runtime source code during this gate unless a later approved plan explicitly changes scope.

---

## Self-Review Checklist

Before telling the user the draft spec / plan are ready for review:

- [ ] Spec coverage: `P2-exit-gate-atomic-task-runtime-readiness-review-spec.md` covers trigger, authoritative inputs, capability boundary, required evidence, readiness classification, M4/M5 classification, P3 decision rules, required outputs, blocked semantics, acceptance criteria and documentation impact.
- [ ] Plan coverage: this plan includes steps to register active drafts, verify prerequisites, run full tests, run permission negative tests, run focused readiness tests, run README minimal example, build evidence summary, scan forbidden governance fields, check ADR requirements, create project log, update project log index, update backlog, mark spec / plan implemented, move indexes and verify final docs.
- [ ] Placeholder scan: no placeholder markers, vague implementation markers or fake evidence placeholders remain.
- [ ] Type / name consistency: file names, P2 IDs, milestone statuses, readiness statuses and Chinese / English terminology match across spec, plan, backlog and indexes.
- [ ] Scope check: no runtime code, external CLI bridge, Boardroom compiler, Boardroom verifier, real provider rerun or P3 creation is included in draft-writing work.
- [ ] Governance check: every new authoritative draft document is indexed in its directory index and global docs index; project log remains an audit record after implementation, not a second implementation fact source.
- [ ] Fail-closed check: failed tests, focused readiness failures, minimal example failure, evidence summary failure, contradictory P2 evidence or ADR-level change block the gate and do not produce a completed P2 closeout.
- [ ] Review gate check: this draft-writing batch stops before implementation and waits for user review.

## Self-Review Result

- Spec coverage（规格覆盖）：计划覆盖 P2 Exit Gate spec（规格）中的 trigger、能力边界、证据收集、runtime readiness（运行时就绪）判断、M4/M5 判定、P3 决策、阻塞语义、文档输出和验收标准。
- Placeholder scan（占位符扫描）：未使用占位标记、未定义步骤或空泛“补充”语义；所有文件路径、命令和预期输出均具体写明。
- Type / naming consistency（类型与命名一致性）：`P2-exit-gate-atomic-task-runtime-readiness-review-spec.md`、`P2-exit-gate-atomic-task-runtime-readiness-review-plan.md`、`AgentInvocation`、`AgentRunResult`、`AgentRuntimePort`、`build_evidence_summary`、`P2-003` 和 `P3` 等命名在计划中保持一致。
- Scope check（范围检查）：本计划当前只写 draft spec / plan 和索引；正式实施 gate 时也只创建 project log、更新 backlog/index，不实现 runtime code、Boardroom compiler、external agent bridge 或 P3。
- No-fallback check（无兜底检查）：测试失败、最小示例失败、证据摘要失败、P2 状态矛盾、治理字段泄漏或 ADR 级变化都会 blocked，不会用 P3 或外部 bridge 掩盖 readiness 失败。
- User review gate（用户评审门禁）：明确要求 draft spec / plan 自审后停止，等待用户评审通过再实施 P2 Exit Gate。
