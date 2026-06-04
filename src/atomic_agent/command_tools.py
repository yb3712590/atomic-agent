from dataclasses import dataclass
import hashlib
from pathlib import Path
import re
import subprocess
from typing import Any

from atomic_agent.models import AgentAction, AgentActionType
from atomic_agent.path_guard import PathDecisionType, WorkspacePathGuard


_COMMAND_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.:-]+$")


@dataclass(frozen=True)
class CommandSpec:
    argv: tuple[str, ...]
    cwd: str | None = None
    timeout_seconds: float | None = None
    env: dict[str, str] | None = None
    allow_network: bool = False


@dataclass(frozen=True)
class CommandToolConfig:
    default_timeout_seconds: float
    max_timeout_seconds: float
    max_output_bytes: int


@dataclass(frozen=True)
class CommandToolResult:
    ok: bool
    tool: str
    command_id: str | None
    data: dict[str, Any]
    error_kind: str | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        if self.ok and (self.error_kind is not None or self.error_message is not None):
            raise ValueError("successful CommandToolResult must not include error fields")
        if not self.ok and (not self.error_kind or not self.error_message):
            raise ValueError("failed CommandToolResult requires error_kind and error_message")


class CommandToolConfigError(ValueError):
    pass


class CommandPolicy:
    def __init__(self, commands: dict[str, CommandSpec]):
        if not isinstance(commands, dict) or not commands:
            raise CommandToolConfigError("command policy must declare at least one command")
        self.commands: dict[str, CommandSpec] = {}
        for command_id, spec in commands.items():
            self._validate_command_id_for_config(command_id)
            self._validate_spec(spec)
            self.commands[command_id] = spec

    def resolve(self, command_id: str) -> CommandSpec | None:
        return self.commands.get(command_id)

    @staticmethod
    def is_valid_command_id(command_id: object) -> bool:
        return isinstance(command_id, str) and bool(_COMMAND_ID_PATTERN.fullmatch(command_id))

    def _validate_command_id_for_config(self, command_id: object) -> None:
        if not self.is_valid_command_id(command_id):
            raise CommandToolConfigError("command_id must be a non-empty stable identifier")

    def _validate_spec(self, spec: object) -> None:
        if not isinstance(spec, CommandSpec):
            raise CommandToolConfigError("command spec must be a CommandSpec")
        if not isinstance(spec.argv, tuple) or not spec.argv:
            raise CommandToolConfigError("command argv must be a non-empty tuple")
        for item in spec.argv:
            if not isinstance(item, str) or item == "":
                raise CommandToolConfigError("command argv entries must be non-empty strings")
        if not Path(spec.argv[0]).is_absolute():
            raise CommandToolConfigError("command executable must be an absolute path")
        if spec.cwd is not None and not isinstance(spec.cwd, str):
            raise CommandToolConfigError("command cwd must be a string or None")
        if spec.timeout_seconds is not None and not self._is_positive_number(spec.timeout_seconds):
            raise CommandToolConfigError("command timeout_seconds must be positive")
        if spec.env is not None:
            if not isinstance(spec.env, dict):
                raise CommandToolConfigError("command env must be a mapping")
            for key, value in spec.env.items():
                if not isinstance(key, str) or key == "":
                    raise CommandToolConfigError("command env keys must be non-empty strings")
                if not isinstance(value, str):
                    raise CommandToolConfigError("command env values must be strings")
        if spec.allow_network:
            raise CommandToolConfigError("P0-005 does not support network-enabled commands")

    def _is_positive_number(self, value: object) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0


