import unittest

from quantra.parsing.engines.mineru_mapper import blocks_from_markdown, map_mineru_output


CONTENT_LIST_FIXTURE = [
    {
        "page_idx": 0,
        "blocks": [
            {
                "type": "title",
                "bbox": [10, 10, 500, 40],
                "lines": [{"spans": [{"content": "消费龙头2025年报点评"}]}],
            },
            {
                "type": "text",
                "bbox": [10, 50, 500, 100],
                "lines": [{"spans": [{"content": "2025年毛利率32.5%"}]}],
            },
            {
                "type": "table",
                "bbox": [10, 110, 500, 200],
                "table_body": {
                    "cells": [
                        {"row_idx": 0, "col_idx": 0, "spans": [{"content": "指标"}]},
                        {"row_idx": 0, "col_idx": 1, "spans": [{"content": "2023"}]},
                        {"row_idx": 1, "col_idx": 0, "spans": [{"content": "毛利率"}]},
                        {"row_idx": 1, "col_idx": 1, "spans": [{"content": "30.1"}]},
                    ]
                },
            },
        ],
    }
]


class TestMineruMapping(unittest.TestCase):
    def test_content_list_maps_to_contract(self):
        result = map_mineru_output(
            CONTENT_LIST_FIXTURE,
            markdown="# 消费龙头2025年报点评\n\n2025年毛利率32.5%",
            source="fake.pdf",
        )
        self.assertEqual(result.engine, "mineru")
        self.assertEqual(len(result.blocks), 3)
        self.assertEqual(result.blocks[0].block_type, "heading")
        self.assertEqual(result.blocks[1].block_type, "paragraph")
        self.assertEqual(result.blocks[2].block_type, "table")
        self.assertEqual(result.blocks[2].page, 1)
        self.assertEqual(result.blocks[2].table_rows[1][1], "30.1")
        self.assertEqual(result.stats["tables"], 1)
        self.assertIn("毛利率32.5%", result.markdown)

    def test_unknown_structure_falls_back_to_markdown(self):
        result = map_mineru_output([{"page_idx": 0, "weird": []}], markdown="## 投资要点\n\n正文内容", source="x.pdf")
        self.assertGreaterEqual(len(result.blocks), 2)
        self.assertTrue(any(b.block_type == "heading" for b in result.blocks))

    def test_blocks_from_markdown(self):
        blocks = blocks_from_markdown("## 标题\n\n| 指标 | 2023 |\n| --- | --- |\n\n正文", "x.pdf")
        types = [b.block_type for b in blocks]
        self.assertIn("heading", types)
        self.assertIn("table", types)
        self.assertIn("paragraph", types)


if __name__ == "__main__":
    unittest.main()
