"""pdfplumber 引擎：基于页面几何坐标的文本/表格抽取。

原理：无 AI，直接读取 PDF 字符坐标，按布局重建段落；表格用线条/文本对齐检测。
适用：文本型 PDF（大多数券商研报）；扫描件需要 OCR 引擎（MinerU 等）。
"""

from __future__ import annotations

import re
import time
from pathlib import Path

from quantra.parsing.interfaces import BaseParser, DocumentBlock, ParseRequest, ParseResult


class PdfPlumberEngine(BaseParser):
    name = "pdfplumber"

    def parse(self, request: ParseRequest) -> ParseResult:
        import pdfplumber

        t0 = time.time()
        blocks: list[DocumentBlock] = []
        order = 0
        tables_found = 0
        pages_total = 0

        with pdfplumber.open(request.source) as pdf:
            pages_total = len(pdf.pages)
            page_numbers = (
                list(range(request.page_range[0], request.page_range[1] + 1))
                if request.page_range
                else list(range(1, pages_total + 1))
            )
            for page_no in page_numbers:
                page = pdf.pages[page_no - 1]
                text = page.extract_text() or ""

                if request.parse_tables:
                    for raw in page.extract_tables() or []:
                        rows = [[cell or "" for cell in row] for row in raw]
                        if not rows:
                            continue
                        tables_found += 1
                        blocks.append(
                            DocumentBlock(
                                block_type="table",
                                page=page_no,
                                table_rows=rows,
                                text=" | ".join(" | ".join(r) for r in rows[:3]),
                                order=order,
                            )
                        )
                        order += 1

                # 文本按空行分块，短单行视为标题（粗粒度，D1 可调）
                for raw in re.split(r"\n\s*\n", text.strip()):
                    line = re.sub(r"\s+", " ", raw).strip()
                    if not line:
                        continue
                    if "\n" not in raw and 1 <= len(line) <= 40:
                        block_type = "heading"
                    else:
                        block_type = "paragraph"
                    blocks.append(
                        DocumentBlock(block_type=block_type, text=line, page=page_no, order=order)
                    )
                    order += 1

        blocks.sort(key=lambda b: (b.page, b.order))
        markdown = self._to_markdown(blocks)
        return ParseResult(
            source=str(request.source),
            title=Path(request.source).stem,
            metadata={"language": request.language, "mode": request.mode},
            blocks=blocks,
            markdown=markdown,
            stats={
                "pages": pages_total,
                "blocks": len(blocks),
                "tables": tables_found,
                "parse_time_s": round(time.time() - t0, 3),
            },
            engine=self.name,
        )

    @staticmethod
    def _to_markdown(blocks: list[DocumentBlock]) -> str:
        parts: list[str] = []
        for block in blocks:
            if block.block_type == "heading":
                parts.append(f"## {block.text}")
            elif block.block_type == "table" and block.table_rows:
                rows = block.table_rows
                lines = ["| " + " | ".join(rows[0]) + " |"]
                lines.append("| " + " | ".join(["---"] * len(rows[0])) + " |")
                for row in rows[1:]:
                    lines.append("| " + " | ".join(row) + " |")
                parts.append("\n".join(lines))
            else:
                parts.append(block.text)
        return "\n\n".join(parts)
