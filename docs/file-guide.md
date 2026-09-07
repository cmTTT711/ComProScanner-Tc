# ComProScanner 文件与目录用途说明

按 2026-09-06 03:21 的实际工作区生成。登记 3460 个物理文件、679 个目录，其中正式包 Python 文件 87 个。

所有目录和文件均在 [完整可搜索清单](file-inventory.html) 中逐条列出。阅读版逐文件解释正式代码、测试、配置与可读参考代码；海量运行产物用同结构说明，完整清单仍为每个实际文件保留独立条目。

清单只说明文件职责。JSON 结构栏只列字段名/数量，不展示论文全文、模型响应或密钥。`.env` 与 Git 配置不读内容；压缩包按物理文件登记，不展开包内成员。缓存和安装元数据也如实列出。

## 先看整条链路

PDF / 出版社来源 → `documents` → 统一 Article → `evidence`（一次切分、五个工具）→ `extraction`（每条证据独立调用模型）→ `results`（材料恢复、预测、Review、Gold、评估）。`presets` 提供属性知识，`cli` 负责接通各阶段。

Article 是一篇文章的统一数据记录，目前落在 CSV/旁存文件中；它不是另一个需要寻找的 article.py 类。Evidence 是来源证据；Fact 是抽出的材料-属性事实。

## 根目录

| 路径 | 具体用途 |
|---|---|
| [.env](<F:/Python_Project/ComProScanner/.env>) | 本机实际 API 密钥和输入路径配置；本次只登记文件用途，不读取或展示内容。 |
| [.env.example](<F:/Python_Project/ComProScanner/.env.example>) | 环境变量填写模板：模型密钥、出版社凭据、IOP 路径等；供配置新环境使用。 |
| [.git](<F:/Python_Project/ComProScanner/.git>) | Git 自身的版本记录、引用、对象和本地状态，不参与论文处理。 |
| [.github](<F:/Python_Project/ComProScanner/.github>) | GitHub 自动化与提问/问题反馈模板。 |
| [.gitignore](<F:/Python_Project/ComProScanner/.gitignore>) | 规定不进入 Git 的密钥、缓存、大型原文、运行资产和构建产物。 |
| [CHANGELOG.md](<F:/Python_Project/ComProScanner/CHANGELOG.md>) | 项目变更记录。 |
| [CITATION.cff](<F:/Python_Project/ComProScanner/CITATION.cff>) | 学术引用项目时使用的作者、名称等引用元数据。 |
| [CONTRIBUTING.md](<F:/Python_Project/ComProScanner/CONTRIBUTING.md>) | 维护、开发、修改与验证约定。 |
| [data](<F:/Python_Project/ComProScanner/data>) | 原始文献、历史运行、人工标准、报告和本地验证产物；不是安装包源码。 |
| [docs](<F:/Python_Project/ComProScanner/docs>) | 面向使用、维护和验收的项目说明。 |
| [LICENSE](<F:/Python_Project/ComProScanner/LICENSE>) | 项目开源许可证。 |
| [pyproject.toml](<F:/Python_Project/ComProScanner/pyproject.toml>) | 包名/版本、Python 和依赖要求、CLI 注册、打包范围、pytest 与格式化配置。 |
| [README.md](<F:/Python_Project/ComProScanner/README.md>) | 项目总入口：目录、安装、基本命令和文档链接。 |
| [reference](<F:/Python_Project/ComProScanner/reference>) | 不参与当前正式运行的历史实现、实验归档和一次性迁移脚本。 |
| [src](<F:/Python_Project/ComProScanner/src>) | 可安装的正式 Python 包源码，以及安装工具生成的包元数据。 |
| [tests](<F:/Python_Project/ComProScanner/tests>) | 正式回归测试及其输入样本；默认离线执行。 |

## 正式代码：逐文件


### src/comproscanner

正式应用包：四个业务模块、属性配置、CLI 和少量共用支持。

| 文件 | 具体用途 |
|---|---|
| [__init__.py](<F:/Python_Project/ComProScanner/src/comproscanner/__init__.py>) | 包的说明和版本号；导入 comproscanner 时不会启动旧流程或模型。 |
| [__main__.py](<F:/Python_Project/ComProScanner/src/comproscanner/__main__.py>) | 使 python -m comproscanner 可以调用统一命令行入口。 |
| [_errors.py](<F:/Python_Project/ComProScanner/src/comproscanner/_errors.py>) | 定义参数、文件、依赖及中断相关异常，统一错误表达。 |
| [_logging.py](<F:/Python_Project/ComProScanner/src/comproscanner/_logging.py>) | 配置日志级别、终端格式和日志文件输出，供各模块记录执行过程。 |
| [_paths.py](<F:/Python_Project/ComProScanner/src/comproscanner/_paths.py>) | 读取 data/path_migrations.json，把历史记录中的旧文件路径定位到迁移后位置，避免改写原结果。 |

### src/comproscanner/cli

命令行入口和阶段编排，把业务模块连成一条流程。

| 文件 | 具体用途 |
|---|---|
| [__init__.py](<F:/Python_Project/ComProScanner/src/comproscanner/cli/__init__.py>) | 包标识与公共接口导出。所属目录用途：命令行入口和阶段编排，把业务模块连成一条流程。 |
| [__main__.py](<F:/Python_Project/ComProScanner/src/comproscanner/cli/__main__.py>) | 支持 python -m comproscanner.cli，转入相同 CLI 主入口。 |
| [common.py](<F:/Python_Project/ComProScanner/src/comproscanner/cli/common.py>) | CLI 共用的小函数：运行编号、安全文件名、网络执行检查，以及 Evidence 和 Fact 的反序列化。 |
| [documents.py](<F:/Python_Project/ComProScanner/src/comproscanner/cli/documents.py>) | 编排文献发现、开放获取 PDF 下载和单独的文献处理命令。 |
| [evidence.py](<F:/Python_Project/ComProScanner/src/comproscanner/cli/evidence.py>) | 读取 Article CSV，加载 preset，按开关运行 Evidence 工具；写出分块、证据、失败项和准备配置。 |
| [extraction.py](<F:/Python_Project/ComProScanner/src/comproscanner/cli/extraction.py>) | 逐条执行 Evidence 抽取，保存模型配置、响应和检查点；组装 Fact，调用材料后处理并写预测。 |
| [main.py](<F:/Python_Project/ComProScanner/src/comproscanner/cli/main.py>) | 定义所有 CLI 子命令和参数；合并 preset 默认模型设置，再把命令分派到对应阶段。 |
| [results.py](<F:/Python_Project/ComProScanner/src/comproscanner/cli/results.py>) | 编排已有预测的材料恢复、最终表格导出、Review 生成及 Gold 评估；准备文章与 PDF 上下文。 |
| [run.py](<F:/Python_Project/ComProScanner/src/comproscanner/cli/run.py>) | 端到端主流程：文献处理、Article 归一化、Evidence 准备、抽取、Review、评估；维护阶段状态和续跑检查。 |

### src/comproscanner/documents

第一模块：来源文献到统一 Article，保留原始资产。

| 文件 | 具体用途 |
|---|---|
| [__init__.py](<F:/Python_Project/ComProScanner/src/comproscanner/documents/__init__.py>) | 包标识与公共接口导出。所属目录用途：第一模块：来源文献到统一 Article，保留原始资产。 |
| [assets.py](<F:/Python_Project/ComProScanner/src/comproscanner/documents/assets.py>) | 在旧 XML 内容变换前保留正文；从 Docling 结果取标题；保存原 PDF、Markdown、结构 JSON、页面图、图片和资产清单。 |
| [csv_store.py](<F:/Python_Project/ComProScanner/src/comproscanner/documents/csv_store.py>) | 清除 CSV 中的 NUL 字符，规范化并保存 Article；关联图片清单，写每篇 article.md 和 metadata.json，按 DOI 避免重复写入。 |
| [dispatch.py](<F:/Python_Project/ComProScanner/src/comproscanner/documents/dispatch.py>) | 按来源和 DOI 的出版社信息分派到五个文献处理器；本身不抽取属性、不建立隐藏向量库。 |
| [docling.py](<F:/Python_Project/ComProScanner/src/comproscanner/documents/docling.py>) | 配置和调用 Docling：OCR、版面、表格、Markdown、图片；还提供从 Markdown 生成历史章节列的适配方法。 |
| [figures.py](<F:/Python_Project/ComProScanner/src/comproscanner/documents/figures.py>) | 各来源共用的图片存储工具：保存图片字节或本地图片、维护说明和 manifest、记录文献处理失败。 |
| [metadata.py](<F:/Python_Project/ComProScanner/src/comproscanner/documents/metadata.py>) | 辅助查询 OpenAlex 元数据和 Crossref DOI；生成统一参数错误信息并记录超时 DOI。 |
| [prepare_iop.py](<F:/Python_Project/ComProScanner/src/comproscanner/documents/prepare_iop.py>) | 在工作副本内整理 IOP XML 和 ZIP，保留图片资源，识别真实 DOI，补全本地元数据并记录图片所在目录。 |
| [signals.py](<F:/Python_Project/ComProScanner/src/comproscanner/documents/signals.py>) | 清理正文字符，识别关键词和正则信号；用于诊断字段，不承担 Article 初筛。 |

### src/comproscanner/documents/config

通用文献格式、服务地址和路径约定。

| 文件 | 具体用途 |
|---|---|
| [__init__.py](<F:/Python_Project/ComProScanner/src/comproscanner/documents/config/__init__.py>) | 导出文献配置类，并用 ArticlePaths 约定解析器中间 CSV 的目录位置。 |
| [article_keywords.py](<F:/Python_Project/ComProScanner/src/comproscanner/documents/config/article_keywords.py>) | 存放通用章节标题、方法等识别词，帮助旧解析器把正文归入章节；不是 Tc 属性抽取词库。 |
| [base_urls.py](<F:/Python_Project/ComProScanner/src/comproscanner/documents/config/base_urls.py>) | 集中保存出版社和文献元数据服务的基础 URL。 |
| [paths.py](<F:/Python_Project/ComProScanner/src/comproscanner/documents/config/paths.py>) | 约定元数据 CSV、处理记录和失败日志位置，并读取 IOP_papers_path 环境变量。 |

### src/comproscanner/documents/ingestion

来源注册、执行计划和多来源 Article 归一化。

| 文件 | 具体用途 |
|---|---|
| [__init__.py](<F:/Python_Project/ComProScanner/src/comproscanner/documents/ingestion/__init__.py>) | 包标识与公共接口导出。所属目录用途：来源注册、执行计划和多来源 Article 归一化。 |
| [normalize.py](<F:/Python_Project/ComProScanner/src/comproscanner/documents/ingestion/normalize.py>) | 将多个处理器 CSV 合并为统一 Article CSV，处理图片清单路径、按 document_id 去重并原子写出。 |
| [process.py](<F:/Python_Project/ComProScanner/src/comproscanner/documents/ingestion/process.py>) | 构建并执行 ArticleProcessingPlan，读取 DOI 文件、检查必要配置，准备出版社元数据输入后调用来源分派。 |
| [registry.py](<F:/Python_Project/ComProScanner/src/comproscanner/documents/ingestion/registry.py>) | 登记本地 PDF、下载 PDF、Elsevier、Springer、Wiley、IOP 等来源及其格式、处理器、联网和凭据要求。 |

### src/comproscanner/documents/literature

文献发现、开放获取下载与原始仓库布局。

| 文件 | 具体用途 |
|---|---|
| [__init__.py](<F:/Python_Project/ComProScanner/src/comproscanner/documents/literature/__init__.py>) | 包标识与公共接口导出。所属目录用途：文献发现、开放获取下载与原始仓库布局。 |
| [io.py](<F:/Python_Project/ComProScanner/src/comproscanner/documents/literature/io.py>) | 文献获取层的基础 IO：规范 DOI、安全文件名，以及 JSON/CSV 的读取和原子写入。 |
| [oa.py](<F:/Python_Project/ComProScanner/src/comproscanner/documents/literature/oa.py>) | 从 Semantic Scholar/OpenAlex 查开放获取位置；下载后验证 PDF、计算哈希并避免重复内容。 |
| [scopus.py](<F:/Python_Project/ComProScanner/src/comproscanner/documents/literature/scopus.py>) | 向 Scopus 检索论文元数据并规范返回项；只做文献发现，不提取材料属性。 |
| [storage.py](<F:/Python_Project/ComProScanner/src/comproscanner/documents/literature/storage.py>) | 定义原始文献仓库布局：manual、按来源划分的 downloaded、normalized 和 quarantine 目录。 |

