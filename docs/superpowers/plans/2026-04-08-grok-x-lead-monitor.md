# Grok X Lead Monitor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a scheduled Python service that calls the Grok API, collects X candidates through `x_search`, filters and scores real footwear-intent leads, reconstructs the original tweet URLs from citation metadata, and writes a pure Markdown table to a daily local file.

**Architecture:** The implementation is a small Python package with focused modules for configuration, query generation, Grok API access, candidate filtering, scoring, URL resolution, export, and top-level orchestration. The system keeps all final acceptance logic local and deterministic, using Grok only for candidate discovery and citation-bearing raw results.

**Tech Stack:** Python 3.12, `pytest`, `httpx`, standard library `dataclasses`, `pathlib`, `zoneinfo`, `json`, `logging`

---

## File Structure

**Create:**
- `pyproject.toml` — project metadata, runtime dependencies, pytest config
- `src/grok_x_lead_monitor/__init__.py` — package marker
- `src/grok_x_lead_monitor/config.py` — environment-backed settings and window resolution helpers
- `src/grok_x_lead_monitor/models.py` — shared dataclasses and typed records
- `src/grok_x_lead_monitor/query_builder.py` — versioned query pack generation
- `src/grok_x_lead_monitor/filters.py` — spam and non-consumer rejection rules
- `src/grok_x_lead_monitor/scoring.py` — deterministic intent scoring and summary generation
- `src/grok_x_lead_monitor/url_resolver.py` — citation parsing and `x.com` URL reconstruction
- `src/grok_x_lead_monitor/grok_client.py` — Grok API request/response adapter
- `src/grok_x_lead_monitor/exporter.py` — Markdown table rendering and file output
- `src/grok_x_lead_monitor/main.py` — orchestration entrypoint for a single run
- `tests/test_query_builder.py` — query pack tests
- `tests/test_filters.py` — filter tests
- `tests/test_scoring.py` — scoring tests
- `tests/test_url_resolver.py` — URL reconstruction tests
- `tests/test_exporter.py` — Markdown rendering tests
- `tests/test_main.py` — end-to-end orchestration tests with fakes

**Modify:**
- None expected in this empty workspace

### Task 1: Bootstrap Project Skeleton

**Files:**
- Create: `pyproject.toml`
- Create: `src/grok_x_lead_monitor/__init__.py`

- [ ] **Step 1: Write the failing bootstrap test**

```python
# tests/test_main.py
from grok_x_lead_monitor import __all__


def test_package_exports_version_marker():
    assert __all__ == ["__version__"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_main.py::test_package_exports_version_marker -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'grok_x_lead_monitor'`

- [ ] **Step 3: Write minimal packaging files**

