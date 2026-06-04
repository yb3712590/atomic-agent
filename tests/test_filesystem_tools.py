import pytest

from atomic_agent.filesystem_tools import (
    FileToolResult,
    FilesystemToolConfig,
    FilesystemToolConfigError,
    FilesystemTools,
    execute_filesystem_action,
)
from atomic_agent.models import AgentAction, AgentActionType
from atomic_agent.path_guard import WorkspacePathGuard


def tool_config():
    return FilesystemToolConfig(
        default_read_limit=12,
        max_read_limit=32,
        default_max_entries=10,
        max_entries_limit=20,
        default_max_matches=5,
        max_matches_limit=10,
    )


def make_tools(tmp_path, allowed_write_set=None):
    guard = WorkspacePathGuard(tmp_path, allowed_write_set or [])
    return FilesystemTools(guard, tool_config())


def test_file_tool_result_success_has_no_error_fields():
    result = FileToolResult(ok=True, tool="read_file", path="README.md", data={"content": "hello"})

    assert result.ok is True
    assert result.error_kind is None
    assert result.error_message is None


def test_file_tool_result_success_rejects_error_fields():
    with pytest.raises(ValueError):
        FileToolResult(
            ok=True,
            tool="read_file",
            path="README.md",
            data={},
            error_kind="not_found",
            error_message="File not found.",
        )


def test_file_tool_result_failure_requires_error_kind():
    with pytest.raises(ValueError):
        FileToolResult(ok=False, tool="read_file", path="missing.md", data={}, error_message="File not found.")


def test_file_tool_result_failure_requires_error_message():
    with pytest.raises(ValueError):
        FileToolResult(ok=False, tool="read_file", path="missing.md", data={}, error_kind="not_found")


def test_file_tool_result_failure_accepts_error_fields():
    result = FileToolResult(
        ok=False,
        tool="read_file",
        path="missing.md",
        data={},
        error_kind="not_found",
        error_message="File not found.",
    )

    assert result.ok is False
    assert result.error_kind == "not_found"
    assert result.error_message == "File not found."


@pytest.mark.parametrize(
    "kwargs",
    [
        {"default_read_limit": 0},
        {"max_read_limit": 0},
        {"default_read_limit": 33},
        {"default_max_entries": 0},
        {"max_entries_limit": 0},
        {"default_max_entries": 21},
        {"default_max_matches": 0},
        {"max_matches_limit": 0},
        {"default_max_matches": 11},
    ],
)
def test_filesystem_tools_rejects_invalid_config(tmp_path, kwargs):
    values = {
        "default_read_limit": 12,
        "max_read_limit": 32,
        "default_max_entries": 10,
        "max_entries_limit": 20,
        "default_max_matches": 5,
        "max_matches_limit": 10,
    }
    values.update(kwargs)
    guard = WorkspacePathGuard(tmp_path, allowed_write_set=[])

    with pytest.raises(FilesystemToolConfigError):
        FilesystemTools(guard, FilesystemToolConfig(**values))


def test_list_files_lists_workspace_root_in_stable_order(tmp_path):
    (tmp_path / "b.txt").write_text("b", encoding="utf-8")
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    tools = make_tools(tmp_path)

    result = tools.list_files()

    assert result.ok is True
    assert result.tool == "list_files"
    assert result.path is None
    assert result.data == {
        "entries": [
            {"path": "a.txt", "kind": "file", "size": 1},
            {"path": "b.txt", "kind": "file", "size": 1},
            {"path": "docs", "kind": "directory", "size": None},
        ],
        "truncated": False,
    }


def test_list_files_lists_nested_directory_non_recursive(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "index.md").write_text("index", encoding="utf-8")
    (docs / "nested").mkdir()
    (docs / "nested" / "hidden.md").write_text("hidden", encoding="utf-8")
    tools = make_tools(tmp_path)

    result = tools.list_files(path="docs")

    assert result.ok is True
    assert result.path == "docs"
    assert result.data == {
        "entries": [
            {"path": "docs/index.md", "kind": "file", "size": 5},
            {"path": "docs/nested", "kind": "directory", "size": None},
        ],
        "truncated": False,
    }


