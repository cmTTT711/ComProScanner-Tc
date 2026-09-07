from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
files={
'README.md':r'''# ComProScanner

从科学文献提取可追溯的材料属性。正式流程只有一条：

**文献 → Article → Evidence → 逐条抽取 → 材料恢复 → 结果表 / Review / 评估。**

Tc 保留已验证的 9 月 4 日 Evidence 抽取策略；材料展开和名称恢复复用已有本地工具。
`band_gap` 展示如何只增加属性配置复用流程，其真实论文准确率尚未验证。

## 项目目录

```text
src/comproscanner/
  documents/     文献获取、出版社适配、Docling、Article 与解析资产
  evidence/      唯一正文切分、五个可选 Evidence 工具、RAG
  extraction/    每条 Evidence 的识别、视觉解读与属性抽取
  results/       材料恢复、保守合并、表格、Review、Gold、评估
  presets/       属性关键词、提示词、模型、字段和规则
  cli/           统一命令入口和阶段编排
data/
  literature/    原始文献、解析来源、获取记录
  runs/          各次运行的独立产物
  gold/          人工标准答案
  reports/       历史审查、基准报告和 PPT
  maintenance/   清理快照、完整性记录和验收结果
tests/           按正式模块组织的离线回归测试
docs/            使用与扩展说明
reference/       停用代码和历史实验；不参与安装、运行或正式测试
```

根目录的 `_paths.py` 等文件实际位于 Python 包内，是日志、异常、历史路径解析等少量通用支持。

## 安装

Python 3.12 或 3.13：

```bash
pip install -e .
pip install -e ".[pdf]"       # Docling PDF 解析
pip install -e ".[rag]"       # 本地 PhysBERT / Chroma 检索
pip install -e ".[all,test]"  # 全部正式功能与测试
```

复制 `.env.example` 为 `.env`，填写需要使用的密钥。已有 `.env` 不需要重新创建。
模型选择和默认服务地址在 preset，密钥值只从环境变量读取。

## 使用

先检查计划，再进行本地准备；最后才启用付费模型：

```bash
comproscanner presets
comproscanner sources
comproscanner run --source manual_pdf --folder data/literature/pdfs/manual --run-id tc_demo
comproscanner run --source manual_pdf --folder data/literature/pdfs/manual --run-id tc_demo --through prepare --execute-pipeline
comproscanner run --source manual_pdf --folder data/literature/pdfs/manual --run-id tc_demo --execute-pipeline --execute-models --resume
```

以上默认使用 `curie_temperature`。指定 `--preset band_gap` 切换属性。
默认 Tc 使用候选文本、表格、图片和公式；PhysBERT 可在 preset 中启用，或追加 `--with-rag`。
重复传入 `--provider` 可覆盖本次工具集合，例如 `--provider rule_text --provider table`。

每次运行写入 `data/runs/<run-id>/`：

- `article.csv`、`processor_workspace/`：统一文章与完整解析产物。
- `evidence/`：正文切分、来源信息和各条 Evidence。
- `extractions/`：每条 Evidence 的抽取检查点和原始模型响应。
- `predictions.json`：保留数值、限定、条件、原始材料名、恢复名称及证据关联。
- `predictions.xlsx` / `predictions.csv`：最终结果表；XLSX 另有论文信息表。
- `review.xlsx`：附带原始 Evidence、图片路径和材料恢复问题的审查表。
- `metrics.json`：显式执行评估后生成的严格匹配指标、FP 和 FN。

输入现有 Article 时会沿用其文件位置，并在配置中记录路径与哈希。
JSON 是完整保存格式；Excel 的单元格长度限制不适合存储整篇文献。

## 修改与验证

新增常规材料属性，只增加 `src/comproscanner/presets/<属性名>.py`。
通用流程不应该出现属性名称判断分支。新数据模态才需要增加通用工具。

```bash
pytest -q
```

离线测试禁止建立网络连接；真实服务测试明确标为 integration。
已有科学结果并非全部正确：材料恢复仍可能不完整，推测性 Tc 和漏项仍需人工审查。

详见 [架构](docs/architecture.md)、[属性配置](docs/presets.md)、[命令与审查](docs/usage.md)、[清理验收](docs/cleanup.md)。

本项目基于原 [ComProScanner](https://github.com/slimeslab/ComProScanner)。原作者信息、MIT 许可证和引用文件保留在仓库中。
''',
'docs/architecture.md':r'''# 四个模块与数据边界

## documents：文献到 Article

本地 PDF、下载 PDF 和 Wiley PDF 使用同一 Docling 解析器，输出 Markdown 后进入统一 Article。
Elsevier、Springer、IOP 的原生 XML 使用已有格式适配器，保留其原始文件并汇入相同的 Article 契约；不会为了统一格式把 XML 再变成 PDF。

`documents/schemas/article_csv.py` 定义 Article：文献标识、论文标题、完整正文、章节、表格、图片清单、来源路径、文件哈希和扩展元数据。
未知章节也保留在正文中。`is_property_mentioned` 只是历史诊断字段，不会剔除文章。

每份 Docling 输入另存原始 PDF、`article.md`、`document.json`、页面图和全部识别出的图片／表格图。资产清单明确记录导出错误。
“完整保存”指原始文件和解析产物完整保留，不意味着 OCR 或版面识别必然无误。
原始文献不因关键词未命中而丢弃图片。

出版社适配器只生成文献数据，不再访问 MySQL 或创建隐藏的向量库。
IOP 的整理操作在工作副本上进行；原始输入目录不被整理过程删除。CDN 图片下载由网络执行许可控制。

## evidence：一次切分、五个工具

统一切分器从 Article 的 `full_text` 生成 TextChunk。章节、编号和文字保持来源关联。
末尾可识别的参考文献区域被标记，在常规检索中跳过，但仍保留在文章和切分产物中。

| preset 工具名 | 职责 |
|---|---|
| `rule_text` | 候选关键词／正则命中统一文本块 |
| `physbert` | 对相同文本块建库，按属性查询检索 |
| `table` | 选择并保存表格原文、标题、行列与注释 |
| `figure` | 选择图片、标题、邻近正文和原图位置 |
| `equation` | 保留公式及附近原始解释 |

候选文本与 RAG 命中相同 chunk 时生成一条文本 Evidence，记录两种检索来源。
停用的工具不会执行其来源读取。工具不负责判断某个材料属性是否真实成立。

## extraction：每条 Evidence 独立抽取

文本、表格、公式：identifier → 被接受后 extractor。
图片：vision 读取像素 → extractor 形成结构化事实。

不把整篇文章的 Evidence 合并后发送。一个 Evidence 失败会记录错误，后续 Evidence 继续执行。
保留原始响应和逐条检查点。Tc 的科学提示词、完整消息模板和 Evidence 规则有冻结回归测试。
没有重新接入旧 CrewAI 流程；其中曾改变 Tc 结果的清洗／多 agent 编排不属于正式流程。

## results：材料恢复到最终表格

使用同一篇文章的上下文和原 PDF 文字，展开明确缩写、恢复母配方，再代入当前事实自己的变量赋值。
不会借用另一篇文章或另一个样品的变量。未能确定的材料名称保留，并记录待审查原因。
保守合并保留所有 Evidence；不同条件、限定或属性扩展字段不会被当作相同事实合并。

JSON 保留原始材料名、恢复名、值、单位、条件、限定、材料恢复过程及 Evidence IDs。
表格额外关联论文标题、DOI、来源及可用的出版社元数据；未知信息留空。
Review 只由人工决定接受、拒绝或修改，抽取运行不会自动改写 Gold。

## 编排与扩展

`cli/` 按 documents、evidence、extraction、results、run 分开编排。
`run` 是正式端到端入口；阶段命令使用相同实现。
各阶段记录配置和状态。恢复运行前检查配置与输入，避免把不同策略混在一次运行中。

新属性加入 preset；新的来源适配器输出 Article；新 Evidence 工具输出统一 Evidence；新导出工具读取最终 Facts。
`reference/` 不在安装路径内，也不被正式源码或测试导入。
''',
'docs/presets.md':r'''# 属性配置

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

核心字段 `material_reported`、`property`、`value`、`unit` 必须存在。
`conditions` 可以保留、删去或在配置中给出需要抽取的键。精确度、测量方法等扩展字段可加入 `fact_fields`，最终表格使用 `attribute.<字段名>` 列展示。

CLI 模型参数覆盖本次默认值，完整解析后的设置会写入运行配置。密钥内容不会写入 preset 或运行记录。
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
''',
'docs/usage.md':r'''# 命令与人工审查

## 输入

`run --source manual_pdf --folder <目录>`：本地 PDF。
`run --source downloaded_pdf --folder <目录>`：已下载的 PDF。
`run --source elsevier|springer|wiley --doi-file <文件>`：对应出版社来源，每行一个 DOI；实际执行还需要 `--execute-network` 和对应密钥。
IOP 使用已有 XML 输入，目录通过 `.env` 中的 `IOP_papers_path` 配置。

`process-articles` 可单独执行文献处理，默认仅展示计划；`--execute-processing` 才处理。
其产物默认放在 `data/literature/processing/<preset>`，也可用 `--workspace` 指定位置。
端到端 `run` 把来源处理工作区放在自己的运行目录中。

已有统一 Article 或历史 CSV：

```bash
comproscanner normalize --csv source_a.csv --csv source_b.csv --output article.csv
comproscanner run --csv article.csv --preset curie_temperature --run-id tc_demo --through prepare --execute-pipeline
```

## 抽取与恢复

```bash
comproscanner extract --run-id tc_demo --preset curie_temperature --execute
comproscanner review --run-id tc_demo
```

`run` 默认执行到 Review。`--resume` 跳过已完成检查点，包括记录过的失败；失败项重试必须明确发起新运行或使用覆盖选项。
不要把 `--force` 和 `--resume` 同时使用。

付费模型只在 `--execute` / `--execute-models` 后调用。
PDF、切分、本地 RAG、材料恢复和表格生成不调用 Qwen / DeepSeek；首次加载 Docling 或嵌入模型可能需要下载本地模型权重。

重新处理已有结果中的材料名称，无需模型调用：

```bash
comproscanner postprocess-materials --predictions data/runs/old_run/predictions.json --evidence data/runs/old_run/evidence/all.json --article-csv article.csv --run-id new_material_run
```

目标运行目录必须为空，原有预测不会被覆盖。

## Review 到 Gold

打开 `review.xlsx`，检查材料、值、条件和 Evidence；在 decision 列选择 `ACCEPT`、`REJECT` 或 `MODIFY`。
修改后的字段随 `MODIFY` 行写入新 Gold。留空行和 REJECT 行不进入 Gold。

```bash
comproscanner accept-review --review data/runs/tc_demo/review.xlsx --output data/gold/tc_reviewed.json
comproscanner evaluate --run-id tc_demo --gold data/gold/tc_reviewed.json
```

Gold 文件已存在时拒绝覆盖。导入只包含人工选择的事实；不要把未完成的 Review 当作完整的召回率评估标准。

## 30 篇历史 Gold

历史 Gold 使用 paper_id，预测使用 document_id，需要显式映射：

```bash
comproscanner evaluate --run-id cleanup_material_replay_20260906 --preset curie_temperature --gold data/gold/tc_001_030/gold_facts.json --paper-map data/gold/tc_001_030/paper_id_map.json
```

这里输出严格事实匹配：材料名、值、单位、限定、条件和扩展属性需要对应，重复项按数量计分，不自动换算单位或理解配方等价。
此前报告的 **43/45 是温度事件覆盖**，不能与严格事实 F1 混用。人工科学等价判断见历史 Gold 对照报告。

## 文件迁移

历史预测、Gold、Evidence 和文章内容保留原样。旧文件中的路径通过 `data/path_migrations.json` 在读取时定位到新位置。
新运行直接记录当前位置。不要删除路径映射后继续使用带旧路径的历史缓存。
历史脚本只作为参考，不保证在新目录中原样运行。
''',
'CONTRIBUTING.md':r'''# 开发约定

- 正式代码只放在 `src/comproscanner/`，按 documents、evidence、extraction、results 分工。
- 属性策略只放在 presets；不复制一套新主流程来增加属性。
- 不从 reference 导入代码，也不把数据库、图谱或 CrewAI 重新作为默认依赖。
- 原始文献、Gold 和已有预测不覆盖。新实验使用新的 run-id。
- 纯重构必须通过冻结 Tc 消息、材料恢复和端到端离线回归。
- 科学策略变更与项目整理分开，报告匹配口径，不能用温度覆盖冒充完整事实准确率。

```bash
pip install -e ".[all,test]"
pytest -q
```

默认测试阻断网络连接。需要真实服务的测试使用 integration 标记，并在实际运行前明确数据范围和调用预算。
''',
'CHANGELOG.md':'''# 变更记录

## 2026-09-06：正式流程净化

- 按文献、Evidence、抽取、结果四个模块重新组织代码与测试。
- 隔离旧 CrewAI、MySQL、Neo4j、图谱及实验代码。
- 属性模型、角色消息、字段和工具规则集中到 presets。
- 保留 Tc 抽取消息与材料恢复结果，增加可回放验收。
- 保存完整解析资产，统一结果表、Review、Gold 导入和严格评估入口。
- 历史数据迁入 data，保留内容及读取旧路径的映射。

原变更记录位于 `reference/documentation_before_cleanup.zip`。
''',
'.env.example':'''# Copy to .env and fill only the services you use. Never commit real keys.
DASHSCOPE_API_KEY=
DEEPSEEK_API_KEY=

# Optional publisher acquisition
SCOPUS_API_KEY=
SCIENCEDIRECT_INSTTOKEN=
SPRINGER_OPENACCESS_API_KEY=
SPRINGER_TDM_API_KEY=
WILEY_API_KEY=
IOP_papers_path=
SEMANTIC_SCHOLAR_API_KEY=

# Optional access for downloading local model weights
HF_TOKEN=
''',
'reference/README.md':'''# 参考代码边界

此目录不参与正式运行、安装包或默认测试。

- `legacy/`：原 CrewAI 流程、MySQL、Neo4j、语义评估、可视化等停用实现，以及对应历史测试。
- `history.zip`：早期实验、示例、临时脚本和开发产物。
- `documentation_before_cleanup.zip`：清理前文档站点和自动发布配置。
- `maintenance/`：这次迁移使用的一次性脚本，仅用于审计或恢复参考。

需要恢复某项功能时，应把需要的能力接到正式模块的接口上，不能直接修改 sys.path 把此目录加入运行依赖。
旧代码可能依赖旧路径、旧包或外部服务；保留代码不代表承诺其仍可独立运行。
完整清理前源码快照与原始 Git 状态保存在 `data/maintenance/cleanup_20260906/`，包含当时尚未提交的修改。
''',
'.github/workflows/ci.yml':'''name: ci
on: [push, pull_request]
permissions:
  contents: read
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.12", "3.13"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - name: Install formal pipeline and offline tests
        run: pip install -e ".[all,test]"
      - name: Offline regression
        run: pytest -q
      - name: Build distributable
        run: pip wheel --no-deps --no-build-isolation . -w dist
'''
}
for name,content in files.items():
    path=ROOT/name
    path.parent.mkdir(parents=True,exist_ok=True)
    # '+' characters above are patch notation only; source strings have normal text.
    path.write_text(content,encoding='utf-8')
print('Wrote',len(files),'documentation/configuration files')