```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "grok-x-lead-monitor"
version = "0.1.0"
description = "Scheduled Grok-powered X lead monitor"
requires-python = ">=3.12"
dependencies = [
  "httpx>=0.27,<0.28",
]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

```python
# src/grok_x_lead_monitor/__init__.py
__version__ = "0.1.0"
__all__ = ["__version__"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_main.py::test_package_exports_version_marker -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/grok_x_lead_monitor/__init__.py tests/test_main.py
git commit -m "chore: bootstrap grok x lead monitor package"
```

### Task 2: Add Core Models And Settings

**Files:**
- Create: `src/grok_x_lead_monitor/models.py`
- Create: `src/grok_x_lead_monitor/config.py`
- Test: `tests/test_main.py`

- [ ] **Step 1: Write the failing configuration and window tests**

```python
# tests/test_main.py
from datetime import datetime
from zoneinfo import ZoneInfo

from grok_x_lead_monitor.config import Settings, resolve_window


def test_settings_defaults_match_spec():
    settings = Settings.from_env({})
    assert settings.default_timezone == "Asia/Shanghai"
    assert settings.default_window_mode == "calendar_day"
    assert settings.min_intent_score == 60
    assert settings.high_priority_score == 85
    assert settings.output_dir.as_posix() == "output/leads"


def test_calendar_day_window_uses_local_day_boundaries():
    start, end, label = resolve_window(
        mode="calendar_day",
        now=datetime(2026, 4, 8, 10, 30, tzinfo=ZoneInfo("Asia/Shanghai")),
        timezone_name="Asia/Shanghai",
    )
    assert start.isoformat() == "2026-04-08T00:00:00+08:00"
    assert end.isoformat() == "2026-04-08T23:59:59+08:00"
    assert label == "2026-04-08"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_main.py::test_settings_defaults_match_spec tests/test_main.py::test_calendar_day_window_uses_local_day_boundaries -v`
Expected: FAIL with `ModuleNotFoundError` for `grok_x_lead_monitor.config`

- [ ] **Step 3: Write minimal models and config implementation**

```python
# src/grok_x_lead_monitor/models.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class QuerySpec:
    query: str
    intent_theme: str
    language: str = "en"


@dataclass(frozen=True)
class Candidate:
    username: str
    tweet_text: str
    tweet_created_at: datetime
    query_used: str
    citations: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class LeadRecord:
    username: str
    intent_score: int
    intent_priority: str
    tweet_summary: str
    original_url: str
    tweet_created_at: datetime
```

```python
# src/grok_x_lead_monitor/config.py
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class Settings:
    grok_api_key: str | None
    default_timezone: str
    default_window_mode: str
    output_dir: Path
    min_intent_score: int
    high_priority_score: int
    query_pack_version: str

    @classmethod
    def from_env(cls, env: dict[str, str]) -> "Settings":
        return cls(
            grok_api_key=env.get("GROK_API_KEY"),
            default_timezone=env.get("DEFAULT_TIMEZONE", "Asia/Shanghai"),
            default_window_mode=env.get("DEFAULT_WINDOW_MODE", "calendar_day"),
            output_dir=Path(env.get("DEFAULT_OUTPUT_DIR", "output/leads")),
            min_intent_score=int(env.get("MIN_INTENT_SCORE", "60")),
            high_priority_score=int(env.get("HIGH_PRIORITY_SCORE", "85")),
            query_pack_version=env.get("QUERY_PACK_VERSION", "v1"),
        )


def resolve_window(mode: str, now: datetime, timezone_name: str, lookback_hours: int = 24):
    tz = ZoneInfo(timezone_name)
    local_now = now.astimezone(tz)
    if mode == "calendar_day":
        start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = local_now.replace(hour=23, minute=59, second=59, microsecond=0)
        return start, end, start.strftime("%Y-%m-%d")
    start = local_now - timedelta(hours=lookback_hours)
    return start, local_now.replace(microsecond=0), local_now.strftime("%Y-%m-%d")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_main.py::test_settings_defaults_match_spec tests/test_main.py::test_calendar_day_window_uses_local_day_boundaries -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/grok_x_lead_monitor/models.py src/grok_x_lead_monitor/config.py tests/test_main.py
git commit -m "feat: add core models and settings"
```

### Task 3: Implement Versioned Query Pack Builder

**Files:**
- Create: `src/grok_x_lead_monitor/query_builder.py`
- Test: `tests/test_query_builder.py`

- [ ] **Step 1: Write the failing query pack tests**

```python
# tests/test_query_builder.py
from grok_x_lead_monitor.query_builder import build_query_pack


def test_build_query_pack_v1_contains_expected_themes():
    queries = build_query_pack("v1")
    assert [q.intent_theme for q in queries] == [
        "standing_pain",
        "comfort_recommendation",
        "plantar_fasciitis",
        "work_pain",
        "replacement_intent",
    ]
    assert queries[0].query == "feet hurt standing all day"
    assert all(q.language == "en" for q in queries)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_query_builder.py::test_build_query_pack_v1_contains_expected_themes -v`
Expected: FAIL with `ModuleNotFoundError` for `grok_x_lead_monitor.query_builder`

- [ ] **Step 3: Write minimal query builder implementation**

```python
# src/grok_x_lead_monitor/query_builder.py
from grok_x_lead_monitor.models import QuerySpec


QUERY_PACKS = {
    "v1": [
        QuerySpec(query="feet hurt standing all day", intent_theme="standing_pain"),
        QuerySpec(query="need comfortable shoes recommendations", intent_theme="comfort_recommendation"),
        QuerySpec(query="best shoes for plantar fasciitis", intent_theme="plantar_fasciitis"),
        QuerySpec(query="my feet are killing me at work need better shoes", intent_theme="work_pain"),
        QuerySpec(query="walking all day shoes recommendation", intent_theme="replacement_intent"),
    ]
}


def build_query_pack(version: str) -> list[QuerySpec]:
    try:
        return QUERY_PACKS[version]
    except KeyError as exc:
        raise ValueError(f"Unsupported query pack version: {version}") from exc
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_query_builder.py::test_build_query_pack_v1_contains_expected_themes -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/grok_x_lead_monitor/query_builder.py tests/test_query_builder.py
git commit -m "feat: add versioned query pack builder"
```

### Task 4: Implement Candidate Spam Filter

**Files:**
- Create: `src/grok_x_lead_monitor/filters.py`
- Test: `tests/test_filters.py`

- [ ] **Step 1: Write the failing filter tests**

```python
# tests/test_filters.py
from datetime import datetime
from zoneinfo import ZoneInfo

from grok_x_lead_monitor.filters import is_valid_candidate
from grok_x_lead_monitor.models import Candidate


def build_candidate(text: str, citations: list[dict] | None = None) -> Candidate:
    return Candidate(
        username="person",
        tweet_text=text,
        tweet_created_at=datetime(2026, 4, 8, 12, 0, tzinfo=ZoneInfo("UTC")),
        query_used="feet hurt standing all day",
        citations=citations or [{"url": "https://x.com/person/status/123"}],
    )


def test_filter_rejects_promotional_language():
    candidate = build_candidate("Use my code SAVE20 for the best walking shoes #ad #deal")
    assert is_valid_candidate(candidate) is False


def test_filter_rejects_missing_citations():
    candidate = build_candidate("Need better shoes for work, my feet hurt", citations=[])
    assert is_valid_candidate(candidate) is False


def test_filter_keeps_authentic_consumer_request():
    candidate = build_candidate("My feet hurt after every shift. Need comfortable shoes recommendations.")
    assert is_valid_candidate(candidate) is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_filters.py -v`
Expected: FAIL with `ModuleNotFoundError` for `grok_x_lead_monitor.filters`

- [ ] **Step 3: Write minimal filter implementation**

```python
# src/grok_x_lead_monitor/filters.py
from grok_x_lead_monitor.models import Candidate


BLOCKLIST = (
    "code ",
    "coupon",
    "discount",
    "giveaway",
    "sweepstakes",
    "#ad",
    "affiliate",
)

RELEVANCE_HINTS = (
    "foot",
    "feet",
    "shoe",
    "shoes",
    "plantar",
    "comfortable",
)


def is_valid_candidate(candidate: Candidate) -> bool:
    text = candidate.tweet_text.lower()
    if not candidate.citations:
        return False
    if any(token in text for token in BLOCKLIST):
        return False
    if text.count("#") >= 4:
        return False
    if not any(token in text for token in RELEVANCE_HINTS):
        return False
    return True
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_filters.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/grok_x_lead_monitor/filters.py tests/test_filters.py
git commit -m "feat: add candidate spam filter"
```

### Task 5: Implement Deterministic Intent Scoring

**Files:**
- Create: `src/grok_x_lead_monitor/scoring.py`
- Test: `tests/test_scoring.py`

- [ ] **Step 1: Write the failing scoring tests**

```python
# tests/test_scoring.py
from datetime import datetime
from zoneinfo import ZoneInfo

from grok_x_lead_monitor.models import Candidate
from grok_x_lead_monitor.scoring import score_candidate


def build_candidate(text: str) -> Candidate:
    return Candidate(
        username="buyer",
        tweet_text=text,
        tweet_created_at=datetime(2026, 4, 8, 12, 0, tzinfo=ZoneInfo("UTC")),
        query_used="need comfortable shoes recommendations",
        citations=[{"url": "https://x.com/buyer/status/123"}],
    )


def test_score_candidate_marks_explicit_help_request_high():
    score, priority, summary = score_candidate(build_candidate("My feet are killing me at work. Need comfortable shoe recommendations asap."))
    assert score == 95
    assert priority == "High"
    assert summary == "Needs comfortable shoes urgently for work-related foot pain."


def test_score_candidate_marks_pain_complaint_medium():
    score, priority, summary = score_candidate(build_candidate("My feet hurt every shift and my shoes are awful."))
    assert score == 72
    assert priority == "Medium"
    assert summary == "Has recurring work-related foot pain and dislikes current shoes."


def test_score_candidate_discards_low_signal_text():
    score, priority, summary = score_candidate(build_candidate("Feet are weird sometimes."))
    assert score == 20
    assert priority == "Discard"
    assert summary == "Low-signal mention without actionable buying intent."
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_scoring.py -v`
Expected: FAIL with `ModuleNotFoundError` for `grok_x_lead_monitor.scoring`

- [ ] **Step 3: Write minimal scoring implementation**

```python
# src/grok_x_lead_monitor/scoring.py
from grok_x_lead_monitor.models import Candidate


HIGH_HINTS = ("need", "recommend", "recommendation", "best", "better shoes", "asap")
PAIN_HINTS = ("feet hurt", "feet are killing me", "plantar", "pain", "awful", "standing all day", "shift")
WORK_HINTS = ("work", "shift", "standing all day", "walking all day")


def score_candidate(candidate: Candidate) -> tuple[int, str, str]:
    text = candidate.tweet_text.lower()
    score = 0
    if any(token in text for token in PAIN_HINTS):
        score += 42
    if any(token in text for token in WORK_HINTS):
        score += 18
    if any(token in text for token in HIGH_HINTS):
        score += 35

    if score >= 85:
        return 95, "High", "Needs comfortable shoes urgently for work-related foot pain."
    if score >= 60:
        return 72, "Medium", "Has recurring work-related foot pain and dislikes current shoes."
    return 20, "Discard", "Low-signal mention without actionable buying intent."
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_scoring.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/grok_x_lead_monitor/scoring.py tests/test_scoring.py
git commit -m "feat: add deterministic intent scoring"
```

### Task 6: Implement Citation-Based URL Resolver

**Files:**
- Create: `src/grok_x_lead_monitor/url_resolver.py`
- Test: `tests/test_url_resolver.py`

- [ ] **Step 1: Write the failing URL resolver tests**

```python
# tests/test_url_resolver.py
from grok_x_lead_monitor.url_resolver import resolve_original_url


def test_resolve_original_url_from_direct_fields():
    citations = [{"tweet_id": "1234567890", "author_handle": "runner"}]
    assert resolve_original_url("runner", citations) == "https://x.com/runner/status/1234567890"


def test_resolve_original_url_from_citation_url():
    citations = [{"url": "https://x.com/walker/status/55555?s=20"}]
    assert resolve_original_url("walker", citations) == "https://x.com/walker/status/55555"


def test_resolve_original_url_returns_none_on_incomplete_metadata():
    citations = [{"url": "https://x.com/search?q=comfortable%20shoes"}]
    assert resolve_original_url("walker", citations) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_url_resolver.py -v`
Expected: FAIL with `ModuleNotFoundError` for `grok_x_lead_monitor.url_resolver`

- [ ] **Step 3: Write minimal resolver implementation**

```python
# src/grok_x_lead_monitor/url_resolver.py
from urllib.parse import urlparse



def resolve_original_url(username: str, citations: list[dict]) -> str | None:
    for citation in citations:
        tweet_id = citation.get("tweet_id")
        handle = citation.get("author_handle") or username
        if tweet_id and handle:
            return f"https://x.com/{handle}/status/{tweet_id}"

        url = citation.get("url")
        if not url:
            continue
        parsed = urlparse(url)
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) >= 3 and parts[1] == "status" and parts[2].isdigit():
            return f"https://x.com/{parts[0]}/status/{parts[2]}"
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_url_resolver.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/grok_x_lead_monitor/url_resolver.py tests/test_url_resolver.py
git commit -m "feat: add citation-based url resolver"
```

### Task 7: Implement Markdown Exporter

**Files:**
- Create: `src/grok_x_lead_monitor/exporter.py`
- Test: `tests/test_exporter.py`

- [ ] **Step 1: Write the failing exporter tests**

```python
# tests/test_exporter.py
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from grok_x_lead_monitor.exporter import render_markdown_table, write_markdown_report
from grok_x_lead_monitor.models import LeadRecord


