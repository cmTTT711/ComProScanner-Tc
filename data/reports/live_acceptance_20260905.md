# 2026-09-05 小样本真实调用验收

**结论：真实抽取链路可以执行，当前科学结果和材料恢复未通过生产验收。暂不进入项目净化，也不能声称相较原流程质量提升。**

## 测试范围与费用记录

从常用前 30 篇中选择第 1、4、12、19、30 篇的 **7 条原始 Evidence**：3 条 Tc 文本、1 条 equation、1 条 table、1 张 figure、1 条带隙文本。每条独立送入现有抽取流程，没有按文章合并抽取。

本轮复用已经生成的统一 Article，重新执行本地 Evidence 准备与真实模型抽取；原 PDF 用于核对来源。**没有重新解析全部 PDF，也不是完整论文召回测试或新一轮 30 篇评测。** 为控制调用量，带隙仅验证一个原文明确报告数值的片段。

- 原先受网络权限阻断的模型请求尝试：7 次。
- 用户明确授权后成功的模型 HTTP 请求：14 次，全部 HTTP 200；总尝试 21 次，低于 24 次上限。
- 服务返回的用量：输入 **19,570 tokens**，输出 **1,569 tokens**，合计 **21,139 tokens**。未读取账单，人民币/美元实际金额未知；该数字不是 Codex 对话额度。
- 模型：Qwen Flash 识别、DeepSeek V4 Flash 抽取、Qwen VL Plus 图片解读。为控制成本，本轮关闭 DeepSeek thinking，关闭自动重试，识别输出上限 256 tokens、其他调用 4,096 tokens。
- 独立材料服务探测 1 次，返回 HTTP 503 后停止。主抽取使用 identity normalizer，不能把服务探测等同于全部 Fact 已完成材料规范化。
- 所有付费调用已结束，没有后台重跑。原始输出与 Gold 均保留。

## 真实输出核对

Tc 得到 15 条原始 Fact，重复的 518 K 在 equation/table 之间合并，最终 **14 条 Fact**，保留两个证据引用。带隙最终 **0 条 Fact**。CLI 未报告接口/JSON 错误，但逐条核对发现 **至少 4 条明确错误**：2 条 Tm 误抽、2 条图面板错配；其他多条材料或条件仍不完整。此处不以小样本比例冒充准确率或完整召回率。

| 样本 | 原文支持与实际结果 | 验收判断 |
|---|---|---|
| Paper 1，BiFeO3 | 正确抽出铁电 Tc=1103 K，排除反铁磁 Néel 643 K | 核心关系通过 |
| Paper 4，0.66BaTiO3–0.33CoFe2O4 | randomly mixed=720 K、tri-layer=746 K，材料与结构未错配；结构留在材料字符串中，conditions 为空 | 核心关系通过，条件结构化不完整 |
| Paper 12，多组分与变量 | 正确找到 x=.01/y=.24 的 853.1 K，保留 E_bias=0 V，但缺母式；额外把 x=.03/.05 的 766.1/741.7 K 当成 Tc | 不通过：原文说明两者属于 relaxor/dipole-glass 的频率相关 Tm，preset 已明确排除，模型仍违反规则 |
| Paper 19，equation | 普通 BLFO–MZFO composite=518 K 绑定正确，但没有完整化学式、80/20 wt.% 比例与条件 | 简单 Tc 等式检出可用，完整事实不通过；未验证旧 EquationTool 的复杂求解能力 |
| Paper 19，Table 1 | 返回 MZFO=518 K、普通复合物=518 K、HPT=367/778 K；数值来自表后正文 | 表格边界不通过。原 Table 1 只有尺寸/应变等数据，没有 Tc；不能把正文命中算作表格成功 |
| Paper 19，Figure 5 | 图中 b 面板 HPT 样品标注 367 K 与 Tc*=778 K；VLM 在 a 面板虚构相同 inset，导致普通 composite 也被抽出这两个温度 | 不通过：数值能读出，样品归属错误；Tc* 区别、化学式与条件也未保留 |
| Paper 30，band_gap preset | 原文明确说 BFO 的 Eg≈2.2 eV；识别器返回 yes，抽取器直接返回 `{"facts":[]}` | 新 preset 的程序接入成功，真实正例抽取未通过。没有既有带隙 Gold，依据原文人工核对 |

带隙空结果没有触发异常、超时或输出截断。当前输入没有另一片段中的 BFO=BiFeO3 定义，但仅凭本轮不能确定这就是漏抽原因，未追加付费因果实验。

## 五个可选 Evidence 工具实际验证到哪里

本地准备使用真实缓存 PhysBERT 权重和 Chroma，未模拟向量结果。三篇核心论文共 92 个文本块，得到 72 条文本 Evidence；18 次向量命中与规则命中合并，保留双方检索来源。本轮独立送入模型的是选定子集，不是这 72 条全部。

| 工具 | 已验证 | 尚未通过或未覆盖 |
|---|---|---|
| rule_text | 当前规则可生成候选，文本真实调用可完成 | 复杂样品 Tc/Tm 语义约束仍失败 |
| PhysBERT/RAG | 真模型加载、3 个向量库、6 次查询、检索来源合并成功 | 未测新增召回价值；本样本所有向量命中也被规则命中 |
| table | 当前 provider 可选中表块并送入抽取 | 表块吞入数页正文，未得到可验收的纯表格正例 |
| equation | 当前 provider 检出简单 Tc 等式并完成抽取 | 不代表变量公式计算、复杂公式求解或旧工具全部可用 |
| figure | 原图实际发送到 VLM，观察结果进入抽取 | VLM 面板绑定失败；图号跨论文重复另有缓存/Review 覆盖风险 |