### src/comproscanner/documents/publishers

五种处理器实现，分别适配 Elsevier、Springer、IOP、Wiley 和本地 PDF。

| 文件 | 具体用途 |
|---|---|
| [__init__.py](<F:/Python_Project/ComProScanner/src/comproscanner/documents/publishers/__init__.py>) | 包标识与公共接口导出。所属目录用途：五种处理器实现，分别适配 Elsevier、Springer、IOP、Wiley 和本地 PDF。 |
| [elsevier_processor.py](<F:/Python_Project/ComProScanner/src/comproscanner/documents/publishers/elsevier_processor.py>) | 调用 Elsevier 内容接口，解析原生 XML 的正文、章节、表格和图片，保留原 XML并写 Article 中间 CSV。 |
| [iop_processor.py](<F:/Python_Project/ComProScanner/src/comproscanner/documents/publishers/iop_processor.py>) | 读取本地 IOP JATS XML，调用工作副本整理，解析正文和表格；图片优先读取本地，可按配置尝试 IOP CDN。 |
| [pdfs_processor.py](<F:/Python_Project/ComProScanner/src/comproscanner/documents/publishers/pdfs_processor.py>) | 遍历本地 PDF，识别 DOI/本地文献 ID、查询可用元数据、记录哈希和处理状态，调用 Docling 生成 Article。 |
| [springer_processor.py](<F:/Python_Project/ComProScanner/src/comproscanner/documents/publishers/springer_processor.py>) | 访问 Springer JATS 来源，处理 XML、正文、表格和图片，保存原始响应并写 Article 中间 CSV。 |
| [wiley_processor.py](<F:/Python_Project/ComProScanner/src/comproscanner/documents/publishers/wiley_processor.py>) | 通过 Wiley TDM 获取 PDF，交给同一个 Docling 解析组件，再写 Article 中间 CSV。 |

### src/comproscanner/documents/schemas

统一 Article 数据契约与校验。

| 文件 | 具体用途 |
|---|---|
| [__init__.py](<F:/Python_Project/ComProScanner/src/comproscanner/documents/schemas/__init__.py>) | 包标识与公共接口导出。所属目录用途：统一 Article 数据契约与校验。 |
| [article_csv.py](<F:/Python_Project/ComProScanner/src/comproscanner/documents/schemas/article_csv.py>) | 定义统一 Article 列、默认值和校验；把历史字段及额外论文元数据转换到正式契约。 |

### src/comproscanner/evidence

第二模块：统一正文切分与可追溯证据准备。

| 文件 | 具体用途 |
|---|---|
| [__init__.py](<F:/Python_Project/ComProScanner/src/comproscanner/evidence/__init__.py>) | 包标识与公共接口导出。所属目录用途：第二模块：统一正文切分与可追溯证据准备。 |
| [figure_manifest.py](<F:/Python_Project/ComProScanner/src/comproscanner/evidence/figure_manifest.py>) | 读取图片 manifest，将图片路径、标题、邻近文字、页码组装为 FigureUnit，并兼容历史相对路径。 |
| [models.py](<F:/Python_Project/ComProScanner/src/comproscanner/evidence/models.py>) | 定义 Evidence、EvidenceType 和 RetrievalMethod：证据 ID、文献、原文、位置、来源类型及检索过程。 |
| [preparation.py](<F:/Python_Project/ComProScanner/src/comproscanner/evidence/preparation.py>) | 统一准备器：从 Article 正文切分、标记参考文献区，再按开关运行文本、表格、图片和公式选择器。 |
| [registry.py](<F:/Python_Project/ComProScanner/src/comproscanner/evidence/registry.py>) | Evidence 工具的注册和按名创建；用于选择工具而不是写死一套全部启用的流程。 |
| [source_units.py](<F:/Python_Project/ComProScanner/src/comproscanner/evidence/source_units.py>) | 把 Article 的表格文本、图片清单和文本块中的显式公式转换为 TableUnit、FigureUnit、EquationUnit；表格保留原文，不保证已经完全结构化行列。 |
| [text.py](<F:/Python_Project/ComProScanner/src/comproscanner/evidence/text.py>) | 把规则和向量检索命中映射到同一 chunk；同一文本块形成一条 Evidence，保留各检索来源。 |
| [vector_store.py](<F:/Python_Project/ComProScanner/src/comproscanner/evidence/vector_store.py>) | TextChunk 与底层 Chroma 管理器之间的适配层：写入规范 chunk，并把检索结果还原为 chunk 命中。 |

### src/comproscanner/evidence/chunking

规则与 RAG 共用的正文分块。

| 文件 | 具体用途 |
|---|---|
| [__init__.py](<F:/Python_Project/ComProScanner/src/comproscanner/evidence/chunking/__init__.py>) | 包标识与公共接口导出。所属目录用途：规则与 RAG 共用的正文分块。 |
| [text_chunker.py](<F:/Python_Project/ComProScanner/src/comproscanner/evidence/chunking/text_chunker.py>) | 唯一正文切分实现：保留段落、章节和位置，控制目标长度、最大长度及重叠，生成稳定的 TextChunk。 |

### src/comproscanner/evidence/providers

五个可选择的 Evidence 工具及统一接口。

| 文件 | 具体用途 |
|---|---|
| [__init__.py](<F:/Python_Project/ComProScanner/src/comproscanner/evidence/providers/__init__.py>) | 包标识与公共接口导出。所属目录用途：五个可选择的 Evidence 工具及统一接口。 |
| [base.py](<F:/Python_Project/ComProScanner/src/comproscanner/evidence/providers/base.py>) | 定义 EvidenceProvider 接口和通用正则匹配函数。 |
| [equation.py](<F:/Python_Project/ComProScanner/src/comproscanner/evidence/providers/equation.py>) | 公式工具：按属性规则选中公式及其上下文，形成公式 Evidence。 |
| [figure.py](<F:/Python_Project/ComProScanner/src/comproscanner/evidence/providers/figure.py>) | 图片工具：根据图题和邻近文字选图，保留图片位置并构造不会跨论文冲突的 Evidence ID；此处不调用视觉模型。 |
| [rule_text.py](<F:/Python_Project/ComProScanner/src/comproscanner/evidence/providers/rule_text.py>) | 候选文本工具：在已有 TextChunk 上按 preset 关键词/正则选择，返回命中记录。 |
| [table.py](<F:/Python_Project/ComProScanner/src/comproscanner/evidence/providers/table.py>) | 表格工具：按规则选择 TableUnit，保留表题、原文或结构化表头/行/注释，输出表格 Evidence。 |
| [vector_text.py](<F:/Python_Project/ComProScanner/src/comproscanner/evidence/providers/vector_text.py>) | RAG 工具：把同一批 TextChunk 建库，执行属性查询，返回向量检索命中及分数。 |

### src/comproscanner/evidence/rag

嵌入模型和持久化向量检索实现。

| 文件 | 具体用途 |
|---|---|
| [__init__.py](<F:/Python_Project/ComProScanner/src/comproscanner/evidence/rag/__init__.py>) | 包标识与公共接口导出。所属目录用途：嵌入模型和持久化向量检索实现。 |
| [config.py](<F:/Python_Project/ComProScanner/src/comproscanner/evidence/rag/config.py>) | 承载从 preset 解析出的嵌入模型、数据库目录、长度和检索数量设置。 |
| [embeddings.py](<F:/Python_Project/ComProScanner/src/comproscanner/evidence/rag/embeddings.py>) | 把文本转换成向量；支持 Hugging Face、Sentence Transformers 和 OpenAI 适配。当前 PhysBERT 配置在本地执行。 |
| [store.py](<F:/Python_Project/ComProScanner/src/comproscanner/evidence/rag/store.py>) | 操作 Chroma 持久化索引：规范 chunk 建库、相似度检索、存在性检查和资源释放；不再次切分正文。 |

### src/comproscanner/extraction

第三模块：每条 Evidence 的识别、视觉解读和属性抽取。

| 文件 | 具体用途 |
|---|---|
| [__init__.py](<F:/Python_Project/ComProScanner/src/comproscanner/extraction/__init__.py>) | 包标识与公共接口导出。所属目录用途：第三模块：每条 Evidence 的识别、视觉解读和属性抽取。 |
| [evidence_flow.py](<F:/Python_Project/ComProScanner/src/comproscanner/extraction/evidence_flow.py>) | 每条 Evidence 的模型编排：文本/表格/公式先 identifier 再 extractor；图片先 vision 再 extractor，逐条隔离错误。 |
| [litellm_adapters.py](<F:/Python_Project/ComProScanner/src/comproscanner/extraction/litellm_adapters.py>) | 实际模型适配层：组装 preset 提示词、读取环境密钥、调用 LiteLLM、解析 JSON；图片被编码后发送给视觉模型。 |

### src/comproscanner/presets

属性知识与模型配置入口；新增属性主要修改这里。

| 文件 | 具体用途 |
|---|---|
| [__init__.py](<F:/Python_Project/ComProScanner/src/comproscanner/presets/__init__.py>) | 包标识与公共接口导出。所属目录用途：属性知识与模型配置入口；新增属性主要修改这里。 |
| [_shared.py](<F:/Python_Project/ComProScanner/src/comproscanner/presets/_shared.py>) | 各 preset 可覆盖的默认配置：identifier/extractor/vision 消息模板、模型选择、Fact 输出字段和本地 RAG 设置。 |
| [band_gap.py](<F:/Python_Project/ComProScanner/src/comproscanner/presets/band_gap.py>) | 带隙属性配置示例：明确材料-能隙绑定，区分光学与计算方法，要求 eV 单位及相关条件；实际论文准确率尚未评测。 |
| [base.py](<F:/Python_Project/ComProScanner/src/comproscanner/presets/base.py>) | PropertyExtractionPreset 契约与校验；约定关键词、工具、查询、提示词、模型、字段、条件和评估映射。 |
| [curie_temperature.py](<F:/Python_Project/ComProScanner/src/comproscanner/presets/curie_temperature.py>) | Tc 专属知识配置：关键词、高召回候选规则、RAG 查询、科学提示词、模型、单位和历史 Gold 字段映射；保留已验证消息内容。 |
| [registry.py](<F:/Python_Project/ComProScanner/src/comproscanner/presets/registry.py>) | 按文件名发现并加载 preset，同时支持显式注册；新增常规属性文件不必修改主流程。 |

### src/comproscanner/results

第四模块：材料恢复、事实合并、最终表格、Review、Gold 和评估。

| 文件 | 具体用途 |
|---|---|
| [__init__.py](<F:/Python_Project/ComProScanner/src/comproscanner/results/__init__.py>) | 包标识与公共接口导出。所属目录用途：第四模块：材料恢复、事实合并、最终表格、Review、Gold 和评估。 |
| [export.py](<F:/Python_Project/ComProScanner/src/comproscanner/results/export.py>) | 把最终 Facts 与 Article 论文信息关联，输出 predictions.csv 和 XLSX 的 facts、papers 工作表。 |
| [gold.py](<F:/Python_Project/ComProScanner/src/comproscanner/results/gold.py>) | 读取人工完成的 Review，只把 ACCEPT/MODIFY 行写到新的 Gold 文件，保留证据关联并拒绝覆盖已有 Gold。 |
| [review.py](<F:/Python_Project/ComProScanner/src/comproscanner/results/review.py>) | 生成 review.xlsx：每条事实附原始 Evidence、图片路径、材料恢复问题及 ACCEPT/REJECT/MODIFY 人工决定列。 |
| [run_store.py](<F:/Python_Project/ComProScanner/src/comproscanner/results/run_store.py>) | 规定一次 run 的目录，原子保存 JSON和阶段状态，阻止写到运行目录外或覆写 Gold。 |

### src/comproscanner/results/evaluation

显式输入映射和严格事实评分。

| 文件 | 具体用途 |
|---|---|
| [__init__.py](<F:/Python_Project/ComProScanner/src/comproscanner/results/evaluation/__init__.py>) | 包标识与公共接口导出。所属目录用途：显式输入映射和严格事实评分。 |
| [inputs.py](<F:/Python_Project/ComProScanner/src/comproscanner/results/evaluation/inputs.py>) | 正式评估输入适配器：根据 preset 映射历史字段/属性别名，根据显式 paper_map 对齐论文标识，拒绝冲突。 |
| [strict.py](<F:/Python_Project/ComProScanner/src/comproscanner/results/evaluation/strict.py>) | 严格多重集合匹配，计算 TP、FP、FN、Precision、Recall、F1，并返回具体 FP/FN；不自动推断材料等价或换算单位。 |

