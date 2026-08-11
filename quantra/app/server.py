"""Quantra 本地主界面（零依赖 Web UI）。

stdlib http.server + 单页前端，无需安装任何 Web 框架。
API 均走同一套业务模块：ArchiveStore / IngestionPipeline / ask / confirm / memory。
"""

from __future__ import annotations

import base64
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from quantra.retrieval.hybrid import HybridRetriever


WEB_DIR = Path(__file__).resolve().parent / "web"


def _ctx():
    from quantra.config import get_settings
    from quantra.storage.archive import ArchiveStore

    settings = get_settings()
    store = ArchiveStore(settings.db_path)
    chunks = store.load_chunks()
    retriever = HybridRetriever(chunks) if chunks else None
    return store, retriever


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # noqa: D102
        pass

    # ---------- 基础 ----------
    def _json(self, obj, status: int = 200) -> None:
        body = json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _html(self) -> None:
        index = WEB_DIR / "index.html"
        body = index.read_bytes() if index.exists() else b"<h1>index.html missing</h1>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length).decode("utf-8")) if length else {}

    # ---------- API ----------
    def _overview(self) -> dict:
        store, _ = _ctx()
        try:
            return {
                "companies": store.conn.execute("SELECT COUNT(*) FROM company").fetchone()[0],
                "reports": store.conn.execute("SELECT COUNT(*) FROM report").fetchone()[0],
                "metrics": store.conn.execute("SELECT COUNT(*) FROM metric_fact").fetchone()[0],
                "chunks": store.conn.execute("SELECT COUNT(*) FROM document_chunk").fetchone()[0],
                "memories": store.conn.execute("SELECT COUNT(*) FROM memory").fetchone()[0],
                "raw_docs": store.get_raw_docs(),
            }
        finally:
            store.close()

    def _companies(self) -> dict:
        store, _ = _ctx()
        try:
            rows = store.conn.execute(
                """SELECT c.company_id, c.name, c.ticker, c.sector,
                          COUNT(DISTINCT r.report_id) AS reports,
                          COUNT(m.fact_id) AS metric_count
                   FROM company c
                   LEFT JOIN report r ON r.company_id = c.company_id
                   LEFT JOIN (SELECT company_id, rowid AS fact_id FROM metric_fact) m ON m.company_id = c.company_id
                   GROUP BY c.company_id ORDER BY c.name"""
            ).fetchall()
            return {"companies": [dict(r) for r in rows]}
        finally:
            store.close()

    def _company(self, company_id: str) -> dict:
        store, _ = _ctx()
        try:
            return {"card": store.query_company_card(company_id)}
        finally:
            store.close()

    def _memories(self, keyword: str = "") -> dict:
        store, _ = _ctx()
        try:
            rows = store.memory_search(keyword) if keyword else store.list_memories(limit=100)
            return {"memories": rows}
        finally:
            store.close()

    def _ask(self, body: dict) -> dict:
        from quantra.query.pipeline import ask

        store, retriever = _ctx()
        try:
            if retriever is None:
                return {"error": "知识库为空，请先上传研报"}
            question = body.get("question", "")
            answer = ask(question, store, retriever)
            return {
                "question": answer.question,
                "answer": answer.answer,
                "intent": answer.intent,
                "channel": answer.channel,
                "fallback": answer.fallback,
                "citations": answer.citations,
                "memories": answer.memories,
            }
        finally:
            store.close()

    def _confirm(self, body: dict) -> dict:
        from quantra.memory.extractor import confirm_facts
        from quantra.query.pipeline import ask

        store, retriever = _ctx()
        try:
            if retriever is None:
                return {"error": "知识库为空"}
            question = body.get("question", "")
            answer = ask(question, store, retriever)
            memory_ids = confirm_facts(question, answer, store)
            return {"memory_count": len(memory_ids), "answer": answer.answer}
        finally:
            store.close()

    def _correct(self, body: dict) -> dict:
        from quantra.memory.extractor import correct_answer

        store, _ = _ctx()
        try:
            memory_id = correct_answer(body.get("question", ""), body.get("correction", ""), store)
            return {"memory_id": memory_id}
        finally:
            store.close()

    def _ingest(self, body: dict) -> dict:
        from quantra.config import get_settings
        from quantra.ingestion.pipeline import IngestionPipeline

        filename = Path(body.get("filename", "upload.pdf")).name
        content = base64.b64decode(body.get("content_b64", ""))
        upload_dir = Path(get_settings().db_path).parent / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        target = upload_dir / filename
        target.write_bytes(content)
        try:
            result = IngestionPipeline().ingest(str(target))
            return {
                "doc_id": result["doc_id"],
                "tags": result["tags"],
                "metrics": result["metrics"],
                "chunks": result["chunks"],
                "risks": result["risks"],
            }
        except Exception as exc:  # noqa: BLE001
            return {"error": str(exc)}

    # ---------- HTTP 分发 ----------
    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/":
            return self._html()
        if parsed.path == "/api/overview":
            return self._json(self._overview())
        if parsed.path == "/api/companies":
            return self._json(self._companies())
        if parsed.path == "/api/company":
            params = parse_qs(parsed.query)
            company_id = params.get("company_id", [""])[0]
            return self._json(self._company(company_id))
        if parsed.path == "/api/memories":
            params = parse_qs(parsed.query)
            return self._json(self._memories(params.get("keyword", [""])[0]))
        self._json({"error": "not found"}, 404)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        body = self._read_json()
        if parsed.path == "/api/ask":
            return self._json(self._ask(body))
        if parsed.path == "/api/confirm":
            return self._json(self._confirm(body))
        if parsed.path == "/api/correct":
            return self._json(self._correct(body))
        if parsed.path == "/api/ingest":
            return self._json(self._ingest(body))
        self._json({"error": "not found"}, 404)


def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"🌐 Quantra 主界面已启动: http://{host}:{server.server_address[1]}")
    print("   Ctrl+C 停止")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")
    finally:
        server.server_close()


def make_server(host: str = "127.0.0.1", port: int = 0):
    """供测试/嵌入使用：返回已启动的 server。"""
    server = ThreadingHTTPServer((host, port), Handler)
    return server
