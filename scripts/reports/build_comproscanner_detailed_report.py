"""Build the offline Chinese architecture and workflow report for this workspace."""

from __future__ import annotations

import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "pdf" / "ComProScanner_项目全流程与代码详解_2026-08-29.pdf"
FONT = Path(r"C:\Windows\Fonts\msyh.ttc")
FONT_BOLD = Path(r"C:\Windows\Fonts\msyhbd.ttc")
PAGE_W, PAGE_H = A4

pdfmetrics.registerFont(TTFont("CN", str(FONT)))
pdfmetrics.registerFont(TTFont("CN-Bold", str(FONT_BOLD if FONT_BOLD.exists() else FONT)))

NAVY = colors.HexColor("#17324D")
BLUE = colors.HexColor("#276B9A")
CYAN = colors.HexColor("#DCEEF7")
PALE = colors.HexColor("#F4F7FA")
GOLD = colors.HexColor("#F0B44D")
RED = colors.HexColor("#A63D40")
GREEN = colors.HexColor("#367B5B")
MID = colors.HexColor("#64748B")


class ReportDoc(BaseDocTemplate):
    def __init__(self, filename: str):
        super().__init__(
            filename,
            pagesize=A4,
            leftMargin=18 * mm,
            rightMargin=18 * mm,
            topMargin=18 * mm,
            bottomMargin=17 * mm,
            title="ComProScanner 项目全流程与代码详解",
            author="ComProScanner project technical report",
        )
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="normal")
        self.addPageTemplates(PageTemplate(id="main", frames=frame, onPage=self._page))

    def _page(self, canvas, doc):
        canvas.saveState()
        if doc.page > 1:
            canvas.setStrokeColor(colors.HexColor("#CBD5E1"))
            canvas.line(18 * mm, 14 * mm, PAGE_W - 18 * mm, 14 * mm)
            canvas.setFont("CN", 7.5)
            canvas.setFillColor(MID)
            canvas.drawString(18 * mm, 9.5 * mm, "ComProScanner｜项目全流程与代码详解｜2026-08-29")
            canvas.drawRightString(PAGE_W - 18 * mm, 9.5 * mm, str(doc.page))
        canvas.restoreState()

    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph):
            level = getattr(flowable.style, "toc_level", None)
            if level is not None:
                text = flowable.getPlainText()
                key = f"h-{self.seq.nextf('heading')}"
                self.canv.bookmarkPage(key)
                self.canv.addOutlineEntry(text, key, level=level, closed=False)
                self.notify("TOCEntry", (level, text, self.page, key))


base = getSampleStyleSheet()
styles = {
    "body": ParagraphStyle(
        "body", parent=base["BodyText"], fontName="CN", fontSize=9.2,
        leading=15, textColor=colors.HexColor("#263746"), alignment=TA_JUSTIFY,
        spaceAfter=5,
    ),
    "small": ParagraphStyle(
        "small", parent=base["BodyText"], fontName="CN", fontSize=7.7,
        leading=11.5, textColor=colors.HexColor("#405466"), spaceAfter=3,
    ),
    "h1": ParagraphStyle(
        "h1", parent=base["Heading1"], fontName="CN-Bold", fontSize=19,
        leading=26, textColor=NAVY, spaceBefore=8, spaceAfter=10, keepWithNext=True,
    ),
    "h2": ParagraphStyle(
        "h2", parent=base["Heading2"], fontName="CN-Bold", fontSize=13.5,
        leading=19, textColor=BLUE, spaceBefore=9, spaceAfter=6, keepWithNext=True,
    ),
    "h3": ParagraphStyle(
        "h3", parent=base["Heading3"], fontName="CN-Bold", fontSize=10.5,
        leading=15, textColor=NAVY, spaceBefore=6, spaceAfter=4, keepWithNext=True,
    ),
    "callout": ParagraphStyle(
        "callout", parent=base["BodyText"], fontName="CN", fontSize=9,
        leading=14, textColor=NAVY, backColor=CYAN, borderColor=BLUE,
        borderWidth=0.7, borderPadding=8, spaceBefore=5, spaceAfter=8,
    ),
    "warning": ParagraphStyle(
        "warning", parent=base["BodyText"], fontName="CN", fontSize=9,
        leading=14, textColor=RED, backColor=colors.HexColor("#FFF4E5"),
        borderColor=GOLD, borderWidth=0.7, borderPadding=8, spaceBefore=5, spaceAfter=8,
    ),
    "code": ParagraphStyle(
        "code", parent=base["Code"], fontName="CN", fontSize=7.7,
        leading=11.5, textColor=colors.HexColor("#183047"), backColor=PALE,
        borderPadding=6, leftIndent=5, rightIndent=5, spaceAfter=6,
    ),
    "cover_title": ParagraphStyle(
        "cover_title", fontName="CN-Bold", fontSize=28, leading=39,
        textColor=colors.white, alignment=TA_LEFT,
    ),
    "cover_sub": ParagraphStyle(
        "cover_sub", fontName="CN", fontSize=12, leading=19,
        textColor=colors.HexColor("#DCEEF7"),
    ),
}
styles["h1"].toc_level = 0
styles["h2"].toc_level = 1


def P(text: str, style: str = "body") -> Paragraph:
    return Paragraph(text, styles[style])


def H(text: str, level: int = 1) -> Paragraph:
    return P(text, f"h{level}")


def bullet(text: str) -> Paragraph:
    return Paragraph(f"• {text}", ParagraphStyle(
        "bullet-tmp", parent=styles["body"], leftIndent=11, firstLineIndent=-7,
        spaceAfter=3,
    ))


