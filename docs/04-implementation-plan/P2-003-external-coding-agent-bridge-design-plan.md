# P2-003 External Coding Agent Bridge Design Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the P2-003 design package for a CLI single-request black-box `external coding agent bridge`（外部编码智能体桥接） by writing the authoritative spec（权威规格）, registering it in docs indexes（文档索引）, and preparing it for user review before any runtime implementation.

**Architecture:** This is a documentation-first implementation. P2-003 specifies a simplified bridge where `atomic-agent`（原子智能体） sends one task string to an already-installed CLI agent（CLI 智能体）, runs it in an isolated worktree（隔离工作树）, captures exit code/stdout/stderr, scans the resulting diff, and imports evidence without parsing the external agent’s internal tool calls.

**Tech Stack:** Markdown docs（Markdown 文档）, existing docs governance（现有文档治理）, `docs/04-implementation-spec/`（实现规格目录）, `docs/04-implementation-plan/`（实施计划目录）, backlog/index files（待办与索引文件）.

**Status:** archived design reference

> Archive note（归档说明，2026-06-08）：P2-003 runtime implementation（运行时实现）已按用户决定延期；本文仅归档 CLI single-request black-box（CLI 单一请求黑盒）设计方案，不作为当前 P2 exit gate（P2 退出门禁）的活跃实施计划。

---

## Scope

This plan implements the P2-003 design work only.

In scope:

- Create or revise `docs/04-implementation-spec/P2-003-external-coding-agent-bridge-design-spec.md` around the CLI single-request black-box model.
- Create or revise `docs/04-implementation-plan/P2-003-external-coding-agent-bridge-design-plan.md`.
- Update `docs/04-implementation-spec/INDEX.md` to list the draft spec（草案规格）.
- Update `docs/04-implementation-plan/INDEX.md` to list the draft plan（草案计划）.
- Update `docs/04-implementation-backlog/backlog.md` to keep P2-003 as draft（草案） design work.
- Update `docs/INDEX.md` so new sessions can discover the P2-003 design documents.
- Run self-review checks for placeholder text（占位文本）, CLI-specific boundaries（CLI 特定边界）, over-designed fields（过度设计字段）, governance leakage（治理泄漏） and index consistency（索引一致性）.

Out of scope:

- No code changes under `src/` or `tests/`.
- No `AgentActionType.EXTERNAL_AGENT_RUN` implementation.
- No event enum implementation.
- No CLI runner（CLI 运行器）.
- No Claude Code / Codex process execution.
- No provider calls, network calls or real external CLI agent gate.
- No git commit unless the user explicitly asks for one.

## File Structure

### Create / Revise

- `docs/04-implementation-spec/P2-003-external-coding-agent-bridge-design-spec.md`
  - Owns the simplified CLI design spec（CLI 简化设计规格）: action boundary（动作边界）, CLI profile（CLI 配置画像）, CLI evidence package（CLI 证据包）, import validation（导入校验）, event mapping（事件映射）, permission boundary（权限边界）, transcript redaction（会话记录脱敏） and future acceptance criteria（未来验收标准）.

- `docs/04-implementation-plan/P2-003-external-coding-agent-bridge-design-plan.md`
  - Owns this step-by-step plan（逐步实施计划） for the P2-003 design package.

### Modify

- `docs/04-implementation-spec/INDEX.md`
  - Lists the P2-003 draft spec in Current Active Documents（当前活跃文档）.

- `docs/04-implementation-plan/INDEX.md`
  - Lists this draft plan in Current Active Documents.

- `docs/04-implementation-backlog/backlog.md`
  - Keeps P2-003 as `draft` and links the spec.

- `docs/INDEX.md`
  - Lists the P2-003 spec and plan as active pointers（活跃指针）.

---

## Task 1: Revise the P2-003 Design Spec（修订设计规格）

**Files:**
- Create or modify: `docs/04-implementation-spec/P2-003-external-coding-agent-bridge-design-spec.md`