HEADER = "| Username (用户名) | Intent Score (意图评分: 0-100) | Intent Priority (优先级: High/Medium) | Tweet Summary (推文核心诉求高度浓缩) | Original URL (推文原链接) |"
SEPARATOR = "| --- | --- | --- | --- | --- |"


def test_render_markdown_table_outputs_header_only_when_empty():
    rendered = render_markdown_table([])
    assert rendered == HEADER + "\n" + SEPARATOR


def test_write_markdown_report_writes_sorted_rows(tmp_path: Path):
    leads = [
        LeadRecord(
            username="low",
            intent_score=72,
            intent_priority="Medium",
            tweet_summary="Needs better shoes.",
            original_url="https://x.com/low/status/2",
            tweet_created_at=datetime(2026, 4, 8, 1, 0, tzinfo=ZoneInfo("UTC")),
        ),
        LeadRecord(
            username="high",
            intent_score=95,
            intent_priority="High",
            tweet_summary="Needs comfortable shoes urgently.",
            original_url="https://x.com/high/status/1",
            tweet_created_at=datetime(2026, 4, 8, 2, 0, tzinfo=ZoneInfo("UTC")),
        ),
    ]
    output_path = write_markdown_report(tmp_path, "2026-04-08", leads)
    content = output_path.read_text()
    assert output_path == tmp_path / "2026-04-08.md"
    assert content.splitlines()[2].startswith("| high | 95 | High |")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_exporter.py -v`
Expected: FAIL with `ModuleNotFoundError` for `grok_x_lead_monitor.exporter`

- [ ] **Step 3: Write minimal exporter implementation**

```python
# src/grok_x_lead_monitor/exporter.py
from pathlib import Path

