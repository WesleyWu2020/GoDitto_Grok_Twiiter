from datetime import datetime
from zoneinfo import ZoneInfo

from grok_x_lead_monitor.models import Candidate
from grok_x_lead_monitor.scoring import infer_pain_point_tag, score_candidate, to_intent_score_10


def build_candidate(text: str) -> Candidate:
    return Candidate(
        username="buyer",
        tweet_text=text,
        tweet_created_at=datetime(2026, 4, 8, 12, 0, tzinfo=ZoneInfo("UTC")),
        query_used="need comfortable shoes recommendations",
        citations=[{"url": "https://x.com/buyer/status/123"}],
    )


def test_score_candidate_marks_explicit_help_request_high():
    score, priority, summary = score_candidate(
        build_candidate("My feet are killing me at work. Need comfortable shoe recommendations asap.")
    )
    assert score == 95
    assert priority == "High"
    assert summary == "Needs comfortable shoes urgently for work-related foot pain."


def test_score_candidate_marks_pain_complaint_medium():
    score, priority, summary = score_candidate(build_candidate("My feet hurt every shift and my shoes are awful."))
    assert score == 72
    assert priority == "Medium"
    assert summary == "Has recurring work-related foot pain and dislikes current shoes."


def test_score_candidate_discards_low_signal_text():
    score, priority, summary = score_candidate(build_candidate("Feet are weird sometimes."))
    assert score == 20
    assert priority == "Discard"
    assert summary == "Low-signal mention without actionable buying intent."


def test_infer_pain_point_tag_prefers_plantar_fasciitis():
    tag = infer_pain_point_tag(
        "I have plantar fasciitis and my feet hurt after standing all day, need shoe recommendations."
    )
    assert tag == "Plantar Fasciitis"


def test_to_intent_score_10_maps_internal_score():
    assert to_intent_score_10(95) == 10
    assert to_intent_score_10(72) == 7
    assert to_intent_score_10(20) == 2
