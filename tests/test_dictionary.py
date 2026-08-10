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
        self.assertIsNone(normalize_metric_name("任意未知指标XYZ"))
        self.assertIsNone(normalize_metric_name(""))

    def test_bank_metrics(self):
        self.assertEqual(normalize_metric_name("净息差"), "净息差")
        self.assertEqual(normalize_metric_name("NIM"), "净息差")
        self.assertEqual(normalize_metric_name("不良贷款率"), "不良贷款率")
        self.assertEqual(normalize_metric_name("拨备覆盖率"), "拨备覆盖率")

    def test_securities_metrics(self):
        self.assertEqual(normalize_metric_name("经纪业务收入"), "经纪业务收入")
        self.assertEqual(normalize_metric_name("投行收入"), "投行业务收入")
        self.assertEqual(normalize_metric_name("两融余额"), "两融余额")

    def test_insurance_metrics(self):
        self.assertEqual(normalize_metric_name("NBV"), "新业务价值")
        self.assertEqual(normalize_metric_name("内含价值"), "内含价值")
        self.assertEqual(normalize_metric_name("综合偿付能力充足率"), "综合偿付能力充足率")

    def test_other_industry_metrics(self):
        self.assertEqual(normalize_metric_name("销售金额"), "销售金额")
        self.assertEqual(normalize_metric_name("合约销售面积"), "销售面积")
        self.assertEqual(normalize_metric_name("产能利用率"), "产能利用率")
        self.assertEqual(normalize_metric_name("新能源渗透率"), "新能源销量占比")
        self.assertEqual(normalize_metric_name("发电量"), "发电量")


if __name__ == "__main__":
    unittest.main()
