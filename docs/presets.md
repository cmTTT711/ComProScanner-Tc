# 属性配置

所有属性相关配置集中在 `src/comproscanner/presets/`。
`base.py` 定义契约，`registry.py` 自动发现配置，`_shared.py` 保存可复用的默认模型和提示词。
以下划线开头的辅助文件不会被当成属性配置。

## 配置内容

| 字段 | 用途 |
|---|---|
| `name` | 与文件名相同的属性标识 |
| `main_extraction_keyword` | 输出中的属性名称 |
| `property_keywords` | 科学信号及非文本 Evidence 的默认筛选规则 |
| `text_candidate_patterns` | 候选正文规则 |
| `evidence_providers` | 默认启用的工具集合 |
| `retrieval_queries`、`rag_settings` | RAG 查询、嵌入模型、输入长度和检索数量 |
| `modality_patterns` | 分别覆盖图片、表格、公式的选择规则 |
| `identifier_query` | 判断 Evidence 是否进入抽取的科学要求 |
| `extraction_instructions`、`examples` | 属性抽取要求和示例 |
| `agent_prompts` | identifier、extractor、vision 的角色说明和完整消息模板 |
| `models` | 三个角色的默认模型、服务地址、密钥变量名及请求参数 |
| `fact_fields` | 输出 JSON 字段示例；基础字段之外的内容保存在 Fact.attributes |
| `allowed_units`、`required_conditions` | 单位和条件检查，异常会标记而不删除事实 |
| `property_aliases`、`legacy_fields` | 评估输入中的属性别名及历史列名 |
| `processing_kwargs` | 传给文献入口的有效参数，例如允许本地 PDF 缺少 DOI |

核心字段 `material_reported`、`property`、`value`、`unit` 必须存在。
`conditions` 可以保留、删去或在配置中给出需要抽取的键。精确度、测量方法等扩展字段可加入 `fact_fields`，最终表格使用 `attribute.<字段名>` 列展示。

CLI 模型参数覆盖本次默认值，完整解析后的设置会写入运行配置。密钥内容不会写入 preset 或运行记录。
旧的 `extraction_kwargs` 已移除：它不被正式流程读取。请直接配置上表中的提示词、模型、字段和条件。
图片、表格和公式的选择使用 `modality_patterns`；文献解析阶段保留原始资产。
模型的 `parameters` 可以配置 `max_tokens` 等服务参数；默认不会新增自动重试，也不会强行改变历史抽取的 thinking 行为。

## 新增属性

复制 `band_gap.py` 为新文件，返回一个完整的 `PropertyExtractionPreset`：

```python
from comproscanner.presets.base import PropertyExtractionPreset

def get_preset_definition():
    return PropertyExtractionPreset(
        name="my_property",
        main_property_keyword="my_property",
        main_extraction_keyword="my property",
        property_keywords={"exact_keywords": ["my property"]},
        text_candidate_patterns=(r"my property",),
        identifier_query="判断是否明确报告了材料的该属性数值。",
        extraction_instructions="仅抽取原文明确支持的材料、数值、单位和测量条件。",
        retrieval_queries=("my property material measured value",),
        allowed_units=("unit",),
        evidence_providers=("rule_text", "table"),
    )
```

之后运行 `comproscanner presets` 即可发现它，不需要改注册表或主流程。
图片工具需要一个可用的 vision 模型。Tc 配置已填入此前项目实际使用的 Qwen VL Plus；其他属性可在自身 `models` 中指定。

## Tc 基线

保留原有高召回候选策略，并由 identifier 判断科学相关性。不要在通用工具中偷偷改成 Tc 专用初筛。
冻结测试不仅检查科学提示词，也比较最终发给模型的完整消息。
改变 Tc 科学规则、条件要求或输出字段属于策略变更，应另开实验和结果目录，不能混入纯清理验收。
