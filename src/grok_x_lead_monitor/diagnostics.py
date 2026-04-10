from __future__ import annotations

from grok_x_lead_monitor.filters import is_valid_candidate
from grok_x_lead_monitor.models import Candidate
from grok_x_lead_monitor.scoring import score_candidate
from grok_x_lead_monitor.url_resolver import resolve_original_url


def diagnose_query_results(
    query: str,
    candidates: list[Candidate],
    high_priority_score: int,
    min_intent_score: int,
) -> dict[str, object]:
    seen_urls: set[str] = set()
    valid_count = 0
    passing_score_count = 0
    unique_url_count = 0
    samples: list[dict[str, object]] = []

    for candidate in candidates:
        passes_filters = is_valid_candidate(candidate)
        if passes_filters:
            valid_count += 1

        score, priority, summary, reason = score_candidate(
            candidate,
            high_threshold=high_priority_score,
        )
        original_url = resolve_original_url(candidate.citations)
        passes_score = passes_filters and score >= min_intent_score
        deduped = passes_score and bool(original_url) and original_url in seen_urls
        if passes_score:
            passing_score_count += 1
        if passes_score and original_url and original_url not in seen_urls:
            seen_urls.add(original_url)
            unique_url_count += 1

        if len(samples) < 3:
            samples.append(
                {
                    "username": candidate.username,
                    "passes_filters": passes_filters,
                    "score": score,
                    "priority": priority,
                    "passes_score": passes_score,
                    "deduped": deduped,
                    "original_url": original_url,
                    "reason": reason,
                    "summary": summary,
                    "tweet_text": candidate.tweet_text,
                }
            )

    return {
        "query": query,
        "raw_count": len(candidates),
        "valid_count": valid_count,
        "passing_score_count": passing_score_count,
        "unique_url_count": unique_url_count,
        "samples": samples,
    }


def format_query_diagnostics(report: dict[str, object]) -> str:
    lines = [
        (
            f"[DIAG] Query='{report['query']}' raw={report['raw_count']} "
            f"valid={report['valid_count']} passing_score={report['passing_score_count']} "
            f"unique_url={report['unique_url_count']}"
        )
    ]
    for sample in report["samples"]:
        lines.append(
            "  "
            f"sample@{sample['username']} "
            f"filters={sample['passes_filters']} "
            f"score={sample['score']} "
            f"passes_score={sample['passes_score']} "
            f"deduped={sample['deduped']} "
            f"reason={sample['reason']}"
        )
    return "\n".join(lines)
