"""内置业务场景注册表。"""

from __future__ import annotations

from pathlib import Path

from quantra.scenarios.scenario import Scenario


ROOT = Path(__file__).resolve().parents[2]


def _sample(name: str) -> str:
    return str(ROOT / "data" / "samples" / name)


SCENARIOS: list[Scenario] = [
    Scenario(
        id="analyst-compare",
        title="基金经理助理：两家公司盈利质量对比",
        role="基金研究助理",
        business_task=(
            "基金经理要求对比消费龙头与同业公司 2025 年毛利率水平、趋势与盈利质量，"
            "输出带引用的对比备忘录，并标注每个数据来源。"
        ),
        reports=[
            _sample("示例-消费龙头2025年报点评.md"),
            _sample("示例-同业公司2025年报点评.md"),
        ],
        questions=[
            "对比消费龙头与同业公司2025年毛利率水平，哪家更高？趋势如何？",
            "两家公司2025年营业收入和归母净利润分别是多少？",
        ],
        success_criteria=[
            "备忘录包含两家公司毛利率数值且来源可溯源",
            "引用覆盖率 ≥ 50%（dry-run 模板基线）",
            "审计日志记录全部工具调用",
        ],
        tags=["对比分析", "盈利质量", "基金经理"],
    ),
    Scenario(
        id="risk-audit",
        title="风控评审：研报风险提示核查",
        role="风控评审员",
        business_task=(
            "从研报中抽取风险提示，核查备忘录是否完整披露风险，"
            "输出带引用的风险清单。"
        ),
        reports=[_sample("示例-消费龙头2025年报点评.md")],
        questions=["该研报披露了哪些风险提示？"],
        success_criteria=[
            "备忘录列出研报披露的风险点",
            "风险点可溯源到研报章节",
        ],
        tags=["风控", "合规", "风险提示"],
    ),
]


def list_scenarios() -> list[Scenario]:
    return SCENARIOS


def get_scenario(scenario_id: str) -> Scenario:
    for scenario in SCENARIOS:
        if scenario.id == scenario_id:
            return scenario
    raise KeyError(f"场景不存在: {scenario_id}，可用场景: {[s.id for s in SCENARIOS]}")
