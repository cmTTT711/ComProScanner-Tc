# 9 月 4 日结果审查与问题 Evidence 重跑

本轮已完成。结论是：**两个历史 FN 的原因已定位；开启 thinking 并不能自动解决材料名称缺失，本轮还有截断、漏项和限定信息丢失，不能认定整体优于 9 月 4 日结果。** 建议继续保留旧结果作为基线，优先修复已有链路中的上下文和材料恢复连接。

## 范围与用量

审查了 9 月 4 日原始预测的全部 61 行。发现 36 行名称未完整展开或变量未确定，另 1 行小数点乱码。缩写不完整不等于材料错误；这些结果中包含重复来源，不能当成 37 个不同材料。未标记的其余行也不代表科学内容全部正确。

只重跑筛选出的 26 条 Evidence：25 条既有证据、1 条从 PDF 恢复的跨页原文；每条独立输入。第 29 篇相同文本对应的 text/equation 证据只发送一次。没有重跑完整 30 篇，没有将 Gold 或人工恢复的材料定义注入抽取输入。

| 项目 | 实际结果 |
|---|---:|
| 主链路请求 | 51 次：26 次 Qwen identifier、25 次 DeepSeek extractor |
| 最后一项独立诊断 | 1 次 DeepSeek，使用已授权的第 11 篇同一条 Evidence |
| 总请求数 | **52 次**，全部 HTTP 200 |
| 主链路 tokens | 182,392 |
| 诊断 tokens | 7,327 |
| 累计 provider-reported tokens | **189,719 / 400,000**，含推理 tokens |
| DeepSeek thinking | 26 次请求均在实际 HTTP 请求体中确认 `enabled` |
| 自动重试 / 材料服务调用 | 0 / 0 |
| 主链路保存结果 | 32 条 Fact，Review 已生成 |
| Evidence 处理结局 | 22 条产生结果，1 条 identifier 拒绝，1 条抽取为空，2 条响应截断 |

