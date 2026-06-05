import json
from pathlib import Path
import sys

import pytest

from atomic_agent.agent_loop import AgentLoop, AgentLoopConfig, AgentLoopDependencies, ProviderContext
from atomic_agent.artifacts import ArtifactWriter, ArtifactWriterConfig
from atomic_agent.command_tools import CommandPolicy, CommandSpec, CommandToolConfig, CommandTools
from atomic_agent.event_recorder import EventRecorder, EventRecorderConfig
from atomic_agent.filesystem_tools import FilesystemToolConfig, FilesystemTools
from atomic_agent.models import AgentInvocation, AgentRunStatus
from atomic_agent.path_guard import WorkspacePathGuard


PYTHON = Path(sys.executable).resolve()


class ScriptedProvider:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.contexts = []

    def complete(self, context: ProviderContext) -> str:
        self.contexts.append(context)
        if not self.outputs:
            raise AssertionError("no provider output scripted")
        output = self.outputs.pop(0)
        if isinstance(output, Exception):
            raise output
        return output


def fixed_clock():
    return "2026-06-05T00:00:00Z"


class FakeRuntimeClock:
    def __init__(self, readings):
        self.readings = list(readings)
        self.calls = 0

    def __call__(self) -> float:
        self.calls += 1
        if self.readings:
            return self.readings.pop(0)
        return 0.0


def action(action_id, action_name, input_payload):
    return json.dumps(
        {
            "action_id": action_id,
            "action": action_name,
            "reason_summary": f"Run {action_name}.",
            "input": input_payload,
        },
        sort_keys=True,
    )


def read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def make_invocation(tmp_path, tools=None, budgets=None, allowed_write_set=None):
    return AgentInvocation(
        invocation_id="inv_001",
        task="Create a fixed output file through a controlled loop.",
        workspace_root=str(tmp_path),
        allowed_write_set=allowed_write_set or ["work/"],
        tools=tools
        or [
            "list_files",
            "read_file",
            "search_files",
            "write_file",
            "apply_patch",
            "run_command",
            "submit_result",
        ],
        permission_policy={"policy_ref": "policy://test/minimal-loop"},
        provider_profile={"provider": "fake", "model": "fake-model"},
        budgets=budgets
        or {
            "max_steps": 8,
            "max_parse_failures": 1,
            "max_observation_chars": 10000,
            "max_wall_seconds": 30.0,
        },
        output_requirements={"summary": True, "event_stream": True},
    )


def make_loop(tmp_path, provider, runtime_clock=None):
    event_dir = tmp_path / "events"
    event_dir.mkdir()
    artifact_dir = tmp_path / "artifacts"
    artifact_dir.mkdir()
    guard = WorkspacePathGuard(tmp_path, allowed_write_set=["work/"])
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
    command_policy = CommandPolicy(
        {
            "check-output": CommandSpec(
                argv=(
                    str(PYTHON),
                    "-c",
                    "from pathlib import Path; import sys; content = Path('work/output.txt').read_text(encoding='utf-8'); sys.exit(0 if content == 'fixed' else 3)",
                )
            )
        }
    )
    command_tools = CommandTools(
        guard,
        command_policy,
        CommandToolConfig(default_timeout_seconds=2.0, max_timeout_seconds=5.0, max_output_bytes=4096),
    )
    recorder = EventRecorder(
        run_id="run_001",
        config=EventRecorderConfig(
            event_stream_path=event_dir / "events.jsonl",
            event_stream_ref="artifact://run_001/events.jsonl",
        ),
        clock=fixed_clock,
    )
    artifact_writer = ArtifactWriter(
        ArtifactWriterConfig(
            artifact_root=artifact_dir,
            artifact_ref_prefix="artifact://run_001",
        )
    )
    if runtime_clock is None:
        runtime_clock = FakeRuntimeClock([0.0] * 100)
    loop = AgentLoop(
        AgentLoopConfig(run_id="run_001"),
        AgentLoopDependencies(
            provider=provider,
            filesystem_tools=filesystem_tools,
            command_tools=command_tools,
            event_recorder=recorder,
            artifact_writer=artifact_writer,
            runtime_clock=runtime_clock,
        ),
    )
    return loop, recorder.config.event_stream_path




