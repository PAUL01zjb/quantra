"""MinerU 输出映射：content_list.json + markdown -> ParseResult（纯函数，可离线测试）。

MinerU 版本间 content_list 结构有差异，这里做"版本宽容"映射：
- 认识的结构（text/title/table/image/equation + bbox）直接转 DocumentBlock；
- 不认识的字段走兜底：整段 markdown 按标题/段落/表格重新分块。
这样输出契约 ParseResult 始终稳定，底层怎么变不影响上层。
"""

from __future__ import annotations

import re
from pathlib import Path

from quantra.parsing.interfaces import DocumentBlock, ParseResult


def _text_of_block(block: dict) -> str:
    """兼容不同版本的 lines/spans 结构。"""
    texts: list[str] = []
    for line in block.get("lines", []) or []:
        for span in line.get("spans", []) or []:
            content = span.get("content")
            if content:
                texts.append(content)
    if texts:
        return "".join(texts)
    # 表格等块可能直接把文本放在 table 字段
    return str(block.get("table", "") or "")


def _table_rows_of_block(block: dict) -> list[list[str]] | None:
    """尽力抽取表格行；拿不到就返回 None（由 markdown 兜底）。"""
    body = block.get("table_body", {}) or block.get("table", {})
    if isinstance(body, dict):
        cells = body.get("cells")
        if isinstance(cells, list):
            rows: list[list[str]] = []
            for cell in cells:
                if not isinstance(cell, dict):
                    continue
                row_idx = cell.get("row_idx")
                col_idx = cell.get("col_idx")
                text = " ".join(
                    span.get("content", "")
                    for span in (cell.get("spans", []) or [])
                ).strip()
                while len(rows) <= (row_idx or 0):
                    rows.append([])
                while len(rows[row_idx]) <= (col_idx or 0):
                    rows[row_idx].append("")
                rows[row_idx][col_idx] = text
            if rows:
                return rows
    return None


def _normalize_type(raw_type: str) -> str:
    return {
        "text": "paragraph",
        "title": "heading",
        "table": "table",
        "image": "figure",
        "equation": "formula",
    }.get(raw_type, "paragraph")


def map_mineru_output(
    content_list: list,
    markdown: str,
    source: str,
    engine: str = "mineru",
    stats: dict | None = None,
) -> ParseResult:
    """把 MinerU 产物映射为统一的 ParseResult。"""
    blocks: list[DocumentBlock] = []
    order = 0
    for page_obj in content_list:
        page_idx = int(page_obj.get("page_idx", 0)) + 1
        raw_blocks = page_obj.get("blocks") or page_obj.get("preproc_blocks") or []
        for raw in raw_blocks:
            if not isinstance(raw, dict):
                continue
            block_type = _normalize_type(str(raw.get("type", "text")))
            bbox = raw.get("bbox")
            table_rows = _table_rows_of_block(raw) if block_type == "table" else None
            text = _text_of_block(raw)
            blocks.append(
                DocumentBlock(
                    block_type=block_type,
                    text=text,
                    page=page_idx,
                    bbox=tuple(bbox) if isinstance(bbox, list) and len(bbox) == 4 else None,
                    table_rows=table_rows,
                    order=order,
                )
            )
            order += 1

    if not blocks:
        blocks = blocks_from_markdown(markdown, source)

    stats = stats or {
        "pages": len(content_list),
        "blocks": len(blocks),
        "tables": sum(1 for b in blocks if b.block_type == "table"),
    }
    return ParseResult(
        source=source,
        title=Path(source).stem,
        metadata={"engine_note": "MinerU（CNN 版面检测 + OCR + 表格/公式模型）"},
        blocks=blocks,
        markdown=markdown,
        stats=stats,
        engine=engine,
    )


def blocks_from_markdown(markdown: str, source: str) -> list[DocumentBlock]:
    """兜底：从 MinerU 生成的 markdown 重新分块。"""
    blocks: list[DocumentBlock] = []
    order = 0
    for raw in re.split(r"\n\s*\n", markdown.strip()):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            block_type = "heading"
        elif line.startswith("|"):
            block_type = "table"
        else:
            block_type = "paragraph"
        blocks.append(DocumentBlock(block_type=block_type, text=line, page=0, order=order))
        order += 1
    return blocks
