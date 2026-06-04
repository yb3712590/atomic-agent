import subprocess
import sys
from pathlib import Path

import pytest

from atomic_agent.path_guard import PathDecisionType, PathGuardConfigError, WorkspacePathGuard


def create_escaping_directory_link(link: Path, target: Path):
    try:
        link.symlink_to(target, target_is_directory=True)
        return
    except OSError as error:
        if sys.platform != "win32":
            pytest.skip(f"symlink creation is unavailable: {error}")

    subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            "New-Item",
            "-ItemType",
            "Junction",
            "-Path",
            str(link),
            "-Target",
            str(target),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )


def test_resolve_read_path_allows_relative_path_inside_workspace(tmp_path):
    target = tmp_path / "src" / "atomic_agent" / "models.py"
    target.parent.mkdir(parents=True)
    target.write_text("content", encoding="utf-8")
    guard = WorkspacePathGuard(tmp_path, allowed_write_set=[])

    decision = guard.resolve_read_path("src/atomic_agent/models.py")

    assert decision.decision == PathDecisionType.ALLOW
    assert decision.requested_path == "src/atomic_agent/models.py"
    assert decision.normalized_path == str(target.resolve())
    assert decision.reason == "read_path_allowed"
    assert decision.matched_policy == "workspace_root"


def test_resolve_read_path_allows_nonexistent_path_inside_workspace(tmp_path):
    existing_parent = tmp_path / "docs"
    existing_parent.mkdir()
    target = existing_parent / "missing.md"
    guard = WorkspacePathGuard(tmp_path, allowed_write_set=[])

    decision = guard.resolve_read_path("docs/missing.md")

    assert decision.decision == PathDecisionType.ALLOW
    assert decision.requested_path == "docs/missing.md"
    assert decision.normalized_path == str(target.resolve())
    assert decision.reason == "read_path_allowed"
    assert decision.matched_policy == "workspace_root"


@pytest.mark.parametrize("requested_path", ["", "   ", ".", "./", ".//"])
def test_resolve_read_path_rejects_empty_paths(tmp_path, requested_path):
    guard = WorkspacePathGuard(tmp_path, allowed_write_set=[])

    decision = guard.resolve_read_path(requested_path)

    assert decision.decision == PathDecisionType.DENY
    assert decision.normalized_path is None
    assert decision.reason == "empty_path_denied"


@pytest.mark.parametrize(
    "requested_path",
    ["/tmp/file.txt", "C:/tmp/file.txt", "C:tmp/file.txt", "\\tmp\\file.txt"],
)
def test_resolve_read_path_rejects_absolute_paths(tmp_path, requested_path):
    guard = WorkspacePathGuard(tmp_path, allowed_write_set=[])

    decision = guard.resolve_read_path(requested_path)

    assert decision.decision == PathDecisionType.DENY
    assert decision.normalized_path is None
    assert decision.reason == "absolute_path_denied"


@pytest.mark.parametrize("requested_path", ["../outside.txt", "docs/../outside.txt"])
def test_resolve_read_path_rejects_path_traversal(tmp_path, requested_path):
    guard = WorkspacePathGuard(tmp_path, allowed_write_set=[])

    decision = guard.resolve_read_path(requested_path)

    assert decision.decision == PathDecisionType.DENY
    assert decision.normalized_path is None
    assert decision.reason == "path_escape_denied"


def test_resolve_read_path_rejects_symlink_escape(tmp_path):
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir()
    outside_file = outside / "secret.txt"
    outside_file.write_text("secret", encoding="utf-8")
    link = tmp_path / "link"
    create_escaping_directory_link(link, outside)
    guard = WorkspacePathGuard(tmp_path, allowed_write_set=[])

    decision = guard.resolve_read_path("link/secret.txt")

    assert decision.decision == PathDecisionType.DENY
    assert decision.normalized_path == str(outside_file.resolve())
    assert decision.reason == "symlink_escape_denied"