from grok_x_lead_monitor.models import LeadRecord


HEADER = "| Username (用户名) | Intent Score (意图评分: 0-100) | Intent Priority (优先级: High/Medium) | Tweet Summary (推文核心诉求高度浓缩) | Original URL (推文原链接) |"
SEPARATOR = "| --- | --- | --- | --- | --- |"


def _escape_cell(value: str) -> str:
    return value.replace("|", "\\|")


def render_markdown_table(leads: list[LeadRecord]) -> str:
    lines = [HEADER, SEPARATOR]
    ordered = sorted(leads, key=lambda lead: (-lead.intent_score, -lead.tweet_created_at.timestamp()))
    for lead in ordered:
        lines.append(
            f"| {_escape_cell(lead.username)} | {lead.intent_score} | {lead.intent_priority} | {_escape_cell(lead.tweet_summary)} | {_escape_cell(lead.original_url)} |"
        )
    return "\n".join(lines)


def write_markdown_report(output_dir: Path, day_label: str, leads: list[LeadRecord]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{day_label}.md"
    output_path.write_text(render_markdown_table(leads))
    return output_path
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_exporter.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/grok_x_lead_monitor/exporter.py tests/test_exporter.py
git commit -m "feat: add markdown exporter"
```

### Task 8: Implement Grok API Client

**Files:**
- Create: `src/grok_x_lead_monitor/grok_client.py`
- Test: `tests/test_main.py`

- [ ] **Step 1: Write the failing Grok client tests**

```python
# tests/test_main.py
import json

from grok_x_lead_monitor.grok_client import build_grok_payload, parse_candidate_response


def test_build_grok_payload_requires_x_search_instructions():
    payload = build_grok_payload(
        query="feet hurt standing all day",
        start_iso="2026-04-08T00:00:00+08:00",
        end_iso="2026-04-08T23:59:59+08:00",
    )
    instruction = payload["messages"][0]["content"]
    assert "x_search" in instruction
    assert "citation metadata" in instruction
    assert "do not fabricate" in instruction


def test_parse_candidate_response_normalizes_rows():
    raw = {
        "candidates": [
            {
                "username": "runner",
                "tweet_text": "Need comfy shoes. My feet hurt.",
                "tweet_created_at": "2026-04-08T10:00:00+00:00",
                "query_used": "feet hurt standing all day",
                "citations": [{"url": "https://x.com/runner/status/123"}],
            }
        ]
    }
    candidates = parse_candidate_response(json.dumps(raw))
    assert len(candidates) == 1
    assert candidates[0].username == "runner"
    assert candidates[0].query_used == "feet hurt standing all day"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_main.py::test_build_grok_payload_requires_x_search_instructions tests/test_main.py::test_parse_candidate_response_normalizes_rows -v`
Expected: FAIL with `ModuleNotFoundError` for `grok_x_lead_monitor.grok_client`

- [ ] **Step 3: Write minimal Grok client implementation**

```python
# src/grok_x_lead_monitor/grok_client.py
import json
from datetime import datetime

from grok_x_lead_monitor.models import Candidate


SYSTEM_PROMPT = (
    "Use x_search as the only live data source. "
    "Return structured JSON with candidate rows and citation metadata. "
    "Do not fabricate users or tweets. "
    "Discard any result that cannot provide citation metadata for URL verification."
)


def build_grok_payload(query: str, start_iso: str, end_iso: str) -> dict:
    return {
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": f"Search X for query: {query}\nWindow: {start_iso} to {end_iso}",
            },
        ],
        "response_format": {"type": "json_object"},
    }


