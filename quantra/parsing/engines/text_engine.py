"""文本引擎：MD/TXT 直接读入（轻量，无 AI）。"""

from __future__ import annotations

import re
from pathlib import Path

from quantra.parsing.interfaces import BaseParser, DocumentBlock, ParseRequest, ParseResult


class TextEngine(BaseParser):
    name = "text"

    def parse(self, request: ParseRequest) -> ParseResult:
        text = Path(request.source).read_text(encoding="utf-8", errors="ignore")
        blocks: list[DocumentBlock] = []
        order = 0
        lines = text.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue
            # markdown 表格：连续 | 行归为一个 table 块
            if line.startswith("|"):
                table_lines = []
                while i < len(lines) and lines[i].strip().startswith("|"):
                    table_lines.append(lines[i].strip())
                    i += 1
                rows = [
                    [cell.strip() for cell in row.strip().strip("|").split("|")]
                    for row in table_lines
                    if "---" not in row
                ]
                blocks.append(
                    DocumentBlock(
                        block_type="table",
                        text=" | ".join(table_lines[:3]),
                        page=0,
                        table_rows=rows,
                        order=order,
                    )
                )
                order += 1
                continue
            if line.startswith("#"):
                block_type = "heading"
            else:
                block_type = "paragraph"
            blocks.append(
                DocumentBlock(
                    block_type=block_type,
                    text=re.sub(r"^#{1,6}\s*", "", line),
                    page=0,
                    order=order,
                )
            )
            order += 1
            i += 1
        markdown = text
        return ParseResult(
            source=str(request.source),
            title=Path(request.source).stem,
            metadata={"language": request.language},
            blocks=blocks,
            markdown=markdown,
            stats={"blocks": len(blocks), "chars": len(text)},
            engine=self.name,
        )
