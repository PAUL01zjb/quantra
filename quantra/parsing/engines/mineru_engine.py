"""MinerU 引擎（可选，重型依赖）。

原理：DocLayout-YOLO（CNN 版面检测）→ PaddleOCR → 表格/公式识别（Transformer）→ Markdown。
安装（需用户确认，含 torch 与模型权重）：pip install magic-pdf[full]
"""

from __future__ import annotations

from quantra.parsing.interfaces import BaseParser, ParseRequest, ParseResult


class MinerUEngine(BaseParser):
    name = "mineru"

    def parse(self, request: ParseRequest) -> ParseResult:
        try:
            from magic_pdf.pipe.OCRPipe import OCRPipe  # noqa: F401
            from magic_pdf.pipe.TXTPipe import TXTPipe  # noqa: F401
        except ImportError as exc:
            raise RuntimeError(
                "MinerU 未安装。它包含 torch 与模型权重（数 GB），需确认后安装："
                "pip install magic-pdf[full]"
            ) from exc
        # 接入点：调用 MinerU 管道，把输出映射为 ParseResult
        raise NotImplementedError("MinerU 引擎接线待 Step 2 实现")
