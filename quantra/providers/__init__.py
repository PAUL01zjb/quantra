"""Pluggable providers: LLM, embeddings, vector store, reranker, observability."""

from quantra.providers.embeddings import (
    BGEEmbedder,
    DummyEmbedder,
    Embedder,
    OpenAIEmbedder,
    build_embedder,
)
from quantra.providers.llm import LLMClient
from quantra.providers.observability import LangfuseTracer, NullTracer, build_tracer
from quantra.providers.reranker import (
    BGEEmbeddingReranker,
    NoopReranker,
    Reranker,
    build_reranker,
)
from quantra.providers.vectorstore import (
    InMemoryVectorStore,
    QdrantVectorStore,
    VectorStore,
    build_vectorstore,
)

__all__ = [
    "Embedder",
    "DummyEmbedder",
    "OpenAIEmbedder",
    "BGEEmbedder",
    "build_embedder",
    "LLMClient",
    "VectorStore",
    "InMemoryVectorStore",
    "QdrantVectorStore",
    "build_vectorstore",
    "Reranker",
    "NoopReranker",
    "BGEEmbeddingReranker",
    "build_reranker",
    "NullTracer",
    "LangfuseTracer",
    "build_tracer",
]
