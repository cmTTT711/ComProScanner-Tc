# 2026-09-06 项目清理验收

本次交付把正式代码组织为四个业务模块，另设统一 CLI 和 presets。没有重新设计 Tc 科学策略，也没有把之前实验中的新结果混入 9 月 4 日基线。

## 已完成

- `documents`：本地／下载 PDF、出版社格式适配、Docling Markdown、统一 Article 和原始资产保存。
- `evidence`：统一正文切分，候选文本、PhysBERT、表格、图片、公式五个可插拔工具。
- `extraction`：每条 Evidence 独立识别和抽取；图片经过视觉解读。保留响应与检查点。
- `results`：既有材料展开和名称恢复、保守合并、JSON／CSV／XLSX、附 Evidence 的 Review、人工 Review 导入新 Gold、严格评估。
- `presets`：属性关键词、RAG 查询、模态选择、模型及请求参数、角色提示词、输出字段、单位与条件规则、评估字段映射集中管理。新增常规属性无需修改流程或注册表。
- `reference`：旧 CrewAI、数据库、可视化、旧评估及历史实验独立保存。正式模块不导入它们，安装包不包含它们。

修复了与入口可靠性有关的旧问题：XML 关键词字典兼容、陌生章节正文丢失、IOP 无元数据无法处理及 DOI 下划线识别、原始目录整理副作用、压缩包图片丢失、多出版社未标注 DOI 被跳过、CSV 写入失败被吞掉。PDF 解析另存完整原件、结构与图片，并恢复可识别的论文标题。这些属于文献入口和输出可靠性修复；对已保存 Evidence 的抽取策略不变。

## 验证证据

| 检查 | 结果 |
|---|---|
| 首次清理的默认本地测试 | 264 通过，8 项依赖外部条件的 integration 测试未默认执行；收尾结果见下文 |
| 清理前源码快照与新代码，处理同一批 30 篇 Article | 均生成 716 条 Evidence，逐字段完全一致；固定相同非 RAG 工具集合比较 |
| Tc 完整模型消息回归 | 文本、表格、公式、图片解读后抽取共 7 组消息保持一致 |
| 4 日已有事实重新执行材料后处理 | 61 条输入 → 59 条最终预测，与清理前材料恢复结果逐字段完全一致 |
| 最终 PDF 入口实跑 | 1 篇复杂论文，10 页页面图、19 张图片／表格图、14 条入选文本 Evidence，资产导出错误为 0，标题已保留 |
| 本地 PhysBERT 实跑 | 实际加载模型，建库、两次查询成功，形成 6 条文本 Evidence |
| 出版社适配 | 离线 XML、路由、PDF 与图片测试通过；IOP 无元数据本地输入实跑，原件哈希不变 |
| Gold 与关键基线 | 20 个受保护文件 SHA-256 一致；234 份原 PDF 经目录迁移保留 |
| 发布包 | wheel 构建及独立安装目录的 CLI 检查通过；正式包无旧数据库／CrewAI 模块 |
| 付费模型 | 本次清理调用 Qwen／DeepSeek **0 次** |

原历史 Evidence 曾使用过不同分块／RAG 运行状态，因此验收比较的是**清理前源码快照与清理后源码在相同输入、相同设置下的输出**，不把不同历史实验文件的差异归因于此次清理。

可直接检查：

- [离线回归日志](../data/maintenance/cleanup_20260906/final_tests.txt)
- [716 条 Evidence 的比较](../data/maintenance/cleanup_20260906/evidence_replay_comparison.json)
- [59 条预测的比较](../data/maintenance/cleanup_20260906/material_replay_comparison.json)
- [最终 PDF 和原件验收](../data/maintenance/cleanup_20260906/final_acceptance.json)
- [最终结果表](../data/runs/cleanup_material_replay_20260906/predictions.xlsx)、[Review](../data/runs/cleanup_material_replay_20260906/review.xlsx)

## 保留的数据与恢复方式

历史运行在 `data/runs/`，Gold 在 `data/gold/`，PDF 和来源文件在 `data/literature/`，审查报告与 PPT 在 `data/reports/`。读取旧记录时通过 `data/path_migrations.json` 解析原路径，不重写历史事实或 Evidence。

清理前源代码、测试、文档和配置快照共 263 个文件，包含当时未提交的工作：`data/maintenance/cleanup_20260906/before_cleanup.zip`。同目录保留原 Git 状态、逐文件哈希、模块与目录迁移记录、验证日志和测试环境包版本。

历史实验、示例和开发产物归档到 `reference/history.zip`，归档后逐文件校验原始字节再移除重复目录；外部依赖的目录链接只记录链接，不归档或删除外部依赖本体。一次性迁移脚本放在 `reference/maintenance/`。原 `.env` 未改动。

## 已知边界

### 收尾补充

随后的小范围收尾移除了不生效的 `extraction_kwargs`、未使用的旧格式化提示词与示例、出版社空表占位对象和无效的附加图片关键词参数。`_legacy_tc.py` 已归档，历史 Tc 输入测试直接验证正式 CLI 使用的通用 `adapt_records`，不再维护重复实现。修正了图片保存与 RAG 编排的过时注释，并修复 Elsevier 请求异常重试时引用未定义成员变量的问题。

收尾后 **265 项测试通过、8 项 integration 测试未默认执行**，日志见 [tests.txt](../data/maintenance/cleanup_finish_20260906/tests.txt)。Tc 科学规则哈希及 7 组完整模型消息使用原有冻结基准，未重新生成预期值。安装包已重新构建并核对当前源码，20 个受保护结果文件哈希一致；详见 [收尾校验记录](../data/maintenance/cleanup_finish_20260906/verification.json)。此次未调用付费模型，也未改动历史 Gold 或预测。

### 生产验证范围

这次验收证明本地链路、接口和已固定结果的兼容性，不等于每个材料名、OCR 或科学判断都正确。此前 Gold 审查中的 FN、材料恢复不完整和少数可疑 Tc 仍然保留，不能因目录清理而宣称准确率改善。

没有重新付费抽取 30 篇，也没有逐一验证出版社线上接口、权限和第三方服务当前可用性。`band_gap` 已验证通用接口可运行，其真实论文准确率尚未评测。

历史 43/45 是温度事件覆盖，严格材料事实 F1 使用另一套判定口径，两者不可互相替代。增加新属性时仍应使用该属性自己的 Gold 验证科学质量。