def test_resolve_read_path_rejects_non_string_path(tmp_path):
    guard = WorkspacePathGuard(tmp_path, allowed_write_set=[])

    decision = guard.resolve_read_path(123)

    assert decision.decision == PathDecisionType.DENY
    assert decision.requested_path == "123"
    assert decision.normalized_path is None
    assert decision.reason == "invalid_path_type_denied"


def test_guard_rejects_missing_workspace_root(tmp_path):
    with pytest.raises(PathGuardConfigError):
        WorkspacePathGuard(tmp_path / "missing", allowed_write_set=[])


def test_resolve_write_path_allows_exact_allowed_file(tmp_path):
    guard = WorkspacePathGuard(tmp_path, allowed_write_set=["docs/output.md"])

    decision = guard.resolve_write_path("docs/output.md")

    assert decision.decision == PathDecisionType.ALLOW
    assert decision.reason == "write_path_allowed"
    assert decision.normalized_path == str((tmp_path / "docs" / "output.md").resolve())
    assert decision.matched_policy == "docs/output.md"


def test_resolve_write_path_rejects_path_outside_allowed_write_set(tmp_path):
    guard = WorkspacePathGuard(tmp_path, allowed_write_set=["docs/output.md"])

    decision = guard.resolve_write_path("src/atomic_agent/models.py")

    assert decision.decision == PathDecisionType.DENY
    assert decision.reason == "write_not_allowed"
    assert decision.matched_policy is None


def test_resolve_write_path_allows_directory_policy_child(tmp_path):
    guard = WorkspacePathGuard(tmp_path, allowed_write_set=["docs/generated/"])

    decision = guard.resolve_write_path("docs/generated/output.md")

    assert decision.decision == PathDecisionType.ALLOW
    assert decision.reason == "write_path_allowed"
    assert decision.matched_policy == "docs/generated/"


def test_resolve_write_path_rejects_directory_policy_string_prefix(tmp_path):
    guard = WorkspacePathGuard(tmp_path, allowed_write_set=["docs/generated/"])

    decision = guard.resolve_write_path("docs/generated-other/output.md")

    assert decision.decision == PathDecisionType.DENY
    assert decision.reason == "write_not_allowed"
    assert decision.matched_policy is None


def test_resolve_write_path_allows_windows_trailing_backslash_directory_policy(tmp_path):
    guard = WorkspacePathGuard(tmp_path, allowed_write_set=["docs\\generated\\"])

    decision = guard.resolve_write_path("docs/generated/output.md")

    assert decision.decision == PathDecisionType.ALLOW
    assert decision.reason == "write_path_allowed"
    assert decision.matched_policy == "docs\\generated\\"


@pytest.mark.parametrize(
    "allowed_path",
    ["", "   ", ".", "./", ".//", "/tmp/output.md", "C:/tmp/output.md", "C:tmp/output.md", "../output.md"],
)
def test_guard_rejects_invalid_allowed_write_set_entries(tmp_path, allowed_path):
    with pytest.raises(PathGuardConfigError):
        WorkspacePathGuard(tmp_path, allowed_write_set=[allowed_path])


def test_guard_rejects_allowed_write_set_symlink_escape(tmp_path):
    outside = tmp_path.parent / f"{tmp_path.name}-outside-policy"
    outside.mkdir()
    link = tmp_path / "allowed-link"
    create_escaping_directory_link(link, outside)

    with pytest.raises(PathGuardConfigError):
        WorkspacePathGuard(tmp_path, allowed_write_set=["allowed-link/output.md"])


def test_guard_rejects_allowed_write_set_dangling_symlink_escape(tmp_path):
    outside = tmp_path.parent / f"{tmp_path.name}-missing-target"
    link = tmp_path / "dangling-link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"dangling symlink creation is unavailable: {error}")

    with pytest.raises(PathGuardConfigError):
        WorkspacePathGuard(tmp_path, allowed_write_set=["dangling-link/output.md"])
