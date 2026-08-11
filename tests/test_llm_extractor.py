import unittest

from quantra.extraction.llm_extractor import LLMExtractor
from quantra.parsing.interfaces import ParseResult


FAKE_JSON = """{
  "company": {"name": "消费龙头", "ticker": ""},
  "report_meta": {"title": "消费龙头2025年报点评", "broker": "华泰证券", "analyst": "张三",
                  "report_date": "2026-03-18", "rating": "买入", "target_price": "68.00"},
  "metrics": [
    {"metric_name": "毛利率", "value": "32.5", "unit": "%", "period": "2025", "source_page": 1, "source_section": "投资要点"},
    {"metric_name": "归母净利润", "value": "21.3", "unit": "亿元", "period": "2025", "source_page": 1, "source_section": "投资要点"},
    {"metric_name": "不存在指标XYZ", "value": "1", "unit": "", "period": "", "source_page": 0, "source_section": ""}
  ],
  "risks": [{"risk_text": "原材料价格波动", "category": "风险"}]
}"""


class FakeClient:
    def __init__(self, settings):
        self.settings = settings

    def chat(self, messages, model, temperature=0.3):
        return FAKE_JSON


class FakeSettings:
    api_key = "test-key"
    primary_model = "deepseek-v4-pro"


class TestLLMExtractor(unittest.TestCase):
    def test_llm_output_maps_to_contract_with_dictionary_validation(self):
        settings = FakeSettings()
        extractor = LLMExtractor(settings)
        extractor.client = FakeClient(settings)  # mock 掉真实 HTTP
        parse_result = ParseResult(source="fake.md", markdown="mock", blocks=[])
        result = extractor.extract(parse_result)

        self.assertEqual(result.company.name, "消费龙头")
        self.assertEqual(result.report_meta.broker, "华泰证券")
        self.assertEqual(result.report_meta.rating, "买入")
        names = {m.metric_name for m in result.metrics}
        self.assertIn("毛利率", names)
        self.assertIn("归母净利润", names)
        self.assertNotIn("不存在指标XYZ", names)  # 词典校验拦截
        self.assertTrue(all(m.method == "llm" for m in result.metrics))
        self.assertGreaterEqual(len(result.risks), 1)

    def test_no_api_key_raises(self):
        settings = FakeSettings()
        settings.api_key = ""
        extractor = LLMExtractor(settings)
        parse_result = ParseResult(source="fake.md", markdown="mock", blocks=[])
        with self.assertRaises(RuntimeError):
            extractor.extract(parse_result)


if __name__ == "__main__":
    unittest.main()
