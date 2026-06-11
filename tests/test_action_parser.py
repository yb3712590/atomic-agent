import json

import pytest

from atomic_agent.action_parser import ActionParseError, parse_agent_action, parse_agent_turn
from atomic_agent.models import AgentActionType


def test_parse_agent_action_accepts_valid_json_text():
    action = parse_agent_action(
        """
        {
          "action_id": "step-0001",
          "action": "read_file",
          "reason_summary": "Read the target file before patching.",
          "input": {"path": "README.md", "offset": 0, "limit": 12000}
        }
        """
    )

    assert action.action_id == "step-0001"
    assert action.action == AgentActionType.READ_FILE
    assert action.input["path"] == "README.md"


def test_parse_agent_action_accepts_run_command_with_command_id():
    action = parse_agent_action(
        """
        {
          "action_id": "step-0002",
          "action": "run_command",
          "reason_summary": "Run the declared test command.",
          "input": {"command_id": "test"}
        }
        """
    )

    assert action.action == AgentActionType.RUN_COMMAND
    assert action.input == {"command_id": "test"}


def test_parse_agent_turn_accepts_single_action():
    parsed = parse_agent_turn(
        json.dumps(
            {
                "action_id": "step-0001",
                "action": "write_file",
                "reason_summary": "Create file.",
                "input": {"path": "work/a.txt", "content": "hello"},
            }
        )
    )

    assert parsed.protocol == "agent-action-v1"
    assert [action.action_id for action in parsed.actions] == ["step-0001"]


def test_parse_agent_turn_accepts_explicit_batch_v1():
    parsed = parse_agent_turn(
        json.dumps(
            {
                "batch_id": "batch-0001",
                "protocol": "agent-action-batch-v1",
                "reason_summary": "Create and check package.",
                "actions": [
                    {
                        "action_id": "step-0001",
                        "action": "write_file",
                        "reason_summary": "Create file.",
                        "input": {"path": "work/a.txt", "content": "hello"},
                    },
                    {
                        "action_id": "step-0002",
                        "action": "run_command",
                        "reason_summary": "Run declared check.",
                        "input": {"command_id": "check"},
                    },
                ],
            }
        )
    )

    assert parsed.protocol == "agent-action-batch-v1"
    assert parsed.batch_id == "batch-0001"
    assert [action.action_id for action in parsed.actions] == ["step-0001", "step-0002"]


def test_parse_agent_turn_rejects_bare_json_array():
    with pytest.raises(ActionParseError, match="explicit batch object") as error:
        parse_agent_turn(
            json.dumps(
                [
                    {
                        "action_id": "step-0001",
                        "action": "write_file",
                        "reason_summary": "Create file.",
                        "input": {"path": "work/a.txt", "content": "hello"},
                    }
                ]
            )
        )

    assert error.value.kind == "invalid_action_batch"


def test_parse_agent_turn_rejects_concatenated_json_objects():
    first = json.dumps(
        {
            "action_id": "step-0001",
            "action": "write_file",
            "reason_summary": "Create file.",
            "input": {"path": "work/a.txt", "content": "hello"},
        }
    )
    second = json.dumps(
        {
            "action_id": "step-0002",
            "action": "run_command",
            "reason_summary": "Run declared check.",
            "input": {"command_id": "check"},
        }
    )

    with pytest.raises(ActionParseError, match="valid JSON") as error:
        parse_agent_turn(first + second)

    assert error.value.kind == "invalid_json"


def test_parse_agent_turn_rejects_batch_without_protocol():
    with pytest.raises(ActionParseError, match="batch_like_without_protocol") as error:
        parse_agent_turn(
            json.dumps(
                {
                    "batch_id": "batch-0001",
                    "reason_summary": "Missing protocol.",
                    "actions": [],
                }
            )
        )

    assert error.value.kind == "batch_like_without_protocol"


@pytest.mark.permission_negative
def test_parse_agent_action_rejects_invalid_json():
    with pytest.raises(ActionParseError) as error:
        parse_agent_action("not json")

    assert error.value.kind == "invalid_json"
    assert "valid JSON" in error.value.message


def test_parse_agent_action_rejects_non_object_json():
    with pytest.raises(ActionParseError) as error:
        parse_agent_action("[]")

    assert error.value.kind == "invalid_action"
    assert "object" in error.value.message


@pytest.mark.permission_negative
def test_parse_agent_action_rejects_unknown_action():
    with pytest.raises(ActionParseError) as error:
        parse_agent_action(
            """
            {
              "action_id": "step-0003",
              "action": "free_shell",
              "reason_summary": "Run a shell command.",
              "input": {"command": "rm -rf ."}
            }
            """
        )

    assert error.value.kind == "schema_validation_failed"


def test_parse_agent_action_rejects_extra_envelope_fields():
    with pytest.raises(ActionParseError) as error:
        parse_agent_action(
            """
            {
              "action_id": "step-0004",
              "action": "read_file",
              "reason_summary": "Read a file.",
              "input": {"path": "README.md"},
              "unexpected": "not allowed"
            }
            """
        )

    assert error.value.kind == "schema_validation_failed"


@pytest.mark.permission_negative
@pytest.mark.parametrize("forbidden_key", ["command", "shell", "cmd"])
def test_parse_agent_action_rejects_run_command_shell_string(forbidden_key):
    with pytest.raises(ActionParseError) as error:
        parse_agent_action(
            f"""
            {{
              "action_id": "step-0005",
              "action": "run_command",
              "reason_summary": "Run tests.",
              "input": {{"{forbidden_key}": "pytest -v"}}
            }}
            """
        )

    assert error.value.kind == "schema_validation_failed"
    assert "command_id" in error.value.message



def test_parse_agent_action_accepts_web_fetch_with_url():
    action = parse_agent_action(
        """
        {
          "action_id": "step-web",
          "action": "web_fetch",
          "reason_summary": "Fetch allowed documentation.",
          "input": {"url": "https://example.com/docs", "method": "GET"}
        }
        """
    )

    assert action.action == AgentActionType.WEB_FETCH
    assert action.input == {"url": "https://example.com/docs", "method": "GET"}


@pytest.mark.permission_negative
@pytest.mark.parametrize("input_payload", ["{}", "{\"url\": \"\"}", "{\"url\": \"https://example.com\", \"method\": \"POST\"}"])
def test_parse_agent_action_rejects_invalid_web_fetch_input(input_payload):
    with pytest.raises(ActionParseError) as error:
        parse_agent_action(
            f"""
            {{
              "action_id": "step-web",
              "action": "web_fetch",
              "reason_summary": "Fetch documentation.",
              "input": {input_payload}
            }}
            """
        )

    assert error.value.kind == "schema_validation_failed"
