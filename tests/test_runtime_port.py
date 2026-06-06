import pytest

from atomic_agent.examples.minimal_fake_loop import (
    EXPECTED_OUTPUT_CONTENT,
    WORKSPACE_OUTPUT_PATH,
    ExamplePaths,
    build_invocation,
    build_loop,
    prepare_paths,
)
from atomic_agent.models import AgentInvocation, AgentRunResult, AgentRunStatus
from atomic_agent.runtime_port import BoardroomAgentRuntimePortAdapter


BANNED_GOVERNANCE_FIELDS = {
    "ticket_completed",
    "closeout_committed",
    "governance_status",
    "evidence_verified",
    "source_inventory_accepted",
}


class RecordingRunner:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.invocations = []

    def run(self, invocation):
        self.invocations.append(invocation)
        if self.error is not None:
            raise self.error
        return self.result


def make_invocation():
    return AgentInvocation(
        invocation_id="inv_boardroom_001",
        task="Run a controlled atomic-agent invocation for Boardroom evidence input.",
        workspace_root="/workspace/project",
        allowed_write_set=["work/"],
        tools=["write_file", "run_command", "submit_result"],
        permission_policy={"policy_ref": "policy://boardroom/runtime-port"},
        provider_profile={"provider": "fake", "model": "scripted"},
        budgets={
            "max_steps": 8,
            "max_parse_failures": 1,
            "max_observation_chars": 10000,
            "max_wall_seconds": 30.0,
        },
        output_requirements={"summary": True, "event_stream": True, "artifacts": True},
        metadata={"boardroom_ticket": "ticket-123"},
    )


def make_completed_result():
    return AgentRunResult(
        run_id="run_boardroom_001",
        status=AgentRunStatus.COMPLETED,
        event_stream_ref="artifact://run_boardroom_001/events.jsonl",
        events_hash="sha256:" + "a" * 64,
        tool_attempts=[
            {
                "tool_attempt_id": "tool_attempt_000001",
                "action_id": "step-0001",
                "tool": "write_file",
                "ok": True,
            }
        ],
        workspace_mutations=[
            {
                "tool_attempt_id": "tool_attempt_000001",
                "action_id": "step-0001",
                "tool": "write_file",
                "path": "work/output.txt",
            }
        ],
        artifacts=[
            {
                "artifact_ref": "artifact://run_boardroom_001/results/step-0002.json",
                "sha256": "sha256:" + "b" * 64,
                "size_bytes": 42,
                "truncated_in_observation": False,
            }
        ],
        summary="Runtime submitted a result for Boardroom evidence verification.",
    )


def make_failed_result():
    return AgentRunResult(
        run_id="run_boardroom_002",
        status=AgentRunStatus.FAILED,
        event_stream_ref="artifact://run_boardroom_002/events.jsonl",
        events_hash="sha256:" + "c" * 64,
        tool_attempts=[],
        workspace_mutations=[],
        artifacts=[],
        summary="Run failed closed: command_id is not declared in command policy",
        failure_kind="policy_denied",
        failure_message="command_id is not declared in command policy",
        failed_action_ref="step-command",
    )


def assert_no_governance_fields(result):
    payload = result.model_dump(mode="json")
    assert BANNED_GOVERNANCE_FIELDS.isdisjoint(payload)


def test_adapter_invokes_runner_with_same_invocation_and_returns_completed_result_unchanged():
    invocation = make_invocation()
    expected_result = make_completed_result()
    runner = RecordingRunner(expected_result)
    adapter = BoardroomAgentRuntimePortAdapter(runner)

    result = adapter.invoke(invocation)

    assert result is expected_result
    assert runner.invocations == [invocation]
    assert result.status == AgentRunStatus.COMPLETED
    assert result.event_stream_ref == "artifact://run_boardroom_001/events.jsonl"
    assert result.events_hash == "sha256:" + "a" * 64
    assert result.tool_attempts == expected_result.tool_attempts
    assert result.workspace_mutations == expected_result.workspace_mutations
    assert result.artifacts == expected_result.artifacts
    assert result.summary == expected_result.summary
    assert_no_governance_fields(result)


def test_adapter_returns_failed_result_unchanged_without_converting_to_success():
    invocation = make_invocation()
    expected_result = make_failed_result()
    runner = RecordingRunner(expected_result)
    adapter = BoardroomAgentRuntimePortAdapter(runner)

    result = adapter.invoke(invocation)

    assert result is expected_result
    assert runner.invocations == [invocation]
    assert result.status == AgentRunStatus.FAILED
    assert result.failure_kind == "policy_denied"
    assert result.failure_message == "command_id is not declared in command policy"
    assert result.failed_action_ref == "step-command"
    assert_no_governance_fields(result)


def test_adapter_rejects_non_agent_invocation_without_calling_runner():
    runner = RecordingRunner(make_completed_result())
    adapter = BoardroomAgentRuntimePortAdapter(runner)

    with pytest.raises(TypeError, match="AgentRuntimePort.invoke requires AgentInvocation"):
        adapter.invoke({"invocation_id": "not-a-model"})

    assert runner.invocations == []


def test_adapter_rejects_runner_result_that_is_not_agent_run_result():
    invocation = make_invocation()
    runner = RecordingRunner({"status": "completed"})
    adapter = BoardroomAgentRuntimePortAdapter(runner)

    with pytest.raises(TypeError, match="runner.run must return AgentRunResult"):
        adapter.invoke(invocation)

    assert runner.invocations == [invocation]


def test_adapter_propagates_runner_exception_without_faking_result():
    invocation = make_invocation()
    runner = RecordingRunner(error=RuntimeError("runtime unavailable"))
    adapter = BoardroomAgentRuntimePortAdapter(runner)

    with pytest.raises(RuntimeError, match="runtime unavailable"):
        adapter.invoke(invocation)

    assert runner.invocations == [invocation]


def test_adapter_works_with_real_agent_loop(tmp_path):
    paths = ExamplePaths(
        workspace=tmp_path / "workspace",
        event_stream=tmp_path / "events" / "events.jsonl",
        artifact_root=tmp_path / "artifacts",
        result=tmp_path / "result.json",
    )
    prepare_paths(paths)
    loop = build_loop("runtime_port_integration", paths)
    invocation = build_invocation(paths)
    adapter = BoardroomAgentRuntimePortAdapter(loop)

    result = adapter.invoke(invocation)

    assert isinstance(result, AgentRunResult)
    assert result.status == AgentRunStatus.COMPLETED
    assert result.run_id == "runtime_port_integration"
    assert (paths.workspace / WORKSPACE_OUTPUT_PATH).read_text(encoding="utf-8") == EXPECTED_OUTPUT_CONTENT
    assert result.event_stream_ref == "artifact://runtime_port_integration/events.jsonl"
    assert [attempt["tool"] for attempt in result.tool_attempts] == [
        "write_file",
        "run_command",
        "apply_patch",
        "run_command",
    ]
    assert [mutation["path"] for mutation in result.workspace_mutations] == [
        WORKSPACE_OUTPUT_PATH,
        WORKSPACE_OUTPUT_PATH,
    ]
    assert_no_governance_fields(result)


def test_package_exports_runtime_port_types():
    from atomic_agent import AgentRuntimePort, AgentRuntimeRunner, BoardroomAgentRuntimePortAdapter as ExportedAdapter

    assert AgentRuntimePort.__name__ == "AgentRuntimePort"
    assert AgentRuntimeRunner.__name__ == "AgentRuntimeRunner"
    assert ExportedAdapter is BoardroomAgentRuntimePortAdapter