### src/comproscanner/results/facts

事实数据模型、材料解析和保守合并逻辑。

| 文件 | 具体用途 |
|---|---|
| [__init__.py](<F:/Python_Project/ComProScanner/src/comproscanner/results/facts/__init__.py>) | 包标识与公共接口导出。所属目录用途：事实数据模型、材料解析和保守合并逻辑。 |
| [materials.py](<F:/Python_Project/ComProScanner/src/comproscanner/results/facts/materials.py>) | 现有本地材料工具：化学式规范化、变量赋值代入、利用同文证据和正文恢复缩写及完整配方。 |
| [merger.py](<F:/Python_Project/ComProScanner/src/comproscanner/results/facts/merger.py>) | 保守合并表示等价的事实，保留所有 Evidence 和原始材料写法；区分条件、限定及扩展属性。 |
| [models.py](<F:/Python_Project/ComProScanner/src/comproscanner/results/facts/models.py>) | 定义 FactValue 和 Fact，保存材料原名、恢复名、属性值、单位、限定、条件、证据 ID 与扩展字段。 |
| [processors.py](<F:/Python_Project/ComProScanner/src/comproscanner/results/facts/processors.py>) | FactProcessor 统一调用材料规范化并检查单位/条件，记录问题；另保留可选外部材料解析 API 适配器。 |

## 正式测试：逐文件


### tests

正式回归测试及其输入样本；默认离线执行。

| 文件 | 具体用途 |
|---|---|
| [conftest.py](<F:/Python_Project/ComProScanner/tests/conftest.py>) | 设置离线环境、禁止普通测试建立网络连接、为每个测试隔离工作目录和输出。 |
| [test_canonical_pipeline_smoke.py](<F:/Python_Project/ComProScanner/tests/test_canonical_pipeline_smoke.py>) | 验证统一 Article→Evidence→抽取→结果的基本链路。 |
| [test_cleanup_contract.py](<F:/Python_Project/ComProScanner/tests/test_cleanup_contract.py>) | 冻结完整模型消息，检查旧依赖隔离、扩展字段和论文元数据保留、preset 控制以及 Review→Gold。 |
| [test_preset_pipeline.py](<F:/Python_Project/ComProScanner/tests/test_preset_pipeline.py>) | 验证不同属性共用通用流水线，属性差异由 preset 提供。 |

### tests/cli

验证命令入口、执行开关、阶段衔接和续跑。

| 文件 | 具体用途 |
|---|---|
| [test_commands.py](<F:/Python_Project/ComProScanner/tests/cli/test_commands.py>) | 验证 CLI 基础子命令及产物。 |
| [test_extract_guard.py](<F:/Python_Project/ComProScanner/tests/cli/test_extract_guard.py>) | 验证抽取必须满足执行条件，防止意外模型调用或覆盖。 |
| [test_process_articles.py](<F:/Python_Project/ComProScanner/tests/cli/test_process_articles.py>) | 验证文献命令的计划模式、执行开关和输入传递。 |
| [test_run.py](<F:/Python_Project/ComProScanner/tests/cli/test_run.py>) | 验证端到端阶段顺序、恢复运行、输入变化检查及错误状态。 |

### tests/documents

验证文献来源、资产保留和 Article 转换。

| 文件 | 具体用途 |
|---|---|
| [test_source_boundaries.py](<F:/Python_Project/ComProScanner/tests/documents/test_source_boundaries.py>) | 验证陌生章节保留、Tc 关键词字典、IOP 原件保护与无元数据输入、DOI 路由和 CSV 失败上报。 |

### tests/documents/ingestion

来源注册、文献处理计划及 CSV 合并测试。

| 文件 | 具体用途 |
|---|---|
| [test_normalize.py](<F:/Python_Project/ComProScanner/tests/documents/ingestion/test_normalize.py>) | 验证多来源 CSV 归一化、标识去重和图片路径处理。 |
| [test_process.py](<F:/Python_Project/ComProScanner/tests/documents/ingestion/test_process.py>) | 验证文献处理计划、来源参数和执行调用。 |
| [test_source_registry.py](<F:/Python_Project/ComProScanner/tests/documents/ingestion/test_source_registry.py>) | 验证来源定义、格式、联网与凭据要求。 |

### tests/documents/literature

文献搜索、下载验证及仓库布局测试。

| 文件 | 具体用途 |
|---|---|
| [test_oa.py](<F:/Python_Project/ComProScanner/tests/documents/literature/test_oa.py>) | 验证开放获取候选解析、PDF 内容验证、哈希及下载行为。 |
| [test_scopus.py](<F:/Python_Project/ComProScanner/tests/documents/literature/test_scopus.py>) | 验证 Scopus 检索条件与元数据规范化。 |
| [test_storage.py](<F:/Python_Project/ComProScanner/tests/documents/literature/test_storage.py>) | 验证原始文献仓库的 manual/downloaded 等目录布局。 |

### tests/documents/publishers

各出版社及本地 PDF 适配器的离线测试。

| 文件 | 具体用途 |
|---|---|
| [test_elsevier_processor.py](<F:/Python_Project/ComProScanner/tests/documents/publishers/test_elsevier_processor.py>) | 验证 Elsevier 请求与 XML 解析、元数据、表格和异常重试；用替代响应执行。 |
| [test_iop_processor.py](<F:/Python_Project/ComProScanner/tests/documents/publishers/test_iop_processor.py>) | 当前此文件主要测试 PrepareIOPFiles：XML/ZIP 整理、DOI 和异常处理；完整入口边界另在 test_source_boundaries.py。 |
| [test_pdfs_processor.py](<F:/Python_Project/ComProScanner/tests/documents/publishers/test_pdfs_processor.py>) | 验证本地 PDF 标识、解析、元数据回退、失败记录和 CSV 输出。 |
| [test_springer_processor.py](<F:/Python_Project/ComProScanner/tests/documents/publishers/test_springer_processor.py>) | 验证 Springer 请求、JATS 解析和中间结果写出。 |
| [test_wiley_processor.py](<F:/Python_Project/ComProScanner/tests/documents/publishers/test_wiley_processor.py>) | 验证 Wiley PDF 获取、解析和失败处理。 |

### tests/documents/schemas

统一 Article 格式测试。

| 文件 | 具体用途 |
|---|---|
| [test_article_csv.py](<F:/Python_Project/ComProScanner/tests/documents/schemas/test_article_csv.py>) | 验证 Article 必需列、缺失值和历史 CSV 适配。 |

### tests/evidence

证据身份、工具行为和来源追溯测试。

| 文件 | 具体用途 |
|---|---|
| [test_figure_identity.py](<F:/Python_Project/ComProScanner/tests/evidence/test_figure_identity.py>) | 验证不同论文/图号不会产生冲突的图片 Evidence 身份。 |

### tests/evidence/chunking

统一正文切分的测试。

| 文件 | 具体用途 |
|---|---|
| [test_text_chunker.py](<F:/Python_Project/ComProScanner/tests/evidence/chunking/test_text_chunker.py>) | 验证段落/章节切分、超长段落、重叠和稳定 ID。 |

### tests/evidence/preparation

从 Article 准备完整 Evidence 集的测试。

| 文件 | 具体用途 |
|---|---|
| [test_evidence_preparation.py](<F:/Python_Project/ComProScanner/tests/evidence/preparation/test_evidence_preparation.py>) | 验证统一正文及表格、图片、公式的准备过程与工具开关。 |

### tests/evidence/providers

规则/RAG与非文本 Evidence 工具的测试。

| 文件 | 具体用途 |
|---|---|
| [test_figure_manifest.py](<F:/Python_Project/ComProScanner/tests/evidence/providers/test_figure_manifest.py>) | 验证图片清单加载、路径、图题和位置元数据。 |
| [test_non_text_evidence.py](<F:/Python_Project/ComProScanner/tests/evidence/providers/test_non_text_evidence.py>) | 验证表格、图片和公式 Evidence 的选择与原始信息保留。 |
| [test_registry.py](<F:/Python_Project/ComProScanner/tests/evidence/providers/test_registry.py>) | 验证 Evidence 工具注册与选择。 |
| [test_source_units.py](<F:/Python_Project/ComProScanner/tests/evidence/providers/test_source_units.py>) | 验证表格文本、显式公式和图片清单转换为来源单元。 |
| [test_text_evidence.py](<F:/Python_Project/ComProScanner/tests/evidence/providers/test_text_evidence.py>) | 验证规则与向量结果汇合，同一文本块保留多个检索来源。 |
| [test_vector_store.py](<F:/Python_Project/ComProScanner/tests/evidence/providers/test_vector_store.py>) | 验证规范 chunk 与向量数据库适配器的建库、检索和返回映射。 |

### tests/extraction

逐条模型编排、消息构造和返回解析测试。

| 文件 | 具体用途 |
|---|---|
| [test_evidence_flow.py](<F:/Python_Project/ComProScanner/tests/extraction/test_evidence_flow.py>) | 验证每条 Evidence 独立执行、拒绝分支、图片路线及错误隔离。 |
| [test_litellm_adapters.py](<F:/Python_Project/ComProScanner/tests/extraction/test_litellm_adapters.py>) | 验证模型请求消息、返回 JSON 解析和图片输入格式。 |

### tests/fixtures

测试固定输入：出版社 XML 与冻结的模型消息，不是生产 Gold。

| 文件 | 具体用途 |
|---|---|
| [elsevier_test.xml](<F:/Python_Project/ComProScanner/tests/fixtures/elsevier_test.xml>) | 对应出版社的固定 XML 响应样本，供离线解析测试。 |
| [springer_test.xml](<F:/Python_Project/ComProScanner/tests/fixtures/springer_test.xml>) | 对应出版社的固定 XML 响应样本，供离线解析测试。 |
| [tc_wire_messages.json](<F:/Python_Project/ComProScanner/tests/fixtures/tc_wire_messages.json>) | 冻结的 7 组完整 Tc 模型请求消息；回归测试与其逐项比较，不是模型响应或 Gold。 |

### tests/presets

属性扩展、配置校验和 Tc 冻结基线测试。

| 文件 | 具体用途 |
|---|---|
| [test_registry.py](<F:/Python_Project/ComProScanner/tests/presets/test_registry.py>) | 验证 preset 自动发现、独立属性与配置校验。 |
| [test_tc_baseline.py](<F:/Python_Project/ComProScanner/tests/presets/test_tc_baseline.py>) | 使用固定 SHA-256 检查 Tc 的关键词、科学提示词、查询和工具策略未变化。 |

### tests/results/evaluation

严格评分与历史输入适配测试。

| 文件 | 具体用途 |
|---|---|
| [test_strict.py](<F:/Python_Project/ComProScanner/tests/results/evaluation/test_strict.py>) | 验证严格 TP/FP/FN/F1、多重项、条件/单位差异和正式通用适配器对历史 Tc 输入的处理。 |

### tests/results/export

运行存储和 Review 导出测试。

| 文件 | 具体用途 |
|---|---|
| [test_review.py](<F:/Python_Project/ComProScanner/tests/results/export/test_review.py>) | 验证 Review 的原文 Evidence、材料信息和 XLSX 内容。 |
| [test_run_store.py](<F:/Python_Project/ComProScanner/tests/results/export/test_run_store.py>) | 验证运行目录、原子输出与禁止越界/写 Gold。 |

### tests/results/facts

材料名称恢复、变量和合并规则的测试。

| 文件 | 具体用途 |
|---|---|
| [test_article_materials.py](<F:/Python_Project/ComProScanner/tests/results/facts/test_article_materials.py>) | 验证利用同文上下文恢复缩写、材料母配方和变量，防止跨样品误用。 |
| [test_fact_merger.py](<F:/Python_Project/ComProScanner/tests/results/facts/test_fact_merger.py>) | 验证保守合并、证据联合以及不同条件/限定的事实分离。 |
| [test_processors.py](<F:/Python_Project/ComProScanner/tests/results/facts/test_processors.py>) | 验证材料处理器、规范化失败标记和单位/条件检查。 |

## 文档与自动化


### docs

面向使用、维护和验收的项目说明。

