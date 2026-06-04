from dataclasses import dataclass
import difflib
import hashlib
from pathlib import Path
from typing import Any, Iterator

from atomic_agent.models import AgentAction, AgentActionType
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

    def read_file(self, path: str, offset: int = 0, limit: int | None = None) -> FileToolResult:
        if not isinstance(path, str):
            return self._failure("read_file", str(path), "invalid_input", "path must be a string")
        if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
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
            content_bytes = target.read_bytes()
        except OSError as error:
            return self._failure("read_file", path, "io_error", str(error))

        chunk = content_bytes[offset : offset + resolved_limit]
        try:
            content = chunk.decode("utf-8")
        except UnicodeDecodeError as error:
            return self._failure("read_file", path, "decode_failed", str(error))

        return FileToolResult(
            ok=True,
            tool="read_file",
            path=path,
            data={
                "content": content,
                "offset": offset,
                "bytes_read": len(chunk),
                "truncated": offset + len(chunk) < len(content_bytes),
            },
        )

    def search_files(
        self,
        query: str,
        path: str | None = None,
        mode: str = "content",
        max_matches: int | None = None,
    ) -> FileToolResult:
        if not isinstance(query, str) or query == "":
            return self._failure("search_files", path, "invalid_input", "query must be a non-empty string")
        if mode not in {"name", "content"}:
            return self._failure("search_files", path, "invalid_input", 'mode must be "name" or "content"')
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

        target = self._resolve_read_target("search_files", path)
        if isinstance(target, FileToolResult):
            return target
        if not target.exists():
            return self._failure("search_files", path, "not_found", "Path not found.")
        if not target.is_dir():
            return self._failure("search_files", path, "not_directory", "Path is not a directory.")

        matches = []
        skipped = []
        truncated = False
        try:
            for candidate in self._iter_entries(target, recursive=True):
                if len(matches) >= limit:
                    truncated = True
                    break
                relative_path = self._relative_path(candidate)
                decision = self.guard.resolve_read_path(relative_path)
                if decision.decision == PathDecisionType.DENY:
                    skipped.append({"path": relative_path, "reason": decision.reason})
                    continue
                if mode == "name":
                    if query in relative_path:
                        matches.append({"path": relative_path, "line": None, "preview": relative_path})
                    continue
                if candidate.is_dir() or candidate.is_symlink():
                    continue
                file_truncated = self._search_file_content(candidate, query, limit, matches, skipped)
                if file_truncated:
                    truncated = True
                    break
        except OSError as error:
            return self._failure("search_files", path, "io_error", str(error))

        return FileToolResult(
            ok=True,
            tool="search_files",
            path=path,
            data={"matches": matches, "truncated": truncated, "skipped": skipped},
        )

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
            before_content = target.read_text(encoding="utf-8") if target.exists() else None
            before_hash = self._sha256(before_content.encode("utf-8")) if before_content is not None else None
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            written_bytes = target.read_bytes()
        except UnicodeDecodeError as error:
            return self._failure("write_file", path, "decode_failed", str(error))
        except OSError as error:
            return self._failure("write_file", path, "io_error", str(error))

        return FileToolResult(
            ok=True,
            tool="write_file",
            path=path,
            data={
                "bytes_written": len(written_bytes),
                "created": before_content is None,
                "before_hash": before_hash,
                "after_hash": self._sha256(written_bytes),
                "diff": self._unified_diff(path, before_content if before_content is not None else "", content),
            },
        )

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
            before_content = target.read_text(encoding="utf-8")
        except UnicodeDecodeError as error:
            return self._failure("apply_patch", path, "decode_failed", str(error))
        except OSError as error:
            return self._failure("apply_patch", path, "io_error", str(error))

        replacements = before_content.count(old_text)
        if replacements == 0:
            return self._failure("apply_patch", path, "patch_not_applied", "old_text was not found")
        if replacements > 1 and not replace_all:
            return self._failure("apply_patch", path, "ambiguous_patch", "old_text matched multiple times")

        after_content = before_content.replace(old_text, new_text, -1 if replace_all else 1)
        try:
            target.write_text(after_content, encoding="utf-8")
            after_bytes = target.read_bytes()
        except OSError as error:
            return self._failure("apply_patch", path, "io_error", str(error))

        before_bytes = before_content.encode("utf-8")
        return FileToolResult(
            ok=True,
            tool="apply_patch",
            path=path,
            data={
                "replacements": replacements if replace_all else 1,
                "before_hash": self._sha256(before_bytes),
                "after_hash": self._sha256(after_bytes),
                "diff": self._unified_diff(path, before_content, after_content),
            },
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

    def _resolve_write_target(self, tool: str, path: str) -> Path | FileToolResult:
        decision = self.guard.resolve_write_path(path)
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

    def _search_file_content(
        self,
        path: Path,
        query: str,
        limit: int,
        matches: list[dict[str, Any]],
        skipped: list[dict[str, str]],
    ) -> bool:
        relative_path = self._relative_path(path)
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as error:
            skipped.append({"path": relative_path, "reason": str(error)})
            return False
        except OSError as error:
            skipped.append({"path": relative_path, "reason": str(error)})
            return False

        for line_number, line in enumerate(content.splitlines(), start=1):
            if query not in line:
                continue
            if len(matches) >= limit:
                return True
            matches.append({"path": relative_path, "line": line_number, "preview": line})
        return False

    def _sha256(self, content: bytes) -> str:
        return f"sha256:{hashlib.sha256(content).hexdigest()}"

    def _unified_diff(self, path: str, before: str, after: str) -> str:
        return "".join(
            difflib.unified_diff(
                before.splitlines(keepends=True),
                after.splitlines(keepends=True),
                fromfile=f"a/{path}",
                tofile=f"b/{path}",
            )
        )

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
            path=action.input.get("path") if isinstance(action.input.get("path"), str) else None,
            data={},
            error_kind="invalid_input",
            error_message=str(error),
        )
    return FileToolResult(
        ok=False,
        tool=action.action.value,
        path=None,
        data={},
        error_kind="unsupported_action",
        error_message="Unsupported filesystem action.",
    )
