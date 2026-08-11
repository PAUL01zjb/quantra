"""生产版抽取：schema-guided LLM（OpenAI 兼容接口）。

设计：LLM 按输出契约抽取 JSON，规则词典做校验归一化（LLM 抽取 + 规则校验双通道）。
未配置 API Key 时抛出明确错误，由入库管道回退规则通道。
"""

from __future__ import annotations

import json
import re

from quantra.agent.orchestrator import LLMClient
from quantra.config import Settings
from quantra.extraction.dictionary import normalize_metric_name
from quantra.extraction.extractor import (
    CompanyInfo,
    ExtractionResult,
    MetricFact,
    ReportMeta,
    RiskItem,
)
from quantra.parsing.interfaces import ParseResult


SCHEMA_GUIDE = """\
你是研报信息抽取器。根据研报内容输出 JSON，严格使用以下结构（不要输出其他文字）：
{
  "company": {"name": "公司名", "ticker": "如 600036.SH"},
  "report_meta": {"title": "", "broker": "", "analyst": "", "report_date": "", "rating": "", "target_price": ""},
  "metrics": [{"metric_name": "指标名", "value": "数字", "unit": "%或亿元或元或倍", "period": "2025 或 2025E 或 2026Q1", "source_page": 页码, "source_section": "章节名"}],
  "risks": [{"risk_text": "风险描述", "category": "类别"}]
}
要求：只抽取原文明确出现的指标；period 填报告对应期间；每个指标附页码。
"""


class LLMExtractor:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = LLMClient(settings)

    def extract(self, parse_result: ParseResult) -> ExtractionResult:
        if not self.settings.api_key:
            raise RuntimeError("未配置 QUANTRA_API_KEY，无法使用 LLM 抽取通道")
        markdown = parse_result.markdown[:8000]
        prompt = SCHEMA_GUIDE + "\n\n研报内容（Markdown）：\n" + markdown
        raw = self.client.chat(
            [{"role": "user", "content": prompt}],
            model=self.settings.primary_model,
            temperature=0.1,
        )
        data = self._parse_json(raw)
        return self._to_extraction_result(data, parse_result)

    @staticmethod
    def _parse_json(raw: str) -> dict:
        start, end = raw.find("{"), raw.rfind("}")
        if start == -1 or end == -1:
            raise ValueError("LLM 未返回 JSON")
        return json.loads(raw[start : end + 1])

    @staticmethod
    def _to_extraction_result(data: dict, parse_result: ParseResult) -> ExtractionResult:
        company_raw = data.get("company") or {}
        meta_raw = data.get("report_meta") or {}
        metrics: list[MetricFact] = []
        for item in data.get("metrics") or []:
            canonical = normalize_metric_name(item.get("metric_name", ""))
            if not canonical:
                continue  # 规则词典校验：不认识的指标不进库
            metrics.append(
                MetricFact(
                    metric_name=canonical,
                    value=str(item.get("value", "")),
                    unit=item.get("unit", ""),
                    period=item.get("period", ""),
                    source_page=int(item.get("source_page") or 0),
                    source_section=item.get("source_section", ""),
                    raw_text="",
                    method="llm",
                    confidence=0.9,
                )
            )
        return ExtractionResult(
            source=parse_result.source,
            engine=f"llm({parse_result.engine})",
            company=CompanyInfo(
                name=company_raw.get("name", ""),
                ticker=company_raw.get("ticker", ""),
            ),
            report_meta=ReportMeta(
                title=meta_raw.get("title", ""),
                broker=meta_raw.get("broker", ""),
                analyst=meta_raw.get("analyst", ""),
                report_date=meta_raw.get("report_date", ""),
                rating=meta_raw.get("rating", ""),
                target_price=meta_raw.get("target_price", ""),
            ),
            metrics=metrics,
            risks=[
                RiskItem(risk_text=r.get("risk_text", ""), category=r.get("category", ""))
                for r in data.get("risks") or []
            ],
        )
