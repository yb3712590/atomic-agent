import json
from typing import Any

from pydantic import ValidationError

from atomic_agent.models import AgentAction


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
