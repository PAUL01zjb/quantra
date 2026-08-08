"""审计日志：每个工具调用/模型调用记录动作、参数、模型、成本。

对齐 8/7 简报的"银行 Agent 合规清单"：权限最小化 + 全链路审计 + 回放。
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from quantra.storage.db import Store


class AuditLogger:
    def __init__(self, store: Store, session: str = "cli"):
        self.store = store
        self.session = session

    def log(
        self,
        action: str,
        detail: str = "",
        model: str = "",
        cost: float = 0.0,
        status: str = "ok",
    ) -> None:
        self.store.audit(
            action=action,
            detail=detail,
            model=model,
            cost=cost,
            status=status,
            session=self.session,
        )

    @contextmanager
    def step(self, action: str, detail: str = "") -> Iterator[None]:
        self.log(action, detail)
        try:
            yield
        except Exception as exc:  # noqa: BLE001
            self.log(action, f"{detail} | ERROR: {exc}", status="error")
            raise
