# 保留 9 月 4 日抽取，接通材料工具

前一次 26 条 Evidence 付费实验保留了抽取，却使用 identity 材料处理，未验证用户要求的材料展开链路。这是实验目标执行偏差；不能用它判断材料工具效果。

现在正常 CLI 的后处理默认使用 `article` 材料工具。抽取仍沿用 4 号的逐 Evidence identifier/extractor 和 Tc 提示词；材料步骤只读取其后保存的 Fact 与同篇 Article 定义。已有 `VariableCompositionNormalizer` 的计算逻辑已恢复，缩写定义连接到同一材料处理入口。已有抽取结果的 `abbreviations` 映射也会传入，而不必为了取全称重新运行旧多 agent 流程。

本次实际执行：**4 号原始 predictions → 同篇材料定义恢复 → 变量代入/排版规范化 → 保留原始 Fact 信息的合并 → JSON/Review**。没有重新抽取 Tc。输入仍为 4 号的 61 行，输出 59 行；逐行检查确认所有原始断言仍能在合并结果中找到，温度、单位、qualifier、conditions 和 Evidence 均未变化。

- 27 行材料字段发生展开或规范化；包含部分展开，不代表 27 行全部完成科学审查。
- 第 12 篇：`y=0.24,x=0.01` 恢复为 `0.76BiFe0.99Cr0.01O3–0.24BaTi0.99Mn0.01O3`，母配方推定过程保留 Review 标记。
- 第 29 篇：恢复为 `0.73BiFe0.97Cr0.03O3–0.27BaTi0.97Mn0.03O3`。
- 第 19 篇：MZFO、BLFO 分别展开为 `Mn0.6Zn0.3Fe2.1O4`、`Bi0.9La0.1FeO3`，保留原名中的粉体、组分相、复合材料、HPT 和配比信息。
- 第 15 篇：母配方展开、x=0 的 MnO2 添加量代入；原来的 732 K 完整保留。小数点乱码也得到修正。
- 第 4 篇：BT-CF 展开为 `0.66BaTiO3–0.33CoFe2O4`，随机混合/层状和测量条件均保留。

20 个原始行有保守 Review 标记，包含未解析标签、未确定变量、部分展开和推定母配方等，不能简单理解为 20 个化学配方错误。第 10 篇的源 PDF 连接号是异常控制字符，程序保留原名，避免误将 `TiO3`、`MnO2` 或局部系数当成整个复合材料。第 27 篇的复杂三元体系也保留原名，避免只恢复内层二元配方。纯样品标签、未明确报告的掺杂比例仍待处理，不能据此宣称所有名称已经完全恢复。

`material_reported` 保留 4 号原始名称；`material_normalized` 存放展开结果；新增 `material_resolution` 保存使用的定义、变量、工具和同篇文件来源。在 Review 中对应原名、规范名、依据和处理问题列。

验证结果：78 项相关测试通过，包含冻结的 Tc 抽取契约、正常抽取入口和无模型材料回放入口；跨论文缩写隔离、冲突定义、完整添加剂、禁止配方尾部替代母配方、禁止内层二元代替三元体系均有检查。最终回放屏蔽了外部请求入口，外部调用尝试为 0。4 号原始预测文件校验值未变。

[恢复后的 Review](F:/Python_Project/ComProScanner/outputs/runs/tc_20260904_material_recovered_20260906/review.xlsx) · [预测 JSON](F:/Python_Project/ComProScanner/outputs/runs/tc_20260904_material_recovered_20260906/predictions.json) · [61 行前后对照](F:/Python_Project/ComProScanner/outputs/runs/tc_20260904_material_recovered_20260906/material_changes.json) · [验证记录](F:/Python_Project/ComProScanner/outputs/runs/tc_20260904_material_recovered_20260906/validation.json)
