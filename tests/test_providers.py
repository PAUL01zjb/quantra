import unittest

import numpy as np

from quantra.providers.embeddings import DummyEmbedder
from quantra.providers.vectorstore import InMemoryVectorStore


class TestProviders(unittest.TestCase):
    def test_dummy_embedder_deterministic(self):
        embedder = DummyEmbedder(dim=32)
        vectors = embedder.embed(["毛利率 32.5", "净息差 1.88"])
        self.assertEqual(vectors.shape, (2, 32))
        again = embedder.embed(["毛利率 32.5"])
        self.assertTrue(np.allclose(vectors[0], again[0]))

    def test_in_memory_vector_store(self):
        store = InMemoryVectorStore(dim=8)
        store.add(["a", "b"], np.eye(8, dtype=np.float32))
        hits = store.search(np.eye(8, dtype=np.float32)[0], top_k=1)
        self.assertEqual(hits[0][0], "a")

    def test_hybrid_retriever_with_vector_and_rerank(self):
        from quantra.models import Chunk
        from quantra.providers.embeddings import DummyEmbedder
        from quantra.providers.reranker import NoopReranker
        from quantra.retrieval.hybrid import HybridRetriever

        chunks = [
            Chunk(chunk_id="c1", report_id="r1", heading="h", page=1, text="公司2025年毛利率32.5%"),
            Chunk(chunk_id="c2", report_id="r1", heading="h", page=1, text="原材料价格波动是主要风险"),
        ]
        retriever = HybridRetriever(
            chunks,
            embedder=DummyEmbedder(dim=16),
            vector_store=InMemoryVectorStore(dim=16),
            reranker=NoopReranker(),
        )
        hits = retriever.search("毛利率 2025", k=2)
        self.assertGreaterEqual(len(hits), 1)
        self.assertEqual(hits[0].chunk.chunk_id, "c1")

    def test_langgraph_wiring_raises_actionable_error(self):
        from quantra.agent.graph import build_langgraph_app

        try:
            import langgraph  # noqa: F401

            self.skipTest("langgraph installed; wiring smoke tested implicitly")
        except ImportError:
            with self.assertRaises(RuntimeError) as ctx:
                build_langgraph_app(None, None, None)  # type: ignore[arg-type]
            self.assertIn("production", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
