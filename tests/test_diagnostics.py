from datetime import datetime
from zoneinfo import ZoneInfo

from grok_x_lead_monitor.diagnostics import diagnose_query_results
from grok_x_lead_monitor.models import Candidate


def _candidate(username: str, text: str, url: str) -> Candidate:
    return Candidate(
        username=username,
        tweet_text=text,
        tweet_created_at=datetime(2026, 4, 8, 12, 0, tzinfo=ZoneInfo("UTC")),
        query_used="best shoes for plantar fasciitis",
        citations=[{"url": url}],
    )


def test_diagnose_query_results_reports_pipeline_dropoff():
    candidates = [
        _candidate(
            "strong",
            "My plantar fasciitis is brutal after every shift and I need comfortable shoe recommendations asap.",
            "https://x.com/strong/status/1",
        ),
        _candidate(
            "weak",
            "Feet are weird sometimes.",
            "https://x.com/weak/status/2",
        ),
        _candidate(
            "promo",
            "Use code SAVE20 for best shoes #ad",
            "https://x.com/promo/status/3",
        ),
    ]

    report = diagnose_query_results(
        query="best shoes for plantar fasciitis",
        candidates=candidates,
        high_priority_score=85,
        min_intent_score=60,
    )

    assert report["query"] == "best shoes for plantar fasciitis"
    assert report["raw_count"] == 3
    assert report["valid_count"] == 1
    assert report["passing_score_count"] == 1
    assert report["unique_url_count"] == 1
    assert report["samples"][0]["username"] == "strong"
    assert report["samples"][0]["passes_filters"] is True
    assert report["samples"][0]["passes_score"] is True
    assert report["samples"][1]["username"] == "weak"
    assert report["samples"][1]["passes_score"] is False