- [ ] **Step 1: Write the CLI-focused spec file**

The spec must use these required sections:

```markdown
# P2-003 External Coding Agent Bridge Design Specification

## Status

draft

## Purpose

## Scope

## Authoritative Inputs

## Current Baseline

## Design Principles

## Execution Flow

## Future AgentAction Extension

## ExternalAgentCliProfile Requirements

## CLI Argument Injection Prevention

## ExternalAgentCliEvidencePackage

## Evidence Package Validation

## Event Mapping

## Permission Boundary

## Transcript Redaction

## Failure Semantics

## Evidence Summary Extension

## Testing and Acceptance Criteria

## Documentation Requirements for Future Implementation

## Self-Review Result
```

The spec must explicitly define:

- CLI single-request black-box execution（CLI 单一请求黑盒执行）.
- Simplified `external_agent_run` input with only `agent_profile_id`, `task`, and `allowed_write_set`.
- `ExternalAgentCliProfile`（外部智能体 CLI 配置画像） with `cli_executable`, `cli_args_template`, `working_directory_mode`, `allow_network`, `env_allowlist`, `max_wall_seconds`, and `max_output_bytes`.
- `ExternalAgentCliEvidencePackage`（外部智能体 CLI 证据包） with `exit_code`, `transcript`, `stderr`, `workspace_mutations`, and `network_fetches`.
- CLI argument injection prevention（CLI 参数注入防护）.
- stdout/stderr transcript redaction（标准输出/错误会话记录脱敏）.
- CLI failure semantics（CLI 失败语义） for executable missing, timeout, nonzero exit, output truncation, hash mismatch, denied mutation and secret leak.
- No parsing of external CLI internal tool calls（不解析外部 CLI 内部工具调用）.

- [ ] **Step 2: Verify the spec does not claim implementation**

Run:

```bash
python - <<'PY'
from pathlib import Path
path = Path('docs/04-implementation-spec/P2-003-external-coding-agent-bridge-design-spec.md')
text = path.read_text(encoding='utf-8')
for forbidden in (
    '## Status\n\nimplemented',
    'CLI ' + '已实现',
    'external_agent_run ' + '已实现',
    'M5 ' + '已完成',
):
    if forbidden in text:
        raise SystemExit(f'{path}: forbidden implementation claim: {forbidden}')
print('spec implementation boundary ok')
PY
```

Expected output:

```text
spec implementation boundary ok
```

- [ ] **Step 3: Verify CLI-specific fields exist and over-designed fields are absent**

Run:

```bash
python - <<'PY'
from pathlib import Path
spec = Path('docs/04-implementation-spec/P2-003-external-coding-agent-bridge-design-spec.md').read_text(encoding='utf-8')
required = [
    'cli_executable',
    'cli_args_template',
    'exit_code',
    'stderr',
    'allow_network',
    'max_wall_seconds',
    'max_output_bytes',
    'external_agent_cli_not_found',
    'external_agent_cli_timeout',
    'external_agent_cli_nonzero_exit',
    'external_agent_cli_output_truncated',
    'Transcript Redaction',
]
for field in required:
    if field not in spec:
        raise SystemExit(f'missing CLI-specific field: {field}')
for forbidden in (
    '"target_paths"',
    '"command_ids"',
    '"network_policy_ref"',
    '"max_external_steps"',
    '"output_contract"',
    '"allowed_tools"',
    '"command_policy_ref"',
    '"transcript_policy"',
    '"command_results"',
    'origin=external_agent',
):
    if forbidden in spec:
        raise SystemExit(f'over-designed field found: {forbidden}')
print('CLI boundary check ok')
PY
```

Expected output:

```text
CLI boundary check ok
```

- [ ] **Step 4: Commit checkpoint if authorized**

```bash
git add docs/04-implementation-spec/P2-003-external-coding-agent-bridge-design-spec.md
git commit -m "docs: 简化P2外部CLI智能体桥接规格"
```

---

