import json
import os
from pathlib import Path
import re
import subprocess
import sys

from atomic_agent.evidence import build_evidence_summary
from atomic_agent.models import AgentRunResult


PYTHON = Path(sys.executable).resolve()
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")


def make_paths(tmp_path):
    base = tmp_path / "minimal-example"
    return {
        "workspace": base / "workspace",
        "event_stream": base / "events" / "events.jsonl",
        "artifact_root": base / "artifacts",
        "result": base / "result.json",
    }


def run_example(paths, env_overrides=None):
    env = dict(os.environ)
    if env_overrides:
        env.update(env_overrides)
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(SRC_ROOT) if not existing_pythonpath else f"{SRC_ROOT}{os.pathsep}{existing_pythonpath}"
    return subprocess.run(
        [
            str(PYTHON),
            "-m",
            "atomic_agent.examples.minimal_fake_loop",
            "--run-id",
            "minimal_example",
            "--workspace",
            str(paths["workspace"]),
            "--event-stream",
            str(paths["event_stream"]),
            "--artifact-root",
            str(paths["artifact_root"]),
            "--result",
            str(paths["result"]),
        ],
        cwd=PROJECT_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_minimal_fake_loop_example_runs_real_multistep_loop(tmp_path):
    paths = make_paths(tmp_path)

    completed = run_example(paths)

    assert completed.returncode == 0, completed.stderr
    assert completed.stderr == ""
    stdout_payload = json.loads(completed.stdout)
    assert '": "' in completed.stdout
    assert stdout_payload == {
        "status": "completed",
        "result_path": str(paths["result"].absolute()),
        "event_stream_path": str(paths["event_stream"].absolute()),
        "artifact_root": str(paths["artifact_root"].absolute()),
        "workspace_output_path": str((paths["workspace"] / "work" / "output.txt").absolute()),
    }

    assert (paths["workspace"] / "work" / "output.txt").read_text(encoding="utf-8") == "fixed"
    result_payload = json.loads(paths["result"].read_text(encoding="utf-8"))
    assert result_payload["run_id"] == "minimal_example"
    assert result_payload["status"] == "completed"
    assert result_payload["summary"] == "Created fixed output through a controlled fake provider loop."
    assert result_payload["event_stream_ref"] == "artifact://minimal_example/events.jsonl"
    assert SHA256_PATTERN.fullmatch(result_payload["events_hash"])
    assert [attempt["tool"] for attempt in result_payload["tool_attempts"]] == [
        "write_file",
        "run_command",
        "apply_patch",
        "run_command",
    ]
    assert [mutation["path"] for mutation in result_payload["workspace_mutations"]] == [
        "work/output.txt",
        "work/output.txt",
    ]

    events = read_jsonl(paths["event_stream"])
    event_types = [event["type"] for event in events]
    assert event_types[0] == "run.started"
    assert event_types[-2:] == ["result.submitted", "run.completed"]
    assert "provider.turn.completed" in event_types
    assert "action.parsed" in event_types
    assert "permission.decided" in event_types
    assert "tool.attempt.completed" in event_types
    assert event_types.count("workspace.mutation.recorded") == 2
    assert event_types.count("command.completed") == 2
    assert [event["sequence"] for event in events] == list(range(1, len(events) + 1))
    assert events[0]["previous_event_hash"] is None
    assert all(events[index]["previous_event_hash"] == events[index - 1]["event_hash"] for index in range(1, len(events)))

    command_events = [event for event in events if event["type"] == "command.completed"]
    assert [event["payload"]["exit_code"] for event in command_events] == [3, 0]
    assert all(event["payload"]["stdout"]["artifact_ref"].endswith(".stdout.txt") for event in command_events)
    assert all(event["payload"]["stderr"]["artifact_ref"].endswith(".stderr.txt") for event in command_events)

    expected_artifacts = [
        paths["artifact_root"] / "provider" / "turn_000001.txt",
        paths["artifact_root"] / "provider" / "turn_000005.txt",
        paths["artifact_root"] / "observations" / "tool_attempt_000002.json",
        paths["artifact_root"] / "diffs" / "tool_attempt_000001.diff",
        paths["artifact_root"] / "diffs" / "tool_attempt_000003.diff",
        paths["artifact_root"] / "commands" / "tool_attempt_000002.stdout.txt",
        paths["artifact_root"] / "commands" / "tool_attempt_000002.stderr.txt",
        paths["artifact_root"] / "commands" / "tool_attempt_000004.stdout.txt",
        paths["artifact_root"] / "commands" / "tool_attempt_000004.stderr.txt",
        paths["artifact_root"] / "results" / "step-0005.json",
    ]
    assert all(path.exists() for path in expected_artifacts)

    evidence_summary = build_evidence_summary(
        AgentRunResult.model_validate(result_payload),
        paths["event_stream"],
    )
    assert evidence_summary["event_stream"]["integrity"]["ok"] is True
    assert [command["exit_code"] for command in evidence_summary["command_results"]] == [3, 0]
    assert all(command["stdout"]["sha256"].startswith("sha256:") for command in evidence_summary["command_results"])
    assert all(command["stderr"]["sha256"].startswith("sha256:") for command in evidence_summary["command_results"])
    assert evidence_summary["source_inventory_lineage"]
    assert evidence_summary["source_inventory_lineage"][0]["path"] == "work/output.txt"
    assert evidence_summary["source_inventory_lineage"][0]["lineage_status"] == "traceable"
    assert [mutation["tool"] for mutation in evidence_summary["source_inventory_lineage"][0]["mutation_refs"]] == [
        "write_file",
        "apply_patch",
    ]
    assert evidence_summary["replay"]["status"] == "not_replayable"


def test_minimal_fake_loop_expands_tilde_paths(tmp_path):
    fake_home = tmp_path / "home"
    paths = {
        "workspace": "~/minimal-example/workspace",
        "event_stream": "~/minimal-example/events/events.jsonl",
        "artifact_root": "~/minimal-example/artifacts",
        "result": "~/minimal-example/result.json",
    }

    completed = run_example(paths, env_overrides={"HOME": str(fake_home)})

    assert completed.returncode == 0, completed.stderr
    stdout_payload = json.loads(completed.stdout)
    assert stdout_payload["workspace_output_path"] == str(fake_home / "minimal-example" / "workspace" / "work" / "output.txt")
    assert stdout_payload["result_path"] == str(fake_home / "minimal-example" / "result.json")
    assert (fake_home / "minimal-example" / "workspace" / "work" / "output.txt").read_text(encoding="utf-8") == "fixed"
    result_payload = json.loads((fake_home / "minimal-example" / "result.json").read_text(encoding="utf-8"))
    assert result_payload["status"] == "completed"


def test_minimal_fake_loop_refuses_to_overwrite_existing_result_file(tmp_path):
    paths = make_paths(tmp_path)
    paths["result"].parent.mkdir(parents=True)
    paths["result"].write_text("keep", encoding="utf-8")

    completed = run_example(paths)

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert paths["result"].read_text(encoding="utf-8") == "keep"
    error_payload = json.loads(completed.stderr)
    assert error_payload["status"] == "failed"
    assert "result path already exists" in error_payload["error"]


def test_minimal_fake_loop_refuses_non_empty_artifact_root(tmp_path):
    paths = make_paths(tmp_path)
    paths["artifact_root"].mkdir(parents=True)
    (paths["artifact_root"] / "old.txt").write_text("old", encoding="utf-8")

    completed = run_example(paths)

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert (paths["artifact_root"] / "old.txt").read_text(encoding="utf-8") == "old"
    error_payload = json.loads(completed.stderr)
    assert error_payload["status"] == "failed"
    assert "artifact root must be empty" in error_payload["error"]


def test_minimal_fake_loop_refuses_existing_workspace_output(tmp_path):
    paths = make_paths(tmp_path)
    output_path = paths["workspace"] / "work" / "output.txt"
    output_path.parent.mkdir(parents=True)
    output_path.write_text("keep", encoding="utf-8")

    completed = run_example(paths)

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert output_path.read_text(encoding="utf-8") == "keep"
    error_payload = json.loads(completed.stderr)
    assert error_payload["status"] == "failed"
    assert "workspace output path already exists" in error_payload["error"]