def test_agent_loop_fails_closed_when_budget_fields_are_missing(tmp_path):
    provider = ScriptedProvider([])
    loop, event_stream_path = make_loop(tmp_path, provider)
    invocation = make_invocation(tmp_path, budgets={"max_steps": 3})

    result = loop.run(invocation)

    assert result.status == AgentRunStatus.FAILED
    assert result.failure_kind == "invalid_invocation"
    events = read_jsonl(event_stream_path)
    assert [event["type"] for event in events] == ["run.started", "run.failed"]


def successful_provider():
    return ScriptedProvider(
        [
            action("step-0001", "write_file", {"path": "work/output.txt", "content": "draft"}),
            action("step-0002", "run_command", {"command_id": "check-output"}),
            action("step-0003", "apply_patch", {"path": "work/output.txt", "old_text": "draft", "new_text": "fixed"}),
            action("step-0004", "run_command", {"command_id": "check-output"}),
            action(
                "step-0005",
                "submit_result",
                {
                    "summary": "Created fixed output.",
                    "produced_paths": ["work/output.txt"],
                    "evidence_refs": ["step-0001", "step-0004"],
                },
            ),
        ]
    )


def test_agent_loop_runs_multistep_fake_provider_to_submit_result(tmp_path):
    provider = successful_provider()
    loop, event_stream_path = make_loop(tmp_path, provider)

    result = loop.run(make_invocation(tmp_path))

    assert result.status == AgentRunStatus.COMPLETED
    assert result.summary == "Created fixed output."
    assert (tmp_path / "work" / "output.txt").read_text(encoding="utf-8") == "fixed"
    assert len(provider.contexts) == 5
    command_observation = provider.contexts[2].observations[-1]
    assert command_observation["step"] == 2
    assert command_observation["tool"] == "run_command"
    assert command_observation["truncated"] is False
    assert command_observation["artifact"]["artifact_ref"].endswith("observations/tool_attempt_000002.json")
    assert '"exit_code":3' in command_observation["visible"]
    assert result.event_stream_ref == "artifact://run_001/events.jsonl"
    assert result.events_hash.startswith("sha256:")
    assert len(result.tool_attempts) == 4
    assert [mutation["path"] for mutation in result.workspace_mutations] == ["work/output.txt", "work/output.txt"]
    assert any(artifact["artifact_ref"].endswith("results/step-0005.json") for artifact in result.artifacts)

    event_types = [event["type"] for event in read_jsonl(event_stream_path)]
    assert event_types[0] == "run.started"
    assert event_types[-2:] == ["result.submitted", "run.completed"]


def test_agent_loop_records_auditable_event_stream_details(tmp_path):
    provider = successful_provider()
    loop, event_stream_path = make_loop(tmp_path, provider)

    result = loop.run(make_invocation(tmp_path))

    events = read_jsonl(event_stream_path)
    event_types = [event["type"] for event in events]
    assert event_types == [
        "run.started",
        "provider.turn.started",
        "provider.turn.completed",
        "action.parsed",
        "permission.decided",
        "tool.attempt.started",
        "tool.attempt.completed",
        "workspace.mutation.recorded",
        "provider.turn.started",
        "provider.turn.completed",
        "action.parsed",
        "permission.decided",
        "tool.attempt.started",
        "tool.attempt.completed",
        "command.completed",
        "provider.turn.started",
        "provider.turn.completed",
        "action.parsed",
        "permission.decided",
        "tool.attempt.started",
        "tool.attempt.completed",
        "workspace.mutation.recorded",
        "provider.turn.started",
        "provider.turn.completed",
        "action.parsed",
        "permission.decided",
        "tool.attempt.started",
        "tool.attempt.completed",
        "command.completed",
        "provider.turn.started",
        "provider.turn.completed",
        "action.parsed",
        "permission.decided",
        "result.submitted",
        "run.completed",
    ]
    assert [event["sequence"] for event in events] == list(range(1, len(events) + 1))
    assert events[0]["previous_event_hash"] is None
    assert all(events[index]["previous_event_hash"] == events[index - 1]["event_hash"] for index in range(1, len(events)))

    provider_completed = [event for event in events if event["type"] == "provider.turn.completed"]
    assert provider_completed[0]["payload"]["output"]["artifact_ref"].endswith("provider/turn_000001.txt")
    permissions = [event for event in events if event["type"] == "permission.decided"]
    assert {event["payload"]["decision"] for event in permissions} == {"allow"}
    assert {event["payload"]["policy_ref"] for event in permissions} == {"policy://test/minimal-loop"}

    mutations = [event["payload"] for event in events if event["type"] == "workspace.mutation.recorded"]
    assert [mutation["path"] for mutation in mutations] == ["work/output.txt", "work/output.txt"]
    assert all(mutation["diff"]["artifact_ref"].endswith(".diff") for mutation in mutations)
    commands = [event["payload"] for event in events if event["type"] == "command.completed"]
    assert [command["exit_code"] for command in commands] == [3, 0]
    assert all(command["stdout"]["artifact_ref"].endswith(".stdout.txt") for command in commands)
    assert all(command["stderr"]["artifact_ref"].endswith(".stderr.txt") for command in commands)

    submission = events[-2]["payload"]
    assert submission["summary"] == result.summary
    assert submission["produced_paths"] == ["work/output.txt"]
    assert submission["artifact_refs"][0]["artifact_ref"].endswith("results/step-0005.json")


