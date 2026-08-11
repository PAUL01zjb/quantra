"""Configuration wizard (config-driven, testable).

Wires production providers: LLM, embeddings, vector store, parser engine, observability.
Secrets are written only to the local `.env` (mode 0600).
"""

from __future__ import annotations

import os
from pathlib import Path


ENV_KEY_MAP: dict[str, str] = {
    "api_base": "QUANTRA_LLM_BASE_URL",
    "api_key": "QUANTRA_API_KEY",
    "primary_model": "QUANTRA_PRIMARY_MODEL",
    "cheap_model": "QUANTRA_CHEAP_MODEL",
    "db_path": "QUANTRA_DB_PATH",
    "embedding_provider": "QUANTRA_EMBEDDING_PROVIDER",
    "embedding_model": "QUANTRA_EMBEDDING_MODEL",
    "embedding_api_base": "QUANTRA_EMBEDDING_API_BASE",
    "embedding_api_key": "QUANTRA_EMBEDDING_API_KEY",
    "vector_store": "QUANTRA_VECTOR_STORE",
    "vector_store_url": "QUANTRA_VECTOR_STORE_URL",
    "vector_store_collection": "QUANTRA_VECTOR_STORE_COLLECTION",
    "reranker": "QUANTRA_RERANKER",
    "parser_engine": "QUANTRA_PARSER_ENGINE",
    "observability": "QUANTRA_OBSERVABILITY",
    "langfuse_public_key": "QUANTRA_LANGFUSE_PUBLIC_KEY",
    "langfuse_secret_key": "QUANTRA_LANGFUSE_SECRET_KEY",
    "langfuse_host": "QUANTRA_LANGFUSE_HOST",
}

DEFAULTS: dict[str, str] = {
    "api_base": "https://api.deepseek.com/v1",
    "api_key": "",
    "primary_model": "deepseek-v4-pro",
    "cheap_model": "deepseek-v4-flash",
    "db_path": "data/quantra.db",
    "embedding_provider": "auto",
    "embedding_model": "bge-m3",
    "embedding_api_base": "",
    "embedding_api_key": "",
    "vector_store": "memory",
    "vector_store_url": "",
    "vector_store_collection": "quantra",
    "reranker": "none",
    "parser_engine": "auto",
    "observability": "none",
    "langfuse_public_key": "",
    "langfuse_secret_key": "",
    "langfuse_host": "https://cloud.langfuse.com",
}


def run_setup(
    config: dict,
    ingest_samples: bool = True,
    run_verify: bool = True,
    root: Path | None = None,
) -> dict:
    root = root or Path.cwd()
    merged = {**DEFAULTS, **{k: v for k, v in config.items() if v not in (None, "")}}
    env_path = root / ".env"

    env_lines = []
    for key, value in merged.items():
        env_name = ENV_KEY_MAP.get(key)
        if env_name:
            env_lines.append(f"{env_name}={value}")
            os.environ[env_name] = str(value)
    env_path.write_text("\n".join(env_lines) + "\n", encoding="utf-8")
    try:
        os.chmod(env_path, 0o600)
    except OSError:
        pass

    from quantra.config import get_settings
    from quantra.storage.archive import ArchiveStore

    settings = get_settings()
    store = ArchiveStore(settings.db_path)
    store.close()

    results = {"env": str(env_path), "db": str(settings.db_path), "providers": _provider_summary(merged)}
    if ingest_samples:
        results["samples"] = _ingest_samples(root)
    if run_verify:
        from quantra.verification.verify import run_verification

        verify = run_verification()
        results["verify_passed"] = verify.passed
        results["verify_checks"] = f"{sum(1 for c in verify.checks if c.ok)}/{len(verify.checks)}"
    return results


def _provider_summary(merged: dict) -> dict:
    return {
        "llm": merged.get("api_base", ""),
        "embedding": merged.get("embedding_provider", "auto"),
        "vector_store": merged.get("vector_store", "memory"),
        "reranker": merged.get("reranker", "none"),
        "parser_engine": merged.get("parser_engine", "auto"),
        "observability": merged.get("observability", "none"),
    }


def _ingest_samples(root: Path) -> dict:
    from quantra.ingestion.pipeline import IngestionPipeline

    samples = list((root / "data" / "samples").glob("*.md"))
    pipeline = IngestionPipeline()
    results = {}
    try:
        for sample in samples:
            result = pipeline.ingest(str(sample))
            results[sample.name] = {
                "metrics": result["metrics"],
                "tags_company": result["tags"]["company"],
            }
        return results
    finally:
        pipeline.close()
