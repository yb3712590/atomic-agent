# Filesystem Tools Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement P0-004 `filesystem tools`（文件系统工具） so the runtime can list, read, search, write, and patch workspace files through the existing fail-closed（失败关闭） path permission boundary.

**Architecture:** Add a focused `filesystem_tools`（文件系统工具） module that depends on `WorkspacePathGuard`（工作区路径守卫） for every user-supplied path decision. The module returns structured `FileToolResult`（文件工具结果） values with real filesystem facts, before/after hashes, and diffs for mutations; it does not emit events, run commands, access the network, or implement AgentLoop（智能体循环） behavior.

**Tech Stack:** Python 3.11+, `pathlib`（路径处理）, `dataclasses`（轻量数据结构）, `hashlib`（哈希）, `difflib`（差异生成）, pytest（测试）.

**Status:** implemented

---

## Scope

This plan implements P0-004 only.

In scope:

- Create `src/atomic_agent/filesystem_tools.py`（文件系统工具模块）.
- Create `tests/test_filesystem_tools.py`（文件系统工具测试）.
- Implement `list_files`, `read_file`, `search_files`, `write_file`, `apply_patch`.
- Implement `execute_filesystem_action`（执行文件系统动作） dispatcher for filesystem actions.
- Use explicit `FilesystemToolConfig`（文件系统工具配置） instead of runtime hardcoded limits.
- Reuse `WorkspacePathGuard` as the only path authorization source.
- Return structured failures for expected errors.

Out of scope:

- No changes to `WorkspacePathGuard` permission semantics.
- No event recorder or JSONL output.
- No command policy or `run_command`.
- No network policy or `web_fetch`.
- No provider adapter.
- No AgentLoop retry logic.
- No complete unified diff parser.
- No commit unless the user explicitly requests it.

## File Structure

- Create: `src/atomic_agent/filesystem_tools.py`
  - Defines `FilesystemToolConfig`（文件系统工具配置）, `FileToolResult`（文件工具结果）, `FilesystemToolConfigError`（文件系统工具配置错误）, `FilesystemTools`（文件系统工具集合）, and `execute_filesystem_action`（执行文件系统动作）.
- Create: `tests/test_filesystem_tools.py`
  - Covers successful and failed filesystem tool behavior with real temporary files.
- Modify after implementation passes: `docs/04-implementation-backlog/backlog.md`
  - Marks P0-004 completed only after tests pass and user review accepts implementation.
- Modify after implementation passes: `docs/04-implementation-spec/INDEX.md`
  - Moves `P0-004-filesystem-tools-spec.md`（文件系统工具规格） from draft to implemented or archived status.
- Modify after implementation passes: `docs/04-implementation-plan/INDEX.md`
  - Moves this plan from current draft to completed / archived.

---

### Task 1: Add result/config boundary tests

**Files:**

- Create: `tests/test_filesystem_tools.py`
- Create: `src/atomic_agent/filesystem_tools.py`

- [ ] **Step 1: Write failing tests for config validation and result shape**

Write `tests/test_filesystem_tools.py`:

```python
import pytest

from atomic_agent.filesystem_tools import (
    FileToolResult,
    FilesystemToolConfig,
    FilesystemToolConfigError,
    FilesystemTools,
)
from atomic_agent.path_guard import WorkspacePathGuard


def tool_config():
    return FilesystemToolConfig(
        default_read_limit=12,
        max_read_limit=32,
        default_max_entries=10,
        max_entries_limit=20,
        default_max_matches=5,
        max_matches_limit=10,
    )


def make_tools(tmp_path, allowed_write_set=None):
    guard = WorkspacePathGuard(tmp_path, allowed_write_set or [])
    return FilesystemTools(guard, tool_config())


def test_file_tool_result_success_has_no_error_fields():
    result = FileToolResult(ok=True, tool="read_file", path="README.md", data={"content": "hello"})

    assert result.ok is True
    assert result.error_kind is None
    assert result.error_message is None


def test_file_tool_result_success_rejects_error_fields():
    with pytest.raises(ValueError):
        FileToolResult(
            ok=True,
            tool="read_file",
            path="README.md",
            data={},
            error_kind="not_found",
            error_message="File not found.",
        )


def test_file_tool_result_failure_requires_error_kind():
    with pytest.raises(ValueError):
        FileToolResult(ok=False, tool="read_file", path="missing.md", data={}, error_message="File not found.")


def test_file_tool_result_failure_requires_error_message():
    with pytest.raises(ValueError):
        FileToolResult(ok=False, tool="read_file", path="missing.md", data={}, error_kind="not_found")


def test_file_tool_result_failure_accepts_error_fields():
    result = FileToolResult(
        ok=False,
        tool="read_file",
        path="missing.md",
        data={},
        error_kind="not_found",
        error_message="File not found.",
    )

    assert result.ok is False
    assert result.error_kind == "not_found"
    assert result.error_message == "File not found."


@pytest.mark.parametrize(
    "kwargs",
    [
        {"default_read_limit": 0},
        {"max_read_limit": 0},
        {"default_read_limit": 33},
        {"default_max_entries": 0},
        {"max_entries_limit": 0},
        {"default_max_entries": 21},
        {"default_max_matches": 0},
        {"max_matches_limit": 0},
        {"default_max_matches": 11},
    ],
)
def test_filesystem_tools_rejects_invalid_config(tmp_path, kwargs):
    values = {
        "default_read_limit": 12,
        "max_read_limit": 32,
        "default_max_entries": 10,
        "max_entries_limit": 20,
        "default_max_matches": 5,
        "max_matches_limit": 10,
    }
    values.update(kwargs)
    guard = WorkspacePathGuard(tmp_path, allowed_write_set=[])

    with pytest.raises(FilesystemToolConfigError):
        FilesystemTools(guard, FilesystemToolConfig(**values))
```

- [ ] **Step 2: Run the new tests and confirm they fail because the module does not exist**

Run:

```bash
pytest tests/test_filesystem_tools.py::test_file_tool_result_success_has_no_error_fields tests/test_filesystem_tools.py::test_file_tool_result_failure_requires_error_fields tests/test_filesystem_tools.py::test_filesystem_tools_rejects_invalid_config -v
```

Expected:

```text
ModuleNotFoundError: No module named 'atomic_agent.filesystem_tools'
```

- [ ] **Step 3: Add the minimal module with config validation**

Write `src/atomic_agent/filesystem_tools.py`:

