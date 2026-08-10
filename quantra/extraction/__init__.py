"""抽取层：ParseResult -> ExtractionResult（结构化事实，供归档入库）。"""

from quantra.extraction.extractor import ExtractionResult, extract

__all__ = ["ExtractionResult", "extract"]
