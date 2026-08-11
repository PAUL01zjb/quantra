"""混合检索：BM25 + 可插拔向量/重排，RRF 融合。

当前 MVP 默认只用 BM25；接入向量检索只需实现 embedder 接口
（embed(texts) -> ndarray）并传入 HybridRetriever。
"""

from __future__ import annotations

from typing import Optional

from quantra.models import Chunk, RetrievedChunk
from quantra.providers.embeddings import Embedder
from quantra.providers.reranker import Reranker
from quantra.providers.vectorstore import VectorStore
from quantra.retrieval.bm25 import BM25


class HybridRetriever:
    def __init__(
        self,
        chunks: list[Chunk],
        embedder: Optional[Embedder] = None,
        vector_store: Optional[VectorStore] = None,
        reranker: Optional[Reranker] = None,
    ):
        self.chunks = chunks
        self.bm25 = BM25().fit([c.text for c in chunks])
        self.embedder = embedder
        self.vector_store = vector_store
        self.reranker = reranker
        self._vectors = None
        if embedder is not None and vector_store is None:
            self._vectors = embedder.embed([c.text for c in chunks])
        if embedder is not None and vector_store is not None and len(chunks):
            vector_store.add(
                [c.chunk_id for c in chunks],
                embedder.embed([c.text for c in chunks]),
                [{"report_id": c.report_id, "heading": c.heading} for c in chunks],
            )

    def search(
        self,
        query: str,
        k: int = 8,
        report_ids: Optional[set[str]] = None,
    ) -> list[RetrievedChunk]:
        idx_to_cid = {i: c.chunk_id for i, c in enumerate(self.chunks)}
        filter_idx = (
            {i for i, c in enumerate(self.chunks) if c.report_id in report_ids}
            if report_ids
            else None
        )

        bm25_hits = self.bm25.top_k(query, k=min(k * 4, max(10, len(self.chunks))), filter_ids=filter_idx)
        scores: dict[str, float] = {}
        for rank, (idx, _score) in enumerate(bm25_hits):
            cid = idx_to_cid[idx]
            scores[cid] = 1.0 / (60 + rank)  # RRF 贡献

        if self._vectors is not None and len(self.chunks) > 0:
            import numpy as np

            qv = np.asarray(self.embedder.embed([query])[0])
            sims = self._vectors @ qv
            order = np.argsort(-sims)
            for rank, idx in enumerate(order[: k * 2]):
                cid = idx_to_cid[int(idx)]
                scores[cid] = scores.get(cid, 0.0) + 1.0 / (60 + rank)

        if self.vector_store is not None and self.embedder is not None:
            qv = self.embedder.embed([query])[0]
            for rank, (cid, _score) in enumerate(self.vector_store.search(qv, top_k=k * 2)):
                scores[cid] = scores.get(cid, 0.0) + 1.0 / (60 + rank)

        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:k]
        by_id = {c.chunk_id: c for c in self.chunks}
        results = [
            RetrievedChunk(chunk=by_id[cid], score=score, source="rrf")
            for cid, score in ranked
        ]
        if self.reranker is not None and results:
            try:
                scores = self.reranker.rerank(query, [r.chunk.text for r in results])
                for result, score in zip(results, scores):
                    result.score = float(score)
                results.sort(key=lambda r: r.score, reverse=True)
            except RuntimeError:
                pass
        return results
