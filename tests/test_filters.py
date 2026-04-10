from datetime import datetime
from zoneinfo import ZoneInfo

from grok_x_lead_monitor.filters import is_valid_candidate
from grok_x_lead_monitor.models import Candidate


def build_candidate(text: str, citations: list[dict] | None = None) -> Candidate:
    return Candidate(
        username="person",
        tweet_text=text,
        tweet_created_at=datetime(2026, 4, 8, 12, 0, tzinfo=ZoneInfo("UTC")),
        query_used="feet hurt standing all day",
        citations=[{"url": "https://x.com/person/status/123"}] if citations is None else citations,
    )


def test_filter_rejects_promotional_language():
    candidate = build_candidate("Use my code SAVE20 for the best walking shoes #ad #deal")
    assert is_valid_candidate(candidate) is False


def test_filter_rejects_missing_citations():
    candidate = build_candidate("Need better shoes for work, my feet hurt", citations=[])
    assert is_valid_candidate(candidate) is False


def test_filter_rejects_obvious_non_consumer_commentary():
    candidate = build_candidate("Our brand just launched a new shoe line and the article is already trending.")
    assert is_valid_candidate(candidate) is False


def test_filter_keeps_authentic_consumer_request():
    candidate = build_candidate("My feet hurt after every shift. Need comfortable shoes recommendations.")
    assert is_valid_candidate(candidate) is True


def test_filter_keeps_question_style_request_for_target_customer():
    candidate = build_candidate("Anyone have suggestions on best walking shoes for wide feet that will make walking easier?")
    assert is_valid_candidate(candidate) is True
