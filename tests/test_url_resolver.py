from grok_x_lead_monitor.url_resolver import resolve_original_url


def test_resolve_original_url_from_direct_fields():
    citations = [{"tweet_id": "1234567890", "author_handle": "runner"}]
    assert resolve_original_url(citations) == "https://x.com/runner/status/1234567890"


def test_resolve_original_url_from_citation_url():
    citations = [{"url": "https://x.com/walker/status/55555?s=20"}]
    assert resolve_original_url(citations) == "https://x.com/walker/status/55555"


def test_resolve_original_url_does_not_use_username_fallback():
    citations = [{"tweet_id": "55555"}]
    assert resolve_original_url(citations) is None


def test_resolve_original_url_returns_none_on_incomplete_metadata():
    citations = [{"url": "https://x.com/search?q=comfortable%20shoes"}]
    assert resolve_original_url(citations) is None
