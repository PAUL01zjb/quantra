import os
import tempfile
import unittest
import uuid
from pathlib import Path

from quantra.ingestion.pipeline import IngestionPipeline


SAMPLE_MD = Path(__file__).resolve().parents[1] / "data" / "samples" / "示例-消费龙头2025年报点评.md"


class TestIngestionPipeline(unittest.TestCase):
    def setUp(self):
        self.tmp_db = Path(tempfile.gettempdir()) / f"quantra_ingest_{uuid.uuid4().hex}.db"
        os.environ["QUANTRA_DB_PATH"] = str(self.tmp_db)

    def tearDown(self):
        os.environ.pop("QUANTRA_DB_PATH", None)
        if self.tmp_db.exists():
            self.tmp_db.unlink()

    def test_ingest_registers_doc_and_tags(self):
        pipeline = IngestionPipeline()
        result = pipeline.ingest(str(SAMPLE_MD))
        self.assertTrue(result["doc_id"])
        self.assertEqual(result["tags"]["company"], "消费龙头")
        self.assertEqual(result["tags"]["report_type"], "年报")
        self.assertEqual(result["tags"]["broker"], "华泰证券")
        self.assertGreaterEqual(result["metrics"], 8)

        docs = pipeline.store.get_raw_docs(tag_key="company", tag_value="消费龙头")
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0]["tags"]["report_type"], "年报")
        pipeline.close()


if __name__ == "__main__":
    unittest.main()
