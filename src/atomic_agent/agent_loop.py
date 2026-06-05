from dataclasses import dataclass, field
import json
import math
from typing import Any, Callable, Literal, Protocol

from atomic_agent.action_parser import ActionParseError, parse_agent_action
from atomic_agent.artifacts import ArtifactWriter
from atomic_agent.command_tools import CommandPolicy, CommandToolResult, CommandTools, execute_command_action
from atomic_agent.event_recorder import EventError, EventRecorder
from atomic_agent.filesystem_tools import FileToolResult, FilesystemTools, execute_filesystem_action
from atomic_agent.models import AgentAction, AgentActionType, AgentInvocation, AgentRunResult, AgentRunStatus
from atomic_agent.path_guard import PathDecisionType


_FILESYSTEM_ACTIONS = {
    AgentActionType.LIST_FILES,
    AgentActionType.READ_FILE,
    AgentActionType.SEARCH_FILES,
    AgentActionType.WRITE_FILE,
    AgentActionType.APPLY_PATCH,
}
_MUTATING_FILESYSTEM_ACTIONS = {AgentActionType.WRITE_FILE, AgentActionType.APPLY_PATCH}


@dataclass(frozen=True)
class ProviderContext:
    invocation: AgentInvocation
    step: int
    observations: tuple[dict[str, Any], ...]


class ProviderAdapter(Protocol):
    def complete(self, context: ProviderContext) -> str:
        ...


@dataclass(frozen=True)
class AgentLoopConfig:
    run_id: str


@dataclass(frozen=True)
class AgentLoopDependencies:
    provider: ProviderAdapter
    filesystem_tools: FilesystemTools
    command_tools: CommandTools
    event_recorder: EventRecorder
    artifact_writer: ArtifactWriter
    runtime_clock: Callable[[], float]


@dataclass(frozen=True)
class PermissionDecision:
    decision: Literal["allow", "deny"]
    reason: str
    policy_ref: str


class AgentLoopError(RuntimeError):
    pass


@dataclass
class _RunState:
    observations: list[dict[str, Any]] = field(default_factory=list)
    tool_attempts: list[dict[str, Any]] = field(default_factory=list)
    workspace_mutations: list[dict[str, Any]] = field(default_factory=list)
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    parse_failures: int = 0


@dataclass(frozen=True)
class _RuntimeRequirements:
    policy_ref: str
    max_steps: int
    max_parse_failures: int
    max_observation_chars: int
    max_wall_seconds: float


