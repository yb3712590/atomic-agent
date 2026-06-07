# atomic-agent

## 1. atomic-agent 是什么

`atomic-agent`（原子智能体）是一个小型、可审计、权限受控的通用 agent runtime（智能体运行时）项目。它的目标不是做大型多智能体平台，而是提供最小但真实的工作循环：读取上下文、执行受控工具、观察结果、修复输出、记录事件，并在失败时 fail closed（失败关闭）。

第一阶段重点能力包括：

- filesystem tools（文件系统工具）：受 workspace root（工作区根目录）和 allowed write set（允许写入集合）约束的读写与 patch（补丁）操作。
- command tools（命令工具）：只执行 policy（策略）允许的命令，不提供自由 shell（自由命令行）。
- web tools（网络工具）：按 allowlist（允许列表）或显式权限访问网络。
- event stream（事件流）：记录 provider turn（模型调用轮次）、tool attempt（工具调用尝试记录）、workspace mutation（工作区变更）、command result（命令结果）等事实。
- permission policy（权限策略）：所有高风险动作必须经过明确策略，不依赖隐式 fallback（降级）。

## 2. 它和 boardroom-os 的关系

`boardroom-os`（Boardroom 操作系统）负责 governance（治理）、contract（契约）、evidence（证据）、reducer（归约器）和 closeout gate（收尾门禁）。`atomic-agent`（原子智能体）负责在受控边界内执行实际工作，并把过程事实以标准事件和结果返回。

推荐边界是：

```text
boardroom-os
  -> AgentRuntimePort（智能体运行时端口）
  -> AgentInvocation（智能体调用请求）
  -> atomic-agent runtime（原子智能体运行时）
  -> AgentRunResult（智能体运行结果）
  -> boardroom-os evidence / closeout（证据与收尾门禁）
```

原则：

- `boardroom-os` 是治理事实源，不被 `atomic-agent` 替代。
- `atomic-agent` 不直接宣布 ticket completed（工单完成）或 closeout committed（收尾提交）。
- `atomic-agent` 只提交可审计的 work result（工作结果）、event stream（事件流）和 artifact references（产物引用）。
- 所有外部 coding agent（编码智能体）或开源 agent framework（智能体框架）都必须被包在权限、事件和证据边界内。

## 3. 如何运行最小示例

当前仓库提供一个 deterministic fake provider loop（确定性假模型供应商循环）作为 minimal example（最小示例）。它不证明真实模型能力；它用于证明 `AgentLoop`（智能体循环）会真实执行受控工具、记录 JSONL event stream（JSONL 事件流）、写入 artifact（产物），并输出 `AgentRunResult`（智能体运行结果）。

从仓库根目录运行：

```bash
rm -rf /tmp/atomic-agent-minimal-example
PYTHONPATH=src python -m atomic_agent.examples.minimal_fake_loop \
  --run-id minimal_example \
  --workspace /tmp/atomic-agent-minimal-example/workspace \
  --event-stream /tmp/atomic-agent-minimal-example/events/events.jsonl \
  --artifact-root /tmp/atomic-agent-minimal-example/artifacts \
  --result /tmp/atomic-agent-minimal-example/result.json
```

成功时 stdout（标准输出）是 JSON：

```json
{"artifact_root": "/tmp/atomic-agent-minimal-example/artifacts", "event_stream_path": "/tmp/atomic-agent-minimal-example/events/events.jsonl", "result_path": "/tmp/atomic-agent-minimal-example/result.json", "status": "completed", "workspace_output_path": "/tmp/atomic-agent-minimal-example/workspace/work/output.txt"}
```

该示例的真实执行路径是：

1. fake provider（假模型供应商）请求 `write_file`（写文件），写入 `work/output.txt = draft`。
2. fake provider 请求 `run_command`（运行声明命令）执行 `check-output`，命令真实返回 exit code `3`。
3. command result（命令结果）作为 observation（观察结果）进入下一轮。
4. fake provider 请求 `apply_patch`（应用补丁），将 `draft` 修复为 `fixed`。
5. fake provider 再次请求 `run_command`，命令真实返回 exit code `0`。
6. fake provider 请求 `submit_result`（提交结果），runtime 写出 `AgentRunResult`（智能体运行结果）。

可检查的输出包括：

