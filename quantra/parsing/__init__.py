"""解析小框架：输入接口 ParseRequest → 引擎层 → 输出接口 ParseResult。

设计原则：上层（抽取/归档/Agent）只依赖输出接口，不关心底层引擎；
引擎（pdfplumber / MinerU / Docling / VLM）按需插拔。
"""

from quantra.parsing.interfaces import (
    BaseParser,
    DocumentBlock,
    ParseRequest,
    ParseResult,
)
from quantra.parsing.registry import parse_document

__all__ = [
    "BaseParser",
    "DocumentBlock",
    "ParseRequest",
    "ParseResult",
    "parse_document",
]
