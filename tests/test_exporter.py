from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from grok_x_lead_monitor.exporter import HEADER, SEPARATOR, render_markdown_table, write_markdown_report
from grok_x_lead_monitor.models import LeadRecord


def test_render_markdown_table_outputs_header_only_when_empty():
    rendered = render_markdown_table([])
    assert rendered == HEADER + "\n" + SEPARATOR


def test_write_markdown_report_writes_sorted_rows(tmp_path: Path):
    leads = [
        LeadRecord(
            username="low",
            pain_point_tag="Foot Pain",
            intent_score_10=7,
            tweet_summary="Needs better shoes.",
            intent_reason="foot pain plus current-shoe dissatisfaction",
            original_url="https://x.com/low/status/2",
            tweet_created_at=datetime(2026, 4, 8, 1, 0, tzinfo=ZoneInfo("UTC")),
        ),
        LeadRecord(
            username="high",
            pain_point_tag="Standing All Day",
            intent_score_10=10,
            tweet_summary="Needs comfortable shoes urgently.",
            intent_reason="explicit recommendation request plus work pain",
            original_url="https://x.com/high/status/1",
            tweet_created_at=datetime(2026, 4, 8, 2, 0, tzinfo=ZoneInfo("UTC")),
        ),
    ]
    output_path = write_markdown_report(tmp_path, "2026-04-08", leads)
    content = output_path.read_text()
    assert output_path == tmp_path / "2026-04-08.md"
    assert content.splitlines()[2].startswith(
        "| @high | Needs comfortable shoes urgently. | Standing All Day | 10 | explicit recommendation request plus work pain |"
    )


def test_render_markdown_table_uses_deterministic_tie_breakers():
    leads = [
        LeadRecord(
            username="zeta",
            pain_point_tag="Foot Pain",
            intent_score_10=8,
            tweet_summary="First tie row.",
            intent_reason="first tie reason",
            original_url="https://x.com/zeta/status/2",
            tweet_created_at=datetime(2026, 4, 8, 1, 0, tzinfo=ZoneInfo("UTC")),
        ),
        LeadRecord(
            username="alpha",
            pain_point_tag="Foot Pain",
            intent_score_10=8,
            tweet_summary="Second tie row.",
            intent_reason="second tie reason",
            original_url="https://x.com/alpha/status/1",
            tweet_created_at=datetime(2026, 4, 8, 1, 0, tzinfo=ZoneInfo("UTC")),
        ),
    ]
    rendered = render_markdown_table(leads).splitlines()
    alpha_cells = [cell.strip() for cell in rendered[2].strip("|").split("|")]
    zeta_cells = [cell.strip() for cell in rendered[3].strip("|").split("|")]
    assert alpha_cells[0] == "@alpha"
    assert zeta_cells[0] == "@zeta"
    assert alpha_cells[5] == "https://x.com/alpha/status/1"
    assert zeta_cells[5] == "https://x.com/zeta/status/2"