def table(rows, widths=None, header=True, font=7.7):
    converted = []
    for ri, row in enumerate(rows):
        converted.append([
            Paragraph(str(cell), ParagraphStyle(
                f"cell-{ri}", parent=styles["small"], fontName="CN-Bold" if header and ri == 0 else "CN",
                fontSize=font, leading=font * 1.45, textColor=colors.white if header and ri == 0 else colors.HexColor("#263746"),
            )) for cell in row
        ])
    t = Table(converted, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    commands = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if header:
        commands.append(("BACKGROUND", (0, 0), (-1, 0), NAVY))
        if len(rows) > 1:
            commands.append(("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE]))
    t.setStyle(TableStyle(commands))
    return t


def flow(labels, caption=None):
    row = []
    widths = []
    usable = 174 * mm
    arrow_w = 5 * mm
    box_w = (usable - arrow_w * (len(labels) - 1)) / len(labels)
    for i, label in enumerate(labels):
        row.append(P(label, "small"))
        widths.append(box_w)
        if i < len(labels) - 1:
            row.append(P("→", "small"))
            widths.append(arrow_w)
    t = Table([row], colWidths=widths)
    style = [("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (0, 0), (-1, -1), "CENTER")]
    for i in range(0, len(row), 2):
        style += [("BACKGROUND", (i, 0), (i, 0), CYAN), ("BOX", (i, 0), (i, 0), 0.7, BLUE), ("LEFTPADDING", (i, 0), (i, 0), 5), ("RIGHTPADDING", (i, 0), (i, 0), 5), ("TOPPADDING", (i, 0), (i, 0), 7), ("BOTTOMPADDING", (i, 0), (i, 0), 7)]
    t.setStyle(TableStyle(style))
    result = [t, Spacer(1, 4)]
    if caption:
        result.append(P(caption, "small"))
    return result


def section_intro(title, text):
    return [H(title), P(text, "callout")]


def load_metrics():
    p = ROOT / "outputs" / "tc_hybrid_qwen_001_030" / "strict_metrics_001_030.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def load_progress():
    pdir = ROOT / "outputs" / "tc_hybrid_qwen_001_030" / "papers"
    counts = {}
    ids = []
    if pdir.exists():
        for p in pdir.glob("paper_*.json"):
            obj = json.loads(p.read_text(encoding="utf-8"))
            counts[obj.get("status", "UNKNOWN")] = counts.get(obj.get("status", "UNKNOWN"), 0) + 1
            ids.append(int(obj.get("paper_id", 0)))
    return counts, max(ids) if ids else 0


def build_story():
    m = load_metrics()
    progress, max_id = load_progress()
    story = []

    # Cover
    cover = Table([[P("ComProScanner", "cover_title")], [P("从 PDF、API 文献发现到材料—性质数据库的完整技术报告", "cover_sub")], [Spacer(1, 8 * mm)], [P("原论文中文精读｜当前 Tc 改造｜目录与逐文件职责｜数据路径｜评测与扩展", "cover_sub")]], colWidths=[174 * mm], rowHeights=[35 * mm, 21 * mm, 8 * mm, 30 * mm])
    cover.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), NAVY), ("LEFTPADDING", (0, 0), (-1, -1), 14 * mm), ("RIGHTPADDING", (0, 0), (-1, -1), 14 * mm), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    story += [Spacer(1, 22 * mm), cover, Spacer(1, 15 * mm)]
    story.append(P("项目位置：F:\\Python_Project\\ComProScanner<br/>分支：magnetic-scientific-facts<br/>报告快照：2026-08-29（Asia/Shanghai）", "callout"))
    story.append(P("阅读目标：读完后应能亲自解释输入文件放在哪里、每一步由哪个模块负责、数据为何可能漏掉、JSON 与数据库在哪里，以及如何用最小改动增加 Ms 等新性质。", "body"))
    story.append(PageBreak())

    story += section_intro("阅读说明与结论先行", "这是一份面向项目维护者的“地图”，不是仅面向使用者的 README。报告同时区分原始开源框架、已经冻结的 Tc 版本、当前尚未冻结的 Hybrid+Qwen 实验，避免把论文能力、代码中存在的能力和当前实际启用的能力混为一谈。")
    story += [H("你应先记住的七件事", 2)]
    for x in [
        "ComProScanner 的核心单位不是整篇 PDF，而是“论文 → 规范化章节 CSV → 候选上下文 → 结构化事实”。",
        "本地 PDF 与出版社/API 获取的全文在入口不同，进入规范化章节表以后会汇合到同一抽取主干。",
        "DOI 主要承担身份、元数据关联、去重和向量库命名；没有 DOI 并不应阻止本地 PDF 抽取。",
        "Tc 适配主要由 preset 和候选策略完成，没有复制整套抽取框架；当前模型分工是 Qwen 做低成本判定，DeepSeek 做材料—Tc 抽取。",
        "PhysBERT/Chroma 是候选补充手段，不是最终抽取模型；当前 hybrid 规则要求它只能追加，失败时退回规则候选。",
        "图像抽取与图表 VLM 工具在仓库中存在，但当前 Tc 批处理显式关闭了相关图保存和图像读取，因此现有 Tc 指标是文本链路指标。",
        "最终可审计资产是逐篇 prediction、合并 prediction、人工接受 Gold 和 metrics；work/db/log/tmp 是可再生中间物。",
    ]: story.append(bullet(x))
    story += [H("当前可量化状态", 2), table([
        ["项目", "快照值", "解释"],
        ["前 30 篇 strict Gold", str(m.get("strict_gold_facts", 46)), "另有 1 条 Paper 30 范围事实作为 non-strict 保留"],
        ["TP / FP / FN", f"{m.get('tp', 42)} / {m.get('fp', 1)} / {m.get('fn', 4)}", "按 hybrid+Qwen 当前严格口径"],
        ["Precision / Recall / F1", f"{m.get('precision', 0):.3f} / {m.get('recall', 0):.3f} / {m.get('f1', 0):.3f}", "不是早期 9 篇 Dev 的 1.000 指标"],
        ["Paper 1–100 批处理", f"已落盘至 Paper {max_id}", "报告生成时动态快照；未完批次不得当作最终评测"],
        ["落盘状态分布", "；".join(f"{k}={v}" for k, v in sorted(progress.items())), "COMPLETED 表示有值；EMPTY_RESULT 也是一次正常完成"],
    ], [42*mm, 45*mm, 87*mm])]
    story.append(PageBreak())

    story += section_intro("目录", "可从 PDF 书签直接跳转。本报告先解释原论文，再解释当前工程；最后给出逐文件索引、运行手册、问题清单与汇报提纲。")
    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle("TOC0", fontName="CN-Bold", fontSize=10, leading=16, leftIndent=0, textColor=NAVY),
        ParagraphStyle("TOC1", fontName="CN", fontSize=8.5, leading=13, leftIndent=14, textColor=BLUE),
    ]
    story += [toc, PageBreak()]

    story += section_intro("1. 原论文：它解决了什么问题", "论文的贡献是把文献检索、全文获取、候选定位、多智能体关系抽取、评价、清洗和知识图谱串成可运行的开放框架。它不是一个训练出的单一模型，而是一套可替换 LLM、嵌入模型和数据源的工程系统。")
    story += [H("1.1 论文信息", 2), table([
        ["字段", "内容"],
        ["题名", "ComProScanner: a multi-agent based framework for composition-property structured data extraction from scientific literature"],
        ["作者", "Aritra Roy, Enrico Grisan, John Buckeridge, Chiara Gattinoni"],
        ["期刊", "Digital Discovery, 2026, 5(4), 1794–1808"],
        ["DOI", "10.1039/D5DD00521C"],
        ["时间", "2025-11-24 投稿；2026-03-19 接收；2026-03-25 首次在线"],
        ["许可", "Open Access，CC BY"],
    ], [34*mm, 140*mm])]
    story += [H("1.2 为什么需要它", 2), P("材料论文中的性能数值常与化学式、变量取值、制备条件、测量条件分散在正文、表格和图中。传统命名实体识别能找到“材料名”和“数值”，却不一定能把二者正确配对；复杂固溶体如 (1−x)A−xB 还需要展开变量。论文因此把任务拆给多个专门 agent，并用工具调用处理检索、公式解析和图表。")]
    story += flow(["检索论文", "获取全文", "定位证据", "抽取关系", "规范化", "评价/建库"], "原论文的核心不是某一个模型，而是端到端工作流。")
    story += [H("1.3 论文四阶段", 2), table([
        ["阶段", "原论文做法", "在本项目中的对应位置"],
        ["A 元数据检索", "Scopus Search API；按时间、文献类型等过滤", "metadata_extractor/fetch_metadata.py、filter_metadata.py"],
        ["B 文章收集", "Elsevier/Springer/Wiley TDM、IOP XML、本地 PDF", "article_processors/*_processor.py"],
        ["C 信息抽取", "RAG + 5 个专门 agent + 工具", "extract_flow/main_extraction_flow.py、crews、tools"],
        ["D 后处理", "语义/agentic 评价、清洗、统计图、Neo4j", "post_processing、data_visualizer.py、eval_visualizer.py"],
    ], [28*mm, 65*mm, 81*mm])]
    story += [H("1.4 五个 agent 与工具", 2), table([
        ["角色", "输入→输出", "边界"],
        ["MaterialsDataIdentifierCrew", "候选文本/检索结果 → yes/no", "决定是否继续，不能替代事实抽取"],
        ["CompositionExtractionCrew", "相关文本 → 原始材料—性质事实", "重科学语义与关系"],
        ["CompositionFormatCrew", "原始事实 → 统一 JSON", "重格式、单位、字段一致性"],
        ["SynthesisExtractionCrew", "实验段落 → 方法、前驱体、步骤、表征", "Tc 当前批处理未启用"],
        ["SynthesisFormatCrew", "制备原文 → 结构化 synthesis_data", "独立于 composition_data"],
        ["RAGTool", "问题 → Chroma 相似片段", "依赖已有向量库"],
        ["MaterialParserTool", "变量化学式 → 展开组合", "解决 x/y 等变量"],
        ["GraphExtractionTool", "图像 → 图中数据", "需图像保存与 VLM 配置"],
        ["EquationTool", "表达式 → 可计算/标准化结果", "辅助复杂数值或公式"],
    ], [39*mm, 73*mm, 62*mm])]
    story.append(PageBreak())

    story += [H("1.5 论文实验与结论的中文精读", 2)]
    for title, text in [
        ("数据集与任务", "作者从 3,916 篇提及 d33 的 Elsevier 文献中选取 100 篇（2019-01 至 2025-03）做评测，目标不仅是识别 d33，而是提取材料组成—d33 的成对关系，并可选抽取合成信息。"),
        ("为什么选 PhysBERT", "论文用 12 个材料学查询比较通用 all-mpnet-base-v2 与领域模型 PhysBERT。PhysBERT 对材料术语的语义邻近性更好，因此用于 Chroma 向量库。它负责“找片段”，不是最后生成数据库。"),
        ("模型比较", "多个闭源与开源 LLM 被放入同一 agent 框架比较。DeepSeek-V3-0324 在综合准确率、组成关系和合成抽取方面表现突出；Llama-3.3-70B 的归一化 P/R/F1 约为 0.80/0.81/0.80；Qwen 系列也有竞争力。结论是架构能换模型，但模型选择依然显著影响结果。"),
        ("数据库结果", "100 篇样本中 BaTiO3 家族占比最高；作者还统计前驱体与表征技术，并构建 1,825 个节点的 Neo4j 图。一个重要发现是提取到的压电材料中超过 99% 不在 Materials Project 的压电数据库里，说明文献抽取能补足数据库。"),
        ("限制", "LLM 非确定性、RAG 参数依任务调节、评价方法本身也会波动；图像/OCR 与多性质联合抽取仍是未来方向。框架提供路径，但不能替代人工 Gold 和质量控制。"),
    ]:
        story += [H(title, 3), P(text)]
    story.append(P("版权说明：本报告提供的是按章节忠实转述、方法解释与结果摘要，不是对原论文逐句完整翻译。建议对照原文阅读：RSC https://pubs.rsc.org/en/content/articlehtml/2026/dd/d5dd00521c；DOI https://doi.org/10.1039/D5DD00521C。", "warning"))

    story += section_intro("2. 原始框架与当前项目：哪些没变，哪些改变了", "当前仓库以原始 ComProScanner 为主体，Tc 工作通过属性 preset、候选构造、DOI 可选本地执行、超时与运行器加固来适配。仓库现在同时存在“已提交的冻结节点”和“工作区中继续实验的改动”，报告据实际工作树描述。")
    story += [table([
        ["维度", "原论文/上游默认", "当前 Tc 项目"],
        ["性质", "示例主要是压电系数 d33", "居里/相变温度 Tc"],
        ["输入", "出版社 TDM + 本地 PDF", "当前 100 篇主要走本地 pdfs/；未来可接检索下载"],
        ["候选", "关键词门控 + RAG", "高召回规则候选 + 前后句 + 完整表格 + PhysBERT 追加"],
        ["identifier", "通常同一 LLM 配置", "Qwen Flash 低成本 yes/no；技术失败回退 DeepSeek"],
        ["extractor", "可配置多种 LLM", "DeepSeek / deepseek-v4-flash，180 s"],
        ["DOI", "强元数据中心", "本地 PDF 可无 DOI；使用 local-pdf/hash 身份"],
        ["图像", "工具与链路存在", "当前 Tc runner 关闭 figure keywords 与保存"],
        ["评价", "语义与 agentic 评价", "人工 Gold + 确定性 strict P/R/F1"],
    ], [28*mm, 70*mm, 76*mm])]
    story += [H("2.1 Git 演进节点", 2), table([
        ["提交", "含义"],
        ["c5470f4", "加入 Curie temperature preset 的基线"],
        ["d1570b1", "稳定本地 Tc：DOI 可选、180 s、NUL sanitation 等"],
        ["0c5cb15", "Tc v2 管线定型"],
        ["5bec309", "高召回预筛"],
        ["3741241", "提高 identifier recall"],
        ["3753149", "拆分 Tc identifier 与 extractor prompt"],
    ], [35*mm, 139*mm])]
    story.append(P("注意：报告生成时工作树仍有未提交的 Hybrid+Qwen、候选上下文、文档和 runner 改动。因此 3753149 是最后一个已提交节点，不等于当前全部运行逻辑都已冻结。", "warning"))

    story += section_intro("3. 总体架构：四层如何配合", "把所有代码看成四层，就不会被大量文件迷惑：核心库负责通用能力；preset 只描述“抽什么”；runner 描述“这次怎么跑”；outputs 保存不可替代的结果。")
    story += flow(["输入/元数据", "核心库", "性质 preset", "运行器", "产物/评价"], "preset 被核心库消费，runner 负责一次实验的边界与落盘。")
    story += [table([
        ["层", "目录", "允许包含", "不应包含"],
        ["核心库", "src/comproscanner", "解析、候选、flow、clean/eval", "具体论文编号、实验输出目录、密钥"],
        ["Preset", "src/comproscanner/presets", "科学范围、关键词、prompt 注释、示例", "API key、重试状态、benchmark 结果"],
        ["Runner", "scripts / examples", "论文选择、模型、timeout、checkpoint、输出路径", "通用科学逻辑的复制品"],
        ["Artifacts", "outputs", "prediction、Gold、metrics、报告", "缓存、PDF 副本、日志、Chroma 临时库"],
    ], [24*mm, 38*mm, 59*mm, 53*mm])]

    story += section_intro("4. 路径 A：你手动放入 PDF 后发生什么", "当前 100 篇 Tc 主要使用这条路径。关键是区分长期输入 pdfs/、逐篇隔离副本 work/.../input、解析后的 CSV、向量库和最终 JSON。")
    story += flow(["pdfs/1-xxx.pdf", "work/.../input", "PDFsProcessor", "Docling", "章节 CSV", "候选/向量", "LLM JSON"], "runner 为每篇论文建立独立运行目录；单篇失败不会污染下一篇。")
    story += [H("4.1 文件选择与编号", 2), P("scripts/run_tc_hybrid_qwen_30.py 的 find_pdf() 用文件名前缀 ^{paper_id}- 匹配 pdfs/*.pdf。每个编号必须唯一；同号两篇（例如曾出现的 68）需要明确策略，否则 runner 会报 multiple matches，避免静默把一篇覆盖另一篇。选中的原始 PDF 复制到 work/tc_hybrid_qwen_001_030/paper_NNN/input/。")]
    story += [H("4.2 PDFsProcessor", 2), P("ComProScanner.process_articles(source_list=['pdfs']) 把任务分派到 article_processors/pdfs_processor.py。它维护已处理记录、尝试从文件名/正文提取 DOI、生成无 DOI 的 local document id、调用 PDFToMarkdownText、记录失败 PDF，并将每篇文章写成规范表格。")]
    story += [H("4.3 Docling 解析", 2), P("utils/pdf_to_markdown_text.py 配置 Docling，把版面转换为 Markdown 式文本与表格，清理软连字符、控制字符等，按 section 写入 DataFrame。当前 NUL 修复保证读取 CSV 时先清除 \\x00，防止正文在中途被截断。Docling 能恢复文本/表格，但扫描件质量、双栏顺序、公式和图中数值仍可能丢失。")]
    story += [H("4.4 规范化章节 CSV", 2), P("产物位于 work/.../results/extracted_data/magnetic/*.csv。典型字段包含 doi、title/metadata、abstract、introduction、experimental/methods、results_discussion、conclusion、tables、is_property_mentioned 等。后续 agent 通常不再直接打开 PDF，而是读取这张章节表。")]
    story += [H("4.5 原始文本恢复", 2), P("当前 runner 还有 recover_raw_text_candidate()：若结构化章节没有把论文判为相关，则用 PyMuPDF 从 PDF 全文取纯文本；只有确定性 Tc 关键词/正则命中时才把全文写入 results_discussion 并建向量库。它弥补章节解析漏检，但会增加上下文长度和噪声。")]
    story += [H("4.6 输出落点", 2), table([
        ["对象", "路径示例", "是否最终保留"],
        ["原始输入", "pdfs/1-title.pdf", "是；作为可复现语料"],
        ["逐篇副本", "work/.../paper_001/input/", "否；可再生"],
        ["章节 CSV", "work/.../results/extracted_data/magnetic/*.csv", "调试时有价值，通常可再生"],
        ["Chroma", "work/.../paper_001/db/", "否；可再建"],
        ["单篇结果", "outputs/.../papers/paper_001.json", "是"],
        ["合并结果", "outputs/.../predictions_001_100.json", "是"],
        ["人工 Gold", "outputs/gold/tc_001_030/gold_facts.json", "是，不可用预测替代"],
        ["指标", "outputs/.../strict_metrics_001_030.json", "是，需带口径"],
    ], [29*mm, 93*mm, 52*mm])]

    story += section_intro("5. 路径 B：API 发现与下载 PDF", "项目要获取“与现有 100 篇类似”的新论文，应把“发现元数据”和“合法获得全文”拆成两个问题。Semantic Scholar/Scopus/Crossref 帮你找文献；Unpaywall、openAccessPdf 或出版社 TDM 决定能否取得全文。")
    story += flow(["种子论文/检索式", "S2/Scopus/Crossref", "候选清单", "人工审核", "OA/TDM 下载", "校验/去重", "pdfs/"], "下载完成后与手动 PDF 汇入同一 PDFsProcessor 主干。")
    story += [H("5.1 推荐的发现流程", 2)]
    for x in [
        "以现有 100 篇 DOI/标题作为正样本种子，查询相似论文、参考文献和被引网络。",
        "限制年份、文献类型和主题：优先研究论文，排除 review、conference、correction。",
        "保存 candidate_manifest.csv/json：paper_id、title、doi、year、journal、authors、source、OA 状态、PDF URL、审核状态。",
        "先人工批准候选，再下载；不要让“检索命中”自动等价于“纳入语料”。",
        "下载后验证 HTTP 类型与文件头 %PDF，计算 SHA-256，以 DOI + hash 双重去重，再重命名为 101-title.pdf 等稳定编号。",
    ]: story.append(bullet(x))
    story += [H("5.2 API 各自负责什么", 2), table([
        ["服务", "主要作用", "不能保证"],
        ["Semantic Scholar", "相似推荐、引用网络、元数据、部分 openAccessPdf", "不能绕过付费墙；key 主要提升额度和稳定性"],
        ["Scopus", "高质量检索、主题与文献类型过滤", "全文下载权取决于订阅与 TDM 条款"],
        ["Crossref", "DOI/标题/期刊元数据核验", "通常不是全文 PDF 仓库"],
        ["Unpaywall", "按 DOI 找合法开放获取位置", "闭源论文可能没有 OA 链接"],
        ["出版社 TDM", "在许可和机构权限下取得结构化全文/PDF", "每家 API、配额、许可不同"],
    ], [35*mm, 70*mm, 69*mm])]
    story += [H("5.3 无 Semantic Scholar key 时", 2), P("多数端点仍可匿名调用，但速率较低。应限制为约 1 request/s、指数退避、缓存响应、支持断点续跑。一个 API key 不会让单个 PDF 网络传输本质变快，也不会增加付费文献访问权；它主要减少限流和失败。")]

    story += section_intro("6. DOI 在项目中的真实作用", "DOI 很重要，但它不是“允许抽取的门票”。本地文件可用稳定哈希身份继续运行；同时必须防止参考文献 DOI 被错当作本文 DOI。")
    story += [table([
        ["阶段", "DOI 的作用", "缺失时策略"],
        ["元数据", "关联标题、期刊、作者、年份", "从文件名/首页/清单补充；未知字段保留空"],
        ["去重", "同一文章跨来源合并", "用 PDF SHA-256 + 标题规范化"],
        ["向量库", "转义后作为 db_name", "local-pdf/<hash> 同样可转义命名"],
        ["checkpoint", "checked_dois 避免重复处理", "改为 document_id 语义更准确"],
        ["最终 JSON", "稳定主键与可追溯引用", "保留 local id，并标记 DOI 待核验"],
    ], [27*mm, 70*mm, 77*mm])]
    story.append(P("已知风险：从全文正则抓 DOI 时可能抓到参考文献 DOI。Paper 11 曾出现这种情形。更稳妥的优先级应为：人工 manifest DOI ＞ 出版商元数据 ＞ 首页标题/DOI 区域 ＞ Crossref 标题核验 ＞ 全文正则；低置信度 DOI 不应覆盖已有 document_id。", "warning"))

    story += section_intro("7. 候选文本如何产生，以及为何会丢上下文", "LLM 并非总是读取整篇文章。候选构造决定了它“看得见什么”，因此 Recall 的上限常在 LLM 调用之前已经确定。")
    story += [H("7.1 SectionProcessor 的规则候选", 2)]
    for x in [
        "把章节中的 Markdown 表格与普通文本分开；表格作为整体保存，避免逐句破坏行列关系。",
        "文本按句切分；保留包含数字或连续大写字母的句子，因为材料式、温度和缩写常满足这个条件。",
        "当前最小改动加入命中句的前一句与后一句，使材料名在前句、数值在后句时仍能配对。",
        "结果/讨论中的完整相关表格被纳入，以减少表格事实漏失。",
        "各章节再按固定标签拼接为 rule_candidate。",
    ]: story.append(bullet(x))
    story += [H("7.2 论文级预筛", 2), P("PDF 解析阶段用 preset 的 exact/substrings/regex 信号判断是否出现 Tc 相关表达。高召回策略宁可让背景材料进入，也不应只保留“本文研究材料”。这是当前目标由“研究对象数据库”转为“论文中正确出现的材料—Tc 对”的关键改变。")]
    story += [H("7.3 Hybrid PhysBERT", 2), P("candidate_context.py 先保留完整 rule_candidate，再按多个 Tc 查询从 Chroma/PhysBERT 取 top-k 片段，规范化空白后去重并追加。若向量库不存在、依赖失败或查询异常，返回原规则候选。这样 RAG 只能提高覆盖，不能删掉确定性规则已经找到的证据。")]
    story += [H("7.4 上下文仍可能缺失的四处", 2), table([
        ["漏失点", "例子", "诊断方法"],
        ["PDF 解析", "双栏错序、扫描页、公式/表格损坏", "对照原 PDF 与章节 CSV"],
        ["章节归类", "关键句被放进 reference/unknown 或未写入", "搜索 raw text 与 CSV 各列"],
        ["规则候选", "材料与温度隔了超过 ±1 句", "搜索 candidate text 是否含证据"],
        ["LLM 抽取", "证据已在 candidate 但模型未输出", "保存 prompt 输入并与 prediction 比较"],
    ], [32*mm, 68*mm, 74*mm])]

    story += section_intro("8. Tc 抽取的实际模型链路", "当前 Hybrid+Qwen runner 把“有没有可抽取事实”和“抽取事实本身”拆给不同模型，以降低成本；任何模型输出都必须经过 JSON 解析、状态记录和人工 Gold 评价。")
    story += flow(["规则+RAG候选", "Qwen yes/no", "DeepSeek 原始抽取", "格式化", "paper_NNN.json"], "Qwen 技术错误时可回退 DeepSeek identifier；科学空结果不因质量差而自动重试。")
    story += [table([
        ["配置", "当前值", "位置"],
        ["属性", "Curie temperature / transition temperature（按 preset 科学边界）", "presets/curie_temperature.py"],
        ["Identifier", "Qwen qwen-flash（DashScope OpenAI-compatible）", "preset extraction_kwargs"],
        ["Extractor", "DeepSeek / deepseek/deepseek-v4-flash", "runner"],
        ["Timeout", "180 s / paper extraction flow", "runner → ComProScanner.extract..."],
        ["候选模式", "hybrid；规则主干 + PhysBERT 追加", "candidate_context.py"],
        ["图像", "本轮关闭", "main/additional_figure_keywords 空；is_save_relevant=False"],
        ["重试", "默认每篇一次；技术失败记录，不因空结果追求重跑", "runner"],
    ], [32*mm, 76*mm, 66*mm])]
    story += [H("8.1 Tc 的科学边界", 2), P("“Curie temperature”通常指铁电—顺电或铁磁—顺磁相变温度；论文也可能写 dielectric anomaly、ferroelectric transition、magnetic transition、T_C 等。当前 Gold 目标已允许论文中的背景材料，只要材料与温度有明确对应。烧结温度、退火温度、测量温度和只表达上/下限而无可归属材料的数值不应误作 Tc。")]
    story += [H("8.2 状态语义", 2), table([
        ["状态", "含义", "是否表示程序失败"],
        ["COMPLETED", "成功完成且至少一个材料—Tc 值", "否"],
        ["EMPTY_RESULT", "flow 完成但无值；可能是真空结果", "否"],
        ["PREFILTER_REJECTED", "确定性门控未发现相关信号", "否，但应抽样审计 Recall"],
        ["PROCESSING_ERROR", "PDF/CSV/解析阶段异常", "是"],
        ["EXTRACTION_ERROR/TIMEOUT", "LLM/flow 阶段异常或超时", "是"],
        ["MISSING_PDF", "编号没有唯一文件", "是，输入问题"],
    ], [42*mm, 85*mm, 47*mm])]

    story += section_intro("9. JSON、Gold、评分与“数据库”", "项目当前最可信的数据库形态是可审计 JSON，而不是必须写入 MySQL。MySQL、CSV、Chroma 和 Neo4j 各自解决不同问题，不能混称为同一个数据库。")
    story += [H("9.1 单篇 prediction 结构", 2), P("runner 外层记录 paper_id、filename、pdf_path、status、runtime_seconds、attempt_count、error、pipeline_report；output 内按 DOI/local id 保存 composition_data、可选 synthesis_data 与 article_metadata。composition_data 中核心是 compositions_property_values、property_unit、family。")]
    story += [P("{<br/>  \"paper_id\": 53, \"status\": \"COMPLETED\",<br/>  \"output\": {\"local-pdf/...\": {<br/>    \"composition_data\": {<br/>      \"compositions_property_values\": {\"BFS-BT-Mn-0\": 624},<br/>      \"property_unit\": \"°C\"<br/>    }, \"article_metadata\": {...}<br/>  }}<br/>}", "code")]
    story += [H("9.2 四种存储后端", 2), table([
        ["存储", "用途", "当前 Tc 是否主用"],
        ["CSV", "规范化文章章节；也可批量落表", "是（中间层）"],
        ["JSON", "模型结果、Gold、metrics，可 git/diff/审计", "是（最终资产）"],
        ["MySQL", "大批结构化章节/结果的关系型持久化", "代码存在，当前 runner 默认未启用"],
        ["Chroma", "PhysBERT 向量索引，仅供 RAG 查询", "hybrid 可用，但属于可再生索引"],
        ["Neo4j", "材料—性质—文献关系可视化/查询", "代码存在，当前 Tc 最终库尚未正式构建"],
    ], [27*mm, 87*mm, 60*mm])]
    story += [H("9.3 Gold 与指标", 2), P("Gold 必须由人基于原文接受；预测不能反向自动成为 Gold。最小 Gold 可只记录 paper_id、material、tc_value、tc_unit，并建议额外保留 page/evidence、fact_role、transition_type、strict_scoring，便于争议复核。匹配时需处理化学式别名、单位换算、范围/不等式和容差。")]
    story += [table([
        ["指标", "公式", "当前解释"],
        ["Precision", "TP / (TP + FP)", "输出的材料—Tc 中有多少是真的"],
        ["Recall", "TP / (TP + FN)", "Gold 中有多少被找回来"],
        ["F1", "2PR / (P + R)", "精确率与召回率的调和平均"],
        ["当前 30 篇", f"P={m.get('precision',0):.3f}, R={m.get('recall',0):.3f}, F1={m.get('f1',0):.3f}", "46 条 strict Gold；42 TP、1 FP、4 FN"],
    ], [30*mm, 64*mm, 80*mm])]

    story += section_intro("10. 当前 30 篇的错误分析", "这些错误展示了三类问题：证据没进入候选、证据进入但模型漏抽、模型把模糊陈述变成了精确值。优化时必须先判断错误发生在哪一层。")
    story += [table([
        ["论文", "现象", "所在层/含义"],
        ["Paper 6", "预测 BaTiO3 = 130 °C；原文仅把 <200 °C 的峰与 BTO Tc 联系", "1 个 FP；模型将含糊背景知识具体化，不是读图所得"],
        ["Paper 11", "Gold 的 BaTiO3 = 120 °C 未输出", "正文/章节上游缺失；还暴露参考文献 DOI 误识别风险"],
        ["Paper 17", "BiFeO3 = 1103 K 未输出", "明确背景事实，但未进入可见上下文"],
        ["Paper 25", "650 °C 与掺 La 后 227 °C 均未输出", "证据已进入 candidate，属于 extractor recall"],
        ["Paper 30", ">约580 °C", "范围/不等式事实；保留 Gold 但暂作 non-strict"],
    ], [25*mm, 80*mm, 69*mm])]
    story += [H("10.1 调试顺序", 2)]
    for x in [
        "先看原 PDF：Gold 事实是否真实存在、材料和温度是否明确对应。",
        "再看 raw text：解析器是否读到该句/表格。",
        "再看章节 CSV：是否被归类和保存。",
        "再看 rule/hybrid candidate：是否到达模型输入。",
        "最后看 identifier/extractor 原始响应：是 gate 拒绝还是抽取遗漏。",
        "只有定位层级后再改代码；否则更换模型可能掩盖解析问题。",
    ]: story.append(bullet(x))

    story += section_intro("11. 项目目录总览", "下面按维护者视角解释目录。并非所有目录都同等重要：先掌握 src/comproscanner、presets、scripts、pdfs、work、outputs 六处即可运行和诊断。")
    story += [P("ComProScanner/<br/>├─ src/comproscanner/　核心库<br/>│　├─ article_processors/　全文入口适配<br/>│　├─ metadata_extractor/　检索与元数据过滤<br/>│　├─ extract_flow/　CrewAI 流程、agent、工具<br/>│　├─ post_processing/　清洗、评价、可视化/知识图谱<br/>│　├─ presets/　性质适配层（当前含 Tc）<br/>│　└─ utils/　解析、候选、数据库、嵌入、路径与日志<br/>├─ scripts/　可恢复 benchmark/批处理 runner<br/>├─ examples/　用户调用示例<br/>├─ tests/　回归与性质特定测试<br/>├─ pdfs/　长期 PDF 输入<br/>├─ work/　逐篇运行中间物（可再生）<br/>├─ outputs/　prediction、Gold、metrics、报告<br/>├─ docs/　MkDocs 文档<br/>└─ tmp/results/db/logs/　临时或历史产物", "code")]

    story += section_intro("12. 逐文件职责：公共入口、处理器与元数据", "本节按代码文件解释“谁调用谁”。文件很多，但大多数都有清晰单一职责；带 * 的文件对当前 Tc 路径最关键。")
    story += [table([
        ["文件", "职责与关键调用"],
        ["src/comproscanner/__init__.py", "对外 facade：导出 ComProScanner、preset、评价和可视化函数，减少用户对内部路径的依赖。"],
        ["src/comproscanner/comproscanner.py *", "总调度器。collect_metadata → 元数据；process_articles → 按 source 分派处理器；extract_composition_property_data → DataExtractionFlow；clean/evaluate → 后处理。"],
        ["article_processors/pdfs_processor.py *", "本地 PDF 批处理、DOI/本地 id、失败记录、Docling 转换、processed checkpoint、CSV/SQL 写入。"],
        ["article_processors/elsevier_processor.py", "用 Elsevier TDM/全文响应解析章节、表格、图与元数据，写统一结构。"],
        ["article_processors/springer_processor.py", "Springer Nature 全文接口与 XML/文档结构适配。"],
        ["article_processors/wiley_processor.py", "Wiley TDM/PDF 获取与解析适配。"],
        ["article_processors/iop_processor.py", "处理本地/批量 IOP XML，映射为统一章节。"],
        ["metadata_extractor/fetch_metadata.py", "构造 Scopus 查询、分页请求、保存原始元数据。"],
        ["metadata_extractor/filter_metadata.py", "按类型、年份、重复项、已有记录等过滤，形成可处理清单。"],
    ], [62*mm, 112*mm], font=7.3)]

    story += section_intro("13. 逐文件职责：抽取 flow、crews 与工具", "DataExtractionFlow 是执行状态机；crew 的 Python 文件装配 agent/task，YAML 保存角色说明和任务 prompt。")
    story += [table([
        ["文件", "职责"],
        ["extract_flow/main_extraction_flow.py *", "MaterialsState + CrewAI Flow；载入论文候选、可选图像检查、identifier 路由、组成抽取、格式化、可选合成抽取、最终保存；记录 flow error。"],
        ["crews/materials_data_identifier_crew/*.py,yaml *", "判断候选是否包含可抽取材料—性质关系；当前支持独立 identifier model/base_url/key。"],
        ["crews/composition_crew/composition_extraction_crew/* *", "保留材料与 Tc 的科学对应、变量组成、条件与单位；tasks.yaml 承载主抽取约束。"],
        ["crews/composition_crew/composition_format_crew/*", "把原始自然语言结果转换为 schema 一致 JSON，处理 property_unit/family 等。"],
        ["crews/synthesis_crew/synthesis_extraction_crew/*", "从实验段抽取方法、前驱体、步骤、表征；Tc 当前未启用。"],
        ["crews/synthesis_crew/synthesis_format_crew/*", "规范化 synthesis_data。"],
        ["tools/rag_tool.py", "面向 agent 的 Chroma 查询工具，返回与 query 最相似的文档块。"],
        ["tools/material_parser_tool.py", "解析变量化学式和取值，生成具体材料表达。"],
        ["tools/equation_tool.py", "计算或规范化数学表达式，防止 agent 手算错误。"],
        ["tools/graph_extractor_tool.py", "调用视觉模型读取已提取的相关图；必须有图像文件与 VLM 配置。"],
    ], [67*mm, 107*mm], font=7.2)]

    story += section_intro("14. 逐文件职责：utils 与配置", "utils 是数据路径中最容易被忽视却最决定召回率的一层。")
    story += [table([
        ["文件", "职责"],
        ["utils/pdf_to_markdown_text.py *", "Docling converter、Markdown/表格、caption、图像保存、文本清理、章节写表、property signal 匹配。"],
        ["utils/data_preparator.py *", "read_csv_sanitizing_nul；SectionProcessor 分表/句、数字/大写筛选与前后句；MatPropDataPreparator 读取未处理论文。"],
        ["utils/candidate_context.py *", "rule candidate 与 PhysBERT chunks 合并、规范化去重、hybrid fail-open。"],
        ["utils/database_manager.py", "MySQL 建表/追加、CSV 分批写入、Chroma create/query/exists。"],
        ["utils/embeddings.py", "统一 HuggingFace、sentence-transformers、OpenAI embeddings；按模型名选择 backend。"],
        ["utils/get_paper_data.py", "把文章表中 metadata/section/figure 信息整理为 extraction flow 可消费对象。"],
        ["utils/figure_extractor.py", "从出版商内容/文件中保存匹配 caption 的图像，建立相关图目录。"],
        ["utils/save_results.py", "JSON 等结果的安全保存/合并辅助。"],
        ["utils/common_functions.py", "跨模块通用工具。"],
        ["utils/prepare_iop_files.py", "IOP 批量文件预处理。"],
        ["utils/error_handler.py", "错误包装/记录策略。"],
        ["utils/logger.py", "统一日志。"],
        ["utils/configs/paths_config.py", "默认目录结构。"],
        ["utils/configs/llm_config.py", "模型/provider 默认配置与环境变量读取。"],
        ["utils/configs/rag_config.py", "chunk size/overlap/top-k、db path、embedding model。"],
        ["utils/configs/article_keywords.py", "通用文章/章节关键词。"],
        ["utils/configs/base_urls.py", "出版社/模型接口基础 URL。"],
        ["utils/configs/database_config.py", "关系数据库配置。"],
        ["utils/configs/custom_dictionary.py", "材料/文本规范化相关自定义词典。"],
    ], [62*mm, 112*mm], font=6.9)]

    story += section_intro("15. 逐文件职责：preset、后处理、runner 与测试", "这部分决定项目是否可扩展、是否可验证。")
    story += [table([
        ["文件/组", "职责"],
        ["presets/base.py", "PropertyExtractionPreset 数据结构与 validate/to_runtime_dict；规定属性适配的边界。"],
        ["presets/registry.py", "按稳定名称注册、获取、列出 preset。"],
        ["presets/curie_temperature.py *", "Tc 关键词/正则、candidate patterns、identifier inclusion/exclusion、extract/format notes、示例、Qwen identifier 配置。"],
        ["post_processing/data_cleaner.py", "材料式括号、缩写、元素、算术/分数组成等清洗。"],
        ["post_processing/evaluation/semantic_evaluator.py", "按语义相似与规范化规则对测试结果与真值比较。"],
        ["post_processing/evaluation/eval_flow/*", "用评价 agent 检查组成与合成结果，形成 agentic metrics。"],
        ["post_processing/visualization/create_knowledge_graph.py", "把结果变换为 Neo4j 节点/关系。"],
        [".../data_distribution_visualizers.py", "材料家族、前驱体、表征等分布图。"],
        [".../eval_plot_visualizers.py", "单/多模型评价可视化。"],
        ["data_visualizer.py / eval_visualizer.py", "对外可视化 facade。"],
        ["scripts/run_tc_hybrid_qwen_30.py *", "实际 Paper 1–100 可恢复 runner：唯一映射、逐篇隔离、一次调用、raw-text recovery、原子 JSON、resume。"],
        ["scripts/run_tc_dev_benchmark.py", "冻结 Dev benchmark 运行。"],
        ["scripts/run_tc_dev_recovery.py", "特定 Dev 恢复场景；不应成为通用生产分支。"],
        ["examples/extract_curie_temperature.py", "用户级 Tc 调用示例。"],
        ["tests/test_curie_temperature_preset.py", "preset 合法性和配置边界。"],
        ["tests/test_tc_*", "高召回预筛、identifier 语义、prompt 分离、recovery 回归。"],
        ["tests/test_candidate_context.py", "hybrid 合并、去重、缺库/失败回退。"],
        ["tests/test_article_processors/*, test_utils/*", "各数据源、PDF、候选、数据库、嵌入与保存的单元回归。"],
    ], [67*mm, 107*mm], font=6.9)]

    story += section_intro("16. 一次运行的调用栈与伪代码", "把路径和类名连起来后，可以用下列调用栈定位任何问题。")
    story += [P("run_tc_hybrid_qwen_30.main()<br/>└─ run_paper(id, pdf)<br/>　├─ get_curie_temperature_preset()<br/>　├─ ComProScanner.process_articles()<br/>　│　└─ PDFsProcessor.process_pdfs()<br/>　│　　└─ PDFToMarkdownText.convert_to_markdown()<br/>　│　　　├─ clean_text / append_section_to_df<br/>　│　　　└─ CSVDatabaseManager.write_to_csv()<br/>　├─ recover_raw_text_candidate() [必要时]<br/>　│　└─ VectorDatabaseManager.create_database()<br/>　└─ ComProScanner.extract_composition_property_data()<br/>　　├─ MatPropDataPreparator.get_unprocessed_data()<br/>　　├─ build_hybrid_candidate_context()<br/>　　└─ DataExtractionFlow.kickoff()<br/>　　　├─ identify_materials_data_presence()<br/>　　　├─ extract_composition_property_data()<br/>　　　├─ extract_final_composition_property_data()<br/>　　　└─ finalize_results()<br/>最终：paper_NNN.json → predictions_001_100.json", "code")]
    story += [H("16.1 为什么单篇失败不停止", 2), P("run_paper 用 try/except/finally 包裹 processing 和 extraction，并把 stage、error、traceback、runtime 写入单篇记录；main 每完成一篇就原子写 JSON，再继续下一篇。重启时加载 papers/paper_*.json 并 SKIPPED_EXISTING，只有 --force 才重发。")]

    story += section_intro("17. 图片、表格与视觉模型：代码存在 ≠ 当前启用", "仓库有 figure extractor 与 GraphExtractionTool，原论文也把图表抽取作为工具链的一部分。但当前 Tc runner 把主/附加 figure keywords 设为空，并设置 is_save_relevant=False，所以 DeepSeek/Qwen 收到的是文本候选，不是 PDF 页面图像。")
    story += [table([
        ["要启用图像 Tc", "需要的最小工作"],
        ["1 图像发现", "给 main_figure_keywords/additional_figure_keywords 配置 Tc、Curie、transition、dielectric 等 caption 信号。"],
        ["2 保存", "启用相关图保存，确保 related_figures_base_path 按 paper/document id 对齐。"],
        ["3 VLM", "配置支持图像的模型/provider/key；GraphExtractionTool 读取图而非文本 LLM 猜测。"],
        ["4 schema", "保存 figure/page、曲线/图例、估读值、单位、不确定性和 evidence_type=figure。"],
        ["5 评价", "图读数应有容差并与正文精确值分开；人工 Gold 标注来源。"],
    ], [45*mm, 129*mm])]
    story.append(P("不要直接把视觉估读与正文精确数值混在同一严格评分里。先建立单独的小型 figure-Gold，再开启图像路径。", "warning"))

    story += section_intro("18. 增加 Ms 等新性质的最小改动方案", "正确扩展方式是增加 preset，而不是复制 PDF 解析器或修改 Tc prompt。只有通用 schema 无法表达新科学信息时，才改核心结构。")
    story += [H("18.1 Ms preset 应包含", 2)]
    for x in [
        "稳定名称 saturation_magnetization；main_property_keyword 用于目录/存储。",
        "高召回信号：saturation magnetization、M_s、Ms、emu/g、A·m²/kg 等，同时排除 mass spectrometry 等歧义。",
        "identifier 定义：材料与 Ms 数值必须可配对；背景材料允许与否需在 Gold 规范先确定。",
        "extractor 注释：区分 Ms、Mr、Mmax；保留测量温度、磁场、单位、样品形态和不等式/范围。",
        "固定/变量组成示例；formatter 示例；代表性正例、负例、边界例测试。",
    ]: story.append(bullet(x))
    story += [H("18.2 何时需要扩 schema", 2), P("如果只需要 material → numeric value + unit，通用 compositions_property_values 可以复用。若要做可信磁学数据库，建议新增 measurement_temperature、applied_field、sample_form、value_operator、value_min/max、uncertainty、evidence、page。否则同一材料在不同条件下的 Ms 会被错误折叠。")]
    story += flow(["定义 Gold 规范", "新增 preset", "20篇 Dev", "冻结 prompt", "Test", "再扩语料"], "性质扩展首先是评价设计，其次才是 prompt。")

    story += section_intro("19. 当前架构中不干净或不合理的地方", "以下不是要求立刻重构，而是按收益/风险排序的维护清单。当前最重要的是冻结可复现路径，而不是在批次运行中大改核心。")
    story += [table([
        ["优先级", "问题", "建议"],
        ["P0", "密钥曾在聊天中暴露", "立即在供应商侧轮换；.env 仅本机保存；日志与报告永不写 key。"],
        ["P0", "当前 Hybrid 逻辑仍有未提交工作树改动", "100 篇完成且审核后跑相关测试，形成单一干净 freeze commit。"],
        ["P1", "输出目录仍叫 tc_hybrid_qwen_001_030，但已承载 1–100", "新批次改名 tc_hybrid_qwen_001_100；保留旧路径映射清单。"],
        ["P1", "runner 中 raw-text recovery 是实验性旁路", "抽象为可配置 core fallback，并为解析漏失/不命中分别测试。"],
        ["P1", "DOI 全文正则可能抓参考文献", "增加来源优先级、标题核验、confidence 与 doi_status。"],
        ["P1", "JSON map 难表示同材料多条件/范围", "迁移到 fact list schema；每条事实有 evidence/condition/operator。"],
        ["P2", "候选与模型原始输入未形成稳定最终审计包", "每篇可选保存 candidate manifest 与响应摘要（不含 key）。"],
        ["P2", "results/work/outputs 历史命名混杂", "明确 retention policy：outputs 仅最终；work 可清理；pdfs 只放语料。"],
        ["P2", "图像链路虽存在但未纳入 Tc QA", "单独建立 10–20 个图读数 Gold，不直接并入文本指标。"],
    ], [16*mm, 75*mm, 83*mm], font=7.1)]

    story += section_intro("20. 安全、成本与可复现运行规范", "模型调用会把候选正文发送给第三方；运行前必须明确授权、模型、范围和次数。API key 只从环境变量读取。")
    for x in [
        "输入授权：记录允许发送的 paper ids、PDF 来源、provider/model、每篇次数。",
        "密钥：.env 加入 .gitignore；出现于聊天/日志后视为泄露并轮换。",
        "断点：每篇 JSON 原子写入；启动时跳过已有记录；失败状态可审计。",
        "成本：identifier 用低价模型，extractor 用更强模型；先预筛再调用，但门控要抽样评估 Recall。",
        "复现：保存 commit hash、preset 名称/版本、模型字符串、timeout、候选模式、运行时间和 Gold 版本。",
        "数据合规：只通过机构许可、出版社 TDM 或合法 OA URL 下载全文；元数据 API 不等于全文许可。",
    ]: story.append(bullet(x))

    story += section_intro("21. 你可以亲自执行的操作手册", "以下是理解项目后最常用的只读检查与运行入口。命令默认在 F:\\Python_Project\\ComProScanner 执行。")
    story += [H("21.1 检查输入映射", 2), P("python scripts/run_tc_hybrid_qwen_30.py --validate-only", "code")]
    story += [H("21.2 运行指定论文", 2), P("python scripts/run_tc_hybrid_qwen_30.py --paper-ids 31 32 33", "code")]
    story += [H("21.3 恢复批次", 2), P("python scripts/run_tc_hybrid_qwen_30.py", "code"), P("已有 paper_NNN.json 会跳过。不要随意使用 --force；它会重新发送并覆盖该篇结果。")]
    story += [H("21.4 查看结果", 2), P("Get-Content outputs/runs/tc_hybrid_001_100/predictions.json", "code")]
    story += [H("21.5 调试一条 FN", 2), P("依次检查 pdfs/原文 → work/.../*.csv → 候选文本/向量 chunks → paper_NNN.json/pipeline_report。先确认事实在哪层消失，再决定改解析、候选还是 prompt。")]

    story += section_intro("22. 明日汇报可直接使用的 10 分钟提纲", "建议把重点放在“为什么做、如何做、做到什么、下一步怎么验证”，而不是逐文件念目录。")
    story += [table([
        ["时间", "讲什么", "一句话重点"],
        ["0–1 min", "问题", "材料性质散落在论文文本/表/图中，手工整理慢且关系容易配错。"],
        ["1–3 min", "原论文", "ComProScanner 用检索、全文获取、RAG、多 agent、清洗评价构成端到端框架。"],
        ["3–5 min", "我们的 Tc 工作", "不复制主框架，用 preset、高召回候选、DOI 可选、NUL 修复和可恢复 runner 适配 Tc。"],
        ["5–7 min", "数据流", "PDF → Docling/章节 CSV → 规则+PhysBERT 候选 → Qwen 判定 → DeepSeek 抽取 → JSON/Gold。"],
        ["7–8 min", "结果", f"前30篇 strict：P={m.get('precision',0):.3f}, R={m.get('recall',0):.3f}, F1={m.get('f1',0):.3f}；主要瓶颈在上游候选和少量幻觉。"],
        ["8–9 min", "现状边界", "文本链路已可运行；图像链路存在但当前未启用；31–100 尚需完整 Gold 才能评价。"],
        ["9–10 min", "未来", "先冻结 100 篇可复现版本，再做 API 发现/合法 OA 下载、fact-list schema、Ms preset 与独立图像 Gold。"],
    ], [20*mm, 62*mm, 92*mm])]

    story += section_intro("23. 术语表", "这些词在项目讨论中经常混用，建议按下列定义统一。")
    story += [table([
        ["术语", "本项目中的准确含义"],
        ["Tc", "居里/相关铁电或磁性相变温度，具体纳入边界由 preset 与 Gold 规范决定。"],
        ["Preset", "一组属性科学配置：关键词、候选信号、identifier/extractor 注释、示例和运行默认项。"],
        ["Prefilter", "LLM 之前的确定性论文相关性门控。"],
        ["Candidate", "真正送给 identifier/extractor 的文本；通常小于全文。"],
        ["RAG", "从向量库检索相关片段并补充上下文；不等于生成最终事实。"],
        ["PhysBERT", "材料科学领域 embedding 模型，用来把文本转为向量。"],
        ["Chroma", "存储和查询向量/文本块的本地数据库。"],
        ["Gold", "经人工查原文确认的参考事实集合。"],
        ["Prediction", "模型输出；未审核前不能视为数据库真值。"],
        ["COMPLETED", "程序成功且输出了至少一个值；不保证每条都正确或没有遗漏。"],
        ["DOI", "论文持久标识符；用于关联与去重，但本地无 DOI 文件仍可抽取。"],
    ], [35*mm, 139*mm])]

    story += section_intro("24. 参考资料与本地证据", "报告中的工程描述来自当前工作树与产物快照；论文描述来自正式 RSC 页面与 arXiv 预印本。")
    refs = [
        "Roy, A.; Grisan, E.; Buckeridge, J.; Gattinoni, C. ComProScanner. Digital Discovery 2026, 5, 1794–1808. DOI: 10.1039/D5DD00521C.",
        "RSC HTML: https://pubs.rsc.org/en/content/articlehtml/2026/dd/d5dd00521c",
        "Official repository: https://github.com/slimeslab/ComProScanner",
        "Official documentation: https://slimeslab.github.io/ComProScanner/",
        "arXiv preprint: https://arxiv.org/abs/2510.20362",
        "本地架构说明：docs/architecture.md；docs/about/project-structure.md；docs/usage/*。",
        "当前严格指标：outputs/metrics/tc_final_001_030.json。",
        "当前人工 Gold：outputs/gold/tc_001_030/gold_facts.json。",
        "当前 runner：scripts/run_tc_hybrid_qwen_30.py。",
    ]
    for i, x in enumerate(refs, 1): story.append(P(f"[{i}] {x}"))
    story.append(HRFlowable(width="100%", thickness=0.7, color=colors.HexColor("#CBD5E1"), spaceBefore=10, spaceAfter=8))
    story.append(P("最后结论：这个项目已经具备可解释、可恢复、可扩展的文本抽取主干，但“链路存在”不等于“所有能力已启用”，也不等于“数据库无需人工校验”。目前最合理的工程方向是：冻结当前 100 篇文本管线与审计资产；修正 DOI/输出命名/schema；再以独立 Gold 推进 Ms 和图像抽取。", "callout"))
    return story


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = ReportDoc(str(OUT))
    doc.multiBuild(build_story())
    print(OUT)


if __name__ == "__main__":
    main()
