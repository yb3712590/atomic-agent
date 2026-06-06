from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
import time
from typing import Any, Sequence

from atomic_agent.agent_loop import AgentLoop, AgentLoopConfig, AgentLoopDependencies, ProviderContext
from atomic_agent.artifacts import ArtifactWriter, ArtifactWriterConfig
from atomic_agent.command_tools import CommandPolicy, CommandSpec, CommandToolConfig, CommandTools
from atomic_agent.event_recorder import EventRecorder, EventRecorderConfig
from atomic_agent.filesystem_tools import FilesystemToolConfig, FilesystemTools
from atomic_agent.models import AgentInvocation, AgentRunResult, AgentRunStatus
from atomic_agent.path_guard import WorkspacePathGuard


SUMMARY = "Created fixed output through a controlled fake provider loop."
WORKSPACE_OUTPUT_PATH = "work/output.txt"
EXPECTED_OUTPUT_CONTENT = "fixed"
CHECK_OUTPUT_SCRIPT = f"""\
from pathlib import Path
import sys

content = Path({WORKSPACE_OUTPUT_PATH!r}).read_text(encoding='utf-8')
sys.exit(0 if content == {EXPECTED_OUTPUT_CONTENT!r} else 3)
""".strip()


class ExampleInputError(ValueError):
    pass


@dataclass(frozen=True)
class ExamplePaths:
    workspace: Path
    event_stream: Path
    artifact_root: Path
    result: Path


class ScriptedProvider:
    def __init__(self, outputs: Sequence[str]):
        self.outputs = list(outputs)

    def complete(self, context: ProviderContext) -> str:
        # Fake provider（假模型供应商）是确定性脚本；接收 context 只用于满足 ProviderAdapter（模型供应商适配器）接口。
        _ = context
        if not self.outputs:
            raise RuntimeError("scripted provider has no remaining outputs")
        return self.outputs.pop(0)


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        paths = ExamplePaths(
            workspace=resolve_cli_path(args.workspace),
            event_stream=resolve_cli_path(args.event_stream),
            artifact_root=resolve_cli_path(args.artifact_root),
            result=resolve_cli_path(args.result),
        )
        prepare_paths(paths)
    except ExampleInputError as error:
        print_failure(str(error))
        return 2

    result = run_example(args.run_id, paths)
    write_result(paths.result, result)
    print_success(paths, result)
    return 0 if result.status == AgentRunStatus.COMPLETED else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the atomic-agent minimal fake provider loop example.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--event-stream", required=True)
    parser.add_argument("--artifact-root", required=True)
    parser.add_argument("--result", required=True)
    return parser


