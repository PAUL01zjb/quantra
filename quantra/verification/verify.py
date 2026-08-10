"""端到端验证器。

对示例研报跑完整链路（parse -> extract -> archive -> company card），
与"金标准期望"逐项比对，输出验证报告（markdown）。
"""

from __future__ import annotations

import sqlite3
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

from quantra.config import get_settings
from quantra.extraction.extractor import extract
from quantra.parsing import parse_document
from quantra.parsing.interfaces import ParseRequest
from quantra.storage.archive import ArchiveStore


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SAMPLES = PROJECT_ROOT / "data" / "samples"


@dataclass
class CheckResult:
    check_id: str
    label: str
    ok: bool
    detail: str = ""


@dataclass
class VerificationResult:
    passed: bool
    checks: list[CheckResult] = field(default_factory=list)
    db_stats: dict = field(default_factory=dict)
    company_cards: dict = field(default_factory=dict)
    generated_at: str = ""


GOLDEN: dict[str, dict] = {
    "示例-消费龙头2025年报点评.md": {
        "company": "消费龙头",
        "broker": "华泰证券",
        "rating": "买入",
        "target_price": "68.00",
        "metrics": {
            "毛利率": {"2025": "32.5"},
            "营业收入": {"2025": "128.7"},
            "归母净利润": {"2025": "21.3"},
            "ROE": {"2025": "18.2"},
        },
        "min_risks": 1,
    },
    "示例-消费龙头2025年报点评.pdf": {
        "company": "消费龙头",
        "broker": "华泰证券",
        "rating": "买入",
        "target_price": "68.00",
        "metrics": {
            "毛利率": {"2025": "32.5"},
            "营业收入": {"2025": "128.7"},
            "归母净利润": {"2025": "21.3"},
        },
        "min_risks": 1,
    },
    "示例-同业公司2025年报点评.md": {
        "company": "同业公司",
        "broker": "中信证券",
        "rating": "增持",
        "target_price": "52.00",
        "metrics": {
            "毛利率": {"2025": "28.9"},
            "营业收入": {"2025": "86.4"},
            "归母净利润": {"2025": "10.6"},
        },
        "min_risks": 1,
    },
}


def _metric_value(result, metric_name: str, period: str) -> str | None:
    for m in result.metrics:
        if m.metric_name == metric_name and m.period == period:
            return m.value
    return None


