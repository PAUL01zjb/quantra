"""交互式配置向导的纯逻辑部分（可测试）：写 .env → 初始化库 → 可选导入样例 → 可选验证。"""

from __future__ import annotations

import os
from pathlib import Path


def run_setup(
    base_url: str,
    api_key: str,
    db_path: str,
    ingest_samples: bool = True,
    run_verify: bool = True,
    root: Path | None = None,
) -> dict:
    root = root or Path.cwd()
    env_path = root / ".env"

    env_lines = [
        f"QUANTRA_LLM_BASE_URL={base_url}",
        f"QUANTRA_API_KEY={api_key}",
        f"QUANTRA_DB_PATH={db_path}",
    ]
    env_path.write_text("\n".join(env_lines) + "\n", encoding="utf-8")
    try:
        os.chmod(env_path, 0o600)
    except OSError:
        pass

    os.environ["QUANTRA_LLM_BASE_URL"] = base_url
    os.environ["QUANTRA_API_KEY"] = api_key
    os.environ["QUANTRA_DB_PATH"] = db_path

    from quantra.config import get_settings
    from quantra.storage.archive import ArchiveStore

    settings = get_settings()
    store = ArchiveStore(settings.db_path)
    store.close()

    results = {"env": str(env_path), "db": str(settings.db_path)}
    if ingest_samples:
        results["samples"] = _ingest_samples(root)
    if run_verify:
        from quantra.verification.verify import run_verification

        verify = run_verification()
        results["verify_passed"] = verify.passed
        results["verify_checks"] = f"{sum(1 for c in verify.checks if c.ok)}/{len(verify.checks)}"
    return results


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