def test_list_files_supports_recursive_listing(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "index.md").write_text("index", encoding="utf-8")
    (docs / "nested").mkdir()
    (docs / "nested" / "child.md").write_text("child", encoding="utf-8")
    tools = make_tools(tmp_path)

    result = tools.list_files(path="docs", recursive=True)

    assert result.ok is True
    assert result.data["entries"] == [
        {"path": "docs/index.md", "kind": "file", "size": 5},
        {"path": "docs/nested", "kind": "directory", "size": None},
        {"path": "docs/nested/child.md", "kind": "file", "size": 5},
    ]


def test_list_files_truncates_when_max_entries_is_reached(tmp_path):
    for name in ["a.txt", "b.txt", "c.txt"]:
        (tmp_path / name).write_text(name, encoding="utf-8")
    tools = make_tools(tmp_path)

    result = tools.list_files(max_entries=2)

    assert result.ok is True
    assert [entry["path"] for entry in result.data["entries"]] == ["a.txt", "b.txt"]
    assert result.data["truncated"] is True


def test_list_files_rejects_file_path(tmp_path):
    (tmp_path / "README.md").write_text("readme", encoding="utf-8")
    tools = make_tools(tmp_path)

    result = tools.list_files(path="README.md")

    assert result.ok is False
    assert result.error_kind == "not_directory"
    assert result.data == {}


def test_list_files_rejects_path_escape(tmp_path):
    tools = make_tools(tmp_path)

    result = tools.list_files(path="../outside")

    assert result.ok is False
    assert result.error_kind == "permission_denied"
    assert result.error_message == "path_escape_denied"


def test_read_file_reads_utf8_slice_and_reports_truncation(tmp_path):
    (tmp_path / "README.md").write_text("hello world", encoding="utf-8")
    tools = make_tools(tmp_path)

    result = tools.read_file("README.md", offset=0, limit=5)

    assert result.ok is True
    assert result.tool == "read_file"
    assert result.path == "README.md"
    assert result.data == {
        "content": "hello",
        "offset": 0,
        "bytes_read": 5,
        "truncated": True,
    }


def test_read_file_returns_not_file_for_directory(tmp_path):
    (tmp_path / "docs").mkdir()
    tools = make_tools(tmp_path)

    result = tools.read_file("docs")

    assert result.ok is False
    assert result.error_kind == "not_file"
    assert result.data == {}


def test_read_file_returns_not_found_for_missing_file(tmp_path):
    tools = make_tools(tmp_path)

    result = tools.read_file("missing.md")

    assert result.ok is False
    assert result.error_kind == "not_found"
    assert result.data == {}


def test_read_file_rejects_invalid_offset(tmp_path):
    (tmp_path / "README.md").write_text("hello", encoding="utf-8")
    tools = make_tools(tmp_path)

    result = tools.read_file("README.md", offset=-1)

    assert result.ok is False
    assert result.error_kind == "invalid_input"
    assert result.error_message == "offset must be a non-negative integer"


def test_read_file_returns_decode_failed_for_non_utf8_file(tmp_path):
    (tmp_path / "binary.dat").write_bytes(b"\xff\xfe")
    tools = make_tools(tmp_path)

    result = tools.read_file("binary.dat")

    assert result.ok is False
    assert result.error_kind == "decode_failed"
    assert result.data == {}


def test_search_files_finds_paths_by_name(tmp_path):
    (tmp_path / "README.md").write_text("readme", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "agent-action.md").write_text("action", encoding="utf-8")
    tools = make_tools(tmp_path)

    result = tools.search_files("agent", mode="name")

    assert result.ok is True
    assert result.tool == "search_files"
    assert result.path is None
    assert result.data == {
        "matches": [{"path": "docs/agent-action.md", "line": None, "preview": "docs/agent-action.md"}],
        "truncated": False,
        "skipped": [],
    }


def test_search_files_finds_content_with_one_based_line_numbers(tmp_path):
    (tmp_path / "a.txt").write_text("alpha\nneedle here\n", encoding="utf-8")
    (tmp_path / "b.txt").write_text("no match\n", encoding="utf-8")
    tools = make_tools(tmp_path)

    result = tools.search_files("needle", mode="content")

    assert result.ok is True
    assert result.data == {
        "matches": [{"path": "a.txt", "line": 2, "preview": "needle here"}],
        "truncated": False,
        "skipped": [],
    }


