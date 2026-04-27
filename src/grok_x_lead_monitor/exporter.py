from __future__ import annotations

import json
from pathlib import Path

from grok_x_lead_monitor.models import LeadRecord, RawCandidateRecord


HEADER = "| User Handle (@username) | Tweet Content Summary | Pain Point Tag | Intent Score (1-10) | Intent Reason | Exact Tweet URL |"
SEPARATOR = "| --- | --- | --- | --- | --- | --- |"


def _escape_cell(value: str) -> str:
    return value.replace("|", "\\|")


def _sort_leads(leads: list[LeadRecord]) -> list[LeadRecord]:
    return sorted(
        leads,
        key=lambda lead: (
            -lead.intent_score_10,
            -lead.tweet_created_at.timestamp(),
            lead.original_url,
            lead.username,
        ),
    )


def render_markdown_table(leads: list[LeadRecord]) -> str:
    ordered = _sort_leads(leads)
    lines = [HEADER, SEPARATOR]
    for lead in ordered:
        lines.append(
            f"| @{_escape_cell(lead.username)} | {_escape_cell(lead.tweet_summary)} | "
            f"{_escape_cell(lead.pain_point_tag)} | {lead.intent_score_10} | "
            f"{_escape_cell(lead.intent_reason)} | {_escape_cell(lead.original_url)} |"
        )
    return "\n".join(lines)


def write_markdown_report(output_dir: Path, day_label: str, leads: list[LeadRecord]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{day_label}.md"
    output_path.write_text(render_markdown_table(leads), encoding="utf-8")
    return output_path


def render_json_records(leads: list[LeadRecord]) -> list[dict[str, str | int]]:
    return [
        {
            "username": lead.username,
            "pain_point_tag": lead.pain_point_tag,
            "intent_score_10": lead.intent_score_10,
            "tweet_summary": lead.tweet_summary,
            "intent_reason": lead.intent_reason,
            "original_url": lead.original_url,
            "tweet_created_at": lead.tweet_created_at.isoformat(),
        }
        for lead in _sort_leads(leads)
    ]


def write_json_report(output_dir: Path, day_label: str, leads: list[LeadRecord]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{day_label}.json"
    output_path.write_text(
        json.dumps(render_json_records(leads), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_path


def write_raw_candidates_jsonl(output_dir: Path, day_label: str, records: list[RawCandidateRecord]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{day_label}.jsonl"
    ordered = sorted(
        records,
        key=lambda record: (
            -record.tweet_created_at.timestamp(),
            record.original_url,
            record.username,
        ),
    )
    lines = [
        json.dumps(
            {
                "username": record.username,
                "tweet_text": record.tweet_text,
                "tweet_created_at": record.tweet_created_at.isoformat(),
                "query_used": record.query_used,
                "original_url": record.original_url,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )
        for record in ordered
    ]
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path
