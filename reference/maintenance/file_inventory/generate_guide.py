"""Generate a local file guide without importing the project or reading secrets."""
from __future__ import annotations

import ast
from collections import Counter
from datetime import datetime
import html
import json
import os
from pathlib import Path
import re
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[3]
DOCS = ROOT / "docs"


def mapping(text):
    return dict(line.split("|", 1) for line in text.strip().splitlines())


CORE = mapping("""
__init__.py|包的说明和版本号；导入 comproscanner 时不会启动旧流程或模型。
__main__.py|使 python -m comproscanner 可以调用统一命令行入口。
_errors.py|定义参数、文件、依赖及中断相关异常，统一错误表达。
_logging.py|配置日志级别、终端格式和日志文件输出，供各模块记录执行过程。
_paths.py|读取 data/path_migrations.json，把历史记录中的旧文件路径定位到迁移后位置，避免改写原结果。
cli/main.py|定义所有 CLI 子命令和参数；合并 preset 默认模型设置，再把命令分派到对应阶段。
cli/__main__.py|支持 python -m comproscanner.cli，转入相同 CLI 主入口。
cli/common.py|CLI 共用的小函数：运行编号、安全文件名、网络执行检查，以及 Evidence 和 Fact 的反序列化。
cli/documents.py|编排文献发现、开放获取 PDF 下载和单独的文献处理命令。
cli/evidence.py|读取 Article CSV，加载 preset，按开关运行 Evidence 工具；写出分块、证据、失败项和准备配置。
cli/extraction.py|逐条执行 Evidence 抽取，保存模型配置、响应和检查点；组装 Fact，调用材料后处理并写预测。
cli/results.py|编排已有预测的材料恢复、最终表格导出、Review 生成及 Gold 评估；准备文章与 PDF 上下文。
cli/run.py|端到端主流程：文献处理、Article 归一化、Evidence 准备、抽取、Review、评估；维护阶段状态和续跑检查。
documents/assets.py|在旧 XML 内容变换前保留正文；从 Docling 结果取标题；保存原 PDF、Markdown、结构 JSON、页面图、图片和资产清单。
documents/csv_store.py|清除 CSV 中的 NUL 字符，规范化并保存 Article；关联图片清单，写每篇 article.md 和 metadata.json，按 DOI 避免重复写入。
documents/dispatch.py|按来源和 DOI 的出版社信息分派到五个文献处理器；本身不抽取属性、不建立隐藏向量库。
documents/docling.py|配置和调用 Docling：OCR、版面、表格、Markdown、图片；还提供从 Markdown 生成历史章节列的适配方法。
documents/figures.py|各来源共用的图片存储工具：保存图片字节或本地图片、维护说明和 manifest、记录文献处理失败。
documents/metadata.py|辅助查询 OpenAlex 元数据和 Crossref DOI；生成统一参数错误信息并记录超时 DOI。
documents/prepare_iop.py|在工作副本内整理 IOP XML 和 ZIP，保留图片资源，识别真实 DOI，补全本地元数据并记录图片所在目录。
documents/signals.py|清理正文字符，识别关键词和正则信号；用于诊断字段，不承担 Article 初筛。
documents/config/__init__.py|导出文献配置类，并用 ArticlePaths 约定解析器中间 CSV 的目录位置。
documents/config/article_keywords.py|存放通用章节标题、方法等识别词，帮助旧解析器把正文归入章节；不是 Tc 属性抽取词库。
documents/config/base_urls.py|集中保存出版社和文献元数据服务的基础 URL。
documents/config/paths.py|约定元数据 CSV、处理记录和失败日志位置，并读取 IOP_papers_path 环境变量。
documents/ingestion/registry.py|登记本地 PDF、下载 PDF、Elsevier、Springer、Wiley、IOP 等来源及其格式、处理器、联网和凭据要求。
documents/ingestion/process.py|构建并执行 ArticleProcessingPlan，读取 DOI 文件、检查必要配置，准备出版社元数据输入后调用来源分派。
documents/ingestion/normalize.py|将多个处理器 CSV 合并为统一 Article CSV，处理图片清单路径、按 document_id 去重并原子写出。
documents/literature/io.py|文献获取层的基础 IO：规范 DOI、安全文件名，以及 JSON/CSV 的读取和原子写入。
documents/literature/oa.py|从 Semantic Scholar/OpenAlex 查开放获取位置；下载后验证 PDF、计算哈希并避免重复内容。
documents/literature/scopus.py|向 Scopus 检索论文元数据并规范返回项；只做文献发现，不提取材料属性。
documents/literature/storage.py|定义原始文献仓库布局：manual、按来源划分的 downloaded、normalized 和 quarantine 目录。
documents/publishers/elsevier_processor.py|调用 Elsevier 内容接口，解析原生 XML 的正文、章节、表格和图片，保留原 XML并写 Article 中间 CSV。
documents/publishers/springer_processor.py|访问 Springer JATS 来源，处理 XML、正文、表格和图片，保存原始响应并写 Article 中间 CSV。
documents/publishers/iop_processor.py|读取本地 IOP JATS XML，调用工作副本整理，解析正文和表格；图片优先读取本地，可按配置尝试 IOP CDN。
documents/publishers/wiley_processor.py|通过 Wiley TDM 获取 PDF，交给同一个 Docling 解析组件，再写 Article 中间 CSV。
documents/publishers/pdfs_processor.py|遍历本地 PDF，识别 DOI/本地文献 ID、查询可用元数据、记录哈希和处理状态，调用 Docling 生成 Article。
documents/schemas/article_csv.py|定义统一 Article 列、默认值和校验；把历史字段及额外论文元数据转换到正式契约。
evidence/models.py|定义 Evidence、EvidenceType 和 RetrievalMethod：证据 ID、文献、原文、位置、来源类型及检索过程。
evidence/registry.py|Evidence 工具的注册和按名创建；用于选择工具而不是写死一套全部启用的流程。
evidence/preparation.py|统一准备器：从 Article 正文切分、标记参考文献区，再按开关运行文本、表格、图片和公式选择器。
evidence/text.py|把规则和向量检索命中映射到同一 chunk；同一文本块形成一条 Evidence，保留各检索来源。
evidence/source_units.py|把 Article 的表格文本、图片清单和文本块中的显式公式转换为 TableUnit、FigureUnit、EquationUnit；表格保留原文，不保证已经完全结构化行列。
evidence/figure_manifest.py|读取图片 manifest，将图片路径、标题、邻近文字、页码组装为 FigureUnit，并兼容历史相对路径。
evidence/vector_store.py|TextChunk 与底层 Chroma 管理器之间的适配层：写入规范 chunk，并把检索结果还原为 chunk 命中。
evidence/chunking/text_chunker.py|唯一正文切分实现：保留段落、章节和位置，控制目标长度、最大长度及重叠，生成稳定的 TextChunk。
evidence/providers/base.py|定义 EvidenceProvider 接口和通用正则匹配函数。
evidence/providers/rule_text.py|候选文本工具：在已有 TextChunk 上按 preset 关键词/正则选择，返回命中记录。
evidence/providers/vector_text.py|RAG 工具：把同一批 TextChunk 建库，执行属性查询，返回向量检索命中及分数。
evidence/providers/table.py|表格工具：按规则选择 TableUnit，保留表题、原文或结构化表头/行/注释，输出表格 Evidence。
evidence/providers/figure.py|图片工具：根据图题和邻近文字选图，保留图片位置并构造不会跨论文冲突的 Evidence ID；此处不调用视觉模型。
evidence/providers/equation.py|公式工具：按属性规则选中公式及其上下文，形成公式 Evidence。
evidence/rag/config.py|承载从 preset 解析出的嵌入模型、数据库目录、长度和检索数量设置。
evidence/rag/embeddings.py|把文本转换成向量；支持 Hugging Face、Sentence Transformers 和 OpenAI 适配。当前 PhysBERT 配置在本地执行。
evidence/rag/store.py|操作 Chroma 持久化索引：规范 chunk 建库、相似度检索、存在性检查和资源释放；不再次切分正文。
extraction/evidence_flow.py|每条 Evidence 的模型编排：文本/表格/公式先 identifier 再 extractor；图片先 vision 再 extractor，逐条隔离错误。
extraction/litellm_adapters.py|实际模型适配层：组装 preset 提示词、读取环境密钥、调用 LiteLLM、解析 JSON；图片被编码后发送给视觉模型。
presets/base.py|PropertyExtractionPreset 契约与校验；约定关键词、工具、查询、提示词、模型、字段、条件和评估映射。
presets/_shared.py|各 preset 可覆盖的默认配置：identifier/extractor/vision 消息模板、模型选择、Fact 输出字段和本地 RAG 设置。
presets/registry.py|按文件名发现并加载 preset，同时支持显式注册；新增常规属性文件不必修改主流程。
presets/curie_temperature.py|Tc 专属知识配置：关键词、高召回候选规则、RAG 查询、科学提示词、模型、单位和历史 Gold 字段映射；保留已验证消息内容。
presets/band_gap.py|带隙属性配置示例：明确材料-能隙绑定，区分光学与计算方法，要求 eV 单位及相关条件；实际论文准确率尚未评测。
results/run_store.py|规定一次 run 的目录，原子保存 JSON和阶段状态，阻止写到运行目录外或覆写 Gold。
results/export.py|把最终 Facts 与 Article 论文信息关联，输出 predictions.csv 和 XLSX 的 facts、papers 工作表。
results/review.py|生成 review.xlsx：每条事实附原始 Evidence、图片路径、材料恢复问题及 ACCEPT/REJECT/MODIFY 人工决定列。
results/gold.py|读取人工完成的 Review，只把 ACCEPT/MODIFY 行写到新的 Gold 文件，保留证据关联并拒绝覆盖已有 Gold。
results/facts/models.py|定义 FactValue 和 Fact，保存材料原名、恢复名、属性值、单位、限定、条件、证据 ID 与扩展字段。
results/facts/materials.py|现有本地材料工具：化学式规范化、变量赋值代入、利用同文证据和正文恢复缩写及完整配方。
results/facts/processors.py|FactProcessor 统一调用材料规范化并检查单位/条件，记录问题；另保留可选外部材料解析 API 适配器。
results/facts/merger.py|保守合并表示等价的事实，保留所有 Evidence 和原始材料写法；区分条件、限定及扩展属性。
results/evaluation/inputs.py|正式评估输入适配器：根据 preset 映射历史字段/属性别名，根据显式 paper_map 对齐论文标识，拒绝冲突。
results/evaluation/strict.py|严格多重集合匹配，计算 TP、FP、FN、Precision、Recall、F1，并返回具体 FP/FN；不自动推断材料等价或换算单位。
""")