| 文件 | 具体用途 |
|---|---|
| [architecture.md](<F:/Python_Project/ComProScanner/docs/architecture.md>) | 解释四模块、数据契约、证据路线和扩展边界。 |
| [cleanup.md](<F:/Python_Project/ComProScanner/docs/cleanup.md>) | 记录清理/收尾内容、回归证据、数据保留位置和未完成的生产验证边界。 |
| [file-guide.md](<F:/Python_Project/ComProScanner/docs/file-guide.md>) | 本次生成的阅读版：逐一说明正式代码、测试、参考文件及主要目录。 |
| [file-inventory.html](<F:/Python_Project/ComProScanner/docs/file-inventory.html>) | 本次生成的完整静态目录清单：可搜索每个文件/文件夹、用途、结构依据与状态。 |
| [presets.md](<F:/Python_Project/ComProScanner/docs/presets.md>) | 说明每个 preset 字段、属性配置方式与新增属性示例。 |
| [usage.md](<F:/Python_Project/ComProScanner/docs/usage.md>) | 提供输入、分阶段执行、材料恢复、Review→Gold 和评估命令。 |

## GitHub 配置


### .github/ISSUE_TEMPLATE

提交缺陷、文档问题、功能建议或一般问题时使用的表单模板。

| 文件 | 具体用途 |
|---|---|
| [bug_report.md](<F:/Python_Project/ComProScanner/.github/ISSUE_TEMPLATE/bug_report.md>) | 缺陷反馈模板。 |
| [documentation.md](<F:/Python_Project/ComProScanner/.github/ISSUE_TEMPLATE/documentation.md>) | 文档问题反馈模板。 |
| [feature_request.md](<F:/Python_Project/ComProScanner/.github/ISSUE_TEMPLATE/feature_request.md>) | 功能建议模板。 |
| [question.md](<F:/Python_Project/ComProScanner/.github/ISSUE_TEMPLATE/question.md>) | 一般问题模板。 |

### .github/workflows

CI 自动执行流程定义。

| 文件 | 具体用途 |
|---|---|
| [ci.yml](<F:/Python_Project/ComProScanner/.github/workflows/ci.yml>) | GitHub CI：在 Python 3.12/3.13 安装正式依赖、跑离线测试并构建 wheel。 |

## 安装元数据


### src/comproscanner.egg-info

pip/setuptools 自动生成的安装元数据，不是另一套业务代码。

| 文件 | 具体用途 |
|---|---|
| [dependency_links.txt](<F:/Python_Project/ComProScanner/src/comproscanner.egg-info/dependency_links.txt>) | 安装工具的依赖链接元数据，当前通常为空。 |
| [entry_points.txt](<F:/Python_Project/ComProScanner/src/comproscanner.egg-info/entry_points.txt>) | 安装工具生成的命令行入口注册。 |
| [PKG-INFO](<F:/Python_Project/ComProScanner/src/comproscanner.egg-info/PKG-INFO>) | 构建生成的包名称、版本、依赖和介绍等元数据。 |
| [requires.txt](<F:/Python_Project/ComProScanner/src/comproscanner.egg-info/requires.txt>) | 安装工具生成的依赖与可选依赖清单。 |
| [SOURCES.txt](<F:/Python_Project/ComProScanner/src/comproscanner.egg-info/SOURCES.txt>) | setuptools 收集的发行包文件列表。 |
| [top_level.txt](<F:/Python_Project/ComProScanner/src/comproscanner.egg-info/top_level.txt>) | 发行包提供的顶层 Python 包名。 |

## 历史参考：逐文件


### reference

不参与当前正式运行的历史实现、实验归档和一次性迁移脚本。

| 文件 | 具体用途 |
|---|---|
| [documentation_before_cleanup.zip](<F:/Python_Project/ComProScanner/reference/documentation_before_cleanup.zip>) | 清理前文档站点、图片与自动发布配置的归档。 |
| [history.zip](<F:/Python_Project/ComProScanner/reference/history.zip>) | 归档的旧实验、示例、临时脚本和开发产物；压缩包作为一个物理文件登记，包内成员不在本次展开。 |
| [README.md](<F:/Python_Project/ComProScanner/reference/README.md>) | 说明参考代码不参与当前运行、安装和正式测试，以及归档和恢复位置。 |

### reference/legacy

未压缩的停用源码、配置和历史测试。

| 文件 | 具体用途 |
|---|---|
| [paper-dependencies.txt](<F:/Python_Project/ComProScanner/reference/legacy/paper-dependencies.txt>) | 旧论文复现实验依赖清单，不是正式包安装依赖入口。 |

### reference/legacy/comproscanner

旧包布局下保留的 CrewAI、数据库、可视化等实现，仅供参考。

| 文件 | 具体用途 |
|---|---|
| [__init__.py](<F:/Python_Project/ComProScanner/reference/legacy/comproscanner/__init__.py>) | 旧包/子包入口与导出，仅供了解历史模块结构；当前正式包不导入这里。 |
| [comproscanner.py](<F:/Python_Project/ComProScanner/reference/legacy/comproscanner/comproscanner.py>) | 旧的一体化 ComProScanner 门面，曾连接检索、出版社、CrewAI、清洗、评估和数据库。 |
| [data_visualizer.py](<F:/Python_Project/ComProScanner/reference/legacy/comproscanner/data_visualizer.py>) | 旧数据分布图和知识图谱的对外包装函数。 |
| [eval_visualizer.py](<F:/Python_Project/ComProScanner/reference/legacy/comproscanner/eval_visualizer.py>) | 旧评估柱图、雷达图、热图、混淆矩阵等绘图包装函数。 |

### reference/legacy/comproscanner/extract_flow

旧流程的 extract_flow 子模块/历史测试目录，仅保留参考，不被正式包加载。

| 文件 | 具体用途 |
|---|---|
| [__init__.py](<F:/Python_Project/ComProScanner/reference/legacy/comproscanner/extract_flow/__init__.py>) | 旧包/子包入口与导出，仅供了解历史模块结构；当前正式包不导入这里。 |
| [main_extraction_flow.py](<F:/Python_Project/ComProScanner/reference/legacy/comproscanner/extract_flow/main_extraction_flow.py>) | 旧 CrewAI Flow，组织材料识别、组成属性抽取/格式化和合成步骤抽取。 |

### reference/legacy/comproscanner/extract_flow/crews/composition_crew/composition_extraction_crew

旧流程的 composition_extraction_crew 子模块/历史测试目录，仅保留参考，不被正式包加载。

| 文件 | 具体用途 |
|---|---|
| [composition_extraction_crew.py](<F:/Python_Project/ComProScanner/reference/legacy/comproscanner/extract_flow/crews/composition_crew/composition_extraction_crew/composition_extraction_crew.py>) | 旧组成-属性抽取 Crew 和输出模型。 |

### reference/legacy/comproscanner/extract_flow/crews/composition_crew/composition_extraction_crew/config

对应旧 Crew 的 agent 角色和任务 YAML 配置。

| 文件 | 具体用途 |
|---|---|
| [agents.yaml](<F:/Python_Project/ComProScanner/reference/legacy/comproscanner/extract_flow/crews/composition_crew/composition_extraction_crew/config/agents.yaml>) | 上级旧 Crew 的 agent 角色、目标和背景提示词配置。 |
| [tasks.yaml](<F:/Python_Project/ComProScanner/reference/legacy/comproscanner/extract_flow/crews/composition_crew/composition_extraction_crew/config/tasks.yaml>) | 上级旧 Crew 的任务说明、输出要求和 agent 分工配置。 |

### reference/legacy/comproscanner/extract_flow/crews/composition_crew/composition_format_crew

旧流程的 composition_format_crew 子模块/历史测试目录，仅保留参考，不被正式包加载。

| 文件 | 具体用途 |
|---|---|
| [composition_format_crew.py](<F:/Python_Project/ComProScanner/reference/legacy/comproscanner/extract_flow/crews/composition_crew/composition_format_crew/composition_format_crew.py>) | 旧组成-属性格式化 Crew 和输出模型。 |

### reference/legacy/comproscanner/extract_flow/crews/composition_crew/composition_format_crew/config

对应旧 Crew 的 agent 角色和任务 YAML 配置。

| 文件 | 具体用途 |
|---|---|
| [agents.yaml](<F:/Python_Project/ComProScanner/reference/legacy/comproscanner/extract_flow/crews/composition_crew/composition_format_crew/config/agents.yaml>) | 上级旧 Crew 的 agent 角色、目标和背景提示词配置。 |
| [tasks.yaml](<F:/Python_Project/ComProScanner/reference/legacy/comproscanner/extract_flow/crews/composition_crew/composition_format_crew/config/tasks.yaml>) | 上级旧 Crew 的任务说明、输出要求和 agent 分工配置。 |

### reference/legacy/comproscanner/extract_flow/crews/materials_data_identifier_crew

旧流程的 materials_data_identifier_crew 子模块/历史测试目录，仅保留参考，不被正式包加载。

| 文件 | 具体用途 |
|---|---|
| [materials_data_identifier_crew.py](<F:/Python_Project/ComProScanner/reference/legacy/comproscanner/extract_flow/crews/materials_data_identifier_crew/materials_data_identifier_crew.py>) | 旧 yes/no 文献材料数据识别 Crew。 |

### reference/legacy/comproscanner/extract_flow/crews/materials_data_identifier_crew/config

对应旧 Crew 的 agent 角色和任务 YAML 配置。

| 文件 | 具体用途 |
|---|---|
| [agents.yaml](<F:/Python_Project/ComProScanner/reference/legacy/comproscanner/extract_flow/crews/materials_data_identifier_crew/config/agents.yaml>) | 上级旧 Crew 的 agent 角色、目标和背景提示词配置。 |
| [tasks.yaml](<F:/Python_Project/ComProScanner/reference/legacy/comproscanner/extract_flow/crews/materials_data_identifier_crew/config/tasks.yaml>) | 上级旧 Crew 的任务说明、输出要求和 agent 分工配置。 |

### reference/legacy/comproscanner/extract_flow/crews/synthesis_crew/synthesis_extraction_crew

旧流程的 synthesis_extraction_crew 子模块/历史测试目录，仅保留参考，不被正式包加载。

| 文件 | 具体用途 |
|---|---|
| [synthesis_extraction_crew.py](<F:/Python_Project/ComProScanner/reference/legacy/comproscanner/extract_flow/crews/synthesis_crew/synthesis_extraction_crew/synthesis_extraction_crew.py>) | 旧合成方法/步骤抽取 Crew。 |

### reference/legacy/comproscanner/extract_flow/crews/synthesis_crew/synthesis_extraction_crew/config

对应旧 Crew 的 agent 角色和任务 YAML 配置。

| 文件 | 具体用途 |
|---|---|
| [agents.yaml](<F:/Python_Project/ComProScanner/reference/legacy/comproscanner/extract_flow/crews/synthesis_crew/synthesis_extraction_crew/config/agents.yaml>) | 上级旧 Crew 的 agent 角色、目标和背景提示词配置。 |
| [tasks.yaml](<F:/Python_Project/ComProScanner/reference/legacy/comproscanner/extract_flow/crews/synthesis_crew/synthesis_extraction_crew/config/tasks.yaml>) | 上级旧 Crew 的任务说明、输出要求和 agent 分工配置。 |

### reference/legacy/comproscanner/extract_flow/crews/synthesis_crew/synthesis_format_crew

旧流程的 synthesis_format_crew 子模块/历史测试目录，仅保留参考，不被正式包加载。

| 文件 | 具体用途 |
|---|---|
| [synthesis_format_crew.py](<F:/Python_Project/ComProScanner/reference/legacy/comproscanner/extract_flow/crews/synthesis_crew/synthesis_format_crew/synthesis_format_crew.py>) | 旧合成数据格式化 Crew。 |

### reference/legacy/comproscanner/extract_flow/crews/synthesis_crew/synthesis_format_crew/config

对应旧 Crew 的 agent 角色和任务 YAML 配置。

| 文件 | 具体用途 |
|---|---|
| [agents.yaml](<F:/Python_Project/ComProScanner/reference/legacy/comproscanner/extract_flow/crews/synthesis_crew/synthesis_format_crew/config/agents.yaml>) | 上级旧 Crew 的 agent 角色、目标和背景提示词配置。 |
| [tasks.yaml](<F:/Python_Project/ComProScanner/reference/legacy/comproscanner/extract_flow/crews/synthesis_crew/synthesis_format_crew/config/tasks.yaml>) | 上级旧 Crew 的任务说明、输出要求和 agent 分工配置。 |

### reference/legacy/comproscanner/extract_flow/tools

旧流程的 tools 子模块/历史测试目录，仅保留参考，不被正式包加载。

