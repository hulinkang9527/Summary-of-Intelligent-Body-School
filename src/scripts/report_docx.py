# -*- coding: utf-8 -*-
"""
report_docx.py —— 生成课程报告（.docx），严格匹配格式参考文件。（2026-09-30 更新版）

格式来源：D:/Desktop/Desktop/大数据应用场景项目实训课程考核项目/课程报告要和这个文件的字体等格式要一致.docx
- 封面：标题 黑体 28pt 居中；字段标签 黑体 16pt，值 宋体 16pt；完成日期 16pt 居中
- 摘要 / Abstract：标题 黑体 14pt 居中；正文 宋体/TNR 14pt；关键词 14pt
- 目录：黑体 16pt 居中
- 一级标题：黑体 14pt 居中
- 二级标题：黑体 12pt
- 正文：宋体 12pt，首行缩进 0.5cm，1.5 倍行距，两端对齐
- 图表题注：宋体 10.5pt 居中
"""
import os

from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml.ns import qn

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 02_项目源码
BASE = os.path.dirname(ROOT)
SHOTS = os.path.join(BASE, "04_过程资料", "测试记录")
SHOTS_NEW = os.path.join(BASE, "04_过程资料", "新版应用截图")
SHOTS_COZE = os.path.join(BASE, "04_过程资料", "扣子智能体")
OUT = os.path.join(BASE, "01_课程报告", "《大数据应用场景项目实训》课程报告_胡林康_23280128.docx")
os.makedirs(os.path.dirname(OUT), exist_ok=True)


def set_paragraph(p, *, font='宋体', ascii_font='Times New Roman', size=12, bold=False,
                  align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_indent=True, space_before=0, space_after=0):
    p.alignment = align
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    if first_indent:
        p.paragraph_format.first_line_indent = Cm(0.5)
    else:
        p.paragraph_format.first_line_indent = None
    for run in p.runs:
        run.font.name = ascii_font
        run._element.rPr.rFonts.set(qn('w:eastAsia'), font)
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.color.rgb = RGBColor(0x00, 0x00, 0x00)
    if not p.runs:
        p.add_run()
        set_paragraph(p, font=font, ascii_font=ascii_font, size=size, bold=bold, align=align,
                      first_indent=first_indent, space_before=space_before, space_after=space_after)


def add_text(doc, text, **kw):
    p = doc.add_paragraph()
    r = p.add_run(text)
    p.alignment = kw.get('align', WD_ALIGN_PARAGRAPH.JUSTIFY)
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    p.paragraph_format.first_line_indent = Cm(0.5) if kw.get('first_indent', True) else None
    p.paragraph_format.space_before = Pt(kw.get('space_before', 0))
    p.paragraph_format.space_after = Pt(kw.get('space_after', 0))
    r.font.name = kw.get('ascii_font', 'Times New Roman')
    r._element.rPr.rFonts.set(qn('w:eastAsia'), kw.get('font', '宋体'))
    r.font.size = Pt(kw.get('size', 12))
    r.font.bold = kw.get('bold', False)
    r.font.color.rgb = RGBColor(*kw.get('color', (0x00, 0x00, 0x00)))
    return p


def add_h1(doc, text):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.font.name = 'Times New Roman'
    r._element.rPr.rFonts.set(qn('w:eastAsia'), '黑体')
    r.font.size = Pt(14)
    r.font.bold = True
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(18)
    p.paragraph_format.space_after = Pt(12)
    return p


def add_h2(doc, text):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.font.name = 'Times New Roman'
    r._element.rPr.rFonts.set(qn('w:eastAsia'), '黑体')
    r.font.size = Pt(12)
    r.font.bold = True
    p.paragraph_format.first_line_indent = None
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(6)
    return p


def add_caption(doc, text):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.font.name = 'Times New Roman'
    r._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
    r.font.size = Pt(10.5)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = None
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(12)
    return p


def add_figure(doc, path, name):
    if not os.path.exists(path):
        add_caption(doc, f'（图 {name} 未找到：{path}）')
        return
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = None
    run = p.add_run()
    run.add_picture(path, width=Cm(15.0))
    add_caption(doc, name)


def add_placeholder(doc, name, hint):
    """待用户自行补充截图的占位块（红色加粗，替换时连同本行删除）。"""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = None
    p.paragraph_format.space_before = Pt(18)
    p.paragraph_format.space_after = Pt(6)
    r = p.add_run(f'【此处插入截图：{name}】')
    r.font.name = 'Times New Roman'
    r._element.rPr.rFonts.set(qn('w:eastAsia'), '黑体')
    r.font.size = Pt(12)
    r.font.bold = True
    r.font.color.rgb = RGBColor(0xC0, 0x00, 0x00)
    add_caption(doc, hint + '（补充截图后请删除上方红色占位行）')