FOLDERS = mapping("""
.git|Git 自身的版本记录、引用、对象和本地状态，不参与论文处理。
.github|GitHub 自动化与提问/问题反馈模板。
.github/ISSUE_TEMPLATE|提交缺陷、文档问题、功能建议或一般问题时使用的表单模板。
.github/workflows|CI 自动执行流程定义。
src|可安装的正式 Python 包源码，以及安装工具生成的包元数据。
src/comproscanner|正式应用包：四个业务模块、属性配置、CLI 和少量共用支持。
src/comproscanner/cli|命令行入口和阶段编排，把业务模块连成一条流程。
src/comproscanner/documents|第一模块：来源文献到统一 Article，保留原始资产。
src/comproscanner/documents/config|通用文献格式、服务地址和路径约定。
src/comproscanner/documents/ingestion|来源注册、执行计划和多来源 Article 归一化。
src/comproscanner/documents/literature|文献发现、开放获取下载与原始仓库布局。
src/comproscanner/documents/publishers|五种处理器实现，分别适配 Elsevier、Springer、IOP、Wiley 和本地 PDF。
src/comproscanner/documents/schemas|统一 Article 数据契约与校验。
src/comproscanner/evidence|第二模块：统一正文切分与可追溯证据准备。
src/comproscanner/evidence/chunking|规则与 RAG 共用的正文分块。
src/comproscanner/evidence/providers|五个可选择的 Evidence 工具及统一接口。
src/comproscanner/evidence/rag|嵌入模型和持久化向量检索实现。
src/comproscanner/extraction|第三模块：每条 Evidence 的识别、视觉解读和属性抽取。
src/comproscanner/presets|属性知识与模型配置入口；新增属性主要修改这里。
src/comproscanner/results|第四模块：材料恢复、事实合并、最终表格、Review、Gold 和评估。
src/comproscanner/results/facts|事实数据模型、材料解析和保守合并逻辑。
src/comproscanner/results/evaluation|显式输入映射和严格事实评分。
src/comproscanner.egg-info|pip/setuptools 自动生成的安装元数据，不是另一套业务代码。
tests|正式回归测试及其输入样本；默认离线执行。
tests/cli|验证命令入口、执行开关、阶段衔接和续跑。
tests/documents|验证文献来源、资产保留和 Article 转换。
tests/documents/publishers|各出版社及本地 PDF 适配器的离线测试。
tests/documents/ingestion|来源注册、文献处理计划及 CSV 合并测试。
tests/documents/literature|文献搜索、下载验证及仓库布局测试。
tests/documents/schemas|统一 Article 格式测试。
tests/evidence|证据身份、工具行为和来源追溯测试。
tests/evidence/chunking|统一正文切分的测试。
tests/evidence/providers|规则/RAG与非文本 Evidence 工具的测试。
tests/evidence/preparation|从 Article 准备完整 Evidence 集的测试。
tests/extraction|逐条模型编排、消息构造和返回解析测试。
tests/presets|属性扩展、配置校验和 Tc 冻结基线测试。
tests/results|最终事实、材料恢复、Review 和评估测试。
tests/results/facts|材料名称恢复、变量和合并规则的测试。
tests/results/export|运行存储和 Review 导出测试。
tests/results/evaluation|严格评分与历史输入适配测试。
tests/fixtures|测试固定输入：出版社 XML 与冻结的模型消息，不是生产 Gold。
docs|面向使用、维护和验收的项目说明。
data|原始文献、历史运行、人工标准、报告和本地验证产物；不是安装包源码。
data/cache|可重新生成的本地缓存。
data/cache/pytest|pytest 运行缓存，如上次失败和测试节点列表。
data/gold|人工标准答案；普通抽取运行不应覆写。
data/gold/tc_001_030|常用前 30 篇论文的 Tc Gold、人工表格和论文 ID 对照。
data/literature|原始 PDF、文献发现结果、来源数据和文献处理工作区。
data/literature/acquisition|检索候选、下载记录和文献获取实验数据。
data/literature/legacy_metadata|迁移保留的旧文献元数据 CSV。
data/literature/pdfs|本地及下载 PDF 的输入仓库。
data/literature/recovered_001_030|前 30 篇历史恢复输入；目前还随数据保留一个旧离线处理脚本，已失配新包路径。
data/literature/validation_sample|用于少量本地验证的复杂论文 PDF。
data/literature/processing|单独运行 process-articles 时的处理工作区。
data/logs|当前程序日志。
data/maintenance|清理与收尾的快照、比较、校验日志和构建包。
data/maintenance/cleanup_20260906|第一次目录重构的备份和验收产物。
data/maintenance/cleanup_finish_20260906|清理收尾的备份、测试、哈希校验和新构建包。
data/metrics|单独保存的历史评估结果。
data/reports|人工审查、实验比较与实现说明。
data/reports/presentations|项目演示用 PPT 文件。
data/reports/project|项目报告的预留/归档目录；是否有文件以本次目录清单为准。
data/runs|按 run-id 隔离的各次运行输入、证据、模型输出和最终结果。
reference|不参与当前正式运行的历史实现、实验归档和一次性迁移脚本。
reference/legacy|未压缩的停用源码、配置和历史测试。
reference/legacy/comproscanner|旧包布局下保留的 CrewAI、数据库、可视化等实现，仅供参考。
reference/legacy/tests|旧流程的测试和样本，未纳入当前默认 pytest；其中还保留历史字节码缓存。
reference/maintenance|一次性迁移和说明生成脚本，不属于业务流程。
reference/maintenance/cleanup_20260906|大清理使用的迁移、归档、冻结消息及交付验证脚本。
reference/maintenance/file_inventory|生成当前逐文件用途说明的本地脚本。
""")

