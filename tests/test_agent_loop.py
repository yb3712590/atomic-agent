from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
import sys
import threading

import pytest

from atomic_agent.agent_loop import AgentLoop, AgentLoopConfig, AgentLoopDependencies, ProviderContext
from atomic_agent.artifacts import ArtifactWriter, ArtifactWriterConfig
from atomic_agent.command_tools import CommandPolicy, CommandSpec, CommandToolConfig, CommandTools
from atomic_agent.event_recorder import EventRecorder, EventRecorderConfig
from atomic_agent.filesystem_tools import FilesystemToolConfig, FilesystemTools
from atomic_agent.models import AgentInvocation, AgentRunStatus
from atomic_agent.path_guard import WorkspacePathGuard
from atomic_agent.web_fetch_tools import NetworkAllowRule, NetworkPolicy, WebFetchToolConfig, WebFetchTools


PYTHON = Path(sys.executable).resolve()
_USE_DEFAULT_COMMAND_TOOLS = object()


class RecordingHandler(BaseHTTPRequestHandler):
    response_status = 200
    response_reason = "OK"
    response_body = b"ok"
    response_content_type = "text/plain; charset=utf-8"
    delay_seconds = 0.0
    request_paths = []

    def do_GET(self):
        if self.delay_seconds:
            import time

            time.sleep(self.delay_seconds)
        self.__class__.request_paths.append(self.path)
        self.send_response(self.response_status, self.response_reason)
        if self.response_content_type is not None:
            self.send_header("Content-Type", self.response_content_type)
        self.end_headers()
        try:
            self.wfile.write(self.response_body)
        except BrokenPipeError:
            pass

    def log_message(self, format, *args):
        return


@pytest.fixture
def local_http_server():
    class Handler(RecordingHandler):
        response_status = 200
        response_reason = "OK"
        response_body = b"ok"
        response_content_type = "text/plain; charset=utf-8"
        delay_seconds = 0.0
        request_paths = []

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server, Handler
    finally:
        server.shutdown()
        thread.join(timeout=2.0)
        server.server_close()


def make_web_fetch_tools(port, timeout_seconds=2.0):
    return WebFetchTools(
        NetworkPolicy((NetworkAllowRule("local-web", "http", "127.0.0.1", port, "/"),)),
        WebFetchToolConfig(timeout_seconds=timeout_seconds, max_response_bytes=4096),
    )


def create_escaping_directory_link(link: Path, target: Path):
    try:
        link.symlink_to(target, target_is_directory=True)
        return
    except OSError as error:
        if sys.platform != "win32":
            pytest.skip(f"symlink creation is unavailable: {error}")

    subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            "New-Item",
            "-ItemType",
            "Junction",
            "-Path",
            str(link),
            "-Target",
            str(target),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )


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


def make_invocation(tmp_path, tools=None, budgets=None, allowed_write_set=None, output_requirements=None):
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
        output_requirements=output_requirements or {"summary": True, "event_stream": True},
    )


def make_loop(
    tmp_path,
    provider,
    runtime_clock=None,
    web_fetch_tools=None,
    command_tools=_USE_DEFAULT_COMMAND_TOOLS,
    allowed_write_set=None,
):
    event_dir = tmp_path / "events"
    event_dir.mkdir()
    artifact_dir = tmp_path / "artifacts"
    artifact_dir.mkdir()
    guard = WorkspacePathGuard(tmp_path, allowed_write_set=allowed_write_set or ["work/"])
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
    if command_tools is _USE_DEFAULT_COMMAND_TOOLS:
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
            web_fetch_tools=web_fetch_tools,
            event_recorder=recorder,
            artifact_writer=artifact_writer,
            runtime_clock=runtime_clock,
        ),
    )
    return loop, recorder.config.event_stream_path




@pytest.mark.permission_negative
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


