from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AgentRunStatus(str, Enum):
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"
    REQUIRES_APPROVAL = "requires_approval"


class AgentActionType(str, Enum):
    LIST_FILES = "list_files"
    READ_FILE = "read_file"
    SEARCH_FILES = "search_files"
    WRITE_FILE = "write_file"
    APPLY_PATCH = "apply_patch"
    RUN_COMMAND = "run_command"
    WEB_FETCH = "web_fetch"
    SUBMIT_RESULT = "submit_result"


class AgentEventType(str, Enum):
    RUN_STARTED = "run.started"
    RUN_COMPLETED = "run.completed"
    RUN_FAILED = "run.failed"
    PROVIDER_TURN_STARTED = "provider.turn.started"
    PROVIDER_TURN_COMPLETED = "provider.turn.completed"
    PROVIDER_TURN_FAILED = "provider.turn.failed"
    ACTION_PARSED = "action.parsed"
    ACTION_REJECTED = "action.rejected"
    PERMISSION_DECIDED = "permission.decided"
    TOOL_ATTEMPT_STARTED = "tool.attempt.started"
    TOOL_ATTEMPT_COMPLETED = "tool.attempt.completed"
    TOOL_ATTEMPT_FAILED = "tool.attempt.failed"
    WORKSPACE_MUTATION_RECORDED = "workspace.mutation.recorded"
    COMMAND_COMPLETED = "command.completed"
    NETWORK_FETCH_COMPLETED = "network.fetch.completed"
    RESULT_SUBMITTED = "result.submitted"


class AgentInvocation(StrictModel):
    invocation_id: str
    task: str
    workspace_root: str
    allowed_write_set: list[str]
    tools: list[str]
    permission_policy: dict[str, Any]
    provider_profile: dict[str, Any]
    budgets: dict[str, Any]
    output_requirements: dict[str, Any]
    role_context: str | None = None
    skill_context: dict[str, Any] | None = None
    initial_files: list[str] | None = None
    metadata: dict[str, Any] | None = None


class AgentAction(StrictModel):
    action_id: str
    action: AgentActionType
    reason_summary: str
    input: dict[str, Any]

    @model_validator(mode="after")
    def run_command_uses_command_id(self):
        if self.action != AgentActionType.RUN_COMMAND:
            return self
        forbidden_keys = {"command", "shell", "cmd"}
        if forbidden_keys.intersection(self.input):
            raise ValueError("run_command input must use command_id, not a shell command string")
        if "command_id" not in self.input:
            raise ValueError("run_command input requires command_id")
        return self


class AgentEvent(StrictModel):
    event_id: str
    run_id: str
    sequence: int = Field(ge=1)
    type: AgentEventType
    timestamp: str
    payload: dict[str, Any]
    previous_event_hash: str | None
    event_hash: str


class AgentRunResult(StrictModel):
    run_id: str
    status: AgentRunStatus
    event_stream_ref: str
    events_hash: str
    tool_attempts: list[dict[str, Any]]
    workspace_mutations: list[dict[str, Any]]
    artifacts: list[dict[str, Any]]
    summary: str
    failure_kind: str | None = None
    failure_message: str | None = None
    failed_action_ref: str | None = None

    @model_validator(mode="after")
    def failed_results_include_failure_details(self):
        if self.status == AgentRunStatus.FAILED and not self.failure_kind:
            raise ValueError("failed AgentRunResult requires failure_kind")
        if self.status == AgentRunStatus.FAILED and not self.failure_message:
            raise ValueError("failed AgentRunResult requires failure_message")
        return self
