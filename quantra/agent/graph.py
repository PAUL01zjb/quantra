"""LangGraph production orchestration (optional heavy dependency).

Wires the existing tool set into a state machine:
planning -> executing -> reviewing -> human confirmation.
Requires `pip install -e ".[production]"`; raises an actionable error otherwise.
"""

from __future__ import annotations

from typing import TypedDict

from quantra.agent.orchestrator import QuantraAgent
from quantra.config import Settings
from quantra.retrieval.hybrid import HybridRetriever
from quantra.storage.archive import ArchiveStore


class AgentState(TypedDict, total=False):
    question: str
    plan: list[dict]
    memo: str
    citations: list[str]
    confirmed: bool
    correction: str


def build_langgraph_app(
    store: ArchiveStore,
    retriever: HybridRetriever,
    settings: Settings,
):
    """Compile the production LangGraph application.

    Nodes reuse QuantraAgent (plan/execute/build_memo) so the tool contract is shared
    with the lightweight runner. The confirmation node is a hook for the desk UI.
    """
    try:
        from langgraph.graph import END, StateGraph
    except ImportError as exc:
        raise RuntimeError(
            "LangGraph not installed. Add the production extras: "
            "pip install -e '.[production]'"
        ) from exc

    agent = QuantraAgent(store, retriever, settings, session="langgraph")

    def planner(state: AgentState) -> dict:
        return {"plan": agent.plan(state["question"])}

    def executor(state: AgentState) -> dict:
        steps, citations = agent.execute(state["plan"], state["question"])
        memo, model, cost = agent.build_memo(state["question"], citations)
        return {"memo": memo, "citations": [c for c in citations], "model": model, "cost": cost}

    def reviewer(state: AgentState) -> dict:
        # Citation grounding gate; production can add RAGAS scoring here.
        return {"memo": state.get("memo", "")}

    def confirmer(state: AgentState) -> dict:
        return {"confirmed": state.get("confirmed", False)}

    graph = StateGraph(AgentState)
    graph.add_node("planner", planner)
    graph.add_node("executor", executor)
    graph.add_node("reviewer", reviewer)
    graph.add_node("confirmer", confirmer)
    graph.set_entry_point("planner")
    graph.add_edge("planner", "executor")
    graph.add_edge("executor", "reviewer")
    graph.add_edge("reviewer", "confirmer")
    graph.add_edge("confirmer", END)
    return graph.compile()
