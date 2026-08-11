import os
import stat
import tempfile
import unittest
from pathlib import Path

from quantra.setup_wizard import run_setup


class TestSetupWizard(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="quantra_setup_"))

    def tearDown(self):
        for key in ("QUANTRA_LLM_BASE_URL", "QUANTRA_API_KEY", "QUANTRA_DB_PATH"):
            os.environ.pop(key, None)

    def test_run_setup_writes_env_and_db(self):
        db_path = str(self.tmp / "setup.db")
        result = run_setup(
            "https://api.deepseek.com/v1",
            "sk-test-secret-123",
            db_path,
            ingest_samples=False,
            run_verify=False,
            root=self.tmp,
        )
        env_path = self.tmp / ".env"
        self.assertTrue(env_path.exists())
        content = env_path.read_text(encoding="utf-8")
        self.assertIn("QUANTRA_API_KEY=sk-test-secret-123", content)
        self.assertEqual(oct(stat.S_IMODE(env_path.stat().st_mode)), "0o600")
        self.assertTrue(Path(result["db"]).exists())


if __name__ == "__main__":
    unittest.main()
