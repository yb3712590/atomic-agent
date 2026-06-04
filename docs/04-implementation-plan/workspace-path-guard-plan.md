# Workspace Path Guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement P0-003 `workspace path guard`（工作区路径守卫） so filesystem tools（文件系统工具） can make fail-closed（失败关闭）, auditable read/write path decisions.

**Architecture:** Add a focused `path_guard`（路径守卫） module that owns path normalization, workspace containment, symlink escape（符号链接逃逸） detection, and allowed write set（允许写入集合） matching. The module returns structured `PathDecision`（路径决策） values only; it does not read, write, patch, emit events, or run tools.

**Tech Stack:** Python 3.11+, `pathlib`（路径处理）, `dataclasses`（轻量数据结构）, pytest（测试）.

**Status:** implemented

---

## Scope

This plan implements P0-003 only.

In scope:

- Create `src/atomic_agent/path_guard.py`（路径守卫模块）.
- Create `tests/test_path_guard.py`（路径守卫测试）.
- Add read path（读路径） decisions constrained by workspace root（工作区根目录）.
- Add write path（写路径） decisions constrained by allowed write set（允许写入集合）.
- Reject absolute paths（绝对路径）, empty paths（空路径）, `..` traversal（路径逃逸）, workspace escape（工作区逃逸）, symlink escape（符号链接逃逸）, and unauthorized writes（未授权写入）.

Out of scope:

- No filesystem tool execution.
- No file content reads or writes.
- No patch application.
- No event recorder or JSONL output.
- No command, network, provider, budget, or AgentLoop（智能体循环） changes.
- No commit unless the user explicitly requests it.

## File Structure

- Create: `src/atomic_agent/path_guard.py`
  - Defines `PathDecisionType`（路径决策类型）, `PathDecision`（路径决策）, `PathGuardConfigError`（路径守卫配置错误）, and `WorkspacePathGuard`（工作区路径守卫）.
- Create: `tests/test_path_guard.py`
  - Covers positive and negative read/write permission decisions with real filesystem paths.
- Modify after implementation passes: `docs/04-implementation-backlog/backlog.md`
  - Marks P0-003 completed only after tests pass and review accepts implementation.
- Modify after implementation passes: `docs/04-implementation-spec/INDEX.md`
  - Moves `workspace-path-guard-spec.md`（路径守卫规格） from draft to implemented or approved status.
- Modify after implementation passes: `docs/04-implementation-plan/INDEX.md`
  - Moves this plan from current draft to completed / archived.

---

### Task 1: Add read-path happy path tests

**Files:**

- Create: `tests/test_path_guard.py`
- Create: `src/atomic_agent/path_guard.py`

- [ ] **Step 1: Write the first failing read-path tests**

Write `tests/test_path_guard.py`:

```python
from pathlib import Path

from atomic_agent.path_guard import PathDecisionType, WorkspacePathGuard


def test_resolve_read_path_allows_relative_path_inside_workspace(tmp_path):
    target = tmp_path / "src" / "atomic_agent" / "models.py"
    target.parent.mkdir(parents=True)
    target.write_text("content", encoding="utf-8")
    guard = WorkspacePathGuard(tmp_path, allowed_write_set=[])

    decision = guard.resolve_read_path("src/atomic_agent/models.py")

    assert decision.decision == PathDecisionType.ALLOW
    assert decision.requested_path == "src/atomic_agent/models.py"
    assert decision.normalized_path == str(target.resolve())
    assert decision.reason == "read_path_allowed"
    assert decision.matched_policy == "workspace_root"


def test_resolve_read_path_allows_nonexistent_path_inside_workspace(tmp_path):
    existing_parent = tmp_path / "docs"
    existing_parent.mkdir()
    target = existing_parent / "missing.md"
    guard = WorkspacePathGuard(tmp_path, allowed_write_set=[])

    decision = guard.resolve_read_path("docs/missing.md")

    assert decision.decision == PathDecisionType.ALLOW
    assert decision.requested_path == "docs/missing.md"
    assert decision.normalized_path == str(target.resolve())
    assert decision.reason == "read_path_allowed"
    assert decision.matched_policy == "workspace_root"
```

