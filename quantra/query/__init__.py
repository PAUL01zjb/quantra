"""问数路由层：规则路由 → 双通道查询（结构化/文档）→ 覆盖度降级。"""

from quantra.query.pipeline import QueryAnswer, ask

__all__ = ["QueryAnswer", "ask"]
