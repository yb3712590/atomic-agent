import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from atomic_agent.evidence import build_evidence_summary, verify_event_stream
from atomic_agent.models import AgentRunResult


PYTHON = Path(sys.executable).resolve()
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
REQUIRED_ENV = (
    "ATOMIC_AGENT_REAL_PROVIDER_BASE_URL",
    "ATOMIC_AGENT_REAL_PROVIDER_API_KEY",
    "ATOMIC_AGENT_REAL_PROVIDER_MODEL",
)


def require_real_provider_enabled():
    if os.environ.get("ATOMIC_AGENT_RUN_REAL_PROVIDER") != "1":
        pytest.skip("set ATOMIC_AGENT_RUN_REAL_PROVIDER=1 to run real provider gate")
    missing = [name for name in REQUIRED_ENV if not os.environ.get(name)]
    if missing:
        pytest.fail("missing required real provider test configuration: " + ", ".join(missing))


def env_value(name, default):
    return os.environ.get(name, default)


def run_real_provider_gate(tmp_path):
    base = tmp_path / "real-provider-gate"
    workspace = base / "workspace"
    event_stream = base / "events" / "events.jsonl"
    artifact_root = base / "artifacts"
    result = base / "result.json"
    env = dict(os.environ)
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(SRC_ROOT) if not existing_pythonpath else f"{SRC_ROOT}{os.pathsep}{existing_pythonpath}"
    env["ATOMIC_AGENT_REAL_PROVIDER_GATE_API_KEY"] = env["ATOMIC_AGENT_REAL_PROVIDER_API_KEY"]
    args = [
        str(PYTHON),
        "-m",
        "atomic_agent.examples.minimal_real_provider_loop",
        "--run-id",
        "real_provider_gate",
        "--workspace",
        str(workspace),
        "--event-stream",
        str(event_stream),
        "--artifact-root",
        str(artifact_root),
        "--result",
        str(result),
        "--base-url",
        env["ATOMIC_AGENT_REAL_PROVIDER_BASE_URL"],
        "--api-key-env",
        "ATOMIC_AGENT_REAL_PROVIDER_GATE_API_KEY",
        "--model",
        env["ATOMIC_AGENT_REAL_PROVIDER_MODEL"],
        "--context-window-tokens",
        env_value("ATOMIC_AGENT_REAL_PROVIDER_CONTEXT_WINDOW_TOKENS", "400000"),
        "--max-output-tokens",
        env_value("ATOMIC_AGENT_REAL_PROVIDER_MAX_OUTPUT_TOKENS", "8192"),
        "--stream-idle-timeout-seconds",
        env_value("ATOMIC_AGENT_REAL_PROVIDER_STREAM_IDLE_TIMEOUT_SECONDS", "30"),
        "--total-timeout-seconds",
        env_value("ATOMIC_AGENT_REAL_PROVIDER_TOTAL_TIMEOUT_SECONDS", "3600"),
        "--max-steps",
        env_value("ATOMIC_AGENT_REAL_PROVIDER_MAX_STEPS", "4"),
    ]
    temperature = os.environ.get("ATOMIC_AGENT_REAL_PROVIDER_TEMPERATURE")
    if temperature is not None:
        args.extend(["--temperature", temperature])
    provider_label = os.environ.get("ATOMIC_AGENT_REAL_PROVIDER_LABEL")
    if provider_label:
        args.extend(["--provider-label", provider_label])
    completed = subprocess.run(args, cwd=PROJECT_ROOT, env=env, text=True, capture_output=True, check=False)
    return completed, result, event_stream


def read_events(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def event_types(events):
    return [event["type"] for event in events]


def failure_text(completed, result):
    pieces = [completed.stdout, completed.stderr]
    if result.exists():
        pieces.append(result.read_text(encoding="utf-8"))
    return "\n".join(pieces)


def assert_not_environment_or_harness_failure(completed, result):
    text = failure_text(completed, result).lower()
    rejected_fragments = (
        "environment variable",
        "api key",
        "apikey",
        "auth",
        "unauthorized",
        "forbidden",
        "dns",
        "connection",
        "connectivity",
        "network",
        "base url",
        "idle timeout",
        "total timeout",
    )
    matches = [fragment for fragment in rejected_fragments if fragment in text]
    assert not matches, "environment/provider availability failure cannot pass real provider gate: " + ", ".join(matches)


@pytest.mark.real_provider
def test_real_provider_minimal_integration_gate(tmp_path):
    require_real_provider_enabled()

    completed, result_path, event_stream_path = run_real_provider_gate(tmp_path)

    assert result_path.exists(), completed.stderr
    assert event_stream_path.exists(), completed.stderr
    result_payload = json.loads(result_path.read_text(encoding="utf-8"))
    result = AgentRunResult.model_validate(result_payload)
    integrity = verify_event_stream(event_stream_path, expected_events_hash=result.events_hash)
    assert integrity["ok"] is True, integrity
    events = read_events(event_stream_path)
    types = event_types(events)
    assert types[-1] in {"run.completed", "run.failed"}

    if "provider.turn.completed" in types and "action.parsed" in types:
        if result.status.value == "completed":
            summary = build_evidence_summary(result, event_stream_path)
            assert summary["event_stream"]["integrity"]["ok"] is True
            assert summary["provider_attempts"]
            assert completed.returncode == 0
            lineage = summary["source_inventory_lineage"]
            if lineage:
                assert lineage[0]["lineage_status"] in {"traceable", "missing_workspace_mutation"}
            return

        assert result.status.value == "failed"
        assert completed.returncode == 1
        assert_not_environment_or_harness_failure(completed, result_path)
        return

    if "provider.turn.failed" in types or "action.rejected" in types:
        assert result.status.value == "failed"
        assert completed.returncode == 1
        assert_not_environment_or_harness_failure(completed, result_path)
        text = failure_text(completed, result_path).lower()
        accepted_fragments = (
            "provider response",
            "provider stream completed without content",
            "stream chunk",
            "truncated by max_output_tokens",
            "action parse",
            "invalid json",
            "action_parse_failed",
        )
        assert any(fragment in text for fragment in accepted_fragments), text
        return

    pytest.fail("real provider gate did not reach an accepted Outcome A, B, or C")
