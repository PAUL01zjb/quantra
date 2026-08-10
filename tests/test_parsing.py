import unittest
from pathlib import Path

from quantra.parsing import parse_document
from quantra.parsing.interfaces import ParseRequest


SAMPLE_PDF = Path(__file__).resolve().parents[1] / "data" / "samples" / "示例-消费龙头2025年报点评.pdf"
SAMPLE_MD = Path(__file__).resolve().parents[1] / "data" / "samples" / "示例-消费龙头2025年报点评.md"


class TestParsingFramework(unittest.TestCase):
    def test_pdfplumber_engine_pdf(self):
        result = parse_document(ParseRequest(source=str(SAMPLE_PDF)))
        self.assertEqual(result.engine, "pdfplumber")
        self.assertGreaterEqual(result.stats["pages"], 1)
        self.assertGreater(len(result.blocks), 0)
        self.assertIn("营业收入", result.markdown)
        self.assertGreaterEqual(result.stats["tables"], 1)

    def test_output_contract_stable(self):
        """上层只依赖输出接口：字段必须齐全。"""
        result = parse_document(ParseRequest(source=str(SAMPLE_MD)))
        self.assertTrue(hasattr(result, "source"))
        self.assertTrue(hasattr(result, "markdown"))
        self.assertTrue(hasattr(result, "blocks"))
        self.assertTrue(hasattr(result, "stats"))
        self.assertGreater(len(result.blocks), 0)

    def test_unknown_engine_raises(self):
        with self.assertRaises(KeyError):
            parse_document(ParseRequest(source=str(SAMPLE_PDF), engine="nope"))


if __name__ == "__main__":
    unittest.main()
