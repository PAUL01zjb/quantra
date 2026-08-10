import os
import tempfile
import unittest
import uuid
from pathlib import Path

from quantra.extraction.extractor import extract
from quantra.parsing import parse_document
from quantra.parsing.interfaces import ParseRequest
from quantra.storage.archive import ArchiveStore


SAMPLE_MD = Path(__file__).resolve().parents[1] / "data" / "samples" / "示例-消费龙头2025年报点评.md"


class TestArchive(unittest.TestCase):
    def setUp(self):
        self.tmp_db = Path(tempfile.gettempdir()) / f"quantra_arch_{uuid.uuid4().hex}.db"
        self.store = ArchiveStore(self.tmp_db)

    def tearDown(self):
        self.store.close()
        if self.tmp_db.exists():
            self.tmp_db.unlink()

    def test_archive_roundtrip(self):
        parse_result = parse_document(ParseRequest(source=str(SAMPLE_MD)))
        result = extract(parse_result)
        ids = self.store.archive(result, parse_result.blocks)

        card = self.store.query_company_card(ids["company_id"])
        self.assertEqual(card["company"]["name"], "消费龙头")
        self.assertIn("毛利率", card["metrics"])
        self.assertGreaterEqual(len(card["risks"]), 1)
        self.assertGreaterEqual(ids["metrics"], 8)
        self.assertGreaterEqual(ids["chunks"], 1)

        audits = self.store.conn.execute(
            "SELECT action, status FROM extraction_audit WHERE report_id=?", (ids["report_id"],)
        ).fetchall()
        self.assertGreaterEqual(len(audits), 1)


if __name__ == "__main__":
    unittest.main()
