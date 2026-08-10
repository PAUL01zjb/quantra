"""解析小框架的输入/输出契约。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ParseRequest:
    """输入接口：统一描述"解析什么、怎么解析"。

    source:      文件路径（PDF/MD/TXT）
    source_type: pdf / md / txt（可由后缀推断）
    mode:        auto / text / layout / ocr
    engine:      auto / pdfplumber / mineru / docling（auto 时按 source_type 选默认）
    """

    source: str | Path
    source_type: str = "auto"
    language: str = "zh"
    mode: str = "auto"
    parse_tables: bool = True
    parse_figures: bool = False
    page_range: Optional[tuple[int, int]] = None
    engine: str = "auto"

    def resolved_source_type(self) -> str:
        if self.source_type != "auto":
            return self.source_type
        suffix = Path(self.source).suffix.lower().lstrip(".")
        return {"pdf": "pdf", "md": "md", "txt": "txt", "markdown": "md"}.get(suffix, suffix)


@dataclass
class DocumentBlock:
    """文档块：解析输出的最小单元（标题/段落/表格/图片/公式）。"""

    block_type: str  # heading / paragraph / table / figure / formula
    text: str = ""
    page: int = 0
    bbox: Optional[tuple[float, float, float, float]] = None
    table_rows: Optional[list[list[str]]] = None
    order: int = 0


@dataclass
class ParseResult:
    """输出接口：无论底层用哪个引擎，上层拿到的都是这个结构。"""

    source: str
    title: str = ""
    metadata: dict = field(default_factory=dict)
    blocks: list[DocumentBlock] = field(default_factory=list)
    markdown: str = ""
    stats: dict = field(default_factory=dict)
    engine: str = ""


class BaseParser:
    """引擎基类：实现 parse(request) -> ParseResult。"""

    name: str = "base"

    def parse(self, request: ParseRequest) -> ParseResult:
        raise NotImplementedError
