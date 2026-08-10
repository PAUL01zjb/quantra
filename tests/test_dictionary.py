import unittest

from quantra.extraction.dictionary import normalize_metric_name


class TestMetricDictionary(unittest.TestCase):
    def test_canonical_names_pass_through(self):
        self.assertEqual(normalize_metric_name("毛利率"), "毛利率")
        self.assertEqual(normalize_metric_name("ROE"), "ROE")

    def test_aliases_normalize(self):
        self.assertEqual(normalize_metric_name("营收"), "营业收入")
        self.assertEqual(normalize_metric_name("营业总收入"), "营业收入")
        self.assertEqual(normalize_metric_name("归母净利"), "归母净利润")
        self.assertEqual(normalize_metric_name("每股收益"), "EPS")
        self.assertEqual(normalize_metric_name("市盈率"), "PE")
        self.assertEqual(normalize_metric_name("市净率"), "PB")

    def test_unknown_returns_none(self):
        self.assertIsNone(normalize_metric_name("自由现金流"))
        self.assertIsNone(normalize_metric_name(""))


if __name__ == "__main__":
    unittest.main()
