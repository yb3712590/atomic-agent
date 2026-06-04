# Filesystem Tools Specification

## Status

implemented

## Purpose

本文定义 P0-004 `filesystem tools`（文件系统工具）的实现规格。该工具层负责在 `WorkspacePathGuard`（工作区路径守卫）允许的边界内执行真实文件系统操作，并返回结构化 tool result（工具结果），为后续 event recorder（事件记录器）和 AgentLoop（智能体循环）提供可审计事实。

## Scope

P0-004 覆盖以下工具执行：

- `list_files`（列出文件）
- `read_file`（读取文件）
- `search_files`（搜索文件）
- `write_file`（写入文件）
- `apply_patch`（应用补丁）

包含：

- 复用 `WorkspacePathGuard.resolve_read_path`（解析读路径）和 `WorkspacePathGuard.resolve_write_path`（解析写路径）作为路径权限事实源。
- 对真实文件系统执行 list/read/search/write/patch 操作。
- 对工具输入做最小 schema（模式）校验。
- 对文件读取、搜索和输出数量使用显式 tool config（工具配置）限制。
- 写入和 patch 只能作用于 allowed write set（允许写入集合）内路径。
- 对写入和 patch 返回 before/after hash（修改前后哈希）和 diff（差异）信息。
- 失败时返回结构化失败结果，不返回伪成功。

不包含：

- 修改 `WorkspacePathGuard`（工作区路径守卫）的路径权限语义。
- event recorder（事件记录器）或 JSONL event stream（JSONL 事件流）输出。
- command policy（命令策略）或 `run_command` 执行。
- network policy（网络策略）或 `web_fetch` 执行。
- provider adapter（模型供应商适配器）。
- AgentLoop（智能体循环）重试逻辑。
- 完整 unified diff parser（统一 diff 解析器）。
- 二进制文件编辑。

这些能力分别由 P0-005、P0-006、P0-007、P0-008 和 P1-001 覆盖。

## Authoritative Inputs

本规格依据以下已索引文档：

- `docs/04-implementation-spec/mvp-runtime-spec.md`（MVP 运行时规格）。
- `docs/04-implementation-acceptance/mvp-acceptance.md`（MVP 验收标准）。
- `docs/04-implementation-spec/P0-003-workspace-path-guard-spec.md`（工作区路径守卫规格）。
- `docs/02-architecture/permission-and-sandbox-architecture.md`（权限与沙箱架构）。
- `docs/09-adr/0003-use-fail-closed-permission-model.md`（失败关闭权限模型 ADR）。

## Public API

新增模块：

```text
src/atomic_agent/filesystem_tools.py
```

公开类型：

```python
@dataclass(frozen=True)
class FilesystemToolConfig:
    default_read_limit: int
    max_read_limit: int
    default_max_entries: int
    max_entries_limit: int
    default_max_matches: int
    max_matches_limit: int


@dataclass(frozen=True)
class FileToolResult:
    ok: bool
    tool: str
    path: str | None
    data: dict[str, Any]
    error_kind: str | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        ...


class FilesystemToolConfigError(ValueError):
    ...


class FilesystemTools:
    def __init__(self, guard: WorkspacePathGuard, config: FilesystemToolConfig):
        ...

    def list_files(self, path: str | None = None, recursive: bool = False, max_entries: int | None = None) -> FileToolResult:
        ...

    def read_file(self, path: str, offset: int = 0, limit: int | None = None) -> FileToolResult:
        ...

    def search_files(self, query: str, path: str | None = None, mode: str = "content", max_matches: int | None = None) -> FileToolResult:
        ...

    def write_file(self, path: str, content: str) -> FileToolResult:
        ...

    def apply_patch(self, path: str, old_text: str, new_text: str, replace_all: bool = False) -> FileToolResult:
        ...


def execute_filesystem_action(action: AgentAction, tools: FilesystemTools) -> FileToolResult:
    ...
```

`FilesystemTools`（文件系统工具集合）必须接收显式 `FilesystemToolConfig`（文件系统工具配置）。runtime code（运行时代码）不得在工具实现中硬编码 read limit（读取限制）、entry limit（条目限制）或 match limit（匹配限制）。

