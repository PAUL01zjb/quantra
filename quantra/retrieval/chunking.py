"""标题感知分块：保留章节完整性，长文按句切分并带重叠窗口。"""

from __future__ import annotations

import re
import uuid

from quantra.models import Chunk, Report


SENT_SPLIT_RE = re.compile(r"(?<=[。！？!?；;])\s*")


def _split_sentences(text: str) -> list[str]:
    parts = [p.strip() for p in SENT_SPLIT_RE.split(text) if p.strip()]
    return parts or ([text.strip()] if text.strip() else [])


def chunk_report(report: Report, max_chars: int = 800, overlap: int = 100) -> list[Chunk]:
    chunks: list[Chunk] = []
    for i, section in enumerate(report.sections):
        text = section.text.strip()
        if not text:
            continue
        heading = section.heading or f"第{i + 1}节"
        if len(text) <= max_chars:
            chunks.append(
                Chunk(
                    chunk_id=f"{_hash(report.source_path, heading, 0)}-{i}",
                    report_id=_hash(report.source_path),
                    heading=heading,
                    page=section.page,
                    text=text,
                    tokens=len(text),
                )
            )
            continue

        sentences = _split_sentences(text)
        buffer = ""
        seg = 0
        for sentence in sentences:
            if buffer and len(buffer) + len(sentence) > max_chars:
                chunks.append(
                    Chunk(
                        chunk_id=f"{_hash(report.source_path, heading, seg)}-{i}",
                        report_id=_hash(report.source_path),
                        heading=heading,
                        page=section.page,
                        text=buffer.strip(),
                        tokens=len(buffer),
                    )
                )
                seg += 1
                buffer = buffer[-overlap:] + sentence
            else:
                buffer += sentence + " "
        if buffer.strip():
            chunks.append(
                Chunk(
                    chunk_id=f"{_hash(report.source_path, heading, seg)}-{i}",
                    report_id=_hash(report.source_path),
                    heading=heading,
                    page=section.page,
                    text=buffer.strip(),
                    tokens=len(buffer),
                )
            )
    return chunks


def _hash(*parts: str) -> str:
    import hashlib

    return hashlib.sha1("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()[:12]
