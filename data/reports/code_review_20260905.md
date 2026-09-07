# ComProScanner 代码审查（2026-09-05）

审查对象是当前工作区，包含未提交的新旧流程接线改动。目标保持为 PDF → 统一 Article → 可选的五种 Evidence 工具 → 每条 Evidence 独立进入旧抽取、格式化、材料恢复、清洗 → JSON/review。

这次没有修改业务代码，没有启动付费模型抽取。之前的 30 篇解析任务已确认没有残留进程。

## 检查范围和验证边界

- 对 `src` 下全部 107 个 Python 文件、约 31,204 行源码完成 AST/语法扫描及跨模块调用、异常、网络、配置和输出接口检索。
- 人工重点核查 CLI、解析器与 Article 适配、Evidence/切块/RAG、旧 Flow/Crew/工具、清洗、JSON/review/评估、依赖与打包；同时抽查文献获取、元数据、数据库、可视化与兼容 API。
- 在现有 `comproscanner` Conda 环境重新运行测试：738 passed，17 deselected。被排除的集成测试以及真实模型抽取质量，不在本次通过结论内。
- 离线构建 wheel 成功，并检查其内容；对以下多项边界构造了独立复现，不依赖真实 API。
- 全项目静态覆盖不等于每条执行路径已验证。测试大量模拟 CrewAI/LLM/数据库，不能以测试全绿代替真实依赖和业务正确性验证。

## 需要先处理的问题

### 1. [P1] 当前 Gold 不能直接用于新输出的严格评估（已复现）

位置：`src/comproscanner/evaluation/strict.py:28`、`src/comproscanner/cli/main.py:538`。

现有 Gold 使用数值 `paper_id`，大部分条目没有 property 字段，评分器默认属性为 `tc`。新输出使用 DOI/local-pdf document_id，属性为 `Curie temperature`。`_evaluate` 直接把双方送入评分器，没有应用 `paper_id_map.json`，也没有属性名映射。

复现：取 Gold 第一条 BiFeO3 / 1103 K，构造科学内容完全相同的新格式预测，得到 TP=0、FP=1、FN=1。

建议：在评估入口统一文章标识和 preset 属性标识，输出映射校验结果；不得通过修改原始 Gold 来掩盖接口不一致。

### 2. [P1] 逐 Evidence 输出与 Gold 的重复计数口径不一致（已复现）

位置：`src/comproscanner/cli/main.py:465`、`src/comproscanner/evaluation/strict.py:60`。

按 Evidence 保留重复事实是符合溯源需求的，但评分仍使用 Counter 多重集。相同事实由两条 Evidence 独立提取，而 Gold 只有一条时，第二条被计为 FP。复现：标识映射后，两条相同预测对一条 Gold 得到 TP=1、FP=1。

建议：保留原始逐 Evidence JSON/review；单独建立事实级评估视图，明确同文章同事实的去重规则，并同时报告原始条数和去重条数。不能把独立证据抽取的重复误认为科学错误。

### 3. [P1] Evidence 准备的 resume 会吞掉历史失败，也不校验输入变化（已复现）

位置：`src/comproscanner/cli/main.py:241`。

只要单篇缓存文件存在便复用，包括 `status=ERROR`。错误没有进入本次 failures，函数返回 0。复现：缓存内容为 ERROR，本次 manifest 仍为 ERROR，但 failures=[]、退出码=0。

同一 run 改变 Article 内容、provider 或切块设置后，prepare 的缓存也没有签名校验。抽取阶段虽然有单 Evidence 签名，仍无法纠正上游提供的过期 Evidence。

建议：只恢复成功且签名匹配的缓存；失败必须重试或明确保留失败状态。

### 4. [P1] 新预测生成后，resume 仍可能保留旧 review 和 metrics（已复现跳过机制）

位置：`src/comproscanner/cli/main.py:566`、`:712`、`:719`。

下游 stage 只看 COMPLETE 和文件存在，不看 predictions/Gold 是否变化。重试失败 Evidence、改变模型或替换 Gold 后，新 JSON 与旧 Excel/metrics 可能同时存在，程序仍报告成功。

建议：记录下游输入签名，或在预测/Gold 变化时使对应下游阶段失效。更新审核表时还需保留人工 decision/note。

### 5. [P1] 工具故障没有隔离，关闭图片工具也可能被图片文件阻断（已复现）

位置：`src/comproscanner/pipeline/evidence_preparation.py:162`、`src/comproscanner/cli/main.py:256`。

`prepare_all` 在检查启用状态之前就读取图片清单、解析表格和公式。仅启用 rule_text，提供有效正文和损坏的图片 JSON，仍抛出 JSONDecodeError。CLI 按整篇捕获异常，已经找到的文本证据也丢失。

