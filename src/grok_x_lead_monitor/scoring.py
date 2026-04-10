from __future__ import annotations

from grok_x_lead_monitor.models import Candidate

def _text_has_any(text: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in text for phrase in phrases)


def infer_pain_point_tag(text: str) -> str:
    normalized = text.lower()
    if _text_has_any(normalized, ("plantar fasciitis", "plantar")):
        return "Plantar Fasciitis"
    if _text_has_any(normalized, ("wide feet", "wide foot", "extra wide", "2e", "4e")):
        return "Wide Feet"
    if _text_has_any(normalized, ("narrow feet", "narrow foot", "narrow fit")):
        return "Narrow Fit"
    if _text_has_any(normalized, ("standing all day", "all day standing", "shift")):
        return "Standing All Day"
    if _text_has_any(normalized, ("walking all day", "walk all day")):
        return "Walking All Day"
    return "Foot Pain"


def to_intent_score_10(score_100: int) -> int:
    if score_100 <= 0:
        return 1
    if score_100 >= 100:
        return 10
    return max(1, min(10, int((score_100 + 5) / 10)))


def score_candidate(candidate: Candidate, high_threshold: int = 85) -> tuple[int, str, str, str]:
    text = candidate.tweet_text.lower()
    score = 0
    reasons: list[str] = []

    pain_signals = _text_has_any(
        text,
        (
            "my feet are killing me",
            "feet hurt",
            "foot pain",
            "hurts after every shift",
            "hurt every shift",
            "my feet hurt",
        ),
    )
    if pain_signals:
        score += 25
        reasons.append("strong foot pain")

    target_condition_hits = 0
    target_condition_signals = (
        ("plantar fasciitis", ("plantar fasciitis", "plantar"), 20),
        ("wide feet", ("wide feet", "wide foot", "extra wide", "2e", "4e"), 20),
        ("narrow fit", ("narrow feet", "narrow foot", "narrow fit"), 20),
        ("standing all day", ("standing all day", "all day standing", "every shift"), 20),
        ("walking all day", ("walking all day", "walk all day"), 10),
    )
    for label, phrases, weight in target_condition_signals:
        if _text_has_any(text, phrases):
            score += weight
            target_condition_hits += 1
            reasons.append(label)

    explicit_buying_intent = _text_has_any(
        text,
        (
            "need comfortable shoes recommendations",
            "need comfortable shoe recommendations",
            "recommend shoes",
            "recommendations",
            "recommendation",
            "need better shoes",
            "best shoes",
            "best walking shoes",
            "looking for shoes",
            "need shoes",
            "anyone have suggestions",
            "anyone have recs",
            "what are some good",
            "what shoes should i",
            "wanting to try",
            "would help or hinder",
            "would help",
        ),
    )
    if explicit_buying_intent:
        score += 35
        reasons.append("explicit recommendation request")

    dissatisfaction = _text_has_any(
        text,
        (
            "shoes are awful",
            "my shoes are awful",
            "current shoes",
            "better shoes",
            "replacement",
            "not helping",
            "never fit right",
            "don't fit right",
        ),
    )
    if dissatisfaction:
        score += 10
        reasons.append("current shoes are not working")

    work_context = _text_has_any(text, ("work", "shift", "retail", "hospitality", "warehouse", "nursing"))
    if work_context:
        score += 5
        reasons.append("work-impact context")

    urgency = _text_has_any(text, ("asap", "urgently", "really need", "need now"))
    if urgency:
        score += 5
        reasons.append("urgent timing")

    if pain_signals and explicit_buying_intent:
        score += 25
    elif target_condition_hits and explicit_buying_intent:
        score += 10
    elif target_condition_hits >= 2 and dissatisfaction:
        score += 15

    score = max(0, min(100, score))

    if score >= high_threshold:
        summary = "Strong footwear lead with urgent pain and clear buying action."
    elif score >= 70:
        summary = "High-fit footwear lead with a strong pain profile."
    else:
        summary = "Weak footwear lead with low commercial relevance."

    if score >= high_threshold:
        priority = "High"
    elif score >= 60:
        priority = "Medium"
    else:
        priority = "Discard"

    if not reasons:
        reasons.append("weak signal only")
    return score, priority, summary, ", ".join(reasons)
