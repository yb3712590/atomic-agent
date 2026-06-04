from dataclasses import dataclass
from enum import Enum
from pathlib import Path, PurePosixPath, PureWindowsPath


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
    crossed_link: bool


@dataclass(frozen=True)
class AllowedWritePath:
    original: str
    path: Path
    is_directory: bool


class PathGuardConfigError(ValueError):
    pass


class WorkspacePathGuard:
    def __init__(self, workspace_root: str | Path, allowed_write_set: list[str]):
        try:
            self.workspace_root = Path(workspace_root).resolve(strict=True)
        except OSError as error:
            raise PathGuardConfigError("workspace_root must be an existing directory") from error
        if not self.workspace_root.is_dir():
            raise PathGuardConfigError("workspace_root must be an existing directory")
        self.allowed_write_set = self._normalize_allowed_write_set(allowed_write_set)

    def resolve_read_path(self, requested_path: str) -> PathDecision:
        decision = self._resolve_workspace_path(requested_path)
        if decision.decision == PathDecisionType.DENY:
            return decision
        return PathDecision(
            decision=PathDecisionType.ALLOW,
            requested_path=decision.requested_path,
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
                decision.requested_path,
                decision.normalized_path,
                "write_not_allowed",
            )
        return PathDecision(
            PathDecisionType.ALLOW,
            decision.requested_path,
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
            is_directory = self._is_directory_policy(entry)
            resolved = self._resolve_candidate(self._workspace_candidate(entry))
            if not resolved.path.is_relative_to(self.workspace_root):
                raise PathGuardConfigError("allowed write path must stay inside workspace_root")
            normalized.append(AllowedWritePath(entry, resolved.path, is_directory))
        return normalized

    def _validate_relative_policy_path(self, path: str) -> str | None:
        if not isinstance(path, str):
            return "allowed write path must be a string"
        validation = self._validate_relative_path(path)
        if validation == "empty_path_denied":
            return "allowed write path must be a non-empty relative path"
        if validation == "absolute_path_denied":
            return "allowed write path must be relative"
        if validation == "path_escape_denied":
            return "allowed write path cannot contain '..'"
        return validation

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
        if not isinstance(requested_path, str):
            return PathDecision(
                PathDecisionType.DENY,
                str(requested_path),
                None,
                "invalid_path_type_denied",
            )

        validation = self._validate_relative_path(requested_path)
        if validation is not None:
            return PathDecision(PathDecisionType.DENY, requested_path, None, validation)

        candidate = self._workspace_candidate(requested_path)
        resolved = self._resolve_candidate(candidate)
        if not resolved.path.is_relative_to(self.workspace_root):
            reason = "symlink_escape_denied" if resolved.crossed_link or candidate.is_relative_to(self.workspace_root) else "path_outside_workspace_denied"
            return PathDecision(
                PathDecisionType.DENY,
                requested_path,
                str(resolved.path),
                reason,
            )
        return PathDecision(PathDecisionType.ALLOW, requested_path, str(resolved.path), "path_allowed")

    def _validate_relative_path(self, path: str) -> str | None:
        if not path or not path.strip():
            return "empty_path_denied"
        if self._is_absolute_like_path(path):
            return "absolute_path_denied"
        if not self._relative_path_parts(path):
            return "empty_path_denied"
        if self._contains_parent_traversal(path):
            return "path_escape_denied"
        return None

    def _is_absolute_like_path(self, path: str) -> bool:
        windows_path = PureWindowsPath(path)
        return (
            Path(path).is_absolute()
            or PurePosixPath(path).is_absolute()
            or windows_path.is_absolute()
            or bool(windows_path.drive or windows_path.root)
        )

    def _contains_parent_traversal(self, path: str) -> bool:
        return ".." in PurePosixPath(path).parts or ".." in PureWindowsPath(path).parts

    def _relative_path_parts(self, path: str) -> tuple[str, ...]:
        windows_path = PureWindowsPath(path)
        return tuple(
            part
            for part in windows_path.parts
            if part not in {"", ".", windows_path.drive, windows_path.root}
        )

    def _is_directory_policy(self, path: str) -> bool:
        return path.endswith(("/", "\\"))

    def _workspace_candidate(self, path: str) -> Path:
        return self.workspace_root.joinpath(*self._relative_path_parts(path))

    def _resolve_candidate(self, candidate: Path) -> ResolvedPath:
        return ResolvedPath(candidate.resolve(strict=False), self._crosses_link(candidate))

    def _crosses_link(self, candidate: Path) -> bool:
        current = self.workspace_root
        try:
            relative_parts = candidate.relative_to(self.workspace_root).parts
        except ValueError:
            return False

        for part in relative_parts:
            current = current / part
            if current.is_symlink() or self._is_junction(current):
                return True
            if not current.exists():
                return False
        return False

    def _is_junction(self, path: Path) -> bool:
        return hasattr(path, "is_junction") and path.is_junction()