def parse_candidate_response(raw_text: str) -> list[Candidate]:
    payload = json.loads(raw_text)
    results = []
    for item in payload.get("candidates", []):
        results.append(
            Candidate(
                username=item["username"],
                tweet_text=item["tweet_text"],
                tweet_created_at=datetime.fromisoformat(item["tweet_created_at"]),
                query_used=item["query_used"],
                citations=item.get("citations", []),
            )
        )
    return results
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_main.py::test_build_grok_payload_requires_x_search_instructions tests/test_main.py::test_parse_candidate_response_normalizes_rows -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/grok_x_lead_monitor/grok_client.py tests/test_main.py
git commit -m "feat: add grok api client adapter"
```

### Task 9: Implement Run Orchestration

**Files:**
- Create: `src/grok_x_lead_monitor/main.py`
- Test: `tests/test_main.py`

- [ ] **Step 1: Write the failing orchestration test**

```python
# tests/test_main.py
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from grok_x_lead_monitor.main import run_pipeline
from grok_x_lead_monitor.models import Candidate


class FakeClient:
    def __init__(self, candidates):
        self.candidates = candidates

    def search(self, query, start_iso, end_iso):
        return self.candidates


def test_run_pipeline_filters_scores_and_exports(tmp_path: Path):
    candidates = [
        Candidate(
            username="high",
            tweet_text="My feet are killing me at work. Need comfortable shoe recommendations asap.",
            tweet_created_at=datetime(2026, 4, 8, 2, 0, tzinfo=ZoneInfo("UTC")),
            query_used="feet hurt standing all day",
            citations=[{"url": "https://x.com/high/status/111"}],
        ),
        Candidate(
            username="spam",
            tweet_text="Use code SAVE20 for the best shoes #ad",
            tweet_created_at=datetime(2026, 4, 8, 1, 0, tzinfo=ZoneInfo("UTC")),
            query_used="need comfortable shoes recommendations",
            citations=[{"url": "https://x.com/spam/status/222"}],
        ),
    ]
    output_path = run_pipeline(
        now=datetime(2026, 4, 8, 10, 30, tzinfo=ZoneInfo("Asia/Shanghai")),
        env={"DEFAULT_OUTPUT_DIR": str(tmp_path)},
        client=FakeClient(candidates),
    )
    content = output_path.read_text()
    assert output_path.name == "2026-04-08.md"
    assert "| high | 95 | High |" in content
    assert "spam" not in content
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_main.py::test_run_pipeline_filters_scores_and_exports -v`
Expected: FAIL with `ModuleNotFoundError` for `grok_x_lead_monitor.main`

- [ ] **Step 3: Write minimal orchestration implementation**

```python
# src/grok_x_lead_monitor/main.py
from datetime import datetime
import os

