"""Agent 工具层：统一 JSON Schema + 白名单 + 审计钩子。"""

from __future__ import annotations

from quantra.models import RetrievedChunk
from quantra.retrieval.hybrid import HybridRetriever
from quantra.storage.db import Store


TOOL_SCHEMAS = [
    {
        "name": "search_reports",
        "description": "在已入库研报中检索与问题相关的段落，返回带报告名/章节/页码的引用。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "检索关键词或问题"},
                "top_k": {"type": "integer", "description": "返回条数，默认 6"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "extract_metric",
        "description": "抽取某财务指标（如 毛利率、营业收入、ROE）在各研报/各期的数值。",
        "parameters": {
            "type": "object",
            "properties": {
                "metric": {"type": "string", "description": "指标名"},
                "report_id": {"type": "string", "description": "可选，限定某份研报"},
            },
            "required": ["metric"],
        },
    },
    {
        "name": "calc_trend",
        "description": "计算某指标最近两期的同比/环比变化（百分比）。",
        "parameters": {
            "type": "object",
            "properties": {
                "metric": {"type": "string", "description": "指标名"},
                "report_id": {"type": "string", "description": "可选，限定某份研报"},
            },
            "required": ["metric"],
        },
    },
    {
        "name": "list_reports",
        "description": "列出已入库的研报（标题、机构、评级、目标价）。",
        "parameters": {"type": "object", "properties": {}},
    },
]

TOOL_WHITELIST = {schema["name"] for schema in TOOL_SCHEMAS}


class Tools:
    def __init__(self, store: Store, retriever: HybridRetriever):
        self.store = store
        self.retriever = retriever
        self._title_map = {r["report_id"]: r["title"] for r in store.list_reports()}

    def _citation(self, hit: RetrievedChunk) -> dict:
        return {
            "chunk_id": hit.chunk.chunk_id,
            "title": self._title_map.get(hit.chunk.report_id, hit.chunk.report_id),
            "heading": hit.chunk.heading,
            "page": hit.chunk.page,
            "text": hit.chunk.text[:300],
        }

    def search_reports(self, query: str, top_k: int = 6) -> dict:
        hits = self.retriever.search(query, k=top_k)
        return {"citations": [self._citation(h) for h in hits]}

    def extract_metric(self, metric: str, report_id: str | None = None) -> dict:
        rows: list[dict] = []
        for rid in [report_id] if report_id else list(self._title_map):
            for m in self.store.get_report_metrics(rid):
                if metric.lower() in m["name"].lower():
                    rows.append(
                        {
                            "report": self._title_map.get(rid, rid),
                            "metric": m["name"],
                            "period": m["period"],
                            "value": m["value"],
                            "unit": m["unit"],
                            "source": m["source"],
                        }
                    )
        return {"metrics": rows}

    def calc_trend(self, metric: str, report_id: str | None = None) -> dict:
        result = self.extract_metric(metric, report_id)
        trends = []
        by_report: dict[str, list[dict]] = {}
        for row in result["metrics"]:
            if row["period"]:
                by_report.setdefault(row["report"], []).append(row)
        for report, rows in by_report.items():
            ordered = sorted(rows, key=lambda r: r["period"])
            for prev, curr in zip(ordered, ordered[1:]):
                try:
                    pv, cv = float(prev["value"]), float(curr["value"])
                except (TypeError, ValueError):
                    continue
                if pv == 0:
                    continue
                trends.append(
                    {
                        "report": report,
                        "metric": metric,
                        "from": f"{prev['period']}={prev['value']}",
                        "to": f"{curr['period']}={curr['value']}",
                        "change_pct": round((cv - pv) / pv * 100, 2),
                    }
                )
        return {"trends": trends}

    def list_reports(self) -> dict:
        return {"reports": self.store.list_reports()}

    def run_tool(self, name: str, args: dict) -> dict:
        if name not in TOOL_WHITELIST:
            raise ValueError(f"工具不在白名单内: {name}")
        return getattr(self, name)(**args)