def test_agent_loop_executes_batch_actions_in_order(tmp_path):
    provider = ScriptedProvider(
        [
            json.dumps(
                {
                    "batch_id": "batch-0001",
                    "protocol": "agent-action-batch-v1",
                    "reason_summary": "Create, check, and submit.",
                    "actions": [
                        {
                            "action_id": "step-0001",
                            "action": "write_file",
                            "reason_summary": "Create output.",
                            "input": {"path": "work/output.txt", "content": "fixed"},
                        },
                        {
                            "action_id": "step-0002",
                            "action": "run_command",
                            "reason_summary": "Run declared check.",
                            "input": {"command_id": "check-output"},
                        },
                        {
                            "action_id": "step-0003",
                            "action": "submit_result",
                            "reason_summary": "Submit checked output.",
                            "input": {
                                "summary": "done",
                                "produced_paths": ["work/output.txt"],
                                "evidence_refs": ["check-output"],
                            },
                        },
                    ],
                }
            )
        ]
    )
    loop, event_stream_path = make_loop(tmp_path, provider)
    invocation = make_invocation(
        tmp_path,
        tools=["write_file", "run_command", "submit_result"],
        budgets={
            "max_steps": 5,
            "max_parse_failures": 0,
            "max_observation_chars": 10000,
            "max_wall_seconds": 30.0,
            "max_actions_per_turn": 4,
        },
    )

    result = loop.run(invocation)

    assert result.status == AgentRunStatus.COMPLETED
    events = read_jsonl(event_stream_path)
    assert [event["type"] for event in events].count("action.parsed") == 3
    assert any(
        event["type"] == "command.completed" and event["payload"]["command_id"] == "check-output"
        for event in events
    )
    parsed_actions = [event["payload"]["action"] for event in events if event["type"] == "action.parsed"]
    assert [action["action_id"] for action in parsed_actions] == ["step-0001", "step-0002", "step-0003"]
    assert {action["batch_id"] for action in parsed_actions} == {"batch-0001"}


@pytest.mark.permission_negative
def test_agent_loop_rejects_batch_over_action_limit(tmp_path):
    provider = ScriptedProvider(
        [
            json.dumps(
                {
                    "batch_id": "batch-0001",
                    "protocol": "agent-action-batch-v1",
                    "reason_summary": "Too many actions.",
                    "actions": [
                        {
                            "action_id": "step-0001",
                            "action": "write_file",
                            "reason_summary": "A.",
                            "input": {"path": "work/a.txt", "content": "a"},
                        },
                        {
                            "action_id": "step-0002",
                            "action": "write_file",
                            "reason_summary": "B.",
                            "input": {"path": "work/b.txt", "content": "b"},
                        },
                    ],
                }
            )
        ]
    )
    loop, _ = make_loop(tmp_path, provider)
    invocation = make_invocation(
        tmp_path,
        tools=["write_file", "submit_result"],
        budgets={
            "max_steps": 5,
            "max_parse_failures": 0,
            "max_observation_chars": 10000,
            "max_wall_seconds": 30.0,
            "max_actions_per_turn": 1,
        },
    )

    result = loop.run(invocation)

    assert result.status == AgentRunStatus.FAILED
    assert result.failure_kind == "action_parse_failed"
    assert not (tmp_path / "work" / "a.txt").exists()


@pytest.mark.permission_negative
def test_agent_loop_stops_batch_on_policy_denied(tmp_path):
    provider = ScriptedProvider(
        [
            json.dumps(
                {
                    "batch_id": "batch-0001",
                    "protocol": "agent-action-batch-v1",
                    "reason_summary": "Second action escapes.",
                    "actions": [
                        {
                            "action_id": "step-0001",
                            "action": "write_file",
                            "reason_summary": "Allowed.",
                            "input": {"path": "work/allowed/a.txt", "content": "a"},
                        },
                        {
                            "action_id": "step-0002",
                            "action": "write_file",
                            "reason_summary": "Denied.",
                            "input": {"path": "work/denied/b.txt", "content": "b"},
                        },
                        {
                            "action_id": "step-0003",
                            "action": "submit_result",
                            "reason_summary": "Should not run.",
                            "input": {
                                "summary": "bad",
                                "produced_paths": ["work/denied/b.txt"],
                                "evidence_refs": [],
                            },
                        },
                    ],
                }
            )
        ]
    )
    loop, event_stream_path = make_loop(tmp_path, provider, allowed_write_set=["work/allowed/"])
    invocation = make_invocation(
        tmp_path,
        allowed_write_set=["work/allowed/"],
        tools=["write_file", "submit_result"],
        budgets={
            "max_steps": 5,
            "max_parse_failures": 0,
            "max_observation_chars": 10000,
            "max_wall_seconds": 30.0,
            "max_actions_per_turn": 3,
        },
    )

    result = loop.run(invocation)

    assert result.status == AgentRunStatus.FAILED
    assert result.failure_kind == "policy_denied"
    events = read_jsonl(event_stream_path)
    parsed_ids = [event["payload"]["action"]["action_id"] for event in events if event["type"] == "action.parsed"]
    assert parsed_ids == ["step-0001", "step-0002"]
    assert (tmp_path / "work" / "allowed" / "a.txt").exists()
    assert not (tmp_path / "work" / "denied" / "b.txt").exists()


