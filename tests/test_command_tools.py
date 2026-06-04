import hashlib
from pathlib import Path
import sys

import pytest
from pydantic import ValidationError

from atomic_agent.command_tools import (
    CommandPolicy,
    CommandSpec,
    CommandToolConfig,
    CommandToolConfigError,
    CommandToolResult,
    CommandTools,
    execute_command_action,
)
from atomic_agent.models import AgentAction, AgentActionType
from atomic_agent.path_guard import WorkspacePathGuard


PYTHON = Path(sys.executable).resolve()


def command_config(max_output_bytes=64):
    return CommandToolConfig(
        default_timeout_seconds=1.0,
        max_timeout_seconds=3.0,
        max_output_bytes=max_output_bytes,
    )


def make_policy(command_id="python-ok", spec=None):
    if spec is None:
        spec = CommandSpec(argv=(str(PYTHON), "-c", "import sys; sys.stdout.write('ok')"))
    return CommandPolicy({command_id: spec})


def make_tools(tmp_path, policy=None, config=None):
    guard = WorkspacePathGuard(tmp_path, allowed_write_set=[])
    return CommandTools(guard, policy or make_policy(), config or command_config())


def test_command_tool_result_success_has_no_error_fields():
    result = CommandToolResult(
        ok=True,
        tool="run_command",
        command_id="test",
        data={"exit_code": 0},
    )

    assert result.ok is True
    assert result.error_kind is None
    assert result.error_message is None


def test_command_tool_result_success_rejects_error_fields():
    with pytest.raises(ValueError):
        CommandToolResult(
            ok=True,
            tool="run_command",
            command_id="test",
            data={"exit_code": 0},
            error_kind="permission_denied",
            error_message="Command denied.",
        )


def test_command_tool_result_failure_requires_error_kind():
    with pytest.raises(ValueError):
        CommandToolResult(
            ok=False,
            tool="run_command",
            command_id="missing",
            data={},
            error_message="Command denied.",
        )


def test_command_tool_result_failure_requires_error_message():
    with pytest.raises(ValueError):
        CommandToolResult(
            ok=False,
            tool="run_command",
            command_id="missing",
            data={},
            error_kind="permission_denied",
        )


def test_command_tool_result_failure_accepts_error_fields():
    result = CommandToolResult(
        ok=False,
        tool="run_command",
        command_id="missing",
        data={},
        error_kind="permission_denied",
        error_message="command_id is not declared in command policy",
    )

    assert result.ok is False
    assert result.error_kind == "permission_denied"
    assert result.error_message == "command_id is not declared in command policy"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"default_timeout_seconds": 0.0},
        {"max_timeout_seconds": 0.0},
        {"default_timeout_seconds": 4.0},
        {"max_output_bytes": 0},
    ],
)
def test_command_tools_rejects_invalid_config(tmp_path, kwargs):
    values = {
        "default_timeout_seconds": 1.0,
        "max_timeout_seconds": 3.0,
        "max_output_bytes": 64,
    }
    values.update(kwargs)
    guard = WorkspacePathGuard(tmp_path, allowed_write_set=[])

    with pytest.raises(CommandToolConfigError):
        CommandTools(guard, make_policy(), CommandToolConfig(**values))


def test_command_policy_rejects_empty_policy():
    with pytest.raises(CommandToolConfigError):
        CommandPolicy({})


@pytest.mark.parametrize("command_id", ["", " ", "bad id", "bad/id", "bad$id"])
def test_command_policy_rejects_invalid_command_id(command_id):
    spec = CommandSpec(argv=(str(PYTHON), "--version"))

    with pytest.raises(CommandToolConfigError):
        CommandPolicy({command_id: spec})


@pytest.mark.parametrize(
    "spec",
    [
        CommandSpec(argv=()),
        CommandSpec(argv=("",)),
        CommandSpec(argv=("python", "--version")),
        CommandSpec(argv=(str(PYTHON), "--version"), timeout_seconds=0.0),
        CommandSpec(argv=(str(PYTHON), "--version"), env={"": "value"}),
        CommandSpec(argv=(str(PYTHON), "--version"), env={"NAME": 123}),
        CommandSpec(argv=(str(PYTHON), "--version"), allow_network=True),
    ],
)
def test_command_policy_rejects_invalid_command_spec(spec):
    with pytest.raises(CommandToolConfigError):
        CommandPolicy({"test": spec})


