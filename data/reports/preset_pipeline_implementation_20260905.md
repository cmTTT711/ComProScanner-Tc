# 统一属性抽取流程：实施与验证

本轮已完成 preset 驱动的流程接通与接口补齐。继续使用同一条 Article → Evidence → Fact 主流程，每条 Evidence 独立判断和抽取，不增加文章级初筛。

## 实施结果

1. **新增属性只增加一个 preset 文件。** `src/comproscanner/presets/<name>.py` 提供 `get_preset_definition()`，自动发现，无须再编辑注册表、CLI 或复制抽取流程。新增 `band_gap.py` 作为第二属性示例。
2. **领域规则与运行配置分开。** preset 明确保存识别/抽取说明、关键词、候选规则、RAG 查询、示例、允许单位和必要条件。模型、服务地址、凭据环境变量名与超时使用统一 CLI 配置。Tc 旧 Python 入口保持兼容。
3. **材料恢复接入现有后处理。** 默认 identity 保留原文；选择 `material-parser-api` 时使用原有材料服务。503、空结果、多候选歧义及第三方解析器异常都保留原材料和 Fact，在 `processing_issues` 记录问题。成功解析缓存，失败不会永久缓存。
4. **条件和来源保留。** 去重键加入实验条件，不同条件分别保留；合并保留全部 Evidence、材料原文变体和处理诊断。Review 展示原始证据及处理问题。
5. **坏记录不影响同批好记录。** 缺材料/值、错误条件结构、错误 qualifier 等模型行写入 `failures.json`，附原始行和 Evidence ID；同一响应中的有效 Fact 仍输出 JSON 和 Review。
6. **恢复运行检查配置。** 检查输入文件、Article 内容、工具选择、RAG 查询、分块参数、提示词、模型及材料处理配置，避免新设置复用旧缓存。历史 Evidence 没有准备配置时要求新 run ID。
7. **评估使用通用字段。** 严格评分要求显式属性、材料、值、单位和条件。Tc 旧字段只在导入时显式转换。文档 ID 或属性名称完全不重合时，CLI 提示先对齐，避免输出误导性的零准确率。
8. **补齐 Review 安装依赖。** 将代码已使用的 `openpyxl` 加入基本依赖，保证默认 Review 路径有对应包。

## 验证证据

- 完整离线测试：**792 passed，17 integration deselected**，用时 41.84 秒。日志：`tmp/preset_pipeline_tests_20260905.log`。
- 随后新增的 Tc 固定契约测试：**1 passed**。合计 793 个离线测试通过。
- 带隙通过真实 CLI 和真实模型适配器的固定响应测试，覆盖两篇 Article、逐 Evidence 调用、不同测定方法、JSON、Review 和严格评估。模型响应是测试替身，未发起 API 请求。
- 模拟 HTTP 503：三条 Fact 全部保留，JSON 和 Review 都显示诊断。
- 异常模型行：保留原始错误行，有效同批结果正常输出；恢复运行保留错误状态。
- 恢复运行改变源 CSV、工具选择、分块参数或模型时，在新模型调用前拒绝旧缓存。
- CLI 帮助与 preset 列表通过子进程检查，不加载 CrewAI、LiteLLM、Torch、Transformers 或 Chroma 等模型依赖。
- `git diff --check` 通过。

## Tc 基线保护

识别提示、抽取提示、RAG 查询、文本候选规则、关键词和默认工具选择均与修改前逐项一致。固定契约 SHA-256：

`69edac2a371405b361f806940572a4e2510ca3e5ecc29cf10c5485a5dc6993be`

历史 `tc_fulltext_001_030_20260904/predictions.json` 的 61 条预测未修改，文件 SHA-256：

`d786e325318a58d418084860bd8453f3ceec7266baa7e1be9a5232924480b3b7`

对这 61 条保存记录分别用修改前、修改后的默认后处理重放，两者都得到 59 条，所有原有字段和 Evidence 引用一致。两边都会合并同样的两条排版等价重复记录；这不是本轮新增删除。新增字段仅为处理诊断。机器可读记录：`outputs/reports/preset_pipeline_validation_20260905.json`。

## 使用方式

```powershell
python -m comproscanner.cli presets
python -m comproscanner.cli run --preset band_gap --csv article.csv --run-id band_gap_demo
python -m comproscanner.cli run --preset curie_temperature --csv article.csv --run-id tc_demo --through prepare --execute-pipeline
```

第二条只显示计划；第三条执行本地 Evidence 准备。模型抽取使用既有 `--execute-pipeline --execute-models`，外部材料服务另需 `--material-normalizer material-parser-api --execute-network`。具体 preset 字段、扩展规则与运行配置见 `docs/extensions.md`。

## 当前验证边界

本轮项目外部模型 API 调用为 **0**，没有重新付费跑 30 篇，也没有进行新的在线材料服务或出版社服务验收。带隙验证证明配置与链路可复用，不代表带隙真实论文准确率；复杂材料服务测试证明传递、容错和保留行为，不代表服务一定能正确恢复所有配方。

离线配置比较与保存结果重放不能代替新的模型质量评估。旧 Gold 的数字 paper_id、DOI、属性别名与实验条件需要明确对齐；旧温度命中诊断与当前完整 Fact 严格评分不能直接比较。

修改前代码与测试保存在 `work/preset_pipeline_baseline_20260905`。历史 Gold、PDF、实验结果和 PPT 保持原样。
