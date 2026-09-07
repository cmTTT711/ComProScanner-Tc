# Evidence 流程恢复记录（2026-09-05）

按用户澄清，恢复的是 9 月 4 日的 Evidence 流程，基准输出 `outputs/runs/tc_fulltext_001_030_20260904`（61 条预测），不是更早的 TC_CONTEXT_WINDOW_30。

源码、测试、项目配置和 README 已恢复至 `7c979bea`。逐文件与 Git 对象核验一致。主入口为 `python -m comproscanner.cli` 或 `comproscanner`。

主链路：PDF / 统一 Article → 可选 Evidence 工具 → 每条 Evidence 的 LiteLLM identifier / extractor → FactProcessor(identity) → 去重 JSON / review。默认 material-normalizer=identity，不强制调用外部材料解析服务，不执行本次新增的 LegacyEvidenceExtractor 和 clean_data(all)。

恢复前完整源码、测试和配置备份在 `work/before_original_restore_20260905`，包括未提交的用户修改及近期修复。中间误恢复的旧原生流程已移出活动目录，保存在 `work/superseded_original_restore_20260905`。所有 Gold、历史及最新运行结果保留。本次没有重跑付费模型，也未宣称已经复现历史质量分数。

入口验证（仅显示计划，不执行）：

```powershell
python -m comproscanner.cli run --source manual_pdf --folder tmp/offline_reprocess_001_030/pdfs --provider rule_text --provider physbert --provider table --provider equation --material-normalizer identity --run-id evidence_restored_check
```

回退也移除了之后的生产修复，历史版本自身的已知限制仍存在。本次目标仅为恢复指定 Evidence 基线，未再次改写流程。

验证结果：727 个测试通过，17 个 integration 测试未运行；入口计划检查通过。所有恢复文件与 7c979bea 的 Git 原始内容一致。测试日志：tmp/evidence_restore_tests.log。