```python
from dataclasses import dataclass
from typing import Any

from atomic_agent.path_guard import WorkspacePathGuard


@dataclass(frozen=True)
class FilesystemToolConfig:
    default_read_limit: int
    max_read_limit: int
    default_max_entries: int
    max_entries_limit: int
    default_max_matches: int
    max_matches_limit: int


@dataclass(frozen=True)
class FileToolResult:
    ok: bool
    tool: str
    path: str | None
    data: dict[str, Any]
    error_kind: str | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        if self.ok and (self.error_kind is not None or self.error_message is not None):
            raise ValueError("successful FileToolResult must not include error fields")
        if not self.ok and (not self.error_kind or not self.error_message):
            raise ValueError("failed FileToolResult requires error_kind and error_message")


class FilesystemToolConfigError(ValueError):
    pass


class FilesystemTools:
    def __init__(self, guard: WorkspacePathGuard, config: FilesystemToolConfig):
        self.guard = guard
        self.config = config
        self._validate_config()

    def _validate_config(self) -> None:
        positive_fields = {
            "default_read_limit": self.config.default_read_limit,
            "max_read_limit": self.config.max_read_limit,
            "default_max_entries": self.config.default_max_entries,
            "max_entries_limit": self.config.max_entries_limit,
            "default_max_matches": self.config.default_max_matches,
            "max_matches_limit": self.config.max_matches_limit,
        }
        for name, value in positive_fields.items():
            if not isinstance(value, int) or value <= 0:
                raise FilesystemToolConfigError(f"{name} must be a positive integer")
        if self.config.default_read_limit > self.config.max_read_limit:
            raise FilesystemToolConfigError("default_read_limit must not exceed max_read_limit")
        if self.config.default_max_entries > self.config.max_entries_limit:
            raise FilesystemToolConfigError("default_max_entries must not exceed max_entries_limit")
        if self.config.default_max_matches > self.config.max_matches_limit:
            raise FilesystemToolConfigError("default_max_matches must not exceed max_matches_limit")
```

- [ ] **Step 4: Run the targeted tests and confirm they pass**

Run:

```bash
pytest tests/test_filesystem_tools.py::test_file_tool_result_success_has_no_error_fields tests/test_filesystem_tools.py::test_file_tool_result_failure_requires_error_fields tests/test_filesystem_tools.py::test_filesystem_tools_rejects_invalid_config -v
```

Expected:

```text
PASSED
```

---

### Task 2: Implement `list_files`

**Files:**

- Modify: `tests/test_filesystem_tools.py`
- Modify: `src/atomic_agent/filesystem_tools.py`

- [ ] **Step 1: Add failing `list_files` tests**

Append to `tests/test_filesystem_tools.py`:

```python

def test_list_files_lists_workspace_root_in_stable_order(tmp_path):
    (tmp_path / "b.txt").write_text("b", encoding="utf-8")
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    tools = make_tools(tmp_path)

    result = tools.list_files()

    assert result.ok is True
    assert result.tool == "list_files"
    assert result.path is None
    assert result.data == {
        "entries": [
            {"path": "a.txt", "kind": "file", "size": 1},
            {"path": "b.txt", "kind": "file", "size": 1},
            {"path": "docs", "kind": "directory", "size": None},
        ],
        "truncated": False,
    }


def test_list_files_lists_nested_directory_non_recursive(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "index.md").write_text("index", encoding="utf-8")
    (docs / "nested").mkdir()
    (docs / "nested" / "hidden.md").write_text("hidden", encoding="utf-8")
    tools = make_tools(tmp_path)

    result = tools.list_files(path="docs")

    assert result.ok is True
    assert result.path == "docs"
    assert result.data == {
        "entries": [
            {"path": "docs/index.md", "kind": "file", "size": 5},
            {"path": "docs/nested", "kind": "directory", "size": None},
        ],
        "truncated": False,
    }


def test_list_files_supports_recursive_listing(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "index.md").write_text("index", encoding="utf-8")
    (docs / "nested").mkdir()
    (docs / "nested" / "child.md").write_text("child", encoding="utf-8")
    tools = make_tools(tmp_path)

    result = tools.list_files(path="docs", recursive=True)

    assert result.ok is True
    assert result.data["entries"] == [
        {"path": "docs/index.md", "kind": "file", "size": 5},
        {"path": "docs/nested", "kind": "directory", "size": None},
        {"path": "docs/nested/child.md", "kind": "file", "size": 5},
    ]


def test_list_files_truncates_when_max_entries_is_reached(tmp_path):
    for name in ["a.txt", "b.txt", "c.txt"]:
        (tmp_path / name).write_text(name, encoding="utf-8")
    tools = make_tools(tmp_path)

    result = tools.list_files(max_entries=2)

    assert result.ok is True
    assert [entry["path"] for entry in result.data["entries"]] == ["a.txt", "b.txt"]
    assert result.data["truncated"] is True


def test_list_files_rejects_file_path(tmp_path):
    (tmp_path / "README.md").write_text("readme", encoding="utf-8")
    tools = make_tools(tmp_path)

    result = tools.list_files(path="README.md")

    assert result.ok is False
    assert result.error_kind == "not_directory"
    assert result.data == {}


def test_list_files_rejects_path_escape(tmp_path):
    tools = make_tools(tmp_path)

    result = tools.list_files(path="../outside")

    assert result.ok is False
    assert result.error_kind == "permission_denied"
    assert result.error_message == "path_escape_denied"
```

- [ ] **Step 2: Run `list_files` tests and confirm method is missing**

Run:

```bash
pytest tests/test_filesystem_tools.py::test_list_files_lists_workspace_root_in_stable_order tests/test_filesystem_tools.py::test_list_files_lists_nested_directory_non_recursive tests/test_filesystem_tools.py::test_list_files_supports_recursive_listing tests/test_filesystem_tools.py::test_list_files_truncates_when_max_entries_is_reached tests/test_filesystem_tools.py::test_list_files_rejects_file_path tests/test_filesystem_tools.py::test_list_files_rejects_path_escape -v
```

Expected:

```text
AttributeError: 'FilesystemTools' object has no attribute 'list_files'
```

- [ ] **Step 3: Implement `list_files` and shared helpers**

Replace `src/atomic_agent/filesystem_tools.py` with:

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from atomic_agent.path_guard import PathDecisionType, WorkspacePathGuard


@dataclass(frozen=True)
class FilesystemToolConfig:
    default_read_limit: int
    max_read_limit: int
    default_max_entries: int
    max_entries_limit: int
    default_max_matches: int
    max_matches_limit: int


@dataclass(frozen=True)
class FileToolResult:
    ok: bool
    tool: str
    path: str | None
    data: dict[str, Any]
    error_kind: str | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        if self.ok and (self.error_kind is not None or self.error_message is not None):
            raise ValueError("successful FileToolResult must not include error fields")
        if not self.ok and (not self.error_kind or not self.error_message):
            raise ValueError("failed FileToolResult requires error_kind and error_message")


class FilesystemToolConfigError(ValueError):
    pass