@pytest.mark.parametrize(
    ("name", "provider_outputs", "invocation_kwargs", "failure_kind", "failed_action_ref", "expected_event"),
    [
        (
            "invalid_json_retry_exceeded",
            ["not json", "still not json"],
            {},
            "action_parse_failed",
            "provider_turn_000002",
            "action.rejected",
        ),
        (
            "disabled_tool",
            [action("step-denied", "write_file", {"path": "work/output.txt", "content": "draft"})],
            {"tools": ["run_command", "submit_result"]},
            "policy_denied",
            "step-denied",
            "permission.decided",
        ),
        (
            "write_outside_allowed_set",
            [action("step-outside", "write_file", {"path": "outside.txt", "content": "draft"})],
            {},
            "policy_denied",
            "step-outside",
            "permission.decided",
        ),
        (
            "undeclared_command",
            [action("step-command", "run_command", {"command_id": "missing-command"})],
            {},
            "policy_denied",
            "step-command",
            "permission.decided",
        ),
        (
            "web_fetch_not_implemented",
            [action("step-web", "web_fetch", {"url": "https://example.com"})],
            {"tools": ["web_fetch", "submit_result"]},
            "policy_denied",
            "step-web",
            "permission.decided",
        ),
        (
            "max_steps_exceeded",
            [action("step-0001", "list_files", {"path": "work", "recursive": False})],
            {"budgets": {"max_steps": 1, "max_parse_failures": 1, "max_observation_chars": 10000, "max_wall_seconds": 30.0}},
            "max_steps_exceeded",
            None,
            "run.failed",
        ),
        (
            "provider_failure",
            [RuntimeError("provider unavailable")],
            {},
            "provider_failed",
            "provider_turn_000001",
            "provider.turn.failed",
        ),
    ],
)
def test_agent_loop_fails_closed_for_runtime_errors(
    tmp_path,
    name,
    provider_outputs,
    invocation_kwargs,
    failure_kind,
    failed_action_ref,
    expected_event,
):
    (tmp_path / "work").mkdir()
    provider = ScriptedProvider(provider_outputs)
    loop, event_stream_path = make_loop(tmp_path, provider)

    result = loop.run(make_invocation(tmp_path, **invocation_kwargs))

    assert name
    assert result.status == AgentRunStatus.FAILED
    assert result.failure_kind == failure_kind
    assert result.failed_action_ref == failed_action_ref
    assert result.failure_message
    events = read_jsonl(event_stream_path)
    assert events[-1]["type"] == "run.failed"
    assert events[-1]["payload"]["error"]["kind"] == failure_kind
    assert expected_event in [event["type"] for event in events]
    assert all(event["type"] != "run.completed" for event in events)