ROOT_FILES = mapping("""
README.md|项目总入口：目录、安装、基本命令和文档链接。
pyproject.toml|包名/版本、Python 和依赖要求、CLI 注册、打包范围、pytest 与格式化配置。
.env|本机实际 API 密钥和输入路径配置；本次只登记文件用途，不读取或展示内容。
.env.example|环境变量填写模板：模型密钥、出版社凭据、IOP 路径等；供配置新环境使用。
.gitignore|规定不进入 Git 的密钥、缓存、大型原文、运行资产和构建产物。
CHANGELOG.md|项目变更记录。
CONTRIBUTING.md|维护、开发、修改与验证约定。
LICENSE|项目开源许可证。
CITATION.cff|学术引用项目时使用的作者、名称等引用元数据。
""")

TESTS = mapping("""
conftest.py|设置离线环境、禁止普通测试建立网络连接、为每个测试隔离工作目录和输出。
test_canonical_pipeline_smoke.py|验证统一 Article→Evidence→抽取→结果的基本链路。
test_cleanup_contract.py|冻结完整模型消息，检查旧依赖隔离、扩展字段和论文元数据保留、preset 控制以及 Review→Gold。
test_preset_pipeline.py|验证不同属性共用通用流水线，属性差异由 preset 提供。
test_commands.py|验证 CLI 基础子命令及产物。
test_extract_guard.py|验证抽取必须满足执行条件，防止意外模型调用或覆盖。
test_process_articles.py|验证文献命令的计划模式、执行开关和输入传递。
test_run.py|验证端到端阶段顺序、恢复运行、输入变化检查及错误状态。
test_source_boundaries.py|验证陌生章节保留、Tc 关键词字典、IOP 原件保护与无元数据输入、DOI 路由和 CSV 失败上报。
test_elsevier_processor.py|验证 Elsevier 请求与 XML 解析、元数据、表格和异常重试；用替代响应执行。
test_springer_processor.py|验证 Springer 请求、JATS 解析和中间结果写出。
test_wiley_processor.py|验证 Wiley PDF 获取、解析和失败处理。
test_pdfs_processor.py|验证本地 PDF 标识、解析、元数据回退、失败记录和 CSV 输出。
test_iop_processor.py|当前此文件主要测试 PrepareIOPFiles：XML/ZIP 整理、DOI 和异常处理；完整入口边界另在 test_source_boundaries.py。
test_normalize.py|验证多来源 CSV 归一化、标识去重和图片路径处理。
test_process.py|验证文献处理计划、来源参数和执行调用。
test_source_registry.py|验证来源定义、格式、联网与凭据要求。
test_oa.py|验证开放获取候选解析、PDF 内容验证、哈希及下载行为。
test_scopus.py|验证 Scopus 检索条件与元数据规范化。
test_storage.py|验证原始文献仓库的 manual/downloaded 等目录布局。
test_article_csv.py|验证 Article 必需列、缺失值和历史 CSV 适配。
test_figure_identity.py|验证不同论文/图号不会产生冲突的图片 Evidence 身份。
test_text_chunker.py|验证段落/章节切分、超长段落、重叠和稳定 ID。
test_evidence_preparation.py|验证统一正文及表格、图片、公式的准备过程与工具开关。
test_figure_manifest.py|验证图片清单加载、路径、图题和位置元数据。
test_non_text_evidence.py|验证表格、图片和公式 Evidence 的选择与原始信息保留。
test_source_units.py|验证表格文本、显式公式和图片清单转换为来源单元。
test_text_evidence.py|验证规则与向量结果汇合，同一文本块保留多个检索来源。
test_vector_store.py|验证规范 chunk 与向量数据库适配器的建库、检索和返回映射。
test_evidence_flow.py|验证每条 Evidence 独立执行、拒绝分支、图片路线及错误隔离。
test_litellm_adapters.py|验证模型请求消息、返回 JSON 解析和图片输入格式。
test_tc_baseline.py|使用固定 SHA-256 检查 Tc 的关键词、科学提示词、查询和工具策略未变化。
test_strict.py|验证严格 TP/FP/FN/F1、多重项、条件/单位差异和正式通用适配器对历史 Tc 输入的处理。
test_article_materials.py|验证利用同文上下文恢复缩写、材料母配方和变量，防止跨样品误用。
test_fact_merger.py|验证保守合并、证据联合以及不同条件/限定的事实分离。
test_processors.py|验证材料处理器、规范化失败标记和单位/条件检查。
test_review.py|验证 Review 的原文 Evidence、材料信息和 XLSX 内容。
test_run_store.py|验证运行目录、原子输出与禁止越界/写 Gold。
""")

