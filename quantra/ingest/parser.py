"""研报解析：MD / TXT / PDF -> Report。

设计说明（D1 可继续迭代）：
- 确定性优先：指标抽取先用规则实现，数字可复现；LLM 抽取作为第二通道后续接入。
- PDF 的章节识别目前依赖文本中的 markdown 标题，或退化为"每页一节"；
  D1 任务里可以按真实研报的版式补规则。
"""

from __future__ import annotations

import re
from pathlib import Path

from quantra.models import Metric, Report, Section, Table


PERIOD_RE = re.compile(r"(20\d{2}\s*年?\s*(?:Q[1-4])?|20\d{2})")

METRIC_RULES: list[tuple[str, str]] = [
    ("毛利率", r"毛利率[^0-9年]{0,12}(\d+\.?\d*)\s*%"),
    ("净利率", r"净利率[^0-9年]{0,12}(\d+\.?\d*)\s*%"),
    ("营业收入", r"(?:营业收入|营收)[^0-9年]{0,12}(\d+\.?\d*)\s*(亿元|亿|万元|百万元|元)?"),
    ("归母净利润", r"归母净利润[^0-9年]{0,12}(\d+\.?\d*)\s*(亿元|亿|万元|元)?"),
    ("净利润", r"(?:^|[^归母])净利润[^0-9年]{0,12}(\d+\.?\d*)\s*(亿元|亿|万元|元)?"),
    ("ROE", r"(?:ROE|净资产收益率)[^0-9年]{0,12}(\d+\.?\d*)\s*%"),
    ("EPS", r"(?:EPS|每股收益)[^0-9年]{0,12}(\d+\.?\d*)\s*(元)?"),
    ("市盈率PE", r"(?:PE|市盈率)[^0-9年]{0,12}(\d+\.?\d*)"),
    ("市净率PB", r"(?:PB|市净率)[^0-9年]{0,12}(\d+\.?\d*)"),
]

RATING_WORDS = ["买入", "强烈推荐", "推荐", "增持", "中性", "持有", "卖出", "回避"]


def _find_period(text: str, pos: int) -> str:
    """在 pos 之前 80 字符内找最近的时间（2025 / 2025年 / 2025Q3）。"""
    window = text[max(0, pos - 80):pos]
    matches = list(PERIOD_RE.finditer(window))
    if not matches:
        return ""
    raw = matches[-1].group(0)
    return re.sub(r"\s+", "", raw).replace("年", "")


def _source(page: int, heading: str = "") -> str:
    if heading:
        return f"p{page}·{heading}"
    return f"p{page}"


def _extract_from_text(text: str, page: int, heading: str = "") -> list[Metric]:
    metrics: list[Metric] = []
    for name, pattern in METRIC_RULES:
        for m in re.finditer(pattern, text):
            period = _find_period(text, m.start())
            value = m.group(1)
            unit = m.group(2) if m.lastindex and m.lastindex >= 2 else ""
            metrics.append(
                Metric(
                    name=name,
                    value=value,
                    unit=unit,
                    period=period,
                    source=_source(page, heading),
                    raw=m.group(0),
                )
            )
    return metrics


def _extract_from_table(table: Table, page: int, heading: str = "") -> list[Metric]:
    """按表头对齐"指标 × 年份"，避免数值错配期间。"""
    metrics: list[Metric] = []
    if not table.rows:
        return metrics
    header = table.rows[0]
    periods: list[str] = []
    for cell in header:
        m = PERIOD_RE.search(cell)
        periods.append(re.sub(r"\s+", "", m.group(0)).replace("年", "") if m else "")

    for row in table.rows[1:]:
        if not row:
            continue
        row_name = row[0].strip()
        metric_name = row_name
        for rule_name, _pattern in METRIC_RULES:
            if rule_name in row_name:
                metric_name = rule_name
                break
        for col in range(1, min(len(row), len(header))):
            cell = row[col].strip()
            if not re.fullmatch(r"-?\d+\.?\d*", cell):
                continue
            period = periods[col] if col < len(periods) else ""
            metrics.append(
                Metric(
                    name=metric_name,
                    value=cell,
                    period=period,
                    source=_source(page, heading or table.title),
                    raw=row_name,
                )
            )
    return metrics


def _dedupe_metrics(metrics: list[Metric]) -> list[Metric]:
    seen: set[tuple[str, str]] = set()
    out: list[Metric] = []
    for metric in metrics:
        key = (metric.name, metric.period)
        if key in seen:
            continue
        seen.add(key)
        out.append(metric)
    return out


def _rating_of(text: str) -> str:
    for word in reversed(RATING_WORDS):
        if word in text:
            return word
    return ""


def _target_price_of(text: str) -> str:
    m = re.search(r"目标价[^0-9]{0,8}(\d+\.?\d*)\s*元?", text)
    return m.group(1) if m else ""


