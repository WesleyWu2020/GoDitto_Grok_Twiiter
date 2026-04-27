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
    "my ",
    " my ",
    "i'm ",
    " i'm ",
    "i am ",
    " i am ",
    "me ",
    " me ",
    "need ",
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

REQUEST_STYLE_HINTS = (
    " any recs",
    " recs ",
    " recs?",
    " shoe recs",
    " shoe recommendations",
    " recommendations for",
    " suggest ",
    " suggestions ",
    " advice ",
    " which shoes",
    " what shoes",
    " help me choose",
)

PAIN_OR_FIT_HINTS = (
    " pain",
    " hurts",
    " aching",
    " sore",
    " blister",
    " plantar",
    " wide feet",
    " wide foot",
    " extra wide",
    " narrow feet",
    " narrow fit",
    " bunion",
    " bunions",
    " bunion pain",
    " swollen feet",
    " foot swelling",
    " swelling",
    " edema",
    " toes cramped",
    " toe pain",
    " high instep",
    " flat feet",
    " non slip",
    " slip resistant",
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
    "bunion",
    "bunions",
    "diabetic",
    "swollen feet",
    "swelling",
    "edema",
    "flat feet",
    "arch support",
    "wide toe box",
    "4e",
    "6e",
    "high instep",
    "non slip",
    "slip resistant",
    "steel toe",
)


def _has_citation_data(candidate: Candidate) -> bool:
    if not candidate.citations:
        return False
    for citation in candidate.citations:
        if citation.get("url") or citation.get("tweet_id"):
            return True
    return False


def _looks_like_consumer_need(text: str) -> bool:
    if any(hint in text for hint in FIRST_PERSON_CONSUMER_HINTS):
        return True
    has_request_style = any(hint in text for hint in REQUEST_STYLE_HINTS)
    has_pain_or_fit = any(hint in text for hint in PAIN_OR_FIT_HINTS)
    has_relevance = any(hint in text for hint in RELEVANCE_HINTS)
    has_question = "?" in text
    if has_request_style and (has_pain_or_fit or has_relevance):
        return True
    if has_question and has_relevance and has_request_style:
        return True
    return False


def _looks_like_broad_footwear_need(text: str) -> bool:
    has_relevance = any(hint in text for hint in RELEVANCE_HINTS)
    has_pain_or_fit = any(hint in text for hint in PAIN_OR_FIT_HINTS)
    has_request_style = any(hint in text for hint in REQUEST_STYLE_HINTS)
    has_question = "?" in text
    return has_relevance and (has_pain_or_fit or has_request_style or has_question)


def _looks_like_non_consumer_commentary(text: str) -> bool:
    return any(pattern in text for pattern in NON_CONSUMER_PATTERNS)


def _has_blocklisted_promo(text: str) -> bool:
    for token in BLOCKLIST:
        if token == "#ad":
            if re.search(r"(?<!\w)#ad(?!\w)", text):
                return True
            continue
        if token in text:
            return True
    return False


def is_valid_candidate(candidate: Candidate) -> bool:
    text = candidate.tweet_text.lower()
    if not _has_citation_data(candidate):
        return False
    if _has_blocklisted_promo(text):
        return False
    if _looks_like_non_consumer_commentary(text):
        return False
    if not (_looks_like_consumer_need(text) or _looks_like_broad_footwear_need(text)):
        return False
    if len(re.findall(r"#\w+", text)) >= 6:
        return False
    if not any(token in text for token in RELEVANCE_HINTS):
        return False
    return True
