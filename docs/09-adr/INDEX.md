# ADR Index

## 1. Directory Purpose

维护 ADR（架构决策记录），记录长期决策、重要架构取舍和替代关系。

## 2. When to Update

产生、替代、废弃或修订重要决策时更新。

## 3. Current Active Documents

| 文档 | 状态 | 用途 | 何时读取 |
|---|---|---|---|
| `INDEX.md` | active | 本目录索引和文档治理规则 | 进入本目录前 |
| `0001-use-standalone-atomic-agent-runtime.md` | accepted | 决定 atomic-agent 作为独立 runtime 项目 | 讨论项目边界或仓库独立性时 |
| `0002-use-provider-agnostic-action-protocol.md` | accepted | 决定第一阶段采用 provider-agnostic JSON action protocol | 讨论 tool calling 或动作协议时 |
| `0003-use-fail-closed-permission-model.md` | accepted | 决定权限模型采用 fail-closed | 讨论权限、安全或沙箱时 |
| `0004-keep-boardroom-os-as-governance-source.md` | accepted | 决定 Boardroom OS 保持治理事实源 | 讨论 Boardroom 集成和完成事件边界时 |

## 4. Completed / Archived Documents

| 文档 | 完成时间 | 保留原因 |
|---|---|---|
| _None_ | - | 当前没有已完成或归档 ADR |

## 5. Update Rules

- 重要决策必须先写 ADR，再更新相关 architecture、contract、acceptance 或 roadmap 文档。
- 新 ADR 文件名使用 `NNNN-kebab-case-title.md`。
- 被替代 ADR 必须标记 superseded（已替代）并指向替代 ADR。
- 未被本索引列出的 ADR 不是权威决策记录。

## 6. AI Reading Guidance

重要决策必须先写 ADR，再更新相关 architecture、contract、acceptance 或 roadmap 文档。
