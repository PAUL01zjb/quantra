import unittest

from quantra.agent.router import estimate_cost, route
from quantra.config import Settings


class TestRouter(unittest.TestCase):
    def setUp(self):
        self.settings = Settings()

    def test_route_simple_to_cheap(self):
        self.assertEqual(route("提取公司2025年营业收入", self.settings), self.settings.cheap_model)

    def test_route_complex_to_strong(self):
        self.assertEqual(route("对比华泰与中信对这家公司毛利率的分析，并评估风险", self.settings), self.settings.primary_model)

    def test_force_mode(self):
        self.assertEqual(route("简单问题", self.settings, mode="strong"), self.settings.primary_model)

    def test_estimate_cost(self):
        cost = estimate_cost("deepseek-v4-flash", 100_000, 10_000, self.settings)
        self.assertAlmostEqual(cost, 0.1 + 0.02, places=4)


if __name__ == "__main__":
    unittest.main()