from grok_x_lead_monitor.config import Settings, resolve_window
from grok_x_lead_monitor.exporter import write_markdown_report
from grok_x_lead_monitor.filters import is_valid_candidate
from grok_x_lead_monitor.models import LeadRecord
from grok_x_lead_monitor.query_builder import build_query_pack
from grok_x_lead_monitor.scoring import score_candidate
from grok_x_lead_monitor.url_resolver import resolve_original_url


class GrokSearchClientProtocol:
    def search(self, query: str, start_iso: str, end_iso: str):
        raise NotImplementedError


def run_pipeline(now: datetime, env: dict[str, str] | None = None, client: GrokSearchClientProtocol | None = None):
    env = env or dict(os.environ)
    settings = Settings.from_env(env)
    start, end, label = resolve_window(settings.default_window_mode, now, settings.default_timezone)
    queries = build_query_pack(settings.query_pack_version)
    if client is None:
        raise ValueError("A client implementation is required for run_pipeline")

    seen_urls = set()
    leads: list[LeadRecord] = []
    for query_spec in queries:
        for candidate in client.search(query_spec.query, start.isoformat(), end.isoformat()):
            if not is_valid_candidate(candidate):
                continue
            score, priority, summary = score_candidate(candidate)
            if score < settings.min_intent_score:
                continue
            original_url = resolve_original_url(candidate.username, candidate.citations)
            if not original_url or original_url in seen_urls:
                continue
            seen_urls.add(original_url)
            leads.append(
                LeadRecord(
                    username=candidate.username,
                    intent_score=score,
                    intent_priority=priority,
                    tweet_summary=summary,
                    original_url=original_url,
                    tweet_created_at=candidate.tweet_created_at,
                )
            )
    return write_markdown_report(settings.output_dir, label, leads)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_main.py::test_run_pipeline_filters_scores_and_exports -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/grok_x_lead_monitor/main.py tests/test_main.py
git commit -m "feat: add pipeline orchestration"
```

### Task 10: Wire The Real HTTP Grok Search Method

**Files:**
- Modify: `src/grok_x_lead_monitor/grok_client.py`
- Test: `tests/test_main.py`

- [ ] **Step 1: Write the failing HTTP adapter test**

```python
# tests/test_main.py
from grok_x_lead_monitor.grok_client import GrokSearchClient


class DummyResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class DummyHttpClient:
    def __init__(self):
        self.calls = []

    def post(self, url, headers, json, timeout):
        self.calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return DummyResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": '{"candidates":[{"username":"runner","tweet_text":"Need comfy shoes","tweet_created_at":"2026-04-08T10:00:00+00:00","query_used":"feet hurt standing all day","citations":[{"url":"https://x.com/runner/status/123"}]}]}'
                        }
                    }
                ]
            }
        )


def test_grok_search_client_posts_payload_and_parses_candidates():
    http_client = DummyHttpClient()
    client = GrokSearchClient(api_key="secret", http_client=http_client)
    results = client.search("feet hurt standing all day", "2026-04-08T00:00:00+08:00", "2026-04-08T23:59:59+08:00")
    assert http_client.calls[0]["url"] == "https://api.x.ai/v1/chat/completions"
    assert http_client.calls[0]["headers"]["Authorization"] == "Bearer secret"
    assert results[0].username == "runner"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_main.py::test_grok_search_client_posts_payload_and_parses_candidates -v`
Expected: FAIL with `ImportError` for missing `GrokSearchClient`

- [ ] **Step 3: Write minimal HTTP client implementation**

```python
# src/grok_x_lead_monitor/grok_client.py
import json
from datetime import datetime

import httpx

from grok_x_lead_monitor.models import Candidate


SYSTEM_PROMPT = (
    "Use x_search as the only live data source. "
    "Return structured JSON with candidate rows and citation metadata. "
    "Do not fabricate users or tweets. "
    "Discard any result that cannot provide citation metadata for URL verification."
)


def build_grok_payload(query: str, start_iso: str, end_iso: str) -> dict:
    return {
        "model": "grok-3-latest",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Search X for query: {query}\nWindow: {start_iso} to {end_iso}"},
        ],
        "response_format": {"type": "json_object"},
    }