LEGACY = mapping("""
comproscanner.py|旧的一体化 ComProScanner 门面，曾连接检索、出版社、CrewAI、清洗、评估和数据库。
data_visualizer.py|旧数据分布图和知识图谱的对外包装函数。
eval_visualizer.py|旧评估柱图、雷达图、热图、混淆矩阵等绘图包装函数。
main_extraction_flow.py|旧 CrewAI Flow，组织材料识别、组成属性抽取/格式化和合成步骤抽取。
composition_extraction_crew.py|旧组成-属性抽取 Crew 和输出模型。
composition_format_crew.py|旧组成-属性格式化 Crew 和输出模型。
materials_data_identifier_crew.py|旧 yes/no 文献材料数据识别 Crew。
synthesis_extraction_crew.py|旧合成方法/步骤抽取 Crew。
synthesis_format_crew.py|旧合成数据格式化 Crew。
equation_tool.py|旧 agent 使用的公式/晶体结构图片辅助工具及模型选择实现。
graph_extractor_tool.py|旧从论文图像抽取数据的 agent 工具。
material_parser_tool.py|旧外部材料解析工具，处理配方、变量和接口返回。
rag_tool.py|旧 agent 的 RAG 工具，把向量检索文段交给模型组织答案。
fetch_metadata.py|旧文献元数据获取实现。
filter_metadata.py|旧元数据去重、无效记录清理及出版社补全实现。
data_cleaner.py|旧抽取结果清洗步骤集合，包括材料组成处理。
composition_evaluation_crew.py|旧通过模型判定组成-属性匹配的评估 Crew，含数值容差工具。
synthesis_evaluation_crew.py|旧合成方法、项目和步骤的模型评估 Crew。
eval_flow.py|旧 agentic 评估流程编排。
semantic_evaluator.py|旧语义匹配评估器；与当前严格评分口径不同。
create_knowledge_graph.py|旧知识图谱生成及语义匹配实现，可供以后 Neo4j 等扩展参考。
data_distribution_visualizers.py|旧材料家族、前驱体、表征技术等数据分布绘图实现。
eval_plot_visualizers.py|旧评估指标图表实现。
_legacy_tc.py|停用的 Tc 专用字段转换器；正式评估现在使用 results/evaluation/inputs.py。
curie_temperature_before_finish.py|收尾前 Tc 配置副本，包含当时未生效的 extraction_kwargs、旧格式化说明和示例。
candidate_context.py|旧候选文本与 RAG 上下文合并实现。
custom_dictionary.py|旧解析/清洗流程使用的自定义词典与常量。
database_config.py|旧数据库与输出表相关配置。
llm_config.py|旧多 agent 流程的模型和提示词配置对象。
data_preparator.py|旧文献章节和材料属性输入准备器。
database_manager.py|旧 MySQL、CSV、向量数据库混合管理器。
get_paper_data.py|旧按 DOI 读取论文数据/元数据的工具。
save_results.py|旧流程结果保存工具。
paper-dependencies.txt|旧论文复现实验依赖清单，不是正式包安装依赖入口。
archive_history.py|大清理时归档历史目录、逐文件校验字节后移除重复副本的脚本。
finish_cleanup.py|大清理结束时移除验证临时副本、归档测试产物并移动迁移脚本。
freeze_messages.py|从清理前适配器捕获固定模型消息，用作回归预期；不调用模型。
organize_data.py|将旧 PDF、Gold、运行与报告移动到 data 并记录路径迁移的脚本。
organize_tests.py|把旧测试按正式模块重新组织的脚本。
restructure.py|大清理的源码模块迁移、导入改写和旧流程隔离脚本。
split_cli.py|将原大型 CLI 文件按文献、证据、抽取、结果、编排拆分的脚本。
verify_delivery.py|检查保护文件哈希、wheel 内容、独立安装入口和文档链接的脚本；需要对应临时安装环境。
write_docs.py|生成第一次清理的 README、使用说明等文档的脚本。
generate_guide.py|只读盘点目录、提取源码定义和文件结构，生成本次逐文件说明和可搜索清单；不执行项目业务代码。
""")

DATA_NAMES = mapping("""
path_migrations.json|旧路径到新 data 位置的映射，供历史结果读取时定位资产。
gold_facts.json|人工标准事实，供评分时作 Gold。
gold_review.xlsx|人工 Gold 审查表，保留人工标注与核对信息。
paper_id_map.json|历史 paper_id 与运行 document_id 的对应关系。
article.csv|统一 Article 输入/中间表，保存正文、表格、图清单及文献信息。
article.md|这一篇文献保存的 Markdown/正文副本。
document.json|Docling 解析结构，包括文本、布局/位置引用和图片/表格等条目。
metadata.json|文献标识、来源和元数据的旁存文件。
original.pdf|为解析追溯保留的输入 PDF 原件副本。
run_config.json|本次运行的 preset、输入、工具和模型等配置；用于追溯与续跑检查。
stage_status.json|端到端各阶段状态、退出码及错误。
summary.json|本次运行/处理的汇总信息；字段以结构栏为准。
run_summary.json|一次历史检索或执行的汇总记录。
manifest.json|本目录的对象清单；运行层记录论文处理状态，资产层记录文件路径和导出情况，图片层记录图文关联。
all.json|该运行合并保存的全部 Evidence。
predictions.json|该运行的预测事实；是否已经材料恢复取决于运行阶段，不是人工 Gold。
predictions.csv|最终事实与论文元数据联表的 CSV 导出。
predictions.xlsx|最终结果工作簿，当前导出含 facts 和 papers 表。
review.xlsx|附 Evidence 的人工审查工作簿；模型输出尚需由人决定接受、拒绝或修改。
failures.json|运行阶段收集的失败项。
tool_usage.json|逐 Evidence 的工具/模型路线与执行状态记录；不一定是精确 token 账单。
metrics.json|该次评估的指标与错误项；需结合运行配置确认评分口径。
material_changes.json|材料恢复前后名称差异记录。
cleaning_report.json|历史实验的清洗/处理变更报告。
extraction_config.json|历史抽取实验的模型和策略配置。
extraction_failures.json|历史实验的抽取失败记录。
prepare_failures.json|历史实验的 Evidence 准备失败记录。
process_failures.json|历史实验的文献处理失败记录。
raw_results.json|历史模型/工具的原始结果，尚不能直接视为最终正确预测。
results.json|历史实验结果集合；以结构栏和同目录 summary 确认阶段。
raw_responses.json|历史模型原始响应留档。
live_report.json|小规模真实服务实验报告，不代表当前整条生产链路已验收。
paid_validation.json|历史付费小样本验证记录。
gold_comparison.json|历史预测与 Gold 对照结果；具体口径见结构及对应报告。
gold_comparison.csv|预测与 Gold 对照表的 CSV 版本。
gold_check_source_spans.json|人工 Gold 核查使用的原文段落/证据位置记录。
info.json|图片编号与标题说明的历史侧车文件。
download_manifest.csv|下载尝试、来源、文件位置等记录表。
corpus_manifest.csv|语料文件和来源的登记表。
scopus_candidates_500.csv|历史 Scopus 候选检索表，文件名表示候选批次目标规模。
scopus_candidates_500.json|历史 Scopus 候选检索记录的 JSON 版本。
review_shortlist_200.csv|历史候选文献审阅短名单。
review_shortlist_200.json|历史审阅短名单的 JSON 版本。
chroma.sqlite3|Chroma 向量库元数据与集合记录，必须和对应索引目录一起使用。
header.bin|向量索引的内部头信息；由向量库维护。
data_level0.bin|HNSW 向量索引的数据层；由向量库维护。
length.bin|向量索引内部长度记录；由向量库维护。
link_lists.bin|HNSW 索引的邻接关系；由向量库维护。
before_cleanup.zip|大清理之前的源码、测试与文档快照，含当时未提交内容。
before_finish.zip|小范围收尾之前的源码、测试与文档快照。
protected_hashes.json|受保护 Gold 和关键结果文件的 SHA-256 基准。
snapshot_manifest.json|清理前快照中各文件的哈希清单。
data_integrity.json|目录迁移后原文与关键结果的完整性检查摘要。
directory_moves.json|实际目录迁移记录。
module_map.json|旧源码模块到新模块的对应表。
final_layout.json|清理结束的根目录、临时目录移除及脚本迁移记录。
final_acceptance.json|实际 PDF 解析资产及关键文件完整性等最终检查结果。
history_archive.json|历史归档的文件数与逐文件字节校验记录。
environment.json|验证环境已安装的 Python 包与版本列表。
evidence_replay_comparison.json|相同输入/设置的清理前后 Evidence 比较结果。
material_replay_comparison.json|材料后处理前后版本的最终预测一致性比较。
verification.json|收尾源码变化、保护文件哈希和安装包检查结果。
git_status_before.txt|清理前工作区的 Git 修改状态，供恢复和审计。
""")