| 文件 | 具体用途 |
|---|---|
| [__init__.py](<F:/Python_Project/ComProScanner/reference/legacy/comproscanner/extract_flow/tools/__init__.py>) | 旧包/子包入口与导出，仅供了解历史模块结构；当前正式包不导入这里。 |
| [equation_tool.py](<F:/Python_Project/ComProScanner/reference/legacy/comproscanner/extract_flow/tools/equation_tool.py>) | 旧 agent 使用的公式/晶体结构图片辅助工具及模型选择实现。 |
| [graph_extractor_tool.py](<F:/Python_Project/ComProScanner/reference/legacy/comproscanner/extract_flow/tools/graph_extractor_tool.py>) | 旧从论文图像抽取数据的 agent 工具。 |
| [material_parser_tool.py](<F:/Python_Project/ComProScanner/reference/legacy/comproscanner/extract_flow/tools/material_parser_tool.py>) | 旧外部材料解析工具，处理配方、变量和接口返回。 |
| [rag_tool.py](<F:/Python_Project/ComProScanner/reference/legacy/comproscanner/extract_flow/tools/rag_tool.py>) | 旧 agent 的 RAG 工具，把向量检索文段交给模型组织答案。 |

### reference/legacy/comproscanner/metadata_extractor

旧流程的 metadata_extractor 子模块/历史测试目录，仅保留参考，不被正式包加载。

| 文件 | 具体用途 |
|---|---|
| [__init__.py](<F:/Python_Project/ComProScanner/reference/legacy/comproscanner/metadata_extractor/__init__.py>) | 旧包/子包入口与导出，仅供了解历史模块结构；当前正式包不导入这里。 |
| [fetch_metadata.py](<F:/Python_Project/ComProScanner/reference/legacy/comproscanner/metadata_extractor/fetch_metadata.py>) | 旧文献元数据获取实现。 |
| [filter_metadata.py](<F:/Python_Project/ComProScanner/reference/legacy/comproscanner/metadata_extractor/filter_metadata.py>) | 旧元数据去重、无效记录清理及出版社补全实现。 |

### reference/legacy/comproscanner/pipeline

旧流程的 pipeline 子模块/历史测试目录，仅保留参考，不被正式包加载。

| 文件 | 具体用途 |
|---|---|
| [__init__.py](<F:/Python_Project/ComProScanner/reference/legacy/comproscanner/pipeline/__init__.py>) | 旧包/子包入口与导出，仅供了解历史模块结构；当前正式包不导入这里。 |

### reference/legacy/comproscanner/post_processing

旧流程的 post_processing 子模块/历史测试目录，仅保留参考，不被正式包加载。

| 文件 | 具体用途 |
|---|---|
| [__init__.py](<F:/Python_Project/ComProScanner/reference/legacy/comproscanner/post_processing/__init__.py>) | 旧包/子包入口与导出，仅供了解历史模块结构；当前正式包不导入这里。 |
| [data_cleaner.py](<F:/Python_Project/ComProScanner/reference/legacy/comproscanner/post_processing/data_cleaner.py>) | 旧抽取结果清洗步骤集合，包括材料组成处理。 |

### reference/legacy/comproscanner/post_processing/evaluation

旧流程的 evaluation 子模块/历史测试目录，仅保留参考，不被正式包加载。

| 文件 | 具体用途 |
|---|---|
| [__init__.py](<F:/Python_Project/ComProScanner/reference/legacy/comproscanner/post_processing/evaluation/__init__.py>) | 旧包/子包入口与导出，仅供了解历史模块结构；当前正式包不导入这里。 |
| [semantic_evaluator.py](<F:/Python_Project/ComProScanner/reference/legacy/comproscanner/post_processing/evaluation/semantic_evaluator.py>) | 旧语义匹配评估器；与当前严格评分口径不同。 |

### reference/legacy/comproscanner/post_processing/evaluation/eval_flow

旧流程的 eval_flow 子模块/历史测试目录，仅保留参考，不被正式包加载。

| 文件 | 具体用途 |
|---|---|
| [__init__.py](<F:/Python_Project/ComProScanner/reference/legacy/comproscanner/post_processing/evaluation/eval_flow/__init__.py>) | 旧包/子包入口与导出，仅供了解历史模块结构；当前正式包不导入这里。 |
| [eval_flow.py](<F:/Python_Project/ComProScanner/reference/legacy/comproscanner/post_processing/evaluation/eval_flow/eval_flow.py>) | 旧 agentic 评估流程编排。 |

### reference/legacy/comproscanner/post_processing/evaluation/eval_flow/crews/composition_evaluation_crew

旧流程的 composition_evaluation_crew 子模块/历史测试目录，仅保留参考，不被正式包加载。

| 文件 | 具体用途 |
|---|---|
| [composition_evaluation_crew.py](<F:/Python_Project/ComProScanner/reference/legacy/comproscanner/post_processing/evaluation/eval_flow/crews/composition_evaluation_crew/composition_evaluation_crew.py>) | 旧通过模型判定组成-属性匹配的评估 Crew，含数值容差工具。 |

### reference/legacy/comproscanner/post_processing/evaluation/eval_flow/crews/composition_evaluation_crew/config

对应旧 Crew 的 agent 角色和任务 YAML 配置。

| 文件 | 具体用途 |
|---|---|
| [agents.yaml](<F:/Python_Project/ComProScanner/reference/legacy/comproscanner/post_processing/evaluation/eval_flow/crews/composition_evaluation_crew/config/agents.yaml>) | 上级旧 Crew 的 agent 角色、目标和背景提示词配置。 |
| [tasks.yaml](<F:/Python_Project/ComProScanner/reference/legacy/comproscanner/post_processing/evaluation/eval_flow/crews/composition_evaluation_crew/config/tasks.yaml>) | 上级旧 Crew 的任务说明、输出要求和 agent 分工配置。 |

### reference/legacy/comproscanner/post_processing/evaluation/eval_flow/crews/synthesis_evaluation_crew

旧流程的 synthesis_evaluation_crew 子模块/历史测试目录，仅保留参考，不被正式包加载。

| 文件 | 具体用途 |
|---|---|
| [synthesis_evaluation_crew.py](<F:/Python_Project/ComProScanner/reference/legacy/comproscanner/post_processing/evaluation/eval_flow/crews/synthesis_evaluation_crew/synthesis_evaluation_crew.py>) | 旧合成方法、项目和步骤的模型评估 Crew。 |

### reference/legacy/comproscanner/post_processing/evaluation/eval_flow/crews/synthesis_evaluation_crew/config

对应旧 Crew 的 agent 角色和任务 YAML 配置。

| 文件 | 具体用途 |
|---|---|
| [agents.yaml](<F:/Python_Project/ComProScanner/reference/legacy/comproscanner/post_processing/evaluation/eval_flow/crews/synthesis_evaluation_crew/config/agents.yaml>) | 上级旧 Crew 的 agent 角色、目标和背景提示词配置。 |
| [tasks.yaml](<F:/Python_Project/ComProScanner/reference/legacy/comproscanner/post_processing/evaluation/eval_flow/crews/synthesis_evaluation_crew/config/tasks.yaml>) | 上级旧 Crew 的任务说明、输出要求和 agent 分工配置。 |

### reference/legacy/comproscanner/post_processing/visualization

旧流程的 visualization 子模块/历史测试目录，仅保留参考，不被正式包加载。

| 文件 | 具体用途 |
|---|---|
| [__init__.py](<F:/Python_Project/ComProScanner/reference/legacy/comproscanner/post_processing/visualization/__init__.py>) | 旧包/子包入口与导出，仅供了解历史模块结构；当前正式包不导入这里。 |
| [create_knowledge_graph.py](<F:/Python_Project/ComProScanner/reference/legacy/comproscanner/post_processing/visualization/create_knowledge_graph.py>) | 旧知识图谱生成及语义匹配实现，可供以后 Neo4j 等扩展参考。 |
| [data_distribution_visualizers.py](<F:/Python_Project/ComProScanner/reference/legacy/comproscanner/post_processing/visualization/data_distribution_visualizers.py>) | 旧材料家族、前驱体、表征技术等数据分布绘图实现。 |
| [eval_plot_visualizers.py](<F:/Python_Project/ComProScanner/reference/legacy/comproscanner/post_processing/visualization/eval_plot_visualizers.py>) | 旧评估指标图表实现。 |

### reference/legacy/comproscanner/presets

旧流程的 presets 子模块/历史测试目录，仅保留参考，不被正式包加载。

| 文件 | 具体用途 |
|---|---|
| [_legacy_tc.py](<F:/Python_Project/ComProScanner/reference/legacy/comproscanner/presets/_legacy_tc.py>) | 停用的 Tc 专用字段转换器；正式评估现在使用 results/evaluation/inputs.py。 |
| [curie_temperature_before_finish.py](<F:/Python_Project/ComProScanner/reference/legacy/comproscanner/presets/curie_temperature_before_finish.py>) | 收尾前 Tc 配置副本，包含当时未生效的 extraction_kwargs、旧格式化说明和示例。 |

### reference/legacy/comproscanner/utils

旧流程的 utils 子模块/历史测试目录，仅保留参考，不被正式包加载。

| 文件 | 具体用途 |
|---|---|
| [__init__.py](<F:/Python_Project/ComProScanner/reference/legacy/comproscanner/utils/__init__.py>) | 旧包/子包入口与导出，仅供了解历史模块结构；当前正式包不导入这里。 |
| [candidate_context.py](<F:/Python_Project/ComProScanner/reference/legacy/comproscanner/utils/candidate_context.py>) | 旧候选文本与 RAG 上下文合并实现。 |
| [data_preparator.py](<F:/Python_Project/ComProScanner/reference/legacy/comproscanner/utils/data_preparator.py>) | 旧文献章节和材料属性输入准备器。 |
| [database_manager.py](<F:/Python_Project/ComProScanner/reference/legacy/comproscanner/utils/database_manager.py>) | 旧 MySQL、CSV、向量数据库混合管理器。 |
| [get_paper_data.py](<F:/Python_Project/ComProScanner/reference/legacy/comproscanner/utils/get_paper_data.py>) | 旧按 DOI 读取论文数据/元数据的工具。 |
| [save_results.py](<F:/Python_Project/ComProScanner/reference/legacy/comproscanner/utils/save_results.py>) | 旧流程结果保存工具。 |

### reference/legacy/comproscanner/utils/configs

旧流程的 configs 子模块/历史测试目录，仅保留参考，不被正式包加载。

| 文件 | 具体用途 |
|---|---|
| [__init__.py](<F:/Python_Project/ComProScanner/reference/legacy/comproscanner/utils/configs/__init__.py>) | 旧包/子包入口与导出，仅供了解历史模块结构；当前正式包不导入这里。 |
| [custom_dictionary.py](<F:/Python_Project/ComProScanner/reference/legacy/comproscanner/utils/configs/custom_dictionary.py>) | 旧解析/清洗流程使用的自定义词典与常量。 |
| [database_config.py](<F:/Python_Project/ComProScanner/reference/legacy/comproscanner/utils/configs/database_config.py>) | 旧数据库与输出表相关配置。 |
| [llm_config.py](<F:/Python_Project/ComProScanner/reference/legacy/comproscanner/utils/configs/llm_config.py>) | 旧多 agent 流程的模型和提示词配置对象。 |

### reference/legacy/tests

旧流程的测试和样本，未纳入当前默认 pytest；其中还保留历史字节码缓存。

| 文件 | 具体用途 |
|---|---|
| [conftest.py](<F:/Python_Project/ComProScanner/reference/legacy/tests/conftest.py>) | 旧测试的大范围依赖替身和通用夹具；正式测试已使用独立的新 conftest.py。 |
| [test_candidate_context.py](<F:/Python_Project/ComProScanner/reference/legacy/tests/test_candidate_context.py>) | 历史测试：candidate_context；验证对象和用例见定义栏，不参与当前默认测试。 |
| [test_curie_temperature_preset.py](<F:/Python_Project/ComProScanner/reference/legacy/tests/test_curie_temperature_preset.py>) | 历史测试：curie_temperature_preset；验证对象和用例见定义栏，不参与当前默认测试。 |
| [test_extract_flow.py](<F:/Python_Project/ComProScanner/reference/legacy/tests/test_extract_flow.py>) | 历史测试：extract_flow；验证对象和用例见定义栏，不参与当前默认测试。 |
| [test_public_api.py](<F:/Python_Project/ComProScanner/reference/legacy/tests/test_public_api.py>) | 历史测试：public_api；验证对象和用例见定义栏，不参与当前默认测试。 |
| [test_tc_dev_recovery.py](<F:/Python_Project/ComProScanner/reference/legacy/tests/test_tc_dev_recovery.py>) | 历史测试：tc_dev_recovery；验证对象和用例见定义栏，不参与当前默认测试。 |
| [test_tc_high_recall_prefilter.py](<F:/Python_Project/ComProScanner/reference/legacy/tests/test_tc_high_recall_prefilter.py>) | 历史测试：tc_high_recall_prefilter；验证对象和用例见定义栏，不参与当前默认测试。 |
| [test_tc_v2_identifier_recovery.py](<F:/Python_Project/ComProScanner/reference/legacy/tests/test_tc_v2_identifier_recovery.py>) | 历史测试：tc_v2_identifier_recovery；验证对象和用例见定义栏，不参与当前默认测试。 |
| [test_tc_v3_identifier_semantics.py](<F:/Python_Project/ComProScanner/reference/legacy/tests/test_tc_v3_identifier_semantics.py>) | 历史测试：tc_v3_identifier_semantics；验证对象和用例见定义栏，不参与当前默认测试。 |
| [test_tc_v3_prompt_separation.py](<F:/Python_Project/ComProScanner/reference/legacy/tests/test_tc_v3_prompt_separation.py>) | 历史测试：tc_v3_prompt_separation；验证对象和用例见定义栏，不参与当前默认测试。 |