同样，向量索引/查询抛错后整篇进入 ERROR，规则 Evidence 不会保留。这削弱了五个工具独立开关的实际效果。

建议：仅执行启用工具的准备工作；按工具记录失败，保留其他成功工具的 Evidence，并明确是否允许部分成功。

### 6. [P1] 旧输出结构无法完整表达新 Fact 支持的科学语义（接口确认）

位置：`src/comproscanner/extract_flow/crews/composition_crew/composition_format_crew/composition_format_crew.py:22`、`src/comproscanner/cli/main.py:475`。

旧结构为 material → 单个数值，整条响应共享一个 property_unit，没有逐事实 qualifier/conditions。一个 Evidence 同时报告同材料在不同条件下的两个值，或同时含 K 与 °C，不能完整装入这一结构。范围、约数和上下限同样没有明确字段。当前转 Fact 时 qualifier 和 conditions 均未传递。

这是旧结构的限制，不是逐 Evidence 独立调用能够自动解决的问题。建议继续复用科学提示词和工具，但在适配处明确保留这些语义，或将不能无损转换的输出标为待审核，避免静默丢失。

### 7. [P1] 材料解析 API 没有超时，会阻塞整个串行批次（代码确认）

位置：`src/comproscanner/extract_flow/tools/material_parser_tool.py:114`。

`requests.post(url, files=files)` 没有 timeout；CLI 的模型 timeout 不控制这个 requests 请求。远端挂起时，一条 Evidence 即可使后续全部等待。多个获取/解析模块还使用无上限重试，例如 `utils/pdf_to_markdown_text.py:229`、`metadata_extractor/fetch_metadata.py:147`。

建议：给工具配置连接/读取超时、有限重试和可识别的失败状态，避免长期运行依赖人工强制停止。

### 8. [P1] 非法模型输出可能被缓存为正常的空结果（代码确认）

位置：`src/comproscanner/extract_flow/main_extraction_flow.py:592`、`src/comproscanner/pipeline/legacy_extraction.py:68`。

旧 JSON 解析器在解析失败时返回默认空字典，Identifier 默认 no。新适配器只检查结果是否为 dict 且有 composition_data。这样格式错误与确实无数据难以区分，空结果可能被成功缓存；后续 resume 不会再试。图片/公式工具返回错误字符串时也缺少统一向外传播的错误状态。

建议：区分 NO_DATA、PARSE_ERROR、TOOL_ERROR；原始响应和失败原因应保存，只有合法无数据结果才可作为成功缓存。

## 其他已确认问题

### 9. [P2] 切块长度上限和零重叠设置失效（已复现）

位置：`src/comproscanner/chunking/text_chunker.py:82`。

切块时先把完整上一句加入 overlap，再判断长度；overlap_words=0 也会保留一句。拼接新句后不再限制 max_words。复现 max_words=10、overlap_words=0，得到长度 7、14、14。更长单句也可能直接超过上限。影响上下文长度、重复提取和费用估算。

### 10. [P2] 缺少标识的不同文章可能被静默去重丢失（已复现）

位置：`src/comproscanner/schemas/article_csv.py:58`、`src/comproscanner/ingestion/normalize.py:43`。

无 doi/paper_id 时统一生成 paper_000，合并时按 document_id 保留第一条。两个不同的合法 CSV 输入只剩一篇。即使有真实 DOI，同文不同来源内容也只是保留第一份，没有选择完整版本或合并来源。建议无标识时使用文件哈希/来源生成稳定唯一 ID，并报告重复处理决策。

### 11. [P2] 化学式分数被提前截成两位小数（已复现）

位置：`src/comproscanner/post_processing/data_cleaner.py:639`。

Ba1/3Sr2/3TiO3 被清洗为 Ba0.33Sr0.67TiO3。不是单纯排版变化，会改变组分精度及材料匹配键。建议将内部精度与显示精度分开，保留原始表达或更高精度系数。

### 12. [P2] 发布 wheel 缺失全部 Crew 配置（已验证构建产物）

位置：`pyproject.toml` 的 setuptools 打包配置；各 Crew 的 config 目录。

离线 wheel 构建成功，但包内 YAML 数量为 0，源码共有 14 个 YAML。旧 Crew 依赖这些 agents/tasks 配置。editable 安装可从源码读取，因而现有环境和测试不暴露问题；普通 wheel 安装缺少运行配置。

建议：显式声明 package-data，并增加安装产物中的配置读取检查。

### 13. [P2] 注册新 provider 不足以让它真正执行（已复现）

