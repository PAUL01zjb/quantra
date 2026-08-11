"""Memory extractor (rule channel).

四类记忆：
- fact       交易员确认过的指标事实（最高置信，确认台入口）
- conclusion 每次业务问答的结论（带来源）
- correction 交易员修正（如"不良率单位是 %"）
- preference 交易员偏好（预留，行为统计）
Production: LLM extraction from transcripts + Mem0/LangGraph Store persistence.
"""

from __future__ import annotations

import re

from quantra.storage.archive import ArchiveStore


def confirm_facts(question: str, answer, store: ArchiveStore) -> list[str]:
    """确认即记忆：把结构化答案的每行事实写入 fact 记忆，并写入结论记忆。"""
    memory_ids: list[str] = []
    if answer.channel == "structured":
        for row in answer.evidence:
            metric = row.get("metric_name")
            value = row.get("value")
            if not metric or not value:
                continue
            period = row.get("period") or ""
            unit = row.get("unit") or ""
            content = f"{metric} {period} = {value}{unit}" if period else f"{metric} = {value}{unit}"
            memory_ids.append(
                store.memory_upsert(
                    kind="fact",
                    entity_type="metric",
                    entity_id=metric,
                    content=content,
                    confidence=0.95,
                    source=f"Q: {question[:80]}",
                )
            )
    memory_ids.append(
        store.memory_upsert(
            kind="conclusion",
            entity_type="qa",
            entity_id=question[:60],
            content=answer.answer[:500],
            confidence=0.9,
            source=question,
        )
    )
    return memory_ids


def correct_answer(question: str, correction: str, store: ArchiveStore) -> str:
    """修正记忆：交易员纠偏，后续回答应参考。"""
    return store.memory_upsert(
        kind="correction",
        entity_type="topic",
        entity_id=question[:40],
        content=correction,
        confidence=1.0,
        source=f"Q: {question[:80]}",
    )


def inject_memory(question: str, store: ArchiveStore, limit: int = 5) -> list[dict]:
    """按问题中的实体/指标检索相关记忆，注入当前问答上下文。"""
    from quantra.query.router import detect_metric, resolve_company

    terms: set[str] = set()
    metric = detect_metric(question)
    if metric:
        terms.add(metric)
    _company_id, ticker = resolve_company(question, store)
    if ticker:
        terms.add(ticker)
    for token in re.split(r"[\s，。？?!?：:；;、]+", question):
        if len(token) >= 2:
            terms.add(token)
    hits: dict[str, dict] = {}
    for term in terms:
        for row in store.memory_search(term, limit=limit):
            hits[row["memory_id"]] = row
    return list(hits.values())[:limit]
