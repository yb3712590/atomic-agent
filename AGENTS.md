# atomic-agent Agent Instructions

这些规则适用于本仓库内的所有 agent（智能体）和自动化编辑。

## 文档治理硬规则

1. 不要随意新增文档。新增文档前必须确认它属于哪个 `docs/` 子目录，以及它是否真的需要成为长期文档。
2. 不要绕过 `docs/INDEX.md`（文档总索引）。新会话和文档修改都必须以 `docs/INDEX.md` 为入口。
3. 修改任何文档时，必须同步更新必要的 `INDEX.md`：
   - `docs/INDEX.md`（文档总索引），当全局入口、当前指针、目录规范或权威文档集合变化时更新。
   - 对应子目录的 `INDEX.md`（目录索引），当该目录内新增、修改、归档、废弃或替代文档时更新。
4. 长期决策和重要架构决策必须先写入 `docs/09-adr/`（架构决策记录），再按规范更新 `docs/INDEX.md` 和相关子目录 `INDEX.md`。
5. 没有被 `docs/INDEX.md` 或对应子目录 `INDEX.md` 列出的文档，都不是 authoritative document（权威文档）。它们只能作为草稿、临时材料或历史参考。
6. 不要创建第二套文档事实源。不要新增 `doc/` 目录；本仓库统一使用 `docs/`。
7. 不要用 silent fallback（静默降级）、mock success path（模拟成功路径）或未验证文本替代真实运行、真实事件和真实验收。

## 更新顺序

文档变更推荐顺序：

1. 判断变更类型：overview（总览）、concept（概念）、architecture（架构）、contract（契约）、implementation（实现）、testing（测试）、roadmap（路线图）、project log（项目日志）、reference（参考资料）或 ADR（架构决策记录）。
2. 如果是长期决策，先创建或更新 `docs/09-adr/` 下的 ADR。
3. 修改目标文档。
4. 更新目标文档所在子目录的 `INDEX.md`。
5. 如影响全局入口或当前权威指针，更新 `docs/INDEX.md`。
6. 检查没有新增未索引的权威文档。

## 权威性规则

- `docs/INDEX.md` 是文档入口和全局导航事实源。
- 子目录 `INDEX.md` 是该目录内文档状态事实源。
- ADR（架构决策记录）用于长期或重要决策；被 ADR 替代的旧文档必须在索引中标记为 superseded（已替代）。
- 草稿可以存在，但必须在索引中标注 draft（草案）；未索引草稿不应被实现任务引用。
