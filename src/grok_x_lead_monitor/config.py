from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Mapping
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class Settings:
    grok_api_key: str | None
    grok_model: str
    default_timezone: str
    default_window_mode: str
    relative_lookback_hours: int
    output_dir: Path
    raw_output_dir: Path
    grok_request_timeout_seconds: int
    min_intent_score: int
    high_priority_score: int
    query_pack_version: str

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> "Settings":
        output_dir = Path(env.get("DEFAULT_OUTPUT_DIR", "output/leads"))
        raw_output_dir = Path(env.get("DEFAULT_RAW_OUTPUT_DIR", str(output_dir.parent / "raw_candidates")))
        return cls(
            grok_api_key=env.get("GROK_API_KEY"),
            grok_model=env.get("GROK_MODEL", "grok-4-1-fast-reasoning"),
            default_timezone=env.get("DEFAULT_TIMEZONE", "Asia/Shanghai"),
            default_window_mode=env.get("DEFAULT_WINDOW_MODE", "relative"),
            relative_lookback_hours=int(env.get("RELATIVE_LOOKBACK_HOURS", "72")),
            output_dir=output_dir,
            raw_output_dir=raw_output_dir,
            grok_request_timeout_seconds=int(env.get("GROK_REQUEST_TIMEOUT_SECONDS", "90")),
            min_intent_score=int(env.get("MIN_INTENT_SCORE", "40")),
            high_priority_score=int(env.get("HIGH_PRIORITY_SCORE", "85")),
            query_pack_version=env.get("QUERY_PACK_VERSION", "v1"),
        )


def resolve_window(
    mode: str,
    now: datetime,
    timezone_name: str,
    lookback_hours: int = 24,
) -> tuple[datetime, datetime, str]:
    tz = ZoneInfo(timezone_name)
    local_now = now.astimezone(tz).replace(microsecond=0)

    if mode == "calendar_day":
        start = local_now.replace(hour=0, minute=0, second=0)
        end = local_now.replace(hour=23, minute=59, second=59)
        return start, end, start.strftime("%Y-%m-%d")
    if mode == "relative":
        start = local_now - timedelta(hours=lookback_hours)
        return start, local_now, local_now.strftime("%Y-%m-%d")
    raise ValueError(f"Unsupported window mode: {mode}")
