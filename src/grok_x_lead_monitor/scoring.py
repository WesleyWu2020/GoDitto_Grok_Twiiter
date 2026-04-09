from __future__ import annotations

from grok_x_lead_monitor.models import Candidate


HIGH_SCORE = 95
MEDIUM_SCORE = 72
LOW_SCORE = 20


HIGH_SUMMARY = "Needs comfortable shoes urgently for work-related foot pain."
MEDIUM_SUMMARY = "Has recurring work-related foot pain and dislikes current shoes."
LOW_SUMMARY = "Low-signal mention without actionable buying intent."


def _text_has_any(text: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in text for phrase in phrases)


def infer_pain_point_tag(text: str) -> str:
    normalized = text.lower()
    if _text_has_any(normalized, ("plantar fasciitis", "plantar")):
        return "Plantar Fasciitis"
    if _text_has_any(normalized, ("wide feet", "wide foot", "extra wide", "2e", "4e")):
        return "Wide Feet"
    if _text_has_any(normalized, ("high instep", "instep")):
        return "High Instep"
    if _text_has_any(normalized, ("standing all day", "all day standing", "shift")):
        return "Standing All Day"
    return "Foot Pain"


def to_intent_score_10(score_100: int) -> int:
    if score_100 <= 0:
        return 1
    if score_100 >= 100:
        return 10
    return max(1, min(10, int((score_100 + 5) / 10)))


def score_candidate(candidate: Candidate, high_threshold: int = 85) -> tuple[int, str, str]:
    text = candidate.tweet_text.lower()

    pain_signals = _text_has_any(
        text,
        (
            "my feet are killing me",
            "feet hurt",
            "foot pain",
            "plantar",
            "hurts after every shift",
            "hurt every shift",
            "standing all day",
            "walking all day",
            "my feet hurt",
        ),
    )
    buying_intent = _text_has_any(
        text,
        (
            "need comfortable shoes recommendations",
            "recommend shoes",
            "recommendations",
            "recommendation",
            "need better shoes",
            "best shoes",
            "looking for shoes",
            "need shoes",
        ),
    )
    dissatisfaction = _text_has_any(
        text,
        (
            "shoes are awful",
            "my shoes are awful",
            "current shoes",
            "better shoes",
            "replacement",
        ),
    )
    work_context = _text_has_any(text, ("work", "shift", "retail", "hospitality", "warehouse", "nursing"))
    urgency = _text_has_any(text, ("asap", "urgently", "really need", "need now"))

    if pain_signals and buying_intent and (work_context or urgency):
        score, summary = HIGH_SCORE, HIGH_SUMMARY
    elif pain_signals and (dissatisfaction or work_context or buying_intent):
        score, summary = MEDIUM_SCORE, MEDIUM_SUMMARY
    elif buying_intent and dissatisfaction:
        score, summary = MEDIUM_SCORE, MEDIUM_SUMMARY
    else:
        score, summary = LOW_SCORE, LOW_SUMMARY

    if score >= high_threshold:
        priority = "High"
    elif score >= 60:
        priority = "Medium"
    else:
        priority = "Discard"
    return score, priority, summary
