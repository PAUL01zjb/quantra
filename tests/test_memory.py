import os
import tempfile
import unittest
import uuid
from pathlib import Path

from quantra.memory.extractor import confirm_facts, correct_answer, inject_memory
from quantra.query.pipeline import ask
from quantra.retrieval.hybrid import HybridRetriever
from quantra.storage.archive import ArchiveStore


SAMPLES = Path(__file__).resolve().parents[1] / "data" / "samples"


class TestMemory(unittest.TestCase):
    def setUp(self):
        self.tmp_db = Path(tempfile.gettempdir()) / f"quantra_mem_{uuid.uuid4().hex}.db"
        self.store = ArchiveStore(self.tmp_db)
        from quantra.extraction.extractor import extract
        from quantra.parsing import parse_document
        from quantra.parsing.interfaces import ParseRequest

        chunks = []
        parse_result = parse_document(ParseRequest(source=str(SAMPLES / "示例-消费龙头2025年报点评.md")))
        self.store.archive(extract(parse_result), parse_result.blocks)
        chunks.extend(self.store.load_chunks())
        self.retriever = HybridRetriever(chunks)

    def tearDown(self):
        self.store.close()
        if self.tmp_db.exists():
            self.tmp_db.unlink()

    def test_confirm_writes_memories_and_injects(self):
        answer = ask("消费龙头2025年毛利率是多少？", self.store, self.retriever)
        memory_ids = confirm_facts("消费龙头2025年毛利率是多少？", answer, self.store)
        self.assertGreaterEqual(len(memory_ids), 2)  # fact + conclusion

        hits = inject_memory("消费龙头毛利率", self.store)
        self.assertGreaterEqual(len(hits), 1)
        self.assertTrue(any(h["kind"] == "fact" for h in hits))

    def test_correction_memory(self):
        correct_answer("招商银行净息差单位", "净息差统一用 % 表示", self.store)
        hits = inject_memory("净息差 单位", self.store)
        self.assertTrue(any(h["kind"] == "correction" for h in hits))

    def test_ask_attaches_memories(self):
        answer = ask("消费龙头2025年毛利率是多少？", self.store, self.retriever)
        confirm_facts("消费龙头2025年毛利率是多少？", answer, self.store)
        second = ask("消费龙头2025年毛利率是多少？", self.store, self.retriever)
        self.assertGreaterEqual(len(second.memories), 1)


if __name__ == "__main__":
    unittest.main()
