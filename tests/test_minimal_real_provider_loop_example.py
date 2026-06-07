import json
import math
import os
from pathlib import Path
import subprocess
import sys

from atomic_agent.models import AgentRunResult, AgentRunStatus


PYTHON = Path(sys.executable).resolve()
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
SECRET = "test-secret-key-should-not-leak"


def make_paths(tmp_path):
    base = tmp_path / "real-provider-example"
    return {
        "workspace": base / "workspace",
        "event_stream": base / "events" / "events.jsonl",
        "artifact_root": base / "artifacts",
        "result": base / "result.json",
    }


def cli_args(paths):
    return [
        "--run-id",
        "real_provider_example",
        "--workspace",
        str(paths["workspace"]),
        "--event-stream",
        str(paths["event_stream"]),
        "--artifact-root",
        str(paths["artifact_root"]),
        "--result",
        str(paths["result"]),
        "--base-url",
        "https://provider.example/v1",
        "--api-key-env",
        "ATOMIC_AGENT_TEST_REAL_PROVIDER_API_KEY",
        "--model",
        "provider-model",
        "--context-window-tokens",
        "400000",
        "--max-output-tokens",
        "8192",
        "--stream-idle-timeout-seconds",
        "30",
        "--total-timeout-seconds",
        "3600",
        "--max-steps",
        "4",
    ]


def run_example(paths, env_overrides=None, extra_args=None):
    env = dict(os.environ)
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(SRC_ROOT) if not existing_pythonpath else f"{SRC_ROOT}{os.pathsep}{existing_pythonpath}"
    if env_overrides:
        env.update(env_overrides)
    args = [str(PYTHON), "-m", "atomic_agent.examples.minimal_real_provider_loop", *cli_args(paths)]
    if extra_args:
        args.extend(extra_args)
    return subprocess.run(args, cwd=PROJECT_ROOT, env=env, text=True, capture_output=True, check=False)


def failed_result():
    return AgentRunResult(
        run_id="real_provider_example",
        status=AgentRunStatus.FAILED,
        event_stream_ref="artifact://real_provider_example/events.jsonl",
        events_hash="sha256:" + "0" * 64,
        tool_attempts=[],
        workspace_mutations=[],
        artifacts=[],
        summary="Run failed closed: injected provider failure",
        failure_kind="provider_failed",
        failure_message="injected provider failure",
        failed_action_ref="provider_turn_000001",
    )


def test_minimal_real_provider_loop_refuses_existing_result_file(tmp_path):
    paths = make_paths(tmp_path)
    paths["result"].parent.mkdir(parents=True)
    paths["result"].write_text("keep", encoding="utf-8")

    completed = run_example(paths, env_overrides={"ATOMIC_AGENT_TEST_REAL_PROVIDER_API_KEY": SECRET})

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert paths["result"].read_text(encoding="utf-8") == "keep"
    assert SECRET not in completed.stderr
    error_payload = json.loads(completed.stderr)
    assert error_payload["status"] == "failed"
    assert "result path already exists" in error_payload["error"]


def test_minimal_real_provider_loop_refuses_non_empty_artifact_root(tmp_path):
    paths = make_paths(tmp_path)
    paths["artifact_root"].mkdir(parents=True)
    (paths["artifact_root"] / "old.txt").write_text("old", encoding="utf-8")

    completed = run_example(paths, env_overrides={"ATOMIC_AGENT_TEST_REAL_PROVIDER_API_KEY": SECRET})

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert (paths["artifact_root"] / "old.txt").read_text(encoding="utf-8") == "old"
    assert SECRET not in completed.stderr
    error_payload = json.loads(completed.stderr)
    assert error_payload["status"] == "failed"
    assert "artifact root must be empty" in error_payload["error"]


def test_minimal_real_provider_loop_refuses_existing_workspace_output(tmp_path):
    paths = make_paths(tmp_path)
    output_path = paths["workspace"] / "work" / "real-provider-output.txt"
    output_path.parent.mkdir(parents=True)
    output_path.write_text("keep", encoding="utf-8")

    completed = run_example(paths, env_overrides={"ATOMIC_AGENT_TEST_REAL_PROVIDER_API_KEY": SECRET})

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert output_path.read_text(encoding="utf-8") == "keep"
    assert SECRET not in completed.stderr
    error_payload = json.loads(completed.stderr)
    assert error_payload["status"] == "failed"
    assert "workspace output path already exists" in error_payload["error"]