- [ ] **Step 2: Run the new tests and confirm they fail because the module does not exist**

Run:

```bash
pytest tests/test_path_guard.py::test_resolve_read_path_allows_relative_path_inside_workspace tests/test_path_guard.py::test_resolve_read_path_allows_nonexistent_path_inside_workspace -v
```

Expected:

```text
ModuleNotFoundError: No module named 'atomic_agent.path_guard'
```

- [ ] **Step 3: Add the minimal module and read-path implementation**

Write `src/atomic_agent/path_guard.py`:

```python
from dataclasses import dataclass
from enum import Enum
from pathlib import Path, PureWindowsPath


class PathDecisionType(str, Enum):
    ALLOW = "allow"
    DENY = "deny"


@dataclass(frozen=True)
class PathDecision:
    decision: PathDecisionType
    requested_path: str
    normalized_path: str | None
    reason: str
    matched_policy: str | None = None


class PathGuardConfigError(ValueError):
    pass


class WorkspacePathGuard:
    def __init__(self, workspace_root: str | Path, allowed_write_set: list[str]):
        self.workspace_root = Path(workspace_root).resolve(strict=True)
        if not self.workspace_root.is_dir():
            raise PathGuardConfigError("workspace_root must be an existing directory")
        self.allowed_write_set = allowed_write_set

    def resolve_read_path(self, requested_path: str) -> PathDecision:
        decision = self._resolve_workspace_path(requested_path)
        if decision.decision == PathDecisionType.DENY:
            return decision
        return PathDecision(
            decision=PathDecisionType.ALLOW,
            requested_path=requested_path,
            normalized_path=decision.normalized_path,
            reason="read_path_allowed",
            matched_policy="workspace_root",
        )

    def resolve_write_path(self, requested_path: str) -> PathDecision:
        return self.resolve_read_path(requested_path)

    def _resolve_workspace_path(self, requested_path: str) -> PathDecision:
        if not requested_path or not requested_path.strip() or requested_path == ".":
            return PathDecision(PathDecisionType.DENY, requested_path, None, "empty_path_denied")
        if Path(requested_path).is_absolute() or PureWindowsPath(requested_path).is_absolute():
            return PathDecision(PathDecisionType.DENY, requested_path, None, "absolute_path_denied")
        if ".." in Path(requested_path).parts:
            return PathDecision(PathDecisionType.DENY, requested_path, None, "path_escape_denied")

        normalized_path = self._resolve_candidate(self.workspace_root / requested_path)
        if not normalized_path.is_relative_to(self.workspace_root):
            return PathDecision(
                PathDecisionType.DENY,
                requested_path,
                str(normalized_path),
                "path_outside_workspace_denied",
            )
        return PathDecision(PathDecisionType.ALLOW, requested_path, str(normalized_path), "path_allowed")

    def _resolve_candidate(self, candidate: Path) -> Path:
        if candidate.exists():
            return candidate.resolve(strict=True)

        missing_parts = []
        current = candidate
        while not current.exists():
            missing_parts.append(current.name)
            parent = current.parent
            if parent == current:
                raise PathGuardConfigError("workspace_root must have an existing ancestor")
            current = parent

        resolved = current.resolve(strict=True)
        for part in reversed(missing_parts):
            resolved = resolved / part
        return resolved
```

- [ ] **Step 4: Run the targeted test and confirm it passes**

Run:

```bash
pytest tests/test_path_guard.py::test_resolve_read_path_allows_relative_path_inside_workspace tests/test_path_guard.py::test_resolve_read_path_allows_nonexistent_path_inside_workspace -v
```

Expected:

```text
PASSED
```

---

### Task 2: Reject invalid path inputs

**Files:**

- Modify: `tests/test_path_guard.py`
- Modify: `src/atomic_agent/path_guard.py`

- [ ] **Step 1: Add tests for empty paths, absolute paths, and traversal**

Append to `tests/test_path_guard.py`:

```python
import pytest


@pytest.mark.parametrize("requested_path", ["", "   ", "."])
def test_resolve_read_path_rejects_empty_paths(tmp_path, requested_path):
    guard = WorkspacePathGuard(tmp_path, allowed_write_set=[])

    decision = guard.resolve_read_path(requested_path)

    assert decision.decision == PathDecisionType.DENY
    assert decision.normalized_path is None
    assert decision.reason == "empty_path_denied"


@pytest.mark.parametrize("requested_path", ["/tmp/file.txt", "C:/tmp/file.txt"])
def test_resolve_read_path_rejects_absolute_paths(tmp_path, requested_path):
    guard = WorkspacePathGuard(tmp_path, allowed_write_set=[])

    decision = guard.resolve_read_path(requested_path)

    assert decision.decision == PathDecisionType.DENY
    assert decision.normalized_path is None
    assert decision.reason == "absolute_path_denied"


@pytest.mark.parametrize("requested_path", ["../outside.txt", "docs/../outside.txt"])
def test_resolve_read_path_rejects_path_traversal(tmp_path, requested_path):
    guard = WorkspacePathGuard(tmp_path, allowed_write_set=[])

    decision = guard.resolve_read_path(requested_path)

    assert decision.decision == PathDecisionType.DENY
    assert decision.normalized_path is None
    assert decision.reason == "path_escape_denied"
```

- [ ] **Step 2: Run the invalid-input tests**

Run:

```bash
pytest tests/test_path_guard.py::test_resolve_read_path_rejects_empty_paths tests/test_path_guard.py::test_resolve_read_path_rejects_absolute_paths tests/test_path_guard.py::test_resolve_read_path_rejects_path_traversal -v
```

Expected:

```text
PASSED
```

The minimal implementation from Task 1 already contains these checks; this step locks them with explicit tests.

---

### Task 3: Reject symlink escape

**Files:**

- Modify: `tests/test_path_guard.py`
- Modify: `src/atomic_agent/path_guard.py`

- [ ] **Step 1: Add symlink escape tests**

Append to `tests/test_path_guard.py`:

```python
def test_resolve_read_path_rejects_symlink_escape(tmp_path):
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir()
    outside_file = outside / "secret.txt"
    outside_file.write_text("secret", encoding="utf-8")
    link = tmp_path / "link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"symlink creation is unavailable: {error}")
    guard = WorkspacePathGuard(tmp_path, allowed_write_set=[])

    decision = guard.resolve_read_path("link/secret.txt")

    assert decision.decision == PathDecisionType.DENY
    assert decision.normalized_path == str(outside_file.resolve())
    assert decision.reason == "symlink_escape_denied"
```

- [ ] **Step 2: Run the symlink test and confirm the reason is not specific enough**

Run:

```bash
pytest tests/test_path_guard.py::test_resolve_read_path_rejects_symlink_escape -v
```

Expected before the fix:

```text
FAILED tests/test_path_guard.py::test_resolve_read_path_rejects_symlink_escape
```

The failure should show `path_outside_workspace_denied` instead of `symlink_escape_denied`.

- [ ] **Step 3: Track whether an input path crosses a symlink**

Modify `src/atomic_agent/path_guard.py` to this complete version:

```python
from dataclasses import dataclass
from enum import Enum
from pathlib import Path, PureWindowsPath


class PathDecisionType(str, Enum):
    ALLOW = "allow"
    DENY = "deny"


@dataclass(frozen=True)
class PathDecision:
    decision: PathDecisionType
    requested_path: str
    normalized_path: str | None
    reason: str
    matched_policy: str | None = None


@dataclass(frozen=True)
class ResolvedPath:
    path: Path
    crossed_symlink: bool


class PathGuardConfigError(ValueError):
    pass


class WorkspacePathGuard:
    def __init__(self, workspace_root: str | Path, allowed_write_set: list[str]):
        self.workspace_root = Path(workspace_root).resolve(strict=True)
        if not self.workspace_root.is_dir():
            raise PathGuardConfigError("workspace_root must be an existing directory")
        self.allowed_write_set = allowed_write_set

    def resolve_read_path(self, requested_path: str) -> PathDecision:
        decision = self._resolve_workspace_path(requested_path)
        if decision.decision == PathDecisionType.DENY:
            return decision
        return PathDecision(
            decision=PathDecisionType.ALLOW,
            requested_path=requested_path,
            normalized_path=decision.normalized_path,
            reason="read_path_allowed",
            matched_policy="workspace_root",
        )

    def resolve_write_path(self, requested_path: str) -> PathDecision:
        return self.resolve_read_path(requested_path)

    def _resolve_workspace_path(self, requested_path: str) -> PathDecision:
        if not requested_path or not requested_path.strip() or requested_path == ".":
            return PathDecision(PathDecisionType.DENY, requested_path, None, "empty_path_denied")
        if Path(requested_path).is_absolute() or PureWindowsPath(requested_path).is_absolute():
            return PathDecision(PathDecisionType.DENY, requested_path, None, "absolute_path_denied")
        if ".." in Path(requested_path).parts:
            return PathDecision(PathDecisionType.DENY, requested_path, None, "path_escape_denied")

        resolved = self._resolve_candidate(self.workspace_root / requested_path)
        if not resolved.path.is_relative_to(self.workspace_root):
            reason = "symlink_escape_denied" if resolved.crossed_symlink else "path_outside_workspace_denied"
            return PathDecision(
                PathDecisionType.DENY,
                requested_path,
                str(resolved.path),
                reason,
            )
        return PathDecision(PathDecisionType.ALLOW, requested_path, str(resolved.path), "path_allowed")

    def _resolve_candidate(self, candidate: Path) -> ResolvedPath:
        crossed_symlink = self._crosses_symlink(candidate)
        if candidate.exists():
            return ResolvedPath(candidate.resolve(strict=True), crossed_symlink)

        missing_parts = []
        current = candidate
        while not current.exists():
            missing_parts.append(current.name)
            parent = current.parent
            if parent == current:
                raise PathGuardConfigError("workspace_root must have an existing ancestor")
            current = parent

        resolved = current.resolve(strict=True)
        for part in reversed(missing_parts):
            resolved = resolved / part
        return ResolvedPath(resolved, crossed_symlink)

    def _crosses_symlink(self, candidate: Path) -> bool:
        current = self.workspace_root
        try:
            relative_parts = candidate.relative_to(self.workspace_root).parts
        except ValueError:
            return False

        for part in relative_parts:
            current = current / part
            if current.is_symlink():
                return True
            if not current.exists():
                return False
        return False
```

- [ ] **Step 4: Run read-path tests**

Run:

```bash
pytest tests/test_path_guard.py::test_resolve_read_path_allows_relative_path_inside_workspace tests/test_path_guard.py::test_resolve_read_path_rejects_empty_paths tests/test_path_guard.py::test_resolve_read_path_rejects_absolute_paths tests/test_path_guard.py::test_resolve_read_path_rejects_path_traversal tests/test_path_guard.py::test_resolve_read_path_rejects_symlink_escape -v
```

Expected:

```text
PASSED
```

---

### Task 4: Add allowed write set semantics

**Files:**

- Modify: `tests/test_path_guard.py`
- Modify: `src/atomic_agent/path_guard.py`

- [ ] **Step 1: Add write-path tests**

Append to `tests/test_path_guard.py`:

```python
def test_resolve_write_path_allows_exact_allowed_file(tmp_path):
    guard = WorkspacePathGuard(tmp_path, allowed_write_set=["docs/output.md"])

    decision = guard.resolve_write_path("docs/output.md")

    assert decision.decision == PathDecisionType.ALLOW
    assert decision.reason == "write_path_allowed"
    assert decision.normalized_path == str((tmp_path / "docs" / "output.md").resolve())
    assert decision.matched_policy == "docs/output.md"


def test_resolve_write_path_rejects_path_outside_allowed_write_set(tmp_path):
    guard = WorkspacePathGuard(tmp_path, allowed_write_set=["docs/output.md"])

    decision = guard.resolve_write_path("src/atomic_agent/models.py")

    assert decision.decision == PathDecisionType.DENY
    assert decision.reason == "write_not_allowed"
    assert decision.matched_policy is None


def test_resolve_write_path_allows_directory_policy_child(tmp_path):
    guard = WorkspacePathGuard(tmp_path, allowed_write_set=["docs/generated/"])

    decision = guard.resolve_write_path("docs/generated/output.md")

    assert decision.decision == PathDecisionType.ALLOW
    assert decision.reason == "write_path_allowed"
    assert decision.matched_policy == "docs/generated/"


def test_resolve_write_path_rejects_directory_policy_string_prefix(tmp_path):
    guard = WorkspacePathGuard(tmp_path, allowed_write_set=["docs/generated/"])

    decision = guard.resolve_write_path("docs/generated-other/output.md")

    assert decision.decision == PathDecisionType.DENY
    assert decision.reason == "write_not_allowed"
    assert decision.matched_policy is None
```

