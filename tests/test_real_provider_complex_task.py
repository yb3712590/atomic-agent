from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import sys
import time

import pytest

from atomic_agent.agent_loop import AgentLoop, AgentLoopConfig, AgentLoopDependencies
from atomic_agent.artifacts import ArtifactWriter, ArtifactWriterConfig
from atomic_agent.command_tools import CommandPolicy, CommandSpec, CommandToolConfig, CommandTools
from atomic_agent.evidence import build_evidence_summary, verify_event_stream
from atomic_agent.event_recorder import EventRecorder, EventRecorderConfig
from atomic_agent.filesystem_tools import FilesystemToolConfig, FilesystemTools
from atomic_agent.models import AgentInvocation, AgentRunStatus
from atomic_agent.path_guard import WorkspacePathGuard
from atomic_agent.providers.openai_compatible import OpenAICompatibleProviderAdapter, OpenAICompatibleProviderOptions


PYTHON = Path(sys.executable).resolve()
REQUIRED_ENV = (
    "ATOMIC_AGENT_REAL_PROVIDER_BASE_URL",
    "ATOMIC_AGENT_REAL_PROVIDER_API_KEY",
    "ATOMIC_AGENT_REAL_PROVIDER_MODEL",
)
OPTIONAL_PROVIDER_ENV = (
    "ATOMIC_AGENT_REAL_PROVIDER_CONTEXT_WINDOW_TOKENS",
    "ATOMIC_AGENT_REAL_PROVIDER_MAX_OUTPUT_TOKENS",
    "ATOMIC_AGENT_REAL_PROVIDER_STREAM_IDLE_TIMEOUT_SECONDS",
    "ATOMIC_AGENT_REAL_PROVIDER_TOTAL_TIMEOUT_SECONDS",
    "ATOMIC_AGENT_REAL_PROVIDER_TEMPERATURE",
    "ATOMIC_AGENT_REAL_PROVIDER_LABEL",
    "ATOMIC_AGENT_REAL_PROVIDER_REASONING_EFFORT",
    "ATOMIC_AGENT_REAL_PROVIDER_TOP_P",
    "ATOMIC_AGENT_REAL_PROVIDER_PRESENCE_PENALTY",
    "ATOMIC_AGENT_REAL_PROVIDER_FREQUENCY_PENALTY",
    "ATOMIC_AGENT_REAL_PROVIDER_SEED",
    "ATOMIC_AGENT_REAL_PROVIDER_STOP",
    "ATOMIC_AGENT_REAL_PROVIDER_RESPONSE_FORMAT_JSON",
    "ATOMIC_AGENT_REAL_PROVIDER_STREAM_OPTIONS_JSON",
    "ATOMIC_AGENT_REAL_PROVIDER_SERVICE_TIER",
    "ATOMIC_AGENT_REAL_PROVIDER_USER",
)


def clear_optional_provider_env(monkeypatch):
    for name in OPTIONAL_PROVIDER_ENV:
        monkeypatch.delenv(name, raising=False)


def require_real_provider_complex_task_enabled():
    if os.environ.get("ATOMIC_AGENT_RUN_REAL_PROVIDER_COMPLEX_TASK") != "1":
        pytest.skip("set ATOMIC_AGENT_RUN_REAL_PROVIDER_COMPLEX_TASK=1 to run complex real provider gate")
    missing = [name for name in REQUIRED_ENV if not os.environ.get(name)]
    if missing:
        pytest.fail("missing required complex real provider test configuration: " + ", ".join(missing))


def env_value(name, default):
    return os.environ.get(name, default)


def env_int(name, default):
    return int(env_value(name, default))


def env_float_or_none(name, default):
    raw = os.environ.get(name, default)
    if raw in (None, ""):
        return None
    return float(raw)


def env_int_or_none(name, default):
    raw = os.environ.get(name, default)
    if raw in (None, ""):
        return None
    return int(raw)


def env_json_object_or_none(name, default):
    raw = os.environ.get(name, default)
    if raw in (None, ""):
        return None
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError(f"{name} must be a JSON object or empty string")
    return parsed


def env_stop_or_none(name, default):
    raw = os.environ.get(name, default)
    if raw in (None, ""):
        return None
    parsed = json.loads(raw)
    if not isinstance(parsed, list) or not parsed or any(not isinstance(item, str) or item == "" for item in parsed):
        raise ValueError(f"{name} must be a non-empty JSON array of non-empty strings or empty string")
    return tuple(parsed)