class CommandTools:
    def __init__(self, guard: WorkspacePathGuard, policy: CommandPolicy, config: CommandToolConfig):
        self.guard = guard
        self.policy = policy
        self.config = config
        self._cwd_by_command_id: dict[str, Path] = {}
        self._validate_config()
        self._validate_policy_against_workspace()

    def _validate_config(self) -> None:
        if not self._is_positive_number(self.config.default_timeout_seconds):
            raise CommandToolConfigError("default_timeout_seconds must be positive")
        if not self._is_positive_number(self.config.max_timeout_seconds):
            raise CommandToolConfigError("max_timeout_seconds must be positive")
        if self.config.default_timeout_seconds > self.config.max_timeout_seconds:
            raise CommandToolConfigError("default_timeout_seconds must not exceed max_timeout_seconds")
        if not isinstance(self.config.max_output_bytes, int) or self.config.max_output_bytes <= 0:
            raise CommandToolConfigError("max_output_bytes must be a positive integer")

    def _validate_policy_against_workspace(self) -> None:
        for command_id, spec in self.policy.commands.items():
            timeout = spec.timeout_seconds if spec.timeout_seconds is not None else self.config.default_timeout_seconds
            if timeout > self.config.max_timeout_seconds:
                raise CommandToolConfigError("command timeout_seconds exceeds configured maximum")
            self._cwd_by_command_id[command_id] = self._resolve_cwd_for_config(spec.cwd)

    def _resolve_cwd_for_config(self, cwd: str | None) -> Path:
        if cwd is None:
            return self.guard.workspace_root
        decision = self.guard.resolve_read_path(cwd)
        if decision.decision == PathDecisionType.DENY:
            raise CommandToolConfigError(f"command cwd denied: {decision.reason}")
        target = Path(decision.normalized_path)
        if not target.exists():
            raise CommandToolConfigError("command cwd must exist")
        if not target.is_dir():
            raise CommandToolConfigError("command cwd must be a directory")
        return target

    def run_command(self, command_id: str) -> CommandToolResult:
        if not CommandPolicy.is_valid_command_id(command_id):
            return self._failure(
                command_id if isinstance(command_id, str) else None,
                "invalid_input",
                "command_id must be a non-empty stable identifier",
            )
        spec = self.policy.resolve(command_id)
        if spec is None:
            return self._failure(
                command_id,
                "permission_denied",
                "command_id is not declared in command policy",
            )

        timeout = spec.timeout_seconds if spec.timeout_seconds is not None else self.config.default_timeout_seconds
        cwd = self._cwd_by_command_id[command_id]
        env = dict(spec.env) if spec.env is not None else {}

        try:
            completed = subprocess.run(
                list(spec.argv),
                cwd=str(cwd),
                env=env,
                shell=False,
                capture_output=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return self._failure(command_id, "timeout", "Command exceeded timeout_seconds")
        except OSError as error:
            return self._failure(command_id, "execution_failed", str(error))

        stdout_data = self._stream_data(completed.stdout)
        stderr_data = self._stream_data(completed.stderr)
        return CommandToolResult(
            ok=True,
            tool="run_command",
            command_id=command_id,
            data={
                "command_id": command_id,
                "argv": list(spec.argv),
                "cwd": str(cwd),
                "exit_code": completed.returncode,
                "stdout": stdout_data["text"],
                "stderr": stderr_data["text"],
                "stdout_hash": stdout_data["hash"],
                "stderr_hash": stderr_data["hash"],
                "stdout_size_bytes": stdout_data["size_bytes"],
                "stderr_size_bytes": stderr_data["size_bytes"],
                "stdout_truncated": stdout_data["truncated"],
                "stderr_truncated": stderr_data["truncated"],
                "stdout_decoded_with_replacement": stdout_data["decoded_with_replacement"],
                "stderr_decoded_with_replacement": stderr_data["decoded_with_replacement"],
                "timeout_seconds": timeout,
            },
        )

    def _stream_data(self, content: bytes) -> dict[str, Any]:
        size_bytes = len(content)
        truncated = size_bytes > self.config.max_output_bytes
        visible = content[: self.config.max_output_bytes]
        text, decoded_with_replacement = self._decode_bytes(visible)
        return {
            "text": text,
            "hash": self._sha256(content),
            "size_bytes": size_bytes,
            "truncated": truncated,
            "decoded_with_replacement": decoded_with_replacement,
        }

    def _decode_bytes(self, content: bytes) -> tuple[str, bool]:
        try:
            return content.decode("utf-8"), False
        except UnicodeDecodeError:
            return content.decode("utf-8", errors="replace"), True

    def _sha256(self, content: bytes) -> str:
        return f"sha256:{hashlib.sha256(content).hexdigest()}"

    def _failure(self, command_id: str | None, error_kind: str, error_message: str) -> CommandToolResult:
        return CommandToolResult(
            ok=False,
            tool="run_command",
            command_id=command_id,
            data={},
            error_kind=error_kind,
            error_message=error_message,
        )

    def _is_positive_number(self, value: object) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0


def execute_command_action(action: AgentAction, tools: CommandTools) -> CommandToolResult:
    if action.action == AgentActionType.RUN_COMMAND:
        return tools.run_command(action.input["command_id"])
    return CommandToolResult(
        ok=False,
        tool=action.action.value,
        command_id=None,
        data={},
        error_kind="unsupported_action",
        error_message="Unsupported command action.",
    )