- `/tmp/atomic-agent-minimal-example/result.json`：结构化 `AgentRunResult`。
- `/tmp/atomic-agent-minimal-example/events/events.jsonl`：JSONL event stream（JSONL 事件流）。
- `/tmp/atomic-agent-minimal-example/artifacts/`：provider output（模型输出）、observation（观察结果）、diff（差异）、command stdout/stderr（命令输出）和 result artifact（结果产物）。
- `/tmp/atomic-agent-minimal-example/workspace/work/output.txt`：最终内容为 `fixed`。

该示例仍必须满足：真实执行、真实退出码、真实事件输出；不得以静态文本、模拟结果或 silent fallback（静默降级）伪装成功。

## 4. 如何运行真实 provider gate（手动/夜间）

除 deterministic fake provider loop（确定性假模型供应商循环）外，本仓库还提供默认禁用的 OpenAI-compatible real provider gate（OpenAI 兼容真实模型供应商门禁）。它用于验证真实 provider streaming（流式响应）、provider-agnostic `AgentAction`（供应商无关智能体动作）、受控工具执行、JSONL event stream（JSONL 事件流）和 evidence summary（证据摘要）链路。

该门禁不同于 fake provider minimal example（假供应商最小示例）：

- fake provider example 默认本地运行、确定性、无网络。
- real provider gate 必须显式提供 OpenAI-compatible provider（OpenAI 兼容供应商）配置和 API key（接口密钥）。
- real provider gate 不进入默认 base CI（基础持续集成）联网路径。
- provider output（模型输出）不能单独作为 implementation evidence（实现证据）；必须结合 tool attempt（工具尝试）、workspace mutation（工作区变更）、event stream integrity（事件流完整性）和 artifact hash（产物哈希）判断。

安装可选依赖：

```bash
python -m pip install ".[test,real-provider]"
```

手动运行 standalone loop（独立循环）：

```bash
rm -rf /tmp/atomic-agent-real-provider
export ATOMIC_AGENT_REAL_PROVIDER_API_KEY="replace-with-real-key"
PYTHONPATH=src python -m atomic_agent.examples.minimal_real_provider_loop \
  --run-id real_provider_example \
  --workspace /tmp/atomic-agent-real-provider/workspace \
  --event-stream /tmp/atomic-agent-real-provider/events/events.jsonl \
  --artifact-root /tmp/atomic-agent-real-provider/artifacts \
  --result /tmp/atomic-agent-real-provider/result.json \
  --base-url https://provider.example/v1 \
  --api-key-env ATOMIC_AGENT_REAL_PROVIDER_API_KEY \
  --model provider-model \
  --context-window-tokens 400000 \
  --max-output-tokens 8192 \
  --stream-idle-timeout-seconds 30 \
  --total-timeout-seconds 3600 \
  --max-steps 4
```

成功时 stdout（标准输出）是 JSON，包含：

```json
{"artifact_root":"/tmp/atomic-agent-real-provider/artifacts","event_stream_path":"/tmp/atomic-agent-real-provider/events/events.jsonl","result_path":"/tmp/atomic-agent-real-provider/result.json","status":"completed","workspace_output_path":"/tmp/atomic-agent-real-provider/workspace/work/real-provider-output.txt"}
```

运行 pytest integration gate（集成门禁）：

```bash
ATOMIC_AGENT_RUN_REAL_PROVIDER=1 \
ATOMIC_AGENT_REAL_PROVIDER_BASE_URL="https://provider.example/v1" \
ATOMIC_AGENT_REAL_PROVIDER_API_KEY="replace-with-real-key" \
ATOMIC_AGENT_REAL_PROVIDER_MODEL="provider-model" \
python -m pytest tests/test_real_provider_integration.py -m real_provider -q
```

未设置 `ATOMIC_AGENT_RUN_REAL_PROVIDER=1` 时，该测试必须 skip（跳过）。认证失败、缺失凭据、网络连接失败、base URL 错误、stream idle timeout（流空闲超时）或 total timeout（总超时）不能算作 gate pass（门禁通过）。本地可使用 `.env.*` 文件保存临时 provider config（供应商配置），但该文件必须保持 git ignored（被 Git 忽略），且不是未来正式调用配置格式。

## 5. 文档入口在哪里

文档入口是：

- `docs/INDEX.md`（文档总索引）

阅读规则：

1. 新会话先读 `AGENTS.md`（智能体协作规则）。
2. 再读 `docs/INDEX.md`（文档总索引）。
3. 只读取 `docs/INDEX.md` 和相关子目录 `INDEX.md` 明确列出的 authoritative documents（权威文档）。
4. 没有被必要 `INDEX.md` 列出的文档，不是当前权威文档。
