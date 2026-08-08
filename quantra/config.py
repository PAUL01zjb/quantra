"""配置与模型成本表。

成本表为示例值，依据 8/6–8/7 情报简报中的定价信号整理
（DeepSeek V4-Flash 输出约 2 元/百万 token、V4-Pro 约 6 元，缓存命中输入约 0.02 元）。
实际以各厂商实时价格为准，上线前请更新本表。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict


DEFAULT_COST_TABLE: Dict[str, dict] = {
    "deepseek-v4-flash": {"in": 1.0, "out": 2.0, "role": "cheap", "note": "批量抽取/检索"},
    "deepseek-v4-pro": {"in": 2.0, "out": 6.0, "role": "strong", "note": "复杂推理/报告生成"},
    "gpt-5.6-luna": {"in": 0.8, "out": 3.2, "role": "cheap", "note": "备选批量模型"},
    "qwen3.8-max": {"in": 1.0, "out": 4.0, "role": "strong", "note": "备选推理模型"},
}


@dataclass
class Settings:
    api_base: str = ""
    api_key: str = ""
    primary_model: str = "deepseek-v4-pro"
    cheap_model: str = "deepseek-v4-flash"
    dry_run: bool = True
    db_path: Path = Path("data/quantra.db")
    cost_table: Dict[str, dict] = field(default_factory=lambda: dict(DEFAULT_COST_TABLE))


def get_settings() -> Settings:
    db_path = os.environ.get("QUANTRA_DB_PATH", "data/quantra.db")
    if not Path(db_path).is_absolute():
        db_path = str(Path.cwd() / db_path)

    api_key = os.environ.get("QUANTRA_API_KEY", "")
    dry_run_env = os.environ.get("QUANTRA_DRY_RUN", "")
    dry_run = (not api_key) or (dry_run_env == "1")

    return Settings(
        api_base=os.environ.get("QUANTRA_LLM_BASE_URL", "https://api.deepseek.com/v1"),
        api_key=api_key,
        primary_model=os.environ.get("QUANTRA_PRIMARY_MODEL", "deepseek-v4-pro"),
        cheap_model=os.environ.get("QUANTRA_CHEAP_MODEL", "deepseek-v4-flash"),
        dry_run=dry_run,
        db_path=Path(db_path),
    )
