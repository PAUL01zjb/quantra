"""Plan-and-Execute 主循环。

两种模式：
- dry_run（默认，零成本）：确定性计划 + 模板备忘录，全链路可演示；
- LLM 模式：计划生成与备忘录撰写走 OpenAI 兼容接口，工具调用仍受白名单与审计约束。
"""

from __future__ import annotations

import json

from quantra.agent.audit import AuditLogger
from quantra.agent.router import estimate_cost, estimate_tokens, route
from quantra.agent.tools import TOOL_SCHEMAS, Tools
from quantra.config import Settings
from quantra.models import AgentResult, AgentStep
from quantra.providers.llm import LLMClient
from quantra.retrieval.hybrid import HybridRetriever
from quantra.storage.db import Store


METRIC_KEYWORDS = ["毛利率", "净利率", "营收", "收入", "利润", "ROE", "EPS", "PE", "PB", "现金流"]

class QuantraAgent:
    def __init__(
        self,
        store: Store,
        retriever: HybridRetriever,
        settings: Settings,
        session: str = "cli",
    ):
        self.store = store
        self.retriever = retriever
        self.settings = settings
        self.audit = AuditLogger(store, session)
        self.tools = Tools(store, retriever)
        self.llm = LLMClient(settings)

    # ---------- 计划 ----------
    def plan(self, question: str) -> list[dict]:
        if not self.settings.dry_run:
            try:
                return self._plan_with_llm(question)
            except Exception:  # noqa: BLE001
                pass
        return self._plan_default(question)

    def _plan_default(self, question: str) -> list[dict]:
        steps: list[dict] = [{"tool": "search_reports", "args": {"query": question, "top_k": 6}}]
        for keyword in METRIC_KEYWORDS:
            if keyword.lower() in question.lower():
                steps.append({"tool": "extract_metric", "args": {"metric": keyword}})
                steps.append({"tool": "calc_trend", "args": {"metric": keyword}})
                break
        return steps

    def _plan_with_llm(self, question: str) -> list[dict]:
        prompt = (
            "你是投研 Agent 的计划器。根据问题生成工具调用计划，只允许以下工具：\n"
            + json.dumps([s["name"] for s in TOOL_SCHEMAS], ensure_ascii=False)
            + "\n返回 JSON 数组，例如 [{\"tool\": \"search_reports\", \"args\": {\"query\": \"...\"}}]\n"
            f"问题：{question}"
        )
        text = self.llm.chat(
            [{"role": "user", "content": prompt}],
            model=route(question, self.settings),
        )
        start, end = text.find("["), text.rfind("]")
        return json.loads(text[start : end + 1]) if start != -1 and end != -1 else self._plan_default(question)

    # ---------- 执行 ----------
    def execute(self, plan: list[dict], question: str) -> tuple[list[AgentStep], list[dict]]:
        steps: list[AgentStep] = []
        citations: list[dict] = []
        for idx, step in enumerate(plan, start=1):
            name = step.get("tool", "")
            args = step.get("args", {})
            with self.audit.step(f"tool:{name}", json.dumps(args, ensure_ascii=False)):
                result = self.tools.run_tool(name, args)
            for citation in result.get("citations", []):
                citations.append(citation)
            steps.append(
                AgentStep(
                    index=idx,
                    action=f"调用工具 {name}",
                    tool=name,
                    args=args,
                    result_preview=json.dumps(result, ensure_ascii=False)[:200],
                )
            )
        return steps, citations

    # ---------- 备忘录 ----------
    def build_memo(self, question: str, citations: list[dict]) -> tuple[str, str, float]:
        model = route(question, self.settings)
        if not self.settings.dry_run:
            try:
                prompt = (
                    "基于以下引用证据撰写一份简洁的中文投资备忘录（300 字内），"
                    "只陈述证据支持的内容，并在每条结论后标注 [cN] 引用编号：\n\n"
                    + "\n".join(
                        f"[c{i + 1}] {c['title']} / {c['heading']} / p{c['page']}：{c['text']}"
                        for i, c in enumerate(citations)
                    )
                    + f"\n\n问题：{question}"
                )
                memo = self.llm.chat(
                    [{"role": "user", "content": prompt}],
                    model=model,
                )
                in_tokens = estimate_tokens(prompt)
                out_tokens = estimate_tokens(memo)
                cost = estimate_cost(model, in_tokens, out_tokens, self.settings)
                return memo, model, cost
            except Exception:  # noqa: BLE001
                pass
        memo = self._memo_template(question, citations)
        return memo, f"{model}(dry-run)", 0.0

    def _memo_template(self, question: str, citations: list[dict]) -> str:
        lines = [f"# 投资备忘录（dry-run 模板）", "", f"**问题**：{question}", ""]
        if not citations:
            lines.append("未检索到相关证据，结论从缺。")
            return "\n".join(lines)
        for i, c in enumerate(citations[:4], start=1):
            lines.append(
                f"- [c{i}] {c['title']} · {c['heading']}（p{c['page']}）：{c['text'][:120]}"
            )
        lines.append("")
        lines.append("> 提示：dry-run 模式不调用 LLM，接入 API Key 后由模型生成完整备忘录。")
        return "\n".join(lines)

    # ---------- 入口 ----------
    def run(self, question: str) -> AgentResult:
        plan = self.plan(question)
        steps, citations = self.execute(plan, question)
        memo, model, cost = self.build_memo(question, citations)
        self.store.memory_append("question", question, "quantra")
        self.store.memory_append("memo", memo[:500], "quantra")
        rendered_citations = [
            f"{c['title']} / {c['heading']} / p{c['page']}" for c in citations
        ]
        return AgentResult(
            memo=memo,
            steps=steps,
            citations=rendered_citations,
            model_used=model,
            cost_yuan=cost,
            dry_run=self.settings.dry_run,
        )
