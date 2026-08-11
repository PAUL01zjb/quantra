"""Reranker providers: no-op, bge-reranker (optional)."""

from __future__ import annotations

from quantra.config import Settings


class Reranker:
    def rerank(self, query: str, documents: list[str]) -> list[float]:
        raise NotImplementedError


class NoopReranker(Reranker):
    def rerank(self, query, documents):
        return [1.0] * len(documents)


class BGEEmbeddingReranker(Reranker):
    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3"):
        try:
            from FlagEmbedding import FlagReranker
        except ImportError as exc:
            raise RuntimeError(
                "FlagEmbedding not installed. Add the production extras: "
                "pip install -e '.[production]'"
            ) from exc
        self.model = FlagReranker(model_name, use_fp16=True)

    def rerank(self, query, documents):
        pairs = [[query, doc] for doc in documents]
        return self.model.compute_score(pairs)


def build_reranker(settings: Settings) -> Reranker:
    if settings.reranker == "bge":
        return BGEEmbeddingReranker()
    return NoopReranker()