## Task 2: Register the Spec in Implementation Spec Index（规格索引）

**Files:**
- Modify: `docs/04-implementation-spec/INDEX.md`

- [ ] **Step 1: Ensure P2-003 appears in Current Active Documents**

`docs/04-implementation-spec/INDEX.md` must contain this row under `## 3. Current Active Documents`:

```markdown
| `P2-003-external-coding-agent-bridge-design-spec.md` | draft | 定义 P2-003 external coding agent bridge（外部编码智能体桥接）的证据导入协议、权限边界和 future implementation（未来实现）验收 | 评审或实现 P2-003 前 |
```

- [ ] **Step 2: Verify index registration**

Run:

```bash
python - <<'PY'
from pathlib import Path
index = Path('docs/04-implementation-spec/INDEX.md').read_text(encoding='utf-8')
needle = 'P2-003-external-coding-agent-bridge-design-spec.md'
if needle not in index:
    raise SystemExit(f'missing {needle} in spec index')
print('spec index ok')
PY
```

Expected output:

```text
spec index ok
```

- [ ] **Step 3: Commit checkpoint if authorized**

```bash
git add docs/04-implementation-spec/INDEX.md
git commit -m "docs: 注册P2外部CLI智能体桥接规格"
```

---

## Task 3: Revise the P2-003 Implementation Plan（修订实施计划）

**Files:**
- Create or modify: `docs/04-implementation-plan/P2-003-external-coding-agent-bridge-design-plan.md`

- [ ] **Step 1: Write this CLI-focused plan file**

The plan must include:

- Standard plan header（标准计划头）.
- Scope and out-of-scope sections（范围与非范围）.
- File structure（文件结构）.
- Tasks for spec revision, index updates, backlog update, global index update and self-review.
- CLI-specific boundary check（CLI 特定边界检查）.
- Explicit statement that no runtime code starts before user review.

- [ ] **Step 2: Verify plan status is draft**

Run:

```bash
python - <<'PY'
from pathlib import Path
path = Path('docs/04-implementation-plan/P2-003-external-coding-agent-bridge-design-plan.md')
text = path.read_text(encoding='utf-8')
if '**Status:** draft' not in text:
    raise SystemExit('plan status must be draft while awaiting user review')
print('plan status ok')
PY
```

Expected output:

```text
plan status ok
```

- [ ] **Step 3: Verify plan includes CLI-specific self-review**

Run:

```bash
python - <<'PY'
from pathlib import Path
text = Path('docs/04-implementation-plan/P2-003-external-coding-agent-bridge-design-plan.md').read_text(encoding='utf-8')
for needle in ('CLI boundary check ok', 'cli_executable', 'cli_args_template', 'exit_code', 'stderr'):
    if needle not in text:
        raise SystemExit(f'plan missing CLI self-review item: {needle}')
print('plan CLI self-review ok')
PY
```

Expected output:

```text
plan CLI self-review ok
```

- [ ] **Step 4: Commit checkpoint if authorized**

```bash
git add docs/04-implementation-plan/P2-003-external-coding-agent-bridge-design-plan.md
git commit -m "docs: 简化P2外部CLI智能体桥接计划"
```

---

## Task 4: Register the Plan in Implementation Plan Index（计划索引）

**Files:**
- Modify: `docs/04-implementation-plan/INDEX.md`

- [ ] **Step 1: Ensure P2-003 appears in Current Active Documents**

`docs/04-implementation-plan/INDEX.md` must contain this row under `## 3. Current Active Documents`:

```markdown
| `P2-003-external-coding-agent-bridge-design-plan.md` | draft | 规划 P2-003 external coding agent bridge（外部编码智能体桥接）设计文档、索引和评审门禁 | 执行或评审 P2-003 设计批次时 |
```

- [ ] **Step 2: Verify plan index registration**

Run:

