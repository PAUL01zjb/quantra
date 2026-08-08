"""业务场景定义。

场景不是"测试用例"，而是真实业务工作流的可运行切片：
角色、业务任务、输入研报、问题、验收标准。
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Scenario:
    id: str
    title: str
    role: str
    business_task: str
    reports: list[str]
    questions: list[str]
    success_criteria: list[str]
    tags: list[str] = field(default_factory=list)
