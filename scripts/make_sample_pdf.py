"""生成示例研报 PDF（用于测试 PDF 解析链路）。

用法：python scripts/make_sample_pdf.py
输出：data/samples/示例-消费龙头2025年报点评.pdf
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


OUT = Path(__file__).resolve().parents[1] / "data" / "samples" / "示例-消费龙头2025年报点评.pdf"

STYLES = getSampleStyleSheet()
pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
H1 = ParagraphStyle("H1cn", parent=STYLES["Heading1"], fontName="STSong-Light", fontSize=16, leading=22)
H2 = ParagraphStyle("H2cn", parent=STYLES["Heading2"], fontName="STSong-Light", fontSize=13, leading=18)
BODY = ParagraphStyle("BodyCN", parent=STYLES["BodyText"], fontName="STSong-Light", fontSize=10.5, leading=16)

TEXT = [
    ("h1", "消费龙头2025年报点评：品牌升级兑现，盈利质量持续改善"),
    ("body", "机构：华泰证券 ｜ 分析师：张三 ｜ 日期：2026-03-18 ｜ 评级：买入 ｜ 目标价：68.00元"),
    ("h2", "投资要点"),
    ("body", "公司2025年实现营业收入128.7亿元，同比增长14.4%；归母净利润21.3亿元，同比增长18.9%。"
     "2025年毛利率32.5%，较2024年提升0.7个百分点；净利率16.6%。"
     "2025年ROE为18.2%，每股收益EPS为1.92元。当前市盈率PE约35.4倍，市净率PB约6.1倍。"),
    ("h2", "财务预测"),
]

TABLE_DATA = [
    ["指标", "2023", "2024", "2025E", "2026E"],
    ["营业收入(亿元)", "98.2", "112.5", "128.7", "145.3"],
    ["归母净利润(亿元)", "15.1", "17.9", "21.3", "24.8"],
    ["毛利率(%)", "30.1", "31.8", "32.5", "33.2"],
    ["净利率(%)", "15.4", "15.9", "16.6", "17.1"],
]


def build() -> None:
    doc = SimpleDocTemplate(str(OUT), pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm)
    story = []
    for kind, content in TEXT:
        story.append(Paragraph(content, H1 if kind == "h1" else H2 if kind == "h2" else BODY))
        story.append(Spacer(1, 6))
    table = Table(TABLE_DATA, colWidths=[4.5 * cm] + [2.6 * cm] * 4)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dde8f3")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTNAME", (0, 0), (-1, -1), "STSong-Light"),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "盈利预测与估值：我们预计公司2026年营业收入145.3亿元、归母净利润24.8亿元，维持买入评级，目标价68元。"
        "风险提示：原材料价格波动、行业竞争加剧、消费复苏不及预期。",
        BODY,
    ))
    doc.build(story)
    print(f"已生成: {OUT}")


if __name__ == "__main__":
    build()
