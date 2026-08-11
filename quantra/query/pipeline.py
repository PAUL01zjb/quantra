"""Q&A pipeline: routing → dual-channel query → coverage fallback → cited answers."""

from __future__ import annotations

from dataclasses import dataclass, field

from quantra.memory.extractor import inject_memory
from quantra.query.channels import query_docs, query_facts, query_risks
from quantra.query.router import classify
from quantra.retrieval.hybrid import HybridRetriever
from quantra.storage.archive import ArchiveStore


@dataclass
class QueryAnswer:
    question: str
    intent: str
    channel: str
    fallback: bool
    answer: str
    citations: list[str] = field(default_factory=list)
    evidence: list[dict] = field(default_factory=list)
    memories: list[dict] = field(default_factory=list)


def _render_facts(question: str, facts: dict, decision) -> str:
    rows = facts["rows"]
    lines = [f"**问题**：{question}", "", f"**回答（结构化通道，{len(rows)} 条事实）**：", ""]
    by_metric: dict[str, list[dict]] = {}
    for row in rows:
        by_metric.setdefault(row["metric_name"], []).append(row)
    for metric, items in by_metric.items():
        values = "；".join(
            f"{item['period'] or '?'} = {item['value']}{item['unit'] or ''}"
            for item in items
        )
        lines.append(f"- {metric}：{values}")
    return "\n".join(lines)


def _render_docs(question: str, docs: dict, fallback: bool, risks: list[dict] | None = None) -> str:
    lines = [f"**问题**：{question}", ""]
    if fallback:
        lines.append("> 结构化库未命中，已自动降级到文档检索。")
        lines.append("")
    lines.append(f"**回答（文档通道，命中 {len(docs['chunks'])} 段）**：")
    for chunk in docs["chunks"][:4]:
        lines.append(f"- [{chunk['title']} p{chunk['page']}] {chunk['text'][:120]}")
    if risks:
        lines.append("")
        lines.append("**相关风险提示（结构化表）**：")
        for risk in risks[:5]:
            lines.append(f"- [{risk['category']}] {risk['risk_text']}")
    return "\n".join(lines)


def ask(
    question: str,
    store: ArchiveStore,
    retriever: HybridRetriever,
    session: str = "cli",
) -> QueryAnswer:
    decision = classify(question, store)
    memories = inject_memory(question, store)
    store.audit(question, f"ask intent={decision.intent} metric={decision.metric}", status="ok")

    if decision.intent == "fact":
        facts = query_facts(decision, store)
        if facts["rows"]:
            answer = _render_facts(question, facts, decision)
            return QueryAnswer(
                question=question,
                intent="fact",
                channel="structured",
                fallback=False,
                answer=answer,
                citations=facts["citations"],
                evidence=facts["rows"][:20],
                memories=memories,
            )
        # 覆盖度降级：结构化未命中 → 文档通道
        docs = query_docs(question, decision, retriever, store)
        answer = _render_docs(question, docs, fallback=True)
        return QueryAnswer(
            question=question,
            intent="fact",
            channel="doc",
            fallback=True,
            answer=answer,
            citations=docs["citations"],
            evidence=docs["chunks"][:20],
            memories=memories,
        )

    docs = query_docs(question, decision, retriever, store)
    risks = query_risks(decision.company_id, store) if "风险" in question else None
    answer = _render_docs(question, docs, fallback=False, risks=risks)
    return QueryAnswer(
        question=question,
        intent=decision.intent,
        channel="doc",
        fallback=False,
        answer=answer,
        citations=docs["citations"],
        evidence=docs["chunks"][:20],
        memories=memories,
    )
