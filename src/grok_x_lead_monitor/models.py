from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class QuerySpec:
    query: str
    intent_theme: str
    language: str = "en"


@dataclass(frozen=True)
class Candidate:
    username: str
    tweet_text: str
    tweet_created_at: datetime
    query_used: str
    citations: list[dict[str, Any]] = field(default_factory=list)
    display_name: str | None = None
    tweet_id: str | None = None
    author_handle: str | None = None


@dataclass(frozen=True)
class LeadRecord:
    username: str
    pain_point_tag: str
    intent_score_10: int
    tweet_summary: str
    intent_reason: str
    original_url: str
    tweet_created_at: datetime
