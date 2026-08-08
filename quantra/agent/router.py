"""成本感知模型路由。

思路（来自 8/3–8/7 简报的多模型成本路由主题）：
批量抽取/检索类任务跑便宜模型，复杂推理/报告生成跑旗舰模型；
缓存命中、时段计价等留作路由策略扩展点。
"""

from __future__ import annotations

from quantra.config import Settings


COMPLEX_HINTS = [
    "对比",
    "分析",
    "为什么",
    "趋势",
    "总结",
    "计算",
    "推理",
    "评估",
    "风险",
    "怎么看",
    "变化",
]


def route(task: str, settings: Settings, mode: str | None = None) -> str:
    if mode == "cheap":
        return settings.cheap_model
    if mode == "strong":
        return settings.primary_model
    if len(task) > 120 or any(hint in task for hint in COMPLEX_HINTS):
        return settings.primary_model
    return settings.cheap_model


def estimate_tokens(text: str) -> int:
    """粗略估计 token 数（中文约 1.6 字/token，英文按词）。"""
    cjk = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    latin = len(text) - cjk
    return int(cjk / 1.6 + latin / 4) + 1


def estimate_cost(
    model: str,
    in_tokens: int,
    out_tokens: int,
    settings: Settings,
) -> float:
    """返回预估成本（人民币元）。"""
    spec = settings.cost_table.get(model)
    if not spec:
        return 0.0
    return (in_tokens * spec["in"] + out_tokens * spec["out"]) / 1_000_000
