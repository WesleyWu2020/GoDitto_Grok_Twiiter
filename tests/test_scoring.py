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
    score, priority, summary, reason = score_candidate(
        build_candidate("My feet are killing me at work. Need comfortable shoe recommendations asap.")
    )
    assert score >= 95
    assert priority == "High"
    assert summary == "Strong footwear lead with urgent pain and clear buying action."
    assert "explicit" in reason.lower()


def test_score_candidate_scores_target_condition_without_explicit_buying_language():
    score, priority, summary, reason = score_candidate(
        build_candidate("My plantar fasciitis is brutal after every shift and my current shoes are not helping.")
    )
    assert score >= 70
    assert priority == "Medium"
    assert summary == "High-fit footwear lead with a strong pain profile."
    assert "plantar fasciitis" in reason.lower()


def test_score_candidate_scores_wide_feet_as_target_customer_signal():
    score, priority, summary, reason = score_candidate(
        build_candidate("I have wide feet and foot pain after walking all day. My shoes never fit right.")
    )
    assert score >= 70
    assert priority in {"Medium", "High"}
    assert summary in {
        "High-fit footwear lead with a strong pain profile.",
        "Strong footwear lead with urgent pain and clear buying action.",
    }
    assert "wide feet" in reason.lower()


def test_score_candidate_scores_wide_feet_recommendation_request_as_lead():
    score, priority, summary, reason = score_candidate(
        build_candidate("Anyone have suggestions on best walking shoes for wide feet that will make walking easier?")
    )
    assert score >= 60
    assert priority == "Medium"
    assert "wide feet" in reason.lower()


def test_score_candidate_scores_plantar_interest_without_direct_need_phrase():
    score, priority, summary, reason = score_candidate(
        build_candidate("I am really wanting to try these shoes, but I have plantar fasciitis. Wonder if this would help or hinder.")
    )
    assert score >= 60
    assert priority == "Medium"
    assert "plantar fasciitis" in reason.lower()


def test_score_candidate_scores_plantar_pain_context_above_recall_threshold():
    score, priority, summary, reason = score_candidate(
        build_candidate("I got plantar fasciitis and now feel pain when I walk in most shoes.")
    )
    assert score >= 40
    assert priority == "Discard" or priority == "Medium"
    assert "plantar fasciitis" in reason.lower()


def test_score_candidate_scores_fit_discomfort_context_above_recall_threshold():
    score, priority, summary, reason = score_candidate(
        build_candidate("These shoes are uncomfortable and gave me blisters after walking all day.")
    )
    assert score >= 40
    assert priority == "Discard" or priority == "Medium"
    assert "walking all day" in reason.lower() or "current shoes are not working" in reason.lower()


def test_score_candidate_scores_bunion_request_as_fitville_lead():
    score, priority, summary, reason = score_candidate(
        build_candidate("What shoes help bunions? Need a wide toe box and better support for walking all day.")
    )
    assert score >= 70
    assert "bunion" in reason.lower()


def test_score_candidate_scores_diabetic_swelling_request_above_threshold():
    score, priority, summary, reason = score_candidate(
        build_candidate("Need diabetic shoes for swollen feet because my current shoes are not helping.")
    )
    assert score >= 60
    assert "diabetic" in reason.lower() or "swollen" in reason.lower()


def test_score_candidate_scores_slip_resistant_work_need_as_fitville_signal():
    score, priority, summary, reason = score_candidate(
        build_candidate("Need non slip work shoes for kitchen shifts. My feet hurt standing all day.")
    )
    assert score >= 70
    assert "standing all day" in reason.lower() or "work" in reason.lower()


def test_score_candidate_discards_low_signal_text():
    score, priority, summary, reason = score_candidate(build_candidate("Feet are weird sometimes."))
    assert score <= 20
    assert priority == "Discard"
    assert summary == "Weak footwear lead with low commercial relevance."
    assert "weak signal" in reason.lower()


def test_infer_pain_point_tag_prefers_plantar_fasciitis():
    tag = infer_pain_point_tag(
        "I have plantar fasciitis and my feet hurt after standing all day, need shoe recommendations."
    )
    assert tag == "Plantar Fasciitis"


def test_to_intent_score_10_maps_internal_score():
    assert to_intent_score_10(95) == 10
    assert to_intent_score_10(75) == 8
    assert to_intent_score_10(20) == 2