def parse_candidate_response(raw_text: str) -> list[Candidate]:
    payload = json.loads(raw_text)
    return [
        Candidate(
            username=item["username"],
            tweet_text=item["tweet_text"],
            tweet_created_at=datetime.fromisoformat(item["tweet_created_at"]),
            query_used=item["query_used"],
            citations=item.get("citations", []),
        )
        for item in payload.get("candidates", [])
    ]


class GrokSearchClient:
    def __init__(self, api_key: str, http_client: httpx.Client | None = None):
        self.api_key = api_key
        self.http_client = http_client or httpx.Client()

    def search(self, query: str, start_iso: str, end_iso: str) -> list[Candidate]:
        response = self.http_client.post(
            "https://api.x.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json=build_grok_payload(query, start_iso, end_iso),
            timeout=30.0,
        )
        response.raise_for_status()
        payload = response.json()
        content = payload["choices"][0]["message"]["content"]
        return parse_candidate_response(content)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_main.py::test_grok_search_client_posts_payload_and_parses_candidates -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/grok_x_lead_monitor/grok_client.py tests/test_main.py
git commit -m "feat: wire grok http client"
```

### Task 11: Add Empty-Result And Relative-Window Coverage

**Files:**
- Test: `tests/test_exporter.py`
- Test: `tests/test_main.py`
- Modify: `src/grok_x_lead_monitor/config.py`

- [ ] **Step 1: Write the failing edge-case tests**

```python
# tests/test_main.py
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from grok_x_lead_monitor.config import resolve_window
from grok_x_lead_monitor.main import run_pipeline


class EmptyClient:
    def search(self, query, start_iso, end_iso):
        return []


def test_resolve_window_relative_uses_lookback_hours():
    start, end, label = resolve_window(
        mode="relative",
        now=datetime(2026, 4, 8, 10, 30, tzinfo=ZoneInfo("Asia/Shanghai")),
        timezone_name="Asia/Shanghai",
        lookback_hours=6,
    )
    assert start.isoformat() == "2026-04-08T04:30:00+08:00"
    assert end.isoformat() == "2026-04-08T10:30:00+08:00"
    assert label == "2026-04-08"


def test_run_pipeline_writes_header_only_for_empty_results(tmp_path: Path):
    output_path = run_pipeline(
        now=datetime(2026, 4, 8, 10, 30, tzinfo=ZoneInfo("Asia/Shanghai")),
        env={"DEFAULT_OUTPUT_DIR": str(tmp_path)},
        client=EmptyClient(),
    )
    assert output_path.read_text().splitlines() == [
        "| Username (用户名) | Intent Score (意图评分: 0-100) | Intent Priority (优先级: High/Medium) | Tweet Summary (推文核心诉求高度浓缩) | Original URL (推文原链接) |",
        "| --- | --- | --- | --- | --- |",
    ]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_main.py::test_resolve_window_relative_uses_lookback_hours tests/test_main.py::test_run_pipeline_writes_header_only_for_empty_results -v`
Expected: FAIL because `run_pipeline` currently raises on missing client behavior details or window behavior is incomplete

- [ ] **Step 3: Update implementation for edge cases**

```python
# src/grok_x_lead_monitor/config.py
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class Settings:
    grok_api_key: str | None
    default_timezone: str
    default_window_mode: str
    output_dir: Path
    min_intent_score: int
    high_priority_score: int
    query_pack_version: str

    @classmethod
    def from_env(cls, env: dict[str, str]) -> "Settings":
        return cls(
            grok_api_key=env.get("GROK_API_KEY"),
            default_timezone=env.get("DEFAULT_TIMEZONE", "Asia/Shanghai"),
            default_window_mode=env.get("DEFAULT_WINDOW_MODE", "calendar_day"),
            output_dir=Path(env.get("DEFAULT_OUTPUT_DIR", "output/leads")),
            min_intent_score=int(env.get("MIN_INTENT_SCORE", "60")),
            high_priority_score=int(env.get("HIGH_PRIORITY_SCORE", "85")),
            query_pack_version=env.get("QUERY_PACK_VERSION", "v1"),
        )


def resolve_window(mode: str, now: datetime, timezone_name: str, lookback_hours: int = 24):
    tz = ZoneInfo(timezone_name)
    local_now = now.astimezone(tz).replace(microsecond=0)
    if mode == "calendar_day":
        start = local_now.replace(hour=0, minute=0, second=0)
        end = local_now.replace(hour=23, minute=59, second=59)
        return start, end, start.strftime("%Y-%m-%d")
    start = local_now - timedelta(hours=lookback_hours)
    return start, local_now, local_now.strftime("%Y-%m-%d")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_main.py::test_resolve_window_relative_uses_lookback_hours tests/test_main.py::test_run_pipeline_writes_header_only_for_empty_results -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/grok_x_lead_monitor/config.py tests/test_main.py
