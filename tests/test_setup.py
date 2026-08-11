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
        for key in (
            "QUANTRA_LLM_BASE_URL",
            "QUANTRA_API_KEY",
            "QUANTRA_DB_PATH",
            "QUANTRA_EMBEDDING_PROVIDER",
            "QUANTRA_VECTOR_STORE",
        ):
            os.environ.pop(key, None)

    def test_run_setup_writes_env_and_db(self):
        db_path = str(self.tmp / "setup.db")
        result = run_setup(
            {
                "api_base": "https://api.deepseek.com/v1",
                "api_key": "sk-test-secret-123",
                "db_path": db_path,
                "embedding_provider": "auto",
                "vector_store": "memory",
                "parser_engine": "auto",
                "observability": "none",
            },
            ingest_samples=False,
            run_verify=False,
            root=self.tmp,
        )
        env_path = self.tmp / ".env"
        self.assertTrue(env_path.exists())
        content = env_path.read_text(encoding="utf-8")
        self.assertIn("QUANTRA_API_KEY=sk-test-secret-123", content)
        self.assertIn("QUANTRA_VECTOR_STORE=memory", content)
        self.assertEqual(oct(stat.S_IMODE(env_path.stat().st_mode)), "0o600")
        self.assertTrue(Path(result["db"]).exists())
        self.assertEqual(result["providers"]["embedding"], "auto")


if __name__ == "__main__":
    unittest.main()