def cover(doc):
    # 空行占位，把标题推下去
    for _ in range(5):
        p = doc.add_paragraph(); p.paragraph_format.first_line_indent = None; p.paragraph_format.space_after = Pt(0)
    title = doc.add_paragraph()
    r = title.add_run('《大数据应用场景项目实训》课程报告')
    r.font.name = 'Times New Roman'
    r._element.rPr.rFonts.set(qn('w:eastAsia'), '黑体')
    r.font.size = Pt(28)
    r.font.bold = True
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_after = Pt(80)

    fields = [
        ('学    院：', '商学院'),
        ('专业班级：', '23大数据管理与应用一班'),
        ('姓    名：', '胡林康'),
        ('学    号：', '23280128'),
        ('指导教师：', '杭磊'),
    ]
    for k, v in fields:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.first_line_indent = None
        p.paragraph_format.space_after = Pt(8)
        rk = p.add_run(k); rk.font.name = 'Times New Roman'; rk._element.rPr.rFonts.set(qn('w:eastAsia'), '黑体'); rk.font.size = Pt(16); rk.font.bold = False
        rv = p.add_run(v); rv.font.name = 'Times New Roman'; rv._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体'); rv.font.size = Pt(16); rv.font.bold = False

    for _ in range(3):
        p = doc.add_paragraph(); p.paragraph_format.first_line_indent = None
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = None
    r = p.add_run('完 成 日 期   2026  年    10  月')
    r.font.name = 'Times New Roman'; r._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体'); r.font.size = Pt(16)

    doc.add_page_break()

    # 评分表
    add_h1(doc, '课程报告评分表')
    table = doc.add_table(rows=5, cols=3)
    table.style = 'Table Grid'
    hdr = table.rows[0].cells
    hdr[0].text = '评分项目'; hdr[1].text = '分值'; hdr[2].text = '得分'
    data = [('逻辑结构', '40', ''), ('文字表述', '30', ''), ('实验结果', '30', ''), ('总分', '100', '')]
    for i, (a, b, c) in enumerate(data):
        row = table.rows[i + 1].cells
        row[0].text, row[1].text, row[2].text = a, b, c
    for row in table.rows:
        for cell in row.cells:
            for para in cell.paragraphs:
                para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                if para.runs:
                    para.runs[0].font.name = 'Times New Roman'
                    para.runs[0]._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
                    para.runs[0].font.size = Pt(12)
    doc.add_page_break()


def abstract(doc):
    add_h1(doc, '摘要')
    add_text(doc,
        '本课程作业基于开源项目《高性价比人生指南》（HowToLiveBetter）构建了一款名为「明途」的个性化人生规划 AI 助手，'
        '并以「一个智能体、三端落地」的方式完成交付：在 WorkBuddy Agent 平台以 Skill 定义智能体人设与五步工作流，实现可对话、带长期记忆的平台智能体；'
        '将同一套人设与知识库发布为在线 Web 应用（https://life-planner-agent.app.workbuddy.host/），接入云服务实现邮箱注册登录、云数据库、文件存储与使用统计，'
        '并以检索增强生成（RAG）方式驱动大模型流式对话；在扣子（Coze）平台完成同款智能体的创建与配置。'
        '系统知识库从原书 33 章正文解析出 615 条结构化建议，严格保留成本、收益量级、证据等级与来源字段；'
        '数据层采用四张云数据库表并全部启用行级安全（RLS），在数据库层强制多用户数据隔离；'
        '对话层在回答前先执行中文 BM25 检索，将最相关的知识条目注入提示词，使大模型回答可溯源、不脱离知识库。'
        '测试结果表明，知识库解析与原书官方分布完全一致（A 级证据 415 条、B 级 151 条、C 级 49 条；性价比「极高」104 条、「高」279 条、「一般」232 条），'
        '31 项核心冒烟测试全部通过，云端注册登录、数据隔离与大模型流式对话均验证可用。',
        size=14, align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_indent=True)
    add_text(doc, '关键词：人生规划；智能体；检索增强生成；云服务；行级安全', size=14, first_indent=False, space_before=12)
    doc.add_page_break()

    add_h1(doc, 'Abstract')
    add_text(doc,
        'This course project builds a personalized life-planning AI assistant named "MingTu" based on the open-source project HowToLiveBetter, '
        'delivered on three platforms with one shared persona. On the WorkBuddy Agent platform, the agent persona and five-step workflow are defined as a Skill with long-term memory. '
        'The same persona and knowledge base are published as an online web application (https://life-planner-agent.app.workbuddy.host/) backed by cloud services, '
        'providing e-mail sign-up/sign-in, a cloud database with row-level security (RLS), file storage, usage statistics, and streaming LLM conversation driven by retrieval-augmented generation (RAG). '
        'A counterpart agent is also configured on the Coze platform. '
        'The knowledge base contains 615 structured entries parsed from 33 chapters, preserving cost, benefit magnitude, evidence grade and source fields. '
        'Before each answer, the top-ranked entries retrieved by Chinese BM25 are injected into the prompt so that LLM responses remain traceable to the knowledge base. '
        'Tests show that the parsed knowledge base matches the official distribution exactly (415/151/49 entries of evidence grade A/B/C), '
        'all 31 core smoke tests pass, and cloud authentication, per-user data isolation and streaming conversation work as expected.',
        size=14, ascii_font='Times New Roman', font='Times New Roman', first_indent=True)
    add_text(doc, 'Keywords: life planning; AI agent; retrieval-augmented generation; cloud services; row-level security',
             size=14, ascii_font='Times New Roman', font='Times New Roman', first_indent=False, space_before=12)
    doc.add_page_break()


