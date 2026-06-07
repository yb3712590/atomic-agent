from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import UTC, datetime
import json
import math
import os
from pathlib import Path
import sys
import time
from typing import Sequence

from atomic_agent.agent_loop import AgentLoop, AgentLoopConfig, AgentLoopDependencies
from atomic_agent.artifacts import ArtifactWriter, ArtifactWriterConfig
from atomic_agent.event_recorder import EventRecorder, EventRecorderConfig
from atomic_agent.filesystem_tools import FilesystemToolConfig, FilesystemTools
from atomic_agent.models import AgentInvocation, AgentRunResult, AgentRunStatus
from atomic_agent.path_guard import WorkspacePathGuard
from atomic_agent.providers.openai_compatible import OpenAICompatibleProviderAdapter, OpenAICompatibleProviderOptions


WORKSPACE_OUTPUT_PATH = "work/real-provider-output.txt"


class ExampleInputError(ValueError):
    pass


@dataclass(frozen=True)
class ExamplePaths:
    workspace: Path
    event_stream: Path
    artifact_root: Path
    result: Path


@dataclass(frozen=True)
class CliProviderConfig:
    base_url: str
    api_key: str
    model: str
    context_window_tokens: int
    max_output_tokens: int
    stream_idle_timeout_seconds: float
    total_timeout_seconds: float
    max_steps: int
    temperature: float | None
    provider_label: str | None


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        paths = ExamplePaths(
            workspace=resolve_cli_path(args.workspace),
            event_stream=resolve_cli_path(args.event_stream),
            artifact_root=resolve_cli_path(args.artifact_root),
            result=resolve_cli_path(args.result),
        )
        provider_config = provider_config_from_args(args)
        prepare_paths(paths)
    except ExampleInputError as error:
        print_failure(str(error))
        return 2

    result = run_example(args.run_id, paths, provider_config)
    write_result(paths.result, result)
    print_success(paths, result)
    return 0 if result.status == AgentRunStatus.COMPLETED else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the atomic-agent minimal OpenAI-compatible real provider loop gate.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--event-stream", required=True)
    parser.add_argument("--artifact-root", required=True)
    parser.add_argument("--result", required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--api-key-env", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--context-window-tokens", required=True, type=parse_positive_int)
    parser.add_argument("--max-output-tokens", required=True, type=parse_positive_int)
    parser.add_argument("--stream-idle-timeout-seconds", required=True, type=parse_positive_float)
    parser.add_argument("--total-timeout-seconds", required=True, type=parse_positive_float)
    parser.add_argument("--max-steps", required=True, type=parse_positive_int)
    parser.add_argument("--temperature", type=parse_float_or_none, default=None)
    parser.add_argument("--provider-label", default=None)
    return parser


def parse_positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be a positive integer") from error
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def parse_positive_float(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be a finite positive number") from error
    if not math.isfinite(parsed) or parsed <= 0:
        raise argparse.ArgumentTypeError("must be a finite positive number")
    return parsed


def parse_float_or_none(value: str) -> float | None:
    if value == "":
        return None
    try:
        parsed = float(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be a finite number or empty string") from error
    if not math.isfinite(parsed):
        raise argparse.ArgumentTypeError("must be a finite number or empty string")
    return parsed


def resolve_cli_path(value: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ExampleInputError("path arguments must be non-empty strings")
    return Path(value).expanduser().absolute()


def provider_config_from_args(args: argparse.Namespace) -> CliProviderConfig:
    api_key_env = args.api_key_env
    if not isinstance(api_key_env, str) or api_key_env == "":
        raise ExampleInputError("api key environment variable name must be a non-empty string")
    api_key = os.environ.get(api_key_env)
    if not api_key:
        raise ExampleInputError(f"environment variable {api_key_env} must be set")
    if args.provider_label is not None and args.provider_label == "":
        raise ExampleInputError("provider label must be non-empty when provided")
    return CliProviderConfig(
        base_url=args.base_url,
        api_key=api_key,
        model=args.model,
        context_window_tokens=args.context_window_tokens,
        max_output_tokens=args.max_output_tokens,
        stream_idle_timeout_seconds=args.stream_idle_timeout_seconds,
        total_timeout_seconds=args.total_timeout_seconds,
        max_steps=args.max_steps,
        temperature=args.temperature,
        provider_label=args.provider_label,
    )


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


def run_example(run_id: str, paths: ExamplePaths, provider_config: CliProviderConfig) -> AgentRunResult:
    invocation = build_invocation(paths, provider_config)
    loop = build_loop(run_id, paths, provider_config)
    return loop.run(invocation)


def build_invocation(paths: ExamplePaths, provider_config: CliProviderConfig) -> AgentInvocation:
    provider_profile = {
        "provider": "openai-compatible",
        "model": provider_config.model,
        "context_window_tokens": provider_config.context_window_tokens,
        "max_output_tokens": provider_config.max_output_tokens,
        "stream_idle_timeout_seconds": provider_config.stream_idle_timeout_seconds,
        "total_timeout_seconds": provider_config.total_timeout_seconds,
    }
    if provider_config.provider_label is not None:
        provider_profile["provider_label"] = provider_config.provider_label
    else:
        provider_profile["base_url"] = provider_config.base_url
    return AgentInvocation(
        invocation_id="inv_minimal_real_provider_example",
        task=(
            f"Use write_file to create {WORKSPACE_OUTPUT_PATH} with a short confirmation that the real provider gate ran. "
            f"After the write succeeds, call submit_result with produced_paths containing exactly {WORKSPACE_OUTPUT_PATH}."
        ),
        workspace_root=str(paths.workspace),
        allowed_write_set=["work/"],
        tools=["write_file", "submit_result"],
        permission_policy={"policy_ref": "policy://examples/minimal-real-provider-loop"},
        provider_profile=provider_profile,
        budgets={
            "max_steps": provider_config.max_steps,
            "max_parse_failures": 1,
            "max_observation_chars": 10000,
            "max_wall_seconds": provider_config.total_timeout_seconds * provider_config.max_steps + 5.0,
        },
        output_requirements={"summary": True, "event_stream": True, "artifacts": True},
        metadata={"example": "minimal_real_provider_loop"},
    )


def build_loop(run_id: str, paths: ExamplePaths, provider_config: CliProviderConfig) -> AgentLoop:
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
    provider = OpenAICompatibleProviderAdapter(
        options=OpenAICompatibleProviderOptions(
            base_url=provider_config.base_url,
            api_key=provider_config.api_key,
            model=provider_config.model,
            context_window_tokens=provider_config.context_window_tokens,
            max_output_tokens=provider_config.max_output_tokens,
            stream_idle_timeout_seconds=provider_config.stream_idle_timeout_seconds,
            total_timeout_seconds=provider_config.total_timeout_seconds,
            temperature=provider_config.temperature,
            provider_label=provider_config.provider_label,
        )
    )
    return AgentLoop(
        AgentLoopConfig(run_id=run_id),
        AgentLoopDependencies(
            provider=provider,
            filesystem_tools=filesystem_tools,
            command_tools=None,
            event_recorder=recorder,
            artifact_writer=artifact_writer,
            runtime_clock=time.monotonic,
        ),
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
