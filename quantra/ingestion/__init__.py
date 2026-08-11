"""入库管道：上传 → 解析 → 抽取 → 打标 → 双写（结构化库 + 原始文档登记）。"""

from quantra.ingestion.pipeline import IngestionPipeline

__all__ = ["IngestionPipeline"]