def provider_options():
    return OpenAICompatibleProviderOptions(
        base_url=os.environ["ATOMIC_AGENT_REAL_PROVIDER_BASE_URL"],
        api_key=os.environ["ATOMIC_AGENT_REAL_PROVIDER_API_KEY"],
        model=os.environ["ATOMIC_AGENT_REAL_PROVIDER_MODEL"],
        context_window_tokens=env_int("ATOMIC_AGENT_REAL_PROVIDER_CONTEXT_WINDOW_TOKENS", "400000"),
        max_output_tokens=env_int("ATOMIC_AGENT_REAL_PROVIDER_MAX_OUTPUT_TOKENS", "128000"),
        stream_idle_timeout_seconds=float(env_value("ATOMIC_AGENT_REAL_PROVIDER_STREAM_IDLE_TIMEOUT_SECONDS", "30")),
        total_timeout_seconds=float(env_value("ATOMIC_AGENT_REAL_PROVIDER_TOTAL_TIMEOUT_SECONDS", "600")),
        temperature=env_float_or_none("ATOMIC_AGENT_REAL_PROVIDER_TEMPERATURE", ""),
        provider_label=os.environ.get("ATOMIC_AGENT_REAL_PROVIDER_LABEL") or None,
        reasoning_effort=os.environ.get("ATOMIC_AGENT_REAL_PROVIDER_REASONING_EFFORT") or "high",
        top_p=env_float_or_none("ATOMIC_AGENT_REAL_PROVIDER_TOP_P", ""),
        presence_penalty=env_float_or_none("ATOMIC_AGENT_REAL_PROVIDER_PRESENCE_PENALTY", ""),
        frequency_penalty=env_float_or_none("ATOMIC_AGENT_REAL_PROVIDER_FREQUENCY_PENALTY", ""),
        seed=env_int_or_none("ATOMIC_AGENT_REAL_PROVIDER_SEED", ""),
        stop=env_stop_or_none("ATOMIC_AGENT_REAL_PROVIDER_STOP", ""),
        response_format=env_json_object_or_none("ATOMIC_AGENT_REAL_PROVIDER_RESPONSE_FORMAT_JSON", ""),
        stream_options=env_json_object_or_none("ATOMIC_AGENT_REAL_PROVIDER_STREAM_OPTIONS_JSON", ""),
        service_tier=os.environ.get("ATOMIC_AGENT_REAL_PROVIDER_SERVICE_TIER") or None,
        user=os.environ.get("ATOMIC_AGENT_REAL_PROVIDER_USER") or None,
    )


FORBIDDEN_FIXTURE_PATHS = (
    "work/data/orders.json",
    "work/data/users.json",
    "work/tests/test_report.py",
    "work/expected/report.txt",
)

EXPECTED_REPORT = """Customer Revenue Report
Ada Lovelace: orders=2 total=17.75
Grace Hopper: orders=1 total=20.00
Katherine Johnson: orders=1 total=7.25
Grand Total: 45.00
"""

BROKEN_REPORT_PY = '''from __future__ import annotations

import json
from pathlib import Path


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_users(path: Path):
    return load_json(path)


def load_orders(path: Path):
    return load_json(path)


def summarize_orders(users, orders):
    names_by_id = {user["id"]: user["id"] for user in users}
    totals_by_user = {}
    counts_by_user = {}
    for order in orders:
        user_id = order["user_id"]
        counts_by_user[user_id] = counts_by_user.get(user_id, 0) + 1
        totals_by_user[user_id] = totals_by_user.get(user_id, 0.0) + int(float(order["total"]))
    return [
        (names_by_id.get(user_id, user_id), counts_by_user[user_id], totals_by_user[user_id])
        for user_id in totals_by_user
    ]


def render_report(users, orders):
    rows = summarize_orders(users, orders)
    lines = ["Customer Revenue Report"]
    for name, count, total in rows:
        lines.append(f"{name}: orders={count} total={total:.2f}")
    lines.append(f"Grand Total: {sum(total for _, _, total in rows):.2f}")
    return "\\n".join(lines) + "\\n"


def write_report(users_path: Path, orders_path: Path, output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_report(load_users(users_path), load_orders(orders_path)), encoding="utf-8")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    write_report(root / "data" / "users.json", root / "data" / "orders.json", root / "output" / "report.txt")
    print("report written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

VALIDATOR_PY = '''from __future__ import annotations