class AgentLoop:
    def __init__(self, config: AgentLoopConfig, dependencies: AgentLoopDependencies):
        if not isinstance(config.run_id, str) or not config.run_id:
            raise AgentLoopError("run_id must be a non-empty string")
        self.config = config
        self.dependencies = dependencies

    def run(self, invocation: AgentInvocation) -> AgentRunResult:
        state = _RunState()
        self.dependencies.event_recorder.record_run_started(invocation.invocation_id)
        requirements_or_error = self._runtime_requirements(invocation)
        if isinstance(requirements_or_error, str):
            return self._fail(
                state=state,
                failure_kind="invalid_invocation",
                failure_message=requirements_or_error,
                failed_action_ref=None,
            )
        requirements = requirements_or_error
        started_at_or_error = self._read_runtime_clock()
        if isinstance(started_at_or_error, str):
            return self._fail(
                state=state,
                failure_kind="invalid_invocation",
                failure_message=started_at_or_error,
                failed_action_ref=None,
            )
        started_at = started_at_or_error

        for step in range(1, requirements.max_steps + 1):
            wall_time_error = self._check_wall_time_budget(
                started_at,
                requirements,
                "max_wall_seconds exceeded before provider turn",
                None,
            )
            if wall_time_error is not None:
                return self._fail(state, *wall_time_error)
            provider_turn_id = f"provider_turn_{step:06d}"
            self.dependencies.event_recorder.record_provider_turn_started(provider_turn_id)
            try:
                provider_output = self.dependencies.provider.complete(
                    ProviderContext(invocation=invocation, step=step, observations=tuple(state.observations))
                )
            except Exception as error:
                message = str(error) or error.__class__.__name__
                self.dependencies.event_recorder.record_provider_turn_failed(
                    provider_turn_id,
                    EventError("provider_failed", message, retryable=False, related_ref=provider_turn_id).to_payload(),
                )
                return self._fail(state, "provider_failed", message, provider_turn_id)

            output_artifact = self.dependencies.artifact_writer.write_text(
                f"provider/turn_{step:06d}.txt", provider_output
            )
            state.artifacts.append(output_artifact)
            self.dependencies.event_recorder.record_provider_turn_completed(provider_turn_id, output_artifact)
            wall_time_error = self._check_wall_time_budget(
                started_at,
                requirements,
                "max_wall_seconds exceeded after provider turn",
                provider_turn_id,
            )
            if wall_time_error is not None:
                return self._fail(state, *wall_time_error)

            try:
                action = parse_agent_action(provider_output)
            except ActionParseError as error:
                state.parse_failures += 1
                can_retry = state.parse_failures <= requirements.max_parse_failures
                self.dependencies.event_recorder.record_action_rejected(
                    EventError(error.kind, error.message, retryable=can_retry, related_ref=provider_turn_id).to_payload()
                )
                if not can_retry:
                    return self._fail(state, "action_parse_failed", error.message, provider_turn_id)
                state.observations.append(
                    {
                        "step": step,
                        "action_id": None,
                        "tool": "provider_output",
                        "ok": False,
                        "visible": error.message[: requirements.max_observation_chars],
                        "truncated": len(error.message) > requirements.max_observation_chars,
                        "artifact": output_artifact,
                        "artifact_ref": output_artifact["artifact_ref"],
                    }
                )
                continue

            self.dependencies.event_recorder.record_action_parsed(action.model_dump(mode="json"))
            decision = self._decide_permission(invocation, requirements, action)
            self.dependencies.event_recorder.record_permission_decided(
                action.action_id,
                decision.decision,
                decision.policy_ref,
                decision.reason,
            )
            if decision.decision == "deny":
                self.dependencies.event_recorder.record_action_rejected(
                    EventError("policy_denied", decision.reason, retryable=False, related_ref=action.action_id).to_payload()
                )
                return self._fail(state, "policy_denied", decision.reason, action.action_id)
            wall_time_error = self._check_wall_time_budget(
                started_at,
                requirements,
                "max_wall_seconds exceeded before action execution",
                action.action_id,
            )
            if wall_time_error is not None:
                return self._fail(state, *wall_time_error)

            if action.action == AgentActionType.SUBMIT_RESULT:
                submission_error = self._validate_result_submission(action)
                if submission_error is not None:
                    self.dependencies.event_recorder.record_action_rejected(
                        EventError(
                            "invalid_result_submission",
                            submission_error,
                            retryable=False,
                            related_ref=action.action_id,
                        ).to_payload()
                    )
                    return self._fail(state, "tool_failed", submission_error, action.action_id)
                return self._submit_result(state, action)

            tool_attempt_id = f"tool_attempt_{step:06d}"
            self.dependencies.event_recorder.record_tool_attempt_started(
                tool_attempt_id,
                action.action_id,
                action.action.value,
            )
            result = self._execute_tool_action(action)
            self._record_tool_result(state, requirements, action, tool_attempt_id, result)
            wall_time_error = self._check_wall_time_budget(
                started_at,
                requirements,
                "max_wall_seconds exceeded after tool execution",
                action.action_id,
            )
            if wall_time_error is not None:
                return self._fail(state, *wall_time_error)
            if not result.ok:
                message = result.error_message or "tool action failed"
                return self._fail(state, "tool_failed", message, action.action_id)

        return self._fail(
            state=state,
            failure_kind="max_steps_exceeded",
            failure_message="max_steps exceeded before submit_result",
            failed_action_ref=None,
        )

    def _runtime_requirements(self, invocation: AgentInvocation) -> _RuntimeRequirements | str:
        policy_ref = invocation.permission_policy.get("policy_ref")
        if not isinstance(policy_ref, str) or not policy_ref:
            return "permission_policy.policy_ref must be a non-empty string"
        max_steps = invocation.budgets.get("max_steps")
        max_parse_failures = invocation.budgets.get("max_parse_failures")
        max_observation_chars = invocation.budgets.get("max_observation_chars")
        max_wall_seconds = invocation.budgets.get("max_wall_seconds")
        if not isinstance(max_steps, int) or isinstance(max_steps, bool) or max_steps <= 0:
            return "budgets.max_steps must be a positive integer"
        if not isinstance(max_parse_failures, int) or isinstance(max_parse_failures, bool) or max_parse_failures < 0:
            return "budgets.max_parse_failures must be a non-negative integer"
        if not isinstance(max_observation_chars, int) or isinstance(max_observation_chars, bool) or max_observation_chars <= 0:
            return "budgets.max_observation_chars must be a positive integer"
        if (
            not isinstance(max_wall_seconds, int | float)
            or isinstance(max_wall_seconds, bool)
            or not math.isfinite(max_wall_seconds)
            or max_wall_seconds <= 0
        ):
            return "budgets.max_wall_seconds must be a finite positive number"
        if "submit_result" not in invocation.tools:
            return "invocation.tools must include submit_result"
        return _RuntimeRequirements(
            policy_ref=policy_ref,
            max_steps=max_steps,
            max_parse_failures=max_parse_failures,
            max_observation_chars=max_observation_chars,
            max_wall_seconds=float(max_wall_seconds),
        )

    def _read_runtime_clock(self) -> float | str:
        try:
            reading = self.dependencies.runtime_clock()
        except Exception as error:
            message = str(error) or error.__class__.__name__
            return f"runtime_clock failed: {message}"
        if not isinstance(reading, int | float) or isinstance(reading, bool) or not math.isfinite(reading):
            return "runtime_clock must return a finite number"
        return float(reading)

    def _check_wall_time_budget(
        self,
        started_at: float,
        requirements: _RuntimeRequirements,
        exceeded_message: str,
        failed_action_ref: str | None,
    ) -> tuple[str, str, str | None] | None:
        now_or_error = self._read_runtime_clock()
        if isinstance(now_or_error, str):
            return "invalid_invocation", now_or_error, failed_action_ref
        elapsed_seconds = now_or_error - started_at
        if elapsed_seconds < 0:
            return "invalid_invocation", "runtime_clock must be monotonic during AgentLoop.run", failed_action_ref
        if elapsed_seconds > requirements.max_wall_seconds:
            return "max_wall_seconds_exceeded", exceeded_message, failed_action_ref
        return None

    def _decide_permission(
        self,
        invocation: AgentInvocation,
        requirements: _RuntimeRequirements,
        action: AgentAction,
    ) -> PermissionDecision:
        if action.action.value not in invocation.tools:
            return PermissionDecision("deny", f"tool is not enabled: {action.action.value}", requirements.policy_ref)
        if action.action == AgentActionType.WEB_FETCH:
            return PermissionDecision("deny", "web_fetch is not implemented in P0-007", requirements.policy_ref)
        if action.action in _MUTATING_FILESYSTEM_ACTIONS:
            requested_path = action.input.get("path")
            decision = self.dependencies.filesystem_tools.guard.resolve_write_path(requested_path)
            if decision.decision == PathDecisionType.DENY:
                return PermissionDecision("deny", decision.reason, requirements.policy_ref)
        if action.action == AgentActionType.RUN_COMMAND:
            command_id = action.input.get("command_id")
            if not CommandPolicy.is_valid_command_id(command_id):
                return PermissionDecision("deny", "command_id must be a non-empty stable identifier", requirements.policy_ref)
            if self.dependencies.command_tools.policy.resolve(command_id) is None:
                return PermissionDecision("deny", "command_id is not declared in command policy", requirements.policy_ref)
        return PermissionDecision("allow", "action allowed by invocation policy", requirements.policy_ref)

    def _execute_tool_action(self, action: AgentAction) -> FileToolResult | CommandToolResult:
        if action.action in _FILESYSTEM_ACTIONS:
            return execute_filesystem_action(action, self.dependencies.filesystem_tools)
        if action.action == AgentActionType.RUN_COMMAND:
            return execute_command_action(action, self.dependencies.command_tools)
        raise AgentLoopError(f"unsupported executable action: {action.action.value}")

    def _record_tool_result(
        self,
        state: _RunState,
        requirements: _RuntimeRequirements,
        action: AgentAction,
        tool_attempt_id: str,
        result: FileToolResult | CommandToolResult,
    ) -> None:
        observation_document = self._tool_result_payload(result)
        visible, truncated = self._visible_observation(observation_document, requirements.max_observation_chars)
        observation_artifact = self.dependencies.artifact_writer.write_json(
            f"observations/{tool_attempt_id}.json",
            observation_document,
            truncated_in_observation=truncated,
        )
        state.artifacts.append(observation_artifact)
        state.observations.append(
            {
                "step": self._step_from_tool_attempt_id(tool_attempt_id),
                "action_id": action.action_id,
                "tool": result.tool,
                "ok": result.ok,
                "visible": visible,
                "truncated": truncated,
                "artifact": observation_artifact,
                "artifact_ref": observation_artifact["artifact_ref"],
            }
        )
        attempt = {
            "tool_attempt_id": tool_attempt_id,
            "action_id": action.action_id,
            "tool": result.tool,
            "ok": result.ok,
            "observation": observation_artifact,
        }
        if not result.ok:
            attempt["error_kind"] = result.error_kind
            attempt["error_message"] = result.error_message
        state.tool_attempts.append(attempt)

        if result.ok:
            self.dependencies.event_recorder.record_tool_attempt_completed(
                tool_attempt_id,
                action.action_id,
                result.tool,
                observation_artifact,
            )
            self._record_workspace_mutation_if_needed(state, action, tool_attempt_id, result)
            self._record_command_completed_if_needed(state, tool_attempt_id, result)
            return

        self.dependencies.event_recorder.record_tool_attempt_failed(
            tool_attempt_id,
            action.action_id,
            result.tool,
            EventError(
                result.error_kind or "tool_failed",
                result.error_message or "tool action failed",
                retryable=False,
                related_ref=action.action_id,
            ).to_payload(),
        )

    def _record_workspace_mutation_if_needed(
        self,
        state: _RunState,
        action: AgentAction,
        tool_attempt_id: str,
        result: FileToolResult | CommandToolResult,
    ) -> None:
        if not isinstance(result, FileToolResult) or action.action not in _MUTATING_FILESYSTEM_ACTIONS:
            return
        if result.path is None:
            raise AgentLoopError("mutating filesystem action must include a path")
        diff_text = result.data["diff"]
        if not isinstance(diff_text, str):
            raise AgentLoopError("workspace mutation diff must be a string")
        diff_artifact = self.dependencies.artifact_writer.write_text(f"diffs/{tool_attempt_id}.diff", diff_text)
        state.artifacts.append(diff_artifact)
        mutation = {
            "tool_attempt_id": tool_attempt_id,
            "action_id": action.action_id,
            "tool": result.tool,
            "path": result.path,
            "before_hash": result.data["before_hash"],
            "after_hash": result.data["after_hash"],
            "diff": diff_artifact,
        }
        state.workspace_mutations.append(mutation)
        self.dependencies.event_recorder.record_workspace_mutation_recorded(
            tool_attempt_id,
            result.path,
            result.data["before_hash"],
            result.data["after_hash"],
            diff_artifact,
        )

    def _record_command_completed_if_needed(
        self,
        state: _RunState,
        tool_attempt_id: str,
        result: FileToolResult | CommandToolResult,
    ) -> None:
        if not isinstance(result, CommandToolResult):
            return
        stdout_artifact = self.dependencies.artifact_writer.write_text(
            f"commands/{tool_attempt_id}.stdout.txt",
            result.data["stdout"],
            truncated_in_observation=result.data["stdout_truncated"],
        )
        stderr_artifact = self.dependencies.artifact_writer.write_text(
            f"commands/{tool_attempt_id}.stderr.txt",
            result.data["stderr"],
            truncated_in_observation=result.data["stderr_truncated"],
        )
        state.artifacts.extend([stdout_artifact, stderr_artifact])
        self.dependencies.event_recorder.record_command_completed(
            tool_attempt_id,
            result.command_id or "",
            result.data["exit_code"],
            stdout_artifact,
            stderr_artifact,
        )

    def _step_from_tool_attempt_id(self, tool_attempt_id: str) -> int:
        prefix = "tool_attempt_"
        if not tool_attempt_id.startswith(prefix):
            raise AgentLoopError("tool_attempt_id must use tool_attempt_<step> format")
        try:
            return int(tool_attempt_id.removeprefix(prefix))
        except ValueError as error:
            raise AgentLoopError("tool_attempt_id step must be an integer") from error

    def _tool_result_payload(self, result: FileToolResult | CommandToolResult) -> dict[str, Any]:
        payload = {
            "ok": result.ok,
            "tool": result.tool,
            "data": result.data,
        }
        if isinstance(result, FileToolResult):
            payload["path"] = result.path
        if isinstance(result, CommandToolResult):
            payload["command_id"] = result.command_id
        if not result.ok:
            payload["error_kind"] = result.error_kind
            payload["error_message"] = result.error_message
        return payload

    def _visible_observation(self, payload: dict[str, Any], max_chars: int) -> tuple[str, bool]:
        visible = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        if len(visible) <= max_chars:
            return visible, False
        return visible[:max_chars], True

    def _validate_result_submission(self, action: AgentAction) -> str | None:
        summary = action.input.get("summary")
        if not isinstance(summary, str) or summary == "":
            return "submit_result input.summary must be a non-empty string"
        produced_paths = action.input.get("produced_paths")
        if not isinstance(produced_paths, list) or any(not isinstance(path, str) for path in produced_paths):
            return "submit_result input.produced_paths must be a list of strings"
        evidence_refs = action.input.get("evidence_refs")
        if not isinstance(evidence_refs, list) or any(not isinstance(ref, str) for ref in evidence_refs):
            return "submit_result input.evidence_refs must be a list of strings"
        return None

    def _submit_result(self, state: _RunState, action: AgentAction) -> AgentRunResult:
        summary = action.input["summary"]
        produced_paths = action.input["produced_paths"]
        result_payload = {
            "summary": summary,
            "produced_paths": produced_paths,
            "evidence_refs": action.input["evidence_refs"],
        }
        result_artifact = self.dependencies.artifact_writer.write_json(f"results/{action.action_id}.json", result_payload)
        state.artifacts.append(result_artifact)
        self.dependencies.event_recorder.record_result_submitted(summary, produced_paths, [result_artifact])
        self.dependencies.event_recorder.record_run_completed(summary)
        return AgentRunResult(
            run_id=self.config.run_id,
            status=AgentRunStatus.COMPLETED,
            event_stream_ref=self.dependencies.event_recorder.event_stream_ref,
            events_hash=self.dependencies.event_recorder.events_hash(),
            tool_attempts=state.tool_attempts,
            workspace_mutations=state.workspace_mutations,
            artifacts=state.artifacts,
            summary=summary,
        )

    def _fail(
        self,
        state: _RunState,
        failure_kind: str,
        failure_message: str,
        failed_action_ref: str | None,
    ) -> AgentRunResult:
        self.dependencies.event_recorder.record_run_failed(
            EventError(
                kind=failure_kind,
                message=failure_message,
                retryable=False,
                related_ref=failed_action_ref,
            ).to_payload()
        )
        return AgentRunResult(
            run_id=self.config.run_id,
            status=AgentRunStatus.FAILED,
            event_stream_ref=self.dependencies.event_recorder.event_stream_ref,
            events_hash=self.dependencies.event_recorder.events_hash(),
            tool_attempts=state.tool_attempts,
            workspace_mutations=state.workspace_mutations,
            artifacts=state.artifacts,
            summary=f"Run failed closed: {failure_message}",
            failure_kind=failure_kind,
            failure_message=failure_message,
            failed_action_ref=failed_action_ref,
        )
