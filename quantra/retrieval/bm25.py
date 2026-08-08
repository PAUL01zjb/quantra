"""轻量 BM25（Robertson 变体），无第三方依赖。

分词策略：拉丁词原样；中文按连续 CJK 片段生成 unigram + bigram，
未装 jieba 时也能工作（装了 jieba 自动优先）。
"""

from __future__ import annotations

import math
import re
from collections import Counter


CJK_RE = re.compile(r"[a-z0-9]+|[\u4e00-\u9fff]+", re.I)


def tokenize(text: str) -> list[str]:
    text = text.lower()
    try:
        import jieba

        words = [w for w in jieba.cut(text) if re.search(r"[a-z0-9\u4e00-\u9fff]", w)]
        return words
    except ImportError:
        tokens: list[str] = []
        for m in CJK_RE.finditer(text):
            tok = m.group(0)
            if tok.isalpha() and all("\u4e00" <= ch <= "\u9fff" for ch in tok):
                tokens.append(tok)
                if len(tok) > 1:
                    tokens.extend(tok[i : i + 2] for i in range(len(tok) - 1))
            else:
                tokens.append(tok)
        return tokens


class BM25:
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.doc_freqs: list[Counter] = []
        self.doc_len: list[int] = []
        self.avgdl = 0.0
        self.n_docs = 0
        self.df: Counter[str] = Counter()

    def fit(self, docs: list[str]) -> "BM25":
        self.doc_freqs = [Counter(tokenize(d)) for d in docs]
        self.doc_len = [sum(f.values()) for f in self.doc_freqs]
        self.n_docs = len(docs)
        self.avgdl = sum(self.doc_len) / max(1, self.n_docs)
        for freq in self.doc_freqs:
            for term in freq:
                self.df[term] += 1
        return self

    def _score(self, query_terms: list[str], idx: int) -> float:
        freq = self.doc_freqs[idx]
        dl = self.doc_len[idx]
        score = 0.0
        for qt in query_terms:
            tf = freq.get(qt, 0)
            if tf == 0:
                continue
            idf_denom = self.n_docs - self.df.get(qt, 0) + 0.5
            idf = math.log((self.n_docs - self.df.get(qt, 0) + 0.5) / idf_denom + 1)
            score += idf * (tf * (self.k1 + 1)) / (tf + self.k1 * (1 - self.b + self.b * dl / self.avgdl))
        return score

    def top_k(self, query: str, k: int = 8, filter_ids: set[str] | None = None) -> list[tuple[int, float]]:
        terms = tokenize(query)
        if not terms:
            return []
        scored = [
            (idx, self._score(terms, idx))
            for idx in range(self.n_docs)
            if filter_ids is None or idx in filter_ids
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:k]
