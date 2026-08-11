import base64
import json
import os
import tempfile
import threading
import unittest
import urllib.request
import uuid
from pathlib import Path


SAMPLE = Path(__file__).resolve().parents[1] / "data" / "samples" / "示例-消费龙头2025年报点评.md"


class TestServer(unittest.TestCase):
    def setUp(self):
        self.tmp_db = Path(tempfile.gettempdir()) / f"quantra_srv_{uuid.uuid4().hex}.db"
        os.environ["QUANTRA_DB_PATH"] = str(self.tmp_db)
        from quantra.app.server import make_server

        try:
            self.server = make_server(host="127.0.0.1", port=0)
        except PermissionError as exc:
            self.skipTest(f"沙箱不允许绑定端口，跳过服务端测试: {exc}")
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        os.environ.pop("QUANTRA_DB_PATH", None)
        if self.tmp_db.exists():
            self.tmp_db.unlink()

    def _get(self, path):
        return json.loads(urllib.request.urlopen(f"http://127.0.0.1:{self.port}{path}").read())

    def _post(self, path, payload):
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        return json.loads(urllib.request.urlopen(req).read())

    def test_full_flow_overview_ingest_ask_confirm(self):
        overview = self._get("/api/overview")
        self.assertIn("companies", overview)

        content = SAMPLE.read_bytes()
        ingest = self._post(
            "/api/ingest",
            {"filename": "sample.md", "content_b64": base64.b64encode(content).decode("utf-8")},
        )
        self.assertIn("doc_id", ingest)
        self.assertEqual(ingest["tags"]["company"], "消费龙头")

        answer = self._post("/api/ask", {"question": "消费龙头2025年毛利率是多少？"})
        self.assertEqual(answer["channel"], "structured")
        self.assertIn("32.5", answer["answer"])
        self.assertGreaterEqual(len(answer["citations"]), 1)

        confirm = self._post("/api/confirm", {"question": "消费龙头2025年毛利率是多少？"})
        self.assertGreaterEqual(confirm["memory_count"], 1)


if __name__ == "__main__":
    unittest.main()