def test_agent_loop_fails_closed_when_max_wall_seconds_is_missing(tmp_path):
    provider = ScriptedProvider([])
    loop, event_stream_path = make_loop(tmp_path, provider)
    invocation = make_invocation(
        tmp_path,
        budgets={
            "max_steps": 3,
            "max_parse_failures": 1,
            "max_observation_chars": 10000,
        },
    )

    result = loop.run(invocation)

    assert result.status == AgentRunStatus.FAILED
    assert result.failure_kind == "invalid_invocation"
    assert "max_wall_seconds" in result.failure_message
    assert provider.contexts == []
    events = read_jsonl(event_stream_path)
    assert [event["type"] for event in events] == ["run.started", "run.failed"]


@pytest.mark.parametrize("max_wall_seconds", [0, -1, True, float("nan"), float("inf"), "30"])
def test_agent_loop_fails_closed_when_max_wall_seconds_is_invalid(tmp_path, max_wall_seconds):
    provider = ScriptedProvider([])
    loop, event_stream_path = make_loop(tmp_path, provider)
    invocation = make_invocation(
        tmp_path,
        budgets={
            "max_steps": 3,
            "max_parse_failures": 1,
            "max_observation_chars": 10000,
            "max_wall_seconds": max_wall_seconds,
        },
    )

    result = loop.run(invocation)

    assert result.status == AgentRunStatus.FAILED
    assert result.failure_kind == "invalid_invocation"
    assert "max_wall_seconds" in result.failure_message
    assert provider.contexts == []
    events = read_jsonl(event_stream_path)
    assert [event["type"] for event in events] == ["run.started", "run.failed"]


def test_agent_loop_fails_closed_when_wall_time_exceeded_before_provider_turn(tmp_path):
    provider = ScriptedProvider([action("step-0001", "submit_result", {"summary": "Done", "produced_paths": [], "evidence_refs": []})])
    runtime_clock = FakeRuntimeClock([0.0, 31.0])
    loop, event_stream_path = make_loop(tmp_path, provider, runtime_clock=runtime_clock)

    result = loop.run(make_invocation(tmp_path))

    assert result.status == AgentRunStatus.FAILED
    assert result.failure_kind == "max_wall_seconds_exceeded"
    assert result.failed_action_ref is None
    assert provider.contexts == []
    events = read_jsonl(event_stream_path)
    assert [event["type"] for event in events] == ["run.started", "run.failed"]


def test_agent_loop_fails_closed_when_wall_time_exceeded_after_provider_turn(tmp_path):
    provider = ScriptedProvider([action("step-0001", "write_file", {"path": "work/output.txt", "content": "draft"})])
    runtime_clock = FakeRuntimeClock([0.0, 0.0, 31.0])
    loop, event_stream_path = make_loop(tmp_path, provider, runtime_clock=runtime_clock)

    result = loop.run(make_invocation(tmp_path))

    assert result.status == AgentRunStatus.FAILED
    assert result.failure_kind == "max_wall_seconds_exceeded"
    assert result.failed_action_ref == "provider_turn_000001"
    assert len(provider.contexts) == 1
    assert not (tmp_path / "work" / "output.txt").exists()
    event_types = [event["type"] for event in read_jsonl(event_stream_path)]
    assert event_types == ["run.started", "provider.turn.started", "provider.turn.completed", "run.failed"]


def test_agent_loop_fails_closed_when_wall_time_exceeded_after_tool_result(tmp_path):
    provider = ScriptedProvider(
        [
            action("step-0001", "write_file", {"path": "work/output.txt", "content": "draft"}),
            action("step-0002", "submit_result", {"summary": "Done", "produced_paths": ["work/output.txt"], "evidence_refs": []}),
        ]
    )
    runtime_clock = FakeRuntimeClock([0.0, 0.0, 0.0, 0.0, 31.0])
    loop, event_stream_path = make_loop(tmp_path, provider, runtime_clock=runtime_clock)

    result = loop.run(make_invocation(tmp_path))

    assert result.status == AgentRunStatus.FAILED
    assert result.failure_kind == "max_wall_seconds_exceeded"
    assert result.failed_action_ref == "step-0001"
    assert len(provider.contexts) == 1
    assert (tmp_path / "work" / "output.txt").read_text(encoding="utf-8") == "draft"
    event_types = [event["type"] for event in read_jsonl(event_stream_path)]
    assert event_types[-4:] == [
        "tool.attempt.started",
        "tool.attempt.completed",
        "workspace.mutation.recorded",
        "run.failed",
    ]
    assert "result.submitted" not in event_types
    assert "run.completed" not in event_types


