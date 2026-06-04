# Workspace Path Guard Specification

## Status

implemented

## Purpose

本文定义 P0-003 `workspace path guard`（工作区路径守卫）的实现规格。该守卫负责把 agent action（智能体动作）中的文件路径请求转换为可审计的 permission decision（权限决策），为后续 filesystem tools（文件系统工具）提供唯一的路径安全边界。

## Scope

P0-003 只覆盖 workspace path（工作区路径）权限边界。

包含：

- 接收 workspace root（工作区根目录）和 allowed write set（允许写入集合）。
- 只接受 relative path（相对路径）。
- 拒绝 empty path（空路径）、absolute path（绝对路径）和 `..` path traversal（路径逃逸）。
- 规范化目标路径，并确认其仍位于 workspace root 内。
- 检测 symlink escape（符号链接逃逸）。
- 对 read path（读路径）和 write path（写路径）分开决策。
- 写入必须命中 allowed write set（允许写入集合）。
- 返回结构化 permission decision（权限决策），供后续 `permission.decided` event（权限决策事件）使用。

不包含：

- `list_files`、`read_file`、`search_files`、`write_file` 或 `apply_patch` 工具执行。
- 文件内容读取、写入、patch（补丁）应用或 diff（差异）生成。
- event recorder（事件记录器）和 JSONL event stream（JSONL 事件流）输出。
- command policy（命令策略）、network policy（网络策略）或 budget limits（预算限制）。
- approval model（审批模型）交互。

这些能力分别由 P0-004、P0-005、P0-006、P0-008 和 P1-001 覆盖。

## Authoritative Inputs

本规格依据以下已索引文档：

- `docs/02-architecture/permission-and-sandbox-architecture.md`（权限与沙箱架构）。
- `docs/04-implementation-spec/mvp-runtime-spec.md`（MVP 运行时规格）。
- `docs/04-implementation-acceptance/mvp-acceptance.md`（MVP 验收标准）。
- `docs/09-adr/0003-use-fail-closed-permission-model.md`（失败关闭权限模型 ADR）。

## Public API

新增模块：

```text
src/atomic_agent/path_guard.py
```

公开类型：

```python
class PathDecisionType(str, Enum):
    ALLOW = "allow"
    DENY = "deny"


@dataclass(frozen=True)
class PathDecision:
    decision: PathDecisionType
    requested_path: str
    normalized_path: str | None
    reason: str
    matched_policy: str | None = None


class PathGuardConfigError(ValueError):
    ...


class WorkspacePathGuard:
    def __init__(self, workspace_root: str | Path, allowed_write_set: list[str]):
        ...

    def resolve_read_path(self, requested_path: str) -> PathDecision:
        ...

    def resolve_write_path(self, requested_path: str) -> PathDecision:
        ...
```

`WorkspacePathGuard`（工作区路径守卫）只返回 permission decision（权限决策），不执行真实读写。调用方必须根据 `decision` 字段决定是否继续执行工具。

## Path Input Rules

### Relative path only（仅相对路径）

`requested_path` 必须是非空字符串，并且必须是 relative path（相对路径）。非字符串输入必须 fail closed（失败关闭）并返回 `invalid_path_type_denied`。

以下输入必须拒绝：

- `""`
- `"   "`
- `"."`
- `"./"`
- `".//"`
- `"/tmp/file.txt"`
- Windows absolute path（Windows 绝对路径），例如 `"C:/tmp/file.txt"`
- Windows drive-relative path（Windows 驱动器相对路径），例如 `"C:tmp/file.txt"`
- Windows rooted path（Windows 根相对路径），例如 `"\\tmp\\file.txt"`
- `"../outside.txt"`
- `"docs/../outside.txt"`

拒绝语义：

```text
decision = "deny"
reason = "invalid_path_type_denied" | "empty_path_denied" | "absolute_path_denied" | "path_escape_denied"
```

### Workspace containment（工作区包含关系）

规范化后的目标路径必须位于 workspace root（工作区根目录）内。路径比较必须基于真实路径边界，而不是字符串前缀。

例如，workspace root 为 `/repo/workspace` 时：

- `/repo/workspace/docs/file.md` 允许。
- `/repo/workspace-other/file.md` 拒绝。

拒绝语义：

```text
decision = "deny"
reason = "path_outside_workspace_denied"
```

### Symlink escape（符号链接逃逸）

如果目标路径或目标路径的既有父目录穿越 symlink（符号链接）后落到 workspace root 外，必须拒绝。

拒绝语义：

```text
decision = "deny"
reason = "symlink_escape_denied"
```

### Missing targets（不存在的目标）

path guard（路径守卫）不负责报告文件是否存在。对于不存在的目标路径，守卫必须解析最深的 existing parent（已存在父目录）以检测 symlink escape（符号链接逃逸），再根据 workspace containment（工作区包含关系）做权限决策。后续 filesystem tool（文件系统工具）负责返回 not found（未找到）或创建文件。

## Read Path Semantics

`resolve_read_path`（解析读路径）只判断 requested path（请求路径）是否在 workspace root 内并且没有逃逸。读路径不要求命中 allowed write set（允许写入集合）。

