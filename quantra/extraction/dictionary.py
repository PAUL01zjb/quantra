"""指标词典（最大公约数版）。

第一版固定为各券商研报普遍覆盖的核心指标：
毛利率/净利率/营业收入/归母净利润/净利润/ROE/EPS/PE/PB。
别名用于抽取归一化（如 营收 -> 营业收入、每股收益 -> EPS）。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MetricDef:
    canonical: str
    aliases: list[str]
    unit: str = ""
    kind: str = "amount"  # ratio / amount / per_share / valuation


METRIC_DICTIONARY: list[MetricDef] = [
    MetricDef("毛利率", ["毛利率", "gross margin", "gross_margin"], "%", "ratio"),
    MetricDef("净利率", ["净利率", "net margin", "net_margin"], "%", "ratio"),
    MetricDef("营业收入", ["营业收入", "营业总收入", "营收", "收入", "revenue"], "亿元", "amount"),
    MetricDef("归母净利润", ["归母净利润", "归母净利", "归属母公司净利润", "归母"], "亿元", "amount"),
    MetricDef("净利润", ["净利润", "net profit", "net_profit"], "亿元", "amount"),
    MetricDef("ROE", ["ROE", "净资产收益率", "roe"], "%", "ratio"),
    MetricDef("EPS", ["EPS", "每股收益", "eps"], "元", "per_share"),
    MetricDef("PE", ["PE", "市盈率", "pe"], "倍", "valuation"),
    MetricDef("PB", ["PB", "市净率", "pb"], "倍", "valuation"),
]


def metric_def(name: str) -> MetricDef | None:
    lowered = name.lower()
    for definition in METRIC_DICTIONARY:
        if name == definition.canonical or lowered in [a.lower() for a in definition.aliases]:
            return definition
    return None


def normalize_metric_name(name: str) -> str | None:
    definition = metric_def(name)
    return definition.canonical if definition else None