def test_agent_loop_runs_required_output_checkpoint_when_paths_exist(tmp_path):
    provider = ScriptedProvider(
        [
            json.dumps(
                {
                    "batch_id": "batch-0001",
                    "protocol": "agent-action-batch-v1",
                    "reason_summary": "Create required outputs.",
                    "actions": [
                        {
                            "action_id": "step-0001",
                            "action": "write_file",
                            "reason_summary": "A.",
                            "input": {"path": "work/a.txt", "content": "a"},
                        },
                        {
                            "action_id": "step-0002",
                            "action": "write_file",
                            "reason_summary": "B.",
                            "input": {"path": "work/b.txt", "content": "b"},
                        },
                    ],
                }
            ),
            json.dumps(
                {
                    "action_id": "step-0003",
                    "action": "submit_result",
                    "reason_summary": "Submit after checkpoint.",
                    "input": {
                        "summary": "done",
                        "produced_paths": ["work/a.txt", "work/b.txt"],
                        "evidence_refs": ["check-output"],
                    },
                }
            ),
        ]
    )
    loop, event_stream_path = make_loop(tmp_path, provider)
    invocation = make_invocation(
        tmp_path,
        tools=["write_file", "submit_result"],
        output_requirements={
            "summary": True,
            "event_stream": True,
            "required_output_checkpoint": {
                "when_all_paths_exist": ["work/a.txt", "work/b.txt"],
                "run_command_id": "check-output",
                "max_auto_runs": 1,
            },
        },
        budgets={
            "max_steps": 5,
            "max_parse_failures": 0,
            "max_observation_chars": 10000,
            "max_wall_seconds": 30.0,
            "max_actions_per_turn": 2,
        },
    )

    result = loop.run(invocation)

    assert result.status == AgentRunStatus.COMPLETED
    events = read_jsonl(event_stream_path)
    assert any(
        event["type"] == "command.completed" and event["payload"]["command_id"] == "check-output"
        for event in events
    )
    assert len(provider.contexts) == 2
    assert provider.contexts[1].observations[-1]["tool"] == "run_command"


@pytest.mark.permission_negative
def test_agent_loop_rejects_checkpoint_for_undeclared_command(tmp_path):
    command_tools = CommandTools(
        WorkspacePathGuard(tmp_path, allowed_write_set=["work/"]),
        CommandPolicy(
            {
                "declared": CommandSpec(
                    argv=(str(PYTHON), "-c", "raise SystemExit(0)"),
                )
            }
        ),
        CommandToolConfig(default_timeout_seconds=2.0, max_timeout_seconds=5.0, max_output_bytes=4096),
    )
    provider = ScriptedProvider([])
    loop, _ = make_loop(tmp_path, provider, command_tools=command_tools)
    invocation = make_invocation(
        tmp_path,
        output_requirements={
            "summary": True,
            "event_stream": True,
            "required_output_checkpoint": {
                "when_all_paths_exist": ["work/a.txt"],
                "run_command_id": "missing",
                "max_auto_runs": 1,
            },
        },
    )

    result = loop.run(invocation)

    assert result.status == AgentRunStatus.FAILED
    assert result.failure_kind == "invalid_invocation"