```bash
python - <<'PY'
from pathlib import Path
index = Path('docs/04-implementation-plan/INDEX.md').read_text(encoding='utf-8')
needle = 'P2-003-external-coding-agent-bridge-design-plan.md'
if needle not in index:
    raise SystemExit(f'missing {needle} in plan index')
print('plan index ok')
PY
```

Expected output:

```text
plan index ok
```

- [ ] **Step 3: Commit checkpoint if authorized**

```bash
git add docs/04-implementation-plan/INDEX.md
git commit -m "docs: 注册P2外部CLI智能体桥接计划"
```

---

## Task 5: Update Backlog（待办）

**Files:**
- Modify: `docs/04-implementation-backlog/backlog.md`

- [ ] **Step 1: Keep P2-003 as draft design work**

The P2-003 row must be:

```markdown
| P2-003 | 设计 external coding agent bridge（外部编码智能体桥接）的证据导入协议和权限边界 | draft | `P2-003-external-coding-agent-bridge-design-spec.md`, `roadmap.md`, `0002-use-provider-agnostic-action-protocol.md`, `0003-use-fail-closed-permission-model.md`, `0004-keep-boardroom-os-as-governance-source.md` |
```

- [ ] **Step 2: Ensure dependency note reflects CLI simplification**

The dependency notes must contain:

```markdown
- P2-003 has been reactivated as a design-only P2 work item using a CLI single-request black-box execution（CLI 单一请求黑盒执行） model. It must produce an authoritative spec（权威规格） and implementation plan（实施计划） for evidence import protocol（证据导入协议） and permission boundary（权限边界） before any `external_agent_run` runtime implementation. It remains draft（草案） until user review approves the design package.
```

- [ ] **Step 3: Verify backlog state**

Run:

```bash
python - <<'PY'
from pathlib import Path
text = Path('docs/04-implementation-backlog/backlog.md').read_text(encoding='utf-8')
if '| P2-003 |' not in text or '| draft |' not in text:
    raise SystemExit('P2-003 backlog row must be draft')
if 'P2-003-external-coding-agent-bridge-design-spec.md' not in text:
    raise SystemExit('P2-003 spec must be referenced in backlog')
if 'CLI 单一请求黑盒执行' not in text:
    raise SystemExit('P2-003 dependency note must mention CLI simplification')
print('backlog ok')
PY
```

Expected output:

```text
backlog ok
```

- [ ] **Step 4: Commit checkpoint if authorized**

```bash
git add docs/04-implementation-backlog/backlog.md
git commit -m "docs: 记录P2外部CLI智能体桥接范围"
```

---

## Task 6: Update Global Docs Index（全局文档索引）

**Files:**
- Modify: `docs/INDEX.md`

- [ ] **Step 1: Ensure current active pointers exist**

`docs/INDEX.md` must contain these rows under `## 3. 当前活跃文档指针`:

```markdown
| P0 | `docs/04-implementation-spec/P2-003-external-coding-agent-bridge-design-spec.md` | draft | 评审或实现 P2-003 external coding agent bridge（外部编码智能体桥接）证据导入协议和权限边界前 |
| P0 | `docs/04-implementation-plan/P2-003-external-coding-agent-bridge-design-plan.md` | draft | 评审或执行 P2-003 external coding agent bridge（外部编码智能体桥接）设计计划时 |
```

- [ ] **Step 2: Verify global index pointers**

Run:

```bash
python - <<'PY'
from pathlib import Path
text = Path('docs/INDEX.md').read_text(encoding='utf-8')
for needle in (
    'docs/04-implementation-spec/P2-003-external-coding-agent-bridge-design-spec.md',
    'docs/04-implementation-plan/P2-003-external-coding-agent-bridge-design-plan.md',
):
    if needle not in text:
        raise SystemExit(f'missing global pointer: {needle}')
print('global index ok')
PY
```

Expected output:

```text
global index ok
```

- [ ] **Step 3: Commit checkpoint if authorized**

```bash
git add docs/INDEX.md
git commit -m "docs: 保持P2外部CLI智能体桥接活跃指针"
```

---

