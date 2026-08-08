"""场景模拟器：加载真实业务场景 → 入库 → Agent 执行 → 评测 → 场景报告。"""

from __future__ import annotations

import json
from pathlib import Path

from quantra.agent.orchestrator import QuantraAgent
from quantra.config import Settings, get_settings
from quantra.eval.grounding import citation_coverage
from quantra.ingest.parser import parse_document
from quantra.models import AgentResult
from quantra.retrieval.chunking import chunk_report
from quantra.retrieval.hybrid import HybridRetriever
from quantra.scenarios.registry import get_scenario
from quantra.scenarios.scenario import Scenario
from quantra.storage.db import Store


class ScenarioRunner:
    def __init__(self, settings: Settings | None = None, session: str = "scenario"):
        self.settings = settings or get_settings()
        self.store = Store(self.settings.db_path)
        self.session = session

    def prepare(self, scenario: Scenario) -> HybridRetriever:
        """导入场景涉及的研报并重建索引。"""
        chunks = []
        for path in scenario.reports:
            report = parse_document(path)
            rid = self.store.upsert_report(report)
            chunks.extend(chunk_report(report))
            self.store.audit("scenario:ingest", f"{path} -> {rid}", session=self.session)
        self.store.store_chunks(chunks)
        return HybridRetriever(self.store.load_chunks())

    def _run_item(self, agent: QuantraAgent, question: str) -> dict:
        result: AgentResult = agent.run(question)
        evidence = [
            c["text"]
            for c in agent.tools.search_reports(question, top_k=6)["citations"]
        ]
        coverage = citation_coverage(result.memo, evidence)
        return {
            "question": question,
            "memo": result.memo,
            "coverage": coverage,
            "model": result.model_used,
            "cost_yuan": result.cost_yuan,
            "steps": [step.action for step in result.steps],
            "citations": result.citations,
        }

    def run(self, scenario_id: str, save_dir: str | Path | None = None) -> dict:
        scenario = get_scenario(scenario_id)
        retriever = self.prepare(scenario)
        agent = QuantraAgent(self.store, retriever, self.settings, session=self.session)

        items = [self._run_item(agent, q) for q in scenario.questions]
        coverages = [item["coverage"]["coverage"] for item in items]
        total_cost = sum(item["cost_yuan"] for item in items)
        total_steps = sum(len(item["steps"]) for item in items)

        report = {
            "scenario_id": scenario.id,
            "title": scenario.title,
            "role": scenario.role,
            "business_task": scenario.business_task,
            "reports": [Path(p).name for p in scenario.reports],
            "items": items,
            "aggregate": {
                "avg_coverage": round(sum(coverages) / max(1, len(coverages)), 3),
                "total_cost_yuan": round(total_cost, 4),
                "total_steps": total_steps,
            },
            "success_criteria": scenario.success_criteria,
            "tags": scenario.tags,
        }

        for item in items:
            self.store.memory_append(
                "scenario_result",
                f"[{scenario.id}] {item['question'][:60]} -> "
                f"coverage={item['coverage']['coverage']} cost={item['cost_yuan']:.4f}",
                scenario.id,
            )

        if save_dir is not None:
            out = Path(save_dir)
            out.mkdir(parents=True, exist_ok=True)
            (out / f"{scenario.id}.json").write_text(
                json.dumps(report, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        return report

    def close(self) -> None:
        self.store.close()
