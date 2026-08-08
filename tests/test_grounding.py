import unittest

from quantra.eval.grounding import citation_coverage, hallucination_guard


class TestGrounding(unittest.TestCase):
    def test_supported_sentence(self):
        evidence = ["公司2025年毛利率32.5%，较2024年提升0.7个百分点"]
        memo = "公司2025年毛利率为32.5%。这看起来不错。"
        report = citation_coverage(memo, evidence)
        self.assertGreaterEqual(report["coverage"], 0.5)

    def test_unsupported_sentence_flagged(self):
        evidence = ["原材料价格波动是主要风险"]
        memo = "公司明年利润将翻倍。"
        flagged = hallucination_guard(memo, evidence)
        self.assertGreaterEqual(len(flagged), 1)


if __name__ == "__main__":
    unittest.main()
