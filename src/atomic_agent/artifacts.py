from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from atomic_agent.event_recorder import ArtifactReference


@dataclass(frozen=True)
class ArtifactWriterConfig:
    artifact_root: Path
    artifact_ref_prefix: str


class ArtifactWriterError(RuntimeError):
    pass


class ArtifactWriter:
    def __init__(self, config: ArtifactWriterConfig):
        self.config = config
        self._validate_config()
        self.artifact_root = config.artifact_root.resolve(strict=True)
        self.artifact_ref_prefix = config.artifact_ref_prefix.rstrip("/")

    def write_text(
        self,
        relative_path: str,
        content: str,
        truncated_in_observation: bool = False,
    ) -> dict[str, Any]:
        if not isinstance(content, str):
            raise ArtifactWriterError("artifact content must be a string")
        if not isinstance(truncated_in_observation, bool):
            raise ArtifactWriterError("truncated_in_observation must be a boolean")
        return self._write_bytes(relative_path, content.encode("utf-8"), truncated_in_observation)

    def write_json(
        self,
        relative_path: str,
        payload: dict[str, Any] | list[Any],
        truncated_in_observation: bool = False,
    ) -> dict[str, Any]:
        text = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return self.write_text(relative_path, text, truncated_in_observation)

    def _write_bytes(self, relative_path: str, content: bytes, truncated_in_observation: bool) -> dict[str, Any]:
        normalized = self._normalize_relative_path(relative_path)
        target = self.artifact_root.joinpath(*normalized.parts)
        self._ensure_target_stays_in_artifact_root(target)
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        except OSError as error:
            raise ArtifactWriterError(f"failed to write artifact: {error}") from error
        return ArtifactReference(
            artifact_ref=f"{self.artifact_ref_prefix}/{normalized.as_posix()}",
            sha256=self._sha256(content),
            size_bytes=len(content),
            truncated_in_observation=truncated_in_observation,
        ).to_payload()

    def _ensure_target_stays_in_artifact_root(self, target: Path) -> None:
        resolved_parent = target.parent.resolve(strict=False)
        if not resolved_parent.is_relative_to(self.artifact_root):
            raise ArtifactWriterError("artifact path must stay inside artifact_root")
        if target.exists():
            try:
                resolved_target = target.resolve(strict=True)
            except OSError as error:
                raise ArtifactWriterError(f"failed to resolve artifact target: {error}") from error
            if not resolved_target.is_relative_to(self.artifact_root):
                raise ArtifactWriterError("artifact target must stay inside artifact_root")

    def _normalize_relative_path(self, relative_path: str) -> PurePosixPath:
        if not isinstance(relative_path, str) or not relative_path.strip():
            raise ArtifactWriterError("artifact relative_path must be a non-empty string")
        if self._is_absolute_like_path(relative_path):
            raise ArtifactWriterError("artifact relative_path must be relative")
        posix_path = PurePosixPath(relative_path)
        windows_path = PureWindowsPath(relative_path)
        if ".." in posix_path.parts or ".." in windows_path.parts:
            raise ArtifactWriterError("artifact relative_path cannot contain '..'")
        parts = tuple(part for part in posix_path.parts if part not in {"", "."})
        if not parts:
            raise ArtifactWriterError("artifact relative_path must contain a filename")
        return PurePosixPath(*parts)

    def _is_absolute_like_path(self, path: str) -> bool:
        windows_path = PureWindowsPath(path)
        return (
            Path(path).is_absolute()
            or PurePosixPath(path).is_absolute()
            or windows_path.is_absolute()
            or bool(windows_path.drive or windows_path.root)
        )

    def _validate_config(self) -> None:
        if not isinstance(self.config.artifact_root, Path):
            raise ArtifactWriterError("artifact_root must be a Path")
        if not self.config.artifact_root.exists():
            raise ArtifactWriterError("artifact_root must exist")
        if not self.config.artifact_root.is_dir():
            raise ArtifactWriterError("artifact_root must be a directory")
        if not isinstance(self.config.artifact_ref_prefix, str) or not self.config.artifact_ref_prefix:
            raise ArtifactWriterError("artifact_ref_prefix must be a non-empty string")

    def _sha256(self, content: bytes) -> str:
        return f"sha256:{hashlib.sha256(content).hexdigest()}"
