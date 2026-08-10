"""Docling 引擎（可选）。

原理：IBM 开源文档转换流水线（版面分析 + 表格结构模型 + 统一文档模型）。
安装：pip install docling
"""

from __future__ import annotations

from quantra.parsing.interfaces import BaseParser, ParseRequest, ParseResult


class DoclingEngine(BaseParser):
    name = "docling"

    def parse(self, request: ParseRequest) -> ParseResult:
        try:
            from docling.document_converter import DocumentConverter  # noqa: F401
        except ImportError as exc:
            raise RuntimeError(
                "Docling 未安装：pip install docling（含模型权重，需确认后安装）"
            ) from exc
        raise NotImplementedError("Docling 引擎接线待 Step 2 实现")