class FilesystemTools:
    def __init__(self, guard: WorkspacePathGuard, config: FilesystemToolConfig):
        self.guard = guard
        self.config = config
        self._validate_config()

    def list_files(
        self,
        path: str | None = None,
        recursive: bool = False,
        max_entries: int | None = None,
    ) -> FileToolResult:
        if not isinstance(recursive, bool):
            return self._failure("list_files", path, "invalid_input", "recursive must be a boolean")
        limit = self._resolve_limit(
            max_entries,
            self.config.default_max_entries,
            self.config.max_entries_limit,
            "max_entries",
            tool="list_files",
            path=path,
        )
        if isinstance(limit, FileToolResult):
            return limit

        target = self._resolve_read_target("list_files", path)
        if isinstance(target, FileToolResult):
            return target
        if not target.exists():
            return self._failure("list_files", path, "not_found", "Path not found.")
        if not target.is_dir():
            return self._failure("list_files", path, "not_directory", "Path is not a directory.")

        entries = []
        truncated = False
        try:
            for entry in self._iter_entries(target, recursive):
                if len(entries) >= limit:
                    truncated = True
                    break
                entries.append(self._entry_data(entry))
        except OSError as error:
            return self._failure("list_files", path, "io_error", str(error))

        return FileToolResult(
            ok=True,
            tool="list_files",
            path=path,
            data={"entries": entries, "truncated": truncated},
        )

    def _validate_config(self) -> None:
        positive_fields = {
            "default_read_limit": self.config.default_read_limit,
            "max_read_limit": self.config.max_read_limit,
            "default_max_entries": self.config.default_max_entries,
            "max_entries_limit": self.config.max_entries_limit,
            "default_max_matches": self.config.default_max_matches,
            "max_matches_limit": self.config.max_matches_limit,
        }
        for name, value in positive_fields.items():
            if not isinstance(value, int) or value <= 0:
                raise FilesystemToolConfigError(f"{name} must be a positive integer")
        if self.config.default_read_limit > self.config.max_read_limit:
            raise FilesystemToolConfigError("default_read_limit must not exceed max_read_limit")
        if self.config.default_max_entries > self.config.max_entries_limit:
            raise FilesystemToolConfigError("default_max_entries must not exceed max_entries_limit")
        if self.config.default_max_matches > self.config.max_matches_limit:
            raise FilesystemToolConfigError("default_max_matches must not exceed max_matches_limit")

    def _resolve_limit(
        self,
        requested: int | None,
        default: int,
        maximum: int,
        name: str,
        tool: str = "filesystem",
        path: str | None = None,
    ) -> int | FileToolResult:
        if requested is None:
            return default
        if not isinstance(requested, int) or requested <= 0:
            return self._failure(tool, path, "invalid_input", f"{name} must be a positive integer")
        if requested > maximum:
            return self._failure(tool, path, "invalid_input", f"{name} exceeds configured maximum")
        return requested

    def _resolve_read_target(self, tool: str, path: str | None) -> Path | FileToolResult:
        if path is None:
            return self.guard.workspace_root
        if not isinstance(path, str):
            return self._failure(tool, str(path), "invalid_input", "path must be a string")
        decision = self.guard.resolve_read_path(path)
        if decision.decision == PathDecisionType.DENY:
            return self._failure(tool, path, "permission_denied", decision.reason)
        return Path(decision.normalized_path)

    def _iter_entries(self, root: Path, recursive: bool) -> Iterator[Path]:
        children = sorted(root.iterdir(), key=self._relative_sort_key)
        for child in children:
            yield child
            if recursive and child.is_dir() and not child.is_symlink():
                yield from self._iter_entries(child, recursive=True)

    def _entry_data(self, path: Path) -> dict[str, Any]:
        if path.is_symlink():
            kind = "symlink"
            size = path.lstat().st_size
        elif path.is_dir():
            kind = "directory"
            size = None
        elif path.is_file():
            kind = "file"
            size = path.stat().st_size
        else:
            kind = "other"
            size = None
        return {"path": self._relative_path(path), "kind": kind, "size": size}

    def _relative_sort_key(self, path: Path) -> str:
        return self._relative_path(path)

    def _relative_path(self, path: Path) -> str:
        return path.relative_to(self.guard.workspace_root).as_posix()

    def _failure(
        self,
        tool: str,
        path: str | None,
        error_kind: str,
        error_message: str,
    ) -> FileToolResult:
        return FileToolResult(False, tool, path, {}, error_kind, error_message)
```

- [ ] **Step 4: Run `list_files` tests and confirm they pass**

Run:

```bash
pytest tests/test_filesystem_tools.py::test_list_files_lists_workspace_root_in_stable_order tests/test_filesystem_tools.py::test_list_files_lists_nested_directory_non_recursive tests/test_filesystem_tools.py::test_list_files_supports_recursive_listing tests/test_filesystem_tools.py::test_list_files_truncates_when_max_entries_is_reached tests/test_filesystem_tools.py::test_list_files_rejects_file_path tests/test_filesystem_tools.py::test_list_files_rejects_path_escape -v
```

Expected:

```text
PASSED
```

---

### Task 3: Implement `read_file`

**Files:**

- Modify: `tests/test_filesystem_tools.py`
- Modify: `src/atomic_agent/filesystem_tools.py`

- [ ] **Step 1: Add failing `read_file` tests**

Append to `tests/test_filesystem_tools.py`:

```python

def test_read_file_reads_utf8_content_with_default_limit(tmp_path):
    (tmp_path / "README.md").write_text("hello world", encoding="utf-8")
    tools = make_tools(tmp_path)

    result = tools.read_file("README.md")

    assert result.ok is True
    assert result.tool == "read_file"
    assert result.path == "README.md"
    assert result.data == {"content": "hello world", "offset": 0, "bytes_read": 11, "truncated": False}


def test_read_file_supports_offset_and_limit(tmp_path):
    (tmp_path / "README.md").write_text("hello world", encoding="utf-8")
    tools = make_tools(tmp_path)

    result = tools.read_file("README.md", offset=6, limit=3)

    assert result.ok is True
    assert result.data == {"content": "wor", "offset": 6, "bytes_read": 3, "truncated": True}


def test_read_file_rejects_invalid_offset(tmp_path):
    (tmp_path / "README.md").write_text("hello", encoding="utf-8")
    tools = make_tools(tmp_path)

    result = tools.read_file("README.md", offset=-1)

    assert result.ok is False
    assert result.error_kind == "invalid_input"


def test_read_file_rejects_limit_above_config(tmp_path):
    (tmp_path / "README.md").write_text("hello", encoding="utf-8")
    tools = make_tools(tmp_path)

    result = tools.read_file("README.md", limit=33)

    assert result.ok is False
    assert result.error_kind == "invalid_input"


def test_read_file_rejects_missing_file(tmp_path):
    tools = make_tools(tmp_path)

    result = tools.read_file("missing.md")

    assert result.ok is False
    assert result.error_kind == "not_found"


def test_read_file_rejects_directory(tmp_path):
    (tmp_path / "docs").mkdir()
    tools = make_tools(tmp_path)

    result = tools.read_file("docs")

    assert result.ok is False
    assert result.error_kind == "not_file"


def test_read_file_rejects_path_escape(tmp_path):
    tools = make_tools(tmp_path)

    result = tools.read_file("../secret.txt")

    assert result.ok is False
    assert result.error_kind == "permission_denied"
    assert result.error_message == "path_escape_denied"


def test_read_file_rejects_non_utf8_content(tmp_path):
    (tmp_path / "binary.dat").write_bytes(b"\xff\xfe")
    tools = make_tools(tmp_path)

    result = tools.read_file("binary.dat")

    assert result.ok is False
    assert result.error_kind == "decode_failed"
