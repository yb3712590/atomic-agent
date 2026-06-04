# Agent Action Protocol

## Status

active

## Purpose

本文定义 provider-agnostic `AgentAction`（模型供应商无关智能体动作）协议。该协议让 runtime 不依赖 provider 原生 tool calling（工具调用），先通过 JSON 动作完成最小闭环。

## Envelope

所有动作使用同一 envelope（信封结构）：

```json
{
  "action_id": "step-0001",
  "action": "read_file",
  "reason_summary": "Inspect the current README before editing.",
  "input": {}
}
```

字段：

| Field | 中文解释 | 要求 |
|---|---|---|
| `action_id` | 动作标识 | 单次运行内唯一。 |
| `action` | 动作类型 | 必须属于允许动作集合。 |
| `reason_summary` | 简短原因 | 不得包含 chain-of-thought（思维链）。 |
| `input` | 输入 | 由具体动作 schema（模式）定义。 |

多余字段默认拒绝，除非协议版本明确允许。

## P0 Actions

### list_files

```json
{
  "action_id": "step-0001",
  "action": "list_files",
  "reason_summary": "Inspect workspace structure.",
  "input": {"path": ".", "max_entries": 200}
}
```

用途：列出 workspace（工作区）内文件。

权限：路径必须在 workspace root（工作区根目录）内。

### read_file

```json
{
  "action_id": "step-0002",
  "action": "read_file",
  "reason_summary": "Read the target file before patching.",
  "input": {"path": "README.md", "offset": 0, "limit": 12000}
}
```

用途：读取文件片段。

权限：路径必须在允许读取范围内。

### search_files

```json
{
  "action_id": "step-0003",
  "action": "search_files",
  "reason_summary": "Find references to the runtime port.",
  "input": {"query": "AgentRuntimePort", "path": ".", "max_matches": 50}
}
```

用途：搜索文件名或内容。

权限：搜索范围必须在 workspace root 内。

### write_file

```json
{
  "action_id": "step-0004",
  "action": "write_file",
  "reason_summary": "Create the initial contract file.",
  "input": {"path": "docs/03-contracts/example.md", "content": "..."}
}
```

用途：完整写入文件。

权限：路径必须在 `AllowedWriteSet`（允许写入集合）内。

### apply_patch

```json
{
  "action_id": "step-0005",
  "action": "apply_patch",
  "reason_summary": "Update the contract section only.",
  "input": {"path": "README.md", "patch": "..."}
}
```

用途：局部修改文件。

权限：路径必须在 `AllowedWriteSet` 内，patch 后必须记录 diff（差异）。

### run_command

```json
{
  "action_id": "step-0006",
  "action": "run_command",
  "reason_summary": "Run the declared tests.",
  "input": {"command_id": "test"}
}
```

用途：运行声明命令。

权限：只能使用 `command_id`（命令标识），不能传自由 shell string（命令字符串）。

### web_fetch

```json
{
  "action_id": "step-0007",
  "action": "web_fetch",
  "reason_summary": "Fetch public documentation for a referenced API.",
  "input": {"url": "https://example.com/docs", "method": "GET"}
}
```

用途：获取公开网络信息。

权限：必须通过 `NetworkPolicy`（网络策略）。

### submit_result

```json
{
  "action_id": "step-0008",
  "action": "submit_result",
  "reason_summary": "Submit the completed work summary.",
  "input": {
    "summary": "Updated the contract and indexes.",
    "produced_paths": ["docs/03-contracts/example.md"],
    "evidence_refs": ["evt_001"]
  }
}
```

用途：提交运行结果。

权限：至少应有可审计事件；实现类任务通常必须有 workspace mutation（工作区变更）或明确说明无文件变更。

## Invalid Actions

以下情况必须拒绝：

- 无效 JSON。
- 未知 action。
- 多余字段。
- path 逃逸 workspace root。
- 写入路径不在 allowed write set。
- 命令不是 command_id。
- 网络目标不被允许。
- reason_summary 包含敏感信息或思维链。

## Future Extensions

后续可以新增：

- `run_service`（运行服务）
- `http_probe`（HTTP 探测）
- `mcp_call`（MCP 调用）
- `external_agent_run`（外部智能体运行）

新增动作必须先更新本协议和对应 `INDEX.md`，重要能力变化需要 ADR。