class VerificationRunner:
    def __init__(self, db_path: str | Path | None = None):
        self.db_path = db_path or Path(tempfile.mkdtemp(prefix="quantra_verify_")) / "verify.db"
        self.store = ArchiveStore(self.db_path)
        self.checks: list[CheckResult] = []
        self.cards: dict[str, dict] = {}

    def run(self) -> VerificationResult:
        files = [SAMPLES / name for name in GOLDEN]
        for path in files:
            name = path.name
            golden = GOLDEN[name]
            self._verify_file(path, name, golden)

        self._verify_database()

        for company_id in self.cards:
            self.cards[company_id] = self.store.query_company_card(company_id)

        db_stats = self._db_stats()
        passed = all(c.ok for c in self.checks)
        return VerificationResult(
            passed=passed,
            checks=self.checks,
            db_stats=db_stats,
            company_cards=self.cards,
            generated_at=time.strftime("%Y-%m-%d %H:%M:%S"),
        )

    # ---------- 单文件链路验证 ----------
    def _verify_file(self, path: Path, name: str, golden: dict) -> None:
        try:
            parse_result = parse_document(ParseRequest(source=str(path), engine="auto"))
        except Exception as exc:  # noqa: BLE001
            self.checks.append(CheckResult(f"{name}:parse", f"{name} 解析", False, str(exc)))
            return

        self.checks.append(
            CheckResult(
                f"{name}:parse",
                f"{name} 输入识别（blocks/markdown）",
                len(parse_result.blocks) > 0 and len(parse_result.markdown) > 0,
                f"blocks={len(parse_result.blocks)}, markdown={len(parse_result.markdown)} 字符",
            )
        )

        try:
            result = extract(parse_result)
        except Exception as exc:  # noqa: BLE001
            self.checks.append(CheckResult(f"{name}:extract", f"{name} 抽取", False, str(exc)))
            return

        self.checks.append(
            CheckResult(
                f"{name}:company",
                f"{name} 公司识别",
                result.company.name == golden["company"],
                f"期望 {golden['company']}，实际 {result.company.name}",
            )
        )
        self.checks.append(
            CheckResult(
                f"{name}:broker",
                f"{name} 机构识别",
                result.report_meta.broker == golden["broker"],
                f"期望 {golden['broker']}，实际 {result.report_meta.broker}",
            )
        )
        self.checks.append(
            CheckResult(
                f"{name}:rating",
                f"{name} 评级识别",
                result.report_meta.rating == golden["rating"],
                f"期望 {golden['rating']}，实际 {result.report_meta.rating}",
            )
        )
        self.checks.append(
            CheckResult(
                f"{name}:target",
                f"{name} 目标价识别",
                result.report_meta.target_price == golden["target_price"],
                f"期望 {golden['target_price']}，实际 {result.report_meta.target_price}",
            )
        )
        for metric_name, periods in golden["metrics"].items():
            for period, expected in periods.items():
                actual = _metric_value(result, metric_name, period)
                self.checks.append(
                    CheckResult(
                        f"{name}:{metric_name}:{period}",
                        f"{name} {metric_name} {period}",
                        actual == expected,
                        f"期望 {expected}，实际 {actual or '未抽取'}",
                    )
                )
        self.checks.append(
            CheckResult(
                f"{name}:risks",
                f"{name} 风险提示抽取",
                len(result.risks) >= golden["min_risks"],
                f"抽取 {len(result.risks)} 条风险",
            )
        )

        ids = self.store.archive(result, parse_result.blocks)
        self.cards[ids["company_id"]] = ids

    # ---------- 数据库验证 ----------
    def _verify_database(self) -> None:
        conn = self.store.conn

        def count(table: str) -> int:
            return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

        checks = [
            ("db:company", "company 表有 2 家公司", count("company") == 2, f"实际 {count('company')}"),
            ("db:report", "report 表有 3 份研报", count("report") == 3, f"实际 {count('report')}"),
            ("db:metric_fact", "metric_fact 指标事实 ≥ 25", count("metric_fact") >= 25, f"实际 {count('metric_fact')}"),
            ("db:document_chunk", "document_chunk 原文块 ≥ 3", count("document_chunk") >= 3, f"实际 {count('document_chunk')}"),
            ("db:risk", "risk 风险 ≥ 4", count("risk") >= 4, f"实际 {count('risk')}"),
            ("db:audit", "extraction_audit 审计 ≥ 3", count("extraction_audit") >= 3, f"实际 {count('extraction_audit')}"),
        ]
        for check_id, label, ok, detail in checks:
            self.checks.append(CheckResult(check_id, label, ok, detail))

        card = self.store.query_company_card(list(self.cards)[0])
        has_gross = any(
            r["period"] == "2025" and r["value"] == "32.5"
            for r in card.get("metrics", {}).get("毛利率", [])
        )
        self.checks.append(
            CheckResult(
                "db:card",
                "公司卡片聚合（毛利率 2025=32.5 可查）",
                has_gross,
                f"毛利率行数: {len(card.get('metrics', {}).get('毛利率', []))}",
            )
        )

    def _db_stats(self) -> dict:
        conn = self.store.conn
        return {
            table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ["company", "report", "metric_fact", "document_chunk", "risk", "extraction_audit"]
        }

    def close(self) -> None:
        self.store.close()


def render_report(result: VerificationResult) -> str:
    lines = [
        "# Quantra 端到端验证报告",
        "",
        f"- 生成时间：{result.generated_at}",
        f"- 结论：**{'通过' if result.passed else '未通过'}**（{sum(1 for c in result.checks if c.ok)}/{len(result.checks)} 项检查通过）",
        "",
        "## 检查明细",
        "",
        "| 检查项 | 结果 | 详情 |",
        "|---|---|---|",
    ]
    for check in result.checks:
        lines.append(f"| {check.label} | {'✅' if check.ok else '❌'} | {check.detail} |")

    lines += ["", "## 数据库沉淀", ""]
    for table, count in result.db_stats.items():
        lines.append(f"- `{table}`: {count} 行")

    lines += ["", "## 公司卡片（聚合视图）", ""]
    for company_id, card in result.company_cards.items():
        if "company" not in card:
            continue
        lines.append(f"### {card['company']['name']}（{card['company'].get('ticker') or '无 ticker'}）")
        lines.append("")
        for metric_name, rows in card["metrics"].items():
            values = ", ".join(f"{r['period']}={r['value']}{r['unit']}" for r in rows[:8])
            lines.append(f"- {metric_name}: {values}")
        risks = "、".join(r["risk_text"] for r in card.get("risks", [])[:5])
        if risks:
            lines.append(f"- 风险: {risks}")
        lines.append("")
    return "\n".join(lines)


def run_verification(db_path: str | Path | None = None) -> VerificationResult:
    runner = VerificationRunner(db_path)
    try:
        return runner.run()
    finally:
        runner.close()
