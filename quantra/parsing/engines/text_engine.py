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
        for raw in re.split(r"\n\s*\n", text.strip()):
            line = raw.strip()
            if not line:
                continue
            if line.startswith("#") or ("\n" not in line and len(line) <= 60):
                block_type = "heading"
            else:
                block_type = "paragraph"
            blocks.append(DocumentBlock(block_type=block_type, text=line, page=0, order=order))
            order += 1
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
