"""抽取器：把统一 ParseResult 转为结构化 ExtractionResult。

当前方法：规则抽取（数字可复现、可审计），LLM 通道作为第二版增强。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from quantra.extraction.dictionary import METRIC_DICTIONARY, MetricDef, normalize_metric_name
from quantra.parsing.interfaces import DocumentBlock, ParseResult


PERIOD_RE = re.compile(r"(20\d{2})(E)?\s*年?\s*(?:Q([1-4]))?")
RATING_WORDS = ["买入", "强烈推荐", "推荐", "增持", "中性", "持有", "卖出", "回避"]
RISK_KEYWORDS = ["风险", "不及预期", "波动", "竞争加剧", "放缓", "政策", "下滑", "价格战"]


@dataclass
class CompanyInfo:
    name: str = ""
    ticker: str = ""
    sector: str = ""


@dataclass
class ReportMeta:
    title: str = ""
    broker: str = ""
    analyst: str = ""
    report_date: str = ""
    rating: str = ""
    target_price: str = ""


@dataclass
class MetricFact:
    metric_name: str
    value: str
    unit: str = ""
    period: str = ""
    source_page: int = 0
    source_section: str = ""
    raw_text: str = ""
    method: str = "rule"
    confidence: float = 0.75


@dataclass
class RiskItem:
    risk_text: str
    category: str = ""


@dataclass
class ExtractionResult:
    source: str
    engine: str
    company: CompanyInfo = field(default_factory=CompanyInfo)
    report_meta: ReportMeta = field(default_factory=ReportMeta)
    metrics: list[MetricFact] = field(default_factory=list)
    risks: list[RiskItem] = field(default_factory=list)


def _period_from(text: str, pos: int) -> str:
    window = text[max(0, pos - 80) : pos]
    matches = list(PERIOD_RE.finditer(window))
    if not matches:
        return ""
    m = matches[-1]
    return f"{m.group(1)}{m.group(2) or ''}{('Q' + m.group(3)) if m.group(3) else ''}"


def _company_name(title: str, full_text: str) -> str:
    title = re.sub(r"^[#\s]+", "", title)
    candidates = [
        re.match(r"^(.{2,16}?)[：:]\s*(?:20\d{2}|年报|点评|深度)", title),
        re.match(r"^(.{2,16}?)\s*(?:20\d{2}年?(?:年报|半年报|三季报|一季报|中报|点评))", title),
        re.match(r"^(.{2,16}?)(?:20\d{2}|年报|点评)", title),
    ]
    for m in candidates:
        if m:
            name = m.group(1).strip(" ：:-—")
            if name:
                return name
    return title[:12] or "未知公司"


def _ticker_of(text: str) -> str:
    m = re.search(r"(?<![A-Za-z0-9])(\d{6})(?:\.(SH|SZ|BJ))?", text)
    if not m:
        return ""
    code = m.group(1)
    suffix = m.group(2)
    if not suffix:
        prefix = code[0]
        suffix = "SH" if prefix in ("6", "9") else "SZ" if prefix in ("0", "2", "3") else "BJ"
    return f"{code}.{suffix}"


def _extract_report_meta(full_text: str, title: str) -> ReportMeta:
    broker_m = re.search(r"(?:机构|来源|研究机构)[：:]\s*([\u4e00-\u9fffA-Za-z0-9]{2,30})", full_text)
    analyst_m = re.search(r"分析师[：:]\s*([\u4e00-\u9fffA-Za-z·]{1,20})", full_text)
    date_m = re.search(r"(\d{4}[-年/]\d{1,2}[-月/]\d{1,2})", full_text)
    target_m = re.search(r"目标价[^0-9]{0,8}(\d+\.?\d*)\s*元?", full_text)
    rating = ""
    for word in reversed(RATING_WORDS):
        if word in full_text:
            rating = word
            break
    return ReportMeta(
        title=title,
        broker=broker_m.group(1) if broker_m else "",
        analyst=analyst_m.group(1) if analyst_m else "",
        report_date=date_m.group(1) if date_m else "",
        rating=rating,
        target_price=target_m.group(1) if target_m else "",
    )


def _facts_from_text(text: str, page: int, section: str) -> list[MetricFact]:
    facts: list[MetricFact] = []
    text = "\n".join(line for line in text.splitlines() if "|" not in line)
    for definition in METRIC_DICTIONARY:
        for alias in definition.aliases:
            alias_pattern = re.escape(alias)
            if definition.canonical == "净利润":
                alias_pattern = r"(?<!归母)" + alias_pattern
            pattern = re.compile(
                r"(?:" + alias_pattern + r")[^0-9年]{0,12}(\d+\.?\d*)\s*(亿元|亿|万元|元|%|倍)?",
                re.IGNORECASE,
            )
            for m in pattern.finditer(text):
                period = _period_from(text, m.start())
                unit = m.group(2) or definition.unit
                confidence = 0.9 if m.group(2) else 0.75
                facts.append(
                    MetricFact(
                        metric_name=definition.canonical,
                        value=m.group(1),
                        unit=unit,
                        period=period,
                        source_page=page,
                        source_section=section,
                        raw_text=m.group(0),
                        confidence=confidence,
                    )
                )
    return facts


def _facts_from_table(block: DocumentBlock, section: str) -> list[MetricFact]:
    facts: list[MetricFact] = []
    rows = block.table_rows or []
    if not rows:
        return facts
    header = rows[0]
    periods: list[str] = []
    for cell in header:
        m = PERIOD_RE.search(cell)
        periods.append(f"{m.group(1)}{m.group(2) or ''}{('Q' + m.group(3)) if m.group(3) else ''}" if m else "")
    for row in rows[1:]:
        if not row:
            continue
        canonical = normalize_metric_name(re.sub(r"\s*\(.*?\)\s*", "", row[0]))
        if not canonical:
            continue
        for col in range(1, min(len(row), len(header))):
            cell = row[col].strip()
            if not re.fullmatch(r"-?\d+\.?\d*", cell):
                continue
            facts.append(
                MetricFact(
                    metric_name=canonical,
                    value=cell,
                    unit="",
                    period=periods[col] if col < len(periods) else "",
                    source_page=block.page,
                    source_section=section,
                    raw_text=row[0],
                    confidence=0.85,
                )
            )
    return facts


def _extract_risks(blocks: list[DocumentBlock]) -> list[RiskItem]:
    risks: list[RiskItem] = []
    in_risk_section = False
    for block in blocks:
        if block.block_type == "heading" and ("风险" in block.text or "提示" in block.text):
            in_risk_section = True
            continue
        if block.block_type == "heading":
            in_risk_section = False
        if not in_risk_section and block.block_type != "paragraph":
            continue
        for sentence in re.split(r"[。；;]", block.text):
            sentence = sentence.strip()
            if len(sentence) < 4:
                continue
            matched = [kw for kw in RISK_KEYWORDS if kw in sentence]
            if not (in_risk_section or matched):
                continue
            for item in re.split(r"[、,]", sentence):
                item = item.strip()
                if len(item) >= 4:
                    risks.append(RiskItem(risk_text=item, category=matched[0] if matched else "风险"))
    return risks


def extract(parse_result: ParseResult) -> ExtractionResult:
    """ParseResult -> ExtractionResult。"""
    full_text = parse_result.markdown
    title = parse_result.title or ""
    for block in parse_result.blocks:
        if block.block_type == "heading" and block.text:
            title = re.sub(r"^[#\s]+", "", block.text)
            break

    meta = _extract_report_meta(full_text, title)
    company = CompanyInfo(name=_company_name(title, full_text), ticker=_ticker_of(full_text))

    facts: list[MetricFact] = []
    current_section = "导语"
    for block in parse_result.blocks:
        if block.block_type == "heading":
            current_section = block.text
            continue
        if block.block_type == "table":
            facts.extend(_facts_from_table(block, current_section))
        else:
            facts.extend(_facts_from_text(block.text, block.page, current_section))

    seen: set[tuple[str, str]] = set()
    deduped: list[MetricFact] = []
    for fact in facts:
        key = (fact.metric_name, fact.period)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(fact)

    return ExtractionResult(
        source=parse_result.source,
        engine=parse_result.engine,
        company=company,
        report_meta=meta,
        metrics=deduped,
        risks=_extract_risks(parse_result.blocks),
    )
