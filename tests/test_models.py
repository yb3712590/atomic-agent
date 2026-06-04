import pytest
from pydantic import ValidationError

from atomic_agent.models import (
    AgentAction,
    AgentActionType,
    AgentEvent,
    AgentEventType,
    AgentInvocation,
    AgentRunResult,
    AgentRunStatus,
)


def valid_invocation_payload():
    return {
        "invocation_id": "inv_001",
        "task": "Read README and summarize current phase.",
        "workspace_root": "/workspace/project",
        "allowed_write_set": ["docs/04-implementation-plan/configuration-source-semantics-plan.md"],
        "tools": ["list_files", "read_file"],
        "permission_policy": {"file_reads": "workspace", "file_writes": "allowed_write_set"},
        "provider_profile": {"provider": "anthropic", "model": "claude-opus-4-7"},
        "budgets": {"max_steps": 8, "max_wall_seconds": 120},
        "output_requirements": {"summary": True, "event_stream": True},
    }


def test_agent_action_accepts_known_action():
    action = AgentAction(
        action_id="step-0001",
        action=AgentActionType.READ_FILE,
        reason_summary="Read the target file before patching.",
        input={"path": "README.md", "offset": 0, "limit": 12000},
    )

    assert action.action == AgentActionType.READ_FILE
    assert action.input["path"] == "README.md"


def test_agent_action_rejects_extra_fields():
    with pytest.raises(ValidationError):
        AgentAction(
            action_id="step-0001",
            action="read_file",
            reason_summary="Read the target file before patching.",
            input={"path": "README.md"},
            unexpected="not allowed",
        )


def test_agent_action_rejects_unknown_action():
    with pytest.raises(ValidationError):
        AgentAction(
            action_id="step-0001",
            action="free_shell",
            reason_summary="Run a shell command.",
            input={"command": "rm -rf ."},
        )


def test_agent_invocation_requires_explicit_provider_profile():
    payload = valid_invocation_payload()
    del payload["provider_profile"]

    with pytest.raises(ValidationError):
        AgentInvocation(**payload)


def test_agent_invocation_does_not_read_env_defaults(monkeypatch):
    monkeypatch.setenv("ATOMIC_AGENT_PROVIDER", "anthropic")
    monkeypatch.setenv("ATOMIC_AGENT_MODEL", "claude-opus-4-7")
    payload = valid_invocation_payload()
    del payload["provider_profile"]

    with pytest.raises(ValidationError):
        AgentInvocation(**payload)


def test_agent_invocation_accepts_complete_payload():
    invocation = AgentInvocation(**valid_invocation_payload())

    assert invocation.invocation_id == "inv_001"
    assert invocation.provider_profile["model"] == "claude-opus-4-7"
    assert invocation.budgets["max_steps"] == 8


def test_failed_agent_run_result_requires_failure_details():
    with pytest.raises(ValidationError):
        AgentRunResult(
            run_id="run_001",
            status=AgentRunStatus.FAILED,
            event_stream_ref="artifact://run_001/events.jsonl",
            events_hash="sha256:events",
            tool_attempts=[],
            workspace_mutations=[],
            artifacts=[],
            summary="The run failed.",
        )


def test_failed_agent_run_result_accepts_failure_details():
    result = AgentRunResult(
        run_id="run_001",
        status=AgentRunStatus.FAILED,
        event_stream_ref="artifact://run_001/events.jsonl",
        events_hash="sha256:events",
        tool_attempts=[],
        workspace_mutations=[],
        artifacts=[],
        summary="The run failed closed.",
        failure_kind="policy_denied",
        failure_message="The action attempted to write outside the allowed write set.",
        failed_action_ref="step-0004",
    )

    assert result.failure_kind == "policy_denied"
    assert result.failed_action_ref == "step-0004"


def test_agent_event_accepts_first_event_without_previous_hash():
    event = AgentEvent(
        event_id="evt_000001",
        run_id="run_001",
        sequence=1,
        type=AgentEventType.RUN_STARTED,
        timestamp="2026-06-04T00:00:00Z",
        payload={"event_protocol_version": 1},
        previous_event_hash=None,
        event_hash="sha256:first",
    )

    assert event.previous_event_hash is None
    assert event.type == AgentEventType.RUN_STARTED


def test_agent_event_rejects_zero_sequence():
    with pytest.raises(ValidationError):
        AgentEvent(
            event_id="evt_000000",
            run_id="run_001",
            sequence=0,
            type=AgentEventType.RUN_STARTED,
            timestamp="2026-06-04T00:00:00Z",
            payload={},
            previous_event_hash=None,
            event_hash="sha256:first",
        )


@pytest.mark.parametrize("forbidden_key", ["command", "shell", "cmd"])
def test_agent_action_rejects_run_command_without_command_id(forbidden_key):
    with pytest.raises(ValidationError):
        AgentAction(
            action_id="step-0006",
            action="run_command",
            reason_summary="Run tests.",
            input={forbidden_key: "pytest -v"},
        )


def test_agent_action_accepts_run_command_with_command_id():
    action = AgentAction(
        action_id="step-0007",
        action="run_command",
        reason_summary="Run declared tests.",
        input={"command_id": "test"},
    )

    assert action.input == {"command_id": "test"}
