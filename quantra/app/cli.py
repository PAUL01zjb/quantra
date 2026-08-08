"""CLI 入口。

用法：
  python -m quantra.app.cli init-db
  python -m quantra.app.cli ingest <研报路径>...
  python -m quantra.app.cli query "<问题>"
  python -m quantra.app.cli demo-memo
  python -m quantra.app.cli audit-log --limit 20
  python -m quantra.app.cli eval
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from quantra.config import get_settings
from quantra.eval.grounding import citation_coverage, hallucination_guard
from quantra.ingest.parser import parse_document
from quantra.models import Chunk
from quantra.retrieval.chunking import chunk_report
from quantra.retrieval.hybrid import HybridRetriever
from quantra.storage.db import Store


def _open_store() -> Store:
    settings = get_settings()
    return Store(settings.db_path)


def _index(store: Store) -> HybridRetriever:
    chunks = store.load_chunks()
    if not chunks:
        raise SystemExit("知识库为空：请先运行 ingest 导入研报。")
    return HybridRetriever(chunks)


def _ingest(paths: list[str]) -> None:
    store = _open_store()
    settings = get_settings()
    all_chunks: list[Chunk] = []
    for path in paths:
        report = parse_document(path)
        rid = store.upsert_report(report)
        chunks = chunk_report(report)
        all_chunks.extend(chunks)
        store.audit("ingest", f"{path} -> {rid}", status="ok")
        print(f"[ingest] {Path(path).name}: {len(report.metrics)} 个指标, {len(chunks)} 个分块")
        for metric in report.metrics[:10]:
            print(f"    - {metric.name} {metric.value}{metric.unit} ({metric.period or '?'})")
    store.store_chunks(all_chunks)
    store.close()


def _query(question: str, verbose: bool = False) -> None:
    store = _open_store()
    settings = get_settings()
    retriever = _index(store)
    from quantra.agent.orchestrator import QuantraAgent

    agent = QuantraAgent(store, retriever, settings)
    result = agent.run(question)
    print(result.memo)
    print()
    print(f"[模型] {result.model_used} ｜ [预估成本] ¥{result.cost_yuan:.4f} ｜ [dry-run] {result.dry_run}")
    if verbose:
        print("\n[执行轨迹]")
        for step in result.steps:
            print(f"  {step.index}. {step.action}")
            if step.args:
                print(f"     参数: {step.args}")
    evidence = [c["text"] for c in agent.tools.search_reports(question)["citations"]]
    report = citation_coverage(result.memo, evidence)
    print(f"\n[引用覆盖率] {report['coverage']:.0%}（{report['supported']}/{report['total']} 句）")
    store.close()


def _demo_memo() -> None:
    sample_dir = Path(__file__).resolve().parents[2] / "data" / "samples"
    sample = sample_dir / "示例-消费龙头2025年报点评.md"
    if not sample.exists():
        raise SystemExit(f"未找到示例研报: {sample}")
    print("=== 1/3 导入示例研报 ===")
    _ingest([str(sample)])
    print("\n=== 2/3 执行 Agent 问答（dry-run） ===")
    _query("华泰证券对这家消费龙头2025年毛利率怎么看？趋势如何？", verbose=True)
    print("\n=== 3/3 审计回放 ===")
    store = _open_store()
    for row in store.audit_log(limit=8):
        print(f"  #{row['id']} {row['action']} | cost={row['cost']} | status={row['status']}")
    store.close()


def _audit_log(limit: int) -> None:
    store = _open_store()
    for row in store.audit_log(limit):
        print(f"#{row['id']} [{row['session']}] {row['action']} cost={row['cost']} {row['status']}")
        if row["detail"]:
            print(f"    {row['detail'][:150]}")
    store.close()


def _eval_run() -> None:
    store = _open_store()
    retriever = _index(store)
    questions = [
        "这家公司2025年净利润是多少？",
        "公司毛利率变化趋势如何？",
        "机构给出的目标价是多少？",
    ]
    total = {"total": 0, "supported": 0}
    for q in questions:
        evidence = [c["text"] for c in retriever.search(q, k=6)]
        # 以证据为基准构造"参考答案"，评测引用覆盖率
        memo = "；".join(s[:40] for s in evidence[:3]) + "。"
        report = citation_coverage(memo, evidence)
        total["total"] += report["total"]
        total["supported"] += report["supported"]
        print(f"[eval] {q[:20]}... 覆盖率 {report['coverage']:.0%}")
    print(f"\n[eval] 汇总覆盖率 {total['supported'] / max(1, total['total']):.0%}")
    store.close()


def _scenario_list() -> None:
    from quantra.scenarios.registry import list_scenarios

    for scenario in list_scenarios():
        print(f"[{scenario.id}] {scenario.title}")
        print(f"    角色: {scenario.role}")
        print(f"    业务任务: {scenario.business_task}")
        print()


def _scenario_run(scenario_id: str) -> None:
    from quantra.scenarios.simulator import ScenarioRunner

    runner = ScenarioRunner(session="cli")
    report = runner.run(scenario_id, save_dir="data/scenario_reports")
    print(f"=== 场景: {report['title']} ===")
    print(f"角色: {report['role']}")
    print(f"业务任务: {report['business_task']}")
    print(f"输入研报: {', '.join(report['reports'])}")
    print()
    for item in report["items"]:
        print(f"--- 问题: {item['question']}")
        print(item["memo"])
        print(f"[模型] {item['model']} ｜ [成本] ¥{item['cost_yuan']:.4f} ｜ "
              f"[引用覆盖率] {item['coverage']['coverage']:.0%} ｜ "
              f"[步骤] {len(item['steps'])}")
        print()
    agg = report["aggregate"]
    print(f"=== 汇总: 平均引用覆盖率 {agg['avg_coverage']:.0%} ｜ "
          f"总成本 ¥{agg['total_cost_yuan']:.4f} ｜ 总步骤 {agg['total_steps']}")
    print(f"验收标准: {report['success_criteria']}")
    print(f"场景报告已保存: data/scenario_reports/{report['scenario_id']}.json")
    runner.close()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="quantra", description="Agentic 研报投研工作台")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("init-db", help="初始化 SQLite 数据库")

    ingest_p = sub.add_parser("ingest", help="导入研报（支持 .md/.txt/.pdf）")
    ingest_p.add_argument("paths", nargs="+")

    query_p = sub.add_parser("query", help="向 Agent 提问")
    query_p.add_argument("question")
    query_p.add_argument("-v", "--verbose", action="store_true")

    sub.add_parser("demo-memo", help="零配置跑通全流程演示")

    audit_p = sub.add_parser("audit-log", help="查看审计日志")
    audit_p.add_argument("--limit", type=int, default=20)

    sub.add_parser("eval", help="运行引用覆盖率评测")

    scenario_p = sub.add_parser("scenario", help="业务场景模拟器")
    scenario_sub = scenario_p.add_subparsers(dest="scenario_cmd")
    scenario_sub.add_parser("list", help="列出内置场景")
    scenario_run_p = scenario_sub.add_parser("run", help="运行一个场景")
    scenario_run_p.add_argument("scenario_id")

    args = parser.parse_args(argv)
    if args.command == "init-db":
        store = _open_store()
        print(f"数据库已初始化: {get_settings().db_path}")
        store.close()
    elif args.command == "ingest":
        _ingest(args.paths)
    elif args.command == "query":
        _query(args.question, verbose=args.verbose)
    elif args.command == "demo-memo":
        _demo_memo()
    elif args.command == "audit-log":
        _audit_log(args.limit)
    elif args.command == "eval":
        _eval_run()
    elif args.command == "scenario":
        if args.scenario_cmd == "list":
            _scenario_list()
        elif args.scenario_cmd == "run":
            _scenario_run(args.scenario_id)
        else:
            print("用法: python -m quantra.app.cli scenario {list|run <id>}")
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
