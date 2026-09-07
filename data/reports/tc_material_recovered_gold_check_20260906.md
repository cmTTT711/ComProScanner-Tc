# 材料恢复结果与 Gold 对照

检查文件：`tc_20260904_material_recovered_20260906/predictions.json`，共 59 行。该文件保留 4 号抽取，只增加材料后处理；没有混入随后 26 条 Evidence 的 LLM 重跑或 FN 诊断结果。

Gold 共 47 行：46 条严格事实（45 个不同的论文/温度/单位事件），以及 1 条非严格下界事实。数值事件覆盖 **43/45 = 95.56%**，与 4 号相同；这不是完整事实准确率。

人工逐项对照严格 Gold：**31 条材料与数值对应，13 条数值对应但材料或必要样品信息未补全，2 条漏项**。MATCH 按科学等价关系判断，允许变量代入、排版、样品条件在不同字段表达；不表示 qualifier、role 等全部字段逐字相等。

**两个漏项**：第 11 篇 BaTiO3 约 120°C；第 27 篇 BiFeO3 背景约 1103 K。第 27 篇 PDF 实为约 830°C，单位差异单独记录；当前文件中连该对应事实也没有。此前两项诊断结果未并入本文件。

**两条不应作为确定 Tc**：预测 43（论文 25）约 320°C 为推测关联/relaxor 异常；预测 58（论文 6）<200°C 只是可能关联 Tc，既不是精确 200°C，也不应丢失推测限定。它们均继承自 4 号结果，材料恢复未新增这些温度。

论文 30 的 over ~580°C 是 Gold 明确接受的非严格下界事实，当前保留正确，不能误算普通点值 FP。论文 19 的额外组分相/商业比较行也单独列出，不能因温度相同就当作复合材料命中。

## 仍需补齐的材料/样品信息

论文 3 的 24 h 样品配方；论文 10 的 BF-BCT 四个配方；论文 19 部分 HPT/组分记录的配比或相语境；论文 24 的完整三元配方；论文 25 的 BFO 全称；论文 27 的三元配方；论文 28 的 BFBKT 晶体配比。

已验证的改善包括论文 12/29 的变量展开、论文 15 x=0 母配方及 732 K 保留、论文 19 的 BLFO/MZFO 化学式、论文 4 的随机混合/层状复合材料。名称展开后仍有未定变量或缺失比例时，不应直接标记为完整恢复。

## 全部 Gold 逐行对照