RUNS = mapping("""
cleanup_before_evidence_20260906|清理前源码快照在同一批 30 篇 Article 上重放 Evidence 的对照输出。
cleanup_evidence_replay_20260906|清理后同配置重放 30 篇 Evidence 的输出，用于比较一致性。
cleanup_docling_20260906|第一次实际 Docling 解析验收输出。
cleanup_docling_final_20260906|最终 Docling 本地验证输出，含论文标题及完整解析资产。
cleanup_material_replay_20260906|重放已有 4 日事实的材料恢复，保存 59 条最终预测及结果表。
cleanup_rag_20260906|第一次本地 PhysBERT 建库和查询验证。
cleanup_rag_final_20260906|收尾配置下的本地 PhysBERT 验证。
tc_fulltext_001_030_20260904|需要保留的 9 月 4 日前 30 篇抽取基线及后续历史附件。
tc_20260904_material_recovered_20260906|在 4 日事实基础上进行材料名称恢复并对照 Gold 的结果。
tc_baseline_targeted_20260906|针对历史问题 Evidence 的小范围重跑及审查记录。
tc_paper12_thinking_comparison_20260906|第 12 篇复杂材料的 thinking 对比实验记录。
tc_single_evidence_30_20260905|9 月 5 日逐 Evidence 的 30 篇准备/抽取与 Gold 比较产物。
tc_single_evidence_001_030_20260905|另一批以 001–030 命名的逐 Evidence 历史运行；以其配置和产物确认范围。
tc_final_001_030|此前前 30 篇结果整理目录；名称不表示它自动取代 4 日基线。
tc_hybrid_001_100|以 001–100 命名的历史候选文本/RAG 实验目录；不据名称推断已全部跑完。
""")

DOC_FILES = mapping("""
architecture.md|解释四模块、数据契约、证据路线和扩展边界。
presets.md|说明每个 preset 字段、属性配置方式与新增属性示例。
usage.md|提供输入、分阶段执行、材料恢复、Review→Gold 和评估命令。
cleanup.md|记录清理/收尾内容、回归证据、数据保留位置和未完成的生产验证边界。
file-guide.md|本次生成的阅读版：逐一说明正式代码、测试、参考文件及主要目录。
file-inventory.html|本次生成的完整静态目录清单：可搜索每个文件/文件夹、用途、结构依据与状态。
""")


def category(rel):
    first = rel.split('/')[0]
    if first == '.git': return 'Git 内部'
    if first == 'reference': return '历史参考'
    if first == 'tests': return '测试'
    if first == 'data': return '数据/产物'
    if '.egg-info' in rel or '__pycache__' in rel: return '安装/缓存'
    if first == 'src': return '正式代码'
    if first == 'docs': return '文档'
    return '项目配置'


def structure(path):
    """Only expose definitions/key names, never secrets or model/paper content."""
    if path.name.startswith('.env') or '.git' in path.relative_to(ROOT).parts:
        return ''
    try:
        if path.suffix == '.py':
            tree = ast.parse(path.read_text(encoding='utf-8-sig'))
            names = [n.name for n in tree.body if isinstance(n,(ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef))]
            return '定义：' + '、'.join(names[:12]) + (' 等' if len(names)>12 else '') if names else '包入口/导出或模块级脚本；无顶层类、函数。'
        if path.suffix == '.json' and path.stat().st_size < 12_000_000:
            value = json.loads(path.read_text(encoding='utf-8-sig'))
            if isinstance(value,dict):
                keys = list(value)[:9]
                # Skip free-form/hash/DOI dictionary keys; retain only schema-like names.
                keys = [k for k in keys if re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]{0,45}',str(k))]
                return ('JSON 字段：' + '、'.join(keys)) if keys else 'JSON 对象/映射。'
            if isinstance(value,list):
                keys = [k for k in (list(value[0])[:9] if value and isinstance(value[0],dict) else []) if re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]{0,45}',str(k))]
                return f'JSON 数组，{len(value)} 项。' + ('首项字段：'+'、'.join(keys) if keys else '')
    except (OSError,ValueError,SyntaxError,UnicodeError):
        return '未解析内容；用途依目录、格式和命名说明。'
    return ''


def git_purpose(rel, directory=False):
    if '/objects/' in rel: return 'Git 内容寻址对象/索引；保存历史提交、目录和文件内容，名称由哈希决定。'
    if '/hooks' in rel: return 'Git 操作钩子目录或示例脚本；不是论文处理入口。'
    if '/logs' in rel: return 'Git 引用变动日志，用于恢复历史位置。'
    if '/refs' in rel: return '分支、标签或远程跟踪引用。'
    name=Path(rel).name
    return {'HEAD':'当前检出的分支/提交引用。','index':'暂存区索引。','config':'本地仓库配置；未读取内容。','COMMIT_EDITMSG':'上次提交说明缓存。','description':'Git 仓库说明。','packed-refs':'打包保存的分支/标签引用。','exclude':'该仓库的本地忽略规则。','FETCH_HEAD':'最近获取的远程引用记录。','ORIG_HEAD':'危险/切换操作前保存的原 HEAD。'}.get(name,'Git 的本地状态或版本管理辅助记录，不参与项目业务。')


