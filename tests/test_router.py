import os
import tempfile
import unittest
import uuid
from pathlib import Path

from quantra.query.router import classify, detect_metric, extract_ticker
from quantra.storage.archive import ArchiveStore


SAMPLE_MD = Path(__file__).resolve().parents[1] / "data" / "samples" / "示例-消费龙头2025年报点评.md"


class TestRouter(unittest.TestCase):
    def setUp(self):
        self.tmp_db = Path(tempfile.gettempdir()) / f"quantra_router_{uuid.uuid4().hex}.db"
        self.store = ArchiveStore(self.tmp_db)
        from quantra.extraction.extractor import extract
        from quantra.parsing import parse_document
        from quantra.parsing.interfaces import ParseRequest

        parse_result = parse_document(ParseRequest(source=str(SAMPLE_MD)))
        self.store.archive(extract(parse_result), parse_result.blocks)

    def tearDown(self):
        self.store.close()
        if self.tmp_db.exists():
            self.tmp_db.unlink()

    def test_fact_intent_with_metric(self):
        decision = classify("消费龙头2025年毛利率是多少？", self.store)
        self.assertEqual(decision.intent, "fact")
        self.assertEqual(decision.metric, "毛利率")
        self.assertTrue(decision.company_id.startswith("co_"))  # 无 ticker，名称 hash 兜底

    def test_semantic_intent(self):
        decision = classify("怎么看消费龙头的资产质量风险？", self.store)
        self.assertEqual(decision.intent, "semantic")

    def test_document_intent(self):
        decision = classify("招商银行这份研报的原文第几页有毛利率？", self.store)
        self.assertEqual(decision.intent, "document")

    def test_ticker_extraction(self):
        self.assertEqual(extract_ticker("招商银行(600036)怎么样"), "600036.SH")
        self.assertEqual(extract_ticker("中信证券600030.SH"), "600030.SH")
        self.assertIsNone(extract_ticker("没有代码"))

    def test_metric_detection(self):
        self.assertEqual(detect_metric("净息差是多少"), "净息差")
        self.assertEqual(detect_metric("营收多少"), "营业收入")


if __name__ == "__main__":
    unittest.main()