```

- [ ] **Step 2: Run `read_file` tests and confirm method is missing**

Run:

```bash
pytest tests/test_filesystem_tools.py::test_read_file_reads_utf8_content_with_default_limit tests/test_filesystem_tools.py::test_read_file_supports_offset_and_limit tests/test_filesystem_tools.py::test_read_file_rejects_invalid_offset tests/test_filesystem_tools.py::test_read_file_rejects_limit_above_config tests/test_filesystem_tools.py::test_read_file_rejects_missing_file tests/test_filesystem_tools.py::test_read_file_rejects_directory tests/test_filesystem_tools.py::test_read_file_rejects_path_escape tests/test_filesystem_tools.py::test_read_file_rejects_non_utf8_content -v
```

Expected:

```text
AttributeError: 'FilesystemTools' object has no attribute 'read_file'
```

- [ ] **Step 3: Add `read_file` imports and method**

In `src/atomic_agent/filesystem_tools.py`, add this method inside `FilesystemTools` after `list_files`:

```python
    def read_file(self, path: str, offset: int = 0, limit: int | None = None) -> FileToolResult:
        if not isinstance(path, str):
            return self._failure("read_file", str(path), "invalid_input", "path must be a string")
        if not isinstance(offset, int) or offset < 0:
            return self._failure("read_file", path, "invalid_input", "offset must be a non-negative integer")
        resolved_limit = self._resolve_limit(
            limit,
            self.config.default_read_limit,
            self.config.max_read_limit,
            "limit",
            tool="read_file",
            path=path,
        )
        if isinstance(resolved_limit, FileToolResult):
            return resolved_limit

        target = self._resolve_read_target("read_file", path)
        if isinstance(target, FileToolResult):
            return target
        if not target.exists():
            return self._failure("read_file", path, "not_found", "File not found.")
        if not target.is_file():
            return self._failure("read_file", path, "not_file", "Path is not a file.")

        try:
            with target.open("rb") as file:
                file.seek(offset)
                raw = file.read(resolved_limit + 1)
        except OSError as error:
            return self._failure("read_file", path, "io_error", str(error))

        chunk = raw[:resolved_limit]
        try:
            content = chunk.decode("utf-8")
        except UnicodeDecodeError:
            return self._failure("read_file", path, "decode_failed", "File is not valid UTF-8 text.")

        return FileToolResult(
            ok=True,
            tool="read_file",
            path=path,
            data={
                "content": content,
                "offset": offset,
                "bytes_read": len(chunk),
                "truncated": len(raw) > resolved_limit,
            },
        )
```

Then change `_resolve_limit` to accept tool and path:

```python
    def _resolve_limit(
        self,
        requested: int | None,
        default: int,
        maximum: int,
        name: str,
        tool: str = "filesystem",
        path: str | None = None,
    ) -> int | FileToolResult:
        if requested is None:
            return default
        if not isinstance(requested, int) or requested <= 0:
            return self._failure(tool, path, "invalid_input", f"{name} must be a positive integer")
        if requested > maximum:
            return self._failure(tool, path, "invalid_input", f"{name} exceeds configured maximum")
        return requested
```

- [ ] **Step 4: Run `read_file` tests and confirm they pass**

Run:

```bash
pytest tests/test_filesystem_tools.py::test_read_file_reads_utf8_content_with_default_limit tests/test_filesystem_tools.py::test_read_file_supports_offset_and_limit tests/test_filesystem_tools.py::test_read_file_rejects_invalid_offset tests/test_filesystem_tools.py::test_read_file_rejects_limit_above_config tests/test_filesystem_tools.py::test_read_file_rejects_missing_file tests/test_filesystem_tools.py::test_read_file_rejects_directory tests/test_filesystem_tools.py::test_read_file_rejects_path_escape tests/test_filesystem_tools.py::test_read_file_rejects_non_utf8_content -v
```

Expected:

```text
PASSED
```

---

### Task 4: Implement `search_files`

**Files:**

- Modify: `tests/test_filesystem_tools.py`
- Modify: `src/atomic_agent/filesystem_tools.py`

- [ ] **Step 1: Add failing `search_files` tests**

Append to `tests/test_filesystem_tools.py`:

```python

def test_search_files_finds_name_matches(tmp_path):
    (tmp_path / "README.md").write_text("readme", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "models.py").write_text("class AgentAction: pass", encoding="utf-8")
    tools = make_tools(tmp_path)

    result = tools.search_files("models", mode="name")

    assert result.ok is True
    assert result.data == {
        "matches": [{"path": "src/models.py", "line": None, "preview": "src/models.py"}],
        "truncated": False,
        "skipped": [],
    }


def test_search_files_finds_content_matches_with_line_numbers(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "models.py").write_text("one\nclass AgentAction:\n    pass\n", encoding="utf-8")
    tools = make_tools(tmp_path)

    result = tools.search_files("AgentAction", path="src", mode="content")

    assert result.ok is True
    assert result.data == {
        "matches": [{"path": "src/models.py", "line": 2, "preview": "class AgentAction:"}],
        "truncated": False,
        "skipped": [],
    }


def test_search_files_rejects_empty_query(tmp_path):
    tools = make_tools(tmp_path)

    result = tools.search_files("   ")

    assert result.ok is False
    assert result.error_kind == "invalid_input"


def test_search_files_rejects_unknown_mode(tmp_path):
    tools = make_tools(tmp_path)

    result = tools.search_files("AgentAction", mode="regex")

    assert result.ok is False
    assert result.error_kind == "invalid_input"


def test_search_files_rejects_non_directory_root(tmp_path):
    (tmp_path / "README.md").write_text("AgentAction", encoding="utf-8")
    tools = make_tools(tmp_path)

    result = tools.search_files("AgentAction", path="README.md")

    assert result.ok is False
    assert result.error_kind == "not_directory"


def test_search_files_truncates_content_matches(tmp_path):
    for name in ["a.txt", "b.txt", "c.txt"]:
        (tmp_path / name).write_text("needle\n", encoding="utf-8")
    tools = make_tools(tmp_path)

    result = tools.search_files("needle", max_matches=2)

    assert result.ok is True
    assert [match["path"] for match in result.data["matches"]] == ["a.txt", "b.txt"]
    assert result.data["truncated"] is True


def test_search_files_truncates_multiple_matches_in_one_file(tmp_path):
    (tmp_path / "a.txt").write_text("needle 1\nneedle 2\nneedle 3\n", encoding="utf-8")
    tools = make_tools(tmp_path)

    result = tools.search_files("needle", max_matches=2)

    assert result.ok is True
    assert [match["preview"] for match in result.data["matches"]] == ["needle 1", "needle 2"]
    assert result.data["truncated"] is True


def test_search_files_records_decode_failures_as_skipped(tmp_path):
    (tmp_path / "good.txt").write_text("needle\n", encoding="utf-8")
    (tmp_path / "bad.bin").write_bytes(b"\xff\xfe")
    tools = make_tools(tmp_path)

    result = tools.search_files("needle")

    assert result.ok is True
    assert result.data["matches"] == [{"path": "good.txt", "line": 1, "preview": "needle"}]
    assert result.data["skipped"] == [{"path": "bad.bin", "reason": "decode_failed"}]
