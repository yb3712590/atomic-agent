import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import sys
import time
from typing import Any, Callable

import pytest

from atomic_agent.agent_loop import AgentLoop, AgentLoopConfig, AgentLoopDependencies
from atomic_agent.artifacts import ArtifactWriter, ArtifactWriterConfig
from atomic_agent.command_tools import CommandPolicy, CommandSpec, CommandToolConfig, CommandTools
from atomic_agent.evidence import build_evidence_summary, verify_event_stream
from atomic_agent.event_recorder import EventRecorder, EventRecorderConfig
from atomic_agent.filesystem_tools import FilesystemToolConfig, FilesystemTools
from atomic_agent.models import AgentInvocation
from atomic_agent.path_guard import WorkspacePathGuard
from atomic_agent.providers.openai_compatible import OpenAICompatibleProviderAdapter, OpenAICompatibleProviderOptions


PYTHON = Path(sys.executable).resolve()
REQUIRED_ENV = (
    "ATOMIC_AGENT_REAL_PROVIDER_BASE_URL",
    "ATOMIC_AGENT_REAL_PROVIDER_API_KEY",
    "ATOMIC_AGENT_REAL_PROVIDER_MODEL",
)
_SHA256_PREFIX = "sha256:"


@dataclass(frozen=True)
class RealProviderToolCase:
    name: str
    task: str
    enabled_tools: tuple[str, ...]
    required_tool: str | None
    expected_produced_paths: tuple[str, ...]
    setup_workspace: Callable[[Path], None]
    build_command_policy: Callable[[WorkspacePathGuard], CommandTools | None]
    assert_workspace: Callable[[Path], None]
    assert_summary: Callable[[str], None]
    required_event_types: tuple[str, ...]


def require_real_provider_tool_success_enabled():
    if os.environ.get("ATOMIC_AGENT_RUN_REAL_PROVIDER_TOOL_SUCCESS") != "1":
        pytest.skip("set ATOMIC_AGENT_RUN_REAL_PROVIDER_TOOL_SUCCESS=1 to run real provider tool success gate")
    missing = [name for name in REQUIRED_ENV if not os.environ.get(name)]
    if missing:
        pytest.fail("missing required real provider success test configuration: " + ", ".join(missing))


def env_value(name, default):
    return os.environ.get(name, default)


def env_int(name, default):
    return int(env_value(name, default))


def env_float_or_none(name, default):
    raw = os.environ.get(name, default)
    if raw in (None, ""):
        return None
    return float(raw)


def env_int_or_none(name, default):
    raw = os.environ.get(name, default)
    if raw in (None, ""):
        return None
    return int(raw)


def env_json_object_or_none(name, default):
    raw = os.environ.get(name, default)
    if raw in (None, ""):
        return None
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError(f"{name} must be a JSON object or empty string")
    return parsed


def env_stop_or_none(name, default):
    raw = os.environ.get(name, default)
    if raw in (None, ""):
        return None
    parsed = json.loads(raw)
    if not isinstance(parsed, list) or not parsed or any(not isinstance(item, str) or item == "" for item in parsed):
        raise ValueError(f"{name} must be a non-empty JSON array of non-empty strings or empty string")
    return tuple(parsed)