- [ ] **Step 2: Run write-path tests and confirm unauthorized write logic is missing**

Run:

```bash
pytest tests/test_path_guard.py::test_resolve_write_path_allows_exact_allowed_file tests/test_path_guard.py::test_resolve_write_path_rejects_path_outside_allowed_write_set tests/test_path_guard.py::test_resolve_write_path_allows_directory_policy_child tests/test_path_guard.py::test_resolve_write_path_rejects_directory_policy_string_prefix -v
```

Expected before the fix:

```text
FAILED tests/test_path_guard.py::test_resolve_write_path_rejects_path_outside_allowed_write_set
FAILED tests/test_path_guard.py::test_resolve_write_path_rejects_directory_policy_string_prefix
```

- [ ] **Step 3: Implement allowed write set matching**

Modify `src/atomic_agent/path_guard.py` to add `AllowedWritePath` and write matching:

```python
from dataclasses import dataclass
from enum import Enum
from pathlib import Path, PureWindowsPath


class PathDecisionType(str, Enum):
    ALLOW = "allow"
    DENY = "deny"


@dataclass(frozen=True)
class PathDecision:
    decision: PathDecisionType
    requested_path: str
    normalized_path: str | None
    reason: str
    matched_policy: str | None = None


@dataclass(frozen=True)
class ResolvedPath:
    path: Path
    crossed_symlink: bool


@dataclass(frozen=True)
class AllowedWritePath:
    original: str
    path: Path
    is_directory: bool


class PathGuardConfigError(ValueError):
    pass


class WorkspacePathGuard:
    def __init__(self, workspace_root: str | Path, allowed_write_set: list[str]):
        self.workspace_root = Path(workspace_root).resolve(strict=True)
        if not self.workspace_root.is_dir():
            raise PathGuardConfigError("workspace_root must be an existing directory")
        self.allowed_write_set = self._normalize_allowed_write_set(allowed_write_set)

    def resolve_read_path(self, requested_path: str) -> PathDecision:
        decision = self._resolve_workspace_path(requested_path)
        if decision.decision == PathDecisionType.DENY:
            return decision
        return PathDecision(
            decision=PathDecisionType.ALLOW,
            requested_path=requested_path,
            normalized_path=decision.normalized_path,
            reason="read_path_allowed",
            matched_policy="workspace_root",
        )

    def resolve_write_path(self, requested_path: str) -> PathDecision:
        decision = self._resolve_workspace_path(requested_path)
        if decision.decision == PathDecisionType.DENY:
            return decision

        normalized = Path(decision.normalized_path) if decision.normalized_path else None
        matched_policy = self._match_allowed_write_path(normalized)
        if matched_policy is None:
            return PathDecision(
                PathDecisionType.DENY,
                requested_path,
                decision.normalized_path,
                "write_not_allowed",
            )
        return PathDecision(
            PathDecisionType.ALLOW,
            requested_path,
            decision.normalized_path,
            "write_path_allowed",
            matched_policy.original,
        )

    def _normalize_allowed_write_set(self, allowed_write_set: list[str]) -> list[AllowedWritePath]:
        normalized = []
        for entry in allowed_write_set:
            validation = self._validate_relative_policy_path(entry)
            if validation is not None:
                raise PathGuardConfigError(validation)
            is_directory = entry.endswith("/")
            resolved = self._resolve_candidate(self.workspace_root / entry.rstrip("/"))
            if not resolved.path.is_relative_to(self.workspace_root):
                raise PathGuardConfigError("allowed write path must stay inside workspace_root")
            normalized.append(AllowedWritePath(entry, resolved.path, is_directory))
        return normalized

    def _validate_relative_policy_path(self, path: str) -> str | None:
        if not path or not path.strip() or path == ".":
            return "allowed write path must be a non-empty relative path"
        if Path(path).is_absolute() or PureWindowsPath(path).is_absolute():
            return "allowed write path must be relative"
        if ".." in Path(path).parts:
            return "allowed write path cannot contain '..'"
        return None

    def _match_allowed_write_path(self, normalized_path: Path | None) -> AllowedWritePath | None:
        if normalized_path is None:
            return None
        for allowed in self.allowed_write_set:
            if allowed.is_directory and normalized_path.is_relative_to(allowed.path):
                return allowed
            if not allowed.is_directory and normalized_path == allowed.path:
                return allowed
        return None

    def _resolve_workspace_path(self, requested_path: str) -> PathDecision:
        if not requested_path or not requested_path.strip() or requested_path == ".":
            return PathDecision(PathDecisionType.DENY, requested_path, None, "empty_path_denied")
        if Path(requested_path).is_absolute() or PureWindowsPath(requested_path).is_absolute():
            return PathDecision(PathDecisionType.DENY, requested_path, None, "absolute_path_denied")
        if ".." in Path(requested_path).parts:
            return PathDecision(PathDecisionType.DENY, requested_path, None, "path_escape_denied")

        resolved = self._resolve_candidate(self.workspace_root / requested_path)
        if not resolved.path.is_relative_to(self.workspace_root):
            reason = "symlink_escape_denied" if resolved.crossed_symlink else "path_outside_workspace_denied"
            return PathDecision(
                PathDecisionType.DENY,
                requested_path,
                str(resolved.path),
                reason,
            )
        return PathDecision(PathDecisionType.ALLOW, requested_path, str(resolved.path), "path_allowed")

    def _resolve_candidate(self, candidate: Path) -> ResolvedPath:
        crossed_symlink = self._crosses_symlink(candidate)
        if candidate.exists():
            return ResolvedPath(candidate.resolve(strict=True), crossed_symlink)

        missing_parts = []
        current = candidate
        while not current.exists():
            missing_parts.append(current.name)
            parent = current.parent
            if parent == current:
                raise PathGuardConfigError("workspace_root must have an existing ancestor")
            current = parent

        resolved = current.resolve(strict=True)
        for part in reversed(missing_parts):
            resolved = resolved / part
        return ResolvedPath(resolved, crossed_symlink)

    def _crosses_symlink(self, candidate: Path) -> bool:
        current = self.workspace_root
        try:
            relative_parts = candidate.relative_to(self.workspace_root).parts
        except ValueError:
            return False

        for part in relative_parts:
            current = current / part
            if current.is_symlink():
                return True
            if not current.exists():
                return False
        return False
```