## 材料恢复与 Review

当前主运行明确记录 `material_normalizer=identity`：材料按模型原文保留。Paper 12 的变量母式、Paper 19 的 BLFO/MZFO 定义位于其他 Evidence，没有随这条输入送入模型。**每条 Evidence 独立抽取的结构存在，但补齐材料定义的上下文还没有满足目标。**

另用同一个 FactProcessor 实际探测 MaterialParser 服务：BiFeO3 返回 HTTP 503，输出 Fact 保留，并标记 `material_normalization_failed: HTTP 503`。该诊断位于总运行记录 `material_checks`，不在使用 identity 的主 predictions/Review 中。服务失败时不丢 Fact 的行为得到验证，复杂材料名称恢复没有验证成功。

JSON 与 Review 仍保留 Evidence 引用。但原始 summary 的 `facts_needing_review=0` 只反映当前程序检查，没有发现上述语义错误和不完整材料，**不能解释为结果无需审核**。新增逐条人工审计 JSON 独立保存，不覆盖模型原始预测。

## 来源与基础代码问题

1. **图片路径已修复。** 历史 manifest 中相对 processor workspace 的路径被再次拼到 manifest 目录，6/6 原图被误认为不存在。增加严格的同文档目录回退后，6/6 原图能正确定位；相关回归已通过。
2. **图片 Evidence ID 跨论文冲突已修复。** 原 provider 直接用每篇从零编号的 `figure_0`，CLI 缓存及 Review 按该 ID 建索引会覆盖。使用真实两篇 manifest 离线复现；本轮只选中一个图，未证明本轮输出已发生跨文覆盖。新 ID 加入文档身份和原始身份摘要，保留原 `source_id`。回归覆盖两份文档名清洗后相同、图号相同的输入，验证独立缓存、Fact 归属、Review 来源及缓存恢复，相关 50 项离线测试通过。该测试替换模型通信，不是新的真实模型效果验证。
3. **表格吞正文。** `schemas/article_csv.py` 在 tables 为空时，把 results_discussion 中第一个 `Table 1.` 后所有剩余讨论移入 tables；`evidence/source_units.py` 仅按下一个表标题分块。Paper 19 Table 1 Evidence 达 15,192 字符。需恢复表体边界，当前仅定位，未改写历史 Article。
4. **Paper 30 DOI 误用参考文献。** 记录是 `10.1016/j.ceramint.2022.11.245`，PDF 首页真实 DOI 为 `10.1016/j.jallcom.2023.169571`。PDF processor 对完整 Markdown 取第一个 DOI，首页 DOI 在导出中缺失时会误取参考文献。应优先可信首页来源，回退时排除参考文献；本轮保留原 ID，未修改 Gold。

图片 ID 修复适用于以后新生成的 Evidence。历史 all.json、缓存、Gold 与本轮真实预测没有迁移；应用修复应使用新 run 重新 prepare，不能仅 resume 旧的图片准备结果。本轮源码修复仅涉及图片路径解析、图片身份及其回归测试，未更改 Tc 科学提示词。

## 后续最小修复顺序

先修 Article 的 DOI/表格边界与证据来源，再给每条 Evidence 补上同文内有出处的材料定义和样品条件。保持每条 Evidence 独立抽取，不引入按整篇合并抽取。随后复验已出现的 Tc/Tm、图面板和带隙失败，并使不完整材料/未确认关系进入 Review。材料服务需恢复或明确使用可验证的本地恢复路径。

完成这些具体失败样例的复验后，再决定是否值得付费重跑固定 30 篇。当前不扩大模型调用量，不进行项目净化，不声称生产完全可用。

## 9 月 6 日后续对照

同一 Paper 12 Evidence 新增两次受限抽取对照：沿用服务默认 thinking 时仅返回正确的 853.1 K；明确关闭 thinking 时重现 766.1/741.7 K 两条 Tm 误抽。两次消息、模型、温度和输出上限相同。这个结果支持上次测试包装器关闭 thinking 是该条退步的重要原因，尚不能推广至所有样本或其他工具。原始验收结果保留不变，详见[基线对照报告](F:/Python_Project/ComProScanner/outputs/reports/tc_baseline_reproduction_20260906.md)。

## 可复核文件

- [逐条科学审计 JSON](F:/Python_Project/ComProScanner/outputs/reports/live_acceptance_20260905.json)
- [真实请求、原始响应与 token 记录](F:/Python_Project/ComProScanner/outputs/runs/live_acceptance_network_20260905/live_report.json)
- [Tc 原始 predictions](F:/Python_Project/ComProScanner/outputs/runs/live_tc_selected_network_20260905/predictions.json)
- [Tc 原始 Review（尚未人工修正）](F:/Python_Project/ComProScanner/outputs/runs/live_tc_selected_network_20260905/review.xlsx)
- [带隙原始抽取响应](F:/Python_Project/ComProScanner/outputs/runs/live_band_gap_selected_network_20260905/papers/10_1016_j_ceramint_2022_11_245_FULL_TEXT_0003_TEXT.json)
- [独立文本/公式/表格核对](F:/Python_Project/ComProScanner/work/live_acceptance_20260905/live_text_audit.md)
- [原文选择与材料定义来源](F:/Python_Project/ComProScanner/work/live_acceptance_20260905/selection_notes.md)