def provider_options():
    return OpenAICompatibleProviderOptions(
        base_url=os.environ["ATOMIC_AGENT_REAL_PROVIDER_BASE_URL"],
        api_key=os.environ["ATOMIC_AGENT_REAL_PROVIDER_API_KEY"],
        model=os.environ["ATOMIC_AGENT_REAL_PROVIDER_MODEL"],
        context_window_tokens=env_int("ATOMIC_AGENT_REAL_PROVIDER_CONTEXT_WINDOW_TOKENS", "400000"),
        max_output_tokens=env_int("ATOMIC_AGENT_REAL_PROVIDER_MAX_OUTPUT_TOKENS", "128000"),
        stream_idle_timeout_seconds=float(env_value("ATOMIC_AGENT_REAL_PROVIDER_STREAM_IDLE_TIMEOUT_SECONDS", "30")),
        total_timeout_seconds=float(env_value("ATOMIC_AGENT_REAL_PROVIDER_TOTAL_TIMEOUT_SECONDS", "3600")),
        temperature=env_float_or_none("ATOMIC_AGENT_REAL_PROVIDER_TEMPERATURE", ""),
        provider_label=os.environ.get("ATOMIC_AGENT_REAL_PROVIDER_LABEL") or None,
        reasoning_effort=os.environ.get("ATOMIC_AGENT_REAL_PROVIDER_REASONING_EFFORT") or None,
        top_p=env_float_or_none("ATOMIC_AGENT_REAL_PROVIDER_TOP_P", ""),
        presence_penalty=env_float_or_none("ATOMIC_AGENT_REAL_PROVIDER_PRESENCE_PENALTY", ""),
        frequency_penalty=env_float_or_none("ATOMIC_AGENT_REAL_PROVIDER_FREQUENCY_PENALTY", ""),
        seed=env_int_or_none("ATOMIC_AGENT_REAL_PROVIDER_SEED", ""),
        stop=env_stop_or_none("ATOMIC_AGENT_REAL_PROVIDER_STOP", ""),
        response_format=env_json_object_or_none("ATOMIC_AGENT_REAL_PROVIDER_RESPONSE_FORMAT_JSON", ""),
        stream_options=env_json_object_or_none("ATOMIC_AGENT_REAL_PROVIDER_STREAM_OPTIONS_JSON", ""),
        service_tier=os.environ.get("ATOMIC_AGENT_REAL_PROVIDER_SERVICE_TIER") or None,
        user=os.environ.get("ATOMIC_AGENT_REAL_PROVIDER_USER") or None,
    )


def test_provider_options_reads_explicit_p2_005_env(monkeypatch):
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_BASE_URL", "https://provider.example/v1")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_API_KEY", "secret-key")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_MODEL", "provider-model")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_TEMPERATURE", "0.2")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_REASONING_EFFORT", "high")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_TOP_P", "1.0")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_PRESENCE_PENALTY", "0.0")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_FREQUENCY_PENALTY", "0.0")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_SEED", "20260608")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_STOP", '["END_ACTION"]')
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_RESPONSE_FORMAT_JSON", '{"type":"json_object"}')
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_STREAM_OPTIONS_JSON", '{"include_usage":true}')
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_SERVICE_TIER", "default")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_USER", "atomic-agent-boardroom-os")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_LABEL", "boardroom-os-real-provider")

    options = provider_options()

    assert options.temperature == 0.2
    assert options.reasoning_effort == "high"
    assert options.top_p == 1.0
    assert options.presence_penalty == 0.0
    assert options.frequency_penalty == 0.0
    assert options.seed == 20260608
    assert options.stop == ("END_ACTION",)
    assert options.response_format == {"type": "json_object"}
    assert options.stream_options == {"include_usage": True}
    assert options.service_tier == "default"
    assert options.user == "atomic-agent-boardroom-os"
    assert options.provider_label == "boardroom-os-real-provider"


def test_provider_options_rejects_non_object_json_env(monkeypatch):
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_BASE_URL", "https://provider.example/v1")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_API_KEY", "secret-key")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_MODEL", "provider-model")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_RESPONSE_FORMAT_JSON", "[]")

    with pytest.raises(ValueError, match="ATOMIC_AGENT_REAL_PROVIDER_RESPONSE_FORMAT_JSON must be a JSON object"):
        provider_options()


def test_provider_options_rejects_invalid_stop_env(monkeypatch):
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_BASE_URL", "https://provider.example/v1")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_API_KEY", "secret-key")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_MODEL", "provider-model")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_STOP", "[]")

    with pytest.raises(ValueError, match="ATOMIC_AGENT_REAL_PROVIDER_STOP must be a non-empty JSON array"):
        provider_options()


