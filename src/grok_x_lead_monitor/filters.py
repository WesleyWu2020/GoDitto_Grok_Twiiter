from __future__ import annotations

import re

from grok_x_lead_monitor.models import Candidate


BLOCKLIST = (
    "coupon",
    "discount",
    "giveaway",
    "sweepstakes",
    "affiliate",
    "promo",
    "promotion",
    "code ",
    "#ad",
)

NON_CONSUMER_PATTERNS = (
    "our brand",
    "brand launched",
    "brand just launched",
    "news",
    "news update",
    "article",
    "report",
    "roundup",
    "aggregate",
    "aggregated",
    "customers are",
    "people are asking",
    "people are talking",
    "followers",
    "audience",
    "trending",
    "viral",
)

FIRST_PERSON_CONSUMER_HINTS = (
    " my ",
    " i'm ",
    " i am ",
    " me ",
    " need ",
    " looking for ",
    " looking to ",
    " recommend",
    " recommendations",
    " recommendation",
    " anyone have suggestions ",
    " anyone have recs ",
    " what shoes should i ",
    " what are some good ",
    " wondering if this would help ",
    " wanting to try ",
    " best walking shoes ",
    " best shoes for ",
)

RELEVANCE_HINTS = (
    "foot",
    "feet",
    "shoe",
    "shoes",
    "plantar",
    "wide feet",
    "wide foot",
    "extra wide",
    "narrow fit",
    "narrow feet",
    "comfortable",
    "walking all day",
    "standing all day",
    "better shoes",
)


def _has_citation_data(candidate: Candidate) -> bool:
    if not candidate.citations:
        return False
    for citation in candidate.citations:
        if citation.get("url") or citation.get("tweet_id"):
            return True
    return False


def _looks_like_consumer_need(text: str) -> bool:
    return any(hint in text for hint in FIRST_PERSON_CONSUMER_HINTS)


def _looks_like_non_consumer_commentary(text: str) -> bool:
    return any(pattern in text for pattern in NON_CONSUMER_PATTERNS)


def is_valid_candidate(candidate: Candidate) -> bool:
    text = candidate.tweet_text.lower()
    if not _has_citation_data(candidate):
        return False
    if any(token in text for token in BLOCKLIST):
        return False
    if _looks_like_non_consumer_commentary(text):
        return False
    if not _looks_like_consumer_need(text):
        return False
    if len(re.findall(r"#\w+", text)) >= 4:
        return False
    if not any(token in text for token in RELEVANCE_HINTS):
        return False
    return True
