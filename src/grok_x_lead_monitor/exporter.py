from __future__ import annotations

from pathlib import Path

from grok_x_lead_monitor.models import LeadRecord


HEADER = "| User Handle (@username) | Tweet Content Summary | Pain Point Tag | Intent Score (1-10) | Intent Reason | Exact Tweet URL |"
SEPARATOR = "| --- | --- | --- | --- | --- | --- |"


def _escape_cell(value: str) -> str:
    return value.replace("|", "\\|")


def render_markdown_table(leads: list[LeadRecord]) -> str:
    ordered = sorted(
        leads,
        key=lambda lead: (
            -lead.intent_score_10,
            -lead.tweet_created_at.timestamp(),
            lead.original_url,
            lead.username,
        ),
    )
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
