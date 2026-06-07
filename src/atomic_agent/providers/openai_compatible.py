from __future__ import annotations

from dataclasses import dataclass
import json
import math
import time
from typing import Any, Callable

from atomic_agent.agent_loop import ProviderContext


class OpenAICompatibleProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class OpenAICompatibleProviderOptions:
    base_url: str
    api_key: str
    model: str
    context_window_tokens: int
    max_output_tokens: int
    stream_idle_timeout_seconds: float
    total_timeout_seconds: float
    temperature: float | None = None
    provider_label: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty_string(self.base_url, "base_url")
        _require_non_empty_string(self.api_key, "api_key")
        _require_non_empty_string(self.model, "model")
        _require_positive_int(self.context_window_tokens, "context_window_tokens")
        _require_positive_int(self.max_output_tokens, "max_output_tokens")
        _require_positive_number(self.stream_idle_timeout_seconds, "stream_idle_timeout_seconds")
        _require_positive_number(self.total_timeout_seconds, "total_timeout_seconds")
        if self.stream_idle_timeout_seconds > self.total_timeout_seconds:
            raise ValueError("stream_idle_timeout_seconds must be less than or equal to total_timeout_seconds")
        if self.temperature is not None:
            _require_finite_number(self.temperature, "temperature")
        if self.provider_label is not None:
            _require_non_empty_string(self.provider_label, "provider_label")


class OpenAICompatibleProviderAdapter:
    def __init__(
        self,
        options: OpenAICompatibleProviderOptions,
        client: Any | None = None,
        clock: Callable[[], float] | None = None,
    ):
        self.options = options
        self._client = client
        self._clock = clock or time.monotonic

    def complete(self, context: ProviderContext) -> str:
        started_at = self._read_clock("before provider request")
        last_chunk_at = started_at
        request = self._request_payload(context)
        try:
            stream = self._client_or_create().chat.completions.create(**request)
        except Exception as error:
            raise OpenAICompatibleProviderError(
                f"provider SDK call failed: {_safe_error_message(error, self.options.api_key)}"
            ) from error

        parts: list[str] = []
        try:
            for chunk in stream:
                now = self._read_clock("while reading provider stream")
                self._check_total_timeout(started_at, now)
                self._check_idle_timeout(last_chunk_at, now)
                last_chunk_at = now
                parts.append(self._content_from_chunk(chunk))
        except OpenAICompatibleProviderError:
            raise
        except Exception as error:
            raise OpenAICompatibleProviderError(f"provider stream read failed: {_safe_error_message(error, self.options.api_key)}") from error

        output = "".join(parts)
        if output == "":
            raise OpenAICompatibleProviderError("provider stream completed without content")
        return output

    def _client_or_create(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            from openai import OpenAI
        except ImportError as error:
            raise OpenAICompatibleProviderError(
                "openai package is required for OpenAICompatibleProviderAdapter; install with `python -m pip install \".[real-provider]\"`"
            ) from error
        return OpenAI(base_url=self.options.base_url, api_key=self.options.api_key, timeout=self.options.total_timeout_seconds)

    def _request_payload(self, context: ProviderContext) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.options.model,
            "messages": self._messages(context),
            "stream": True,
            "max_tokens": self.options.max_output_tokens,
        }
        if self.options.temperature is not None:
            payload["temperature"] = self.options.temperature
        return payload

    def _messages(self, context: ProviderContext) -> list[dict[str, str]]:
        invocation = context.invocation
        protocol = {
            "action_envelope": {
                "action_id": "stable unique string",
                "action": "one enabled tool name",
                "reason_summary": "short reason",
                "input": "tool-specific object",
            },
            "rules": [
                "Return exactly one JSON object and no markdown.",
                "Do not wrap the JSON in code fences.",
                "Do not return shell command strings.",
                "Use run_command only with command_id.",
                "Only request tools listed in invocation.tools.",
                "Use submit_result when the task is complete.",
            ],
        }
        task_payload = {
            "task": invocation.task,
            "step": context.step,
            "tools": invocation.tools,
            "allowed_write_set": invocation.allowed_write_set,
            "output_requirements": invocation.output_requirements,
            "provider_capabilities": {
                "provider": "openai-compatible",
                "provider_label": self.options.provider_label,
                "model": self.options.model,
                "context_window_tokens": self.options.context_window_tokens,
                "max_output_tokens": self.options.max_output_tokens,
            },
            "previous_observations": list(context.observations),
        }
        return [
            {"role": "system", "content": json.dumps(protocol, sort_keys=True, ensure_ascii=False)},
            {"role": "user", "content": json.dumps(task_payload, sort_keys=True, ensure_ascii=False)},
        ]

    def _content_from_chunk(self, chunk: Any) -> str:
        choices = getattr(chunk, "choices", None)
        if not isinstance(choices, list) or not choices:
            raise OpenAICompatibleProviderError("stream chunk choices must not be empty")
        choice = choices[0]
        finish_reason = getattr(choice, "finish_reason", None)
        if finish_reason == "length":
            raise OpenAICompatibleProviderError("provider response truncated by max_output_tokens")
        delta = getattr(choice, "delta", None)
        if delta is None:
            raise OpenAICompatibleProviderError("stream chunk choice delta is required")
        content = getattr(delta, "content", None)
        if content is None:
            return ""
        if not isinstance(content, str):
            raise OpenAICompatibleProviderError("stream chunk delta content must be a string or None")
        return content

    def _read_clock(self, context: str) -> float:
        try:
            reading = self._clock()
        except Exception as error:
            raise OpenAICompatibleProviderError(f"provider timeout clock failed {context}: {_safe_error_message(error)}") from error
        if not isinstance(reading, int | float) or isinstance(reading, bool) or not math.isfinite(reading):
            raise OpenAICompatibleProviderError("provider timeout clock must return a finite number")
        return float(reading)

    def _check_idle_timeout(self, previous_at: float, now: float) -> None:
        if now < previous_at:
            raise OpenAICompatibleProviderError("provider timeout clock must be monotonic")
        if now - previous_at > self.options.stream_idle_timeout_seconds:
            raise OpenAICompatibleProviderError("provider stream idle timeout exceeded")

    def _check_total_timeout(self, started_at: float, now: float) -> None:
        if now < started_at:
            raise OpenAICompatibleProviderError("provider timeout clock must be monotonic")
        if now - started_at > self.options.total_timeout_seconds:
            raise OpenAICompatibleProviderError("provider total timeout exceeded")


def _require_non_empty_string(value: object, field_name: str) -> None:
    if not isinstance(value, str) or value == "":
        raise ValueError(f"{field_name} must be a non-empty string")


def _require_positive_int(value: object, field_name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer")


def _require_positive_number(value: object, field_name: str) -> None:
    _require_finite_number(value, field_name)
    if float(value) <= 0:
        raise ValueError(f"{field_name} must be a positive number")


def _require_finite_number(value: object, field_name: str) -> None:
    if not isinstance(value, int | float) or isinstance(value, bool) or not math.isfinite(value):
        raise ValueError(f"{field_name} must be a finite number")


def _safe_error_message(error: Exception, api_key: str | None = None) -> str:
    message = str(error) or error.__class__.__name__
    sanitized = message.replace("\n", " ")
    if api_key:
        sanitized = sanitized.replace(api_key, "[REDACTED_API_KEY]")
    return sanitized