from pathlib import Path
import sys


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    expected = root / "expected" / "report.txt"
    actual = root / "output" / "report.txt"
    if not actual.exists():
        print("missing work/output/report.txt", file=sys.stderr)
        return 2
    expected_text = expected.read_text(encoding="utf-8")
    actual_text = actual.read_text(encoding="utf-8")
    if actual_text != expected_text:
        print("report content does not match expected output", file=sys.stderr)
        print("expected:", file=sys.stderr)
        print(expected_text, file=sys.stderr)
        print("actual:", file=sys.stderr)
        print(actual_text, file=sys.stderr)
        return 3
    print("report validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

TEST_REPORT_PY = '''from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from report import load_orders, load_users, render_report, write_report

DATA = ROOT / "data"
EXPECTED = (ROOT / "expected" / "report.txt").read_text(encoding="utf-8")


def rendered_report():
    return render_report(load_users(DATA / "users.json"), load_orders(DATA / "orders.json"))


def test_report_matches_expected_output():
    assert rendered_report() == EXPECTED


def test_cancelled_orders_are_excluded_from_totals():
    output = rendered_report()
    assert "orders=3" not in output
    assert "117.74" not in output
    assert "Grand Total: 45.00" in output


def test_customer_names_and_sorting_are_stable():
    lines = rendered_report().splitlines()
    assert lines == [
        "Customer Revenue Report",
        "Ada Lovelace: orders=2 total=17.75",
        "Grace Hopper: orders=1 total=20.00",
        "Katherine Johnson: orders=1 total=7.25",
        "Grand Total: 45.00",
    ]


def test_write_report_creates_expected_file(tmp_path):
    output_path = tmp_path / "report.txt"
    write_report(DATA / "users.json", DATA / "orders.json", output_path)
    assert output_path.read_text(encoding="utf-8") == EXPECTED
'''


def write_text(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def setup_complex_workspace(workspace):
    work = workspace / "work"
    for relative in ("data", "src", "tests", "expected", "output"):
        (work / relative).mkdir(parents=True, exist_ok=True)

    write_text(
        work / "README.md",
        """# Repair Task

This workspace contains a small broken customer revenue report generator.
Fix the implementation in `work/src/report.py`, produce `work/output/report.txt`,
and write `work/output/repair-summary.md`.

Do not modify `work/data/`, `work/tests/`, or `work/expected/`.
""",
    )
    write_text(
        work / "data" / "users.json",
        json.dumps(
            [
                {"id": "u1", "name": "Ada Lovelace"},
                {"id": "u2", "name": "Grace Hopper"},
                {"id": "u3", "name": "Katherine Johnson"},
            ],
            sort_keys=True,
            indent=2,
        )
        + "\n",
    )
    write_text(
        work / "data" / "orders.json",
        json.dumps(
            [
                {"id": "o-001", "user_id": "u2", "status": "paid", "total": "20.00"},
                {"id": "o-002", "user_id": "u1", "status": "paid", "total": "12.25"},
                {"id": "o-003", "user_id": "u1", "status": "cancelled", "total": "99.99"},
                {"id": "o-004", "user_id": "u1", "status": "paid", "total": "5.50"},
                {"id": "o-005", "user_id": "u3", "status": "paid", "total": "7.25"},
            ],
            sort_keys=True,
            indent=2,
        )
        + "\n",
    )
    write_text(work / "expected" / "report.txt", EXPECTED_REPORT)
    write_text(work / "src" / "report.py", BROKEN_REPORT_PY)
    write_text(work / "src" / "validator.py", VALIDATOR_PY)
    write_text(work / "tests" / "test_report.py", TEST_REPORT_PY)
    return forbidden_fixture_hashes(workspace)


def sha256_file(path):
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def forbidden_fixture_hashes(workspace):
    return {relative: sha256_file(workspace / relative) for relative in FORBIDDEN_FIXTURE_PATHS}


def make_path_guard(workspace):
    return WorkspacePathGuard(workspace, allowed_write_set=["work/src/", "work/output/"])


def build_complex_command_policy(guard):
    return CommandTools(
        guard,
        CommandPolicy(
            {
                "run-tests": CommandSpec(
                    argv=(str(PYTHON), "-m", "pytest", "work/tests/test_report.py", "-q"),
                    timeout_seconds=20.0,
                    allow_network=False,
                ),
                "validate-report": CommandSpec(
                    argv=(str(PYTHON), "work/src/validator.py"),
                    timeout_seconds=10.0,
                    allow_network=False,
                ),
            }
        ),
        CommandToolConfig(default_timeout_seconds=10.0, max_timeout_seconds=30.0, max_output_bytes=20000),
    )


COMPLEX_GATE_TOOLS = [
    "list_files",
    "read_file",
    "search_files",
    "apply_patch",
    "write_file",
    "run_command",
    "submit_result",
]

REQUIRED_PRODUCED_PATHS = [
    "work/src/report.py",
    "work/output/report.txt",
    "work/output/repair-summary.md",
]


def provider_config_summary(options):
    return {
        "base_url_configured": bool(options.base_url),
        "api_key_configured": bool(options.api_key),
        "model": options.model,
        "provider_label": options.provider_label,
        "context_window_tokens": options.context_window_tokens,
        "max_output_tokens": options.max_output_tokens,
        "stream_idle_timeout_seconds": options.stream_idle_timeout_seconds,
        "total_timeout_seconds": options.total_timeout_seconds,
        "temperature": options.temperature,
        "reasoning_effort": options.reasoning_effort,
        "top_p": options.top_p,
        "presence_penalty": options.presence_penalty,
        "frequency_penalty": options.frequency_penalty,
        "seed": options.seed,
        "stop_configured": options.stop is not None,
        "response_format_configured": options.response_format is not None,
        "stream_options_configured": options.stream_options is not None,
        "service_tier": options.service_tier,
        "user": options.user,
    }


def build_invocation(workspace, options):
    max_steps = env_int("ATOMIC_AGENT_REAL_PROVIDER_MAX_STEPS", "100")
    task = (
        "You are repairing a small Python report project under work/. "
        "Return exactly one AgentAction JSON object per turn, with no markdown and no code fences. "
        "Every action object must include action_id, action, reason_summary, and input. "
        "Do not concatenate two JSON objects; each provider turn must contain exactly one JSON object and nothing after it. "
        "Use list_files, read_file, and search_files to understand the project. "
        "Tool input schemas: "
        'list_files: {"path":"work","recursive":true}; '
        'read_file: {"path":"work/src/report.py"}; '
        'search_files: {"query":"report","path":"work","mode":"content","max_matches":20}; '
        'apply_patch: {"path":"work/src/report.py","old_text":"exact existing text","new_text":"replacement text","replace_all":false}; '
        'write_file: {"path":"work/output/report.txt","content":"file content"}; '
        'run_command: {"command_id":"run-tests"} or {"command_id":"validate-report"}; '
        'submit_result: {"summary":"...","produced_paths":["work/src/report.py","work/output/report.txt","work/output/repair-summary.md"],"evidence_refs":[]}. '
        "search_files input must use query, optional path, optional mode, and optional max_matches. "
        "search_files mode must be content or name; use content when searching file text. "
        "Do not use a pattern key for search_files. "
        "For multi-line source repairs, prefer write_file with the complete corrected file content. "
        "Use apply_patch only for short exact replacements where old_text and new_text are small. "
        "You must use search_files before the final submit_result so the event stream shows search-based investigation. "
        "The completed run must include at least two of search_files, apply_patch, and write_file as successful tools. "
        "You must run run_command with command_id run-tests at least once before making a final submission, "
        "then repair the project so the tests pass. "
        "After repairing, run run_command with command_id run-tests again and run command_id validate-report. "
        "Only modify files under work/src/ and work/output/. Do not modify work/tests/, work/expected/, or work/data/. "
        "The final submit_result input.produced_paths must be exactly "
        '["work/src/report.py", "work/output/report.txt", "work/output/repair-summary.md"]. '
        "Write work/output/report.txt with the final report content, and write work/output/repair-summary.md with a concise repair summary. "
        "When the task is complete, use submit_result with a non-empty summary and evidence_refs as a list of strings. "
        "Do not use tools that are not listed in invocation.tools."
    )
    return AgentInvocation(
        invocation_id="inv_real_provider_complex_task",
        task=task,
        workspace_root=str(workspace),
        allowed_write_set=["work/src/", "work/output/"],
        tools=COMPLEX_GATE_TOOLS,
        permission_policy={"policy_ref": "policy://tests/real-provider-complex-task"},
        provider_profile=options.to_provider_profile(),
        budgets={
            "max_steps": max_steps,
            "max_parse_failures": 1,
            "max_observation_chars": 30000,
            "max_wall_seconds": options.total_timeout_seconds * max_steps + 5.0,
        },
        output_requirements={"summary": True, "event_stream": True, "artifacts": True},
        metadata={
            "test": "real_provider_complex_task",
            "provider_config_summary": provider_config_summary(options),
        },
    )


@dataclass(frozen=True)
class ComplexGateRun:
    result: object
    event_stream: Path
    artifact_root: Path
    workspace: Path
    original_forbidden_hashes: dict[str, str]


def utc_timestamp():
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def make_filesystem_tools(guard):
    return FilesystemTools(
        guard,
        FilesystemToolConfig(
            default_read_limit=20000,
            max_read_limit=80000,
            default_max_entries=300,
            max_entries_limit=1500,
            default_max_matches=100,
            max_matches_limit=1000,
        ),
    )


def run_complex_gate(tmp_path):
    base = tmp_path / "real-provider-complex-task"
    workspace = base / "workspace"
    event_stream = base / "events" / "events.jsonl"
    artifact_root = base / "artifacts"
    workspace.mkdir(parents=True)
    event_stream.parent.mkdir(parents=True)
    artifact_root.mkdir(parents=True)

    original_hashes = setup_complex_workspace(workspace)
    options = provider_options()
    guard = make_path_guard(workspace)
    filesystem_tools = make_filesystem_tools(guard)
    command_tools = build_complex_command_policy(guard)
    run_id = "real_provider_complex_task"
    recorder = EventRecorder(
        run_id=run_id,
        config=EventRecorderConfig(
            event_stream_path=event_stream,
            event_stream_ref=f"artifact://{run_id}/events.jsonl",
        ),
        clock=utc_timestamp,
    )
    artifact_writer = ArtifactWriter(
        ArtifactWriterConfig(
            artifact_root=artifact_root,
            artifact_ref_prefix=f"artifact://{run_id}",
        )
    )
    loop = AgentLoop(
        AgentLoopConfig(run_id=run_id),
        AgentLoopDependencies(
            provider=OpenAICompatibleProviderAdapter(options=options),
            filesystem_tools=filesystem_tools,
            command_tools=command_tools,
            event_recorder=recorder,
            artifact_writer=artifact_writer,
            runtime_clock=time.monotonic,
        ),
    )
    result = loop.run(build_invocation(workspace, options))
    return ComplexGateRun(
        result=result,
        event_stream=event_stream,
        artifact_root=artifact_root,
        workspace=workspace,
        original_forbidden_hashes=original_hashes,
    )


_SHA256_PREFIX = "sha256:"


def read_events(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def event_types(events):
    return [event["type"] for event in events]


def submitted_produced_paths(events):
    for event in reversed(events):
        if event["type"] == "result.submitted":
            return event["payload"]["produced_paths"]
    return []


def completed_tools(events):
    return [event["payload"]["tool"] for event in events if event["type"] == "tool.attempt.completed"]


def command_exit_history(summary, command_id):
    return [item["exit_code"] for item in summary["command_results"] if item["command_id"] == command_id]


def assert_sha256(value, label):
    assert isinstance(value, str) and value.startswith(_SHA256_PREFIX) and len(value) == 71, {label: value}


def assert_command_artifacts_have_sha256(summary):
    for command in summary["command_results"]:
        assert_sha256(command["stdout"]["sha256"], f"{command['command_id']} stdout sha256")
        assert_sha256(command["stderr"]["sha256"], f"{command['command_id']} stderr sha256")


def assert_required_tool_coverage(events):
    tools = completed_tools(events)
    for required in ("list_files", "read_file", "run_command"):
        assert required in tools, {"missing_tool": required, "completed_tools": tools}
    flexible = {"search_files", "apply_patch", "write_file"}
    used_flexible = flexible.intersection(tools)
    assert len(used_flexible) >= 2, {"expected_at_least_two_of": sorted(flexible), "actual": sorted(used_flexible)}


def assert_required_command_history(summary):
    run_tests = command_exit_history(summary, "run-tests")
    validate_report = command_exit_history(summary, "validate-report")
    assert len(run_tests) >= 2, {"run-tests history": run_tests}
    assert any(exit_code != 0 for exit_code in run_tests), {"run-tests history": run_tests}
    assert run_tests[-1] == 0, {"run-tests history": run_tests}
    assert validate_report, {"validate-report history": validate_report}
    assert validate_report[-1] == 0, {"validate-report history": validate_report}


def assert_required_workspace_mutations(summary):
    mutations = summary["workspace_mutations"]
    assert mutations, "expected at least one workspace mutation"
    mutated_paths = {mutation["path"] for mutation in mutations}
    assert "work/src/report.py" in mutated_paths, mutated_paths
    assert "work/output/report.txt" in mutated_paths, mutated_paths
    assert "work/output/repair-summary.md" in mutated_paths, mutated_paths
    for mutation in mutations:
        assert "work/tests/" not in mutation["path"]
        assert "work/expected/" not in mutation["path"]
        assert "work/data/" not in mutation["path"]
        assert_sha256(mutation["after_hash"], "mutation after_hash")
        assert mutation["diff"]["artifact_ref"], mutation
        assert_sha256(mutation["diff"]["sha256"], "mutation diff sha256")


def assert_required_lineage(summary):
    lineage_by_path = {item["path"]: item for item in summary["source_inventory_lineage"]}
    for path in REQUIRED_PRODUCED_PATHS:
        assert path in lineage_by_path, summary["source_inventory_lineage"]
        assert lineage_by_path[path]["lineage_status"] == "traceable", lineage_by_path[path]


def assert_forbidden_fixture_unchanged(run):
    assert forbidden_fixture_hashes(run.workspace) == run.original_forbidden_hashes


def assert_complex_gate_success(run):
    result = run.result
    assert result.status == AgentRunStatus.COMPLETED, failure_context(result, run.event_stream)

    integrity = verify_event_stream(run.event_stream, expected_events_hash=result.events_hash)
    assert integrity["ok"] is True, integrity

    events = read_events(run.event_stream)
    types = event_types(events)
    assert types[-1] == "run.completed", types
    assert "provider.turn.completed" in types, types
    assert "result.submitted" in types, types
    assert submitted_produced_paths(events) == REQUIRED_PRODUCED_PATHS
    assert_required_tool_coverage(events)

    summary = build_evidence_summary(result, run.event_stream)
    assert summary["event_stream"]["integrity"]["ok"] is True
    assert summary["provider_attempts"], summary
    assert_required_command_history(summary)
    assert_required_workspace_mutations(summary)
    assert_required_lineage(summary)
    assert_command_artifacts_have_sha256(summary)
    assert_forbidden_fixture_unchanged(run)

    assert (run.workspace / "work" / "output" / "report.txt").read_text(encoding="utf-8") == EXPECTED_REPORT
    assert (run.workspace / "work" / "output" / "repair-summary.md").read_text(encoding="utf-8").strip()


def failure_context(result, event_stream):
    context = {"result": redact_sensitive_values(result.model_dump(mode="json"))}
    if event_stream.exists():
        events = read_events(event_stream)
        context["event_types"] = event_types(events)
    return context


def redact_sensitive_values(value):
    if isinstance(value, dict):
        return {key: redact_sensitive_values(child) for key, child in value.items()}
    if isinstance(value, list):
        return [redact_sensitive_values(child) for child in value]
    if isinstance(value, str):
        redacted = value
        replacements = {
            os.environ.get("ATOMIC_AGENT_REAL_PROVIDER_API_KEY"): "[REDACTED_API_KEY]",
            os.environ.get("ATOMIC_AGENT_REAL_PROVIDER_BASE_URL"): "[REDACTED_BASE_URL]",
        }
        for raw, replacement in replacements.items():
            if raw:
                redacted = redacted.replace(raw, replacement)
        return redacted
    return value

@pytest.mark.real_provider_complex_task
def test_real_provider_complex_atomic_task_gate(tmp_path):
    require_real_provider_complex_task_enabled()
    run = run_complex_gate(tmp_path)
    assert_complex_gate_success(run)


def test_provider_options_defaults_to_complex_gate_profile(monkeypatch):
    clear_optional_provider_env(monkeypatch)
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_BASE_URL", "https://provider.example/v1")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_API_KEY", "secret-key")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_MODEL", "provider-model")

    options = provider_options()

    assert isinstance(options, OpenAICompatibleProviderOptions)
    assert options.context_window_tokens == 400000
    assert options.max_output_tokens == 128000
    assert options.stream_idle_timeout_seconds == 30.0
    assert options.total_timeout_seconds == 600.0
    assert options.reasoning_effort == "high"


def test_provider_options_reads_explicit_p2_005_env(monkeypatch):
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_BASE_URL", "https://provider.example/v1")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_API_KEY", "secret-key")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_MODEL", "provider-model")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_CONTEXT_WINDOW_TOKENS", "123456")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_MAX_OUTPUT_TOKENS", "4096")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_STREAM_IDLE_TIMEOUT_SECONDS", "12.5")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_TOTAL_TIMEOUT_SECONDS", "777")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_TEMPERATURE", "0.2")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_REASONING_EFFORT", "medium")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_TOP_P", "1.0")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_PRESENCE_PENALTY", "0.0")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_FREQUENCY_PENALTY", "0.0")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_SEED", "20260608")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_STOP", '["END_ACTION"]')
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_RESPONSE_FORMAT_JSON", '{"type":"json_object"}')
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_STREAM_OPTIONS_JSON", '{"include_usage":true}')
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_SERVICE_TIER", "default")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_USER", "atomic-agent-boardroom-os")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_LABEL", "boardroom-os-real-provider")

    options = provider_options()

    assert options.context_window_tokens == 123456
    assert options.max_output_tokens == 4096
    assert options.stream_idle_timeout_seconds == 12.5
    assert options.total_timeout_seconds == 777.0
    assert options.temperature == 0.2
    assert options.reasoning_effort == "medium"
    assert options.top_p == 1.0
    assert options.presence_penalty == 0.0
    assert options.frequency_penalty == 0.0
    assert options.seed == 20260608
    assert options.stop == ("END_ACTION",)
    assert options.response_format == {"type": "json_object"}
    assert options.stream_options == {"include_usage": True}
    assert options.service_tier == "default"
    assert options.user == "atomic-agent-boardroom-os"
    assert options.provider_label == "boardroom-os-real-provider"


def test_provider_options_rejects_non_object_json_env(monkeypatch):
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_BASE_URL", "https://provider.example/v1")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_API_KEY", "secret-key")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_MODEL", "provider-model")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_RESPONSE_FORMAT_JSON", "[]")

    with pytest.raises(ValueError, match="ATOMIC_AGENT_REAL_PROVIDER_RESPONSE_FORMAT_JSON must be a JSON object"):
        provider_options()


def test_provider_options_rejects_invalid_stop_env(monkeypatch):
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_BASE_URL", "https://provider.example/v1")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_API_KEY", "secret-key")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_MODEL", "provider-model")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_STOP", "[]")

    with pytest.raises(ValueError, match="ATOMIC_AGENT_REAL_PROVIDER_STOP must be a non-empty JSON array"):
        provider_options()


def test_complex_workspace_fixture_starts_broken(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    original_hashes = setup_complex_workspace(workspace)

    assert (workspace / "work" / "README.md").exists()
    assert (workspace / "work" / "src" / "report.py").exists()
    assert (workspace / "work" / "src" / "validator.py").exists()
    assert (workspace / "work" / "tests" / "test_report.py").exists()
    assert (workspace / "work" / "expected" / "report.txt").exists()
    assert original_hashes["work/data/orders.json"].startswith("sha256:")

    command_tools = build_complex_command_policy(make_path_guard(workspace))
    first_test_run = command_tools.run_command("run-tests")
    first_validation = command_tools.run_command("validate-report")

    assert first_test_run.ok is True
    assert first_test_run.data["exit_code"] != 0
    assert first_validation.ok is True
    assert first_validation.data["exit_code"] != 0


def test_forbidden_fixture_hashes_detect_mutation(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    original_hashes = setup_complex_workspace(workspace)

    (workspace / "work" / "data" / "orders.json").write_text("[]\n", encoding="utf-8")

    assert forbidden_fixture_hashes(workspace) != original_hashes


def test_build_invocation_uses_complex_gate_bounds(monkeypatch, tmp_path):
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_BASE_URL", "https://provider.example/v1")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_API_KEY", "secret-key")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_MODEL", "provider-model")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    options = provider_options()

    invocation = build_invocation(workspace, options)

    assert isinstance(invocation, AgentInvocation)
    assert invocation.allowed_write_set == ["work/src/", "work/output/"]
    assert invocation.tools == [
        "list_files",
        "read_file",
        "search_files",
        "apply_patch",
        "write_file",
        "run_command",
        "submit_result",
    ]
    assert invocation.budgets["max_steps"] == 100
    assert invocation.budgets["max_parse_failures"] == 1
    assert invocation.metadata["test"] == "real_provider_complex_task"
    assert invocation.metadata["provider_config_summary"]["reasoning_effort"] == "high"
    assert "work/output/repair-summary.md" in invocation.task
    assert "Tool input schemas:" in invocation.task
    assert 'list_files: {"path":"work","recursive":true}' in invocation.task
    assert 'read_file: {"path":"work/src/report.py"}' in invocation.task
    assert 'search_files: {"query":"report","path":"work","mode":"content","max_matches":20}' in invocation.task
    assert 'apply_patch: {"path":"work/src/report.py","old_text":"exact existing text","new_text":"replacement text","replace_all":false}' in invocation.task
    assert 'write_file: {"path":"work/output/report.txt","content":"file content"}' in invocation.task
    assert 'run_command: {"command_id":"run-tests"}' in invocation.task
    assert 'submit_result: {"summary":"...","produced_paths":["work/src/report.py","work/output/report.txt","work/output/repair-summary.md"],"evidence_refs":[]}' in invocation.task
    assert "You must use search_files before the final submit_result" in invocation.task
    assert "search_files input must use query" in invocation.task
    assert "search_files mode must be content or name" in invocation.task
    assert "Do not use a pattern key for search_files" in invocation.task
    assert "Do not concatenate two JSON objects" in invocation.task
    assert "For multi-line source repairs, prefer write_file" in invocation.task
    assert "Use apply_patch only for short exact replacements" in invocation.task
    assert "at least two of search_files, apply_patch, and write_file" in invocation.task


def test_run_complex_gate_builds_workspace_and_event_stream(monkeypatch, tmp_path):
    class ImmediateSubmitProvider:
        def __init__(self, options):
            self.options = options

        def complete(self, context):
            return json.dumps(
                {
                    "action_id": "submit_for_runner_test",
                    "action": "submit_result",
                    "reason_summary": "exercise runner wiring",
                    "input": {"summary": "runner wired", "produced_paths": [], "evidence_refs": []},
                },
                sort_keys=True,
            )

    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_BASE_URL", "https://provider.example/v1")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_API_KEY", "secret-key")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_MODEL", "provider-model")
    monkeypatch.setattr(sys.modules[__name__], "OpenAICompatibleProviderAdapter", ImmediateSubmitProvider, raising=False)

    run = run_complex_gate(tmp_path)

    assert run.workspace == tmp_path / "real-provider-complex-task" / "workspace"
    assert run.event_stream.exists()
    assert run.artifact_root.exists()
    assert run.result.status.value == "completed"
    assert run.original_forbidden_hashes["work/data/orders.json"].startswith("sha256:")


def test_success_assertion_rejects_missing_required_outputs(monkeypatch, tmp_path):
    class ImmediateSubmitProvider:
        def __init__(self, options):
            self.options = options

        def complete(self, context):
            return json.dumps(
                {
                    "action_id": "submit_for_assertion_test",
                    "action": "submit_result",
                    "reason_summary": "submit without required evidence",
                    "input": {"summary": "missing evidence", "produced_paths": [], "evidence_refs": []},
                },
                sort_keys=True,
            )

    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_BASE_URL", "https://provider.example/v1")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_API_KEY", "secret-key")
    monkeypatch.setenv("ATOMIC_AGENT_REAL_PROVIDER_MODEL", "provider-model")
    monkeypatch.setattr(sys.modules[__name__], "OpenAICompatibleProviderAdapter", ImmediateSubmitProvider, raising=False)

    run = run_complex_gate(tmp_path)

    with pytest.raises(AssertionError):
        assert_complex_gate_success(run)
