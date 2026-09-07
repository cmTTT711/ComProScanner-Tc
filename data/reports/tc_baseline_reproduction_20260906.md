# Paper 12：9 月 4 日基线结果与 thinking 对照

**找到一个有直接对照证据支持的运行设置问题：上次小样本测试脚本显式关闭 DeepSeek thinking。对同一 Evidence，沿用服务默认设置恢复了历史正确抽取；关闭 thinking 再次产生两条相同的 Tm 误抽。**

这支持把关闭 thinking 视为这条证据退步的重要原因，尚不证明它是所有退步的唯一原因，也不代表 30 篇整体效果已恢复。

## 实验保持了什么

- 同一条 `10_1007_s10854_022_08492_3_FULL_TEXT_0011_TEXT`，1,605 字符，与 9 月 4 日 Review 中原文逐字一致。
- 当前 extractor 和 client 的 AST 与恢复版本 `7c979bea` 一致；Tc 抽取提示与恢复基线契约相同。
- 同一模型 `deepseek/deepseek-v4-flash`、接口、messages、temperature=0、输出上限 8,192、timeout=180 秒、自动重试 0。两次实际传出的 messages 哈希一致。
- 实验变量：一组不传 thinking 字段，另一组传 `thinking={"type":"disabled"}`。
- 复用已被识别器接受的 Evidence，仅比较抽取阶段；没有追加材料定义，没有调用材料服务，没有修改 prompt 或项目生产代码。

历史完整请求与服务默认参数没有保存。共同的 8,192 输出上限是本次预算约束，并非已经确认的历史值，所以这是有预算限制的设置对照，不应称作对历史运行环境的完整复现。

## 实际结果

| 记录 | 返回温度 | 科学判断 | 总 tokens | 耗时 |
|---|---|---|---:|---:|
| 9 月 4 日保存结果 | 853.1 K | 正确 | 无完整记录 | 无完整记录 |
| 本次沿用服务默认 thinking | 853.1 K | 正确；材料、属性、值、单位、qualifier、conditions 与历史该条一致 | 7,210 | 45.83 秒 |
| 本次明确关闭 thinking | 853.1、766.1、741.7 K | 后两条为应排除的 relaxor/dipole-glass Tm，错误 | 1,174 | 1.08 秒 |

两次均 HTTP 200、正常 stop，没有截断。默认组返回的使用记录包含 **6,052 reasoning tokens**，说明这次服务默认确实执行了思考；关闭组无 reasoning 内容。未保存或公开模型的详细思考文本，只记录用量、字符数及最终答案。

关闭组的完整抽取对象与前次小样本返回对象一致，重现了误抽；默认组的核心 Fact 字段与 9 月 4 日该条原始预测一致。材料仍为 `y=0.24, x=0.01`，完整母式没有恢复，历史原始预测同样如此。

本次默认组共使用 6,105 completion tokens，包含 reasoning。后续思考模式测试若限制到 4,096 输出 tokens，存在截断风险。控制费用应优先缩小样本量，并记录实际运行设置，不能把减少思考和降低输出预算当作无影响的测试替代。

## 对项目结论的影响

上次强制关闭 thinking 的设置来自 `work/live_acceptance_20260905/run_live.py` 测试包装器，当前正式 `_LiteLLMClient` 并没有这个覆盖。因此，当前证据支持先保留恢复版正式调用设置；不能仅依据上次测试误抽就推翻 Evidence 路线或继续增加大量处理代码。

此前“原文缺上下文”“材料服务 503”等问题不能解释这条相同输入上新增的两条 Tm 误抽。这个实验开始把运行参数造成的差异与原有流程缺口分开。但只有单条证据、每种设置各一次，仍需谨慎对待可重复性和全量泛化。

本次不改变历史预测/Gold，不修订旧测试的原始结果，也不声称解决图片错配、表格吞正文、DOI 或带隙漏抽。没有新增生产代码改动。

## 用量与记录

新增模型请求 **2 次**，输入 2,131 tokens，输出 6,253 tokens，总计 **8,384 tokens**。实际货币金额未查账。

从首次小样本验收累计：16 次成功模型响应、7 次网络阻断尝试，模型尝试合计 23 次；加上独立材料服务 1 次，合计 24 次。成功模型响应累计报告 29,523 tokens。所有调用已完成，未启动其他付费任务。

- [原始请求参数、最终响应、使用记录](F:/Python_Project/ComProScanner/outputs/runs/tc_paper12_thinking_comparison_20260906/live_report.json)
- [历史与当前结果的程序核对](F:/Python_Project/ComProScanner/outputs/runs/tc_paper12_thinking_comparison_20260906/comparison.json)
- [实际发送的相同 messages](F:/Python_Project/ComProScanner/outputs/runs/tc_paper12_thinking_comparison_20260906/request_messages.json)
- [实验脚本（已有运行防重复）](F:/Python_Project/ComProScanner/work/live_acceptance_20260905/compare_thinking.py)
