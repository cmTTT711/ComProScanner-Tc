# 四个模块与数据边界

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