def test_search_files_rejects_empty_query(tmp_path):
    tools = make_tools(tmp_path)

    result = tools.search_files("", mode="content")

    assert result.ok is False
    assert result.error_kind == "invalid_input"
    assert result.error_message == "query must be a non-empty string"


def test_search_files_rejects_invalid_mode(tmp_path):
    tools = make_tools(tmp_path)

    result = tools.search_files("needle", mode="regex")

    assert result.ok is False
    assert result.error_kind == "invalid_input"
    assert result.error_message == 'mode must be "name" or "content"'


def test_search_files_requires_directory_target(tmp_path):
    (tmp_path / "README.md").write_text("needle", encoding="utf-8")
    tools = make_tools(tmp_path)

    result = tools.search_files("needle", path="README.md")

    assert result.ok is False
    assert result.error_kind == "not_directory"


def test_search_files_truncates_multiple_matches_in_one_file(tmp_path):
    (tmp_path / "a.txt").write_text("needle 1\nneedle 2\nneedle 3\n", encoding="utf-8")
    tools = make_tools(tmp_path)

    result = tools.search_files("needle", max_matches=2)

    assert result.ok is True
    assert result.data == {
        "matches": [
            {"path": "a.txt", "line": 1, "preview": "needle 1"},
            {"path": "a.txt", "line": 2, "preview": "needle 2"},
        ],
        "truncated": True,
        "skipped": [],
    }


def test_search_files_records_decode_failures_as_skipped(tmp_path):
    (tmp_path / "binary.dat").write_bytes(b"\xff\xfe")
    (tmp_path / "text.txt").write_text("needle\n", encoding="utf-8")
    tools = make_tools(tmp_path)

    result = tools.search_files("needle", mode="content")

    assert result.ok is True
    assert result.data["matches"] == [{"path": "text.txt", "line": 1, "preview": "needle"}]
    assert result.data["truncated"] is False
    assert len(result.data["skipped"]) == 1
    assert result.data["skipped"][0]["path"] == "binary.dat"


def test_write_file_creates_file_inside_allowed_directory(tmp_path):
    tools = make_tools(tmp_path, allowed_write_set=["generated/"])

    result = tools.write_file("generated/output.md", "hello\n")

    assert result.ok is True
    assert result.tool == "write_file"
    assert result.path == "generated/output.md"
    assert (tmp_path / "generated" / "output.md").read_text(encoding="utf-8") == "hello\n"
    assert result.data["bytes_written"] == 6
    assert result.data["created"] is True
    assert result.data["before_hash"] is None
    assert result.data["after_hash"].startswith("sha256:")
    assert "hello" in result.data["diff"]


def test_write_file_overwrites_exact_allowed_file_and_reports_before_hash(tmp_path):
    target = tmp_path / "output.md"
    target.write_text("old\n", encoding="utf-8")
    tools = make_tools(tmp_path, allowed_write_set=["output.md"])

    result = tools.write_file("output.md", "new\n")

    assert result.ok is True
    assert target.read_text(encoding="utf-8") == "new\n"
    assert result.data["created"] is False
    assert result.data["before_hash"].startswith("sha256:")
    assert result.data["after_hash"].startswith("sha256:")
    assert result.data["before_hash"] != result.data["after_hash"]
    assert "-old" in result.data["diff"]
    assert "+new" in result.data["diff"]


def test_write_file_rejects_path_outside_allowed_write_set(tmp_path):
    tools = make_tools(tmp_path, allowed_write_set=["generated/"])

    result = tools.write_file("README.md", "hello")

    assert result.ok is False
    assert result.error_kind == "permission_denied"
    assert result.error_message == "write_not_allowed"
    assert not (tmp_path / "README.md").exists()


def test_write_file_rejects_directory_target(tmp_path):
    (tmp_path / "generated").mkdir()
    tools = make_tools(tmp_path, allowed_write_set=["generated"])

    result = tools.write_file("generated", "hello")

    assert result.ok is False
    assert result.error_kind == "not_file"
    assert result.data == {}


