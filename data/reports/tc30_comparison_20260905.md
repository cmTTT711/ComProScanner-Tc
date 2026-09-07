# 前 30 篇重跑与历史结果比较（2026-09-05）

结论：本轮完整执行到 JSON、review 和 Gold 评估，但有 14 条 Evidence 失败；质量没有提升，温度命中诊断明显退步，尚不能认定生产可用。保留全部原始结果，不做数据净化、不自动重复付费运行。

## 执行范围

- Run：tc_single_evidence_30_20260905；原先常用的前 30 篇 PDF，30 篇统一 Article 均成功生成，prepare failures 为 0。
- 无 Article 初筛；每条 Evidence 独立进入旧抽取、格式化、材料恢复和清洗流程。
- 与 2026-09-04 基线一致启用 rule_text、physbert、table、equation；本轮未启用 figure，不能用本轮证明图像工具可用。
- 共 716 条：710 text（规则/RAG 合并来源）、2 table、4 equation。702 条完成、14 条失败；完成包括正常 NO_DATA。
- 有数据的 Evidence：text 38、table 2、equation 1。最终 JSON 78 条，比较时按完整字段去重后 77 条。
- 标识模型 qwen-flash；抽取/格式化/公式模型 deepseek-v4-flash，thinking disabled；3 个并发 worker；无小样本请求总上限，有正常超时和有限重试。
- 付费抽取及汇总耗时 489.5 秒（约 8.2 分钟），不包括此前 PDF 解析与 RAG 准备。

## 可直接对照的温度诊断

三组原始结果使用同一脚本按论文身份对齐。严格 Gold 的 46 条材料事实，折叠为 45 个“论文、温度、单位”事件。此诊断忽略材料、条件、限定词，不能作为材料抽取正确率；未按物理等价换算 K/°C。FP 表示 Gold 未匹配，并非每条都已人工证实错误。

| 结果 | 命中 TP | 未匹配 FP | 漏掉 FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| 旧成熟流程保留原始结果 | 39 | 1 | 6 | 97.50% | 86.67% | 91.76% |
| 2026-09-04 上次运行 | 43 | 3 | 2 | 93.48% | 95.56% | 94.51% |
| 本次逐 Evidence 运行 | 24 | 44 | 21 | 35.29% | 53.33% | 42.48% |

与上次相比，温度事件少命中 19 个，诊断 F1 下降 52.03 个百分点。本次命中的 Gold 温度事件都是上次已命中的，没有新增命中。

完整字段字面评分 F1：旧成熟原始结果 15.91%、上次 7.48%、本次 9.76%。这些数值受材料名称、公式表达和限定词差异严重影响，不适合直接解释为科学准确率。旧人工复核报告 F1 93.02% 使用另一套人工复核、去重及排除口径，不与本次自动评分直接相减。

## 已核实的具体问题

1. **没有 Evidence 支持的数据进入最终结果。** 第 24 篇 `10_1063_5_0133946_FULL_TEXT_0001_TEXT` 只有标题、作者和机构等信息，没有 Tc 数据。identifier 返回 yes，extractor 却生成 BiFeO3 / Nd 掺杂系列的 21 条温度（1103 K 至 50 K），formatter 保留了它们。原始阶段响应已经证实问题出现在抽取阶段；确切诱因尚未定位，不能直接归因于并发、模型或架构中的单一因素。
2. **有目标温度的 Evidence 返回空数据。** 第 12 篇 `_FULL_TEXT_0011_TEXT` 包含 y=0.24、x=0.01 样品的 853.1 K 铁电相变，identifier=yes，但 extractor 返回空字典，最终 NO_DATA。该段缺母体化学式；这次漏抽发生在材料服务调用之前。
3. **材料服务失败造成有效数据丢失。** 第 24 篇 `_FULL_TEXT_0009_TEXT` 包含 774 K Tc，但材料解析 HTTP 503 导致整条失败。
4. **材料恢复不只是名称格式差异。** 第 10 篇 683 K 的 Gold 为 `0.7BiFeO3-0.3(Ba0.85Ca0.15)TiO3`，输出 `Bi0.7Fe0.7O2.1-Ba0.21Ca0.09Ti0.3O0.9`，Ba/Ca 比例不等价。即使温度命中也不能算材料正确。第 28 篇 671.5 K 输出 `BiFeO3-BiK0.5Ti0.5O3`，也未正确保留 Gold 的母体比例/化学式。
5. **公式工具不稳定。** 4 条公式 Evidence 仅 1 条完成有数据，3 条失败；其中一条未真正调用公式工具。不能将整个工具链判定为全部可用。