def test_agent_loop_fails_closed_when_runtime_clock_moves_backwards(tmp_path):
    provider = ScriptedProvider([action("step-0001", "submit_result", {"summary": "Done", "produced_paths": [], "evidence_refs": []})])
    runtime_clock = FakeRuntimeClock([10.0, 9.0])
    loop, event_stream_path = make_loop(tmp_path, provider, runtime_clock=runtime_clock)

    result = loop.run(make_invocation(tmp_path))

    assert result.status == AgentRunStatus.FAILED
    assert result.failure_kind == "invalid_invocation"
    assert provider.contexts == []
    assert [event["type"] for event in read_jsonl(event_stream_path)] == ["run.started", "run.failed"]


def test_agent_loop_fails_closed_when_runtime_clock_returns_non_finite_value(tmp_path):
    provider = ScriptedProvider([])
    runtime_clock = FakeRuntimeClock([float("nan")])
    loop, event_stream_path = make_loop(tmp_path, provider, runtime_clock=runtime_clock)

    result = loop.run(make_invocation(tmp_path))

    assert result.status == AgentRunStatus.FAILED
    assert result.failure_kind == "invalid_invocation"
    assert provider.contexts == []
    assert [event["type"] for event in read_jsonl(event_stream_path)] == ["run.started", "run.failed"]


def test_agent_loop_fails_closed_when_runtime_clock_raises(tmp_path):
    provider = ScriptedProvider([])

    def failing_runtime_clock() -> float:
        raise RuntimeError("clock unavailable")

    loop, event_stream_path = make_loop(tmp_path, provider, runtime_clock=failing_runtime_clock)

    result = loop.run(make_invocation(tmp_path))

    assert result.status == AgentRunStatus.FAILED
    assert result.failure_kind == "invalid_invocation"
    assert "runtime_clock failed" in result.failure_message
    assert "clock unavailable" in result.failure_message
    assert provider.contexts == []
    assert [event["type"] for event in read_jsonl(event_stream_path)] == ["run.started", "run.failed"]


def test_agent_loop_preserves_invalid_json_retry_limit_with_wall_budget(tmp_path):
    provider = ScriptedProvider(["not json", "still not json"])
    runtime_clock = FakeRuntimeClock([0.0] * 100)
    loop, event_stream_path = make_loop(tmp_path, provider, runtime_clock=runtime_clock)
    invocation = make_invocation(
        tmp_path,
        budgets={
            "max_steps": 4,
            "max_parse_failures": 1,
            "max_observation_chars": 10000,
            "max_wall_seconds": 30.0,
        },
    )

    result = loop.run(invocation)

    assert result.status == AgentRunStatus.FAILED
    assert result.failure_kind == "action_parse_failed"
    assert len(provider.contexts) == 2
    event_types = [event["type"] for event in read_jsonl(event_stream_path)]
    assert event_types.count("action.rejected") == 2
    assert event_types[-1] == "run.failed"


def test_agent_loop_preserves_max_steps_failure_with_wall_budget(tmp_path):
    (tmp_path / "work").mkdir()
    provider = ScriptedProvider([action("step-0001", "list_files", {"path": "work", "recursive": False})])
    runtime_clock = FakeRuntimeClock([0.0] * 100)
    loop, event_stream_path = make_loop(tmp_path, provider, runtime_clock=runtime_clock)
    invocation = make_invocation(
        tmp_path,
        budgets={
            "max_steps": 1,
            "max_parse_failures": 1,
            "max_observation_chars": 10000,
            "max_wall_seconds": 30.0,
        },
    )

    result = loop.run(invocation)

    assert result.status == AgentRunStatus.FAILED
    assert result.failure_kind == "max_steps_exceeded"
    assert result.failed_action_ref is None
    event_types = [event["type"] for event in read_jsonl(event_stream_path)]
    assert event_types[-1] == "run.failed"
    assert "run.completed" not in event_types