@pytest.mark.permission_negative
def test_agent_loop_does_not_auto_submit_after_checkpoint_passes(tmp_path):
    provider = ScriptedProvider(
        [
            json.dumps(
                {
                    "action_id": "step-0001",
                    "action": "write_file",
                    "reason_summary": "A.",
                    "input": {"path": "work/output.txt", "content": "fixed"},
                }
            )
        ]
    )
    loop, event_stream_path = make_loop(tmp_path, provider)
    invocation = make_invocation(
        tmp_path,
        tools=["write_file", "submit_result"],
        output_requirements={
            "summary": True,
            "event_stream": True,
            "required_output_checkpoint": {
                "when_all_paths_exist": ["work/output.txt"],
                "run_command_id": "check-output",
                "max_auto_runs": 1,
            },
        },
        budgets={
            "max_steps": 1,
            "max_parse_failures": 0,
            "max_observation_chars": 10000,
            "max_wall_seconds": 30.0,
            "max_actions_per_turn": 1,
        },
    )

    result = loop.run(invocation)

    assert result.status == AgentRunStatus.FAILED
    assert result.failure_kind == "max_steps_exceeded"
    events = read_jsonl(event_stream_path)
    assert any(event["type"] == "command.completed" for event in events)
    assert "result.submitted" not in [event["type"] for event in events]


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


@pytest.mark.permission_negative
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
            "web_fetch_tools_not_configured",
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


@pytest.mark.permission_negative
def test_agent_loop_fails_closed_when_web_fetch_tools_are_not_configured(tmp_path):
    provider = ScriptedProvider([action("step-web", "web_fetch", {"url": "https://example.com/docs"})])
    loop, event_stream_path = make_loop(tmp_path, provider)
    invocation = make_invocation(tmp_path, tools=["web_fetch", "submit_result"])

    result = loop.run(invocation)

    assert result.status == AgentRunStatus.FAILED
    assert result.failure_kind == "policy_denied"
    assert result.failed_action_ref == "step-web"
    assert "web_fetch_tools" in result.failure_message
    event_types = [event["type"] for event in read_jsonl(event_stream_path)]
    assert "tool.attempt.started" not in event_types
    assert "network.fetch.completed" not in event_types
    assert event_types[-3:] == ["permission.decided", "action.rejected", "run.failed"]


@pytest.mark.permission_negative
def test_agent_loop_fails_closed_when_command_tools_are_not_configured(tmp_path):
    provider = ScriptedProvider([action("step-command", "run_command", {"command_id": "check-output"})])
    loop, event_stream_path = make_loop(tmp_path, provider, command_tools=None)
    invocation = make_invocation(tmp_path, tools=["run_command", "submit_result"])

    result = loop.run(invocation)

    assert result.status == AgentRunStatus.FAILED
    assert result.failure_kind == "policy_denied"
    assert result.failed_action_ref == "step-command"
    assert "command_tools" in result.failure_message
    event_types = [event["type"] for event in read_jsonl(event_stream_path)]
    assert "tool.attempt.started" not in event_types
    assert "command.completed" not in event_types
    assert event_types[-3:] == ["permission.decided", "action.rejected", "run.failed"]


@pytest.mark.permission_negative
def test_agent_loop_denies_unallowed_web_fetch_without_tool_attempt(tmp_path, local_http_server):
    server, handler = local_http_server
    provider = ScriptedProvider([action("step-web", "web_fetch", {"url": f"http://127.0.0.1:{server.server_port}/denied"})])
    tools = WebFetchTools(
        NetworkPolicy((NetworkAllowRule("allowed-only", "http", "127.0.0.1", server.server_port, "/allowed"),)),
        WebFetchToolConfig(timeout_seconds=2.0, max_response_bytes=4096),
    )
    loop, event_stream_path = make_loop(tmp_path, provider, web_fetch_tools=tools)
    invocation = make_invocation(tmp_path, tools=["web_fetch", "submit_result"])

    result = loop.run(invocation)

    assert result.status == AgentRunStatus.FAILED
    assert result.failure_kind == "policy_denied"
    assert result.failed_action_ref == "step-web"
    assert handler.request_paths == []
    event_types = [event["type"] for event in read_jsonl(event_stream_path)]
    assert "tool.attempt.started" not in event_types
    assert "network.fetch.completed" not in event_types
    assert event_types[-3:] == ["permission.decided", "action.rejected", "run.failed"]


