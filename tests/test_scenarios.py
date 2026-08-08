import os
import tempfile
import unittest
import uuid
from pathlib import Path


class TestScenarioRunner(unittest.TestCase):
    def setUp(self):
        self.tmp_db = Path(tempfile.gettempdir()) / f"quantra_test_{uuid.uuid4().hex}.db"
        os.environ["QUANTRA_DB_PATH"] = str(self.tmp_db)
        os.environ["QUANTRA_API_KEY"] = ""

    def tearDown(self):
        os.environ.pop("QUANTRA_DB_PATH", None)
        if self.tmp_db.exists():
            self.tmp_db.unlink()

    def test_analyst_compare_scenario(self):
        from quantra.scenarios.simulator import ScenarioRunner

        runner = ScenarioRunner(session="test")
        report = runner.run("analyst-compare")
        self.assertEqual(report["scenario_id"], "analyst-compare")
        self.assertGreaterEqual(len(report["items"]), 2)
        self.assertIn("毛利率", report["items"][0]["question"])
        self.assertGreaterEqual(report["aggregate"]["avg_coverage"], 0.0)
        self.assertGreaterEqual(len(runner.store.audit_log(limit=100)), 6)
        memories = runner.store.memory_search("analyst-compare")
        self.assertGreaterEqual(len(memories), 1)
        runner.close()

    def test_risk_audit_scenario(self):
        from quantra.scenarios.simulator import ScenarioRunner

        runner = ScenarioRunner(session="test")
        report = runner.run("risk-audit")
        self.assertEqual(report["scenario_id"], "risk-audit")
        self.assertIn("风险", report["items"][0]["question"])
        runner.close()


if __name__ == "__main__":
    unittest.main()
