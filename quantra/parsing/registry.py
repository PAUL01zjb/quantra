"""引擎注册与分发。"""

from __future__ import annotations

from quantra.parsing.engines import PdfPlumberEngine, TextEngine
from quantra.parsing.engines.docling_engine import DoclingEngine
from quantra.parsing.engines.mineru_engine import MinerUEngine
from quantra.parsing.interfaces import BaseParser, ParseRequest, ParseResult


ENGINES: dict[str, type[BaseParser]] = {
    "pdfplumber": PdfPlumberEngine,
    "mineru": MinerUEngine,
    "docling": DoclingEngine,
    "text": TextEngine,
}

DEFAULT_BY_TYPE = {"pdf": "pdfplumber", "md": "text", "txt": "text"}


def get_engine(name: str) -> BaseParser:
    try:
        return ENGINES[name]()
    except KeyError as exc:
        raise KeyError(f"未知引擎: {name}，可选: {list(ENGINES)}") from exc


def parse_document(request: ParseRequest) -> ParseResult:
    source_type = request.resolved_source_type()
    engine_name = request.engine if request.engine != "auto" else DEFAULT_BY_TYPE.get(source_type, "pdfplumber")
    return get_engine(engine_name).parse(request)
