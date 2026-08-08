import unittest
from pathlib import Path

from quantra.ingest.parser import parse_document


SAMPLE = Path(__file__).resolve().parents[1] / "data" / "samples" / "示例-消费龙头2025年报点评.md"


class TestParser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = parse_document(str(SAMPLE))

    def test_metadata(self):
        self.assertEqual(self.report.rating, "买入")
        self.assertEqual(self.report.target_price, "68.00")
        self.assertEqual(self.report.institution, "华泰证券")
        self.assertIn("消费龙头", self.report.title)

    def test_sections(self):
        headings = [s.heading for s in self.report.sections]
        self.assertTrue(any("投资要点" in h for h in headings))
        self.assertTrue(any("财务预测" in h for h in headings))

    def test_metrics(self):
        metrics = self.report.metrics
        names = {m.name for m in metrics}
        self.assertIn("毛利率", names)
        self.assertIn("营业收入", names)
        self.assertIn("归母净利润", names)

        gross = [m for m in metrics if m.name == "毛利率" and m.period == "2025"]
        self.assertTrue(any(m.value == "32.5" for m in gross))

        revenue_2025 = [m for m in metrics if m.name == "营业收入" and m.period == "2025"]
        self.assertTrue(any(m.value == "128.7" for m in revenue_2025))

    def test_tables(self):
        self.assertGreaterEqual(len(self.report.tables), 1)
        first = self.report.tables[0]
        self.assertGreaterEqual(len(first.rows), 2)


if __name__ == "__main__":
    unittest.main()
