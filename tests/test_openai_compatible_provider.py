import json

import pytest

from atomic_agent.agent_loop import ProviderContext
from atomic_agent.models import AgentInvocation
from atomic_agent.providers.openai_compatible import (
    OpenAICompatibleProviderAdapter,
    OpenAICompatibleProviderError,
    OpenAICompatibleProviderOptions,
)


VALID_ACTION_TEXT = json.dumps(
    {
        "action_id": "step-0001",
        "action": "submit_result",
        "reason_summary": "Return a valid result.",
        "input": {"summary": "ok", "produced_paths": [], "evidence_refs": []},
    },
    sort_keys=True,
)


class FakeClock:
    def __init__(self, readings):
        self.readings = list(readings)
        self.last = self.readings[-1] if self.readings else 0.0

    def __call__(self):
        if self.readings:
            self.last = self.readings.pop(0)
        return self.last


class FakeDelta:
    def __init__(self, content):
        self.content = content


class FakeChoice:
    def __init__(self, content=None, finish_reason=None, has_delta=True):
        self.finish_reason = finish_reason
        if has_delta:
            self.delta = FakeDelta(content)


class FakeChunk:
    def __init__(self, choices):
        self.choices = choices


class FakeCompletions:
    def __init__(self, owner):
        self.owner = owner

    def create(self, **kwargs):
        self.owner.requests.append(kwargs)
        if self.owner.error is not None:
            raise self.owner.error
        return iter(self.owner.chunks)


class FakeChat:
    def __init__(self, owner):
        self.completions = FakeCompletions(owner)


class FakeOpenAIClient:
    def __init__(self, chunks=None, error=None):
        self.chunks = chunks or []
        self.error = error
        self.requests = []
        self.chat = FakeChat(self)


def chunk(content=None, finish_reason=None, has_delta=True):
    return FakeChunk([FakeChoice(content=content, finish_reason=finish_reason, has_delta=has_delta)])


def empty_choices_chunk():
    return FakeChunk([])


def options(**overrides):
    values = {
        "base_url": "https://provider.example/v1",
        "api_key": "secret-key",
        "model": "provider-model",
        "context_window_tokens": 400000,
        "max_output_tokens": 8192,
        "stream_idle_timeout_seconds": 30.0,
        "total_timeout_seconds": 3600.0,
        "temperature": None,
        "provider_label": "test-provider",
    }
    values.update(overrides)
    return OpenAICompatibleProviderOptions(**values)


def invocation(task="Create work/real-provider-output.txt, then submit the result."):
    return AgentInvocation(
        invocation_id="inv-real-provider-test",
        task=task,
        workspace_root="/tmp/atomic-agent-test/workspace",
        allowed_write_set=["work/"],
        tools=["write_file", "submit_result"],
        permission_policy={"policy_ref": "policy://tests/real-provider"},
        provider_profile={"provider": "openai-compatible", "model": "provider-model"},
        budgets={
            "max_steps": 4,
            "max_parse_failures": 1,
            "max_observation_chars": 10000,
            "max_wall_seconds": 3605.0,
        },
        output_requirements={"summary": True, "event_stream": True, "artifacts": True},
    )


def provider_context(task="Create work/real-provider-output.txt, then submit the result.", observations=()):
    return ProviderContext(invocation=invocation(task), step=1, observations=tuple(observations))


def adapter(client, clock=None, opts=None):
    return OpenAICompatibleProviderAdapter(
        options=opts or options(),
        client=client,
        clock=clock or FakeClock([0.0, 0.1, 0.2, 0.3]),
    )


def test_adapter_sends_streaming_chat_completion_request_without_temperature_when_none():
    client = FakeOpenAIClient(chunks=[chunk(VALID_ACTION_TEXT)])

    output = adapter(client).complete(provider_context())

    assert json.loads(output)["action"] == "submit_result"
    assert len(client.requests) == 1
    request = client.requests[0]
    assert request["stream"] is True
    assert request["model"] == "provider-model"
    assert request["max_tokens"] == 8192
    assert "temperature" not in request
    assert "messages" in request
    assert "secret-key" not in json.dumps(request["messages"], sort_keys=True)


def test_adapter_sends_temperature_when_configured():
    client = FakeOpenAIClient(chunks=[chunk(VALID_ACTION_TEXT)])
    opts = options(temperature=0.2)

    adapter(client, opts=opts).complete(provider_context())

    assert client.requests[0]["temperature"] == 0.2


