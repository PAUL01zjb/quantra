"""双通道查询：结构化事实通道 + 文档检索通道。"""

from __future__ import annotations

from quantra.query.router import RouteDecision
from quantra.retrieval.hybrid import HybridRetriever
from quantra.storage.archive import ArchiveStore


def query_facts(decision: RouteDecision, store: ArchiveStore) -> dict:
    """结构化通道：按 company/metric/period 查 metric_fact，带来源引用。"""
    sql = """
        SELECT m.metric_name, m.period, m.value, m.unit, m.source_page, m.source_section,
               r.title, r.broker, r.report_date
        FROM metric_fact m
        LEFT JOIN report r ON m.report_id = r.report_id
        WHERE 1=1
    """
    params: list = []
    if decision.company_id:
        sql += " AND m.company_id = ?"
        params.append(decision.company_id)
    if decision.metric:
        sql += " AND m.metric_name = ?"
        params.append(decision.metric)
    if decision.period:
        sql += " AND (m.period = ? OR m.period LIKE ?)"
        params.extend([decision.period, decision.period + "%"])
    sql += " ORDER BY m.metric_name, m.period"
    rows = [dict(r) for r in store.conn.execute(sql, params).fetchall()]

    citations = []
    seen = set()
    for row in rows:
        key = (row["title"], row["broker"], row["source_section"], row["source_page"])
        if key in seen:
            continue
        seen.add(key)
        citations.append(
            f"{row['broker'] or '未知机构'}《{row['title'] or '未知研报'}》"
            f" {row['source_section'] or ''} p{row['source_page'] or '?'}"
        )
    return {"rows": rows, "citations": citations}


def query_risks(company_id: str | None, store: ArchiveStore) -> list[dict]:
    if not company_id:
        return []
    return [
        dict(r)
        for r in store.conn.execute(
            "SELECT risk_text, category, report_id FROM risk WHERE company_id=?",
            (company_id,),
        ).fetchall()
    ]


def query_docs(
    question: str,
    decision: RouteDecision,
    retriever: HybridRetriever,
    store: ArchiveStore,
) -> dict:
    """文档通道：BM25/混合检索，支持公司标签预过滤。"""
    report_ids = None
    if decision.company_id:
        report_ids = {
            r["report_id"]
            for r in store.conn.execute(
                "SELECT report_id FROM report WHERE company_id=?", (decision.company_id,)
            ).fetchall()
        }
    hits = retriever.search(question, k=6, report_ids=report_ids)
    title_map = {r["report_id"]: r["title"] for r in store.list_reports()}
    chunks = []
    citations = []
    for hit in hits:
        chunk = hit.chunk
        title = title_map.get(chunk.report_id, chunk.report_id)
        chunks.append(
            {
                "title": title,
                "heading": chunk.heading,
                "page": chunk.page,
                "text": chunk.text[:300],
                "score": round(hit.score, 4),
            }
        )
        citations.append(f"{title} · {chunk.heading or '正文'} p{chunk.page}")
    return {"chunks": chunks, "citations": citations}