### reference/legacy/tests/test_agent_tools

旧流程的 test_agent_tools 子模块/历史测试目录，仅保留参考，不被正式包加载。

| 文件 | 具体用途 |
|---|---|
| [test_equation_tool.py](<F:/Python_Project/ComProScanner/reference/legacy/tests/test_agent_tools/test_equation_tool.py>) | 历史测试：equation_tool；验证对象和用例见定义栏，不参与当前默认测试。 |
| [test_graph_extractor_tool.py](<F:/Python_Project/ComProScanner/reference/legacy/tests/test_agent_tools/test_graph_extractor_tool.py>) | 历史测试：graph_extractor_tool；验证对象和用例见定义栏，不参与当前默认测试。 |
| [test_material_parser_tool.py](<F:/Python_Project/ComProScanner/reference/legacy/tests/test_agent_tools/test_material_parser_tool.py>) | 历史测试：material_parser_tool；验证对象和用例见定义栏，不参与当前默认测试。 |
| [test_rag_tool.py](<F:/Python_Project/ComProScanner/reference/legacy/tests/test_agent_tools/test_rag_tool.py>) | 历史测试：rag_tool；验证对象和用例见定义栏，不参与当前默认测试。 |

### reference/legacy/tests/test_apis_primary

旧流程的 test_apis_primary 子模块/历史测试目录，仅保留参考，不被正式包加载。

| 文件 | 具体用途 |
|---|---|
| [elsevier_test.xml](<F:/Python_Project/ComProScanner/reference/legacy/tests/test_apis_primary/elsevier_test.xml>) | 历史出版社测试输入样本。 |
| [springer_test.xml](<F:/Python_Project/ComProScanner/reference/legacy/tests/test_apis_primary/springer_test.xml>) | 历史出版社测试输入样本。 |
| [test_elsevier.py](<F:/Python_Project/ComProScanner/reference/legacy/tests/test_apis_primary/test_elsevier.py>) | 历史测试：elsevier；验证对象和用例见定义栏，不参与当前默认测试。 |
| [test_springer.py](<F:/Python_Project/ComProScanner/reference/legacy/tests/test_apis_primary/test_springer.py>) | 历史测试：springer；验证对象和用例见定义栏，不参与当前默认测试。 |
| [test_wiley.py](<F:/Python_Project/ComProScanner/reference/legacy/tests/test_apis_primary/test_wiley.py>) | 历史测试：wiley；验证对象和用例见定义栏，不参与当前默认测试。 |
| [wiley_test.pdf](<F:/Python_Project/ComProScanner/reference/legacy/tests/test_apis_primary/wiley_test.pdf>) | 历史出版社测试输入样本。 |

### reference/legacy/tests/test_metadata

旧流程的 test_metadata 子模块/历史测试目录，仅保留参考，不被正式包加载。

| 文件 | 具体用途 |
|---|---|
| [test_fetch_metadata.py](<F:/Python_Project/ComProScanner/reference/legacy/tests/test_metadata/test_fetch_metadata.py>) | 历史测试：fetch_metadata；验证对象和用例见定义栏，不参与当前默认测试。 |
| [test_filter_metadata.py](<F:/Python_Project/ComProScanner/reference/legacy/tests/test_metadata/test_filter_metadata.py>) | 历史测试：filter_metadata；验证对象和用例见定义栏，不参与当前默认测试。 |

### reference/legacy/tests/test_post_processing

旧流程的 test_post_processing 子模块/历史测试目录，仅保留参考，不被正式包加载。

| 文件 | 具体用途 |
|---|---|
| [test_data_cleaner.py](<F:/Python_Project/ComProScanner/reference/legacy/tests/test_post_processing/test_data_cleaner.py>) | 历史测试：data_cleaner；验证对象和用例见定义栏，不参与当前默认测试。 |

### reference/legacy/tests/test_post_processing/test_evaluation

旧流程的 test_evaluation 子模块/历史测试目录，仅保留参考，不被正式包加载。

| 文件 | 具体用途 |
|---|---|
| [test_eval_flow.py](<F:/Python_Project/ComProScanner/reference/legacy/tests/test_post_processing/test_evaluation/test_eval_flow.py>) | 历史测试：eval_flow；验证对象和用例见定义栏，不参与当前默认测试。 |
| [test_semantic_evaluator.py](<F:/Python_Project/ComProScanner/reference/legacy/tests/test_post_processing/test_evaluation/test_semantic_evaluator.py>) | 历史测试：semantic_evaluator；验证对象和用例见定义栏，不参与当前默认测试。 |

### reference/legacy/tests/test_post_processing/test_visualization

旧流程的 test_visualization 子模块/历史测试目录，仅保留参考，不被正式包加载。

| 文件 | 具体用途 |
|---|---|
| [test_create_knowledge_graph.py](<F:/Python_Project/ComProScanner/reference/legacy/tests/test_post_processing/test_visualization/test_create_knowledge_graph.py>) | 历史测试：create_knowledge_graph；验证对象和用例见定义栏，不参与当前默认测试。 |
| [test_data_distribution_visualizer.py](<F:/Python_Project/ComProScanner/reference/legacy/tests/test_post_processing/test_visualization/test_data_distribution_visualizer.py>) | 历史测试：data_distribution_visualizer；验证对象和用例见定义栏，不参与当前默认测试。 |
| [test_eval_plot_visualizer.py](<F:/Python_Project/ComProScanner/reference/legacy/tests/test_post_processing/test_visualization/test_eval_plot_visualizer.py>) | 历史测试：eval_plot_visualizer；验证对象和用例见定义栏，不参与当前默认测试。 |

### reference/legacy/tests/test_utils

旧流程的 test_utils 子模块/历史测试目录，仅保留参考，不被正式包加载。

| 文件 | 具体用途 |
|---|---|
| [test_common_functions.py](<F:/Python_Project/ComProScanner/reference/legacy/tests/test_utils/test_common_functions.py>) | 历史测试：common_functions；验证对象和用例见定义栏，不参与当前默认测试。 |
| [test_data_preparator.py](<F:/Python_Project/ComProScanner/reference/legacy/tests/test_utils/test_data_preparator.py>) | 历史测试：data_preparator；验证对象和用例见定义栏，不参与当前默认测试。 |
| [test_database_manager.py](<F:/Python_Project/ComProScanner/reference/legacy/tests/test_utils/test_database_manager.py>) | 历史测试：database_manager；验证对象和用例见定义栏，不参与当前默认测试。 |
| [test_embeddings.py](<F:/Python_Project/ComProScanner/reference/legacy/tests/test_utils/test_embeddings.py>) | 历史测试：embeddings；验证对象和用例见定义栏，不参与当前默认测试。 |
| [test_get_paper_data.py](<F:/Python_Project/ComProScanner/reference/legacy/tests/test_utils/test_get_paper_data.py>) | 历史测试：get_paper_data；验证对象和用例见定义栏，不参与当前默认测试。 |
| [test_pdf_to_markdown_text.py](<F:/Python_Project/ComProScanner/reference/legacy/tests/test_utils/test_pdf_to_markdown_text.py>) | 历史测试：pdf_to_markdown_text；验证对象和用例见定义栏，不参与当前默认测试。 |
| [test_prepare_iop_files.py](<F:/Python_Project/ComProScanner/reference/legacy/tests/test_utils/test_prepare_iop_files.py>) | 历史测试：prepare_iop_files；验证对象和用例见定义栏，不参与当前默认测试。 |
| [test_property_keyword_compatibility.py](<F:/Python_Project/ComProScanner/reference/legacy/tests/test_utils/test_property_keyword_compatibility.py>) | 历史测试：property_keyword_compatibility；验证对象和用例见定义栏，不参与当前默认测试。 |
| [test_save_results.py](<F:/Python_Project/ComProScanner/reference/legacy/tests/test_utils/test_save_results.py>) | 历史测试：save_results；验证对象和用例见定义栏，不参与当前默认测试。 |

### reference/maintenance/cleanup_20260906

大清理使用的迁移、归档、冻结消息及交付验证脚本。

| 文件 | 具体用途 |
|---|---|
| [archive_history.py](<F:/Python_Project/ComProScanner/reference/maintenance/cleanup_20260906/archive_history.py>) | 大清理时归档历史目录、逐文件校验字节后移除重复副本的脚本。 |
| [finish_cleanup.py](<F:/Python_Project/ComProScanner/reference/maintenance/cleanup_20260906/finish_cleanup.py>) | 大清理结束时移除验证临时副本、归档测试产物并移动迁移脚本。 |
| [freeze_messages.py](<F:/Python_Project/ComProScanner/reference/maintenance/cleanup_20260906/freeze_messages.py>) | 从清理前适配器捕获固定模型消息，用作回归预期；不调用模型。 |
| [organize_data.py](<F:/Python_Project/ComProScanner/reference/maintenance/cleanup_20260906/organize_data.py>) | 将旧 PDF、Gold、运行与报告移动到 data 并记录路径迁移的脚本。 |
| [organize_tests.py](<F:/Python_Project/ComProScanner/reference/maintenance/cleanup_20260906/organize_tests.py>) | 把旧测试按正式模块重新组织的脚本。 |
| [restructure.py](<F:/Python_Project/ComProScanner/reference/maintenance/cleanup_20260906/restructure.py>) | 大清理的源码模块迁移、导入改写和旧流程隔离脚本。 |
| [split_cli.py](<F:/Python_Project/ComProScanner/reference/maintenance/cleanup_20260906/split_cli.py>) | 将原大型 CLI 文件按文献、证据、抽取、结果、编排拆分的脚本。 |
| [verify_delivery.py](<F:/Python_Project/ComProScanner/reference/maintenance/cleanup_20260906/verify_delivery.py>) | 检查保护文件哈希、wheel 内容、独立安装入口和文档链接的脚本；需要对应临时安装环境。 |
| [write_docs.py](<F:/Python_Project/ComProScanner/reference/maintenance/cleanup_20260906/write_docs.py>) | 生成第一次清理的 README、使用说明等文档的脚本。 |

### reference/maintenance/file_inventory

生成当前逐文件用途说明的本地脚本。

| 文件 | 具体用途 |
|---|---|
| [generate_guide.py](<F:/Python_Project/ComProScanner/reference/maintenance/file_inventory/generate_guide.py>) | 只读盘点目录、提取源码定义和文件结构，生成本次逐文件说明和可搜索清单；不执行项目业务代码。 |

## 数据目录与每次运行

数据文件不是另一套流程代码。原 PDF、历史预测、Gold、图片和向量索引会随论文和运行次数增长；它们的体积不等于代码架构复杂度。