def folder_purpose(rel):
    if rel in FOLDERS: return FOLDERS[rel]
    if rel.startswith('.git/'): return git_purpose(rel,True)
    if '__pycache__' in rel: return 'Python/pytest 自动生成的字节码缓存；其中的 .pyc 不作为业务源码维护。'
    if rel.startswith('data/runs/'):
        parts=rel.split('/'); run=parts[2]
        if len(parts)==3:
            return RUNS.get(run,'历史独立运行目录。名称用于区分实验；是否实际成功、调用何种模型以本目录配置/状态为准。')
        tail=parts[-1]
        kinds={'evidence':'该运行的规范分块和各篇/全部 Evidence。','papers':'逐 Evidence 抽取检查点（文件夹名沿用 papers，不代表合并整篇抽取）。','processor_workspace':'该运行的文献解析工作区，保存原始/中间资产和解析器结果。','vector_db':'该运行独立的向量检索数据库。','documents':'按原 PDF 哈希保存的 Docling 解析原件和资产。','pages':'文献整页渲染图。','pictures':'Docling 识别的图片裁剪。','tables':'Docling 识别的表格图。','articles':'逐 Article 的 Markdown 与元数据旁存文件。','related_figures':'按文献组织的图片、图题和图片清单。','logs':'这次文献处理的日志/已处理记录。','results':'该运行中解析器沿用的中间结果目录。','extracted_data':'文献解析结果和关联资产；不是最终材料事实。','raw_responses':'该历史实验保留的模型原始响应。'}
        if tail in kinds:return kinds[tail]
        if 'vector_db' in parts:return f'运行 {run} 的文献集合或内部向量索引分区；由 Chroma 管理。'
        if 'related_figures' in parts:return f'运行 {run} 中这一文献的图片和标题资产。'
        if 'documents' in parts:return f'运行 {run} 按输入 PDF 内容哈希建立的资产目录。'
        if 'articles' in parts:return f'运行 {run} 按文献标识建立的 Article 旁存目录。'
        return f'运行 {run} 的阶段/来源子目录；文件用途见各条目。'
    if rel.startswith('data/literature/'):
        name=Path(rel).name
        roles={'manual':'手工放入的 PDF。','downloaded':'按获取来源分类的已下载 PDF。','normalized':'规范化文献输出的预留/使用目录。','quarantine':'下载验证不通过或待隔离检查的文件目录。','pdfs':'该批次保留的 PDF 输入。','discovery':'文献检索候选与筛选记录。','corpus':'文献仓库及其登记表。','oa_downloads':'开放获取下载文件和下载清单。','oa_expansion_500':'历史扩大开放获取候选范围的实验结果。'}
        return roles.get(name,'文献获取/历史来源批次或来源子目录；名称标识具体批次，文件用途见下级条目。')
    if rel.startswith('reference/legacy/'):
        if rel.endswith('/config'):return '对应旧 Crew 的 agent 角色和任务 YAML 配置。'
        return '旧流程的 '+Path(rel).name+' 子模块/历史测试目录，仅保留参考，不被正式包加载。'
    if rel.startswith('data/maintenance/'):
        return {'dist':'已构建的 wheel 安装包。','generated_test_outputs':'归档的测试临时输出。','data':'独立安装检查工作目录内生成的数据。','logs':'验证过程生成的日志。'}.get(Path(rel).name,'此轮清理/验收的辅助产物目录。')
    if rel.startswith('data/cache/'):return 'pytest 自动维护的缓存和状态分区。'
    parent=Path(rel).parent.as_posix()
    return '子目录：'+FOLDERS.get(parent,'组织同类文件，具体用途见目录内文件条目。')


def file_purpose(rel):
    p=Path(rel);name=p.name
    if '/' not in rel:return ROOT_FILES.get(name,'项目根目录文件。')
    if rel.startswith('.git/'):return git_purpose(rel)
    if name.endswith('.pyc'):return 'Python/pytest 为同名 .py 自动生成的字节码缓存；不是独立业务实现。'
    if rel.startswith('src/comproscanner/'):
        key=rel[len('src/comproscanner/'):]
        if key in CORE:return CORE[key]
        if name=='__init__.py':return '包标识与公共接口导出。所属目录用途：'+folder_purpose(p.parent.as_posix())
        raise ValueError('正式文件缺少明确用途：'+rel)
    if '.egg-info/' in rel:
        return {'PKG-INFO':'构建生成的包名称、版本、依赖和介绍等元数据。','SOURCES.txt':'setuptools 收集的发行包文件列表。','requires.txt':'安装工具生成的依赖与可选依赖清单。','entry_points.txt':'安装工具生成的命令行入口注册。','top_level.txt':'发行包提供的顶层 Python 包名。','dependency_links.txt':'安装工具的依赖链接元数据，当前通常为空。'}.get(name,'安装工具生成的包元数据。')
    if rel.startswith('.github/'):
        if name=='ci.yml':return 'GitHub CI：在 Python 3.12/3.13 安装正式依赖、跑离线测试并构建 wheel。'
        return {'bug_report.md':'缺陷反馈模板。','documentation.md':'文档问题反馈模板。','feature_request.md':'功能建议模板。','question.md':'一般问题模板。'}[name]
    if rel.startswith('docs/'):return DOC_FILES.get(name,'项目说明文档。')
    if rel.startswith('tests/'):
        if name=='test_registry.py':return '验证 preset 自动发现、独立属性与配置校验。' if '/presets/' in rel else '验证 Evidence 工具注册与选择。'
        if name=='tc_wire_messages.json':return '冻结的 7 组完整 Tc 模型请求消息；回归测试与其逐项比较，不是模型响应或 Gold。'
        if name.endswith('_test.xml'):return '对应出版社的固定 XML 响应样本，供离线解析测试。'
        if name in TESTS:return TESTS[name]
        raise ValueError('测试文件缺少明确用途：'+rel)
    if rel.startswith('reference/'):
        if name in LEGACY:return LEGACY[name]
        if name=='README.md':return '说明参考代码不参与当前运行、安装和正式测试，以及归档和恢复位置。'
        if name=='history.zip':return '归档的旧实验、示例、临时脚本和开发产物；压缩包作为一个物理文件登记，包内成员不在本次展开。'
        if name=='documentation_before_cleanup.zip':return '清理前文档站点、图片与自动发布配置的归档。'
        if name=='__init__.py':return '旧包/子包入口与导出，仅供了解历史模块结构；当前正式包不导入这里。'
        if name=='agents.yaml':return '上级旧 Crew 的 agent 角色、目标和背景提示词配置。'
        if name=='tasks.yaml':return '上级旧 Crew 的任务说明、输出要求和 agent 分工配置。'
        if '/tests/' in rel:
            if name=='conftest.py':return '旧测试的大范围依赖替身和通用夹具；正式测试已使用独立的新 conftest.py。'
            if name.startswith('test_'):return '历史测试：'+name.removeprefix('test_').removesuffix('.py')+'；验证对象和用例见定义栏，不参与当前默认测试。'
            if p.suffix in ('.xml','.pdf'):return '历史出版社测试输入样本。'
        return '停用模块的参考附件；按路径/格式标识，未确认更细的业务用途。'
    if rel.startswith('data/'):
        if name=='postprocess_existing.py':return '历史离线变量配方恢复脚本：读取 4 日预测与 Review，再从 PDF 补上下文。仍引用旧 comproscanner.facts 和 outputs/tmp 路径，不能当作当前入口直接执行。'
        if name in DATA_NAMES:return DATA_NAMES[name]
        if name.startswith('pdf_') and name.endswith('_paragraphs.csv'):return 'PDF 处理器写出的规范 Article/章节中间 CSV，供后续归一化。'
        if p.suffix=='.pdf':return '原始论文 PDF或该历史测试批次保留的副本；具体论文由文件名和文献登记表标识。'
        if p.suffix=='.pptx':return '项目演示文稿：'+p.stem+'；页数/版本标识来自文件名，本次未重新审阅幻灯片内容。'
        if p.suffix in ('.png','.jpg'):
            if '/pages/' in rel:return 'PDF 第 '+p.stem+' 页的整页渲染图，用于视觉追溯。'
            if '/pictures/' in rel:return 'Docling 识别的第 '+p.stem+' 个图片区域。'
            if '/tables/' in rel:return 'Docling 识别的第 '+p.stem+' 个表格区域图。'
            return '此文献/运行保留的图片裁剪；图题及来源关联见同目录 info.json 或 manifest.json。'
        if p.suffix=='.whl':return '该轮验收构建的 Python 安装包；可安装，不是可编辑源码目录。'
        if '/papers/' in rel and p.suffix=='.json':return '按文件标识保存的单条 Evidence 抽取检查点/响应，包含识别决定、抽取事实或错误；以结构栏区分旧格式。'
        if '/evidence/' in rel and p.suffix=='.json':return '这一篇文献或选定证据项的准备记录，可能包含 TextChunk、Evidence 和状态；字段见结构栏。'
        if p.suffix=='.jsonl':return '按行追加的历史执行/响应记录，一行一个 JSON 对象。'
        if p.suffix=='.log':return '此目录所属程序/实验的运行日志。'
        if p.suffix=='.txt':
            if 'processed_dois' in name:return '已处理 PDF/DOI 标记，供对应处理器避免重复解析。'
            if 'failed' in name or 'failures' in name:return '文献处理失败项目或失败文件名记录。'
            if 'tests' in name:return '对应验证阶段的 pytest 命令输出。'
            return '历史命令输出/验证记录：'+p.stem+'；具体结论应读取文件，不以文件名推定成功。'
        if p.suffix=='.md':return '人工或程序整理的历史说明/报告：'+p.stem+'；记录当时实验状态，不自动代表当前结果。'
        if p.suffix=='.xlsx':return '历史人工审查或预测对照工作簿：'+p.stem+'，与该目录的运行记录关联。'
        if p.suffix=='.csv':return '历史文献/实验中间表：'+p.stem+'；具体字段由表头定义。'
        if p.suffix=='.json':return '历史运行/验收的 JSON 附件：'+p.stem+'；具体结构见右侧，未根据名称断言实验成功。'
        if 'cache/pytest' in rel:return 'pytest 缓存元数据/节点记录，可由测试重新生成。'
        return '数据或运行辅助文件；用途按位置推断，尚未确认更具体的含义。'
    return '本地辅助文件；需结合所在目录判断用途。'


