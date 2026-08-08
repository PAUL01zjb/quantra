import unittest

from quantra.retrieval.bm25 import BM25, tokenize


class TestBM25(unittest.TestCase):
    def test_tokenize_cjk(self):
        tokens = tokenize("毛利率与净利润的对比")
        self.assertTrue(any("毛利率" in t or "毛利率" == t for t in tokens))

    def test_top_k_ranking(self):
        docs = [
            "公司2025年毛利率32.5%，较2024年提升0.7个百分点",
            "原材料价格波动与行业竞争加剧是主要风险",
            "目标价68元，对应2026年约30倍市盈率",
        ]
        bm25 = BM25().fit(docs)
        hits = bm25.top_k("毛利率 2025", k=1)
        self.assertEqual(hits[0][0], 0)


if __name__ == "__main__":
    unittest.main()
