"""SQLite 单文件存储：研报、章节、指标、检索分块、审计日志、记忆。"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Iterable

from quantra.models import Chunk, Metric, Report


SCHEMA = """
CREATE TABLE IF NOT EXISTS reports (
    report_id TEXT PRIMARY KEY,
    source_path TEXT,
    title TEXT,
    institution TEXT,
    analyst TEXT,
    date TEXT,
    rating TEXT,
    target_price TEXT,
    summary TEXT,
    created_at REAL
);
CREATE TABLE IF NOT EXISTS sections (
    report_id TEXT,
    heading TEXT,
    level INTEGER,
    page INTEGER,
    text TEXT
);
CREATE TABLE IF NOT EXISTS metrics (
    report_id TEXT,
    name TEXT,
    value TEXT,
    unit TEXT,
    period TEXT,
    source TEXT
);
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id TEXT PRIMARY KEY,
    report_id TEXT,
    heading TEXT,
    page INTEGER,
    text TEXT,
    tokens INTEGER
);
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL,
    session TEXT,
    action TEXT,
    detail TEXT,
    model TEXT,
    cost REAL,
    status TEXT
);
CREATE TABLE IF NOT EXISTS memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL,
    kind TEXT,
    content TEXT,
    tags TEXT
);
"""


def _report_id(source_path: str) -> str:
    return hashlib.sha1(source_path.encode("utf-8")).hexdigest()[:16]


class Store:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)

    # ---------- 研报入库 ----------
    def upsert_report(self, report: Report) -> str:
        rid = _report_id(report.source_path)
        with self.conn:
            self.conn.execute(
                """INSERT OR REPLACE INTO reports
                   (report_id, source_path, title, institution, analyst, date,
                    rating, target_price, summary, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    rid,
                    report.source_path,
                    report.title,
                    report.institution,
                    report.analyst,
                    report.date,
                    report.rating,
                    report.target_price,
                    report.summary,
                    time.time(),
                ),
            )
            self.conn.execute("DELETE FROM sections WHERE report_id=?", (rid,))
            for section in report.sections:
                self.conn.execute(
                    "INSERT INTO sections (report_id, heading, level, page, text) VALUES (?,?,?,?,?)",
                    (rid, section.heading, section.level, section.page, section.text),
                )
            self.conn.execute("DELETE FROM metrics WHERE report_id=?", (rid,))
            for metric in report.metrics:
                self.conn.execute(
                    "INSERT INTO metrics (report_id, name, value, unit, period, source) VALUES (?,?,?,?,?,?)",
                    (rid, metric.name, metric.value, metric.unit, metric.period, metric.source),
                )
        return rid

    def store_chunks(self, chunks: Iterable[Chunk]) -> None:
        with self.conn:
            self.conn.executemany(
                """INSERT OR REPLACE INTO chunks
                   (chunk_id, report_id, heading, page, text, tokens)
                   VALUES (?,?,?,?,?,?)""",
                [
                    (c.chunk_id, c.report_id, c.heading, c.page, c.text, c.tokens)
                    for c in chunks
                ],
            )

    # ---------- 查询 ----------
    def list_reports(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT report_id, title, institution, date, rating, target_price FROM reports ORDER BY created_at"
        ).fetchall()
        return [dict(r) for r in rows]

    def get_report_metrics(self, report_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT name, value, unit, period, source FROM metrics WHERE report_id=?",
            (report_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def load_chunks(self) -> list[Chunk]:
        rows = self.conn.execute(
            "SELECT chunk_id, report_id, heading, page, text FROM chunks"
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

    # ---------- 审计 ----------
    def audit(
        self,
        action: str,
        detail: str = "",
        model: str = "",
        cost: float = 0.0,
        status: str = "ok",
        session: str = "cli",
    ) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT INTO audit_log (ts, session, action, detail, model, cost, status) VALUES (?,?,?,?,?,?,?)",
                (time.time(), session, action, detail[:2000], model, cost, status),
            )

    def audit_log(self, limit: int = 50) -> list[dict]:
        rows = self.conn.execute(
            "SELECT id, ts, session, action, detail, model, cost, status FROM audit_log ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    # ---------- 记忆 ----------
    def memory_append(self, kind: str, content: str, tags: str = "") -> None:
        with self.conn:
            self.conn.execute(
                "INSERT INTO memory (ts, kind, content, tags) VALUES (?,?,?,?)",
                (time.time(), kind, content, tags),
            )

    def memory_search(self, query: str, limit: int = 10) -> list[dict]:
        rows = self.conn.execute(
            """SELECT id, ts, kind, content, tags FROM memory
               WHERE content LIKE ? OR tags LIKE ? OR kind LIKE ?
               ORDER BY id DESC LIMIT ?""",
            (f"%{query}%", f"%{query}%", f"%{query}%", limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def close(self) -> None:
        self.conn.close()