## Task 7: Self-Review and Validation（自审与验证）

**Files:**
- Verify: all files touched by this plan

- [ ] **Step 1: Scan for placeholders**

Run:

```bash
python - <<'PY'
from pathlib import Path
paths = [
    Path('docs/04-implementation-spec/P2-003-external-coding-agent-bridge-design-spec.md'),
    Path('docs/04-implementation-plan/P2-003-external-coding-agent-bridge-design-plan.md'),
]
needles = ('T' + 'BD', 'TO' + 'DO', 'implement' + ' later', 'fill in' + ' details', '稍后' + '补充', '待' + '补充')
for path in paths:
    text = path.read_text(encoding='utf-8')
    for needle in needles:
        if needle in text:
            raise SystemExit(f'{path}: placeholder found: {needle}')
print('placeholder scan ok')
PY
```

Expected output:

```text
placeholder scan ok
```

- [ ] **Step 2: Scan for forbidden implementation semantics**

Run:

```bash
python - <<'PY'
from pathlib import Path
paths = [
    Path('docs/04-implementation-spec/P2-003-external-coding-agent-bridge-design-spec.md'),
    Path('docs/04-implementation-plan/P2-003-external-coding-agent-bridge-design-plan.md'),
]
for path in paths:
    text = path.read_text(encoding='utf-8')
    for forbidden in ('## Status\n\nimplemented', '**Status:** ' + 'implemented', 'CLI ' + '已实现', 'external_agent_run ' + '已实现', 'M5 ' + '已完成'):
        if forbidden in text:
            raise SystemExit(f'{path}: forbidden implementation semantics: {forbidden}')
print('implementation semantics ok')
PY
```

Expected output:

```text
implementation semantics ok
```

- [ ] **Step 3: Verify CLI-specific boundaries**

Run:

```bash
python - <<'PY'
from pathlib import Path
spec = Path('docs/04-implementation-spec/P2-003-external-coding-agent-bridge-design-spec.md').read_text(encoding='utf-8')
required = [
    'cli_executable',
    'cli_args_template',
    'exit_code',
    'stderr',
    'allow_network',
    'max_wall_seconds',
    'max_output_bytes',
    'external_agent_cli_not_found',
    'external_agent_cli_timeout',
    'external_agent_cli_nonzero_exit',
    'external_agent_cli_output_truncated',
    'Transcript Redaction',
]
for field in required:
    if field not in spec:
        raise SystemExit(f'missing CLI-specific field: {field}')
for forbidden in (
    '"target_paths"',
    '"command_ids"',
    '"network_policy_ref"',
    '"max_external_steps"',
    '"output_contract"',
    '"allowed_tools"',
    '"command_policy_ref"',
    '"transcript_policy"',
    '"command_results"',
    'origin=external_agent',
):
    if forbidden in spec:
        raise SystemExit(f'over-designed field found: {forbidden}')
print('CLI boundary check ok')
PY
```

Expected output:

```text
CLI boundary check ok
```

- [ ] **Step 4: Check indexes**

Run:

```bash
python - <<'PY'
from pathlib import Path
checks = {
    Path('docs/04-implementation-spec/INDEX.md'): ['P2-003-external-coding-agent-bridge-design-spec.md'],
    Path('docs/04-implementation-plan/INDEX.md'): ['P2-003-external-coding-agent-bridge-design-plan.md'],
    Path('docs/04-implementation-backlog/backlog.md'): ['| P2-003 |', '| draft |', 'P2-003-external-coding-agent-bridge-design-spec.md', 'CLI 单一请求黑盒执行'],
    Path('docs/INDEX.md'): [
        'docs/04-implementation-spec/P2-003-external-coding-agent-bridge-design-spec.md',
        'docs/04-implementation-plan/P2-003-external-coding-agent-bridge-design-plan.md',
    ],
}
for path, needles in checks.items():
    text = path.read_text(encoding='utf-8')
    for needle in needles:
        if needle not in text:
            raise SystemExit(f'{path}: missing {needle}')
print('index registration ok')
PY
```