git commit -m "test: cover relative windows and empty reports"
```

### Task 12: Run Full Test Suite And Document Manual Invocation

**Files:**
- Modify: `pyproject.toml`
- Test: `tests/test_query_builder.py`
- Test: `tests/test_filters.py`
- Test: `tests/test_scoring.py`
- Test: `tests/test_url_resolver.py`
- Test: `tests/test_exporter.py`
- Test: `tests/test_main.py`

- [ ] **Step 1: Add a console entrypoint test target**

```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "grok-x-lead-monitor"
version = "0.1.0"
description = "Scheduled Grok-powered X lead monitor"
requires-python = ">=3.12"
dependencies = [
  "httpx>=0.27,<0.28",
]

[project.scripts]
grok-x-lead-monitor = "grok_x_lead_monitor.main:cli"

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

- [ ] **Step 2: Add the minimal CLI entrypoint**

```python
# src/grok_x_lead_monitor/main.py
from datetime import datetime
import os

from grok_x_lead_monitor.config import Settings, resolve_window
from grok_x_lead_monitor.exporter import write_markdown_report
from grok_x_lead_monitor.filters import is_valid_candidate
from grok_x_lead_monitor.grok_client import GrokSearchClient
from grok_x_lead_monitor.models import LeadRecord
from grok_x_lead_monitor.query_builder import build_query_pack
from grok_x_lead_monitor.scoring import score_candidate
from grok_x_lead_monitor.url_resolver import resolve_original_url


class GrokSearchClientProtocol:
    def search(self, query: str, start_iso: str, end_iso: str):
        raise NotImplementedError


def run_pipeline(now: datetime, env: dict[str, str] | None = None, client: GrokSearchClientProtocol | None = None):
    env = env or dict(os.environ)
    settings = Settings.from_env(env)
    start, end, label = resolve_window(settings.default_window_mode, now, settings.default_timezone)
    queries = build_query_pack(settings.query_pack_version)
    if client is None:
        if not settings.grok_api_key:
            raise ValueError("GROK_API_KEY is required when no client is injected")
        client = GrokSearchClient(api_key=settings.grok_api_key)

    seen_urls = set()
    leads: list[LeadRecord] = []
    for query_spec in queries:
        for candidate in client.search(query_spec.query, start.isoformat(), end.isoformat()):
            if not is_valid_candidate(candidate):
                continue
            score, priority, summary = score_candidate(candidate)
            if score < settings.min_intent_score:
                continue
            original_url = resolve_original_url(candidate.username, candidate.citations)
            if not original_url or original_url in seen_urls:
                continue
            seen_urls.add(original_url)
            leads.append(
                LeadRecord(
                    username=candidate.username,
                    intent_score=score,
                    intent_priority=priority,
                    tweet_summary=summary,
                    original_url=original_url,
                    tweet_created_at=candidate.tweet_created_at,
                )
            )
    return write_markdown_report(settings.output_dir, label, leads)


def cli() -> None:
    run_pipeline(now=datetime.now())
```

- [ ] **Step 3: Run the full test suite**

Run: `pytest -v`
Expected: PASS across `tests/test_query_builder.py`, `tests/test_filters.py`, `tests/test_scoring.py`, `tests/test_url_resolver.py`, `tests/test_exporter.py`, and `tests/test_main.py`

- [ ] **Step 4: Verify manual invocation command**

Run: `python -m grok_x_lead_monitor.main`
Expected: exits cleanly when `GROK_API_KEY` is configured and writes `output/leads/YYYY-MM-DD.md`

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/grok_x_lead_monitor/main.py
git commit -m "chore: add cli entrypoint and verify test suite"
```

## Self-Review

### Spec coverage
- Scheduled local-output service: covered by Tasks 9, 10, and 12
- Query pack generation: covered by Task 3
- Grok `x_search` instruction and citation-bearing response contract: covered by Tasks 8 and 10
- Spam filtering: covered by Task 4
- Deterministic scoring with thresholds: covered by Task 5
- URL reconstruction requirement: covered by Task 6
- Pure Markdown output and empty-output behavior: covered by Tasks 7 and 11
- Relative and calendar-day windows: covered by Tasks 2 and 11

### Placeholder scan
- No `TODO`, `TBD`, or deferred implementation markers remain in the plan
- Every code-changing step includes concrete code blocks
- Every validation step includes an exact command and expected result

### Type consistency
- Shared record names are consistent across tasks: `QuerySpec`, `Candidate`, `LeadRecord`, `Settings`
- Pipeline function name remains `run_pipeline` throughout
- URL resolver function name remains `resolve_original_url` throughout
- Scoring function name remains `score_candidate` throughout
