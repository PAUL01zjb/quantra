"""Quantra command-line interface."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from quantra.config import get_settings
from quantra.eval.grounding import citation_coverage
from quantra.ingest.parser import parse_document
from quantra.models import Chunk
from quantra.retrieval.chunking import chunk_report
from quantra.retrieval.hybrid import HybridRetriever
from quantra.storage.db import Store


def _open_store() -> Store:
    return Store(get_settings().db_path)


def _index(store: Store) -> HybridRetriever:
    chunks = store.load_chunks()
    if not chunks:
        raise SystemExit("Knowledge base is empty: run ingest first.")
    return HybridRetriever(chunks)


def _ingest(paths: list[str]) -> None:
    store = _open_store()
    all_chunks: list[Chunk] = []
    for path in paths:
        report = parse_document(path)
        rid = store.upsert_report(report)
        chunks = chunk_report(report)
        all_chunks.extend(chunks)
        store.audit("ingest", f"{path} -> {rid}", status="ok")
        print(f"[ingest] {Path(path).name}: {len(report.metrics)} metrics, {len(chunks)} chunks")
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
    print(
        f"[model] {result.model_used} | [est. cost] ¥{result.cost_yuan:.4f} "
        f"| [dry-run] {result.dry_run}"
    )
    if verbose:
        print("\n[execution trace]")
        for step in result.steps:
            print(f"  {step.index}. {step.action}")
            if step.args:
                print(f"     args: {step.args}")
    evidence = [c["text"] for c in agent.tools.search_reports(question)["citations"]]
    report = citation_coverage(result.memo, evidence)
    print(f"\n[citation coverage] {report['coverage']:.0%} ({report['supported']}/{report['total']} sentences)")
    store.close()


def _demo_memo() -> None:
    sample_dir = Path(__file__).resolve().parents[2] / "data" / "samples"
    sample = sample_dir / "示例-消费龙头2025年报点评.md"
    if not sample.exists():
        raise SystemExit(f"Sample report not found: {sample}")
    print("=== 1/3 Ingest sample report ===")
    _ingest([str(sample)])
    print("\n=== 2/3 Agent Q&A (deterministic mode) ===")
    _query("华泰证券对这家消费龙头2025年毛利率怎么看？趋势如何？", verbose=True)
    print("\n=== 3/3 Audit replay ===")
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
        memo = "；".join(s[:40] for s in evidence[:3]) + "。"
        report = citation_coverage(memo, evidence)
        total["total"] += report["total"]
        total["supported"] += report["supported"]
        print(f"[eval] {q[:20]}... coverage {report['coverage']:.0%}")
    print(f"\n[eval] overall coverage {total['supported'] / max(1, total['total']):.0%}")
    store.close()


def _scenario_list() -> None:
    from quantra.scenarios.registry import list_scenarios

    for scenario in list_scenarios():
        print(f"[{scenario.id}] {scenario.title}")
        print(f"    role: {scenario.role}")
        print(f"    task: {scenario.business_task}")
        print()


def _scenario_run(scenario_id: str) -> None:
    from quantra.scenarios.simulator import ScenarioRunner

    runner = ScenarioRunner(session="cli")
    report = runner.run(scenario_id, save_dir="data/scenario_reports")
    print(f"=== Scenario: {report['title']} ===")
    print(f"role: {report['role']}")
    print(f"task: {report['business_task']}")
    print(f"reports: {', '.join(report['reports'])}")
    print()
    for item in report["items"]:
        print(f"--- Q: {item['question']}")
        print(item["memo"])
        print(
            f"[model] {item['model']} | [cost] ¥{item['cost_yuan']:.4f} | "
            f"[coverage] {item['coverage']['coverage']:.0%} | [steps] {len(item['steps'])}"
        )
        print()
    agg = report["aggregate"]
    print(
        f"=== Summary: avg coverage {agg['avg_coverage']:.0%} | "
        f"total cost ¥{agg['total_cost_yuan']:.4f} | total steps {agg['total_steps']}"
    )
    print(f"success criteria: {report['success_criteria']}")
    print(f"report saved: data/scenario_reports/{report['scenario_id']}.json")
    runner.close()


def _parse_file(path: str, engine: str, out: str) -> None:
    from quantra.parsing import parse_document
    from quantra.parsing.interfaces import ParseRequest

    request = ParseRequest(source=path, engine=engine)
    result = parse_document(request)
    print(f"=== Parse result (engine: {result.engine}) ===")
    print(f"source: {result.source}")
    print(f"stats: {result.stats}")
    print()
    for block in result.blocks[:15]:
        prefix = {"heading": "##", "table": "[table]", "paragraph": ""}.get(block.block_type, "")
        preview = block.text[:100].replace("\n", " ")
        print(f"  p{block.page} {prefix} {preview}")
    if len(result.blocks) > 15:
        print(f"  ... {len(result.blocks)} blocks total")
    if out:
        target = Path(out)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(result.markdown, encoding="utf-8")
        print(f"\nMarkdown saved: {target}")


def _extract_file(path: str, engine: str) -> None:
    from quantra.extraction.extractor import extract
    from quantra.parsing import parse_document
    from quantra.parsing.interfaces import ParseRequest
    from quantra.storage.archive import ArchiveStore

    parse_result = parse_document(ParseRequest(source=path, engine=engine))
    result = extract(parse_result)
    store = ArchiveStore(get_settings().db_path)
    ids = store.archive(result, parse_result.blocks)
    card = store.query_company_card(ids["company_id"])

    print(f"=== Extraction & archive (engine: {result.engine}) ===")
    print(f"company: {card['company']['name']} | ticker: {card['company'].get('ticker') or 'not detected'}")
    print(
        f"report: {result.report_meta.title} | {result.report_meta.broker} "
        f"| {result.report_meta.report_date}"
    )
    print(f"rating: {result.report_meta.rating or '-'} | target: {result.report_meta.target_price or '-'} CNY")
    print()
    for metric_name, rows in card["metrics"].items():
        values = ", ".join(f"{r['period']}={r['value']}{r['unit']}" for r in rows)
        print(f"  {metric_name}: {values}")
    if card["risks"]:
        print("\nrisks:")
        for risk in card["risks"]:
            print(f"  - [{risk['category']}] {risk['risk_text']}")
    print(
        f"\n[archived] report={ids['report_id'][:8]} metrics={ids['metrics']} "
        f"chunks={ids['chunks']} risks={ids['risks']}"
    )
    store.close()


def _verify(out: str) -> None:
    from quantra.verification.verify import render_report, run_verification

    result = run_verification()
    report = render_report(result)
    if out:
        target = Path(out)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(report, encoding="utf-8")
        print(f"Verification report saved: {target}")
    print(report[:2000])
    print("\n[result]", "PASS ✅" if result.passed else "FAIL ❌")


def _ask(question: str) -> None:
    from quantra.query.pipeline import ask
    from quantra.storage.archive import ArchiveStore

    store = ArchiveStore(get_settings().db_path)
    chunks = store.load_chunks()
    if not chunks:
        store.close()
        raise SystemExit("Knowledge base is empty: run ingest-doc first.")
    retriever = HybridRetriever(chunks)
    answer = ask(question, store, retriever)
    print(answer.answer)
    print()
    if answer.memories:
        print("[memory hints]")
        for memory in answer.memories[:3]:
            tag = {"fact": "confirmed fact", "conclusion": "history", "correction": "correction"}.get(
                memory["kind"], memory["kind"]
            )
            print(f"  - [{tag}] {memory['content'][:100]}")
        print()
    print(f"[route] intent={answer.intent} | channel={answer.channel} | fallback={answer.fallback}")
    if answer.citations:
        print("[citations]")
        for citation in answer.citations[:5]:
            print(f"  - {citation}")
    store.close()


def _ingest_doc(path: str, engine: str) -> None:
    from quantra.ingestion.pipeline import IngestionPipeline

    pipeline = IngestionPipeline()
    result = pipeline.ingest(path, engine=engine)
    print(f"=== Ingestion complete ({result['method']}) ===")
    print(f"raw doc: {result['doc_id']}")
    print(f"tags: {result['tags']}")
    print(
        f"archived: report={result['report_id'][:8]} metrics={result['metrics']} "
        f"chunks={result['chunks']} risks={result['risks']}"
    )
    pipeline.close()


def _confirm(question: str) -> None:
    from quantra.memory.extractor import confirm_facts
    from quantra.query.pipeline import ask
    from quantra.storage.archive import ArchiveStore

    store = ArchiveStore(get_settings().db_path)
    chunks = store.load_chunks()
    retriever = HybridRetriever(chunks) if chunks else None
    if retriever is None:
        store.close()
        raise SystemExit("Knowledge base is empty: run ingest-doc first.")
    answer = ask(question, store, retriever)
    memory_ids = confirm_facts(question, answer, store)
    print(answer.answer)
    print()
    print(f"[confirm] {len(memory_ids)} memories written (fact + conclusion)")
    store.close()


def _correct(question: str, correction: str) -> None:
    from quantra.memory.extractor import correct_answer
    from quantra.storage.archive import ArchiveStore

    store = ArchiveStore(get_settings().db_path)
    memory_id = correct_answer(question, correction, store)
    print(f"[correct] memory written: {memory_id}")
    print(f"  question: {question}")
    print(f"  correction: {correction}")
    store.close()


def _memories(keyword: str) -> None:
    from quantra.storage.archive import ArchiveStore

    store = ArchiveStore(get_settings().db_path)
    rows = store.memory_search(keyword) if keyword else store.list_memories(limit=30)
    if not rows:
        print("No memories yet. Use confirm/correct to create them.")
    kind_label = {"fact": "fact", "conclusion": "conclusion", "correction": "correction", "preference": "preference"}
    for row in rows:
        label = kind_label.get(row["kind"], row["kind"])
        print(f"[{label}][{row['confidence']:.2f}] {row['content'][:120]}")
    store.close()


def _setup() -> None:
    import getpass

    from quantra.setup_wizard import run_setup

    print("⚙️  Quantra configuration wizard")
    print("    Providers: LLM / Embeddings / Vector Store / Parser / Observability")
    print("    Secrets are written only to the local .env (mode 0600).")
    print("──────────────────────────────────────────────────────────")
    config: dict = {}
    print("\n[LLM provider]")
    config["api_base"] = input("Base URL (default https://api.deepseek.com/v1): ").strip() or "https://api.deepseek.com/v1"
    config["api_key"] = getpass.getpass("API key (optional; empty = deterministic mode): ").strip()
    config["primary_model"] = input("Primary model (default deepseek-v4-pro): ").strip() or "deepseek-v4-pro"
    config["cheap_model"] = input("Cheap model (default deepseek-v4-flash): ").strip() or "deepseek-v4-flash"

    print("\n[Embeddings]")
    config["embedding_provider"] = input("Provider auto/openai/bge-m3/none (default auto): ").strip() or "auto"
    if config["embedding_provider"] in ("openai", "api"):
        config["embedding_api_base"] = input("Embedding API base (default: same as LLM): ").strip()
        config["embedding_api_key"] = getpass.getpass("Embedding API key: ").strip()

    print("\n[Vector store]")
    config["vector_store"] = input("Store memory/qdrant (default memory): ").strip() or "memory"
    if config["vector_store"] == "qdrant":
        config["vector_store_url"] = input("Qdrant URL (e.g. http://localhost:6333): ").strip()
        config["vector_store_collection"] = input("Collection name (default quantra): ").strip() or "quantra"

    print("\n[Parser / Observability]")
    config["parser_engine"] = input("Parser auto/mineru/docling (default auto): ").strip() or "auto"
    config["observability"] = input("Observability none/langfuse (default none): ").strip() or "none"
    if config["observability"] == "langfuse":
        config["langfuse_public_key"] = getpass.getpass("Langfuse public key: ").strip()
        config["langfuse_secret_key"] = getpass.getpass("Langfuse secret key: ").strip()

    config["db_path"] = input("Database path (default data/quantra.db): ").strip() or "data/quantra.db"

    results = run_setup(config, ingest_samples=True, run_verify=True)
    print("──────────────────────────────────────────────────────────")
    print("✅ Configuration complete")
    print(f"   .env: {results['env']} (mode 0600)")
    print(f"   database: {results['db']}")
    print(f"   providers: {results['providers']}")
    if results.get("samples"):
        print(f"   samples ingested: {len(results['samples'])}")
    if results.get("verify_passed"):
        print(f"   end-to-end verification: PASS ({results['verify_checks']})")
    print("Next: quantra ui  |  quantra ask \"your question\"")


def _ui(port: int, host: str) -> None:
    from quantra.app.server import serve

    serve(host=host, port=port)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="quantra", description="Agentic research intelligence platform")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("init-db", help="Initialize the SQLite database")
    ingest_p = sub.add_parser("ingest", help="Ingest reports (.md/.txt/.pdf)")
    ingest_p.add_argument("paths", nargs="+")
    query_p = sub.add_parser("query", help="Ask the agent a question")
    query_p.add_argument("question")
    query_p.add_argument("-v", "--verbose", action="store_true")
    sub.add_parser("demo-memo", help="Run the full pipeline demo")
    audit_p = sub.add_parser("audit-log", help="Show the audit trail")
    audit_p.add_argument("--limit", type=int, default=20)
    sub.add_parser("eval", help="Run citation-coverage evaluation")

    scenario_p = sub.add_parser("scenario", help="Business scenario simulator")
    scenario_sub = scenario_p.add_subparsers(dest="scenario_cmd")
    scenario_sub.add_parser("list", help="List scenarios")
    scenario_run_p = scenario_sub.add_parser("run", help="Run a scenario")
    scenario_run_p.add_argument("scenario_id")

    parse_p = sub.add_parser("parse", help="Parse a document (ParseRequest -> engine -> ParseResult)")
    parse_p.add_argument("path")
    parse_p.add_argument("--engine", default="auto", help="auto/pdfplumber/mineru/docling")
    parse_p.add_argument("--out", default="", help="Save markdown to a path")

    extract_p = sub.add_parser("extract", help="Extract and archive (ParseResult -> ExtractionResult -> DB)")
    extract_p.add_argument("path")
    extract_p.add_argument("--engine", default="auto")

    verify_p = sub.add_parser("verify", help="End-to-end verification")
    verify_p.add_argument("--out", default="", help="Report output path")

    ask_p = sub.add_parser("ask", help="Routed Q&A (SQL-first, doc fallback)")
    ask_p.add_argument("question")

    ingest_doc_p = sub.add_parser("ingest-doc", help="Ingestion pipeline: parse -> extract -> tag -> dual-write")
    ingest_doc_p.add_argument("path")
    ingest_doc_p.add_argument("--engine", default="auto")

    confirm_p = sub.add_parser("confirm", help="Confirm an answer -> durable memory")
    confirm_p.add_argument("question")
    correct_p = sub.add_parser("correct", help="Record a trader correction")
    correct_p.add_argument("question")
    correct_p.add_argument("correction")
    memories_p = sub.add_parser("memories", help="List/search cross-conversation memory")
    memories_p.add_argument("keyword", nargs="?", default="")

    sub.add_parser("setup", help="Configuration wizard (providers -> .env)")
    ui_p = sub.add_parser("ui", help="Launch the web console")
    ui_p.add_argument("--host", default="127.0.0.1")
    ui_p.add_argument("--port", type=int, default=8000)

    args = parser.parse_args(argv)
    if args.command == "init-db":
        store = _open_store()
        print(f"Database initialized: {get_settings().db_path}")
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
            print("Usage: quantra scenario {list|run <id>}")
            sys.exit(1)
    elif args.command == "parse":
        _parse_file(args.path, args.engine, args.out)
    elif args.command == "extract":
        _extract_file(args.path, args.engine)
    elif args.command == "verify":
        _verify(args.out)
    elif args.command == "ask":
        _ask(args.question)
    elif args.command == "ingest-doc":
        _ingest_doc(args.path, args.engine)
    elif args.command == "confirm":
        _confirm(args.question)
    elif args.command == "correct":
        _correct(args.question, args.correction)
    elif args.command == "memories":
        _memories(args.keyword)
    elif args.command == "setup":
        _setup()
    elif args.command == "ui":
        _ui(args.port, args.host)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