| 目录 | 具体用途 |
|---|---|
| [data/cache](<F:/Python_Project/ComProScanner/data/cache>) | 可重新生成的本地缓存。 |
| [data/cache/pytest](<F:/Python_Project/ComProScanner/data/cache/pytest>) | pytest 运行缓存，如上次失败和测试节点列表。 |
| [data/gold](<F:/Python_Project/ComProScanner/data/gold>) | 人工标准答案；普通抽取运行不应覆写。 |
| [data/gold/tc_001_030](<F:/Python_Project/ComProScanner/data/gold/tc_001_030>) | 常用前 30 篇论文的 Tc Gold、人工表格和论文 ID 对照。 |
| [data/literature](<F:/Python_Project/ComProScanner/data/literature>) | 原始 PDF、文献发现结果、来源数据和文献处理工作区。 |
| [data/literature/acquisition](<F:/Python_Project/ComProScanner/data/literature/acquisition>) | 检索候选、下载记录和文献获取实验数据。 |
| [data/literature/legacy_metadata](<F:/Python_Project/ComProScanner/data/literature/legacy_metadata>) | 迁移保留的旧文献元数据 CSV。 |
| [data/literature/pdfs](<F:/Python_Project/ComProScanner/data/literature/pdfs>) | 本地及下载 PDF 的输入仓库。 |
| [data/literature/processing](<F:/Python_Project/ComProScanner/data/literature/processing>) | 单独运行 process-articles 时的处理工作区。 |
| [data/literature/recovered_001_030](<F:/Python_Project/ComProScanner/data/literature/recovered_001_030>) | 前 30 篇历史恢复输入；目前还随数据保留一个旧离线处理脚本，已失配新包路径。 |
| [data/literature/validation_sample](<F:/Python_Project/ComProScanner/data/literature/validation_sample>) | 用于少量本地验证的复杂论文 PDF。 |
| [data/logs](<F:/Python_Project/ComProScanner/data/logs>) | 当前程序日志。 |
| [data/maintenance](<F:/Python_Project/ComProScanner/data/maintenance>) | 清理与收尾的快照、比较、校验日志和构建包。 |
| [data/maintenance/cleanup_20260906](<F:/Python_Project/ComProScanner/data/maintenance/cleanup_20260906>) | 第一次目录重构的备份和验收产物。 |
| [data/maintenance/cleanup_finish_20260906](<F:/Python_Project/ComProScanner/data/maintenance/cleanup_finish_20260906>) | 清理收尾的备份、测试、哈希校验和新构建包。 |
| [data/metrics](<F:/Python_Project/ComProScanner/data/metrics>) | 单独保存的历史评估结果。 |
| [data/reports](<F:/Python_Project/ComProScanner/data/reports>) | 人工审查、实验比较与实现说明。 |
| [data/reports/presentations](<F:/Python_Project/ComProScanner/data/reports/presentations>) | 项目演示用 PPT 文件。 |
| [data/reports/project](<F:/Python_Project/ComProScanner/data/reports/project>) | 项目报告的预留/归档目录；是否有文件以本次目录清单为准。 |
| [data/runs](<F:/Python_Project/ComProScanner/data/runs>) | 按 run-id 隔离的各次运行输入、证据、模型输出和最终结果。 |
| [data/runs/cleanup_before_evidence_20260906](<F:/Python_Project/ComProScanner/data/runs/cleanup_before_evidence_20260906>) | 清理前源码快照在同一批 30 篇 Article 上重放 Evidence 的对照输出。 |
| [data/runs/cleanup_docling_20260906](<F:/Python_Project/ComProScanner/data/runs/cleanup_docling_20260906>) | 第一次实际 Docling 解析验收输出。 |
| [data/runs/cleanup_docling_final_20260906](<F:/Python_Project/ComProScanner/data/runs/cleanup_docling_final_20260906>) | 最终 Docling 本地验证输出，含论文标题及完整解析资产。 |
| [data/runs/cleanup_evidence_replay_20260906](<F:/Python_Project/ComProScanner/data/runs/cleanup_evidence_replay_20260906>) | 清理后同配置重放 30 篇 Evidence 的输出，用于比较一致性。 |
| [data/runs/cleanup_material_replay_20260906](<F:/Python_Project/ComProScanner/data/runs/cleanup_material_replay_20260906>) | 重放已有 4 日事实的材料恢复，保存 59 条最终预测及结果表。 |
| [data/runs/cleanup_rag_20260906](<F:/Python_Project/ComProScanner/data/runs/cleanup_rag_20260906>) | 第一次本地 PhysBERT 建库和查询验证。 |
| [data/runs/cleanup_rag_final_20260906](<F:/Python_Project/ComProScanner/data/runs/cleanup_rag_final_20260906>) | 收尾配置下的本地 PhysBERT 验证。 |
| [data/runs/complex_paper12_prepare_20260905](<F:/Python_Project/ComProScanner/data/runs/complex_paper12_prepare_20260905>) | 历史独立运行目录。名称用于区分实验；是否实际成功、调用何种模型以本目录配置/状态为准。 |
| [data/runs/live_acceptance_20260905](<F:/Python_Project/ComProScanner/data/runs/live_acceptance_20260905>) | 历史独立运行目录。名称用于区分实验；是否实际成功、调用何种模型以本目录配置/状态为准。 |
| [data/runs/live_acceptance_network_20260905](<F:/Python_Project/ComProScanner/data/runs/live_acceptance_network_20260905>) | 历史独立运行目录。名称用于区分实验；是否实际成功、调用何种模型以本目录配置/状态为准。 |
| [data/runs/live_band_gap_selected_20260905](<F:/Python_Project/ComProScanner/data/runs/live_band_gap_selected_20260905>) | 历史独立运行目录。名称用于区分实验；是否实际成功、调用何种模型以本目录配置/状态为准。 |
| [data/runs/live_band_gap_selected_network_20260905](<F:/Python_Project/ComProScanner/data/runs/live_band_gap_selected_network_20260905>) | 历史独立运行目录。名称用于区分实验；是否实际成功、调用何种模型以本目录配置/状态为准。 |
| [data/runs/live_tc_prepare_20260905](<F:/Python_Project/ComProScanner/data/runs/live_tc_prepare_20260905>) | 历史独立运行目录。名称用于区分实验；是否实际成功、调用何种模型以本目录配置/状态为准。 |
| [data/runs/live_tc_selected_20260905](<F:/Python_Project/ComProScanner/data/runs/live_tc_selected_20260905>) | 历史独立运行目录。名称用于区分实验；是否实际成功、调用何种模型以本目录配置/状态为准。 |
| [data/runs/live_tc_selected_network_20260905](<F:/Python_Project/ComProScanner/data/runs/live_tc_selected_network_20260905>) | 历史独立运行目录。名称用于区分实验；是否实际成功、调用何种模型以本目录配置/状态为准。 |
| [data/runs/paid_complex_paper12_20260905](<F:/Python_Project/ComProScanner/data/runs/paid_complex_paper12_20260905>) | 历史独立运行目录。名称用于区分实验；是否实际成功、调用何种模型以本目录配置/状态为准。 |
| [data/runs/paid_complex_paper12_nonthinking_20260905](<F:/Python_Project/ComProScanner/data/runs/paid_complex_paper12_nonthinking_20260905>) | 历史独立运行目录。名称用于区分实验；是否实际成功、调用何种模型以本目录配置/状态为准。 |
| [data/runs/paid_small_validation_20260905](<F:/Python_Project/ComProScanner/data/runs/paid_small_validation_20260905>) | 历史独立运行目录。名称用于区分实验；是否实际成功、调用何种模型以本目录配置/状态为准。 |
| [data/runs/production_fixture_end_to_end_20260905](<F:/Python_Project/ComProScanner/data/runs/production_fixture_end_to_end_20260905>) | 历史独立运行目录。名称用于区分实验；是否实际成功、调用何种模型以本目录配置/状态为准。 |
| [data/runs/production_local_tools_20260905](<F:/Python_Project/ComProScanner/data/runs/production_local_tools_20260905>) | 历史独立运行目录。名称用于区分实验；是否实际成功、调用何种模型以本目录配置/状态为准。 |
| [data/runs/production_single_pdf_20260905](<F:/Python_Project/ComProScanner/data/runs/production_single_pdf_20260905>) | 历史独立运行目录。名称用于区分实验；是否实际成功、调用何种模型以本目录配置/状态为准。 |
| [data/runs/tc_20260904_material_recovered_20260906](<F:/Python_Project/ComProScanner/data/runs/tc_20260904_material_recovered_20260906>) | 在 4 日事实基础上进行材料名称恢复并对照 Gold 的结果。 |
| [data/runs/tc_baseline_targeted_20260906](<F:/Python_Project/ComProScanner/data/runs/tc_baseline_targeted_20260906>) | 针对历史问题 Evidence 的小范围重跑及审查记录。 |
| [data/runs/tc_final_001_030](<F:/Python_Project/ComProScanner/data/runs/tc_final_001_030>) | 此前前 30 篇结果整理目录；名称不表示它自动取代 4 日基线。 |
| [data/runs/tc_fulltext_001_030_20260904](<F:/Python_Project/ComProScanner/data/runs/tc_fulltext_001_030_20260904>) | 需要保留的 9 月 4 日前 30 篇抽取基线及后续历史附件。 |
| [data/runs/tc_hybrid_001_100](<F:/Python_Project/ComProScanner/data/runs/tc_hybrid_001_100>) | 以 001–100 命名的历史候选文本/RAG 实验目录；不据名称推断已全部跑完。 |
| [data/runs/tc_paper12_thinking_comparison_20260906](<F:/Python_Project/ComProScanner/data/runs/tc_paper12_thinking_comparison_20260906>) | 第 12 篇复杂材料的 thinking 对比实验记录。 |
| [data/runs/tc_single_evidence_001_030_20260905](<F:/Python_Project/ComProScanner/data/runs/tc_single_evidence_001_030_20260905>) | 另一批以 001–030 命名的逐 Evidence 历史运行；以其配置和产物确认范围。 |
| [data/runs/tc_single_evidence_30_20260905](<F:/Python_Project/ComProScanner/data/runs/tc_single_evidence_30_20260905>) | 9 月 5 日逐 Evidence 的 30 篇准备/抽取与 Gold 比较产物。 |

### 同一次运行中各文件的区别

| 文件/子目录 | 具体用途 |
|---|---|
| `article.csv` | 统一 Article 输入/中间表，保存正文、表格、图清单及文献信息。 |
| `run_config.json` | 本次运行的 preset、输入、工具和模型等配置；用于追溯与续跑检查。 |
| `manifest.json` | 本目录的对象清单；运行层记录论文处理状态，资产层记录文件路径和导出情况，图片层记录图文关联。 |
| `stage_status.json` | 端到端各阶段状态、退出码及错误。 |
| `all.json` | 该运行合并保存的全部 Evidence。 |
| `predictions.json` | 该运行的预测事实；是否已经材料恢复取决于运行阶段，不是人工 Gold。 |
| `predictions.csv` | 最终事实与论文元数据联表的 CSV 导出。 |
| `predictions.xlsx` | 最终结果工作簿，当前导出含 facts 和 papers 表。 |
| `review.xlsx` | 附 Evidence 的人工审查工作簿；模型输出尚需由人决定接受、拒绝或修改。 |
| `failures.json` | 运行阶段收集的失败项。 |
| `tool_usage.json` | 逐 Evidence 的工具/模型路线与执行状态记录；不一定是精确 token 账单。 |
| `metrics.json` | 该次评估的指标与错误项；需结合运行配置确认评分口径。 |
| `material_changes.json` | 材料恢复前后名称差异记录。 |
| `gold_facts.json` | 人工标准事实，供评分时作 Gold。 |
| `gold_review.xlsx` | 人工 Gold 审查表，保留人工标注与核对信息。 |
| `paper_id_map.json` | 历史 paper_id 与运行 document_id 的对应关系。 |
| `original.pdf` | 为解析追溯保留的输入 PDF 原件副本。 |
| `article.md` | 这一篇文献保存的 Markdown/正文副本。 |
| `document.json` | Docling 解析结构，包括文本、布局/位置引用和图片/表格等条目。 |
| `metadata.json` | 文献标识、来源和元数据的旁存文件。 |
| `info.json` | 图片编号与标题说明的历史侧车文件。 |
| `chroma.sqlite3` | Chroma 向量库元数据与集合记录，必须和对应索引目录一起使用。 |
| `header.bin` | 向量索引的内部头信息；由向量库维护。 |
| `data_level0.bin` | HNSW 向量索引的数据层；由向量库维护。 |
| `length.bin` | 向量索引内部长度记录；由向量库维护。 |
| `link_lists.bin` | HNSW 索引的邻接关系；由向量库维护。 |

`evidence/` 保存分块与 Evidence；`papers/` 保存逐 Evidence 检查点；`processor_workspace/` 保存来源解析中间产物；`vector_db/` 保存这次运行的向量库。相同文件名位于不同 run-id 下，代表不同实验，不可直接混用。

### 清理验证产物：逐文件