位置：`src/comproscanner/pipeline/evidence_preparation.py:106`。

registry 能接受 custom，名称校验也通过，但管线仅实例化并调用四个固定名称，PhysBERT 另由 CLI 处理。复现 custom 工厂从未被调用，也不报错。现有五种工具可以选择，但不能把“已注册”视为“已接入”。

### 14. [P2] 清洗后的名称被展示为 material_reported（代码确认）

位置：`src/comproscanner/cli/main.py:476`、`src/comproscanner/results/review.py:52`。

material_reported 与 material_normalized 均填清洗后名称。predictions 附加了 scope 说明，但 review 丢弃该说明，审阅者容易误以为 reported 是原始模型/论文名称。raw_results 在格式化之后保存，也没有保留抽取 Crew 格式化前的完整响应。建议明确区分原文、抽取、恢复、清洗名称，至少避免审核表列名误导。

### 15. [P2] 部分可选依赖仍通过公共模块强制导入（代码确认）

位置：`src/comproscanner/utils/database_manager.py:25`、`src/comproscanner/comproscanner.py:19`、`pyproject.toml:45`。

RAG 路径导入 VectorDatabaseManager 时，database_manager 同时导入 mysql.connector；但 mysql-connector-python 只在 database/all extras 中。仅安装 rag 不足以运行该路径。原始解析入口也先导入 CrewAI/清洗/评估模块，导致只安装 pdf 未必能解析 PDF。当前完整 Conda 环境掩盖了这些组合问题。

### 16. [P2] 新增 preset 时，部分配置会被适配器覆盖或静默忽略（代码确认）

位置：`src/comproscanner/pipeline/legacy_extraction.py:25`、`:35`、`:57`。

配置先按 DataExtractionFlow 构造签名过滤，然后覆盖模型、identifier_context_mode、vision 设置；synthesis_text_data 固定为空。模型 CLI 默认值也不来自任意 preset。新增属性的科学提示词可以复用，但不能把 preset 的所有旧配置都视为有效。应明确支持的配置契约，对不支持的字段报错，而不是默默丢弃。

### 17. [P2] 批量运行没有可靠的实际 API 消耗记录（代码确认）

位置：`src/comproscanner/cli/main.py:451`。

tool_usage.json 目前只是成功 Evidence 和 resumed 标记，不记录 identifier/extractor/formatter 各自请求次数、token、工具失败或费用。旧 Crew 工具循环可能导致一次 Evidence 多次调用，因此无法用 Evidence 数量推断实际费用。建议至少保存各步骤调用次数、token 和重试数，预算信息不能以文件名 tool_usage 替代。

## 仍存在但默认主链已避开的旧问题

- `facts/processors.py:103` 的 VariableCompositionNormalizer 仍可能从上下文挑错母体化学式；此前已复现明确报告 BiFe1-xCrxO3 却被替换为另一固溶体。默认 legacy 不再使用它，但显式选择 variable-local 仍有风险。
- `facts/models.py:48` 的 merge_key 不包括 conditions，原 merge_facts 路径可能丢失条件。当前逐 Evidence 主输出不调用该合并函数，但公共 Fact 合并 API 仍有此问题。
- GraphExtractorTool 仍要求图中值输出整数；对需要小数精度的新属性，单加 preset 无法覆盖这个工具内部要求。
- 文本 chunk 的页面字段目前通常为空，full_text 路径也将正文统一标为 full_text；review 有原文但不能保证提供页码或原章节。

## 本轮排除/确认正常的项目

- 当前抽取调用单位确为单条 Evidence，新建独立 Flow，不再按文章拼接输入；相同 chunk 的规则/RAG 多来源保留在 retrieval_methods。
- 新抽取缓存以 Evidence 和配置生成签名，旧文章包缓存不会混用；抽取失败项会重试。缺陷主要还在 prepare 和下游 review/metrics。
- JSON 主存储采用临时文件加 os.replace，且写路径受 run 目录约束。
- 没有把清洗器的 eval 直接认定为任意代码执行：当前有算术字符筛选。表达式资源限制仍可改进，但本轮没有执行危险载荷。
- 本机 CLI 导入后可以读取 .env 配置；未将未复现的“完全不加载 .env”列为问题。

## 修复顺序建议

先修评估标识/去重口径、prepare 恢复状态、下游结果失效和工具隔离，再处理超时、错误传播和科学字段保真。随后补切块、材料精度、打包与依赖测试。以上以局部修补为主，不需要推翻当前流程，也无需先做目录净化。

本次发现包含前面接线改动引入或尚未补齐的问题；先前“测试通过/流程接通”只证明基本调用可达，并不代表这些业务边界已正确。