Expected output:

```text
index registration ok
```

- [ ] **Step 5: Check markdown whitespace**

Run:

```bash
git diff --check \
  docs/04-implementation-spec/P2-003-external-coding-agent-bridge-design-spec.md \
  docs/04-implementation-plan/P2-003-external-coding-agent-bridge-design-plan.md \
  docs/04-implementation-spec/INDEX.md \
  docs/04-implementation-plan/INDEX.md \
  docs/04-implementation-backlog/backlog.md \
  docs/INDEX.md
```

Expected: no output.

- [ ] **Step 6: Check git scope**

Run:

```bash
git status --short
```

Expected scope:

```text
 M docs/INDEX.md
 M docs/04-implementation-backlog/backlog.md
 M docs/04-implementation-plan/INDEX.md
 M docs/04-implementation-spec/INDEX.md
?? docs/04-implementation-plan/P2-003-external-coding-agent-bridge-design-plan.md
?? docs/04-implementation-spec/P2-003-external-coding-agent-bridge-design-spec.md
```

If additional files appear, inspect and explain before asking for user review.

---

## Task 8: User Review Gate（用户评审门禁）

**Files:**
- No additional file changes.

- [ ] **Step 1: Stop after self-review**

After Task 7 passes, stop and ask the user to review:

```text
Spec and plan revised for the CLI single-request black-box design and self-reviewed. Please review the P2-003 design package before implementation:
- docs/04-implementation-spec/P2-003-external-coding-agent-bridge-design-spec.md
- docs/04-implementation-plan/P2-003-external-coding-agent-bridge-design-plan.md
```

- [ ] **Step 2: Do not implement runtime code before approval**

Do not modify:

```text
src/atomic_agent/models.py
src/atomic_agent/action_parser.py
src/atomic_agent/agent_loop.py
src/atomic_agent/event_recorder.py
src/atomic_agent/evidence.py
tests/*.py
```

until the user explicitly approves the design and asks to begin implementation.

---

## Self-Review Result

### Spec Coverage（规格覆盖）

- Covers the P2-003 backlog requirement to design evidence import protocol（证据导入协议） and permission boundary（权限边界）.
- Aligns with the CLI single-request black-box model requested in review.
- Defines simplified `external_agent_run` input.
- Defines `ExternalAgentCliProfile` and `ExternalAgentCliEvidencePackage`.
- Defines CLI execution flow, argument injection prevention, transcript redaction, event mapping, failure kinds and no-fallback rules.
- Keeps Boardroom OS as governance source（治理事实源）.
- Leaves real implementation and external CLI agent gates for a later approved implementation batch.

### Over-Design Removal（过度设计移除）

- Removes `target_paths`, `command_ids`, `network_policy_ref`, `max_external_steps`, and `output_contract` from action input.
- Removes `allowed_tools`, `command_policy_ref`, and `transcript_policy` from profile requirements.
- Removes `command_results` from evidence package.
- Removes `command.completed` mapping for external CLI internals.

### CLI-Specific Additions（CLI 特定补充）

- Adds `cli_executable` and `cli_args_template`.
- Adds `exit_code` and `stderr` to evidence package.
- Adds `allow_network`, `max_wall_seconds`, and `max_output_bytes`.
- Adds CLI failure types for missing executable, timeout, nonzero exit and output truncation.
- Adds CLI argument injection prevention.
- Adds stdout/stderr redaction rules.

### Scope Check（范围检查）

- This plan does not include runtime code, tests, provider calls, CLI execution or Boardroom verifier implementation.
- The design package is suitable for user review before a separate implementation plan is executed.

### No-Fallback Check（无降级检查）

- The spec explicitly rejects executable fallback, sandbox fallback, nonzero-exit success, output truncation success, network fallback, hash mismatch trust and secret leak import.
- Evidence import must fail closed on schema, hash, path, network, redaction or governance violations.