这是外部模型返回的 token 用量，不是人民币费用，也不是 Codex 账户额度统计。显式 thinking 参数采用 [DeepSeek 官方接口说明](https://api-docs.deepseek.com/guides/thinking_mode/)。两次截断也消耗 tokens，已纳入以上统计。

## 两个 FN

旧结果按同论文、同数值、同单位的温度事件检查，覆盖严格 Gold 的 43/45 个事件。这个指标忽略材料、条件和限定，不应解释为完整事实准确率。

| 论文 | 原文与缺失原因 | 本轮结果 |
|---|---|---|
| 11 | PDF 第 6 页指出 BaTiO3 的典型 FE→PE 峰约 120°C，但当前复合材料未观察到该峰。这是 BaTiO3 背景事实，不能转给复合材料。 | Qwen identifier 返回 no，主链路未抽取。最后用相同 Evidence、相同抽取提示词直接调用开启 thinking 的 DeepSeek，得到 BaTiO3、约 120°C。确认本次主链路漏在 identifier；该诊断不计为主链路成功。结果的背景/未在复合材料观察到的语义仍需要 Review 保留。 |
| 27 | 原解析既有数字乱码，又把句子切到两页。Gold 写 1103 K，PDF 实际写约 830°C，即约 1103.15 K。 | 恢复 PDF 第 1–2 页原文段落后，主链路得到 BiFeO3、约 830°C。保留原文单位，未改 Gold。该改善包含输入修复，不能只归因于 thinking。 |

## 材料名称及退步

完整的 37 行问题及原文定义见 [材料名称审查表](F:/Python_Project/ComProScanner/outputs/reports/tc_material_name_audit_20260906.md)。本轮 32 条新结果中，人工仍标记 **29 条名称完整性问题**，见 [逐条人工 Review 标记](F:/Python_Project/ComProScanner/outputs/runs/tc_baseline_targeted_20260906/manual_review_findings.json)。典型情况仍是 BF-BCT、BFO、PZT、BFBKT、BLFO/MZFO、只有 x/y 的标签和只有球磨时间的样品名称。

明确的自动修正是第 15 篇 `Ba0:85Ca0:15` 恢复为 `Ba0.85Ca0.15`。第 19 篇长表格再次给出了完整 MZFO 配方，但对应完整配方在旧结果已有，不能作为原有名称问题全部解决的证据。

| 问题 | 新旧对比及判断 |
|---|---|
| 第 15 篇 732 K 新漏项 | 旧行 18 有结果，新抽取为空。PDF 第 7 页末尾给出 x=0，第 8 页接 732 K；选中的 Evidence 从 732 K 开始。应补齐源句，而不是期待模型补猜样品。 |
| 第 19 篇长表格失败 | TABLE_0002 混入后续正文，约 1.6 万字符。推理耗尽 16,384 输出 tokens，未形成答案，`finish_reason=length`。旧行 35 的 BLFO fraction、778 K 没有从该来源重新得到。其他 Evidence 的复合材料 778 K 不能直接视为恢复了同一相事实。 |
| 第 25 篇失败 | TEXT_0015 也耗尽 16,384 输出 tokens，只返回半截 JSON。旧行 42–44 的 650/227/约 320°C 均未产生可接受的新记录。320°C 本身还需核对 Tc/Tm 语义，不能把保留它当成必然正确。 |
| 第 19 篇限定丢失 | 778 K 新结果丢失 `new FM order (T_C*)`；367/950 K 的材料名从 fraction 退成 MZFO/BLFO，且没有保留 HPT/组分相语境。 |
| 第 4 篇条件丢失 | 720/746 K 保留，但新结果未保留旧结果的 field-cooled、10 kOe out-of-plane 条件。 |
| 第 28 篇属性细化丢失 | 1100 K 保留，property 从明确的 ferroelectric Curie temperature 变为通用 Curie temperature。 |
| 第 12 篇语义正确但名称未解决 | 本次只抽 853.1 K，没有混入 766.1/741.7 K 的 relaxor Tm；材料却仍只有 y=0.24、x=0.01。相对 9 月 4 日，这是维持该段温度表现，而非新的温度提升。 |

在 37 条被标记的旧行中，32 行能在相应重跑来源找到同数值、同单位，5 行找不到。但其中存在同温度的不同材料、重复记录和信息丢失，**32/37 仅是数值覆盖检查，不能当成材料事实召回率**。本轮是定向重跑，也不能用它计算或宣称完整 30 篇 F1 提升。

## 已有材料恢复为何没有起效

本轮 canonical CLI 使用 `FactProcessor` 的默认 `IdentityMaterialNormalizer`，它保留原始名称，不会展开同文缩写，也不会将 x/y 代入母配方。项目备份中的 `VariableCompositionNormalizer` 确实存在，但没有接到当前默认抽取链路。

独立离线调用已有变量恢复代码，再对照原 PDF，成功恢复旧行 7、17、50、51。其中 50/51 为重复来源，合计 3 个不同结果条目。恢复了第 12 篇 `0.76BiFe0.99Cr0.01O3–0.24BaTi0.99Mn0.01O3`、第 29 篇 `0.73BiFe0.97Cr0.03O3–0.27BaTi0.97Mn0.03O3`，并修正第 15 篇小数点。详见 [离线恢复及来源核验](F:/Python_Project/ComProScanner/outputs/runs/tc_baseline_targeted_20260906/offline_name_recovery_verified.json)。这些是独立后处理证据，没有混入主链路预测，也未作为 LLM 提升计分。

## 后续应优先接通的部分

1. 保留每条 Evidence 独立抽取，同时让其带齐完整源句，并能引用同一 Article 的材料定义与变量赋值。第 15、27 篇已经证明跨页切断会影响可抽取性。
2. 接回已有的同文材料定义恢复和变量代入；保留 `material_reported`、恢复后的名称、引用位置和 unresolved 状态。不能猜未报告的掺杂量或使用其他论文的同名缩写。
3. 修正 Evidence identifier 对明确背景 Tc 的误拦；本轮第 11 篇已经用相同输入验证了抽取器有能力抽到。
4. 修正表格边界，并处理 thinking 与答案输出共用额度导致的截断。此次失败均被记录，没有接收残缺答案；不能靠无限重试处理。
5. 让 Review 识别名称未解析、条件/相变限定丢失和抽取失败。当前 `facts_needing_review=0` 仅统计已有 processing issues，不代表科学质量合格。摘要的 `identifier_accepted=23` 还排除了后续抽取失败的两条；实际 identifier yes 为 25，阶段统计应分开。

这些工作属于接通和修复已有流程，不需要引入多 agent 或重写整套框架。本轮未修改生产代码，未进行项目净化，也没有覆盖 9 月 4 日预测或改动 Gold。

## 可复核产物

- [本轮预测 JSON](F:/Python_Project/ComProScanner/outputs/runs/tc_baseline_targeted_20260906/predictions.json)
- [主链路原始 Review](F:/Python_Project/ComProScanner/outputs/runs/tc_baseline_targeted_20260906/review.xlsx)；请结合人工标记阅读，不能把自动 0 标记当成通过。
- [旧结果全部 61 行审查](F:/Python_Project/ComProScanner/outputs/runs/tc_baseline_targeted_20260906/audit_before.json)
- [26 条 Evidence 新旧对比](F:/Python_Project/ComProScanner/outputs/runs/tc_baseline_targeted_20260906/comparison.json)
- [主链路真实调用记录](F:/Python_Project/ComProScanner/outputs/runs/tc_baseline_targeted_20260906/live_report.json)
- [第 11 篇直接抽取诊断](F:/Python_Project/ComProScanner/outputs/runs/tc_baseline_targeted_20260906/fn11_direct_extractor_probe.json)
- [最终用量和状态](F:/Python_Project/ComProScanner/outputs/runs/tc_baseline_targeted_20260906/final_audit_summary.json)

已检查主链路选定输入与实际输入一致、26 个 Evidence ID 唯一、所有 DeepSeek 请求显式开启 thinking、累计请求和 tokens 未超授权、Review 文件容器完整。旧预测 SHA256 保持 `d786e325318a58d418084860bd8453f3ceec7266baa7e1be9a5232924480b3b7`。
