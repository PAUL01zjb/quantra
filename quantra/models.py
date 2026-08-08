"""核心数据模型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Section:
    heading: str
    level: int = 1
    text: str = ""
    page: int = 0


@dataclass
class Table:
    title: str
    page: int
    rows: list[list[str]] = field(default_factory=list)


@dataclass
class Metric:
    name: str
    value: str
    unit: str = ""
    period: str = ""
    source: str = ""
    raw: str = ""


@dataclass
class Report:
    source_path: str
    title: str = ""
    institution: str = ""
    analyst: str = ""
    date: str = ""
    rating: str = ""
    target_price: str = ""
    sector: str = ""
    summary: str = ""
    sections: list[Section] = field(default_factory=list)
    tables: list[Table] = field(default_factory=list)
    metrics: list[Metric] = field(default_factory=list)


@dataclass
class Chunk:
    chunk_id: str
    report_id: str
    heading: str
    page: int
    text: str
    tokens: int = 0


@dataclass
class RetrievedChunk:
    chunk: Chunk
    score: float
    source: str = "bm25"


@dataclass
class AgentStep:
    """Agent 执行轨迹中的一步。"""

    index: int
    action: str
    detail: str = ""
    tool: Optional[str] = None
    args: Optional[dict] = None
    result_preview: str = ""


@dataclass
class AgentResult:
    memo: str
    steps: list[AgentStep] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)
    model_used: str = ""
    cost_yuan: float = 0.0
    dry_run: bool = True