def test_adapter_accumulates_streaming_delta_content():
    client = FakeOpenAIClient(chunks=[chunk(VALID_ACTION_TEXT[:20]), chunk(None), chunk(VALID_ACTION_TEXT[20:])])

    output = adapter(client).complete(provider_context())

    assert output == VALID_ACTION_TEXT


def test_adapter_prompt_is_task_agnostic_and_uses_invocation_task():
    client = FakeOpenAIClient(chunks=[chunk(VALID_ACTION_TEXT)])
    task = "Use write_file to create work/custom-from-task.txt, then submit_result."

    adapter(client).complete(provider_context(task=task))

    messages = client.requests[0]["messages"]
    serialized = json.dumps(messages, sort_keys=True)
    assert task in serialized
    assert "work/custom-from-task.txt" in serialized
    assert "work/real-provider-output.txt" not in serialized


def test_adapter_includes_observations_without_api_key():
    client = FakeOpenAIClient(chunks=[chunk(VALID_ACTION_TEXT)])
    observations = (
        {"step": 1, "tool": "write_file", "ok": True, "visible": "created", "artifact_ref": "artifact://obs"},
    )

    adapter(client).complete(provider_context(observations=observations))

    messages = client.requests[0]["messages"]
    serialized = json.dumps(messages, sort_keys=True)
    assert "created" in serialized
    assert "artifact://obs" in serialized
    assert "secret-key" not in serialized


def test_adapter_skips_empty_choices_chunks_as_stream_heartbeats():
    client = FakeOpenAIClient(chunks=[empty_choices_chunk(), chunk(VALID_ACTION_TEXT)])

    output = adapter(client).complete(provider_context())

    assert output == VALID_ACTION_TEXT


def test_adapter_rejects_stream_with_only_empty_choices_chunks():
    client = FakeOpenAIClient(chunks=[empty_choices_chunk()])

    with pytest.raises(OpenAICompatibleProviderError, match="provider stream completed without content"):
        adapter(client).complete(provider_context())


def test_adapter_rejects_missing_delta():
    client = FakeOpenAIClient(chunks=[chunk("ignored", has_delta=False)])

    with pytest.raises(OpenAICompatibleProviderError, match="stream chunk choice delta is required"):
        adapter(client).complete(provider_context())


def test_adapter_rejects_empty_stream_content():
    client = FakeOpenAIClient(chunks=[chunk(None)])

    with pytest.raises(OpenAICompatibleProviderError, match="provider stream completed without content"):
        adapter(client).complete(provider_context())


def test_adapter_rejects_length_finish_reason():
    client = FakeOpenAIClient(chunks=[chunk(VALID_ACTION_TEXT[:10], finish_reason="length")])

    with pytest.raises(OpenAICompatibleProviderError, match="provider response truncated by max_output_tokens"):
        adapter(client).complete(provider_context())


def test_adapter_wraps_sdk_exceptions_without_leaking_api_key():
    client = FakeOpenAIClient(error=RuntimeError("upstream exploded"))

    with pytest.raises(OpenAICompatibleProviderError) as raised:
        adapter(client).complete(provider_context())

    message = str(raised.value)
    assert "provider SDK call failed" in message
    assert "upstream exploded" in message
    assert "secret-key" not in message


def test_adapter_redacts_api_key_from_sdk_exception_messages():
    client = FakeOpenAIClient(error=RuntimeError("request failed with bearer secret-key"))

    with pytest.raises(OpenAICompatibleProviderError) as raised:
        adapter(client).complete(provider_context())

    message = str(raised.value)
    assert "secret-key" not in message
    assert "[REDACTED_API_KEY]" in message


def test_adapter_rejects_idle_timeout_between_chunks():
    client = FakeOpenAIClient(chunks=[chunk("{"), chunk("}")])
    clock = FakeClock([0.0, 0.1, 31.0])

    with pytest.raises(OpenAICompatibleProviderError, match="provider stream idle timeout exceeded"):
        adapter(client, clock=clock).complete(provider_context())


def test_adapter_rejects_total_timeout():
    client = FakeOpenAIClient(chunks=[chunk("{"), chunk("}")])
    clock = FakeClock([0.0, 0.1, 3601.0])

    with pytest.raises(OpenAICompatibleProviderError, match="provider total timeout exceeded"):
        adapter(client, clock=clock).complete(provider_context())


def test_options_reject_invalid_values():
    with pytest.raises(ValueError, match="max_output_tokens must be a positive integer"):
        OpenAICompatibleProviderOptions(
            base_url="https://provider.example/v1",
            api_key="secret-key",
            model="provider-model",
            context_window_tokens=400000,
            max_output_tokens=0,
            stream_idle_timeout_seconds=30.0,
            total_timeout_seconds=3600.0,
        )