| Gold 行 | 论文 | Gold 材料 | 温度 | 当前预测行 | 结论 | 核查说明 |
|---|---|---|---|---|---|---|
| 1 | 1 | BiFeO3 | 1103 K | 1 | 材料与数值对应 | 材料与数值、单位对应；允许配方排版、近似符号和样品描述的等价写法，不表示所有元数据字段全等。 |
| 2 | 3 | 0.8BaTiO3–0.2Ni0.5Co0.5Fe2O4 (24 h ball-milled sample) | 129 °C | 50 | 数值对应，材料/样品信息待补 | 仅有 24 h 样品标签，缺 0.8BaTiO3–0.2Ni0.5Co0.5Fe2O4 母配方。 |
| 3 | 4 | 0.66BaTiO3–0.33CoFe2O4 (randomly mixed) | 720 K | 53,56 | 材料与数值对应 | 配方正确，随机混合条件在 conditions 或材料名中保留；同一事实有不同 Evidence/限定的重复记录。 |
| 4 | 4 | 0.66BaTiO3–0.33CoFe2O4 (tri-layered) | 746 K | 54,57 | 材料与数值对应 | 配方正确，三层/层状条件保留；不要与 720 K 的随机混合样品混配。 |
| 5 | 4 | CoFe2O4 | 793 K | 55 | 材料与数值对应 | 材料与数值、单位对应；允许配方排版、近似符号和样品描述的等价写法，不表示所有元数据字段全等。 |
| 6 | 7 | BaTiO3 | 120 °C | 59 | 材料与数值对应 | 原文描述 BaTiO3 冷却时 cubic→tetragonal 的 120°C 转变；预测 cubic 标签是相变起始相，不是新的材料。 |
| 7 | 10 | 0.7BiFeO3-0.3(Ba0.85Ca0.15)TiO3 | 683 K | 2 | 数值对应，材料/样品信息待补 | BF-BCT 未展开，母配方仍缺失。 |
| 8 | 10 | 0.7BiFeO3-0.3(Ba0.85Ca0.15)TiO3 with CuO and MnO2 additives | 687 K | 5 | 数值对应，材料/样品信息待补 | BF-BCT-CM 未展开，母配方与 CuO/MnO2 添加信息未写全。 |
| 9 | 10 | 0.7BiFeO3-0.3(Ba0.85Ca0.15)TiO3 with MnO2 additive | 690 K | 4 | 数值对应，材料/样品信息待补 | BF-BCT-M 未展开，母配方与 MnO2 添加信息未写全。 |
| 10 | 10 | 0.7BiFeO3-0.3(Ba0.85Ca0.15)TiO3 with CuO additive | 692 K | 3 | 数值对应，材料/样品信息待补 | BF-BCT-C 未展开，母配方与 CuO 添加信息未写全。 |
| 11 | 11 | BaTiO3 | 120 °C | — | 漏项 | 当前文件完全缺失。此前单独诊断已抽到 BaTiO3 约 120°C，但未写入这份保留 4 号抽取的结果。 |
| 12 | 12 | (1−y)BiFe1−xCrxO3–yBaTi1−xMnxO3 (y=0.24, x=0.01) | 853.1 K | 7 | 材料与数值对应 | 变量代入与 Gold 母配方等价，853.1 K 正确；母配方候选选择仍保留人工 Review 提示。 |
| 13 | 12 | BiFeO3 | 1100 K | 6 | 材料与数值对应 | 材料与数值、单位对应；允许配方排版、近似符号和样品描述的等价写法，不表示所有元数据字段全等。 |
| 14 | 14 | BiFeO3 | 1103 K | 8 | 材料与数值对应 | 材料与数值、单位对应；允许配方排版、近似符号和样品描述的等价写法，不表示所有元数据字段全等。 |
| 15 | 15 | 0.67BiFeO3–0.33Ba0.70Ca0.30TiO3 | 634 K | 12 | 材料与数值对应 | 材料与数值、单位对应；允许配方排版、近似符号和样品描述的等价写法，不表示所有元数据字段全等。 |
| 16 | 15 | 0.725BiFeO3–0.275Ba0.85Ca0.15Ti0.9Zr0.075Sn0.025O3 | 673 K | 13 | 材料与数值对应 | 材料与数值、单位对应；允许配方排版、近似符号和样品描述的等价写法，不表示所有元数据字段全等。 |
| 17 | 15 | 0.74BiFeO3–0.26(Ba0.85Ca0.15)TiO3–1.2 wt.% MnO2 | 689 K | 16 | 材料与数值对应 | 按 Gold 接受的表 I Tc=689 K、1.2 wt.% MnO2 配对核验；全文同时存在 relaxor Tm 讨论，不能仅按数值关联其他样品。 |
| 18 | 15 | 0.6BiFe0.85Co0.15O3–0.4(Bi0.5K0.5)TiO3 | 690 K | 10 | 材料与数值对应 | 材料与数值、单位对应；允许配方排版、近似符号和样品描述的等价写法，不表示所有元数据字段全等。 |
| 19 | 15 | 0.74BiFeO3–0.26(Ba0.85Ca0.15)TiO3–0.8 wt.% MnO2 | 698 K | 15,18 | 材料与数值对应 | 预测 15 的 0.8 wt.%/698 K 完整对应；预测 18 是未赋值 x 的冗余不完整记录。Gold 的 relaxor 审查备注应保留。 |
| 20 | 15 | 0.6BiFeO3–0.4Bi0.5K0.5TiO3 | 703 K | 9 | 材料与数值对应 | 材料与数值、单位对应；允许配方排版、近似符号和样品描述的等价写法，不表示所有元数据字段全等。 |
| 21 | 15 | 0.7Bi0.9925Ca0.0075FeO3–0.3BaTiO3 + 0.3 wt.% MnO2 | 711 K | 14 | 材料与数值对应 | 材料与数值、单位对应；允许配方排版、近似符号和样品描述的等价写法，不表示所有元数据字段全等。 |
| 22 | 15 | 0.67Bi1.05Fe0.97Ga0.03O3–0.33BaTiO3 | 727 K | 11 | 材料与数值对应 | 材料与数值、单位对应；允许配方排版、近似符号和样品描述的等价写法，不表示所有元数据字段全等。 |
| 23 | 15 | 0.74BiFeO3–0.26(Ba0.85Ca0.15)TiO3 | 732 K | 17 | 材料与数值对应 | x=0 被写为 0 wt.% MnO2，与 Gold 不添加 MnO2 的母配方等价；732 K 保留。 |
| 24 | 17 | BiFeO3 | 1103 K | 19 | 材料与数值对应 | 材料与数值、单位对应；允许配方排版、近似符号和样品描述的等价写法，不表示所有元数据字段全等。 |
| 25 | 19 | 80 wt.% Bi0.9La0.1FeO3–20 wt.% Mn0.6Zn0.3Fe2.1O4 composite after high-pressure torsion | 367 K | 25,29,33 | 数值对应，材料/样品信息待补 | 已展开两相配方并保留 HPT，但该条结果未写出 80/20 wt.% 配比。不能用同温度的 MZFO fraction 代替复合材料。 |
| 26 | 19 | Mn0.6Zn0.3Fe2.1O4 (MZFO, literature value) | 501 K | 20 | 材料与数值对应 | 材料与数值、单位对应；允许配方排版、近似符号和样品描述的等价写法，不表示所有元数据字段全等。 |
| 27 | 19 | Mn0.6Zn0.3Fe2.1O4 (initial MZFO powder) | 518 K | 21,30 | 材料与数值对应 | initial MZFO powder 的 518 K 正确；商业牌号记录为其他来源陈述，不能按同温度直接计成这一 Gold 行。 |
| 28 | 19 | 80 wt.% Bi0.9La0.1FeO3–20 wt.% Mn0.6Zn0.3Fe2.1O4 composite | 518 K | 23,24,32 | 材料与数值对应 | 预测 23 的 80/20 wt.% 配方及 518 K 完整对应；预测 24、32 未写全配比。 |
| 29 | 19 | 80 wt.% Bi0.9La0.1FeO3–20 wt.% Mn0.6Zn0.3Fe2.1O4 composite after high-pressure torsion (new ferromagnetic order) | 778 K | 26 | 数值对应，材料/样品信息待补 | 已展开两相配方，HPT 和 new FM order (T_C*) 保留；80/20 wt.% 配比仍未写入本条。 |
| 30 | 19 | Bi0.9La0.1FeO3 fraction in high-pressure-torsion composite | 950 K | 28 | 数值对应，材料/样品信息待补 | BLFO 化学式及 fraction 正确，但 HPT 复合材料语境和 FE 转变类型只在 Evidence 中，尚未结构化保留。 |
| 31 | 20 | CrFe2O4 | 420 K | 36 | 材料与数值对应 | 材料与数值、单位对应；允许配方排版、近似符号和样品描述的等价写法，不表示所有元数据字段全等。 |
| 32 | 20 | BiFeO3 | 1103 K | 35 | 材料与数值对应 | 材料与数值、单位对应；允许配方排版、近似符号和样品描述的等价写法，不表示所有元数据字段全等。 |
| 33 | 22 | BiFeO3 | 1103 K | 37 | 材料与数值对应 | 材料与数值、单位对应；允许配方排版、近似符号和样品描述的等价写法，不表示所有元数据字段全等。 |
| 34 | 24 | BF-BNT-BT (y=0.23, x=0.00; y0.23x0.00) | 774 K | 39 | 数值对应，材料/样品信息待补 | 774 K 和 y=.23/x=0 样品对应，当前仅部分展开；缺完整外层配比和 BTM 展开，不能把现有字符串当最终三元配方。原文为约 774 K，预测还丢失了近似限定。 |
| 35 | 24 | BiFeO3 | 1100 K | 38 | 材料与数值对应 | BiFeO3/1100 K 对应，但 Gold 和原文的 approximately 未在本条 qualifier 中保留。 |
| 36 | 25 | lanthanum-substituted (1−x)BiFeO3−xPbTiO3 | 227 °C | 42 | 数值对应，材料/样品信息待补 | La-substituted 与 227°C 对应；PTO 已展开，BFO 仍未展开。原文未明确给出 La 掺杂量，不应猜测补齐。 |
| 37 | 25 | undoped (1−x)BiFeO3−xPbTiO3 | 650 °C | 41 | 数值对应，材料/样品信息待补 | undoped 与 650°C 对应；PTO 已展开，BFO 仍未展开，x 未确定。 |
| 38 | 25 | BiFeO3 | 1103 K | 40 | 材料与数值对应 | 材料与数值、单位对应；允许配方排版、近似符号和样品描述的等价写法，不表示所有元数据字段全等。 |
| 39 | 26 | PZT phase in 3BFO_n/7PZT_m composite sintered at 650 °C | 355 °C | 44 | 材料与数值对应 | PZT 相、355°C、3BFO_n/7PZT_m 和 650°C 烧结条件均与 Gold 对应；Gold 本身也使用 PZT 标签，完整 Zr/Ti 比例仍未明确。 |
| 40 | 27 | 0.65BiFeO3–0.35[(1−x)Bi0.5K0.5TiO3−xBaTiO3] (x=0.4) | 742.6 K | 45 | 数值对应，材料/样品信息待补 | x=.4、约 742.6 K 对应，BF-BKT-BT 母配方未展开。禁止拿内层二元配方替代整个三元体系。 |
| 41 | 27 | BiFeO3 | 1103 K | — | 漏项 | 当前文件缺失。原 PDF 实际写约 830°C，约合 1103.15 K；此前源段落恢复实验已抽到，但未并入此文件，也未修改 Gold。 |
| 42 | 28 | 0.58BiFeO3–0.42Bi0.5K0.5TiO3 single crystal | 671.5 K | 47 | 数值对应，材料/样品信息待补 | 约 671.5 K 和晶体样品对应，BFBKT 尚未展开成 0.58/0.42 配方。 |
| 43 | 28 | BiFeO3 | 1100 K | 46 | 材料与数值对应 | 材料与数值、单位对应；允许配方排版、近似符号和样品描述的等价写法，不表示所有元数据字段全等。 |
| 44 | 29 | (1−y)BiFe1−xCrxO3−yBaTi1−xMnxO3 (y=0.27, x=0.03) | 795.2 K | 49 | 材料与数值对应 | 代入 x=.03/y=.27 后与 Gold 等价，约 795.2 K 对应；旧重复文本/公式记录已合并。 |
| 45 | 29 | BiFeO3 | 1100 K | 48 | 材料与数值对应 | 材料与数值、单位对应；允许配方排版、近似符号和样品描述的等价写法，不表示所有元数据字段全等。 |
| 46 | 30 | BiFeO3-BaTiO3 composite | 580 °C | 52 | 下界对应（非严格） | Gold 明确为非严格下界事实；预测保留 over ~580°C，不能当作精确 580°C 或误报普通 FP。 |
| 47 | 30 | BiFeO3 | 830 °C | 51 | 材料与数值对应 | 材料与数值、单位对应；允许配方排版、近似符号和样品描述的等价写法，不表示所有元数据字段全等。 |

