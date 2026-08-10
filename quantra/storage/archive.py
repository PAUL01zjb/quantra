"""归档存储：把 ExtractionResult 落库，并提供"公司卡片"聚合视图。"""

from __future__ import annotations

import hashlib
import sqlite3
import time
from pathlib import Path

from quantra.extraction.extractor import ExtractionResult
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

    def close(self) -> None:
        self.conn.close()
