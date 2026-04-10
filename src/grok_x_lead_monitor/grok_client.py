from __future__ import annotations

import json
import re
import time
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any, Mapping

import httpx

from grok_x_lead_monitor.models import Candidate


SYSTEM_PROMPT = (
    "Use x_search as the only live data source. "
    "Find real human X users with high intent to buy orthopedic or comfort footwear. "
    "Strictly exclude promotional links, marketing spam, bot posts, competitor brand promotion, news articles, and irrelevant topics such as animal paws. "
    "Return structured JSON with candidate rows and citation metadata. "
    "Do not fabricate users or tweets. "
    "Do not keep rows whose URL cannot be verified. "
    "Citation metadata must be included for every retained candidate."
)


def build_grok_payload(
    query: str,
    start_iso: str,
    end_iso: str,
    model: str = "grok-4-1-fast-reasoning",
) -> dict[str, Any]:
    from_date = start_iso[:10]
    to_date = end_iso[:10]
    return {
        "model": model,
        "input": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": (
                    "Search X for consumer footwear-intent leads in the last 7 days.\n"
                    f"Query: {query}\n"
                    f"Window: {start_iso} to {end_iso}\n"
                    "Focus on users complaining shoes hurt, asking for wide shoes, plantar fasciitis recommendations, or standing all day shoe help.\n"
                    "Return JSON with a top-level candidates array containing up to 100 rows.\n"
                    "Each candidate row must include: username, tweet_text, tweet_created_at, query_used, pain_point_tag, intent_score_1_to_10, citations."
                ),
            },
        ],
        "tools": [
            {
                "type": "x_search",
                "from_date": from_date,
                "to_date": to_date,
            }
        ],
        "text": {"format": {"type": "json_object"}},
        "temperature": 0,
        "max_output_tokens": 8000,
    }


def _clean_json_text(raw_text: str) -> str:
    text = raw_text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text


def _parse_datetime(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return parsedate_to_datetime(value)


def _load_payload(raw: str | Mapping[str, Any]) -> Mapping[str, Any]:
    if isinstance(raw, Mapping):
        return raw
    try:
        return json.loads(_clean_json_text(raw))
    except json.JSONDecodeError:
        return {}


def _candidate_rows(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    rows = payload.get("candidates", [])
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, Mapping)]


def _is_nonempty_str(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def parse_candidate_response(
    raw_text: str | Mapping[str, Any],
    annotation_lookup: Mapping[str, str] | None = None,
) -> list[Candidate]:
    payload = _load_payload(raw_text)
    candidates: list[Candidate] = []
    for item in _candidate_rows(payload):
        try:
            username = item["username"]
            tweet_text = item["tweet_text"]
            tweet_created_at = _parse_datetime(item["tweet_created_at"])
            query_used = item["query_used"]
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
        if not all(_is_nonempty_str(value) for value in (username, tweet_text, query_used)):
            continue

        raw_citations = item.get("citations", [])
        citations: list[dict[str, Any]] = []
        if isinstance(raw_citations, list):
            for citation in raw_citations:
                if isinstance(citation, Mapping):
                    citations.append(dict(citation))
                elif isinstance(citation, str):
                    token = citation.strip()
                    if token.startswith("http://") or token.startswith("https://"):
                        citations.append({"url": token})
                    elif annotation_lookup and token in annotation_lookup:
                        citations.append({"url": annotation_lookup[token]})
        if not citations:
            for url_key in ("original_url", "tweet_url", "url", "exact_tweet_url"):
                raw_url = item.get(url_key)
                if isinstance(raw_url, str) and raw_url.strip():
                    citations = [{"url": raw_url.strip()}]
                    break
        if not citations:
            raw_tweet_id = item.get("tweet_id")
            raw_handle = item.get("author_handle") or item.get("handle") or item.get("username") or username
            if raw_tweet_id is not None and isinstance(raw_handle, str) and raw_handle.strip():
                citations = [{"tweet_id": str(raw_tweet_id), "author_handle": raw_handle.strip().lstrip("@")}]

        candidates.append(
            Candidate(
                username=username,
                display_name=item.get("display_name"),
                tweet_text=tweet_text,
                tweet_created_at=tweet_created_at,
                query_used=query_used,
                citations=citations,
                tweet_id=item.get("tweet_id"),
                author_handle=item.get("author_handle"),
            )
        )
    return candidates


class GrokSearchClient:
    def __init__(
        self,
        api_key: str,
        http_client: httpx.Client | None = None,
        model: str = "grok-4-1-fast-reasoning",
    ):
        self.api_key = api_key
        self._http_client = http_client or httpx.Client()
        self.model = model

    def search(self, query: str, start_iso: str, end_iso: str) -> list[Candidate]:
        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                response = self._http_client.post(
                    "https://api.x.ai/v1/responses",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                        # Avoid flaky keep-alive connections in some proxy/network paths.
                        "Connection": "close",
                    },
                    json=build_grok_payload(query, start_iso, end_iso, model=self.model),
                    timeout=45.0,
                )
                status_code = getattr(response, "status_code", 200)
                if status_code >= 500:
                    if attempt < 2:
                        time.sleep(1.0 * (attempt + 1))
                        continue
                response.raise_for_status()
                break
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.RemoteProtocolError, httpx.WriteError) as exc:
                last_exc = exc
                if attempt < 2:
                    time.sleep(1.0 * (attempt + 1))
                    continue
                raise
        else:
            if last_exc:
                raise last_exc
            return []

        try:
            payload = response.json()
        except ValueError:
            return []

        if not isinstance(payload, Mapping):
            return []

        output = payload.get("output")
        text_chunks: list[str] = []
        annotation_lookup: dict[str, str] = {}
        annotation_index = 1
        if isinstance(output, list):
            for item in output:
                if not isinstance(item, Mapping):
                    continue
                if item.get("type") != "message":
                    continue
                content = item.get("content")
                if not isinstance(content, list):
                    continue
                for part in content:
                    if not isinstance(part, Mapping):
                        continue
                    part_type = part.get("type")
                    if part_type in {"output_text", "text"}:
                        text = part.get("text")
                        if isinstance(text, str) and text.strip():
                            text_chunks.append(text)
                        annotations = part.get("annotations")
                        if isinstance(annotations, list):
                            for ann in annotations:
                                if not isinstance(ann, Mapping):
                                    continue
                                ann_url = ann.get("url")
                                if isinstance(ann_url, str) and ann_url.strip():
                                    annotation_lookup[f"post:{annotation_index}"] = ann_url.strip()
                                    annotation_index += 1

        if not text_chunks:
            output_text = payload.get("output_text")
            if isinstance(output_text, str) and output_text.strip():
                text_chunks.append(output_text)
        if not text_chunks:
            return []
        return parse_candidate_response("\n".join(text_chunks), annotation_lookup=annotation_lookup)
