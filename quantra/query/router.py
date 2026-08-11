"""规则路由：意图分类 + 实体识别（第一道确定性关卡）。

设计：90% 的问题由规则判定通道（快、便宜、可解释）；
歧义问题留给轻量判别 Agent（当前规则占位，生产版接便宜模型）。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from quantra.extraction.dictionary import METRIC_DICTIONARY
from quantra.storage.archive import ArchiveStore


PERIOD_RE = re.compile(r"(20\d{2})(E)?\s*年?(?:Q([1-4]))?")
TICKER_RE = re.compile(r"(?<![A-Za-z0-9])(\d{6})(?:\.(SH|SZ|BJ))?")

SEMANTIC_WORDS = [
    "怎么看",
    "如何",
    "观点",
    "评价",
    "风险",
    "趋势",
    "分析",
    "逻辑",
    "为什么",
    "影响",
    "展望",
    "对比",
    "比较",
    "关注",
]
DOCUMENT_WORDS = ["原文", "溯源", "第几页", "原始", "报告内容", "出处", "全文", "页码", "PDF", "第.页"]


@dataclass
class RouteDecision:
    intent: str  # fact / semantic / document
    metric: str | None = None
    company_id: str | None = None
    ticker: str | None = None
    period: str | None = None


def extract_ticker(text: str) -> str | None:
    m = TICKER_RE.search(text)
    if not m:
        return None
    code = m.group(1)
    suffix = m.group(2)
    if not suffix:
        prefix = code[0]
        suffix = "SH" if prefix in ("6", "9") else "SZ" if prefix in ("0", "2", "3") else "BJ"
    return f"{code}.{suffix}"


def resolve_company(text: str, store: ArchiveStore) -> tuple[str | None, str | None]:
    ticker = extract_ticker(text)
    if ticker:
        return ticker, ticker
    rows = store.conn.execute(
        "SELECT company_id, name, ticker FROM company"
    ).fetchall()
    for row in rows:
        if row["name"] and row["name"] in text:
            return row["company_id"], row["ticker"] or row["company_id"]
    return None, None


def detect_metric(text: str) -> str | None:
    lowered = text.lower()
    candidates: list[tuple[int, str]] = []
    for definition in METRIC_DICTIONARY:
        for alias in definition.aliases:
            if alias.lower() in lowered:
                candidates.append((len(alias), definition.canonical))
    if not candidates:
        return None
    # 最长别名优先：'归母净利润' 优先于 '净利润'，避免粗匹配
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def detect_period(text: str) -> str | None:
    m = PERIOD_RE.search(text)
    if not m:
        return None
    return f"{m.group(1)}{m.group(2) or ''}{('Q' + m.group(3)) if m.group(3) else ''}"


def classify(text: str, store: ArchiveStore) -> RouteDecision:
    metric = detect_metric(text)
    company_id, ticker = resolve_company(text, store)
    period = detect_period(text)

    if any(word in text for word in DOCUMENT_WORDS):
        intent = "document"
    elif metric:
        intent = "fact"
    elif any(word in text for word in SEMANTIC_WORDS):
        intent = "semantic"
    else:
        intent = "semantic"

    return RouteDecision(
        intent=intent,
        metric=metric,
        company_id=company_id,
        ticker=ticker,
        period=period,
    )