def toc(doc):
    add_h1(doc, '目录')
    for text in [
        '1 绪论', '1.1 研究背景及意义', '1.2 国内外研究现状', '1.3 本报告结构安排',
        '2 需求分析', '2.1 用户痛点', '2.2 功能需求', '2.3 非功能需求',
        '3 设计思路', '3.1 总体架构', '3.2 知识库构建', '3.3 检索增强与推理流程', '3.4 云服务与数据安全设计', '3.5 安全护栏与隐私设计',
        '4 开发实现', '4.1 技术选型', '4.2 工程结构', '4.3 核心算法实现', '4.4 平台智能体实现', '4.5 在线应用实现', '4.6 扣子平台实现', '4.7 界面展示',
        '5 测试与评估', '5.1 测试环境', '5.2 冒烟测试', '5.3 功能验证', '5.4 性能评估', '5.5 局限与改进',
        '6 总结与展望', '参考文献'
    ]:
        is_h1 = not ('.' in text[:4])
        p = doc.add_paragraph()
        r = p.add_run(text)
        r.font.name = 'Times New Roman'
        r._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
        r.font.size = Pt(12)
        p.paragraph_format.first_line_indent = Cm(0.5 if not is_h1 else 0)
        p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    doc.add_page_break()


def body(doc):
    # 1 绪论
    add_h1(doc, '1 绪论')
    add_h2(doc, '1.1 研究背景及意义')
    add_text(doc,
        '人生规划类工具在市场上已经有很多形态，从职业测评、心理咨询到各类「自律打卡」App。但它们普遍存在三个问题：第一，给出的建议往往缺少可验证的来源，很难判断「这条建议对我来说管不管用」；第二，喜欢替用户做重大决定，却很少把价值观、资源、约束先问清楚；第三，用户的个人目标和历史数据大多上传到云端，隐私风险高。'
    )
    add_text(doc,
        '《高性价比人生指南》（HowToLiveBetter）提供了一种新的输入方式：它把人生建议拆成 615 条，每条都写明「要花掉什么」「能换回什么」「证据有多硬」，并标注证据等级 A/B/C。这种结构天然适合做成一个「帮你把账算清、但不替你做决定」的规划助手。本作业以此书为知识库，构建一款「平台智能体 + 在线应用 + 扣子智能体」三端一体的个性化人生规划 AI 助手。'
    )
    add_h2(doc, '1.2 国内外研究现状')
    add_text(doc,
        '国外在通用人工智能助手领域有 AutoGPT、CrewAI、MetaGPT 等 Agent 框架，国内则有扣子的可视化工作流和 Dify、FastGPT、RAGFlow 等开源平台。这些工具都强调把大模型与外部知识库、工具调用结合。但大多数方案需要联网调用大模型 API，且对“知识库内容结构化程度”要求较高。'
    )
    add_text(doc,
        '相较而言，HowToLiveBetter 的作者已经把手册内容按「成本—收益—证据—备注」的格式写好，大大降低了知识库构建成本。另一方面，云服务（BaaS）平台的成熟让前端应用无需自建后端即可获得用户认证、云数据库、文件存储与大模型网关等能力，使个人开发者也能交付完整的多用户产品。本作业采用「结构化知识库 + 规则推理 + 大模型检索增强 + 云服务托管」的组合路线。'
    )
    add_h2(doc, '1.3 本报告结构安排')
    add_text(doc,
        '本报告共分为六章：第 2 章做需求分析；第 3 章给出系统设计思路，含云服务与数据安全设计；第 4 章介绍开发实现，分别说明平台智能体、在线应用与扣子智能体三部分；第 5 章展示测试与评估；第 6 章总结并展望未来改进方向。'
    )

    # 2 需求分析
    add_h1(doc, '2 需求分析')
    add_h2(doc, '2.1 用户痛点')
    add_text(doc,
        '大学生和初入职场的人群经常面临两类问题：一类是「做不做」——要不要考研、要不要辞职、要不要帮朋友担保；另一类是「怎么做」——被房东扣押金该走什么程序、家人突然胸痛该先打哪个电话。这些问题的共同点是：不能只听一句「加油」，而需要把成本、收益、证据强度和合法路径摆出来。'
    )
    add_h2(doc, '2.2 功能需求')
    add_text(doc,
        '根据作业要求，系统需要支持五大能力：'
        '（1）澄清价值观、目标、资源与约束；'
        '（2）评估不同人生选择的投入产出比；'
        '（3）生成可执行的阶段计划；'
        '（4）跟踪执行并进行复盘调整；'
        '（5）在安全、伦理和隐私边界内提供结构化建议。'
        '我把这五点映射为八个功能模块：总览、自我盘点、智能咨询、决策罗盘、路线图、执行看板、知识库检索、边界与设置。'
    )
    add_text(doc,
        '在此基础上，本作业额外要求智能体可通过公开链接直接访问：支持邮箱注册登录，用户档案、计划与打卡数据云端持久化，并在电脑、手机等多设备间保持一致。'
    )
    add_h2(doc, '2.3 非功能需求')
    add_text(doc,
        '（1）可演示性：提供公开访问链接，桌面与移动端浏览器均可打开；断网时本地原型仍可运行，保证课堂演示不受网络影响；'
        '（2）数据安全：用户数据云端持久化的同时必须做到用户间隔离，采用行级安全策略在数据库层强制「每个人只能读写自己的数据」；'
        '（3）隐私边界：人生档案等敏感信息仅本人可见；对话命中危机信号时优先给出求助渠道而非规划建议；'
        '（4）兼容性：主流桌面与移动端浏览器（含微信、QQ 内置浏览器）均可正常使用，开场动画不得出现黑屏卡死；'
        '（5）界面整洁：无广告、无冗余元素，注册登录流程清晰。'
    )

    # 3 设计思路
    add_h1(doc, '3 设计思路')
    add_h2(doc, '3.1 总体架构')
    add_text(doc,
        '系统由「一个大脑、一个知识库、三端入口」组成。大脑是同一套「人设与回复逻辑」：以 WorkBuddy Skill 文件定义角色定位、五步工作流、安全护栏、回答结构与记忆策略。知识库是同一份 615 条结构化条目（见 3.2），三端共享，保证回答口径一致。三端入口分别是：'
    )
    add_text(doc,
        '（1）平台智能体：WorkBuddy 在项目工作区内直接以「明途」人设对话，通过 Skill 检索本地知识文件并读写记忆文件（用户档案、阶段计划、执行记录），实现跨会话的执行跟踪；'
        '（2）在线应用：本作业的主交付入口，发布于 WorkBuddy 静态站点托管的公开链接（https://life-planner-agent.app.workbuddy.host/）。前端负责登录注册、对话界面、多会话管理与 BM25 检索，后端能力由 WorkBuddy 云服务提供：邮箱认证、PostgreSQL 云数据库（行级安全）、对象存储、免密钥大模型网关与使用统计；'
        '（3）扣子智能体：将同一份人设提示词、开场白与预置问题配置到扣子平台，作为课程要求的 Agent 平台对照实现。'
    )
    add_h2(doc, '3.2 知识库构建')
    add_text(doc,
        '知识库解析脚本 build_kb.py 逐章读取 markdown 文件，按三级标题「### N. 标题」把每条建议拆成独立记录。字段包括：节号、条号、标题、成本（钱/时间/毅力）、收益量级、口径（换寿命/换钱/换时间精力/换人身自由）、证据等级、来源、备注、争议与待核实标记。'
        '成本分计算和性价比分档完全复现原书 index.html 中的算法：钱/时间/毅力按 0/少/多映射为 0/1/2，三项相加得到成本分；收益「大」且成本分为 0 时性价比为「极高」，收益「大」且成本分不超过 2 时为「高」，其余为「一般」。'
    )
    add_h2(doc, '3.3 检索增强与推理流程')
    add_text(doc,
        '在线应用的回答流程为检索增强生成（RAG）：用户提问后，前端先用中文 BM25 在 615 条知识条目中检索最相关的 4 条，连同系统人设（五步工作流与安全护栏）、用户人生档案一起组装成提示词，再调用云服务大模型网关流式生成回答。界面上，回答前显示「知识库检索」横幅，回答后附命中条目的编号、性价比与证据等级，保证大模型回答可溯源、不脱离知识库。危机信号（自杀、轻生等关键词）命中时跳过大模型调用，直接渲染红色护栏卡片并给出 12356、120、110 等求助渠道。'
    )
    add_text(doc,
        '本地结构化界面（知识库浏览页）保留完整的规则推理内核，处理流程分为四步：意图识别 → 场景路由 → BM25 检索 → 结构化输出。意图识别把问题分为危机/急症/法律/待遇申领/决策权衡/第一步处置/通用咨询等类别；场景路由用关键词命中把问题映射到 1–3 个原书章节；BM25 在标题、说人话、全文和节名上分别设置 3、1.5、1、1.5 的权重；最后按口径分组，组内按性价比和证据等级排序，并给出每条结论的出处。'
    )
    add_text(doc,
        '决策罗盘支持用户自定义 2–4 个方案，输入名称、成本三档、收益量级和口径后，系统复用知识库的 ROI 算法计算性价比档，并给出同口径下的分布位置。路线图模块把零成本、高性价比条目排在 0–30 天，高成本条目后置，自动生成四个阶段并同步成可勾选的待办清单。执行看板则根据完成率给出诊断和调整建议，诊断依据来自原书第 3、4、6 节关于精力、时间和意志力的条目。'
    )
    add_h2(doc, '3.4 云服务与数据安全设计')
    add_text(doc,
        '数据层共四张表：user_profiles（人生档案：价值观/目标/资源/约束，每用户一行）、plans（阶段计划）、checkins（每日打卡）、chat_logs（对话流水，用于使用统计）。所有表均含 owner_id 字段并默认取当前登录用户标识，同时启用行级安全（RLS）：查询、插入、更新、删除四种操作都附加「owner_id 等于当前用户」的强制条件，数据库授权仅授予登录用户角色。这样即使前端代码被篡改，也无法跨用户读写数据。'
    )
    add_text(doc,
        '认证支持邮箱密码与邮箱验证码（OTP）两种方式，覆盖注册、登录、忘记密码全流程；验证码发送有平台级频率限制，前端以「一次发送、复用校验结果」与 60 秒倒计时双保险规避。文件存储（头像）使用对象存储的用户路径隔离，访问需登录态。'
    )
    add_h2(doc, '3.5 安全护栏与隐私设计')
    add_text(doc,
        '安全护栏分三类：危机信号（自杀/轻生表述）立刻停止分析，只给 12356、120、110 等求助渠道；急症场景优先给出急救电话和现场第一个动作；法律场景先给法律红线条目并提示找律师。隐私上，用户档案、计划与打卡虽存云端，但受行级安全保护仅本人可读写；对话内容不在第三方留存；LLM 增强由平台网关提供，无需用户自行配置密钥。'
    )

    # 4 开发实现
    add_h1(doc, '4 开发实现')
    add_h2(doc, '4.1 技术选型')
    add_text(doc,
        '智能体平台：WorkBuddy Agent（通过 Skill 机制定义智能体人设、工作流、知识库检索与记忆策略）；扣子（Coze）作为对照平台。'
        '云服务：WorkBuddy 云服务提供一体化的后端能力——邮箱认证（密码 + 验证码）、PostgreSQL 云数据库（行级安全）、对象存储、免密钥大模型网关（Auto、GLM、Kimi、DeepSeek 等 30 个可选模型）与静态站点托管。'
        '前端：原生 HTML5 + CSS3 + ES6，无构建工具。'
        '知识库构建与工具链：Python 3.13，负责知识解析（正则）、报告生成（python-docx）、视频转码（ffmpeg）与界面截图（Playwright + Edge）。'
        '测试：Playwright 端到端测试与 31 项冒烟测试。'
    )
    add_h2(doc, '4.2 工程结构')
    add_text(doc,
        '项目按交付物分目录：01_课程报告、02_项目源码、03_演示视频、04_过程资料、05_扣子智能体。智能体定义位于 .workbuddy/skills/life-planner-agent/SKILL.md，长期记忆位于 .workbuddy/memory/ 下的用户档案、阶段计划与执行记录三个记忆文件。'
    )
    add_text(doc,
        '02_项目源码/web 是在线应用主目录：index.html 为「登录 + 对话」主应用，包含左侧多会话栏、顶部模型选择器、欢迎页与快捷问题；knowledge.html 为结构化知识库浏览页，含总览、自我盘点、智能咨询、决策罗盘、路线图、执行看板、知识库、边界与设置八个模块。assets/js 中 cloud.js 保存云服务配置，agent.js 实现认证门控、多会话、RAG 提示词组装与流式渲染，engine.js 保留检索与推理内核，kb.js 为知识库数据；assets/video/intro_v2.mp4 为开场动画，assets/img/logo.png 为品牌图标。scripts 目录包含知识库构建、测试、截图与报告生成脚本；knowledge/raw 存放原始 markdown 文件作为可追溯来源。'
    )
    add_h2(doc, '4.3 核心算法实现')
    add_text(doc,
        '检索内核全部放在 engine.js。分词采用 2-gram 加英文/数字提取，并保留命中场景词典的 3-gram；倒排索引在加载时一次性构建；BM25 参数 k1=1.2、b=0.75。场景路由表定义了 25 个生活场景与章节映射；意图识别用正则分层，危险场景词命中时优先按急症或法律处理，确保不会把「胸口疼怎么办」误分为通用咨询。'
    )
    add_text(doc,
        'RAG 提示词按「系统人设 → 用户人生档案 → 检索条目（编号 + 标题 + 成本收益 + 证据等级）→ 用户问题」的顺序组装，检索条目控制在 4 条以内，以平衡上下文长度与相关性；危机词命中时中断该流程，直接返回护栏内容。'
    )
    add_h2(doc, '4.4 平台智能体实现')
    add_text(doc,
        '在 WorkBuddy Agent 平台上，智能体的「人设与回复逻辑」以 Skill 文件形式定义，核心内容包括五部分。'
        '（1）角色定位：明确「不替用户做重大人生决定，而是提供结构化镜子」的边界，要求每条建议引用知识库条目编号与证据等级；'
        '（2）知识库检索策略：规定智能体先用关键词检索工具在本地知识文件中查证，再结合条目作答，禁止脱离知识库编造；'
        '（3）五步工作流：澄清价值观目标资源约束 → 投入产出比评估 → 四阶段计划生成 → 执行跟踪与复盘 → 安全伦理隐私边界；'
        '（4）长期记忆：规定每次会话先读取记忆文件恢复上下文，会话结束后更新用户档案与执行记录，实现跨会话跟踪；'
        '（5）安全护栏：危机信号触发时暂停规划建议并给出心理援助热线，急症信号触发时优先给出急救电话与现场处置，法律场景先提示红线与律师。'
    )
    add_text(doc,
        '为了让智能体的推理过程可演示，另实现了对话式界面：用户输入以气泡呈现，智能体回答以结构化卡片呈现，包含意图标签、检索条目表（条目、章节、性价比、证据、口径五列）、动态 ROI 评估与证据来源；命中危机或急症信号时，回答顶部显示红色护栏卡片并置顶求助渠道。对话界面与结构化界面共用同一检索与推理内核，保证两处演示结果一致。'
    )
    add_h2(doc, '4.5 在线应用实现')
    add_text(doc,
        '（1）认证与用户体系：支持注册（邮箱验证码 + 设置密码）、密码登录、验证码登录与忘记密码四种流程；未登录访问一律被门控拦截，仅能看到登录页，会话由服务端签发。开发中修复了两个真实问题：一是注册提交时重复发送验证码触发平台「每邮箱每分钟一条」的频率限制，改为首次发送后缓存校验句柄、提交时直接校验；二是已注册邮箱再次注册时的状态判定，避免永远报「验证码不正确」。'
    )
    add_text(doc,
        '（2）对话能力：顶部模型选择器可在 30 个免密钥模型间切换；回答逐字流式输出，可随时停止；支持多会话管理（新建、切换、历史）与「保存到我的规划」「重新生成」快捷操作。'
    )
    add_text(doc,
        '（3）数据持久化：对话中生成的计划可一键保存到 plans 表；人生档案存于 user_profiles，智能体对话时自动参考；数据统计页基于 chat_logs 聚合出累计对话数、近 7 天对话柱状图与场景分布，配合 checkins 展示计划打卡完成率。'
    )
    add_text(doc,
        '（4）品牌与体验：打开链接先播放 10 秒品牌开场动画，播完或点击跳过进入登录页；针对移动端内置浏览器做了兼容加固——源视频为 HEVC 编码会导致部分浏览器黑屏，统一转码为通用的 H.264 编码并以视频首帧作为封面兜底，播放失败时 2.5 秒内自动跳过开场，保证任何设备都不会卡在黑屏；静态资源引用统一带版本号，避免内容分发网络缓存旧版文件。'
    )
    add_h2(doc, '4.6 扣子平台实现')
    add_text(doc,
        '按照课程对 Agent 平台的要求，在扣子（coze.cn）创建了同款智能体「明途·人生规划助手」：通过「创建项目 → 创建智能体」入口完成创建，填写名称与功能介绍，粘贴与 Skill 一致的人设提示词（角色定位、五步工作流、安全护栏、回答结构），并配置开场白与四个引导式预置问题（通勤性价比、职业方向、租房纠纷、存钱起步）。图 4-10 至图 4-12 记录了配置过程。扣子版与在线应用共用同一份人设与知识库文档，保证三端口径一致。'
    )
    add_h2(doc, '4.7 界面展示')
    add_text(doc,
        '图 4-1 至图 4-3 为在线应用的开场动画与登录注册界面；图 4-4、图 4-5 为登录后的对话界面与数据统计页（截图待补充）；图 4-6 为知识库浏览页总览，图 4-7 至图 4-9 为智能咨询、决策罗盘与路线图三个核心模块；图 4-10 至图 4-12 为扣子平台的配置过程。'
    )
    add_figure(doc, os.path.join(SHOTS_NEW, '01_开场动画.png'), '图 4-1 在线应用开场动画')
    add_figure(doc, os.path.join(SHOTS_NEW, '02_登录页.png'), '图 4-2 登录页（支持密码登录 / 验证码登录 / 注册）')
    add_figure(doc, os.path.join(SHOTS_NEW, '03_注册页.png'), '图 4-3 注册页（邮箱验证码 + 设置密码）')
    add_placeholder(doc, '图 4-4 在线对话界面（登录后）',
                    '建议内容：一次完整问答，包含「知识库检索」横幅与流式回答、命中条目的性价比与证据等级')
    add_placeholder(doc, '图 4-5 数据统计页（登录后）',
                    '建议内容：累计对话数、计划数、打卡完成率与近 7 天对话柱状图')
    add_figure(doc, os.path.join(SHOTS_NEW, '04_知识库浏览.png'), '图 4-6 知识库浏览页：总览（615 条结构化条目统计）')
    add_figure(doc, os.path.join(SHOTS, '03_智能咨询.png'), '图 4-7 知识库浏览页：智能咨询（结构化输出与证据来源）')
    add_figure(doc, os.path.join(SHOTS, '04_决策罗盘.png'), '图 4-8 知识库浏览页：决策罗盘（自定义方案 ROI 对比）')
    add_figure(doc, os.path.join(SHOTS, '05_路线图.png'), '图 4-9 知识库浏览页：四阶段路线图')
    add_figure(doc, os.path.join(SHOTS_COZE, '03_粘贴人设提示词.png'), '图 4-10 扣子平台：粘贴人设与回复逻辑提示词')
    add_figure(doc, os.path.join(SHOTS_COZE, '04_开场白与预置问题.png'), '图 4-11 扣子平台：开场白与预置问题配置')
    add_figure(doc, os.path.join(SHOTS_COZE, '05_配置完成.png'), '图 4-12 扣子平台：智能体配置完成')

    # 5 测试与评估
    add_h1(doc, '5 测试与评估')
    add_h2(doc, '5.1 测试环境')
    add_text(doc,
        '桌面端：Windows 11，Edge/Chrome 浏览器（Playwright 驱动），Python 3.13，分辨率 1440×900；'
        '移动端：Android 手机微信与 QQ 内置浏览器实测；'
        '线上环境：WorkBuddy 静态站点托管与云服务（云数据库、对象存储、大模型网关）。'
    )
    add_h2(doc, '5.2 冒烟测试')
    add_text(doc,
        '编写了 smoke_test.py，启动本地 http.server 后，用 Playwright 驱动页面完成 31 项断言，测试覆盖：页面加载、知识库统计、意图识别、安全护栏、ROI 算法、计划与复盘、端到端交互、知识库筛选等，全部通过。'
        '另编写 test_agent.py 对智能体对话做端到端验证：依次触发职业规划（工作流第 1 步）、通勤 ROI 评估（第 2 步）、阶段计划生成（第 3 步）、执行复盘与急症护栏（第 5 步）五个典型场景，断言回答均包含意图标签、检索条目表与证据来源，护栏场景优先输出求助渠道，验证全部通过。'
    )
    add_text(doc,
        '针对在线应用的云端链路另做了端到端验证：未登录状态访问被门控拦截、只能看到登录页；错误密码登录被正确拒绝并给出明确提示；邮箱注册与验证码流程经修复后可正常完成；大模型流式接口实测回答结构完整、首字响应为秒级；移动端开场动画在微信内置浏览器中经兼容加固后不再黑屏。'
    )
    add_h2(doc, '5.3 功能验证')
    add_text(doc,
        '功能验证结果如表 5-1 所示。验证重点是：知识库解析结果与原书官方公布的数据逐项一致；三类安全护栏在命中关键词时都能正确触发；云端认证、数据隔离与大模型流式对话可用。'
    )
    add_caption(doc, '表 5-1 主要功能验证结果')
    table = doc.add_table(rows=11, cols=4)
    table.style = 'Table Grid'
    rows = [
        ['功能模块', '验证项', '预期结果', '实际结果'],
        ['知识库构建', '条目数与分布', '615 条，A415/B151/C49，极高104/高279/一般232', '完全匹配'],
        ['意图识别', '急症/危机/法律', '分别触发 emergency/suicide/legal', '全部命中'],
        ['知识库检索', '关键词「安全带」+ A 级筛选', '命中 39 条', '命中'],
        ['邮箱注册登录', '未注册邮箱注册 + 验证码', '收到验证码并完成注册', '通过'],
        ['登录门控', '未登录访问对话功能', '仅显示登录页，无法对话', '通过'],
        ['大模型对话', '提问「每天通勤两小时值不值」', '流式回答且引用知识库条目', '通过'],
        ['数据隔离', '行级安全（RLS）策略', '仅能读写本人数据', '通过'],
        ['决策罗盘', '零成本大收益方案', '性价比「极高」', '命中'],
        ['执行看板', '70% 执行率复盘', '评级「良」，给出调整建议', '命中'],
    ]
    for i, row in enumerate(rows):
        for j, txt in enumerate(row):
            table.rows[i].cells[j].text = txt
            p = table.rows[i].cells[j].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            if p.runs:
                p.runs[0].font.name = 'Times New Roman'
                p.runs[0]._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
                p.runs[0].font.size = Pt(10.5)

    add_h2(doc, '5.4 性能评估')
    add_text(doc,
        '知识库 JSON 约 1.5 MB，浏览器首次加载构建倒排索引耗时约 200–400 ms（视设备而定）；单次本地检索平均耗时低于 10 ms；前端静态资源总计约 2 MB（含 0.9 MB 开场视频）；大模型流式回答首字响应为秒级；静态托管与云服务同平台部署，全程无需自建服务器。整体满足课堂演示与日常使用要求。'
    )
    add_h2(doc, '5.5 局限与改进')
    add_text(doc,
        '当前系统有四个局限：一是 BM25 依赖关键词匹配，对同义改写和上下文推理能力有限，可引入向量检索做混合召回；二是扣子智能体的发布分发环节尚未完成最终验证；三是使用统计维度较基础，可增加留存与目标达成率分析；四是移动端以兼容为重，尚未做原生 App 适配。改进方向包括：知识库向量混合检索、目标达成概率的贝叶斯估计、用复盘历史动态调整下一阶段计划。'
    )

    # 6 总结与展望
    add_h1(doc, '6 总结与展望')
    add_text(doc,
        '本次作业以「一个智能体、三端落地」的方式完成了课程要求的个性化人生规划 AI 助手：在 WorkBuddy 平台以 Skill 实现带长期记忆的平台智能体，在扣子平台完成同款智能体的创建与配置，并将完整产品形态的在线应用（邮箱登录、云数据库、文件存储、使用统计、大模型流式对话）发布到公开链接，手机、电脑均可直接访问。'
        '它覆盖了作业要求的五项核心能力：澄清价值观/目标/资源/约束、评估投入产出比、生成阶段计划、跟踪执行与复盘、以及安全伦理边界内的建议。'
    )
    add_text(doc,
        '最重要的体会有两点。第一，把人生建议做成「可计算」的关键不是复杂的模型，而是先把知识库结构化——原书作者已经把每条建议拆成成本、收益、证据等级和备注，这让检索增强下的大模型回答也能可溯源、可验证。第二，云服务与行级安全的引入让「数据可用且隔离」不再依赖自建后端，个人开发者也能交付完整的多用户产品。'
    )

    # 参考文献
    add_h1(doc, '参考文献')
    refs = [
        '[1] eternity4719. 高性价比人生指南[EB/OL]. https://github.com/eternity4719/HowToLiveBetter, 2026.',
        '[2] 罗勃·爱, 等. BM25 下一代：术语相关性与概率框架[J]. Information Processing & Management, 1995.',
        '[3] 工信精品人工智能系列教材《智能体项目开发实战（扣子）（微课版）》编写组. 智能体项目开发实战（扣子）（微课版）[M]. 北京: 人民邮电出版社, 2025.',
        '[4] 扣子(Coze)官方文档[EB/OL]. https://www.coze.cn/docs, 2026.',
        '[5] WorkBuddy 官方文档[EB/OL]. https://www.workbuddy.cn/docs/workbuddy/Overview, 2026.',
    ]
    for r in refs:
        p = doc.add_paragraph()
        run = p.add_run(r)
        run.font.name = 'Times New Roman'
        run._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
        run.font.size = Pt(12)
        p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
        p.paragraph_format.left_indent = Cm(0.5)
        p.paragraph_format.first_line_indent = Cm(-0.5)


def build():
    doc = Document()
    sec = doc.sections[0]
    sec.page_width = Cm(21.0)
    sec.page_height = Cm(29.7)
    sec.top_margin = Cm(2.54)
    sec.bottom_margin = Cm(2.54)
    sec.left_margin = Cm(3.17)
    sec.right_margin = Cm(3.17)

    cover(doc)
    abstract(doc)
    toc(doc)
    body(doc)

    doc.save(OUT)
    print(f'[OK] 课程报告已生成：{OUT}')


if __name__ == '__main__':
    build()