## Result Contract

所有工具必须返回 `FileToolResult`（文件工具结果）。

成功结果：

```text
ok = True
error_kind = None
error_message = None
data = <tool-specific structured data>
```

失败结果：

```text
ok = False
error_kind = <stable machine-readable kind>
error_message = <short human-readable message>
data = {}
```

工具不得把可预期失败转换为成功结果。可预期失败包括 permission denied（权限拒绝）、not found（未找到）、invalid input（非法输入）、decode failure（解码失败）、patch mismatch（补丁不匹配）和 unsupported action（不支持动作）。

## Configuration Rules

`FilesystemToolConfig`（文件系统工具配置）字段语义：

| Field | 中文解释 | 约束 |
|---|---|---|
| `default_read_limit` | 默认读取字节数 | `> 0` 且 `<= max_read_limit` |
| `max_read_limit` | 单次最大读取字节数 | `> 0` |
| `default_max_entries` | 默认列出条目数 | `> 0` 且 `<= max_entries_limit` |
| `max_entries_limit` | 单次最大列出条目数 | `> 0` |
| `default_max_matches` | 默认搜索匹配数 | `> 0` 且 `<= max_matches_limit` |
| `max_matches_limit` | 单次最大搜索匹配数 | `> 0` |

非法配置是 invocation configuration defect（调用配置缺陷），必须在 `FilesystemTools` 初始化时失败，不得在执行工具时 silent fallback（静默降级）为默认值。

## Tool Semantics

### `list_files`（列出文件）

输入：

```json
{
  "path": "docs",
  "recursive": false,
  "max_entries": 100
}
```

字段语义：

- `path` 可省略或为 `null`。省略或 `null` 表示列出 workspace root（工作区根目录）。
- 如果 `path` 是字符串，必须通过 `WorkspacePathGuard.resolve_read_path`。
- `recursive` 默认为 `false`。
- `max_entries` 可省略；省略时使用 `FilesystemToolConfig.default_max_entries`。
- `max_entries` 必须 `> 0` 且 `<= FilesystemToolConfig.max_entries_limit`。

成功输出 `data`：

```json
{
  "entries": [
    {"path": "README.md", "kind": "file", "size": 1200},
    {"path": "docs", "kind": "directory", "size": null}
  ],
  "truncated": false
}
```

规则：

- 返回路径必须是 workspace root 相对路径。
- entries（条目）必须稳定排序。
- recursive list（递归列出）不得递归进入 symlink directory（符号链接目录）。
- symlink（符号链接）本身可以作为 `kind = "symlink"` 条目返回，但工具不得跟随它读取目标内容。
- `path` 指向文件时失败，`error_kind = "not_directory"`。

### `read_file`（读取文件）

输入：

```json
{
  "path": "README.md",
  "offset": 0,
  "limit": 12000
}
```

字段语义：

- `path` 必填，必须是字符串，并通过 `WorkspacePathGuard.resolve_read_path`。
- `offset` 默认为 `0`，必须 `>= 0`。
- `limit` 可省略；省略时使用 `FilesystemToolConfig.default_read_limit`。
- `limit` 必须 `> 0` 且 `<= FilesystemToolConfig.max_read_limit`。

成功输出 `data`：

```json
{
  "content": "# atomic-agent\n",
  "offset": 0,
  "bytes_read": 15,
  "truncated": false
}
```

规则：

- 只读取 UTF-8 text file（文本文件）。
- 文件不存在时失败，`error_kind = "not_found"`。
- 路径是目录时失败，`error_kind = "not_file"`。
- UTF-8 解码失败时失败，`error_kind = "decode_failed"`。
- 读取范围超过文件剩余长度时返回已有内容，`truncated = false`。
- 仍有剩余内容未读取时 `truncated = true`。

### `search_files`（搜索文件）

输入：

```json
{
  "query": "AgentAction",
  "path": null,
  "mode": "content",
  "max_matches": 50
}
```

字段语义：