def utc_timestamp():
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def make_filesystem_tools(workspace):
    guard = WorkspacePathGuard(workspace, allowed_write_set=["work/"])
    return guard, FilesystemTools(
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


def build_invocation(case, workspace, options):
    max_steps = env_int("ATOMIC_AGENT_REAL_PROVIDER_MAX_STEPS", "100")
    return AgentInvocation(
        invocation_id=f"inv_{case.name}",
        task=case.task,
        workspace_root=str(workspace),
        allowed_write_set=["work/"],
        tools=list(case.enabled_tools),
        permission_policy={"policy_ref": f"policy://tests/real-provider-tool-success/{case.name}"},
        provider_profile=options.to_provider_profile(),
        budgets={
            "max_steps": max_steps,
            "max_parse_failures": 1,
            "max_observation_chars": 20000,
            "max_wall_seconds": options.total_timeout_seconds * max_steps + 5.0,
        },
        output_requirements={"summary": True, "event_stream": True, "artifacts": True},
        metadata={"test": "real_provider_tool_success", "case": case.name},
    )


def run_and_assert_case(case, tmp_path):
    base = tmp_path / case.name
    workspace = base / "workspace"
    event_stream = base / "events" / "events.jsonl"
    artifact_root = base / "artifacts"
    workspace.mkdir(parents=True)
    event_stream.parent.mkdir(parents=True)
    artifact_root.mkdir(parents=True)
    (workspace / "work").mkdir()
    case.setup_workspace(workspace)

    options = provider_options()
    artifact_ref_prefix = f"artifact://real_provider_tool_success/{case.name}"
    guard, filesystem_tools = make_filesystem_tools(workspace)
    command_tools = case.build_command_policy(guard)
    recorder = EventRecorder(
        run_id=f"real_provider_tool_success_{case.name}",
        config=EventRecorderConfig(
            event_stream_path=event_stream,
            event_stream_ref=f"{artifact_ref_prefix}/events.jsonl",
        ),
        clock=utc_timestamp,
    )
    artifact_writer = ArtifactWriter(
        ArtifactWriterConfig(
            artifact_root=artifact_root,
            artifact_ref_prefix=artifact_ref_prefix,
        )
    )
    loop = AgentLoop(
        AgentLoopConfig(run_id=f"real_provider_tool_success_{case.name}"),
        AgentLoopDependencies(
            provider=OpenAICompatibleProviderAdapter(options=options),
            filesystem_tools=filesystem_tools,
            command_tools=command_tools,
            event_recorder=recorder,
            artifact_writer=artifact_writer,
            runtime_clock=time.monotonic,
        ),
    )

    result = loop.run(build_invocation(case, workspace, options))
    assert result.status.value == "completed", failure_context(result, event_stream)

    integrity = verify_event_stream(event_stream, expected_events_hash=result.events_hash)
    assert integrity["ok"] is True, integrity
    events = read_events(event_stream)
    types = event_types(events)
    assert types[-1] == "run.completed", types
    for event_type in case.required_event_types:
        assert event_type in types, {"missing_event_type": event_type, "event_types": types}

    submitted_paths = submitted_produced_paths(events)
    assert submitted_paths == list(case.expected_produced_paths), {
        "expected_produced_paths": case.expected_produced_paths,
        "actual_produced_paths": submitted_paths,
    }

    if case.required_tool is None:
        assert "tool.attempt.started" not in types, types
    else:
        observation = completed_observation_for_tool(events, artifact_root, artifact_ref_prefix, case.required_tool)
        assert observation["ok"] is True, observation
        assert observation["tool"] == case.required_tool, observation
        assert_observation_contents(case, observation)

    summary = build_evidence_summary(result, event_stream)
    assert summary["event_stream"]["integrity"]["ok"] is True
    for path in case.expected_produced_paths:
        lineage = [item for item in summary["source_inventory_lineage"] if item["path"] == path]
        assert lineage and lineage[0]["lineage_status"] == "traceable", summary["source_inventory_lineage"]
    if case.required_tool == "run_command":
        assert_successful_command_summary(summary)

    case.assert_workspace(workspace)
    case.assert_summary(result.summary)
    return result, events, summary, workspace


def read_events(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def event_types(events):
    return [event["type"] for event in events]


def submitted_produced_paths(events):
    for event in reversed(events):
        if event["type"] == "result.submitted":
            return event["payload"]["produced_paths"]
    return []


def completed_observation_for_tool(events, artifact_root, artifact_ref_prefix, tool):
    for event in events:
        if event["type"] == "tool.attempt.completed" and event["payload"]["tool"] == tool:
            observation_ref = event["payload"]["observation"]["artifact_ref"]
            observation_path = artifact_path(artifact_root, artifact_ref_prefix, observation_ref)
            return json.loads(observation_path.read_text(encoding="utf-8"))
    raise AssertionError({"missing_completed_tool": tool, "event_types": event_types(events)})


def artifact_path(artifact_root, artifact_ref_prefix, artifact_ref):
    prefix = artifact_ref_prefix + "/"
    assert artifact_ref.startswith(prefix), {"artifact_ref": artifact_ref, "expected_prefix": prefix}
    return artifact_root / artifact_ref.removeprefix(prefix)


def assert_observation_contents(case, observation):
    text = json.dumps(observation, sort_keys=True, ensure_ascii=False)
    if case.name == "read_file":
        assert "read fixture token" in text, observation
    if case.name == "list_files":
        assert "work/list-a.txt" in text, observation


def assert_successful_command_summary(summary):
    matching = [item for item in summary["command_results"] if item["command_id"] == "check-command-input"]
    assert matching, summary["command_results"]
    command = matching[-1]
    assert command["exit_code"] == 0, command
    assert_sha256(command["stdout"]["sha256"], "stdout sha256")
    assert_sha256(command["stderr"]["sha256"], "stderr sha256")


def assert_sha256(value, label):
    assert isinstance(value, str) and value.startswith(_SHA256_PREFIX) and len(value) == 71, {label: value}


def failure_context(result, event_stream):
    context = {"result": redact_sensitive_values(result.model_dump(mode="json"))}
    if event_stream.exists():
        events = read_events(event_stream)
        context["event_types"] = event_types(events)
    return context


def redact_sensitive_values(value):
    if isinstance(value, dict):
        return {key: redact_sensitive_values(child) for key, child in value.items()}
    if isinstance(value, list):
        return [redact_sensitive_values(child) for child in value]
    if isinstance(value, str):
        redacted = value
        replacements = {
            os.environ.get("ATOMIC_AGENT_REAL_PROVIDER_API_KEY"): "[REDACTED_API_KEY]",
            os.environ.get("ATOMIC_AGENT_REAL_PROVIDER_BASE_URL"): "[REDACTED_BASE_URL]",
        }
        for raw, replacement in replacements.items():
            if raw:
                redacted = redacted.replace(raw, replacement)
        return redacted
    return value


def assert_file_contains(path, expected):
    assert expected in path.read_text(encoding="utf-8")


def noop_workspace(workspace):
    return None


def no_command_policy(guard):
    return None


def assert_noop_workspace(workspace):
    return None


def assert_summary_non_empty(summary):
    assert isinstance(summary, str) and summary


def assert_summary_mentions_read_token(summary):
    assert "read fixture token" in summary


def assert_summary_mentions_list_file(summary):
    assert "list-a.txt" in summary or "list-b.txt" in summary


def protocol_task(goal, tool_input):
    return (
        f"{goal} "
        "Return exactly one AgentAction JSON object per turn, with no markdown and no code fences. "
        "Every action object must include action_id, action, reason_summary, and input. "
        f"For the required tool, use this input shape: {tool_input}. "
        "When the task is complete, use submit_result with input.summary as a non-empty string, "
        "input.produced_paths as the exact list requested by this task, and input.evidence_refs as a list of strings. "
        "Do not use tools that are not listed in invocation.tools."
    )


def write_file_case():
    return RealProviderToolCase(
        name="write_file",
        task=protocol_task(
            "Use write_file before submit_result. Create work/write-success.txt with content containing "
            "the exact phrase real provider write success. The final submit_result produced_paths must be "
            '["work/write-success.txt"].',
            '{"path":"work/write-success.txt","content":"real provider write success"}',
        ),
        enabled_tools=("write_file", "submit_result"),
        required_tool="write_file",
        expected_produced_paths=("work/write-success.txt",),
        setup_workspace=noop_workspace,
        build_command_policy=no_command_policy,
        assert_workspace=lambda workspace: assert_file_contains(
            workspace / "work" / "write-success.txt", "real provider write success"
        ),
        assert_summary=assert_summary_non_empty,
        required_event_types=("tool.attempt.completed", "workspace.mutation.recorded", "result.submitted"),
    )


def setup_read_workspace(workspace):
    (workspace / "work" / "read-input.txt").write_text("read fixture token", encoding="utf-8")


def read_file_case():
    return RealProviderToolCase(
        name="read_file",
        task=protocol_task(
            "Use read_file before submit_result. Read work/read-input.txt and include the exact phrase "
            "read fixture token in submit_result input.summary. The final submit_result produced_paths must be [].",
            '{"path":"work/read-input.txt"}',
        ),
        enabled_tools=("read_file", "submit_result"),
        required_tool="read_file",
        expected_produced_paths=(),
        setup_workspace=setup_read_workspace,
        build_command_policy=no_command_policy,
        assert_workspace=lambda workspace: assert_file_contains(workspace / "work" / "read-input.txt", "read fixture token"),
        assert_summary=assert_summary_mentions_read_token,
        required_event_types=("tool.attempt.completed", "result.submitted"),
    )


def setup_list_workspace(workspace):
    (workspace / "work" / "list-a.txt").write_text("alpha", encoding="utf-8")
    (workspace / "work" / "nested").mkdir()
    (workspace / "work" / "nested" / "list-b.txt").write_text("beta", encoding="utf-8")


def list_files_case():
    return RealProviderToolCase(
        name="list_files",
        task=protocol_task(
            "Use list_files before submit_result. List files under work/ and mention list-a.txt or list-b.txt "
            "in submit_result input.summary. The final submit_result produced_paths must be [].",
            '{"path":"work","recursive":true}',
        ),
        enabled_tools=("list_files", "submit_result"),
        required_tool="list_files",
        expected_produced_paths=(),
        setup_workspace=setup_list_workspace,
        build_command_policy=no_command_policy,
        assert_workspace=lambda workspace: assert_file_contains(workspace / "work" / "list-a.txt", "alpha"),
        assert_summary=assert_summary_mentions_list_file,
        required_event_types=("tool.attempt.completed", "result.submitted"),
    )


def setup_patch_workspace(workspace):
    (workspace / "work" / "patch-target.txt").write_text("before patch", encoding="utf-8")


def assert_patch_workspace(workspace):
    assert (workspace / "work" / "patch-target.txt").read_text(encoding="utf-8") == "after patch"


def apply_patch_case():
    return RealProviderToolCase(
        name="apply_patch",
        task=protocol_task(
            "Use apply_patch before submit_result. Change work/patch-target.txt from before patch to after patch. "
            "The final submit_result produced_paths must be [\"work/patch-target.txt\"].",
            '{"path":"work/patch-target.txt","old_text":"before patch","new_text":"after patch","replace_all":false}',
        ),
        enabled_tools=("apply_patch", "submit_result"),
        required_tool="apply_patch",
        expected_produced_paths=("work/patch-target.txt",),
        setup_workspace=setup_patch_workspace,
        build_command_policy=no_command_policy,
        assert_workspace=assert_patch_workspace,
        assert_summary=assert_summary_non_empty,
        required_event_types=("tool.attempt.completed", "workspace.mutation.recorded", "result.submitted"),
    )


def setup_command_workspace(workspace):
    (workspace / "work" / "command-input.txt").write_text("command ok", encoding="utf-8")


def build_check_command_policy(guard):
    return CommandTools(
        guard,
        CommandPolicy(
            {
                "check-command-input": CommandSpec(
                    argv=(
                        str(PYTHON),
                        "-c",
                        "from pathlib import Path; import sys; "
                        "content = Path('work/command-input.txt').read_text(encoding='utf-8'); "
                        "print('command ok verified' if content == 'command ok' else 'command mismatch'); "
                        "sys.exit(0 if content == 'command ok' else 3)",
                    )
                )
            }
        ),
        CommandToolConfig(default_timeout_seconds=2.0, max_timeout_seconds=5.0, max_output_bytes=4096),
    )


def run_command_case():
    return RealProviderToolCase(
        name="run_command",
        task=protocol_task(
            "Use run_command before submit_result. Run the declared command_id check-command-input exactly once. "
            "Then submit_result with a non-empty summary. The final submit_result produced_paths must be [].",
            '{"command_id":"check-command-input"}',
        ),
        enabled_tools=("run_command", "submit_result"),
        required_tool="run_command",
        expected_produced_paths=(),
        setup_workspace=setup_command_workspace,
        build_command_policy=build_check_command_policy,
        assert_workspace=lambda workspace: assert_file_contains(workspace / "work" / "command-input.txt", "command ok"),
        assert_summary=assert_summary_non_empty,
        required_event_types=("tool.attempt.completed", "command.completed", "result.submitted"),
    )


def submit_result_case():
    return RealProviderToolCase(
        name="submit_result",
        task=protocol_task(
            "No file or command work is needed. Use submit_result directly with a concise non-empty summary. "
            "The final submit_result produced_paths must be [].",
            '{"summary":"submit result success","produced_paths":[],"evidence_refs":[]}',
        ),
        enabled_tools=("submit_result",),
        required_tool=None,
        expected_produced_paths=(),
        setup_workspace=noop_workspace,
        build_command_policy=no_command_policy,
        assert_workspace=assert_noop_workspace,
        assert_summary=assert_summary_non_empty,
        required_event_types=("result.submitted",),
    )


@pytest.mark.real_provider_tool_success
def test_real_provider_success_write_file(tmp_path):
    require_real_provider_tool_success_enabled()
    run_and_assert_case(write_file_case(), tmp_path)


@pytest.mark.real_provider_tool_success
def test_real_provider_success_read_file(tmp_path):
    require_real_provider_tool_success_enabled()
    run_and_assert_case(read_file_case(), tmp_path)


@pytest.mark.real_provider_tool_success
def test_real_provider_success_list_files(tmp_path):
    require_real_provider_tool_success_enabled()
    run_and_assert_case(list_files_case(), tmp_path)


@pytest.mark.real_provider_tool_success
def test_real_provider_success_apply_patch(tmp_path):
    require_real_provider_tool_success_enabled()
    run_and_assert_case(apply_patch_case(), tmp_path)


@pytest.mark.real_provider_tool_success
def test_real_provider_success_run_command(tmp_path):
    require_real_provider_tool_success_enabled()
    run_and_assert_case(run_command_case(), tmp_path)


@pytest.mark.real_provider_tool_success
def test_real_provider_success_submit_result(tmp_path):
    require_real_provider_tool_success_enabled()
    run_and_assert_case(submit_result_case(), tmp_path)