| 文件 | 具体用途 |
|---|---|
| [data/maintenance/cleanup_20260906/archive_history.txt](<F:/Python_Project/ComProScanner/data/maintenance/cleanup_20260906/archive_history.txt>) | 历史命令输出/验证记录：archive_history；具体结论应读取文件，不以文件名推定成功。 |
| [data/maintenance/cleanup_20260906/baseline_replay.log](<F:/Python_Project/ComProScanner/data/maintenance/cleanup_20260906/baseline_replay.log>) | 此目录所属程序/实验的运行日志。 |
| [data/maintenance/cleanup_20260906/baseline_tests.txt](<F:/Python_Project/ComProScanner/data/maintenance/cleanup_20260906/baseline_tests.txt>) | 对应验证阶段的 pytest 命令输出。 |
| [data/maintenance/cleanup_20260906/before.log](<F:/Python_Project/ComProScanner/data/maintenance/cleanup_20260906/before.log>) | 此目录所属程序/实验的运行日志。 |
| [data/maintenance/cleanup_20260906/before_cleanup.zip](<F:/Python_Project/ComProScanner/data/maintenance/cleanup_20260906/before_cleanup.zip>) | 大清理之前的源码、测试与文档快照，含当时未提交内容。 |
| [data/maintenance/cleanup_20260906/collection.txt](<F:/Python_Project/ComProScanner/data/maintenance/cleanup_20260906/collection.txt>) | 历史命令输出/验证记录：collection；具体结论应读取文件，不以文件名推定成功。 |
| [data/maintenance/cleanup_20260906/data/logs/comproscanner.log](<F:/Python_Project/ComProScanner/data/maintenance/cleanup_20260906/data/logs/comproscanner.log>) | 此目录所属程序/实验的运行日志。 |
| [data/maintenance/cleanup_20260906/data_integrity.json](<F:/Python_Project/ComProScanner/data/maintenance/cleanup_20260906/data_integrity.json>) | 目录迁移后原文与关键结果的完整性检查摘要。 |
| [data/maintenance/cleanup_20260906/delivery_checks.txt](<F:/Python_Project/ComProScanner/data/maintenance/cleanup_20260906/delivery_checks.txt>) | 历史命令输出/验证记录：delivery_checks；具体结论应读取文件，不以文件名推定成功。 |
| [data/maintenance/cleanup_20260906/diff_check.txt](<F:/Python_Project/ComProScanner/data/maintenance/cleanup_20260906/diff_check.txt>) | 历史命令输出/验证记录：diff_check；具体结论应读取文件，不以文件名推定成功。 |
| [data/maintenance/cleanup_20260906/directory_moves.json](<F:/Python_Project/ComProScanner/data/maintenance/cleanup_20260906/directory_moves.json>) | 实际目录迁移记录。 |
| [data/maintenance/cleanup_20260906/dist/comproscanner-2026.9.6-py3-none-any.whl](<F:/Python_Project/ComProScanner/data/maintenance/cleanup_20260906/dist/comproscanner-2026.9.6-py3-none-any.whl>) | 该轮验收构建的 Python 安装包；可安装，不是可编辑源码目录。 |
| [data/maintenance/cleanup_20260906/docling_final.txt](<F:/Python_Project/ComProScanner/data/maintenance/cleanup_20260906/docling_final.txt>) | 历史命令输出/验证记录：docling_final；具体结论应读取文件，不以文件名推定成功。 |
| [data/maintenance/cleanup_20260906/docling_real.txt](<F:/Python_Project/ComProScanner/data/maintenance/cleanup_20260906/docling_real.txt>) | 历史命令输出/验证记录：docling_real；具体结论应读取文件，不以文件名推定成功。 |
| [data/maintenance/cleanup_20260906/environment.json](<F:/Python_Project/ComProScanner/data/maintenance/cleanup_20260906/environment.json>) | 验证环境已安装的 Python 包与版本列表。 |
| [data/maintenance/cleanup_20260906/evidence_before.txt](<F:/Python_Project/ComProScanner/data/maintenance/cleanup_20260906/evidence_before.txt>) | 历史命令输出/验证记录：evidence_before；具体结论应读取文件，不以文件名推定成功。 |
| [data/maintenance/cleanup_20260906/evidence_replay.txt](<F:/Python_Project/ComProScanner/data/maintenance/cleanup_20260906/evidence_replay.txt>) | 历史命令输出/验证记录：evidence_replay；具体结论应读取文件，不以文件名推定成功。 |
| [data/maintenance/cleanup_20260906/evidence_replay_comparison.json](<F:/Python_Project/ComProScanner/data/maintenance/cleanup_20260906/evidence_replay_comparison.json>) | 相同输入/设置的清理前后 Evidence 比较结果。 |
| [data/maintenance/cleanup_20260906/final_acceptance.json](<F:/Python_Project/ComProScanner/data/maintenance/cleanup_20260906/final_acceptance.json>) | 实际 PDF 解析资产及关键文件完整性等最终检查结果。 |
| [data/maintenance/cleanup_20260906/final_layout.json](<F:/Python_Project/ComProScanner/data/maintenance/cleanup_20260906/final_layout.json>) | 清理结束的根目录、临时目录移除及脚本迁移记录。 |
| [data/maintenance/cleanup_20260906/final_tests.txt](<F:/Python_Project/ComProScanner/data/maintenance/cleanup_20260906/final_tests.txt>) | 对应验证阶段的 pytest 命令输出。 |
| [data/maintenance/cleanup_20260906/formatter_install.txt](<F:/Python_Project/ComProScanner/data/maintenance/cleanup_20260906/formatter_install.txt>) | 历史命令输出/验证记录：formatter_install；具体结论应读取文件，不以文件名推定成功。 |
| [data/maintenance/cleanup_20260906/full_tests.txt](<F:/Python_Project/ComProScanner/data/maintenance/cleanup_20260906/full_tests.txt>) | 对应验证阶段的 pytest 命令输出。 |
| [data/maintenance/cleanup_20260906/generated_test_outputs/article_processor_failed_articles.txt](<F:/Python_Project/ComProScanner/data/maintenance/cleanup_20260906/generated_test_outputs/article_processor_failed_articles.txt>) | 文献处理失败项目或失败文件名记录。 |
| [data/maintenance/cleanup_20260906/git_status_before.txt](<F:/Python_Project/ComProScanner/data/maintenance/cleanup_20260906/git_status_before.txt>) | 清理前工作区的 Git 修改状态，供恢复和审计。 |
| [data/maintenance/cleanup_20260906/history_archive.json](<F:/Python_Project/ComProScanner/data/maintenance/cleanup_20260906/history_archive.json>) | 历史归档的文件数与逐文件字节校验记录。 |
| [data/maintenance/cleanup_20260906/material_replay.txt](<F:/Python_Project/ComProScanner/data/maintenance/cleanup_20260906/material_replay.txt>) | 历史命令输出/验证记录：material_replay；具体结论应读取文件，不以文件名推定成功。 |
| [data/maintenance/cleanup_20260906/material_replay_comparison.json](<F:/Python_Project/ComProScanner/data/maintenance/cleanup_20260906/material_replay_comparison.json>) | 材料后处理前后版本的最终预测一致性比较。 |
| [data/maintenance/cleanup_20260906/migration_tests.txt](<F:/Python_Project/ComProScanner/data/maintenance/cleanup_20260906/migration_tests.txt>) | 对应验证阶段的 pytest 命令输出。 |
| [data/maintenance/cleanup_20260906/module_map.json](<F:/Python_Project/ComProScanner/data/maintenance/cleanup_20260906/module_map.json>) | 旧源码模块到新模块的对应表。 |
| [data/maintenance/cleanup_20260906/preset_tests.txt](<F:/Python_Project/ComProScanner/data/maintenance/cleanup_20260906/preset_tests.txt>) | 对应验证阶段的 pytest 命令输出。 |
| [data/maintenance/cleanup_20260906/protected_hashes.json](<F:/Python_Project/ComProScanner/data/maintenance/cleanup_20260906/protected_hashes.json>) | 受保护 Gold 和关键结果文件的 SHA-256 基准。 |
| [data/maintenance/cleanup_20260906/rag_final.txt](<F:/Python_Project/ComProScanner/data/maintenance/cleanup_20260906/rag_final.txt>) | 历史命令输出/验证记录：rag_final；具体结论应读取文件，不以文件名推定成功。 |
| [data/maintenance/cleanup_20260906/rag_real.txt](<F:/Python_Project/ComProScanner/data/maintenance/cleanup_20260906/rag_real.txt>) | 历史命令输出/验证记录：rag_real；具体结论应读取文件，不以文件名推定成功。 |
| [data/maintenance/cleanup_20260906/snapshot_manifest.json](<F:/Python_Project/ComProScanner/data/maintenance/cleanup_20260906/snapshot_manifest.json>) | 清理前快照中各文件的哈希清单。 |
| [data/maintenance/cleanup_20260906/source_boundary_tests.txt](<F:/Python_Project/ComProScanner/data/maintenance/cleanup_20260906/source_boundary_tests.txt>) | 对应验证阶段的 pytest 命令输出。 |
| [data/maintenance/cleanup_20260906/wheel_build.txt](<F:/Python_Project/ComProScanner/data/maintenance/cleanup_20260906/wheel_build.txt>) | 历史命令输出/验证记录：wheel_build；具体结论应读取文件，不以文件名推定成功。 |
| [data/maintenance/cleanup_20260906/wheel_install.txt](<F:/Python_Project/ComProScanner/data/maintenance/cleanup_20260906/wheel_install.txt>) | 历史命令输出/验证记录：wheel_install；具体结论应读取文件，不以文件名推定成功。 |
| [data/maintenance/cleanup_20260906/wheel_smoke.txt](<F:/Python_Project/ComProScanner/data/maintenance/cleanup_20260906/wheel_smoke.txt>) | 历史命令输出/验证记录：wheel_smoke；具体结论应读取文件，不以文件名推定成功。 |
| [data/maintenance/cleanup_finish_20260906/before_finish.zip](<F:/Python_Project/ComProScanner/data/maintenance/cleanup_finish_20260906/before_finish.zip>) | 小范围收尾之前的源码、测试与文档快照。 |
| [data/maintenance/cleanup_finish_20260906/diff_check.txt](<F:/Python_Project/ComProScanner/data/maintenance/cleanup_finish_20260906/diff_check.txt>) | 历史命令输出/验证记录：diff_check；具体结论应读取文件，不以文件名推定成功。 |
| [data/maintenance/cleanup_finish_20260906/dist/comproscanner-2026.9.6-py3-none-any.whl](<F:/Python_Project/ComProScanner/data/maintenance/cleanup_finish_20260906/dist/comproscanner-2026.9.6-py3-none-any.whl>) | 该轮验收构建的 Python 安装包；可安装，不是可编辑源码目录。 |
| [data/maintenance/cleanup_finish_20260906/tests.txt](<F:/Python_Project/ComProScanner/data/maintenance/cleanup_finish_20260906/tests.txt>) | 对应验证阶段的 pytest 命令输出。 |
| [data/maintenance/cleanup_finish_20260906/verification.json](<F:/Python_Project/ComProScanner/data/maintenance/cleanup_finish_20260906/verification.json>) | 收尾源码变化、保护文件哈希和安装包检查结果。 |
| [data/maintenance/cleanup_finish_20260906/wheel.txt](<F:/Python_Project/ComProScanner/data/maintenance/cleanup_finish_20260906/wheel.txt>) | 历史命令输出/验证记录：wheel；具体结论应读取文件，不以文件名推定成功。 |

## 哪些文件需要经常关注

- 新增属性：`presets/`，通常以 `band_gap.py` 为参考。
- 跑整条流程：`cli/main.py` 和 `cli/run.py`。
- 修改某个证据工具：`evidence/providers/`；切分规则只在 `evidence/chunking/text_chunker.py`。
- 看模型到底收到什么：`presets/_shared.py`、属性 preset、`extraction/litellm_adapters.py`。
- 修改材料恢复：`results/facts/materials.py` 与 `processors.py`。
- 查结果和人工判断：对应 run 的 `predictions.json`、`review.xlsx`，以及 `data/gold/`。

## 本次盘点发现的历史残留

`data/literature/recovered_001_030/postprocess_existing.py` 仍随历史数据保留，它引用旧包名和旧路径，不能作为当前入口。`reference/legacy/tests/` 中存在历史 `.pyc` 缓存；`src/comproscanner.egg-info/` 是安装生成信息。本次是用途说明，没有修改这些文件或业务逻辑。

## 范围与更新

本清单为静态快照；新运行会增加文件。生成脚本在 `reference/maintenance/file_inventory/generate_guide.py`，只读取目录/定义/有限结构并重写这两份说明。Git 哈希对象、重复论文资产和每个运行 JSON 均可在完整清单搜索到；对仅按命名或位置判断的附件，已明确标注，不宣称逐篇验证科学内容。
