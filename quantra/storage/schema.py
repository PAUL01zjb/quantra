"""归档层 Schema v2（已确认的多维复合模型）。

company（主维度，ticker 优先）→ report → metric_fact（复合键）/ document_chunk / risk / conclusion。
"""

SCHEMA_V2 = """
CREATE TABLE IF NOT EXISTS company (
    company_id TEXT PRIMARY KEY,
    ticker TEXT UNIQUE,
    name TEXT NOT NULL,
    sector TEXT,
    updated_at REAL
);

CREATE TABLE IF NOT EXISTS report (
    report_id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL REFERENCES company(company_id),
    source_path TEXT,
    broker TEXT,
    analyst TEXT,
    report_date TEXT,
    title TEXT,
    rating TEXT,
    target_price TEXT,
    ingested_at REAL
);

CREATE TABLE IF NOT EXISTS metric_fact (
    report_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    period TEXT,
    value TEXT,
    unit TEXT,
    source_page INTEGER,
    source_section TEXT,
    raw_text TEXT,
    method TEXT,
    confidence REAL,
    created_at REAL,
    PRIMARY KEY (report_id, company_id, metric_name, period)
);

CREATE TABLE IF NOT EXISTS document_chunk (
    chunk_id TEXT PRIMARY KEY,
    report_id TEXT NOT NULL,
    heading TEXT,
    page INTEGER,
    text TEXT
);

CREATE TABLE IF NOT EXISTS risk (
    risk_id TEXT PRIMARY KEY,
    report_id TEXT NOT NULL,
    company_id TEXT,
    risk_text TEXT,
    category TEXT
);

CREATE TABLE IF NOT EXISTS conclusion (
    conclusion_id TEXT PRIMARY KEY,
    report_id TEXT NOT NULL,
    company_id TEXT,
    text TEXT,
    evidence_chunk_ids TEXT
);

CREATE TABLE IF NOT EXISTS extraction_audit (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id TEXT,
    action TEXT,
    model TEXT,
    cost REAL,
    status TEXT,
    detail TEXT,
    ts REAL
);
"""
