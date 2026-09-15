# 命令与人工审查

## 输入

### DOI 检索与 PDF 获取

`discover` 检索 Scopus，`discover-openalex` 检索 OpenAlex。
两个检索来源的查询语法不同；请记录检索词、年份和抽样方式，不将测试集当作主题全集。
运行前在本机环境中加载 `.env`，不要把 Key 写入命令或结果文件。

```bash
comproscanner discover --query "TITLE-ABS-KEY(multiferroic* AND magnetoelectric*)" --start-year 2020 --end-year 2026 --limit 50 --shortlist 50 --output data/literature/acquisition/scopus --execute-network
comproscanner discover-openalex --query "multiferroic magnetoelectric" --start-year 2020 --end-year 2026 --max-records 50 --shortlist 50 --output data/literature/acquisition/openalex --execute-network
comproscanner acquire-pdfs --candidates data/literature/acquisition/scopus/candidates.json --candidates data/literature/acquisition/openalex/candidates.json --limit 50 --max-archive-requests 50 --output data/literature/acquisition/combined --execute-network
```

`acquire-pdfs` 按 DOI 合并来源并交替选择，先尝试 OpenAlex 报告的公开 PDF 地址，再尝试缓存。
缓存使用 `OPENALEX_API_KEY`；每次缓存请求开始前持久化预算，默认最多 50 次。
目录内 `pdfs/` 只存身份校验通过的文件；待核对文件进入 `quarantine/`。
`manifest.csv/json` 记录每篇状态，`remaining_dois.txt` 保存全部待下载 DOI，`browser_input/` 按出版社生成 InstSci 输入。
该步骤只验证 PDF 获取，不执行 Docling 或付费属性抽取。

```bash
instsci papers data/literature/acquisition/combined/browser_input/elsevier.txt --publisher elsevier --institution "Harbin Institute of Technology" --output data/literature/acquisition/combined/browser/elsevier --no-retry
```

InstSci 是独立安装的下载工具。当前版本的 `--publisher auto` 要求同一批 DOI 属于同一出版社，不能直接处理混合清单；按 `browser_input/` 分组运行，unknown 留待人工确认。机构登录、验证码由用户完成，出版社批量访问需符合对应授权。
将其包含 `doi` 和 `pdf_path` 的结果列表或 `results` 汇总 JSON 传给 `acquire-pdfs --browser-manifest <文件>`，其余参数保持一致，即可本地校验并合并到同一结果清单，不再联网。
相同输出目录续跑会跳过已有有效 PDF 和已尝试下载地址；失败重试使用明确的新运行目录。
PDF 身份采用前两页 DOI 或长标题词匹配，属于自动初验；无文本、补充材料或无法匹配的文件保留待核对。
下载后使用下面的 `downloaded_pdf` 入口进入现有 Article 流程。

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