def _institution_of(text: str) -> str:
    m = re.search(r"(机构|来源)[:：]\s*([\u4e00-\u9fffA-Za-z0-9]{2,30})", text)
    if m:
        return m.group(2)
    m = re.search(r"^([\u4e00-\u9fff]{2,10}(?:证券|基金|研究所|国际))\b", text, re.M)
    return m.group(1) if m else ""


def _date_of(text: str) -> str:
    m = re.search(r"(\d{4}[-年/]\d{1,2}[-月/]\d{1,2})", text)
    return m.group(1) if m else ""


def parse_markdown(text: str, source_path: str) -> Report:
    lines = text.splitlines()
    sections: list[Section] = []
    tables: list[Table] = []
    current: Section | None = None
    table_rows: list[list[str]] = []
    title = ""

    for line in lines:
        stripped = line.strip()
        heading_match = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading_match:
            if current:
                sections.append(current)
            current = Section(
                heading=heading_match.group(2).strip(),
                level=len(heading_match.group(1)),
                page=0,
            )
            if not title:
                title = current.heading
            continue
        if re.match(r"^\s*\|.*\|\s*$", line) and "---" not in line:
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            table_rows.append(cells)
            continue
        if table_rows and stripped == "":
            tables.append(Table(title=f"表格{len(tables) + 1}", page=0, rows=table_rows))
            table_rows = []
        if current:
            current.text += line + "\n"
        elif stripped:
            current = Section(heading="导语", level=0, page=0)
            current.text = stripped + "\n"

    if current:
        sections.append(current)
    if table_rows:
        tables.append(Table(title=f"表格{len(tables) + 1}", page=0, rows=table_rows))

    full_text = text
    # 表格行交给 _extract_from_table 处理，避免按行文本重复抽取且期间错位
    text_for_metrics = "\n".join(
        line for line in full_text.splitlines() if not line.strip().startswith("|")
    )
    metrics = _extract_from_text(text_for_metrics, 0, "全文")
    for table in tables:
        metrics.extend(_extract_from_table(table, 0, table.title))
    metrics = _dedupe_metrics(metrics)

    return Report(
        source_path=source_path,
        title=title,
        institution=_institution_of(full_text),
        date=_date_of(full_text),
        rating=_rating_of(full_text),
        target_price=_target_price_of(full_text),
        summary=re.sub(r"\s+", " ", text)[:300],
        sections=sections,
        tables=tables,
        metrics=metrics,
    )


def parse_pdf(path: str) -> Report:
    import pdfplumber

    sections: list[Section] = []
    tables: list[Table] = []
    metrics: list[Metric] = []
    pages_text: list[str] = []

    with pdfplumber.open(path) as pdf:
        for page_no, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            pages_text.append(text)
            for raw_table in page.extract_tables() or []:
                rows = [[c or "" for c in row] for row in raw_table]
                tables.append(Table(title=f"第{page_no}页表格", page=page_no, rows=rows))
                flat = " ".join(" ".join(row) for row in rows)
                metrics.extend(_extract_from_text(flat, page_no, f"第{page_no}页表格"))

            # 章节识别：优先 markdown 标题，否则整页一节
            heading_matches = list(re.finditer(r"^#{1,6}\s+(.+)$", text, re.M))
            if heading_matches:
                pos = 0
                for m in heading_matches:
                    segment = text[pos:m.start()]
                    if segment.strip():
                        sections.append(
                            Section(heading="(正文)", level=1, text=segment, page=page_no)
                        )
                    sections.append(
                        Section(
                            heading=m.group(1).strip(),
                            level=len(m.group(0).split()[0]) - 1,
                            page=page_no,
                        )
                    )
                    pos = m.end()
                if text[pos:].strip():
                    sections.append(Section(heading="(正文)", level=1, text=text[pos:], page=page_no))
            else:
                sections.append(Section(heading=f"第{page_no}页", level=1, text=text, page=page_no))
            # 真实研报常见数字跨行断开（如 "毛利率32.\n5%"），压平换行后再抽取
            text_flat = re.sub(r"\s*\n\s*", "", text)
            metrics.extend(_extract_from_text(text_flat, page_no, f"第{page_no}页"))

    full_text = "\n".join(pages_text)
    metrics = _dedupe_metrics(metrics)
    return Report(
        source_path=path,
        title=Path(path).stem,
        institution=_institution_of(full_text),
        date=_date_of(full_text),
        rating=_rating_of(full_text),
        target_price=_target_price_of(full_text),
        summary=re.sub(r"\s+", " ", full_text)[:300],
        sections=sections,
        tables=tables,
        metrics=metrics,
    )


def parse_document(path: str) -> Report:
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix == ".pdf":
        return parse_pdf(path)
    text = p.read_text(encoding="utf-8", errors="ignore")
    return parse_markdown(text, path)


def extract_metrics(path: str) -> list[Metric]:
    """便捷入口：只做指标抽取。"""
    return parse_document(path).metrics