- [ ] **Step 4: Run write-path tests**

Run:

```bash
pytest tests/test_path_guard.py::test_resolve_write_path_allows_exact_allowed_file tests/test_path_guard.py::test_resolve_write_path_rejects_path_outside_allowed_write_set tests/test_path_guard.py::test_resolve_write_path_allows_directory_policy_child tests/test_path_guard.py::test_resolve_write_path_rejects_directory_policy_string_prefix -v
```

Expected:

```text
PASSED
```

---

### Task 5: Reject invalid allowed write set configuration

**Files:**

- Modify: `tests/test_path_guard.py`
- Verify: `src/atomic_agent/path_guard.py`

- [ ] **Step 1: Add configuration failure tests**

Update the import line in `tests/test_path_guard.py` to:

```python
from atomic_agent.path_guard import PathDecisionType, PathGuardConfigError, WorkspacePathGuard
```

Append:

```python
@pytest.mark.parametrize("allowed_path", ["", "   ", ".", "/tmp/output.md", "C:/tmp/output.md", "../output.md"])
def test_guard_rejects_invalid_allowed_write_set_entries(tmp_path, allowed_path):
    with pytest.raises(PathGuardConfigError):
        WorkspacePathGuard(tmp_path, allowed_write_set=[allowed_path])


def test_guard_rejects_allowed_write_set_symlink_escape(tmp_path):
    outside = tmp_path.parent / f"{tmp_path.name}-outside-policy"
    outside.mkdir()
    link = tmp_path / "allowed-link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"symlink creation is unavailable: {error}")

    with pytest.raises(PathGuardConfigError):
        WorkspacePathGuard(tmp_path, allowed_write_set=["allowed-link/output.md"])
```

