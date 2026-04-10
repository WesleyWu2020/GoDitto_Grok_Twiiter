from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from pprint import pprint
from zoneinfo import ZoneInfo

from grok_x_lead_monitor.config import Settings, resolve_window
from grok_x_lead_monitor.diagnostics import diagnose_query_results
from grok_x_lead_monitor.grok_client import GrokSearchClient
from grok_x_lead_monitor.query_builder import build_query_pack


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


def main() -> None:
    env = dict(os.environ)
    _merge_dotenv(Path.cwd() / ".env", env)
    settings = Settings.from_env(env)
    client = GrokSearchClient(api_key=settings.grok_api_key or "")
    start, end, label = resolve_window(
        settings.default_window_mode,
        datetime.now(tz=ZoneInfo("UTC")),
        settings.default_timezone,
        settings.relative_lookback_hours,
    )

    print("WINDOW", start.isoformat(), end.isoformat(), label)
    for query_spec in build_query_pack(settings.query_pack_version):
        print("\nQUERY", query_spec.query)
        try:
            candidates = client.search(query_spec.query, start.isoformat(), end.isoformat()) or []
        except Exception as exc:
            print("ERROR", repr(exc))
            continue
        pprint(
            diagnose_query_results(
                query=query_spec.query,
                candidates=candidates,
                high_priority_score=settings.high_priority_score,
                min_intent_score=settings.min_intent_score,
            ),
            sort_dicts=False,
        )


if __name__ == "__main__":
    main()
