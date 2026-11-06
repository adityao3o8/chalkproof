"""N-gram overlap plagiarism guard vs source texts."""

from __future__ import annotations

import re
from typing import Optional


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def find_ngram_overlaps(
    passage: str,
    source_text: str,
    n: int = 8,
) -> list[str]:
    """
    Find sequences of >= n consecutive words shared by passage and source.
    Returns the matching phrases.
    """
    if not passage or not source_text:
        return []

    p_tokens = tokenize(passage)
    s_tokens = tokenize(source_text)
    if len(p_tokens) < n or len(s_tokens) < n:
        return []

    source_ngrams = set()
    for i in range(len(s_tokens) - n + 1):
        source_ngrams.add(tuple(s_tokens[i : i + n]))

    matches: list[str] = []
    i = 0
    while i <= len(p_tokens) - n:
        gram = tuple(p_tokens[i : i + n])
        if gram in source_ngrams:
            # Extend match as far as it continues
            j = i + n
            while j < len(p_tokens) and tuple(p_tokens[j - n + 1 : j + 1]) in source_ngrams:
                j += 1
            phrase = " ".join(p_tokens[i:j])
            matches.append(phrase)
            i = j
        else:
            i += 1
    return matches


def check_passage_against_sources(
    passage: str,
    sources: list[tuple[int, str]],
    n: int = 8,
) -> list[dict]:
    """
    sources: list of (source_id, fetched_text)
    Returns list of {source_id, matched_phrase, n_words}
    """
    findings = []
    for source_id, text in sources:
        overlaps = find_ngram_overlaps(passage, text, n=n)
        for phrase in overlaps:
            findings.append(
                {
                    "source_id": source_id,
                    "matched_phrase": phrase,
                    "n_words": len(phrase.split()),
                }
            )
    return findings


def suggest_rewrite_hint(matched_phrase: str) -> str:
    return (
        f"Rewrite in your own words. Avoid this near-verbatim sequence: "
        f"\"{matched_phrase[:120]}{'…' if len(matched_phrase) > 120 else ''}\""
    )