def resolve_cli_path(value: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ExampleInputError("path arguments must be non-empty strings")
    return Path(value).expanduser().absolute()


def prepare_paths(paths: ExamplePaths) -> None:
    workspace_output = paths.workspace / WORKSPACE_OUTPUT_PATH
    if paths.result.exists() or paths.result.is_symlink():
        raise ExampleInputError("result path already exists")
    if paths.event_stream.is_symlink() or paths.event_stream.is_dir():
        raise ExampleInputError("event stream path must be a file path")
    if paths.event_stream.exists() and paths.event_stream.stat().st_size > 0:
        raise ExampleInputError("event stream path must be empty or absent")
    if paths.artifact_root.is_symlink():
        raise ExampleInputError("artifact root must not be a symlink")
    if paths.artifact_root.exists():
        if not paths.artifact_root.is_dir():
            raise ExampleInputError("artifact root must be a directory")
        if any(paths.artifact_root.iterdir()):
            raise ExampleInputError("artifact root must be empty")
    if workspace_output.exists() or workspace_output.is_symlink():
        raise ExampleInputError("workspace output path already exists")

    ensure_directory(paths.workspace)
    ensure_directory(paths.event_stream.parent)
    ensure_directory(paths.artifact_root)
    ensure_directory(paths.result.parent)


def ensure_directory(path: Path) -> None:
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise ExampleInputError(f"failed to create directory {path}: {error}") from error
    if not path.is_dir():
        raise ExampleInputError(f"path is not a directory: {path}")


def run_example(run_id: str, paths: ExamplePaths) -> AgentRunResult:
    invocation = build_invocation(paths)
    loop = build_loop(run_id, paths)
    return loop.run(invocation)


def build_invocation(paths: ExamplePaths) -> AgentInvocation:
    return AgentInvocation(
        invocation_id="inv_minimal_example",
        task=f"Create {WORKSPACE_OUTPUT_PATH} with the content {EXPECTED_OUTPUT_CONTENT} through a controlled fake provider loop.",
        workspace_root=str(paths.workspace),
        allowed_write_set=["work/"],
        tools=["list_files", "read_file", "search_files", "write_file", "apply_patch", "run_command", "submit_result"],
        permission_policy={"policy_ref": "policy://examples/minimal-fake-loop"},
        provider_profile={"provider": "fake", "model": "scripted-minimal-loop"},
        budgets={
            "max_steps": 8,
            "max_parse_failures": 1,
            "max_observation_chars": 10000,
            "max_wall_seconds": 30.0,
        },
        output_requirements={"summary": True, "event_stream": True, "artifacts": True},
        metadata={"example": "minimal_fake_loop"},
    )


def build_loop(run_id: str, paths: ExamplePaths) -> AgentLoop:
    guard = WorkspacePathGuard(paths.workspace, allowed_write_set=["work/"])
    filesystem_tools = FilesystemTools(
        guard,
        FilesystemToolConfig(
            default_read_limit=12000,
            max_read_limit=50000,
            default_max_entries=200,
            max_entries_limit=1000,
            default_max_matches=50,
            max_matches_limit=500,
        ),
    )
    command_tools = CommandTools(
        guard,
        CommandPolicy(
            {
                "check-output": CommandSpec(
                    argv=(
                        str(Path(sys.executable).resolve()),
                        "-c",
                        CHECK_OUTPUT_SCRIPT,
                    )
                )
            }
        ),
        CommandToolConfig(default_timeout_seconds=2.0, max_timeout_seconds=5.0, max_output_bytes=4096),
    )
    recorder = EventRecorder(
        run_id=run_id,
        config=EventRecorderConfig(
            event_stream_path=paths.event_stream,
            event_stream_ref=f"artifact://{run_id}/events.jsonl",
        ),
        clock=utc_timestamp,
    )
    artifact_writer = ArtifactWriter(
        ArtifactWriterConfig(
            artifact_root=paths.artifact_root,
            artifact_ref_prefix=f"artifact://{run_id}",
        )
    )
    return AgentLoop(
        AgentLoopConfig(run_id=run_id),
        AgentLoopDependencies(
            provider=ScriptedProvider(provider_outputs()),
            filesystem_tools=filesystem_tools,
            command_tools=command_tools,
            event_recorder=recorder,
            artifact_writer=artifact_writer,
            runtime_clock=time.monotonic,
        ),
    )


def provider_outputs() -> list[str]:
    return [
        action("step-0001", "write_file", {"path": WORKSPACE_OUTPUT_PATH, "content": "draft"}),
        action("step-0002", "run_command", {"command_id": "check-output"}),
        action("step-0003", "apply_patch", {"path": WORKSPACE_OUTPUT_PATH, "old_text": "draft", "new_text": EXPECTED_OUTPUT_CONTENT}),
        action("step-0004", "run_command", {"command_id": "check-output"}),
        action(
            "step-0005",
            "submit_result",
            {
                "summary": SUMMARY,
                "produced_paths": [WORKSPACE_OUTPUT_PATH],
                "evidence_refs": ["step-0001", "step-0002", "step-0003", "step-0004"],
            },
        ),
    ]


def action(action_id: str, action_name: str, input_payload: dict[str, Any]) -> str:
    return json.dumps(
        {
            "action_id": action_id,
            "action": action_name,
            "reason_summary": f"Run {action_name} in the minimal fake provider loop.",
            "input": input_payload,
        },
        sort_keys=True,
    )


def utc_timestamp() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def write_result(path: Path, result: AgentRunResult) -> None:
    payload = result.model_dump(mode="json")
    path.write_text(json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def print_success(paths: ExamplePaths, result: AgentRunResult) -> None:
    status = "completed" if result.status == AgentRunStatus.COMPLETED else "failed"
    print(
        json.dumps(
            {
                "status": status,
                "result_path": str(paths.result),
                "event_stream_path": str(paths.event_stream),
                "artifact_root": str(paths.artifact_root),
                "workspace_output_path": str(paths.workspace / WORKSPACE_OUTPUT_PATH),
            },
            sort_keys=True,
            ensure_ascii=False,
        )
    )


def print_failure(message: str) -> None:
    print(json.dumps({"status": "failed", "error": message}, sort_keys=True, ensure_ascii=False), file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