@pytest.mark.permission_negative
def test_agent_loop_denies_path_traversal_write_without_tool_attempt(tmp_path):
    outside_target = tmp_path.parent / f"{tmp_path.name}-outside-agent-loop.txt"
    provider = ScriptedProvider(
        [action("step-escape", "write_file", {"path": f"../{outside_target.name}", "content": "secret"})]
    )
    loop, event_stream_path = make_loop(tmp_path, provider)

    result = loop.run(make_invocation(tmp_path))

    assert result.status == AgentRunStatus.FAILED
    assert result.failure_kind == "policy_denied"
    assert result.failed_action_ref == "step-escape"
    assert "path_escape_denied" in result.failure_message
    assert not outside_target.exists()
    assert result.tool_attempts == []
    assert result.workspace_mutations == []
    event_types = [event["type"] for event in read_jsonl(event_stream_path)]
    assert event_types[-3:] == ["permission.decided", "action.rejected", "run.failed"]
    assert "tool.attempt.started" not in event_types


@pytest.mark.permission_negative
def test_agent_loop_denies_symlink_escape_write_without_mutation(tmp_path):
    outside = tmp_path.parent / f"{tmp_path.name}-outside-agent-loop"
    outside.mkdir()
    work = tmp_path / "work"
    work.mkdir()
    create_escaping_directory_link(work / "link", outside)
    provider = ScriptedProvider(
        [action("step-symlink", "write_file", {"path": "work/link/output.txt", "content": "secret"})]
    )
    loop, event_stream_path = make_loop(tmp_path, provider)

    result = loop.run(make_invocation(tmp_path))

    assert result.status == AgentRunStatus.FAILED
    assert result.failure_kind == "policy_denied"
    assert result.failed_action_ref == "step-symlink"
    assert "symlink_escape_denied" in result.failure_message
    assert not (outside / "output.txt").exists()
    assert result.tool_attempts == []
    assert result.workspace_mutations == []
    event_types = [event["type"] for event in read_jsonl(event_stream_path)]
    assert event_types[-3:] == ["permission.decided", "action.rejected", "run.failed"]
    assert "tool.attempt.started" not in event_types


@pytest.mark.permission_negative
def test_agent_loop_rejects_unknown_action_and_fails_closed(tmp_path):
    provider = ScriptedProvider(
        [
            json.dumps(
                {
                    "action_id": "step-unknown",
                    "action": "delete_workspace",
                    "reason_summary": "Delete the workspace.",
                    "input": {"path": "."},
                },
                sort_keys=True,
            )
        ]
    )
    loop, event_stream_path = make_loop(tmp_path, provider)
    invocation = make_invocation(
        tmp_path,
        budgets={
            "max_steps": 3,
            "max_parse_failures": 0,
            "max_observation_chars": 10000,
            "max_wall_seconds": 30.0,
        },
    )

    result = loop.run(invocation)

    assert result.status == AgentRunStatus.FAILED
    assert result.failure_kind == "action_parse_failed"
    assert result.failed_action_ref == "provider_turn_000001"
    assert result.tool_attempts == []
    assert result.workspace_mutations == []
    event_types = [event["type"] for event in read_jsonl(event_stream_path)]
    assert event_types == [
        "run.started",
        "provider.turn.started",
        "provider.turn.completed",
        "action.rejected",
        "run.failed",
    ]


