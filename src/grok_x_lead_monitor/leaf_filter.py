from __future__ import annotations

import csv
import json
import re
from pathlib import Path


URL_RE = re.compile(r"https?://\S+")
WHITESPACE_RE = re.compile(r"\s+")
NON_WORD_RE = re.compile(r"[^\w\s]")

SHOE_KEYWORDS = {
    "shoe",
    "shoes",
    "sandal",
    "sandals",
    "sneaker",
    "sneakers",
    "boot",
    "boots",
    "heel",
    "heels",
    "toe box",
    "wide toe box",
    "wide feet",
    "narrow fit",
    "comfy",
    "comfortable",
}
INTENT_KEYWORDS = {
    "need",
    "looking for",
    "where are we getting",
    "recommend",
    "recommendation",
    "buy",
    "getting",
    "cheap",
    "best",
    "friendly",
}
MEDICAL_KEYWORDS = {
    "plantar fasciitis",
    "swollen feet",
    "swollen foot",
    "foot hurts",
    "feet hurt",
    "foot pain",
}
OBSERVER_PATTERNS = (
    "looking at her",
    "looking at him",
    "looking at them",
    "her feet hurt",
    "his feet hurt",
    "their feet hurt",
)


def _normalize_text(value: str) -> str:
    text = URL_RE.sub("", value or "")
    text = WHITESPACE_RE.sub(" ", text).strip()
    return text


def _normalized_for_dedupe(title: str, content: str) -> str:
    normalized = _normalize_text(f"{title} {content}").lower()
    normalized = NON_WORD_RE.sub(" ", normalized)
    return WHITESPACE_RE.sub(" ", normalized).strip()


def _contains_any(text: str, phrases: set[str]) -> bool:
    return any(phrase in text for phrase in phrases)


def classify_leaf_row(row: dict[str, str]) -> dict[str, str]:
    title = row.get("Title", "")
    content = row.get("Content", "")
    combined = _normalize_text(f"{title} {content}")
    lowered = combined.lower()

    if not combined or len(combined) < 12:
        return {"decision": "drop", "reason": "empty_or_too_short"}

    if _contains_any(lowered, set(OBSERVER_PATTERNS)):
        return {"decision": "drop", "reason": "observer_commentary"}

    has_shoe_signal = _contains_any(lowered, SHOE_KEYWORDS)
    has_intent_signal = _contains_any(lowered, INTENT_KEYWORDS)
    has_medical_signal = _contains_any(lowered, MEDICAL_KEYWORDS)

    if has_medical_signal and not has_shoe_signal and not has_intent_signal:
        return {"decision": "drop", "reason": "medical_without_shoe_intent"}

    if not has_shoe_signal and len(URL_RE.sub("", content).strip()) < 20:
        return {"decision": "drop", "reason": "empty_or_link_heavy"}

    return {"decision": "keep", "reason": "default_keep"}


def export_leaf_filter_json(input_csv_path: Path, output_json_path: Path) -> Path:
    with input_csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    seen_urls: set[str] = set()
    seen_texts: set[str] = set()
    duplicate_rows = 0
    records: list[dict[str, str]] = []

    for row in rows:
        post_url = (row.get("Post URL") or "").strip()
        normalized_text = _normalized_for_dedupe(row.get("Title", ""), row.get("Content", ""))

        if post_url and post_url in seen_urls:
            duplicate_rows += 1
            decision = "drop"
            reason = "duplicate_post_url"
        elif normalized_text and normalized_text in seen_texts:
            duplicate_rows += 1
            decision = "drop"
            reason = "duplicate_normalized_content"
        else:
            classification = classify_leaf_row(row)
            decision = classification["decision"]
            reason = classification["reason"]
            if post_url:
                seen_urls.add(post_url)
            if normalized_text:
                seen_texts.add(normalized_text)

        records.append(
            {
                "platform": row.get("Platform", ""),
                "posted_date": row.get("Posted Date", ""),
                "title": row.get("Title", ""),
                "content": row.get("Content", ""),
                "source": row.get("Source", ""),
                "post_url": post_url,
                "decision": decision,
                "reason": reason,
            }
        )

    payload = {
        "summary": {
            "total_rows": len(rows),
            "kept_rows": sum(1 for record in records if record["decision"] == "keep"),
            "dropped_rows": sum(1 for record in records if record["decision"] == "drop"),
            "duplicate_rows": duplicate_rows,
        },
        "records": records,
    }
    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    output_json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_json_path