```

- [ ] **Step 2: Run `search_files` tests and confirm method is missing**

Run:

```bash
pytest tests/test_filesystem_tools.py::test_search_files_finds_name_matches tests/test_filesystem_tools.py::test_search_files_finds_content_matches_with_line_numbers tests/test_filesystem_tools.py::test_search_files_rejects_empty_query tests/test_filesystem_tools.py::test_search_files_rejects_unknown_mode tests/test_filesystem_tools.py::test_search_files_rejects_non_directory_root tests/test_filesystem_tools.py::test_search_files_truncates_content_matches tests/test_filesystem_tools.py::test_search_files_records_decode_failures_as_skipped -v
```

Expected:

```text
AttributeError: 'FilesystemTools' object has no attribute 'search_files'
```

- [ ] **Step 3: Add `search_files` method and helpers**

In `src/atomic_agent/filesystem_tools.py`, add this method inside `FilesystemTools` after `read_file`:

```python
    def search_files(
        self,
        query: str,
        path: str | None = None,
        mode: str = "content",
        max_matches: int | None = None,
    ) -> FileToolResult:
        if not isinstance(query, str) or not query.strip():
            return self._failure("search_files", path, "invalid_input", "query must be a non-empty string")
        if mode not in {"name", "content"}:
            return self._failure("search_files", path, "invalid_input", "mode must be 'name' or 'content'")
        limit = self._resolve_limit(
            max_matches,
            self.config.default_max_matches,
            self.config.max_matches_limit,
            "max_matches",
            tool="search_files",
            path=path,
        )
        if isinstance(limit, FileToolResult):
            return limit

        root = self._resolve_read_target("search_files", path)
        if isinstance(root, FileToolResult):
            return root
        if not root.exists():
            return self._failure("search_files", path, "not_found", "Path not found.")
        if not root.is_dir():
            return self._failure("search_files", path, "not_directory", "Path is not a directory.")

        matches: list[dict[str, Any]] = []
        skipped: list[dict[str, str]] = []
        truncated = False
        try:
            for entry in self._iter_entries(root, recursive=True):
                if len(matches) >= limit:
                    truncated = True
                    break
                relative = self._relative_path(entry)
                decision = self.guard.resolve_read_path(relative)
                if decision.decision == PathDecisionType.DENY:
                    skipped.append({"path": relative, "reason": decision.reason})
                    continue
                if mode == "name":
                    if query in relative:
                        matches.append({"path": relative, "line": None, "preview": relative})
                    continue
                if not entry.is_file():
                    continue
                if self._search_file_content(entry, query, limit, matches, skipped):
                    truncated = True
                    break
        except OSError as error:
            return self._failure("search_files", path, "io_error", str(error))

        if len(matches) > limit:
            del matches[limit:]
            truncated = True

        return FileToolResult(
            ok=True,
            tool="search_files",
            path=path,
            data={"matches": matches, "truncated": truncated, "skipped": skipped},
        )

    def _search_file_content(
        self,
        entry: Path,
        query: str,
        limit: int,
        matches: list[dict[str, Any]],
        skipped: list[dict[str, str]],
    ) -> bool:
        relative = self._relative_path(entry)
        try:
            text = entry.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            skipped.append({"path": relative, "reason": "decode_failed"})
            return False
        except OSError:
            skipped.append({"path": relative, "reason": "io_error"})
            return False
        for line_number, line in enumerate(text.splitlines(), start=1):
            if query not in line:
                continue
            if len(matches) >= limit:
                return True
            matches.append({"path": relative, "line": line_number, "preview": line.strip()})
        return False
```

- [ ] **Step 4: Run `search_files` tests and confirm they pass**

Run:

```bash
pytest tests/test_filesystem_tools.py::test_search_files_finds_name_matches tests/test_filesystem_tools.py::test_search_files_finds_content_matches_with_line_numbers tests/test_filesystem_tools.py::test_search_files_rejects_empty_query tests/test_filesystem_tools.py::test_search_files_rejects_unknown_mode tests/test_filesystem_tools.py::test_search_files_rejects_non_directory_root tests/test_filesystem_tools.py::test_search_files_truncates_content_matches tests/test_filesystem_tools.py::test_search_files_records_decode_failures_as_skipped -v
```

Expected:

```text
PASSED
```

---

### Task 5: Implement `write_file`

**Files:**

- Modify: `tests/test_filesystem_tools.py`
- Modify: `src/atomic_agent/filesystem_tools.py`

- [ ] **Step 1: Add failing `write_file` tests**

Append to `tests/test_filesystem_tools.py`:

```python

def test_write_file_writes_allowed_exact_path(tmp_path):
    tools = make_tools(tmp_path, allowed_write_set=["docs/output.md"])

    result = tools.write_file("docs/output.md", "hello\n")

    assert result.ok is True
    assert (tmp_path / "docs" / "output.md").read_text(encoding="utf-8") == "hello\n"
    assert result.data["bytes_written"] == 6
    assert result.data["created"] is True
    assert result.data["before_hash"] is None
    assert result.data["after_hash"].startswith("sha256:")
    assert "hello" in result.data["diff"]


def test_write_file_writes_allowed_directory_child(tmp_path):
    tools = make_tools(tmp_path, allowed_write_set=["docs/generated/"])

    result = tools.write_file("docs/generated/output.md", "generated\n")

    assert result.ok is True
    assert (tmp_path / "docs" / "generated" / "output.md").read_text(encoding="utf-8") == "generated\n"
    assert result.data["created"] is True


def test_write_file_rejects_unallowed_path(tmp_path):
    tools = make_tools(tmp_path, allowed_write_set=["docs/output.md"])

    result = tools.write_file("src/models.py", "content")

    assert result.ok is False
    assert result.error_kind == "permission_denied"
    assert not (tmp_path / "src" / "models.py").exists()


def test_write_file_rejects_non_string_content(tmp_path):
    tools = make_tools(tmp_path, allowed_write_set=["docs/output.md"])

    result = tools.write_file("docs/output.md", 123)

    assert result.ok is False
    assert result.error_kind == "invalid_input"


