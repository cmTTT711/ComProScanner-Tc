# 9 月 4 日材料名称审查

审查对象为 `outputs/runs/tc_fulltext_001_030_20260904/predictions.json` 的全部 61 行。下表行号从 1 开始。36 行存在缩写未展开、母配方缺失或变量未确定，另 1 行存在数字排版乱码。这些是完整性问题，不等同于 37 条材料识别错误；其余 24 行也不代表科学内容全部正确。

以下定义来自同一篇原始 PDF，仅用于离线核查，没有作为答案注入本轮 LLM 输入。完整路径、PDF 页号和原文片段保存在 [source_definition_audit.json](F:/Python_Project/ComProScanner/outputs/runs/tc_baseline_targeted_20260906/source_definition_audit.json)。不能通过跨论文的同名缩写直接套用配方。

| 论文 / 旧结果行 | 问题 | 原文定义及恢复边界 |
|---|---|---|
| 10 / 2–5 | BF-BCT、C、M、CM 未展开 | PDF 第 3 页：母配方 0.7BiFeO3–0.3(Ba0.85Ca0.15)TiO3；C 加 0.4 wt.% CuO；M 加 0.4 wt.% MnO2；CM 加 0.2 wt.% CuO 和 0.2 wt.% MnO2。须保留各自 683/692/690/687 K 的对应关系。 |
| 12 / 7 | 只有 y=0.24、x=0.01 | PDF 第 1–2 页给出 (1−y)BiFe1−xCrxO3–yBaTi1−xMnxO3。代入为 0.76BiFe0.99Cr0.01O3–0.24BaTi0.99Mn0.01O3。853.1 K 是本轮支持的 Tc；同段 766.1/741.7 K 为 relaxor Tm，不能一起抽成 Tc。 |
| 15 / 17 | Ba0:85Ca0:15 小数点乱码 | PDF 第 3 页表 I 可交叉核对为 0.74BiFeO3–0.26(Ba0.85Ca0.15)TiO3–0.8 wt.% MnO2，698 K。 |
| 15 / 18 | BF-BCT-Mn-x 母配方未展开 | 母配方同上，但 x=0，代表未加入 MnO2 的样品，732 K。PDF 第 7 页句末给出 x=0，第 8 页才接 732 K；本轮 Evidence 从 732 K 起始，缺少前半句。 |
| 15 / 19 | 已有母配方，但 x wt.% 未赋值 | 结论段给出 698 K，却没有在该句绑定 x。应通过样品定义和结果表恢复，不能把附近压电最优样品 x=1.2 直接套给 Tc。表 I 的 x=0.8、698 K 与正文其他样品的 Tm=698 K 也不能仅按同数值合并。 |
| 19 / 21–30、32–35 | MZFO、BLFO 和复合材料未展开 | 本文 MZFO 为 Mn0.6Zn0.3Fe2.1O4，BLFO 为 Bi0.9La0.1FeO3；复合材料为 80 wt.% BLFO / 20 wt.% MZFO。保留初始粉体、商业牌号、普通压制、HPT 和组分相各自身份，不能把相的 Tc 转给整个复合材料。 |
| 19 / 27、35 | 除名称外，还需要保留相变含义 | 778 K 指 T_C* 新出现的 FM 有序；不能与 367 K 的 MZFO 磁转变、950 K 的 BLFO 铁电转变混写。名称恢复不能丢失 HPT、fraction 和原有 qualifier/context。 |
| 24 / 40 | BF-BNT-BTM 及 x/y 变量未展开 | PDF 第 3 页：母配方 (1−y)[0.9BiFeO3–0.1Bi0.5Na0.5TiO3]–yBaTi1−xMnxO3；本样品 y=0.23、x=0.00，774 K。需保留 as-prepared 条件。 |
| 25 / 42–43 | BFO/PTO 未展开；掺杂比例未给出 | BFO=BiFeO3、PTO=PbTiO3；背景对比为未掺杂与 La 取代体系 650/227°C。局部语句未给 La 含量和固溶比例，不能为追求完整而猜测。 |
| 25 / 44 | (BNFPT)x 母配方未展开 | PDF 第 1–2 页定义 0.6Bi1−xNdxFeO3–0.4PbTiO3。约 320°C 的 Tc/Tm 性质与对应掺杂样品需要额外核对；恢复名称本身不证明该温度为正确 Tc。 |
| 26 / 45 | PZT 未展开 | 本文 PZT=Pb(Zr1−xTix)O3，局部定义未确定 Zr/Ti 比例。355°C 对应 PZT 相；保留 3BFO_n/7PZT_m 样品和 650°C 烧结条件，不能把烧结温度当 Tc。 |
| 27 / 46 | BF-BKT-BT 及配比未展开，原解析有数字乱码 | PDF 定义 0.65BiFeO3–0.35[(1−x)Bi0.5K0.5TiO3−xBaTiO3]；目标 x=0.4、约 742.6 K。原 Evidence 的 x 和 Tc 数字均有字符映射错误，应先修复原文，不能依赖模型猜乱码。 |
| 28 / 47–48 | BFO/BFBKT 未展开 | BFO=BiFeO3；本篇 BF-BKT 晶体为 0.58BiFeO3–0.42Bi0.5K0.5TiO3，约 671.5 K。BFO 背景约 1100 K，应保留铁电转变含义。 |
| 29 / 50–51 | BFC/BTM 及 x/y 未展开；文本和公式证据重复 | PDF 第 1–2 页母配方 (1−y)BiFe1−xCrxO3–yBaTi1−xMnxO3，x=0.03、y=0.27；代入为 0.73BiFe0.97Cr0.03O3–0.27BaTi0.97Mn0.03O3，约 795.2 K。两条旧结果引用的文本相同，本轮只发送一次。 |
| 3 / 52 | 仅有 “Composite sample of 24 h” 工艺标签 | 原文体系为 0.8BaTiO3–0.2Ni0.5Co0.5Fe2O4；24 h 是球磨时间，129°C 是对应温度，不能将 24 h 当成独立材料名称。 |
| 30 / 53–54 | BFO/BTO 未展开 | BFO=BiFeO3、BTO=BaTiO3；本段背景复合体系比例未指定。分别保留 pristine BFO 约 830°C 和 BFO–BTO 高于约 580°C 的限定含义。 |
| 4 / 58–59 | BT-CF 及配比未展开 | 本文为 0.66BaTiO3–0.33CoFe2O4；随机混合和层状样品分别约 720/746 K。保留排列方式、field-cooled、10 kOe out-of-plane。 |

原始 DOI/document_id 存在误抓参考文献 DOI 的历史问题。本次按既有 paper_id 映射核查并保持稳定 ID，不改 Gold 或旧预测。论文 25 的原文 DOI 为 10.1016/j.jallcom.2023.169333，旧 document_id 却为 10.1143/JPSJ.7.5，这也是后续需要修复的解析溯源问题。

现有 `VariableCompositionNormalizer` 的离线试运行恢复了旧行 7、17、50、51；每项都已对照原 PDF 核验，详见 [offline_name_recovery_verified.json](F:/Python_Project/ComProScanner/outputs/runs/tc_baseline_targeted_20260906/offline_name_recovery_verified.json)。其中 50/51 是重复来源，因此这是 4 行、3 个不同结果条目。该步骤没有外部调用，没有覆盖本轮原始预测，也不能算作 LLM 自身的提升。
