import unittest
from pathlib import Path

from quantra.extraction.extractor import extract
from quantra.parsing import parse_document
from quantra.parsing.interfaces import ParseRequest


SAMPLE_MD = Path(__file__).resolve().parents[1] / "data" / "samples" / "示例-消费龙头2025年报点评.md"
SAMPLE_PDF = Path(__file__).resolve().parents[1] / "data" / "samples" / "示例-消费龙头2025年报点评.pdf"


class TestExtractor(unittest.TestCase):
    def test_extract_from_markdown(self):
        result = extract(parse_document(ParseRequest(source=str(SAMPLE_MD))))
        names = {m.metric_name for m in result.metrics}
        self.assertIn("毛利率", names)
        self.assertIn("营业收入", names)
        self.assertIn("归母净利润", names)
        self.assertIn("ROE", names)
        self.assertIn("EPS", names)

        gross = [m for m in result.metrics if m.metric_name == "毛利率" and m.period == "2025"]
        self.assertTrue(any(m.value == "32.5" for m in gross))

        self.assertEqual(result.report_meta.rating, "买入")
        self.assertEqual(result.report_meta.target_price, "68.00")
        self.assertEqual(result.report_meta.broker, "华泰证券")
        self.assertGreaterEqual(len(result.risks), 1)

    def test_extract_from_pdf(self):
        result = extract(parse_document(ParseRequest(source=str(SAMPLE_PDF))))
        names = {m.metric_name for m in result.metrics}
        self.assertIn("毛利率", names)
        self.assertIn("营业收入", names)

    def test_company_name_from_title(self):
        result = extract(parse_document(ParseRequest(source=str(SAMPLE_MD))))
        self.assertEqual(result.company.name, "消费龙头")


if __name__ == "__main__":
    unittest.main()