@pytest.mark.permission_negative
def test_agent_loop_truncates_oversized_observation_without_losing_artifact(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    long_name = "very-long-file-name-that-forces-observation-truncation.txt"
    (work / long_name).write_text("content", encoding="utf-8")
    provider = ScriptedProvider(
        [
            action("step-list", "list_files", {"path": "work", "recursive": False}),
            action(
                "step-submit",
                "submit_result",
                {
                    "summary": "Listed workspace files.",
                    "produced_paths": [],
                    "evidence_refs": ["step-list"],
                },
            ),
        ]
    )
    loop, event_stream_path = make_loop(tmp_path, provider)
    max_observation_chars = 48
    invocation = make_invocation(
        tmp_path,
        tools=["list_files", "submit_result"],
        budgets={
            "max_steps": 2,
            "max_parse_failures": 1,
            "max_observation_chars": max_observation_chars,
            "max_wall_seconds": 30.0,
        },
    )

    result = loop.run(invocation)

    assert result.status == AgentRunStatus.COMPLETED
    assert len(provider.contexts) == 2
    # Step 2 的 ProviderContext（模型上下文）在 submit_result（提交结果）解析前创建，只包含 step 1 的工具观察。
    observation = provider.contexts[1].observations[-1]
    assert observation["tool"] == "list_files"
    assert observation["truncated"] is True
    assert len(observation["visible"]) == max_observation_chars
    assert observation["artifact"]["truncated_in_observation"] is True
    artifact_path = tmp_path / "artifacts" / "observations" / "tool_attempt_000001.json"
    artifact_payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert artifact_payload["data"]["entries"] == [
        {"path": f"work/{long_name}", "kind": "file", "size": 7}
    ]
    event_types = [event["type"] for event in read_jsonl(event_stream_path)]
    assert event_types[-2:] == ["result.submitted", "run.completed"]


def test_agent_loop_records_network_fetch_completed_for_allowed_web_fetch(tmp_path, local_http_server):
    server, handler = local_http_server
    handler.response_body = b"agent loop body"
    provider = ScriptedProvider(
        [
            action("step-web", "web_fetch", {"url": f"http://127.0.0.1:{server.server_port}/docs"}),
            action(
                "step-submit",
                "submit_result",
                {
                    "summary": "Fetched allowed URL.",
                    "produced_paths": [],
                    "evidence_refs": ["step-web"],
                },
            ),
        ]
    )
    loop, event_stream_path = make_loop(tmp_path, provider, web_fetch_tools=make_web_fetch_tools(server.server_port))
    invocation = make_invocation(tmp_path, tools=["web_fetch", "submit_result"])

    result = loop.run(invocation)

    assert result.status == AgentRunStatus.COMPLETED
    assert handler.request_paths == ["/docs"]
    assert result.tool_attempts[0]["tool"] == "web_fetch"
    assert result.tool_attempts[0]["ok"] is True
    events = read_jsonl(event_stream_path)
    event_types = [event["type"] for event in events]
    assert "network.fetch.completed" in event_types
    network_event = next(event for event in events if event["type"] == "network.fetch.completed")
    assert network_event["payload"]["tool_attempt_id"] == "tool_attempt_000001"
    assert network_event["payload"]["url"] == f"http://127.0.0.1:{server.server_port}/docs"
    assert network_event["payload"]["status_code"] == 200
    assert network_event["payload"]["response"]["artifact_ref"].endswith("web_fetch/tool_attempt_000001.response.json")


def test_agent_loop_records_failed_tool_attempt_when_web_fetch_times_out(tmp_path, local_http_server):
    server, handler = local_http_server
    handler.delay_seconds = 0.3
    provider = ScriptedProvider([action("step-web", "web_fetch", {"url": f"http://127.0.0.1:{server.server_port}/slow"})])
    loop, event_stream_path = make_loop(
        tmp_path,
        provider,
        web_fetch_tools=make_web_fetch_tools(server.server_port, timeout_seconds=0.05),
    )
    invocation = make_invocation(tmp_path, tools=["web_fetch", "submit_result"])

    result = loop.run(invocation)

    assert result.status == AgentRunStatus.FAILED
    assert result.failure_kind == "tool_failed"
    assert result.failed_action_ref == "step-web"
    assert result.tool_attempts[0]["tool"] == "web_fetch"
    assert result.tool_attempts[0]["ok"] is False
    assert result.tool_attempts[0]["error_kind"] == "timeout"
    event_types = [event["type"] for event in read_jsonl(event_stream_path)]
    assert event_types[-3:] == ["tool.attempt.started", "tool.attempt.failed", "run.failed"]
    assert "network.fetch.completed" not in event_types


@pytest.mark.permission_negative
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


@pytest.mark.permission_negative
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


@pytest.mark.permission_negative
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


@pytest.mark.permission_negative
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
