"""归档存储：把 ExtractionResult 落库，并提供"公司卡片"聚合视图。"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from pathlib import Path

from quantra.extraction.extractor import ExtractionResult
from quantra.models import Chunk
from quantra.parsing.interfaces import DocumentBlock
from quantra.storage.schema import SCHEMA_V2


def _hash(*parts: str) -> str:
    return hashlib.sha1("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()[:16]


class ArchiveStore:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA_V2)

    # ---------- 写入 ----------
    def upsert_company(self, name: str, ticker: str = "", sector: str = "") -> str:
        company_id = ticker if ticker else "co_" + _hash(name)
        with self.conn:
            self.conn.execute(
                """INSERT INTO company (company_id, ticker, name, sector, updated_at)
                   VALUES (?,?,?,?,?)
                   ON CONFLICT(company_id) DO UPDATE SET
                     ticker=COALESCE(excluded.ticker, company.ticker),
                     name=excluded.name,
                     sector=COALESCE(excluded.sector, company.sector),
                     updated_at=excluded.updated_at""",
                (company_id, ticker or None, name, sector, time.time()),
            )
        return company_id

    def upsert_report(self, company_id: str, source: str, result: ExtractionResult) -> str:
        report_id = _hash(source)
        meta = result.report_meta
        with self.conn:
            self.conn.execute(
                """INSERT OR REPLACE INTO report
                   (report_id, company_id, source_path, broker, analyst, report_date,
                    title, rating, target_price, ingested_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    report_id,
                    company_id,
                    source,
                    meta.broker,
                    meta.analyst,
                    meta.report_date,
                    meta.title,
                    meta.rating,
                    meta.target_price,
                    time.time(),
                ),
            )
        return report_id

    def upsert_metric_facts(self, report_id: str, company_id: str, result: ExtractionResult) -> int:
        with self.conn:
            self.conn.executemany(
                """INSERT OR REPLACE INTO metric_fact
                   (report_id, company_id, metric_name, period, value, unit,
                    source_page, source_section, raw_text, method, confidence, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                [
                    (
                        report_id,
                        company_id,
                        m.metric_name,
                        m.period,
                        m.value,
                        m.unit,
                        m.source_page,
                        m.source_section,
                        m.raw_text,
                        m.method,
                        m.confidence,
                        time.time(),
                    )
                    for m in result.metrics
                ],
            )
        return len(result.metrics)

    def upsert_chunks(self, report_id: str, blocks: list[DocumentBlock]) -> int:
        rows = []
        for order, block in enumerate(blocks):
            chunk_id = _hash(report_id, block.heading if hasattr(block, "heading") else str(block.page), str(order))
            rows.append((chunk_id, report_id, "", block.page, block.text))
        with self.conn:
            self.conn.executemany(
                "INSERT OR REPLACE INTO document_chunk (chunk_id, report_id, heading, page, text) VALUES (?,?,?,?,?)",
                rows,
            )
        return len(rows)

    def load_chunks(self) -> list[Chunk]:
        rows = self.conn.execute(
            "SELECT chunk_id, report_id, heading, page, text FROM document_chunk"
        ).fetchall()
        return [
            Chunk(
                chunk_id=r["chunk_id"],
                report_id=r["report_id"],
                heading=r["heading"],
                page=r["page"],
                text=r["text"],
            )
            for r in rows
        ]

    def upsert_risks(self, report_id: str, company_id: str, result: ExtractionResult) -> int:
        with self.conn:
            self.conn.executemany(
                "INSERT OR REPLACE INTO risk (risk_id, report_id, company_id, risk_text, category) VALUES (?,?,?,?,?)",
                [
                    (_hash(report_id, r.risk_text), report_id, company_id, r.risk_text, r.category)
                    for r in result.risks
                ],
            )
        return len(result.risks)

    # ---------- 原始文档登记（多模态/对象存储层的元数据索引） ----------
    def register_raw_doc(self, source_path: str, doc_hash: str, tags: dict | None = None) -> str:
        doc_id = _hash(doc_hash)
        file_size = Path(source_path).stat().st_size if Path(source_path).exists() else 0
        with self.conn:
            self.conn.execute(
                """INSERT OR REPLACE INTO raw_doc
                   (doc_id, source_path, doc_hash, file_size, tags, registered_at)
                   VALUES (?,?,?,?,?,?)""",
                (doc_id, source_path, doc_hash, file_size, json.dumps(tags or {}, ensure_ascii=False), time.time()),
            )
        return doc_id

    def get_raw_docs(self, tag_key: str | None = None, tag_value: str | None = None) -> list[dict]:
        rows = self.conn.execute("SELECT doc_id, source_path, doc_hash, file_size, tags, registered_at FROM raw_doc ORDER BY registered_at DESC").fetchall()
        docs = []
        for row in rows:
            doc = dict(row)
            doc["tags"] = json.loads(doc["tags"] or "{}")
            if tag_key and tag_value and doc["tags"].get(tag_key) != tag_value:
                continue
            docs.append(doc)
        return docs

    # ---------- 跨对话记忆（四类：fact / conclusion / correction / preference） ----------
    def memory_upsert(
        self,
        kind: str,
        entity_type: str,
        entity_id: str,
        content: str,
        confidence: float = 0.8,
        source: str = "",
    ) -> str:
        memory_id = _hash(kind, entity_type, entity_id, content)
        now = time.time()
        with self.conn:
            self.conn.execute(
                """INSERT INTO memory (memory_id, kind, entity_type, entity_id, content, confidence, source, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(kind, entity_type, entity_id, content) DO UPDATE SET
                     confidence=MAX(memory.confidence, excluded.confidence),
                     source=excluded.source,
                     updated_at=excluded.updated_at""",
                (memory_id, kind, entity_type, entity_id, content, confidence, source, now, now),
            )
        return memory_id

    def memory_search(self, query: str, limit: int = 10) -> list[dict]:
        like = f"%{query}%"
        rows = self.conn.execute(
            """SELECT memory_id, kind, entity_type, entity_id, content, confidence, source, updated_at
               FROM memory
               WHERE content LIKE ? OR entity_id LIKE ? OR source LIKE ?
               ORDER BY confidence DESC, updated_at DESC LIMIT ?""",
            (like, like, like, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def list_memories(self, kind: str | None = None, limit: int = 50) -> list[dict]:
        sql = "SELECT memory_id, kind, entity_type, entity_id, content, confidence, source, updated_at FROM memory"
        params: list = []
        if kind:
            sql += " WHERE kind=?"
            params.append(kind)
        sql += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)
        return [dict(r) for r in self.conn.execute(sql, params).fetchall()]

    def audit(self, report_id: str, action: str, detail: str = "", status: str = "ok") -> None:
        with self.conn:
            self.conn.execute(
                "INSERT INTO extraction_audit (report_id, action, status, detail, ts) VALUES (?,?,?,?,?)",
                (report_id, action, status, detail[:2000], time.time()),
            )

    def archive(self, result: ExtractionResult, blocks: list[DocumentBlock]) -> dict:
        company_id = self.upsert_company(result.company.name, result.company.ticker, result.company.sector)
        report_id = self.upsert_report(company_id, result.source, result)
        n_metrics = self.upsert_metric_facts(report_id, company_id, result)
        n_chunks = self.upsert_chunks(report_id, blocks)
        n_risks = self.upsert_risks(report_id, company_id, result)
        self.audit(report_id, "archive", f"metrics={n_metrics} chunks={n_chunks} risks={n_risks}")
        return {"company_id": company_id, "report_id": report_id, "metrics": n_metrics, "chunks": n_chunks, "risks": n_risks}

    # ---------- 查询（公司卡片聚合视图） ----------
    def query_company_card(self, company_id: str) -> dict:
        company = self.conn.execute(
            "SELECT * FROM company WHERE company_id=?", (company_id,)
        ).fetchone()
        if company is None:
            return {}
        reports = [dict(r) for r in self.conn.execute(
            "SELECT report_id, broker, report_date, title, rating, target_price FROM report WHERE company_id=? ORDER BY report_date",
            (company_id,),
        ).fetchall()]
        metrics: dict[str, list[dict]] = {}
        for row in self.conn.execute(
            "SELECT metric_name, period, value, unit, source_page, source_section, report_id FROM metric_fact WHERE company_id=? ORDER BY metric_name, period",
            (company_id,),
        ).fetchall():
            metrics.setdefault(row["metric_name"], []).append(dict(row))
        risks = [dict(r) for r in self.conn.execute(
            "SELECT risk_text, category FROM risk WHERE company_id=?", (company_id,)
        ).fetchall()]
        return {
            "company": dict(company),
            "reports": reports,
            "metrics": metrics,
            "risks": risks,
        }

    def list_reports(self) -> list[dict]:
        return [
            dict(r)
            for r in self.conn.execute(
                "SELECT report_id, title, broker, report_date FROM report ORDER BY report_date"
            ).fetchall()
        ]

    def close(self) -> None:
        self.conn.close()