def test_apply_patch_replaces_single_match(tmp_path):
    target = tmp_path / "output.md"
    target.write_text("hello old\n", encoding="utf-8")
    tools = make_tools(tmp_path, allowed_write_set=["output.md"])

    result = tools.apply_patch("output.md", "old", "new")

    assert result.ok is True
    assert result.tool == "apply_patch"
    assert result.path == "output.md"
    assert target.read_text(encoding="utf-8") == "hello new\n"
    assert result.data["replacements"] == 1
    assert result.data["before_hash"].startswith("sha256:")
    assert result.data["after_hash"].startswith("sha256:")
    assert result.data["before_hash"] != result.data["after_hash"]
    assert "-hello old" in result.data["diff"]
    assert "+hello new" in result.data["diff"]


def test_apply_patch_returns_patch_not_applied_and_keeps_file_unchanged(tmp_path):
    target = tmp_path / "output.md"
    target.write_text("hello old\n", encoding="utf-8")
    tools = make_tools(tmp_path, allowed_write_set=["output.md"])

    result = tools.apply_patch("output.md", "missing", "new")

    assert result.ok is False
    assert result.error_kind == "patch_not_applied"
    assert target.read_text(encoding="utf-8") == "hello old\n"


def test_apply_patch_rejects_ambiguous_patch_and_keeps_file_unchanged(tmp_path):
    target = tmp_path / "output.md"
    target.write_text("old old\n", encoding="utf-8")
    tools = make_tools(tmp_path, allowed_write_set=["output.md"])

    result = tools.apply_patch("output.md", "old", "new")

    assert result.ok is False
    assert result.error_kind == "ambiguous_patch"
    assert target.read_text(encoding="utf-8") == "old old\n"


def test_apply_patch_replace_all_replaces_every_match(tmp_path):
    target = tmp_path / "output.md"
    target.write_text("old old\n", encoding="utf-8")
    tools = make_tools(tmp_path, allowed_write_set=["output.md"])

    result = tools.apply_patch("output.md", "old", "new", replace_all=True)

    assert result.ok is True
    assert target.read_text(encoding="utf-8") == "new new\n"
    assert result.data["replacements"] == 2


def test_apply_patch_returns_not_found_for_missing_file(tmp_path):
    tools = make_tools(tmp_path, allowed_write_set=["output.md"])

    result = tools.apply_patch("output.md", "old", "new")

    assert result.ok is False
    assert result.error_kind == "not_found"
    assert result.data == {}


def test_apply_patch_rejects_path_outside_allowed_write_set(tmp_path):
    target = tmp_path / "README.md"
    target.write_text("old\n", encoding="utf-8")
    tools = make_tools(tmp_path, allowed_write_set=["output.md"])

    result = tools.apply_patch("README.md", "old", "new")

    assert result.ok is False
    assert result.error_kind == "permission_denied"
    assert result.error_message == "write_not_allowed"
    assert target.read_text(encoding="utf-8") == "old\n"


def test_apply_patch_rejects_empty_old_text(tmp_path):
    target = tmp_path / "output.md"
    target.write_text("old\n", encoding="utf-8")
    tools = make_tools(tmp_path, allowed_write_set=["output.md"])

    result = tools.apply_patch("output.md", "", "new")

    assert result.ok is False
    assert result.error_kind == "invalid_input"
    assert target.read_text(encoding="utf-8") == "old\n"


def test_execute_filesystem_action_dispatches_list_files(tmp_path):
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    tools = make_tools(tmp_path)
    action = AgentAction(
        action_id="act-list",
        action=AgentActionType.LIST_FILES,
        reason_summary="List files",
        input={},
    )

    result = execute_filesystem_action(action, tools)

    assert result.ok is True
    assert result.tool == "list_files"
    assert result.data["entries"] == [{"path": "a.txt", "kind": "file", "size": 1}]


