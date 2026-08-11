"""Embedding providers: OpenAI-compatible API, local bge-m3, deterministic fallback."""

from __future__ import annotations

import hashlib
import json
import urllib.request

import numpy as np

from quantra.config import Settings


class Embedder:
    def embed(self, texts: list[str]) -> np.ndarray:
        raise NotImplementedError


class DummyEmbedder(Embedder):
    """Deterministic hash-based embeddings (no key / no model required)."""

    def __init__(self, dim: int = 64):
        self.dim = dim

    def embed(self, texts: list[str]) -> np.ndarray:
        rows = []
        for text in texts:
            vector = np.zeros(self.dim, dtype=np.float32)
            for token in text.split():
                idx = int(hashlib.md5(token.encode("utf-8")).hexdigest()[:8], 16) % self.dim
                vector[idx] += 1.0
            norm = np.linalg.norm(vector)
            rows.append(vector / norm if norm else vector)
        return np.vstack(rows)


class OpenAIEmbedder(Embedder):
    """OpenAI-compatible embeddings endpoint."""

    def __init__(self, settings: Settings):
        self.settings = settings

    def embed(self, texts: list[str]) -> np.ndarray:
        if not self.settings.embedding_api_key:
            raise RuntimeError("Embedding API key not configured (QUANTRA_EMBEDDING_API_KEY)")
        url = (self.settings.embedding_api_base or self.settings.api_base).rstrip("/") + "/embeddings"
        payload = json.dumps({"model": self.settings.embedding_model, "input": texts}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.settings.embedding_api_key}",
            },
        )
        with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310
            body = json.loads(resp.read().decode("utf-8"))
        return np.asarray([item["embedding"] for item in body["data"]], dtype=np.float32)


class BGEEmbedder(Embedder):
    """Local bge-m3 via sentence-transformers (optional heavy dependency)."""

    def __init__(self, model_name: str = "BAAI/bge-m3"):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "sentence-transformers not installed. Add the production extras: "
                "pip install -e '.[production]'"
            ) from exc
        self.model = SentenceTransformer(model_name)

    def embed(self, texts: list[str]) -> np.ndarray:
        return self.model.encode(texts, normalize_embeddings=True)


def build_embedder(settings: Settings) -> Embedder:
    provider = settings.embedding_provider
    if provider in ("openai", "api"):
        return OpenAIEmbedder(settings)
    if provider == "bge-m3":
        return BGEEmbedder(settings.embedding_model)
    if provider == "none":
        return DummyEmbedder()
    # auto: API key -> OpenAI-compatible; otherwise deterministic fallback
    if settings.embedding_api_key or settings.api_key:
        return OpenAIEmbedder(settings)
    return DummyEmbedder()
