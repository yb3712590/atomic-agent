import json
from typing import Any

from pydantic import ValidationError

from atomic_agent.models import AgentAction, AgentActionBatch, ParsedAgentTurn


class ActionParseError(ValueError):
    def __init__(self, kind: str, message: str):
        self.kind = kind
        self.message = message
        super().__init__(message)


def parse_agent_action(provider_output: str) -> AgentAction:
    try:
        parsed: Any = json.loads(provider_output)
    except json.JSONDecodeError as error:
        raise ActionParseError("invalid_json", "Provider output must be valid JSON.") from error

    if not isinstance(parsed, dict):
        raise ActionParseError("invalid_action", "Provider output JSON must be an object.")

    try:
        return AgentAction.model_validate(parsed)
    except ValidationError as error:
        raise ActionParseError("schema_validation_failed", str(error)) from error


def parse_agent_turn(provider_output: str) -> ParsedAgentTurn:
    parsed = _load_last_provider_json_object(provider_output)

    if isinstance(parsed, list):
        raise ActionParseError(
            "invalid_action_batch",
            "Provider output must use an explicit batch object with protocol agent-action-batch-v1.",
        )
    if not isinstance(parsed, dict):
        raise ActionParseError("invalid_action", "Provider output JSON must be an object.")

    if parsed.get("protocol") == "agent-action-batch-v1":
        try:
            batch = AgentActionBatch.model_validate(parsed)
        except ValidationError as error:
            raise ActionParseError("schema_validation_failed", str(error)) from error
        return ParsedAgentTurn(
            protocol=batch.protocol,
            batch_id=batch.batch_id,
            reason_summary=batch.reason_summary,
            actions=batch.actions,
        )

    if "actions" in parsed or "batch_id" in parsed:
        raise ActionParseError(
            "batch_like_without_protocol",
            "batch_like_without_protocol: batch-shaped provider output must include protocol agent-action-batch-v1.",
        )

    try:
        action = AgentAction.model_validate(parsed)
    except ValidationError as error:
        raise ActionParseError("schema_validation_failed", str(error)) from error
    return ParsedAgentTurn(protocol="agent-action-v1", actions=[action])


def _load_last_provider_json_object(provider_output: str) -> Any:
    decoder = json.JSONDecoder()
    objects: list[Any] = []
    position = 0
    while position < len(provider_output):
        while position < len(provider_output) and provider_output[position].isspace():
            position += 1
        if position >= len(provider_output):
            break
        try:
            parsed, end = decoder.raw_decode(provider_output, position)
        except json.JSONDecodeError as error:
            raise ActionParseError("invalid_json", "Provider output must be valid JSON.") from error
        objects.append(parsed)
        position = end

    if not objects:
        raise ActionParseError("invalid_json", "Provider output must be valid JSON.")
    return objects[-1]
