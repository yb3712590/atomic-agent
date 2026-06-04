# MVP Acceptance Criteria

## Status

active

## Purpose

本文定义 `atomic-agent`（原子智能体）MVP 的完成标准。任何实现必须满足这些标准，不能用 mock success path（模拟成功路径）替代真实验收。

## Functional Acceptance

MVP 通过时必须证明：

- 可以接收 `AgentInvocation`（智能体调用请求）。
- 可以执行至少一个多步 `AgentLoop`（智能体循环）。
- 可以读取文件、写入允许路径、运行声明命令并提交结果。
- 可以把工具输出作为 observation（观察结果）进入下一轮。
- 可以输出 `AgentRunResult`（智能体运行结果）。

## Security Acceptance

必须通过以下负向场景：

| 场景 | 期望 |
|---|---|
| 写入 `AllowedWriteSet`（允许写入集合）之外路径 | deny（拒绝）并记录失败事件 |
| 使用 `../` 逃逸 workspace root（工作区根目录） | deny 并记录失败事件 |
| 通过 symlink（符号链接）逃逸 | deny 并记录失败事件 |
| 运行未声明命令 | deny 并记录失败事件 |
| provider 输出自由 shell string（命令字符串） | deny 并记录失败事件 |
| 访问未允许网络目标 | deny 并记录失败事件 |
| 超过 max steps（最大步数） | fail closed |
| provider 输出无效 JSON | 受限 retry，超限后 fail closed |

## Event Acceptance

成功或失败运行都必须产生 event stream（事件流）。事件流必须包含：

- `run.started`
- provider turn event（模型轮次事件）
- action event（动作事件）
- permission event（权限事件）
- tool attempt event（工具调用事件）
- terminal event（终止事件）

如果发生文件变更，必须包含 `workspace.mutation.recorded`。

## Boardroom Integration Acceptance

用于 Boardroom OS（Boardroom 操作系统）时：

- `AgentRunResult` 不能直接声明 ticket completed（工单完成）。
- provider output（模型输出）不能单独作为 implementation evidence（实现证据）。
- source file（源码文件）必须能追溯到 tool attempt（工具调用尝试记录）和 workspace mutation（工作区变更）。
- command evidence（命令证据）必须包含 exit code、stdout/stderr artifact hash（产物哈希）。

## Documentation Acceptance

实现 MVP 时必须同步更新：

- `README.md` 的最小示例命令。
- `docs/INDEX.md` 的当前活跃文档指针。
- 相关子目录 `INDEX.md`。
- 如有长期决策，先更新 `docs/09-adr/`。

## Prohibited Success Conditions

以下情况不能算通过：

- 只返回文本摘要，没有真实 tool attempt。
- 只写测试 fixture（测试夹具）模拟成功。
- 命令未真实执行但记录为成功。
- 权限拒绝后自动改用未记录 fallback。
- 事件流缺失或不可解析。
