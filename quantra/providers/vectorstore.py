"""Vector store providers: Qdrant, pgvector, in-memory fallback."""

from __future__ import annotations

import numpy as np

from quantra.config import Settings


class VectorStore:
    def add(self, ids: list[str], vectors: np.ndarray, metadatas: list[dict] | None = None) -> None:
        raise NotImplementedError

    def search(self, query: np.ndarray, top_k: int = 10) -> list[tuple[str, float]]:
        raise NotImplementedError


class InMemoryVectorStore(VectorStore):
    def __init__(self, dim: int = 64):
        self.dim = dim
        self.ids: list[str] = []
        self.vectors: np.ndarray | None = None
        self.metadatas: list[dict] = []

    def add(self, ids, vectors, metadatas=None):
        vectors = np.asarray(vectors, dtype=np.float32)
        self.ids.extend(ids)
        self.metadatas.extend(metadatas or [{}] * len(ids))
        self.vectors = vectors if self.vectors is None else np.vstack([self.vectors, vectors])

    def search(self, query, top_k=10):
        if self.vectors is None or len(self.ids) == 0:
            return []
        scores = self.vectors @ np.asarray(query, dtype=np.float32).reshape(-1)
        order = np.argsort(-scores)[:top_k]
        return [(self.ids[int(i)], float(scores[int(i)])) for i in order]


class QdrantVectorStore(VectorStore):
    def __init__(self, url: str, collection: str, api_key: str = ""):
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams
        except ImportError as exc:
            raise RuntimeError(
                "qdrant-client not installed. Add the production extras: "
                "pip install -e '.[production]'"
            ) from exc
        self.client = QdrantClient(url=url, api_key=api_key or None)
        self.collection = collection
        self._vector_params = VectorParams(size=1024, distance=Distance.COSINE)
        self.client.recreate_collection(collection_name=collection, vectors_config=self._vector_params)

    def add(self, ids, vectors, metadatas=None):
        from qdrant_client.models import PointStruct

        points = [
            PointStruct(id=idx, vector=vec.tolist(), payload=(metadatas or [{}])[idx])
            for idx, vec in enumerate(np.asarray(vectors))
        ]
        self.client.upsert(collection_name=self.collection, points=points)

    def search(self, query, top_k=10):
        hits = self.client.search(
            collection_name=self.collection, query_vector=np.asarray(query).tolist(), limit=top_k
        )
        return [(str(h.id), float(h.score)) for h in hits]


def build_vectorstore(settings: Settings) -> VectorStore:
    if settings.vector_store == "qdrant":
        return QdrantVectorStore(
            settings.vector_store_url, settings.vector_store_collection, settings.api_key
        )
    if settings.vector_store == "pgvector":
        raise NotImplementedError("pgvector provider: provide connection via QUANTRA_VECTOR_STORE_URL")
    return InMemoryVectorStore()
