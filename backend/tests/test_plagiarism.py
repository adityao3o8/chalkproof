from app.utils.plagiarism import find_ngram_overlaps, check_passage_against_sources


def test_detects_eight_word_overlap():
    source = "the quick brown fox jumps over the lazy dog today and yesterday"
    passage = "Students should note the quick brown fox jumps over the lazy dog in this example."
    overlaps = find_ngram_overlaps(passage, source, n=8)
    assert overlaps
    assert any(len(o.split()) >= 8 for o in overlaps)


def test_no_false_positive_short():
    source = "HTTP GET retrieves a representation of the resource"
    passage = "Use GET when you need to retrieve data safely."
    assert find_ngram_overlaps(passage, source, n=8) == []


def test_check_against_sources():
    findings = check_passage_against_sources(
        "alpha beta gamma delta epsilon zeta eta theta iota",
        [(1, "alpha beta gamma delta epsilon zeta eta theta iota kappa")],
        n=8,
    )
    assert findings and findings[0]["source_id"] == 1
