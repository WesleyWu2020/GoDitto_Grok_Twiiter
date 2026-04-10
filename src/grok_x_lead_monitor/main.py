from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from grok_x_lead_monitor.config import Settings, resolve_window
from grok_x_lead_monitor.diagnostics import diagnose_query_results, format_query_diagnostics
from grok_x_lead_monitor.exporter import write_markdown_report
from grok_x_lead_monitor.filters import is_valid_candidate
from grok_x_lead_monitor.grok_client import GrokSearchClient
from grok_x_lead_monitor.models import LeadRecord
from grok_x_lead_monitor.query_builder import build_query_pack
from grok_x_lead_monitor.scoring import infer_pain_point_tag, score_candidate, to_intent_score_10
from grok_x_lead_monitor.url_resolver import resolve_original_url


class GrokSearchClientProtocol:
    def search(self, query: str, start_iso: str, end_iso: str):
        raise NotImplementedError


def _merge_dotenv(path: Path, env: dict[str, str]) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in env:
            continue
        env[key] = value.strip().strip('"').strip("'")


def _build_client(settings: Settings, client: GrokSearchClientProtocol | None) -> GrokSearchClientProtocol:
    if client is not None:
        return client
    if not settings.grok_api_key:
        raise ValueError("GROK_API_KEY is required when no client is injected")
    return GrokSearchClient(api_key=settings.grok_api_key, model=settings.grok_model)


def run_pipeline(
    now: datetime,
    env: dict[str, str] | None = None,
    client: GrokSearchClientProtocol | None = None,
):
    if env is None:
        effective_env = dict(os.environ)
        _merge_dotenv(Path.cwd() / ".env", effective_env)
    else:
        effective_env = dict(env)
    settings = Settings.from_env(effective_env)
    client = _build_client(settings, client)
    start, end, label = resolve_window(
        settings.default_window_mode,
        now,
        settings.default_timezone,
        settings.relative_lookback_hours,
    )
    query_specs = build_query_pack(settings.query_pack_version)

    seen_urls: set[str] = set()
    leads: list[LeadRecord] = []
    for query_spec in query_specs:
        try:
            candidates = client.search(query_spec.query, start.isoformat(), end.isoformat()) or []
        except Exception as exc:
            print(f"[WARN] Grok query failed: {query_spec.query} ({exc})", file=sys.stderr)
            continue

        diagnostic_report = diagnose_query_results(
            query=query_spec.query,
            candidates=candidates,
            high_priority_score=settings.high_priority_score,
            min_intent_score=settings.min_intent_score,
        )
        print(format_query_diagnostics(diagnostic_report), file=sys.stderr)

        for candidate in candidates:
            if not is_valid_candidate(candidate):
                continue
            score, _, summary, reason = score_candidate(candidate, high_threshold=settings.high_priority_score)
            if score < settings.min_intent_score:
                continue
            original_url = resolve_original_url(candidate.citations)
            if not original_url or original_url in seen_urls:
                continue
            seen_urls.add(original_url)
            leads.append(
                LeadRecord(
                    username=candidate.username,
                    pain_point_tag=infer_pain_point_tag(candidate.tweet_text),
                    intent_score_10=to_intent_score_10(score),
                    tweet_summary=summary,
                    intent_reason=reason,
                    original_url=original_url,
                    tweet_created_at=candidate.tweet_created_at,
                )
            )

    return write_markdown_report(settings.output_dir, label, leads)


def cli() -> None:
    run_pipeline(now=datetime.now(tz=ZoneInfo("UTC")))


if __name__ == "__main__":
    cli()
