# ComProScanner

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

包内另有少量日志、异常和历史路径解析支持文件。

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
- `papers/`：每条 Evidence 的抽取检查点和原始模型响应。
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

详见 [架构](docs/architecture.md)、[属性配置](docs/presets.md)、[命令与审查](docs/usage.md)、[清理验收](docs/cleanup.md)、[逐文件用途说明](docs/file-guide.md) 和 [完整可搜索清单](docs/file-inventory.html)。

本项目基于原 [ComProScanner](https://github.com/slimeslab/ComProScanner)。原作者信息、MIT 许可证和引用文件保留在仓库中。