失败归类：10 条材料解析 HTTP 503、3 条模型输出格式/结构解析失败、1 条选中公式 Evidence 未调用公式工具。失败分布在 9 篇论文。模型 completion 调用本身没有记录异常，并不意味着后续工具和 JSON 处理成功。

这些证据表明退步不能只用评分名称差异解释。当前运行同时改变了模型运行配置、材料清洗配置等因素，与历史结果不是仅改变 Evidence 粒度的严格消融实验，因此尚不能断言“单条 Evidence 模式本身不行”。应先修正有据抽取约束、局部材料定义补充及材料服务容错，再用固定小样本复测；整篇合并不是此次证据支持的必然结论。

## 用量与输出

- 980 次 completion 调用：Qwen 716 次、DeepSeek 264 次。此计数不保证等于底层 HTTP 请求数（内部重试可能不同）。
- 接口返回总 tokens：1,568,238；输入 1,508,538，输出 59,700。
- Qwen 800,074 tokens；DeepSeek 768,164 tokens。未取得账单金额，不能据此给出准确费用；这些是项目模型 API 用量，不是本次 Codex 对话用量统计。
- `review.xlsx` 已生成，包含 evidence、evidence_ids、verification_note 和人工 decision/review_note 列；Evidence 并未丢失。
- 逐 Gold 比较：`gold_comparison.csv`；完整评分：`comparison_metrics.json`；简表：`comparison_summary.json`。
- 用量：`benchmark_usage_summary.json`、`model_usage_events.jsonl`；运行状态：`batch_done.json`。
- 原始证据：`evidence/all.json`；逐条流程原始响应：`papers/legacy-evidence-*.json` 及 `raw_results.json`；最终结果：`predictions.json`。

本报告进行了关键异常抽查，并非对全部 78 条结果完成新的人工 Gold 审核。现有 Gold、历史结果和本次原始输出均保持不变。


## 进一步归因：清洗前后追踪（同日补充）

对照上次命中、本次最终漏掉的 19 个 Gold 温度事件，并检查本次 `raw_results.json` 和 `cleaning_report.json`：**13 个在清洗前已经存在，清洗后消失**。本次清洗前命中 37/45，清洗后 24/45；这不代表清洗前材料名称全部正确。

13 个事件分别为：第 3 篇 129°C；第 4 篇 720/746 K；第 10 篇 687/690/692 K；第 15 篇 689/698/711 K；第 19 篇 501/778 K；第 26 篇 355°C；第 29 篇 795.2 K。原因记录包括 element_validation_strict、abbreviation_filtering、unresolved_brackets_or_operators。含样品描述、wt.% 添加剂或未解析变量的条目被整体过滤；上次 summary 记录 material_normalizer=identity，本次为 legacy。接通旧清洗流程时没有充分验证其过滤语义适合复合材料及待恢复名称，是此次集成的主要回归点。

剩余 6 个漏失事件：第 12 篇 853.1 K 抽取返回空；第 15 篇 732 K 与第 27 篇 742.6 K 对应输出解析失败；第 24 篇 774 K、第 25 篇 227/650°C 对应材料服务 503。这是按既有 Evidence 链路归类，并非假设修复服务后一定能得到正确材料。

精度方面，第 24 篇标题页 Evidence 无依据的 21 个温度事件，占当前 44 个未匹配预测中的 21 个，显著拉低 precision。其 BiFeO3/Nd 系列与 preset 示例相似，存在示例污染的可能，但尚未证明具体诱因。

两次每篇 Evidence 数一致；本次仍有 180 个 physbert 来源记录。run_config 的 with_rag=false 是未使用该快捷开关；显式 provider 已包含 physbert，不能据此说本次关闭了 RAG。旧完整模型调用配置未保留，不能把差异武断归因于 thinking 设置或单条 Evidence 架构。

追踪数据见 `regression_stage_audit.json`。以上是离线审计，没有新增付费调用。
