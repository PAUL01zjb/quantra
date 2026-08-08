"""业务场景模拟器：用真实业务工作流驱动 Agent 与评测。"""

from quantra.scenarios.registry import get_scenario, list_scenarios
from quantra.scenarios.simulator import ScenarioRunner

__all__ = ["ScenarioRunner", "get_scenario", "list_scenarios"]