def test_minimal_real_provider_loop_requires_named_api_key_env(tmp_path):
    paths = make_paths(tmp_path)

    completed = run_example(paths, env_overrides={"ATOMIC_AGENT_TEST_REAL_PROVIDER_API_KEY": ""})

    assert completed.returncode == 2
    assert completed.stdout == ""
    error_payload = json.loads(completed.stderr)
    assert error_payload["status"] == "failed"
    assert "environment variable ATOMIC_AGENT_TEST_REAL_PROVIDER_API_KEY must be set" in error_payload["error"]


def test_minimal_real_provider_loop_rejects_non_finite_float_args(tmp_path):
    paths = make_paths(tmp_path)

    completed = run_example(
        paths,
        env_overrides={"ATOMIC_AGENT_TEST_REAL_PROVIDER_API_KEY": SECRET},
        extra_args=["--stream-idle-timeout-seconds", "nan"],
    )

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert "traceback" not in completed.stderr.lower()
    assert "must be a finite positive number" in completed.stderr


def test_minimal_real_provider_loop_budgets_wall_time_for_all_provider_steps(tmp_path):
    from atomic_agent.examples import minimal_real_provider_loop

    raw_paths = make_paths(tmp_path)
    paths = minimal_real_provider_loop.ExamplePaths(
        workspace=raw_paths["workspace"],
        event_stream=raw_paths["event_stream"],
        artifact_root=raw_paths["artifact_root"],
        result=raw_paths["result"],
    )
    provider_config = minimal_real_provider_loop.CliProviderConfig(
        base_url="https://provider.example/v1",
        api_key=SECRET,
        model="provider-model",
        context_window_tokens=400000,
        max_output_tokens=8192,
        stream_idle_timeout_seconds=30.0,
        total_timeout_seconds=3600.0,
        max_steps=4,
        temperature=None,
        provider_label=None,
    )

    invocation = minimal_real_provider_loop.build_invocation(paths, provider_config)

    assert invocation.budgets["max_wall_seconds"] == 3600.0 * 4 + 5.0
    assert math.isfinite(invocation.budgets["max_wall_seconds"])


def test_minimal_real_provider_loop_builds_write_only_loop_without_command_policy(tmp_path):
    from atomic_agent.examples import minimal_real_provider_loop

    raw_paths = make_paths(tmp_path)
    paths = minimal_real_provider_loop.ExamplePaths(
        workspace=raw_paths["workspace"],
        event_stream=raw_paths["event_stream"],
        artifact_root=raw_paths["artifact_root"],
        result=raw_paths["result"],
    )
    minimal_real_provider_loop.prepare_paths(paths)
    provider_config = minimal_real_provider_loop.CliProviderConfig(
        base_url="https://provider.example/v1",
        api_key=SECRET,
        model="provider-model",
        context_window_tokens=400000,
        max_output_tokens=8192,
        stream_idle_timeout_seconds=30.0,
        total_timeout_seconds=3600.0,
        max_steps=4,
        temperature=None,
        provider_label=None,
    )

    loop = minimal_real_provider_loop.build_loop("real_provider_example", paths, provider_config)

    assert loop.dependencies.command_tools is None


def test_minimal_real_provider_loop_writes_failed_result_without_leaking_api_key(tmp_path, monkeypatch, capsys):
    from atomic_agent.examples import minimal_real_provider_loop

    paths = make_paths(tmp_path)
    monkeypatch.setenv("ATOMIC_AGENT_TEST_REAL_PROVIDER_API_KEY", SECRET)
    monkeypatch.setattr(minimal_real_provider_loop, "run_example", lambda run_id, example_paths, provider_config: failed_result())

    return_code = minimal_real_provider_loop.main(cli_args(paths))

    captured = capsys.readouterr()
    assert return_code == 1
    assert SECRET not in captured.out
    assert SECRET not in captured.err
    assert paths["result"].exists()
    payload = json.loads(paths["result"].read_text(encoding="utf-8"))
    assert payload["status"] == "failed"
    assert SECRET not in json.dumps(payload, sort_keys=True)
    stdout_payload = json.loads(captured.out)
    assert stdout_payload["status"] == "failed"
    assert stdout_payload["workspace_output_path"] == str(paths["workspace"] / "work" / "real-provider-output.txt")