- `query` 必填，必须是非空字符串。
- `path` 可省略或为 `null`。省略或 `null` 表示从 workspace root 搜索。
- 如果 `path` 是字符串，必须通过 `WorkspacePathGuard.resolve_read_path`，且目标必须是 directory（目录）。
- `mode` 必须是 `"name"` 或 `"content"`。
- `max_matches` 可省略；省略时使用 `FilesystemToolConfig.default_max_matches`。
- `max_matches` 必须 `> 0` 且 `<= FilesystemToolConfig.max_matches_limit`。

成功输出 `data`：

```json
{
  "matches": [
    {"path": "src/atomic_agent/models.py", "line": 64, "preview": "class AgentAction(StrictModel):"}
  ],
  "truncated": false,
  "skipped": []
}
```

规则：

- `mode = "name"` 时匹配相对路径字符串，返回 `line = null`。
- `mode = "content"` 时按 UTF-8 文本逐行搜索，返回 1-based line number（从 1 开始的行号）。
- 搜索不得递归进入 symlink directory（符号链接目录）。
- 每个候选文件必须再次通过 `WorkspacePathGuard.resolve_read_path`，被拒绝的文件加入 `skipped`。
- UTF-8 解码失败或读取失败的文件加入 `skipped`，不得把读取失败伪装为完整搜索成功。
- 命中超过 `max_matches` 时停止搜索并设置 `truncated = true`。

### `write_file`（写入文件）

输入：

```json
{
  "path": "docs/generated/output.md",
  "content": "hello\n"
}
```

字段语义：

- `path` 必填，必须是字符串，并通过 `WorkspacePathGuard.resolve_write_path`。
- `content` 必填，必须是字符串。

成功输出 `data`：

```json
{
  "bytes_written": 6,
  "created": true,
  "before_hash": null,
  "after_hash": "sha256:<hex>",
  "diff": "--- a/docs/generated/output.md\n+++ b/docs/generated/output.md\n..."
}
```

规则：

- 允许在授权路径下创建缺失父目录。
- 如果目标路径存在且是目录，失败，`error_kind = "not_file"`。
- 写入使用 UTF-8。
- 写入必须真实落盘。
- `before_hash` 对不存在文件为 `null`。
- `after_hash` 必须基于真实写入后的文件内容计算。
- diff 必须反映写入前后文本变化。

### `apply_patch`（应用补丁）

P0-004 的 patch（补丁）语义是 exact replace（精确替换），不是 unified diff parser（统一 diff 解析器）。

输入：

```json
{
  "path": "docs/generated/output.md",
  "old_text": "old",
  "new_text": "new",
  "replace_all": false
}
```

字段语义：

- `path` 必填，必须是字符串，并通过 `WorkspacePathGuard.resolve_write_path`。
- `old_text` 必填，必须是非空字符串。
- `new_text` 必填，必须是字符串。
- `replace_all` 默认为 `false`，必须是布尔值。

成功输出 `data`：

```json
{
  "replacements": 1,
  "before_hash": "sha256:<hex>",
  "after_hash": "sha256:<hex>",
  "diff": "--- a/docs/generated/output.md\n+++ b/docs/generated/output.md\n..."
}
```

规则：

- 文件必须存在且是 UTF-8 text file（文本文件）。
- `old_text` 匹配 0 次时失败，`error_kind = "patch_not_applied"`，文件内容不变。
- `old_text` 匹配多次且 `replace_all = false` 时失败，`error_kind = "ambiguous_patch"`，文件内容不变。
- `replace_all = true` 时替换全部匹配。
- patch 成功后必须真实落盘，并返回 before/after hash 和 diff。

### `execute_filesystem_action`（执行文件系统动作）

`execute_filesystem_action` 接收 `AgentAction`（智能体动作），只分发 filesystem action（文件系统动作）：

- `AgentActionType.LIST_FILES`
- `AgentActionType.READ_FILE`
- `AgentActionType.SEARCH_FILES`
- `AgentActionType.WRITE_FILE`
- `AgentActionType.APPLY_PATCH`

其他 action 必须失败：

```text
ok = False
error_kind = "unsupported_action"
```

该函数不得执行 `run_command`、`web_fetch` 或 `submit_result`。

## Error Semantics