def test_write_file_rejects_directory_target(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    tools = make_tools(tmp_path, allowed_write_set=["docs"])

    result = tools.write_file("docs", "content")

    assert result.ok is False
    assert result.error_kind == "not_file"
```

- [ ] **Step 2: Run `write_file` tests and confirm method is missing**

Run:

```bash
pytest tests/test_filesystem_tools.py::test_write_file_writes_allowed_exact_path tests/test_filesystem_tools.py::test_write_file_writes_allowed_directory_child tests/test_filesystem_tools.py::test_write_file_rejects_unallowed_path tests/test_filesystem_tools.py::test_write_file_rejects_non_string_content tests/test_filesystem_tools.py::test_write_file_rejects_directory_target -v
```

Expected:

```text
AttributeError: 'FilesystemTools' object has no attribute 'write_file'
```

- [ ] **Step 3: Add imports, `write_file`, and mutation helpers**

At the top of `src/atomic_agent/filesystem_tools.py`, add:

```python
import difflib
import hashlib
```

Inside `FilesystemTools`, add this method after `search_files`:

```python
    def write_file(self, path: str, content: str) -> FileToolResult:
        if not isinstance(path, str):
            return self._failure("write_file", str(path), "invalid_input", "path must be a string")
        if not isinstance(content, str):
            return self._failure("write_file", path, "invalid_input", "content must be a string")

        target = self._resolve_write_target("write_file", path)
        if isinstance(target, FileToolResult):
            return target
        if target.exists() and not target.is_file():
            return self._failure("write_file", path, "not_file", "Path is not a file.")

        try:
            created = not target.exists()
            before_text = target.read_text(encoding="utf-8") if target.exists() else ""
            before_hash = self._hash_file(target) if target.exists() else None
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            after_hash = self._hash_file(target)
        except UnicodeDecodeError:
            return self._failure("write_file", path, "decode_failed", "Existing file is not valid UTF-8 text.")
        except OSError as error:
            return self._failure("write_file", path, "io_error", str(error))

        return FileToolResult(
            ok=True,
            tool="write_file",
            path=path,
            data={
                "bytes_written": len(content.encode("utf-8")),
                "created": created,
                "before_hash": before_hash,
                "after_hash": after_hash,
                "diff": self._diff(path, before_text, content),
            },
        )
```

Add these helpers near the other helpers:

```python
    def _resolve_write_target(self, tool: str, path: str) -> Path | FileToolResult:
        decision = self.guard.resolve_write_path(path)
        if decision.decision == PathDecisionType.DENY:
            return self._failure(tool, path, "permission_denied", decision.reason)
        return Path(decision.normalized_path)

    def _hash_file(self, path: Path) -> str:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        return f"sha256:{digest}"

    def _diff(self, path: str, before: str, after: str) -> str:
        return "".join(
            difflib.unified_diff(
                before.splitlines(keepends=True),
                after.splitlines(keepends=True),
                fromfile=f"a/{path}",
                tofile=f"b/{path}",
            )
        )
```

- [ ] **Step 4: Run `write_file` tests and confirm they pass**

Run:

```bash
pytest tests/test_filesystem_tools.py::test_write_file_writes_allowed_exact_path tests/test_filesystem_tools.py::test_write_file_writes_allowed_directory_child tests/test_filesystem_tools.py::test_write_file_rejects_unallowed_path tests/test_filesystem_tools.py::test_write_file_rejects_non_string_content tests/test_filesystem_tools.py::test_write_file_rejects_directory_target -v
```

Expected:

```text
PASSED
```

---

### Task 6: Implement `apply_patch`

**Files:**

- Modify: `tests/test_filesystem_tools.py`
- Modify: `src/atomic_agent/filesystem_tools.py`

- [ ] **Step 1: Add failing `apply_patch` tests**

Append to `tests/test_filesystem_tools.py`:

```python

def test_apply_patch_replaces_single_match(tmp_path):
    target = tmp_path / "docs" / "output.md"
    target.parent.mkdir()
    target.write_text("hello old\n", encoding="utf-8")
    tools = make_tools(tmp_path, allowed_write_set=["docs/output.md"])

    result = tools.apply_patch("docs/output.md", "old", "new")

    assert result.ok is True
    assert target.read_text(encoding="utf-8") == "hello new\n"
    assert result.data["replacements"] == 1
    assert result.data["before_hash"].startswith("sha256:")
    assert result.data["after_hash"].startswith("sha256:")
    assert "hello new" in result.data["diff"]


def test_apply_patch_rejects_missing_match_and_leaves_file_unchanged(tmp_path):
    target = tmp_path / "docs" / "output.md"
    target.parent.mkdir()
    target.write_text("hello old\n", encoding="utf-8")
    tools = make_tools(tmp_path, allowed_write_set=["docs/output.md"])

    result = tools.apply_patch("docs/output.md", "missing", "new")

    assert result.ok is False
    assert result.error_kind == "patch_not_applied"
    assert target.read_text(encoding="utf-8") == "hello old\n"


def test_apply_patch_rejects_ambiguous_match_and_leaves_file_unchanged(tmp_path):
    target = tmp_path / "docs" / "output.md"
    target.parent.mkdir()
    target.write_text("old old\n", encoding="utf-8")
    tools = make_tools(tmp_path, allowed_write_set=["docs/output.md"])

    result = tools.apply_patch("docs/output.md", "old", "new")

    assert result.ok is False
    assert result.error_kind == "ambiguous_patch"
    assert target.read_text(encoding="utf-8") == "old old\n"


def test_apply_patch_replace_all_replaces_all_matches(tmp_path):
    target = tmp_path / "docs" / "output.md"
    target.parent.mkdir()
    target.write_text("old old\n", encoding="utf-8")
    tools = make_tools(tmp_path, allowed_write_set=["docs/output.md"])

    result = tools.apply_patch("docs/output.md", "old", "new", replace_all=True)

    assert result.ok is True
    assert result.data["replacements"] == 2
    assert target.read_text(encoding="utf-8") == "new new\n"


def test_apply_patch_rejects_missing_file(tmp_path):
    tools = make_tools(tmp_path, allowed_write_set=["docs/output.md"])

    result = tools.apply_patch("docs/output.md", "old", "new")

    assert result.ok is False
    assert result.error_kind == "not_found"


def test_apply_patch_rejects_unallowed_path(tmp_path):
    target = tmp_path / "src" / "models.py"
    target.parent.mkdir()
    target.write_text("old\n", encoding="utf-8")
    tools = make_tools(tmp_path, allowed_write_set=["docs/output.md"])

    result = tools.apply_patch("src/models.py", "old", "new")

    assert result.ok is False
    assert result.error_kind == "permission_denied"
    assert target.read_text(encoding="utf-8") == "old\n"


def test_apply_patch_rejects_empty_old_text(tmp_path):
    target = tmp_path / "docs" / "output.md"
    target.parent.mkdir()
    target.write_text("content\n", encoding="utf-8")
    tools = make_tools(tmp_path, allowed_write_set=["docs/output.md"])

    result = tools.apply_patch("docs/output.md", "", "new")

    assert result.ok is False
    assert result.error_kind == "invalid_input"
```

- [ ] **Step 2: Run `apply_patch` tests and confirm method is missing**

Run:

```bash
pytest tests/test_filesystem_tools.py::test_apply_patch_replaces_single_match tests/test_filesystem_tools.py::test_apply_patch_rejects_missing_match_and_leaves_file_unchanged tests/test_filesystem_tools.py::test_apply_patch_rejects_ambiguous_match_and_leaves_file_unchanged tests/test_filesystem_tools.py::test_apply_patch_replace_all_replaces_all_matches tests/test_filesystem_tools.py::test_apply_patch_rejects_missing_file tests/test_filesystem_tools.py::test_apply_patch_rejects_unallowed_path tests/test_filesystem_tools.py::test_apply_patch_rejects_empty_old_text -v
```

Expected:

```text
AttributeError: 'FilesystemTools' object has no attribute 'apply_patch'
```

- [ ] **Step 3: Add `apply_patch` method**

In `src/atomic_agent/filesystem_tools.py`, add this method inside `FilesystemTools` after `write_file`:

```python
    def apply_patch(
        self,
        path: str,
        old_text: str,
        new_text: str,
        replace_all: bool = False,
    ) -> FileToolResult:
        if not isinstance(path, str):
            return self._failure("apply_patch", str(path), "invalid_input", "path must be a string")
        if not isinstance(old_text, str) or old_text == "":
            return self._failure("apply_patch", path, "invalid_input", "old_text must be a non-empty string")
        if not isinstance(new_text, str):
            return self._failure("apply_patch", path, "invalid_input", "new_text must be a string")
        if not isinstance(replace_all, bool):
            return self._failure("apply_patch", path, "invalid_input", "replace_all must be a boolean")

        target = self._resolve_write_target("apply_patch", path)
        if isinstance(target, FileToolResult):
            return target
        if not target.exists():
            return self._failure("apply_patch", path, "not_found", "File not found.")
        if not target.is_file():
            return self._failure("apply_patch", path, "not_file", "Path is not a file.")

        try:
            before_text = target.read_text(encoding="utf-8")
            before_hash = self._hash_file(target)
        except UnicodeDecodeError:
            return self._failure("apply_patch", path, "decode_failed", "File is not valid UTF-8 text.")
        except OSError as error:
            return self._failure("apply_patch", path, "io_error", str(error))

        match_count = before_text.count(old_text)
        if match_count == 0:
            return self._failure("apply_patch", path, "patch_not_applied", "old_text was not found.")
        if match_count > 1 and not replace_all:
            return self._failure("apply_patch", path, "ambiguous_patch", "old_text matched more than once.")

        after_text = before_text.replace(old_text, new_text) if replace_all else before_text.replace(old_text, new_text, 1)
        try:
            target.write_text(after_text, encoding="utf-8")
            after_hash = self._hash_file(target)
        except OSError as error:
            return self._failure("apply_patch", path, "io_error", str(error))

        return FileToolResult(
            ok=True,
            tool="apply_patch",
            path=path,
            data={
                "replacements": match_count if replace_all else 1,
                "before_hash": before_hash,
                "after_hash": after_hash,
                "diff": self._diff(path, before_text, after_text),
            },
        )
```

- [ ] **Step 4: Run `apply_patch` tests and confirm they pass**

Run:

```bash
pytest tests/test_filesystem_tools.py::test_apply_patch_replaces_single_match tests/test_filesystem_tools.py::test_apply_patch_rejects_missing_match_and_leaves_file_unchanged tests/test_filesystem_tools.py::test_apply_patch_rejects_ambiguous_match_and_leaves_file_unchanged tests/test_filesystem_tools.py::test_apply_patch_replace_all_replaces_all_matches tests/test_filesystem_tools.py::test_apply_patch_rejects_missing_file tests/test_filesystem_tools.py::test_apply_patch_rejects_unallowed_path tests/test_filesystem_tools.py::test_apply_patch_rejects_empty_old_text -v
```

Expected:

```text
PASSED
```

---

### Task 7: Add filesystem action dispatcher

**Files:**

- Modify: `tests/test_filesystem_tools.py`
- Modify: `src/atomic_agent/filesystem_tools.py`

- [ ] **Step 1: Add failing dispatcher tests**

Append imports at the top of `tests/test_filesystem_tools.py`:

```python
from atomic_agent.filesystem_tools import execute_filesystem_action
from atomic_agent.models import AgentAction
```

Append tests:

```python

def test_execute_filesystem_action_dispatches_read_file(tmp_path):
    (tmp_path / "README.md").write_text("hello", encoding="utf-8")
    tools = make_tools(tmp_path)
    action = AgentAction(
        action_id="step-0001",
        action="read_file",
        reason_summary="Read README.",
        input={"path": "README.md"},
    )

    result = execute_filesystem_action(action, tools)

    assert result.ok is True
    assert result.tool == "read_file"
    assert result.data["content"] == "hello"


@pytest.mark.parametrize(
    "action_name,input_payload,expected_tool",
    [
        ("list_files", {}, "list_files"),
        ("search_files", {"query": "README", "mode": "name"}, "search_files"),
        ("write_file", {"path": "docs/output.md", "content": "hello"}, "write_file"),
        ("apply_patch", {"path": "docs/output.md", "old_text": "hello", "new_text": "hi"}, "apply_patch"),
    ],
)
def test_execute_filesystem_action_dispatches_all_filesystem_actions(tmp_path, action_name, input_payload, expected_tool):
    if action_name == "apply_patch":
        target = tmp_path / "docs" / "output.md"
        target.parent.mkdir()
        target.write_text("hello", encoding="utf-8")
    tools = make_tools(tmp_path, allowed_write_set=["docs/output.md"])
    action = AgentAction(
        action_id=f"step-{action_name}",
        action=action_name,
        reason_summary="Dispatch filesystem action.",
        input=input_payload,
    )

    result = execute_filesystem_action(action, tools)

    assert result.tool == expected_tool


def test_execute_filesystem_action_rejects_non_filesystem_action(tmp_path):
    tools = make_tools(tmp_path)
    action = AgentAction(
        action_id="step-0002",
        action="run_command",
        reason_summary="Run tests.",
        input={"command_id": "test"},
    )

    result = execute_filesystem_action(action, tools)

    assert result.ok is False
    assert result.tool == "run_command"
    assert result.error_kind == "unsupported_action"
```

- [ ] **Step 2: Run dispatcher tests and confirm function is missing**

Run:

```bash
pytest tests/test_filesystem_tools.py::test_execute_filesystem_action_dispatches_read_file tests/test_filesystem_tools.py::test_execute_filesystem_action_dispatches_all_filesystem_actions tests/test_filesystem_tools.py::test_execute_filesystem_action_rejects_non_filesystem_action -v
```

Expected:

```text
ImportError: cannot import name 'execute_filesystem_action'
```

- [ ] **Step 3: Add dispatcher function**

Add this import near the top of `src/atomic_agent/filesystem_tools.py`:

```python
from atomic_agent.models import AgentAction, AgentActionType
```

Add this function at module level after `FilesystemTools`:

```python
def execute_filesystem_action(action: AgentAction, tools: FilesystemTools) -> FileToolResult:
    try:
        if action.action == AgentActionType.LIST_FILES:
            return tools.list_files(**action.input)
        if action.action == AgentActionType.READ_FILE:
            return tools.read_file(**action.input)
        if action.action == AgentActionType.SEARCH_FILES:
            return tools.search_files(**action.input)
        if action.action == AgentActionType.WRITE_FILE:
            return tools.write_file(**action.input)
        if action.action == AgentActionType.APPLY_PATCH:
            return tools.apply_patch(**action.input)
    except TypeError as error:
        return FileToolResult(
            ok=False,
            tool=action.action.value,
            path=action.input.get("path") if isinstance(action.input, dict) else None,
            data={},
            error_kind="invalid_input",
            error_message=str(error),
        )

    return FileToolResult(
        ok=False,
        tool=action.action.value,
        path=action.input.get("path") if isinstance(action.input, dict) else None,
        data={},
        error_kind="unsupported_action",
        error_message="Action is not a filesystem action.",
    )
```

- [ ] **Step 4: Run dispatcher tests and confirm they pass**

Run:

```bash
pytest tests/test_filesystem_tools.py::test_execute_filesystem_action_dispatches_read_file tests/test_filesystem_tools.py::test_execute_filesystem_action_dispatches_all_filesystem_actions tests/test_filesystem_tools.py::test_execute_filesystem_action_rejects_non_filesystem_action -v
```

Expected:

```text
PASSED
```

---

### Task 8: Add symlink and full verification coverage

**Files:**

- Modify: `tests/test_filesystem_tools.py`
- Verify: `src/atomic_agent/filesystem_tools.py`
- Verify: existing tests

- [ ] **Step 1: Add symlink traversal regression tests**

Append to `tests/test_filesystem_tools.py`:

```python

def test_list_files_does_not_recurse_into_symlink_directory(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    (real / "visible.txt").write_text("visible", encoding="utf-8")
    link = tmp_path / "link"
    try:
        link.symlink_to(real, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"symlink creation is unavailable: {error}")
    tools = make_tools(tmp_path)

    result = tools.list_files(recursive=True)

    paths = [entry["path"] for entry in result.data["entries"]]
    assert "link" in paths
    assert "link/visible.txt" not in paths
    assert "real/visible.txt" in paths


def test_read_file_rejects_symlink_escape_through_path_guard(tmp_path):
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("secret", encoding="utf-8")
    link = tmp_path / "link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"symlink creation is unavailable: {error}")
    tools = make_tools(tmp_path)

    result = tools.read_file("link/secret.txt")

    assert result.ok is False
    assert result.error_kind == "permission_denied"
    assert result.error_message == "symlink_escape_denied"


def test_write_file_rejects_symlink_escape_through_path_guard(tmp_path):
    outside = tmp_path.parent / f"{tmp_path.name}-outside-write"
    outside.mkdir()
    generated = tmp_path / "generated"
    generated.mkdir()
    link = generated / "link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"symlink creation is unavailable: {error}")
    tools = make_tools(tmp_path, allowed_write_set=["generated/"])

    result = tools.write_file("generated/link/output.md", "secret")

    assert result.ok is False
    assert result.error_kind == "permission_denied"
    assert result.error_message == "symlink_escape_denied"
    assert not (outside / "output.md").exists()
```

- [ ] **Step 2: Run symlink tests**

Run:

```bash
pytest tests/test_filesystem_tools.py::test_list_files_does_not_recurse_into_symlink_directory tests/test_filesystem_tools.py::test_read_file_rejects_symlink_escape_through_path_guard tests/test_filesystem_tools.py::test_write_file_rejects_symlink_escape_through_path_guard -v
```

Expected:

```text
PASSED
```

- [ ] **Step 3: Run all filesystem tool tests**

Run:

```bash
pytest tests/test_filesystem_tools.py -v
```

Expected:

```text
PASSED
```

- [ ] **Step 4: Run full test suite**

Run:

```bash
pytest -v
```

Expected:

```text
PASSED
```

- [ ] **Step 5: Check there is no runtime environment fallback**

Run:

```bash
python - <<'PY'
from pathlib import Path
for path in Path('src').rglob('*.py'):
    text = path.read_text(encoding='utf-8')
    for needle in ('os.environ', 'getenv', 'dotenv', '.env'):
        if needle in text:
            print(f'{path}: contains {needle}')
PY
```

Expected:

```text

```

No output means runtime source does not read environment fallback.

- [ ] **Step 6: Check working tree scope**

Run:

```bash
git status --short
```

Expected before implementation review:

```text
 M docs/04-implementation-backlog/backlog.md
 M docs/04-implementation-plan/INDEX.md
 M docs/04-implementation-spec/INDEX.md
?? docs/04-implementation-plan/P0-004-filesystem-tools-plan.md
?? docs/04-implementation-spec/P0-004-filesystem-tools-spec.md
```

Expected after implementation:

```text
 M docs/04-implementation-backlog/backlog.md
 M docs/04-implementation-plan/INDEX.md
 M docs/04-implementation-spec/INDEX.md
?? docs/04-implementation-plan/P0-004-filesystem-tools-plan.md
?? docs/04-implementation-spec/P0-004-filesystem-tools-spec.md
?? src/atomic_agent/filesystem_tools.py
?? tests/test_filesystem_tools.py
```

Only P0-004 docs, implementation, and tests should be present.

---

### Task 9: Update docs after implementation passes

**Files:**

- Modify: `docs/04-implementation-backlog/backlog.md`
- Modify: `docs/04-implementation-spec/INDEX.md`
- Modify: `docs/04-implementation-plan/INDEX.md`

- [ ] **Step 1: Mark P0-004 completed only after tests pass**

Change `docs/04-implementation-backlog/backlog.md` from:

```markdown
| P0-004 | 实现 filesystem tools（文件系统工具）：list/read/search/write/patch | pending | `P0-004-filesystem-tools-spec.md`, `mvp-runtime-spec.md` |
```

To:

```markdown
| P0-004 | 实现 filesystem tools（文件系统工具）：list/read/search/write/patch | completed | `P0-004-filesystem-tools-spec.md`, `mvp-runtime-spec.md` |
```

- [ ] **Step 2: Move spec index entry out of draft status**

Change `docs/04-implementation-spec/INDEX.md` by moving `P0-004-filesystem-tools-spec.md` from Current Active Documents to Completed / Archived Documents after implementation and verification are accepted.

Completed entry:

```markdown
| `P0-004-filesystem-tools-spec.md` | 2026-06-05 | 已实现 P0-004 filesystem tools，保留为文件系统工具规格记录 |
```

- [ ] **Step 3: Move plan index entry to completed / archived**

Change `docs/04-implementation-plan/INDEX.md` by moving `P0-004-filesystem-tools-plan.md` from Current Active Documents to Completed / Archived Documents after implementation and verification are accepted.

Completed entry:

```markdown
| `P0-004-filesystem-tools-plan.md` | 2026-06-05 | 已实施 P0-004 filesystem tools，保留为 TDD 实施记录 |
```

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

`git status --short` should show only P0-004 implementation, tests, and required docs/index updates.

---

## Self-Review Checklist

Before implementation is considered ready for review:

- [ ] Spec coverage: Every requirement in `docs/04-implementation-spec/P0-004-filesystem-tools-spec.md` is covered by a task, test, or explicit out-of-scope statement.
- [ ] Placeholder scan: This plan contains no unspecified implementation steps, no deferred tool behavior, and no missing test cases for required tools.
- [ ] Type consistency: `FilesystemToolConfig`, `FileToolResult`, `FilesystemToolConfigError`, `FilesystemTools`, and `execute_filesystem_action` names match across tests, implementation steps, and spec.
- [ ] Scope check: No event recorder, JSONL output, command policy, network policy, provider logic, budget logic, or AgentLoop logic is included.
- [ ] Security check: Every user-supplied path goes through `WorkspacePathGuard`; no denied path falls back to another path; no write or patch happens outside allowed write set.
- [ ] Mutation check: `write_file` and `apply_patch` return real hashes and diff generated from real file contents.
- [ ] Verification check: `pytest -v` passes with real execution output.