## 全部预测逐行核查

| 预测行 | 论文 | 当前材料名称 | 温度/限定 | Gold 行 | 状态 |
|---|---|---|---|---|---|
| 1 | 1 | BiFeO3 |  1103 K | 1 | MATCH |
| 2 | 10 | BF-BCT |  683 K | 7 | INCOMPLETE |
| 3 | 10 | BF-BCT-C |  692 K | 10 | INCOMPLETE |
| 4 | 10 | BF-BCT-M |  690 K | 9 | INCOMPLETE |
| 5 | 10 | BF-BCT-CM |  687 K | 8 | INCOMPLETE |
| 6 | 12 | BiFeO3 | ~ 1100 K | 13 | MATCH |
| 7 | 12 | 0.76BiFe0.99Cr0.01O3-0.24BaTi0.99Mn0.01O3 [y=0.24, x=0.01] |  853.1 K | 12 | MATCH |
| 8 | 14 | BiFeO3 |  1103 K | 14 | MATCH |
| 9 | 15 | 0.6BiFeO3 - 0.4Bi0.5K0.5TiO3 |  703 K | 20 | MATCH |
| 10 | 15 | 0.6BiFe0.85Co0.15O3 - 0.4(Bi0.5K0.5)TiO3 |  690 K | 18 | MATCH |
| 11 | 15 | 0.67Bi1.05Fe0.97Ga0.03O3 - 0.33BaTiO3 |  727 K | 22 | MATCH |
| 12 | 15 | 0.67BiFeO3 - 0.33Ba0.70Ca0.30TiO3 |  634 K | 15 | MATCH |
| 13 | 15 | 0.725BiFeO3 - 0.275Ba0.85Ca0.15Ti0.9Zr0.075Sn0.025O3 |  673 K | 16 | MATCH |
| 14 | 15 | 0.7Bi0.9925Ca0.0075FeO3 - 0.3BaTiO3 +0.3 wt.% MnO2 |  711 K | 21 | MATCH |
| 15 | 15 | 0.74BiFeO3 - 0.26(Ba0.85Ca0.15)TiO3 - 0.8 wt.% MnO2 |  698 K | 19 | MATCH |
| 16 | 15 | 0.74BiFeO3 - 0.26(Ba0.85Ca0.15)TiO3 - 1.2 wt.% MnO2 |  689 K | 17 | MATCH |
| 17 | 15 | 0.74BiFeO3-0.26(Ba0.85Ca0.15)TiO3-0wt.%MnO2 (x=0) |  732 K | 23 | MATCH |
| 18 | 15 | 0.74BiFeO3-0.26(Ba0.85Ca0.15)TiO3-x wt.% MnO2 |  698 K | 19 | INCOMPLETE_DUPLICATE |
| 19 | 17 | bulk BiFeO3 | ~ 1103 K | 24 | MATCH |
| 20 | 19 | Mn0.6Zn0.3Fe2.1O4 ferrospinel |  501 K | 26 | MATCH |
| 21 | 19 | initial Mn0.6Zn0.3Fe2.1O4 powder |  518 K | 27 | MATCH |
| 22 | 19 | Mn-Zn ferrospinels of industrial grades 3000HMC (USSR), 3C91 (Germany), ML27D (Japan) |  518 K | — | ADDITIONAL_COMPARISON |
| 23 | 19 | Bi0.9La0.1FeO3-Mn0.6Zn0.3Fe2.1O4 composite (80 wt.% Bi0.9La0.1FeO3 / 20 wt.% Mn0.6Zn0.3Fe2.1O4) |  518 K | 28 | MATCH |
| 24 | 19 | Bi0.9La0.1FeO3-Mn0.6Zn0.3Fe2.1O4 composite |  518 K | 28 | INCOMPLETE_DUPLICATE |
| 25 | 19 | Bi0.9La0.1FeO3-Mn0.6Zn0.3Fe2.1O4 composite HPT |  367 K | 25 | INCOMPLETE |
| 26 | 19 | Bi0.9La0.1FeO3-Mn0.6Zn0.3Fe2.1O4 composite HPT | new FM order (T_C*) 778 K | 29 | INCOMPLETE |
| 27 | 19 | Mn0.6Zn0.3Fe2.1O4 fraction |  367 K | — | ADDITIONAL_PHASE |
| 28 | 19 | Bi0.9La0.1FeO3 fraction |  950 K | 30 | INCOMPLETE |
| 29 | 19 | Bi0.9La0.1FeO3-Mn0.6Zn0.3Fe2.1O4 nanocomposite HPT |  367 K | 25 | INCOMPLETE |
| 30 | 19 | Mn0.6Zn0.3Fe2.1O4 powder (Mn0.6Zn0.3Fe2.1O4) |  518 K | 27 | MATCH |
| 31 | 19 | Mn-Zn ferrospinels of industrial grades 3000HMC (USSR), 3C91 (Germany), ML27D (Japan), same stoichiometric composition as Mn0.6Zn0.3Fe2.1O4 |  518 K | — | ADDITIONAL_COMPARISON |
| 32 | 19 | Bi0.9La0.1FeO3-Mn0.6Zn0.3Fe2.1O4 composite processed by compression |  518 K | 28 | INCOMPLETE_DUPLICATE |
| 33 | 19 | Bi0.9La0.1FeO3-Mn0.6Zn0.3Fe2.1O4 composite processed by HPT |  367 K | 25 | INCOMPLETE |
| 34 | 19 | Bi0.9La0.1FeO3 fraction |  778 K | — | ADDITIONAL_PHASE |
| 35 | 20 | BiFeO3 | ~ 1103 K | 32 | MATCH |
| 36 | 20 | CrFe2O4 | approximately 420 K | 31 | MATCH |
| 37 | 22 | BiFeO3 (BFO) | ~ 1103 K | 33 | MATCH |
| 38 | 24 | BiFeO3 |  1100 K | 35 | MATCH |
| 39 | 24 | 0.9BiFeO3-0.1Bi0.5Na0.5TiO3-BTM (y = 0.23, x = 0.00) |  774 K | 34 | INCOMPLETE |
| 40 | 25 | BiFeO3 (BFO) |  1103 K | 38 | MATCH |
| 41 | 25 | undoped (1-x)BFO-xPbTiO3 |  650 °C | 37 | INCOMPLETE |
| 42 | 25 | lanthanum-substituted (1-x)BFO-xPbTiO3 |  227 °C | 36 | INCOMPLETE |
| 43 | 25 | (BNFPT)x ceramics with Nd substitution | approximately 320 °C | — | REJECT_DEFINITE_TC |
| 44 | 26 | PZT | around 355 °C | 39 | MATCH |
| 45 | 27 | BF-BKT-BT (x=0.4) | approximately 742.6 K | 40 | INCOMPLETE |
| 46 | 28 | BiFeO3 | ~ 1100 K | 43 | MATCH |
| 47 | 28 | BFBKT crystal | about 671.5 K | 42 | INCOMPLETE |
| 48 | 29 | BiFeO3 (BFO) | ~ 1100 K | 45 | MATCH |
| 49 | 29 | 0.73BiFe0.97Cr0.03O3-0.27BaTi0.97Mn0.03O3 (x=0.03, y=0.27) | ~ 795.2 K | 44 | MATCH |
| 50 | 3 | Composite sample of 24 h |  129 °C | 2 | INCOMPLETE |
| 51 | 30 | pristine BiFeO3 ceramic | approximately 830 °C | 47 | MATCH |
| 52 | 30 | BiFeO3-BaTiO3 composite | over ~ 580 °C | 46 | MATCH |
| 53 | 4 | 0.66BaTiO3-0.33CoFe2O4 |  720 K | 3 | MATCH |
| 54 | 4 | 0.66BaTiO3-0.33CoFe2O4 |  746 K | 4 | MATCH |
| 55 | 4 | CoFe2O4 |  793 K | 5 | MATCH |
| 56 | 4 | 0.66BaTiO3-0.33CoFe2O4 randomly mixed ceramic composite | ~ 720 K | 3 | MATCH |
| 57 | 4 | 0.66BaTiO3-0.33CoFe2O4 layered ceramic composite | ~ 746 K | 4 | MATCH |
| 58 | 6 | BaTiO3 | below 200 °C | — | UNCERTAIN_BOUND |
| 59 | 7 | cubic BaTiO3 |  120 °C | 6 | MATCH |

以上为离线审查：未改 Gold、预测、材料工具或原始 Evidence，未调用 LLM。每行候选、材料、条件和审核说明保存在 [机器可读对照](F:/Python_Project/ComProScanner/outputs/runs/tc_20260904_material_recovered_20260906/gold_comparison.json)。

第 6/25 篇补核的原 PDF 段落见 [原文核查片段](F:/Python_Project/ComProScanner/outputs/runs/tc_20260904_material_recovered_20260906/gold_check_source_spans.json)。
