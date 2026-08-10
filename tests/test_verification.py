import unittest

from quantra.verification.verify import render_report, run_verification


class TestVerification(unittest.TestCase):
    def test_full_chain_passes(self):
        result = run_verification()
        failures = [c for c in result.checks if not c.ok]
        self.assertTrue(
            result.passed,
            f"验证未通过: {[f.label + ' -> ' + f.detail for f in failures]}",
        )
        self.assertGreaterEqual(len(result.checks), 30)
        report = render_report(result)
        self.assertIn("端到端验证报告", report)
        self.assertIn("通过", report)


if __name__ == "__main__":
    unittest.main()
