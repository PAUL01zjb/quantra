"""入库管道（业务只需上传文档，剩下的自动完成）。

链路：parse -> extract -> archive（结构化库）-> register raw doc（原始文档层 + 复合标签）。
学习版标签自动生成：ticker/公司/行业/报告类型/报告日期/机构；生产版由 MinerU + LLM 输出更全。
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from quantra.config import Settings, get_settings
from quantra.extraction.extractor import ExtractionResult, extract as extract_rules
from quantra.extraction.llm_extractor import LLMExtractor
from quantra.parsing import parse_document
from quantra.parsing.interfaces import ParseRequest
from quantra.storage.archive import ArchiveStore


INDUSTRY_KEYWORDS: list[tuple[str, list[str]]] = [
    ("银行", ["银行", "银行业"]),
    ("证券", ["证券", "券商", "非银金融"]),
    ("保险", ["保险"]),
    ("地产", ["地产", "房地产", "物业"]),
    ("医药", ["医药", "医疗", "生物", "创新药"]),
    ("消费", ["消费", "食品", "白酒", "饮料", "零售", "家电"]),
    ("汽车", ["汽车", "整车", "新能源车"]),
    ("科技", ["科技", "电子", "半导体", "计算机", "通信", "软件", "互联网"]),
    ("制造", ["制造", "机械", "军工", "电力设备"]),
    ("能源化工", ["能源", "化工", "石油", "煤炭", "有色"]),
    ("公用基建", ["公用", "电力", "基建", "建筑", "环保"]),
]


def guess_report_type(title: str) -> str:
    for keyword, label in [
        ("年报", "年报"),
        ("半年报", "半年报"),
        ("中报", "半年报"),
        ("三季报", "三季报"),
        ("一季报", "一季报"),
        ("季报", "季报"),
        ("快报", "业绩快报"),
        ("点评", "点评"),
        ("深度", "深度"),
    ]:
        if keyword in title:
            return label
    return "研报"


def guess_industry(title: str) -> str:
    for industry, keywords in INDUSTRY_KEYWORDS:
        if any(k in title for k in keywords):
            return industry
    return ""


def build_tags(result: ExtractionResult) -> dict:
    meta = result.report_meta
    return {
        "ticker": result.company.ticker or "",
        "company": result.company.name,
        "industry": guess_industry(meta.title + result.source),
        "report_type": guess_report_type(meta.title),
        "report_date": meta.report_date,
        "broker": meta.broker,
        "source": result.source,
    }


def _file_hash(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:32]


class IngestionPipeline:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.store = ArchiveStore(self.settings.db_path)

    def _extract(self, parse_result) -> ExtractionResult:
        if self.settings.api_key and not self.settings.dry_run:
            try:
                return LLMExtractor(self.settings).extract(parse_result)
            except Exception:  # noqa: BLE001
                pass
        return extract_rules(parse_result)

    def ingest(self, path: str, engine: str = "auto") -> dict:
        parse_result = parse_document(ParseRequest(source=path, engine=engine))
        result = self._extract(parse_result)
        ids = self.store.archive(result, parse_result.blocks)
        tags = build_tags(result)
        doc_id = self.store.register_raw_doc(path, _file_hash(path), tags)
        self.store.audit("ingest_doc", f"{path} -> doc={doc_id} report={ids['report_id']}", status="ok")
        return {
            "doc_id": doc_id,
            "company_id": ids["company_id"],
            "report_id": ids["report_id"],
            "tags": tags,
            "metrics": ids["metrics"],
            "chunks": ids["chunks"],
            "risks": ids["risks"],
            "engine": result.engine,
            "method": result.metrics[0].method if result.metrics else "rule",
        }

    def close(self) -> None:
        self.store.close()
