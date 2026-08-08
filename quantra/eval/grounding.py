"""引用评测。

核心问题：备忘录里有多少结论是"有据可查"的？
- citation_coverage：结论句与证据文本的重合度（bigram 覆盖率）
- hallucination_guard：列出证据不足的句子，供人工复核
"""

from __future__ import annotations

import re


SENTENCE_RE = re.compile(r"[^。！？!?；;\n]+[。！？!?；;]?")


def _bigrams(text: str) -> set[str]:
    chars = re.sub(r"\s+", "", text.lower())
    if len(chars) <= 1:
        return set(chars)
    return {chars[i : i + 2] for i in range(len(chars) - 1)}


def _overlap_ratio(sentence: str, evidence: list[str]) -> float:
    if not sentence.strip():
        return 0.0
    s_bigrams = _bigrams(sentence)
    if not s_bigrams:
        return 0.0
    best = 0.0
    for chunk in evidence:
        e_bigrams = _bigrams(chunk)
        if not e_bigrams:
            continue
        inter = len(s_bigrams & e_bigrams)
        best = max(best, inter / len(s_bigrams))
    return best


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in SENTENCE_RE.findall(text) if s.strip()]


def sentence_supported(
    sentence: str,
    evidence: list[str],
    threshold: float = 0.35,
) -> bool:
    return _overlap_ratio(sentence, evidence) >= threshold


def citation_coverage(memo: str, evidence: list[str], threshold: float = 0.35) -> dict:
    """返回总覆盖率与句子级明细。"""
    sentences = split_sentences(memo)
    if not sentences:
        return {"coverage": 0.0, "total": 0, "supported": 0, "details": []}
    details = []
    supported = 0
    for sentence in sentences:
        ok = sentence_supported(sentence, evidence, threshold)
        supported += int(ok)
        details.append(
            {
                "sentence": sentence,
                "supported": ok,
                "overlap": round(_overlap_ratio(sentence, evidence), 3),
            }
        )
    return {
        "coverage": round(supported / len(sentences), 3),
        "total": len(sentences),
        "supported": supported,
        "details": details,
    }


def hallucination_guard(memo: str, evidence: list[str], threshold: float = 0.35) -> list[str]:
    """返回证据不足的句子列表（"幻觉风险"提示）。"""
    return [
        d["sentence"]
        for d in citation_coverage(memo, evidence, threshold)["details"]
        if not d["supported"]
    ]