def test_execute_filesystem_action_dispatches_read_file(tmp_path):
    (tmp_path / "README.md").write_text("hello", encoding="utf-8")
    tools = make_tools(tmp_path)
    action = AgentAction(
        action_id="act-read",
        action=AgentActionType.READ_FILE,
        reason_summary="Read file",
        input={"path": "README.md"},
    )

    result = execute_filesystem_action(action, tools)

    assert result.ok is True
    assert result.tool == "read_file"
    assert result.data["content"] == "hello"


def test_execute_filesystem_action_dispatches_search_files(tmp_path):
    (tmp_path / "README.md").write_text("needle", encoding="utf-8")
    tools = make_tools(tmp_path)
    action = AgentAction(
        action_id="act-search",
        action=AgentActionType.SEARCH_FILES,
        reason_summary="Search files",
        input={"query": "needle"},
    )

    result = execute_filesystem_action(action, tools)

    assert result.ok is True
    assert result.tool == "search_files"
    assert result.data["matches"] == [{"path": "README.md", "line": 1, "preview": "needle"}]


def test_execute_filesystem_action_dispatches_write_file(tmp_path):
    tools = make_tools(tmp_path, allowed_write_set=["generated/"])
    action = AgentAction(
        action_id="act-write",
        action=AgentActionType.WRITE_FILE,
        reason_summary="Write file",
        input={"path": "generated/output.md", "content": "hello"},
    )

    result = execute_filesystem_action(action, tools)

    assert result.ok is True
    assert result.tool == "write_file"
    assert (tmp_path / "generated" / "output.md").read_text(encoding="utf-8") == "hello"


def test_execute_filesystem_action_dispatches_apply_patch(tmp_path):
    target = tmp_path / "output.md"
    target.write_text("old", encoding="utf-8")
    tools = make_tools(tmp_path, allowed_write_set=["output.md"])
    action = AgentAction(
        action_id="act-patch",
        action=AgentActionType.APPLY_PATCH,
        reason_summary="Patch file",
        input={"path": "output.md", "old_text": "old", "new_text": "new"},
    )

    result = execute_filesystem_action(action, tools)

    assert result.ok is True
    assert result.tool == "apply_patch"
    assert target.read_text(encoding="utf-8") == "new"


def test_execute_filesystem_action_rejects_non_filesystem_action(tmp_path):
    tools = make_tools(tmp_path)
    action = AgentAction(
        action_id="act-command",
        action=AgentActionType.RUN_COMMAND,
        reason_summary="Run command",
        input={"command_id": "list"},
    )

    result = execute_filesystem_action(action, tools)

    assert result.ok is False
    assert result.tool == "run_command"
    assert result.error_kind == "unsupported_action"
    assert result.data == {}


def test_execute_filesystem_action_returns_invalid_input_for_malformed_input(tmp_path):
    tools = make_tools(tmp_path)
    action = AgentAction(
        action_id="act-read-malformed",
        action=AgentActionType.READ_FILE,
        reason_summary="Read file with malformed input",
        input={"unexpected": "README.md"},
    )

    result = execute_filesystem_action(action, tools)

    assert result.ok is False
    assert result.tool == "read_file"
    assert result.error_kind == "invalid_input"
    assert result.data == {}


def test_list_files_does_not_recurse_into_symlink_directory(tmp_path):
    outside = tmp_path.parent / "outside-list"
    outside.mkdir()
    (outside / "secret.txt").write_text("secret", encoding="utf-8")
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "link").symlink_to(outside, target_is_directory=True)
    tools = make_tools(tmp_path)

    result = tools.list_files(path="docs", recursive=True)

    assert result.ok is True
    assert result.data == {
        "entries": [{"path": "docs/link", "kind": "symlink", "size": len(str(outside))}],
        "truncated": False,
    }


def test_write_file_rejects_symlink_escape_inside_allowed_directory(tmp_path):
    outside = tmp_path.parent / "outside-write"
    outside.mkdir()
    generated = tmp_path / "generated"
    generated.mkdir()
    (generated / "link").symlink_to(outside, target_is_directory=True)
    tools = make_tools(tmp_path, allowed_write_set=["generated/"])

    result = tools.write_file("generated/link/output.md", "secret")

    assert result.ok is False
    assert result.error_kind == "permission_denied"
    assert result.error_message == "symlink_escape_denied"
    assert not (outside / "output.md").exists()