def test_command_tools_accepts_workspace_cwd(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    policy = make_policy(spec=CommandSpec(argv=(str(PYTHON), "--version"), cwd="work"))

    tools = make_tools(tmp_path, policy=policy)

    assert tools is not None


@pytest.mark.parametrize("cwd", ["../outside", "missing", "file.txt"])
def test_command_tools_rejects_invalid_cwd(tmp_path, cwd):
    (tmp_path / "file.txt").write_text("not a directory", encoding="utf-8")
    policy = make_policy(spec=CommandSpec(argv=(str(PYTHON), "--version"), cwd=cwd))
    guard = WorkspacePathGuard(tmp_path, allowed_write_set=[])

    with pytest.raises(CommandToolConfigError):
        CommandTools(guard, policy, command_config())


def test_command_tools_rejects_cwd_symlink_escape(tmp_path):
    outside = tmp_path.parent / f"{tmp_path.name}-outside-command-cwd"
    outside.mkdir()
    link = tmp_path / "link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"symlink creation is unavailable: {error}")
    policy = make_policy(spec=CommandSpec(argv=(str(PYTHON), "--version"), cwd="link"))
    guard = WorkspacePathGuard(tmp_path, allowed_write_set=[])

    with pytest.raises(CommandToolConfigError):
        CommandTools(guard, policy, command_config())


def test_run_command_executes_declared_command_and_captures_output(tmp_path):
    policy = make_policy(
        "python-io",
        CommandSpec(
            argv=(str(PYTHON), "-c", "import sys; sys.stdout.write('ok'); sys.stderr.write('warn')"),
        ),
    )
    tools = make_tools(tmp_path, policy=policy)

    result = tools.run_command("python-io")

    assert result.ok is True
    assert result.tool == "run_command"
    assert result.command_id == "python-io"
    assert result.data["command_id"] == "python-io"
    assert result.data["argv"] == [str(PYTHON), "-c", "import sys; sys.stdout.write('ok'); sys.stderr.write('warn')"]
    assert result.data["cwd"] == str(tmp_path.resolve())
    assert result.data["exit_code"] == 0
    assert result.data["stdout"] == "ok"
    assert result.data["stderr"] == "warn"
    assert result.data["stdout_hash"] == "sha256:" + hashlib.sha256(b"ok").hexdigest()
    assert result.data["stderr_hash"] == "sha256:" + hashlib.sha256(b"warn").hexdigest()
    assert result.data["stdout_size_bytes"] == 2
    assert result.data["stderr_size_bytes"] == 4
    assert result.data["stdout_truncated"] is False
    assert result.data["stderr_truncated"] is False
    assert result.data["stdout_decoded_with_replacement"] is False
    assert result.data["stderr_decoded_with_replacement"] is False
    assert result.data["timeout_seconds"] == 1.0


def test_run_command_returns_completed_result_for_nonzero_exit_code(tmp_path):
    policy = make_policy(
        "python-fail",
        CommandSpec(argv=(str(PYTHON), "-c", "import sys; sys.stderr.write('failed'); sys.exit(3)")),
    )
    tools = make_tools(tmp_path, policy=policy)

    result = tools.run_command("python-fail")

    assert result.ok is True
    assert result.data["exit_code"] == 3
    assert result.data["stderr"] == "failed"


def test_run_command_rejects_unknown_command_without_execution(tmp_path):
    tools = make_tools(tmp_path)

    result = tools.run_command("missing")

    assert result.ok is False
    assert result.command_id == "missing"
    assert result.error_kind == "permission_denied"
    assert result.error_message == "command_id is not declared in command policy"
    assert result.data == {}


@pytest.mark.parametrize("command_id", ["", " ", "bad id", 123])
def test_run_command_rejects_invalid_command_id_input(tmp_path, command_id):
    tools = make_tools(tmp_path)

    result = tools.run_command(command_id)

    assert result.ok is False
    assert result.error_kind == "invalid_input"
    assert result.data == {}


def test_run_command_times_out_and_returns_failure(tmp_path):
    policy = make_policy(
        "python-sleep",
        CommandSpec(
            argv=(str(PYTHON), "-c", "import time; time.sleep(2)"),
            timeout_seconds=0.1,
        ),
    )
    tools = make_tools(tmp_path, policy=policy)

    result = tools.run_command("python-sleep")

    assert result.ok is False
    assert result.error_kind == "timeout"
    assert result.data == {}


def test_run_command_truncates_stdout_and_hashes_full_output(tmp_path):
    policy = make_policy(
        "python-output",
        CommandSpec(argv=(str(PYTHON), "-c", "import sys; sys.stdout.write('abcdef')")),
    )
    tools = make_tools(tmp_path, policy=policy, config=command_config(max_output_bytes=4))

    result = tools.run_command("python-output")

    assert result.ok is True
    assert result.data["stdout"] == "abcd"
    assert result.data["stdout_size_bytes"] == 6
    assert result.data["stdout_hash"] == "sha256:" + hashlib.sha256(b"abcdef").hexdigest()
    assert result.data["stdout_truncated"] is True


def test_run_command_truncates_stderr_and_hashes_full_output(tmp_path):
    policy = make_policy(
        "python-stderr",
        CommandSpec(argv=(str(PYTHON), "-c", "import sys; sys.stderr.write('uvwxyz')")),
    )
    tools = make_tools(tmp_path, policy=policy, config=command_config(max_output_bytes=3))

    result = tools.run_command("python-stderr")

    assert result.ok is True
    assert result.data["stderr"] == "uvw"
    assert result.data["stderr_size_bytes"] == 6
    assert result.data["stderr_hash"] == "sha256:" + hashlib.sha256(b"uvwxyz").hexdigest()
    assert result.data["stderr_truncated"] is True


def test_run_command_records_decode_replacement_for_non_utf8_output(tmp_path):
    policy = make_policy(
        "python-binary-output",
        CommandSpec(argv=(str(PYTHON), "-c", "import sys; sys.stdout.buffer.write(b'\\xff')")),
    )
    tools = make_tools(tmp_path, policy=policy)

    result = tools.run_command("python-binary-output")

    assert result.ok is True
    assert result.data["stdout"] == "�"
    assert result.data["stdout_decoded_with_replacement"] is True


def test_run_command_uses_explicit_env_without_inheriting_process_env(tmp_path, monkeypatch):
    monkeypatch.setenv("ATOMIC_AGENT_SHOULD_NOT_LEAK", "leaked")
    policy = make_policy(
        "python-env",
        CommandSpec(
            argv=(
                str(PYTHON),
                "-c",
                "import os, sys; sys.stdout.write(os.environ.get('VISIBLE', 'missing') + ':' + os.environ.get('ATOMIC_AGENT_SHOULD_NOT_LEAK', 'not-leaked'))",
            ),
            env={"VISIBLE": "yes"},
        ),
    )
    tools = make_tools(tmp_path, policy=policy)

    result = tools.run_command("python-env")

    assert result.ok is True
    assert result.data["stdout"] == "yes:not-leaked"


def test_run_command_executes_in_declared_workspace_cwd(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    policy = make_policy(
        "python-cwd",
        CommandSpec(
            argv=(str(PYTHON), "-c", "from pathlib import Path; print(Path.cwd().name, end='')"),
            cwd="work",
        ),
    )
    tools = make_tools(tmp_path, policy=policy)

    result = tools.run_command("python-cwd")

    assert result.ok is True
    assert result.data["stdout"] == "work"
    assert result.data["cwd"] == str(work.resolve())


def test_execute_command_action_dispatches_run_command(tmp_path):
    tools = make_tools(tmp_path)
    action = AgentAction(
        action_id="step-0001",
        action=AgentActionType.RUN_COMMAND,
        reason_summary="Run declared command.",
        input={"command_id": "python-ok"},
    )

    result = execute_command_action(action, tools)

    assert result.ok is True
    assert result.tool == "run_command"
    assert result.command_id == "python-ok"
    assert result.data["stdout"] == "ok"


def test_execute_command_action_rejects_non_command_action(tmp_path):
    tools = make_tools(tmp_path)
    action = AgentAction(
        action_id="step-0002",
        action=AgentActionType.READ_FILE,
        reason_summary="Read file.",
        input={"path": "README.md"},
    )

    result = execute_command_action(action, tools)

    assert result.ok is False
    assert result.tool == "read_file"
    assert result.command_id is None
    assert result.error_kind == "unsupported_action"
    assert result.data == {}


def test_agent_action_still_rejects_run_command_shell_string():
    with pytest.raises(ValidationError):
        AgentAction(
            action_id="step-0003",
            action=AgentActionType.RUN_COMMAND,
            reason_summary="Run forbidden shell command.",
            input={"command": "python --version"},
        )