允许结果必须包含：

```text
decision = "allow"
reason = "read_path_allowed"
normalized_path = <absolute normalized path>
matched_policy = "workspace_root"
```

## Write Path Semantics

`resolve_write_path`（解析写路径）必须先满足所有 read path（读路径）安全规则，再命中 allowed write set（允许写入集合）。读权限不自动授予写权限。

allowed write set（允许写入集合）条目必须是相对路径，且不得包含 `..`。非法 policy（策略）条目是 invocation configuration defect（调用配置缺陷），必须在 `WorkspacePathGuard` 初始化时抛出 `PathGuardConfigError`，不得静默忽略。`"./"`、`".//"`、Windows drive-relative path（Windows 驱动器相对路径）和 Windows rooted path（Windows 根相对路径）同样必须视为非法配置。

allowed write set 支持两种条目：

| 形式 | 中文解释 | 匹配语义 |
|---|---|---|
| `docs/output.md` | 精确文件授权 | 只允许写入该路径 |
| `docs/generated/` | POSIX 风格目录授权 | 允许写入该目录及其子路径 |
| `docs\\generated\\` | Windows 风格目录授权 | 允许写入该目录及其子路径 |

目录授权必须使用路径边界匹配。`docs/generated/` 不允许写入 `docs/generated-other/file.md`。

允许结果必须包含：

```text
decision = "allow"
reason = "write_path_allowed"
normalized_path = <absolute normalized path>
matched_policy = <matched allowed write set entry>
```

未命中 allowed write set 时必须拒绝：

```text
decision = "deny"
reason = "write_not_allowed"
matched_policy = None
```

## Error Semantics

| Reason | 中文解释 | 触发条件 |
|---|---|---|
| `invalid_path_type_denied` | 非字符串路径被拒绝 | `requested_path` 不是字符串 |
| `empty_path_denied` | 空路径被拒绝 | 输入为空、空白、`.`、`./` 或 `.//` |
| `absolute_path_denied` | 绝对路径被拒绝 | 输入是 POSIX absolute path、Windows absolute path、Windows drive-relative path 或 Windows rooted path |
| `path_escape_denied` | 路径逃逸被拒绝 | 输入包含 `..` 片段 |
| `path_outside_workspace_denied` | 工作区外路径被拒绝 | 规范化后不在 workspace root 内 |
| `symlink_escape_denied` | 符号链接逃逸被拒绝 | 解析 symlink 后目标在 workspace root 外 |
| `read_path_allowed` | 读路径允许 | 请求路径通过 workspace root 守卫 |
| `write_path_allowed` | 写路径允许 | 请求路径通过 workspace root 与 allowed write set 守卫 |
| `write_not_allowed` | 写路径未授权 | 请求路径未命中 allowed write set |

所有拒绝都必须 fail closed（失败关闭）：不得返回替代路径、不得改写为其他允许路径、不得自动扩大 allowed write set。

## Security and No-Fallback Rules

- path guard 不得读取 `.env`、environment variables（环境变量）、local config files（本地配置文件）或 process defaults（进程默认值）。
- path guard 不得在路径被拒绝后尝试 fallback（兜底）到 workspace root、临时目录或当前工作目录。
- path guard 不得把字符串前缀匹配当作路径边界匹配。
- path guard 不得把 read permission（读权限）升级为 write permission（写权限）。
- path guard 不得静默忽略非法 allowed write set 条目。

## Acceptance Criteria

P0-003 完成时必须证明：

- workspace root 内的普通相对读路径允许。
- workspace root 内不存在的相对读路径允许，由后续 filesystem tool（文件系统工具）报告 not found（未找到）或创建文件。
- absolute path（绝对路径）、Windows drive-relative path（Windows 驱动器相对路径）和 Windows rooted path（Windows 根相对路径）被拒绝。
- 非字符串路径被拒绝。
- empty path（空路径）、`.`、`./` 和 `.//` 被拒绝。
- 包含 `..` 的路径被拒绝。
- 规范化后落在 workspace root 外的路径被拒绝。
- symlink escape（符号链接逃逸）被拒绝。
- 写入 allowed write set 中的精确文件路径允许。
- 写入 allowed write set 中的目录子路径允许。
- 写入 allowed write set 外路径被拒绝。
- 目录授权使用路径边界匹配，不接受字符串前缀伪匹配。
- 非法 allowed write set 配置初始化失败，且不得静默丢弃。
- `pytest -v` 通过。

## Documentation Impact

评审通过并完成实现后，需要更新：

- `docs/04-implementation-backlog/backlog.md`：将 P0-003 标记为 `completed`。
- `docs/04-implementation-spec/INDEX.md`：将本规格从 draft（草案）调整为 implemented（已实现）或按评审决定调整状态。
- `docs/04-implementation-plan/INDEX.md`：将对应 plan（实施计划）移动到 completed / archived（已完成 / 已归档）区。

如果实现过程中发现 filesystem policy（文件系统策略）需要破坏性语义变更，必须先更新 ADR（架构决策记录）。
