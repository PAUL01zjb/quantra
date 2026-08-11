import os
import tempfile
import unittest
import uuid
from pathlib import Path

from quantra.query.pipeline import ask
from quantra.retrieval.hybrid import HybridRetriever
from quantra.storage.archive import ArchiveStore


SAMPLES = Path(__file__).resolve().parents[1] / "data" / "samples"


class TestAskPipeline(unittest.TestCase):
    def setUp(self):
        self.tmp_db = Path(tempfile.gettempdir()) / f"quantra_ask_{uuid.uuid4().hex}.db"
        self.store = ArchiveStore(self.tmp_db)
        from quantra.extraction.extractor import extract
        from quantra.parsing import parse_document
        from quantra.parsing.interfaces import ParseRequest

        chunks = []
        for name in ["示例-消费龙头2025年报点评.md", "示例-同业公司2025年报点评.md"]:
            parse_result = parse_document(ParseRequest(source=str(SAMPLES / name)))
            self.store.archive(extract(parse_result), parse_result.blocks)
            chunks.extend(self.store.load_chunks())
        self.retriever = HybridRetriever(chunks)

    def tearDown(self):
        self.store.close()
        if self.tmp_db.exists():
            self.tmp_db.unlink()

    def test_fact_question_uses_structured_channel(self):
        result = ask("消费龙头2025年毛利率是多少？", self.store, self.retriever)
        self.assertEqual(result.channel, "structured")
        self.assertFalse(result.fallback)
        self.assertIn("32.5", result.answer)
        self.assertGreaterEqual(len(result.citations), 1)

    def test_coverage_fallback_to_docs(self):
        # 消费龙头示例里没有"净息差"（银行指标），结构化未命中应自动降级
        result = ask("消费龙头2025年净息差是多少？", self.store, self.retriever)
        self.assertEqual(result.channel, "doc")
        self.assertTrue(result.fallback)
        self.assertGreaterEqual(len(result.citations), 1)

    def test_semantic_question_uses_doc_channel(self):
        result = ask("怎么看消费龙头的盈利质量？", self.store, self.retriever)
        self.assertEqual(result.channel, "doc")
        self.assertFalse(result.fallback)


if __name__ == "__main__":
    unittest.main()