def rows():
    output=[]
    for current, dirs, files in os.walk(ROOT, followlinks=False):
        for name in sorted(dirs+files):
            path=Path(current)/name; rel=path.relative_to(ROOT).as_posix()
            if path.is_symlink() or path.is_junction():
                if name in dirs:dirs.remove(name)
                output.append({'path':rel,'kind':'链接','category':category(rel),'purpose':'目录/文件链接，未遍历外部目标。','details':'','bytes':0})
                continue
            directory=path.is_dir()
            output.append({'path':rel,'kind':'目录' if directory else '文件','category':category(rel),'purpose':folder_purpose(rel) if directory else file_purpose(rel),'details':'' if directory else structure(path),'bytes':0 if directory else path.stat().st_size})
    return sorted(output,key=lambda r:r['path'].casefold())


def file_link(rel):
    return '['+rel+'](<' + (ROOT/rel).as_posix()+'>)'


def write_guide(items):
    files=[r for r in items if r['kind']=='文件']; counts=Counter(r['category'] for r in files)
    ncode=sum(r['path'].startswith('src/comproscanner/') and r['path'].endswith('.py') for r in files)
    text=['# ComProScanner 文件与目录用途说明','',f'按 {datetime.now():%Y-%m-%d %H:%M} 的实际工作区生成。登记 {len(files)} 个物理文件、{sum(r["kind"]=="目录" for r in items)} 个目录，其中正式包 Python 文件 {ncode} 个。',
          '', '所有目录和文件均在 [完整可搜索清单](file-inventory.html) 中逐条列出。阅读版逐文件解释正式代码、测试、配置与可读参考代码；海量运行产物用同结构说明，完整清单仍为每个实际文件保留独立条目。',
          '', '清单只说明文件职责。JSON 结构栏只列字段名/数量，不展示论文全文、模型响应或密钥。`.env` 与 Git 配置不读内容；压缩包按物理文件登记，不展开包内成员。缓存和安装元数据也如实列出。',
          '', '## 先看整条链路','', 'PDF / 出版社来源 → `documents` → 统一 Article → `evidence`（一次切分、五个工具）→ `extraction`（每条证据独立调用模型）→ `results`（材料恢复、预测、Review、Gold、评估）。`presets` 提供属性知识，`cli` 负责接通各阶段。',
          '', 'Article 是一篇文章的统一数据记录，目前落在 CSV/旁存文件中；它不是另一个需要寻找的 article.py 类。Evidence 是来源证据；Fact 是抽出的材料-属性事实。',
          '', '## 根目录','', '| 路径 | 具体用途 |','|---|---|']
    for r in items:
        if '/' not in r['path']:text.append(f'| {file_link(r["path"])} | {r["purpose"]} |')
    for title,prefix in [('正式代码：逐文件','src/comproscanner/'),('正式测试：逐文件','tests/'),('文档与自动化','docs/'),('GitHub 配置','.github/'),('安装元数据','src/comproscanner.egg-info/'),('历史参考：逐文件','reference/')]:
        text += ['', '## '+title,'']
        subset=[r for r in items if r['path'].startswith(prefix) and r['kind']=='文件' and not r['path'].endswith('.pyc')]
        for parent in sorted({str(Path(r['path']).parent).replace('\\','/') for r in subset}):
            text += ['', '### '+parent,'',folder_purpose(parent),'','| 文件 | 具体用途 |','|---|---|']
            for r in subset:
                if Path(r['path']).parent.as_posix()==parent:
                    label=r['path'].split('/')[-1]
                    link='['+label+'](<'+(ROOT/r['path']).as_posix()+'>)'
                    text.append(f'| {link} | {r["purpose"].replace("|","/")} |')
    text += ['', '## 数据目录与每次运行','', '数据文件不是另一套流程代码。原 PDF、历史预测、Gold、图片和向量索引会随论文和运行次数增长；它们的体积不等于代码架构复杂度。', '', '| 目录 | 具体用途 |','|---|---|']
    for r in items:
        if r['kind']=='目录' and r['path'].startswith('data/') and len(Path(r['path']).parts)<=3:
            text.append(f'| {file_link(r["path"])} | {r["purpose"]} |')
    text += ['', '### 同一次运行中各文件的区别','', '| 文件/子目录 | 具体用途 |','|---|---|']
    for name in ['article.csv','run_config.json','manifest.json','stage_status.json','all.json','predictions.json','predictions.csv','predictions.xlsx','review.xlsx','failures.json','tool_usage.json','metrics.json','material_changes.json','gold_facts.json','gold_review.xlsx','paper_id_map.json','original.pdf','article.md','document.json','metadata.json','info.json','chroma.sqlite3','header.bin','data_level0.bin','length.bin','link_lists.bin']:
        text.append(f'| `{name}` | {DATA_NAMES[name]} |')
    text += ['', '`evidence/` 保存分块与 Evidence；`papers/` 保存逐 Evidence 检查点；`processor_workspace/` 保存来源解析中间产物；`vector_db/` 保存这次运行的向量库。相同文件名位于不同 run-id 下，代表不同实验，不可直接混用。',
          '', '### 清理验证产物：逐文件','', '| 文件 | 具体用途 |','|---|---|']
    for r in files:
        if r['path'].startswith('data/maintenance/'):text.append(f'| {file_link(r["path"])} | {r["purpose"]} |')
    text += ['', '## 哪些文件需要经常关注','', '- 新增属性：`presets/`，通常以 `band_gap.py` 为参考。', '- 跑整条流程：`cli/main.py` 和 `cli/run.py`。', '- 修改某个证据工具：`evidence/providers/`；切分规则只在 `evidence/chunking/text_chunker.py`。', '- 看模型到底收到什么：`presets/_shared.py`、属性 preset、`extraction/litellm_adapters.py`。', '- 修改材料恢复：`results/facts/materials.py` 与 `processors.py`。', '- 查结果和人工判断：对应 run 的 `predictions.json`、`review.xlsx`，以及 `data/gold/`。',
          '', '## 本次盘点发现的历史残留','', '`data/literature/recovered_001_030/postprocess_existing.py` 仍随历史数据保留，它引用旧包名和旧路径，不能作为当前入口。`reference/legacy/tests/` 中存在历史 `.pyc` 缓存；`src/comproscanner.egg-info/` 是安装生成信息。本次是用途说明，没有修改这些文件或业务逻辑。',
          '', '## 范围与更新','', '本清单为静态快照；新运行会增加文件。生成脚本在 `reference/maintenance/file_inventory/generate_guide.py`，只读取目录/定义/有限结构并重写这两份说明。Git 哈希对象、重复论文资产和每个运行 JSON 均可在完整清单搜索到；对仅按命名或位置判断的附件，已明确标注，不宣称逐篇验证科学内容。','']
    (DOCS/'file-guide.md').write_text('\n'.join(text),encoding='utf-8')