- [ ] **Step 2: Run configuration tests**

Run:

```bash
pytest tests/test_path_guard.py::test_guard_rejects_invalid_allowed_write_set_entries tests/test_path_guard.py::test_guard_rejects_allowed_write_set_symlink_escape -v
```

Expected:

```text
PASSED
```

The implementation from Task 4 should already pass these tests because invalid policy entries raise `PathGuardConfigError` during initialization.

---

### Task 6: Run full verification

**Files:**

- Verify: `src/atomic_agent/path_guard.py`
- Verify: `tests/test_path_guard.py`
- Verify existing tests

- [ ] **Step 1: Run path guard tests**

Run:

```bash
pytest tests/test_path_guard.py -v
```

Expected:

```text
PASSED
```

- [ ] **Step 2: Run full test suite**

Run:

```bash
pytest -v
```

Expected:

```text
PASSED
```

- [ ] **Step 3: Check there is no runtime environment fallback**

Run:

```powershell
@'
from pathlib import Path
for path in Path('src').rglob('*.py'):
    text = path.read_text(encoding='utf-8')
    for needle in ('os.environ', 'getenv', 'dotenv', '.env'):
        if needle in text:
            print(f'{path}: contains {needle}')
'@ | python
```

Expected:

```text

```

No output means runtime source does not read environment fallback.

- [ ] **Step 4: Check working tree scope**

Run:

```bash
git status --short
```

Expected:

```text
 M docs/04-implementation-plan/INDEX.md
 M docs/04-implementation-spec/INDEX.md
?? docs/04-implementation-plan/workspace-path-guard-plan.md
?? docs/04-implementation-spec/workspace-path-guard-spec.md
?? src/atomic_agent/path_guard.py
?? tests/test_path_guard.py
```

Before user review, only the two docs and indexes should exist. After implementation, `src/atomic_agent/path_guard.py` and `tests/test_path_guard.py` should appear.

---

### Task 7: Update docs after implementation passes

**Files:**

- Modify: `docs/04-implementation-backlog/backlog.md`
- Modify: `docs/04-implementation-spec/INDEX.md`
- Modify: `docs/04-implementation-plan/INDEX.md`

- [ ] **Step 1: Mark P0-003 completed only after tests pass**

Change `docs/04-implementation-backlog/backlog.md` from:

```markdown
| P0-003 | 实现 workspace path guard（工作区路径守卫） | pending | `permission-and-sandbox-architecture.md` |
```

To:

```markdown
| P0-003 | 实现 workspace path guard（工作区路径守卫） | completed | `workspace-path-guard-spec.md`, `permission-and-sandbox-architecture.md` |
```

- [ ] **Step 2: Move spec index entry out of draft status**

Change `docs/04-implementation-spec/INDEX.md` current entry for `workspace-path-guard-spec.md` from `draft` to `implemented` after tests pass and user review accepts the implementation.

- [ ] **Step 3: Move plan index entry to completed / archived**

Move `workspace-path-guard-plan.md` from Current Active Documents to Completed / Archived Documents after P0-003 is implemented and verified.

- [ ] **Step 4: Run final verification**

Run:

```bash
pytest -v
git status --short
```

Expected:

```text
PASSED
```

`git status --short` should show only P0-003 implementation, tests, and required docs/index updates.

---

## Self-Review Checklist

Before implementation is considered ready for review:

- [ ] Spec coverage: All P0-003 requirements in `workspace-path-guard-spec.md` are covered by tests or code.
- [ ] Placeholder scan: This plan contains no placeholders, deferred implementation steps, or unspecified test cases.
- [ ] Type consistency: `PathDecisionType`, `PathDecision`, `PathGuardConfigError`, `WorkspacePathGuard`, and method names match across tests and implementation steps.
- [ ] Scope check: No filesystem tool execution, event recording, command policy, network policy, provider logic, budget logic, or AgentLoop logic is included.
- [ ] Security check: No silent fallback, no string-prefix authorization, no read-to-write permission escalation, and no ignored invalid allowed write set entries.
- [ ] Verification check: `pytest -v` passes with real execution output.
