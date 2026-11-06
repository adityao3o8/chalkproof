"""Programmatic quote-in-source matching (exact + fuzzy)."""

from __future__ import annotations

import re

from rapidfuzz import fuzz


def normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s]", "", text)
    return text.strip()


def quote_in_source(
    quote: str,
    source_text: str,
    fuzzy_threshold: int = 85,
) -> tuple[bool, str]:
    """
    Check whether `quote` appears in `source_text`.
    Returns (matched, method) where method is 'exact'|'fuzzy'|'none'.
    """
    if not quote or not source_text:
        return False, "none"

    q = quote.strip()
    if q in source_text:
        return True, "exact"

    nq = normalize(q)
    ns = normalize(source_text)
    if nq and nq in ns:
        return True, "exact"

    # Sliding window fuzzy match for short quotes
    if len(nq) < 20:
        ratio = fuzz.partial_ratio(nq, ns)
        if ratio >= fuzzy_threshold:
            return True, "fuzzy"
        return False, "none"

    # For longer quotes, check best substring of similar length
    window = len(nq)
    best = 0
    step = max(1, window // 4)
    for i in range(0, max(1, len(ns) - window + 1), step):
        chunk = ns[i : i + window + 20]
        best = max(best, fuzz.ratio(nq, chunk))
        if best >= fuzzy_threshold:
            return True, "fuzzy"

    return False, "none"
