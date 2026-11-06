from app.utils.quote_match import quote_in_source


def test_exact_match():
    ok, method = quote_in_source("The GET method", "Docs say: The GET method retrieves a resource.")
    assert ok and method == "exact"


def test_normalized_match():
    ok, method = quote_in_source("The GET method!", "the get method retrieves")
    assert ok


def test_no_match():
    ok, method = quote_in_source("401 is a server error category 5xx", "401 Unauthorized is a client error.")
    assert not ok and method == "none"