PAGE = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ComProScanner · 文件用途清单</title>
<style>body{margin:0;font:15px/1.65 system-ui,"Microsoft YaHei",sans-serif;background:#f4f6f9;color:#172735}main{max-width:1500px;margin:auto;padding:28px}h1{font-size:27px;margin:0}header{margin-bottom:22px}small,.hint{color:#566779}a{color:#155eb1}section{background:white;border:1px solid #dce3eb;border-radius:10px;padding:16px;margin-bottom:18px}.filters{display:flex;gap:10px;flex-wrap:wrap}input,select,button{font:inherit;border:1px solid #b9c7d5;border-radius:5px;padding:8px;background:white;color:inherit}input{flex:1;min-width:240px}button{cursor:pointer}button:disabled{opacity:.4;cursor:default}.chips{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}.chips button{font-size:13px;padding:4px 9px}.tablewrap{overflow:auto}table{border-collapse:collapse;width:100%;table-layout:fixed}th,td{text-align:left;border-bottom:1px solid #e1e7ee;padding:12px;vertical-align:top;overflow-wrap:anywhere}th{background:#edf2f7}th:nth-child(1){width:30%}th:nth-child(2){width:9%}th:nth-child(3){width:39%}th:nth-child(4){width:22%}code{font-size:13px}nav{display:flex;justify-content:space-between;align-items:center;gap:12px}#stats{margin:12px 0}footer{color:#637285;margin-top:20px}@media(max-width:800px){main{padding:14px}table{min-width:850px}h1{font-size:23px}}</style>
<main><header><h1>ComProScanner · 每个目录和文件的用途</h1><p>当前工作区静态快照 · <a href="file-guide.md">阅读版逐文件说明</a></p><p class="hint">文件用途依据实际源码、数据结构或所在目录。未读取 .env 内容；压缩包按一个物理文件登记。名称不等于验证结论。</p></header>
<section><div class="filters"><input id="query" aria-label="搜索文件或用途" placeholder="搜索路径、材料恢复、preset、Review、文件名…"><select id="category" aria-label="分类"><option value="">全部分类</option></select><select id="kind" aria-label="目录或文件"><option value="">目录和文件</option><option>目录</option><option>文件</option><option>链接</option></select><label><input type="checkbox" id="git" style="min-width:0">显示 Git 内部记录</label></div><div class="chips"><button data-prefix="src/comproscanner/">正式源码</button><button data-prefix="src/comproscanner/presets/">属性配置</button><button data-prefix="tests/">测试</button><button data-prefix="data/runs/">每次运行</button><button data-prefix="data/gold/">Gold</button><button data-prefix="reference/">历史参考</button><button id="clear">清除筛选</button></div><p id="stats"></p></section>
<section><nav><button id="prev">上一页</button><span id="page"></span><button id="next">下一页</button></nav><div class="tablewrap"><table><thead><tr><th>实际路径</th><th>类别</th><th>具体用途</th><th>结构依据</th></tr></thead><tbody id="rows"></tbody></table></div></section><footer id="footer"></footer></main>
<script id="inventory" type="application/json">__DATA__</script><script>
const data=JSON.parse(document.getElementById('inventory').textContent),$=id=>document.getElementById(id);let current=0,filtered=[];const size=80;
for(const name of [...new Set(data.map(x=>x.category))].sort()){const opt=document.createElement('option');opt.value=name;opt.textContent=name;$('category').append(opt)}
function filter(){const q=$('query').value.toLowerCase().trim(),cat=$('category').value,kind=$('kind').value;filtered=data.filter(r=>($('git').checked||r.category!=='Git 内部')&&(!cat||r.category===cat)&&(!kind||r.kind===kind)&&(!q||(r.path+' '+r.purpose+' '+r.details).toLowerCase().includes(q)));current=0;render()}
function render(){const total=data.filter(x=>x.kind==='文件').length;$('stats').textContent=`总计 ${total} 个文件、${data.length-total} 个目录/链接；当前匹配 ${filtered.length} 项。每页 ${size} 项。`;$('rows').replaceChildren();for(const r of filtered.slice(current*size,(current+1)*size)){const tr=document.createElement('tr');for(const value of [r.path,r.kind+' · '+r.category,r.purpose,r.details]){const td=document.createElement('td');td.textContent=value;tr.append(td)}$('rows').append(tr)}$('page').textContent=`第 ${current+1} / ${Math.max(1,Math.ceil(filtered.length/size))} 页`;$('prev').disabled=current===0;$('next').disabled=(current+1)*size>=filtered.length}
for(const id of ['query','category','kind','git'])$(id).addEventListener('input',filter);$('prev').onclick=()=>{current--;render()};$('next').onclick=()=>{current++;render()};for(const btn of document.querySelectorAll('[data-prefix]'))btn.onclick=()=>{$('query').value=btn.dataset.prefix;filter()};$('clear').onclick=()=>{$('query').value='';$('category').value='';$('kind').value='';$('git').checked=false;filter()};$('footer').textContent='所有内容均已嵌入本文件，离线可用，不发送搜索或目录数据。';filter();
</script></html>'''


def main():
    DOCS.mkdir(exist_ok=True)
    for name in ('file-guide.md','file-inventory.html'):
        if not (DOCS/name).exists():(DOCS/name).write_text('',encoding='utf-8')
    items=rows()
    write_guide(items)
    encoded=json.dumps(items,ensure_ascii=False).replace('<','\\u003c')
    (DOCS/'file-inventory.html').write_text(PAGE.replace('__DATA__',encoded),encoding='utf-8')
    assert len({r['path'] for r in items})==len(items)
    assert all(r['purpose'] for r in items)
    print(json.dumps({'files':sum(r['kind']=='文件' for r in items),'directories':sum(r['kind']=='目录' for r in items),'formal_python_files':sum(r['path'].startswith('src/comproscanner/') and r['path'].endswith('.py') for r in items),'guide':str(DOCS/'file-guide.md'),'inventory':str(DOCS/'file-inventory.html')},ensure_ascii=False))


if __name__=='__main__':main()
