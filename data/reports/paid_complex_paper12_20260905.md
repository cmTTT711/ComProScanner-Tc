# 复杂材料论文少量付费验证：第 12 篇（2026-09-05）

论文：Phase evolution and enhanced piezoelectric, multiferroic, and magnetoelectric properties in Cr–Mn co-doped BiFeO3–BaTiO3 system。DOI：10.1007/s10854-022-08492-3。

只解析这一篇，并将 canonical pipeline 实际生成的一条含 853.1 K 的 Evidence 送入旧抽取链路。未拼入其他 Evidence、全文或 Gold 答案。本文目标组成为 (1−y)BiFe1−xCrxO3–yBaTi1−xMnxO3，目标样品 y=0.24、x=0.01。

## 结果

**本样本没有完成有效的最终材料事实输出，不能算端到端通过。**

- 第二轮抽取阶段正确返回 `y=0.24, x=0.01 → 853.1 K`；没有把 766.1 K、741.7 K 两个弛豫/偶极玻璃峰作为 Tc 输出。
- 完整材料名称未恢复。当前 Evidence 只有样品变量、相变讨论，没有出现在文章前部的母体化学式定义。不能从另处的 Gold 补答案来声称恢复成功。
- 材料解析 HTTP 服务实际被调用，但返回 503；原始工具诊断已保存。
- formatter 还需后续模型请求完成，其请求被实验硬上限拦截。最终 predictions.json 为空。即使移除请求上限，工具 503 仍是一项需解决的失败，不能假定其余流程必然成功。

## 请求与消耗

第一轮为原模式：Qwen identifier 1 次成功，DeepSeek extractor 三次响应均因 2048 输出 token 上限而 length 截断。原框架自动重试导致累计 4 次请求，未形成有效结果。

第二轮仍为同一条 Evidence，显式关闭 DeepSeek thinking 和 Crew 级重试，硬上限 3 次模型请求。identifier 和 extractor 完成，formatter 发起工具恢复；服务 503 后的后续模型请求被阻止。

DeepSeek 的开关依据其[官方思考模式文档](https://api-docs.deepseek.com/guides/thinking_mode/)。这是本次实验脚本的配置调整，不代表已更改全项目默认运行模式。

- `paid_complex_paper12_20260905`：4 次模型请求，供应商返回合计 18249 tokens。
- `paid_complex_paper12_nonthinking_20260905`：3 次模型请求，供应商返回合计 7480 tokens。

两轮共 7 次真实模型请求、25729 tokens（含重复请求、输入和输出）。这不是费用金额，未查询供应商账单。材料解析服务请求单独记录，不包含在模型请求数里。实验已经结束，不追加付费重试。

## 对项目的实际结论

简单材料样本通过，并不能证明复杂材料名称恢复可用。本次至少暴露三个问题：

1. 单条候选 Evidence 可能缺少样品代号/变量对应的母体定义，旧恢复流程接收到的信息不足。
2. 外部材料解析服务会不可用，需要明确失败/降级策略。
3. 思考模式、输出限制、框架自动重试的组合会重复消耗 token；实验级 HTTP 限额成功阻止继续调用，但尚不等于全项目已具备统一预算控制。

应保持每条 Evidence 独立抽取，同时研究在其准备阶段携带必要的样品定义与来源；不能靠恢复按文章合并抽取掩盖这个上下文缺口。本次没有改变此结构，也没有启动额外批次。

两轮完整诊断、原始 extractor 响应与请求用量位于上述 outputs/runs 目录下的 paid_validation.json 和 papers/*.json。Gold 原件未修改。
