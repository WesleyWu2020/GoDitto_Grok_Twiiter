from __future__ import annotations

import re
from urllib.parse import urlparse


X_TWEET_URL_RE = re.compile(r"^/([^/]+)/status/(\d+)/?$")


def _normalize_url(url: str) -> str | None:
    parsed = urlparse(url)
    if parsed.netloc.lower() not in {"x.com", "www.x.com"}:
        return None
    match = X_TWEET_URL_RE.match(parsed.path)
    if not match:
        return None
    handle, tweet_id = match.groups()
    return f"https://x.com/{handle}/status/{tweet_id}"


def resolve_original_url(citations_or_username: object, citations: list[dict] | None = None) -> str | None:
    if isinstance(citations_or_username, list) and citations is None:
        resolved_citations = citations_or_username
    elif isinstance(citations_or_username, str) and isinstance(citations, list):
        resolved_citations = citations
    else:
        return None

    for citation in resolved_citations:
        tweet_id = citation.get("tweet_id")
        handle = citation.get("author_handle") or citation.get("handle") or citation.get("username")
        if tweet_id and handle:
            tweet_id_text = str(tweet_id)
            if tweet_id_text.isdigit() and str(handle).strip():
                return f"https://x.com/{handle}/status/{tweet_id_text}"

        citation_url = citation.get("url")
        if not citation_url:
            continue
        normalized = _normalize_url(citation_url)
        if normalized:
            return normalized
    return None