| `error_kind` | 中文解释 | 触发条件 |
|---|---|---|
| `invalid_input` | 非法工具输入 | 字段缺失、类型错误、limit 越界、mode 非法 |
| `permission_denied` | 权限拒绝 | path guard 返回 deny |
| `not_found` | 未找到 | 目标路径不存在 |
| `not_file` | 不是文件 | 目标路径是目录或非普通文件 |
| `not_directory` | 不是目录 | list/search 的目标不是目录 |
| `decode_failed` | 解码失败 | 目标文件不是 UTF-8 文本 |
| `patch_not_applied` | 补丁未应用 | `old_text` 未匹配 |
| `ambiguous_patch` | 补丁歧义 | `old_text` 多次匹配且 `replace_all = false` |
| `unsupported_action` | 不支持动作 | dispatcher 收到非 filesystem action |
| `io_error` | 文件系统错误 | 真实 IO 操作失败 |

所有失败都必须 fail closed（失败关闭）：不得改写路径、不得扩大 allowed write set（允许写入集合）、不得把失败记录为成功、不得尝试未记录 fallback（兜底）。

## Security and No-Fallback Rules

- filesystem tools 不得读取 `.env`、environment variables（环境变量）、local config files（本地配置文件）或 process defaults（进程默认值）。
- filesystem tools 不得在 path guard（路径守卫）拒绝后尝试替代路径。
- filesystem tools 不得绕过 `WorkspacePathGuard` 自行授权用户提供的路径。
- `write_file` 和 `apply_patch` 不得在 allowed write set 外创建、修改或删除文件。
- `apply_patch` 不得在匹配失败时执行 best-effort fuzzy patch（模糊补丁）。
- 搜索和列出不得递归进入 symlink directory（符号链接目录）。
- 工具结果必须反映真实文件系统状态，不得返回 mock success path（模拟成功路径）。

## Acceptance Criteria

P0-004 完成时必须证明：

- `list_files` 可以列出 workspace root 或 workspace 内目录，返回稳定排序的相对路径。
- `list_files` 对文件路径返回 `not_directory`。
- `list_files` 对 path traversal（路径穿越）返回 `permission_denied`。
- `read_file` 可以读取 UTF-8 文件，并支持 `offset` 与 `limit`。
- `read_file` 对目录返回 `not_file`。
- `read_file` 对缺失文件返回 `not_found`。
- `search_files` 可以按文件名搜索。
- `search_files` 可以按内容搜索并返回 1-based line number（从 1 开始的行号）。
- `search_files` 对空 query 返回 `invalid_input`。
- `write_file` 可以写入 allowed write set 内的精确文件路径。
- `write_file` 可以写入 allowed write set 内的目录子路径。
- `write_file` 对 allowed write set 外路径返回 `permission_denied`。
- `write_file` 返回真实 `after_hash` 和 diff。
- `apply_patch` 可以执行单次 exact replace（精确替换）。
- `apply_patch` 对未匹配 `old_text` 返回 `patch_not_applied`，并保持文件不变。
- `apply_patch` 对多次匹配且 `replace_all = false` 返回 `ambiguous_patch`，并保持文件不变。
- `apply_patch` 在 `replace_all = true` 时替换全部匹配。
- `execute_filesystem_action` 分发五个 filesystem action，并拒绝非 filesystem action。
- symlink escape（符号链接逃逸）由 `WorkspacePathGuard` 拒绝，工具层不绕过该拒绝。
- `pytest -v` 通过。

## Documentation Impact

评审通过并完成实现后，需要更新：

- `docs/04-implementation-backlog/backlog.md`：将 P0-004 标记为 `completed`。
- `docs/04-implementation-spec/INDEX.md`：将本规格从 draft（草案）移动到 completed / archived（已完成 / 已归档）区，或按评审决定调整状态。
- `docs/04-implementation-plan/INDEX.md`：将对应 plan（实施计划）移动到 completed / archived 区。
- `docs/INDEX.md`：移除或调整 P0-004 draft 指针，确保全局当前指针不保留已完成计划。

如果实现过程中发现 filesystem tool contract（文件系统工具契约）需要破坏性语义变更，必须先更新本规格；如果影响长期架构原则，必须先新增或更新 ADR（架构决策记录）。
