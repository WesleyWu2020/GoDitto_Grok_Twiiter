import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from grok_x_lead_monitor.config import Settings, resolve_window
from grok_x_lead_monitor.grok_client import GrokSearchClient, build_grok_payload, parse_candidate_response
from grok_x_lead_monitor.main import cli, run_pipeline
from grok_x_lead_monitor.models import Candidate


def test_settings_defaults_match_spec():
    settings = Settings.from_env({})
    assert settings.grok_model == "grok-4-1-fast-reasoning"
    assert settings.default_timezone == "Asia/Shanghai"
    assert settings.default_window_mode == "relative"
    assert settings.relative_lookback_hours == 168
    assert settings.min_intent_score == 60
    assert settings.high_priority_score == 85
    assert settings.output_dir.as_posix() == "output/leads"
    assert settings.query_pack_version == "v1"


def test_calendar_day_window_uses_local_day_boundaries():
    start, end, label = resolve_window(
        mode="calendar_day",
        now=datetime(2026, 4, 8, 10, 30, tzinfo=ZoneInfo("Asia/Shanghai")),
        timezone_name="Asia/Shanghai",
    )
    assert start.isoformat() == "2026-04-08T00:00:00+08:00"
    assert end.isoformat() == "2026-04-08T23:59:59+08:00"
    assert label == "2026-04-08"


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


def test_settings_reads_relative_lookback_hours_from_env():
    settings = Settings.from_env({"RELATIVE_LOOKBACK_HOURS": "12"})
    assert settings.relative_lookback_hours == 12


def test_settings_reads_grok_model_from_env():
    settings = Settings.from_env({"GROK_MODEL": "grok-4.20-reasoning"})
    assert settings.grok_model == "grok-4.20-reasoning"


def test_run_pipeline_uses_relative_lookback_hours_from_env():
    class WindowClient:
        def __init__(self):
            self.calls = []

        def search(self, query, start_iso, end_iso):
            self.calls.append((query, start_iso, end_iso))
            return []

    client = WindowClient()
    run_pipeline(
        now=datetime(2026, 4, 8, 10, 30, tzinfo=ZoneInfo("Asia/Shanghai")),
        env={"DEFAULT_WINDOW_MODE": "relative", "RELATIVE_LOOKBACK_HOURS": "6"},
        client=client,
    )
    assert client.calls
    assert client.calls[0][1] == "2026-04-08T04:30:00+08:00"
    assert client.calls[0][2] == "2026-04-08T10:30:00+08:00"


def test_build_grok_payload_requires_x_search_instructions():
    payload = build_grok_payload(
        query="feet hurt standing all day",
        start_iso="2026-04-08T00:00:00+08:00",
        end_iso="2026-04-08T23:59:59+08:00",
    )
    assert payload["model"] == "grok-4-1-fast-reasoning"
    instruction = payload["input"][0]["content"]
    assert "x_search" in instruction
    assert "citation metadata" in instruction
    assert "do not fabricate" in instruction.lower()
    assert "promotional links" in instruction.lower()
    assert "bot posts" in instruction.lower()
    assert "animal paws" in instruction.lower()
    assert payload["tools"][0]["type"] == "x_search"
    assert payload["tools"][0]["from_date"] == "2026-04-08"
    assert payload["tools"][0]["to_date"] == "2026-04-08"


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


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"output": []},
        {"output": [{"type": "message"}]},
        {"output": [{"type": "message", "content": []}]},
        {"output": [{"type": "message", "content": [{"type": "output_text", "text": ""}]}]},
        {"output_text": "not json"},
    ],
)
def test_grok_search_client_handles_malformed_response_shapes(payload):
    class MalformedResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return payload

    class MalformedHttpClient:
        def post(self, url, headers, json, timeout):
            return MalformedResponse()

    client = GrokSearchClient(api_key="secret", http_client=MalformedHttpClient())
    results = client.search(
        "feet hurt standing all day",
        "2026-04-08T00:00:00+08:00",
        "2026-04-08T23:59:59+08:00",
    )
    assert results == []


def test_parse_candidate_response_skips_malformed_rows():
    raw = {
        "candidates": [
            {
                "username": "runner",
                "tweet_text": "Need comfy shoes. My feet hurt.",
                "tweet_created_at": "2026-04-08T10:00:00+00:00",
                "query_used": "feet hurt standing all day",
                "citations": [{"url": "https://x.com/runner/status/123"}],
            },
            {
                "username": "missing_timestamp",
                "tweet_text": "Need comfy shoes. My feet hurt.",
                "query_used": "feet hurt standing all day",
                "citations": [{"url": "https://x.com/missing_timestamp/status/124"}],
            },
            "not-a-dict",
            {
                "username": "bad_timestamp",
                "tweet_text": "Need comfy shoes. My feet hurt.",
                "tweet_created_at": "not-a-timestamp",
                "query_used": "feet hurt standing all day",
                "citations": [{"url": "https://x.com/bad_timestamp/status/125"}],
            },
        ]
    }
    candidates = parse_candidate_response(json.dumps(raw))
    assert [candidate.username for candidate in candidates] == ["runner"]


def test_parse_candidate_response_backfills_citation_from_url_or_tweet_id():
    raw = {
        "candidates": [
            {
                "username": "runner_url",
                "tweet_text": "Need comfy shoes. My feet hurt.",
                "tweet_created_at": "2026-04-08T10:00:00+00:00",
                "query_used": "feet hurt standing all day",
                "original_url": "https://x.com/runner_url/status/123",
            },
            {
                "username": "runner_id",
                "tweet_text": "Need wide shoes for plantar fasciitis.",
                "tweet_created_at": "2026-04-08T11:00:00+00:00",
                "query_used": "best shoes for plantar fasciitis",
                "tweet_id": "456",
                "author_handle": "runner_id",
            },
        ]
    }
    candidates = parse_candidate_response(raw)
    assert candidates[0].citations[0]["url"] == "https://x.com/runner_url/status/123"
    assert candidates[1].citations[0]["tweet_id"] == "456"
    assert candidates[1].citations[0]["author_handle"] == "runner_id"


def test_parse_candidate_response_supports_rfc_1123_datetime():
    raw = {
        "candidates": [
            {
                "username": "runner_time",
                "tweet_text": "Need better shoes, my feet hurt.",
                "tweet_created_at": "Sun, 05 Apr 2026 17:31:36 GMT",
                "query_used": "feet hurt standing all day",
                "citations": [{"url": "https://x.com/runner_time/status/999"}],
            }
        ]
    }
    candidates = parse_candidate_response(raw)
    assert len(candidates) == 1
    assert candidates[0].tweet_created_at.isoformat() == "2026-04-05T17:31:36+00:00"


def test_parse_candidate_response_maps_post_tokens_with_annotation_lookup():
    raw = {
        "candidates": [
            {
                "username": "runner_post_token",
                "tweet_text": "Need better shoes, my feet hurt.",
                "tweet_created_at": "2026-04-08T10:00:00+00:00",
                "query_used": "feet hurt standing all day",
                "citations": ["post:1"],
            }
        ]
    }
    candidates = parse_candidate_response(raw, annotation_lookup={"post:1": "https://x.com/runner/status/321"})
    assert len(candidates) == 1
    assert candidates[0].citations[0]["url"] == "https://x.com/runner/status/321"


class FakeClient:
    def __init__(self, candidates):
        self.candidates = candidates
        self.calls: list[tuple[str, str, str]] = []

    def search(self, query, start_iso, end_iso):
        self.calls.append((query, start_iso, end_iso))
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
    assert "| @high |" in content
    assert "| Foot Pain |" in content
    assert "| 10 |" in content
    assert "explicit recommendation request" in content
    assert "spam" not in content


def test_run_pipeline_emits_query_diagnostics_to_stderr(tmp_path: Path, capsys):
    class DiagnosticClient:
        def search(self, query, start_iso, end_iso):
            if query == "feet hurt standing all day":
                return [
                    Candidate(
                        username="strong",
                        tweet_text="My plantar fasciitis is brutal after every shift and I need comfortable shoe recommendations asap.",
                        tweet_created_at=datetime(2026, 4, 8, 2, 0, tzinfo=ZoneInfo("UTC")),
                        query_used=query,
                        citations=[{"url": "https://x.com/strong/status/111"}],
                    ),
                    Candidate(
                        username="weak",
                        tweet_text="Need shoes because plantar fasciitis is annoying.",
                        tweet_created_at=datetime(2026, 4, 8, 3, 0, tzinfo=ZoneInfo("UTC")),
                        query_used=query,
                        citations=[{"url": "https://x.com/weak/status/222"}],
                    ),
                    Candidate(
                        username="dup",
                        tweet_text="My plantar fasciitis is brutal after every shift and I need comfortable shoe recommendations asap.",
                        tweet_created_at=datetime(2026, 4, 8, 4, 0, tzinfo=ZoneInfo("UTC")),
                        query_used=query,
                        citations=[{"url": "https://x.com/strong/status/111"}],
                    ),
                ]
            return []

    run_pipeline(
        now=datetime(2026, 4, 8, 10, 30, tzinfo=ZoneInfo("Asia/Shanghai")),
        env={"DEFAULT_OUTPUT_DIR": str(tmp_path)},
        client=DiagnosticClient(),
    )

    captured = capsys.readouterr()
    assert (
        "[DIAG] Query='feet hurt standing all day' raw=3 valid=2 passing_score=2 unique_url=1"
        in captured.err
    )
    assert "sample@strong filters=True score=95 passes_score=True deduped=False" in captured.err
    assert "sample@weak filters=False score=65 passes_score=False deduped=False" in captured.err
    assert "sample@dup filters=True score=95 passes_score=True deduped=True" in captured.err


def test_run_pipeline_continues_when_one_query_fails(tmp_path: Path):
    class PartiallyFailingClient:
        def __init__(self):
            self.calls = []

        def search(self, query, start_iso, end_iso):
            self.calls.append(query)
            if query == "need comfortable shoes recommendations":
                raise RuntimeError("boom")
            if query == "feet hurt standing all day":
                return [
                    Candidate(
                        username="survivor",
                        tweet_text="My feet hurt and I need comfortable shoes recommendations asap for work.",
                        tweet_created_at=datetime(2026, 4, 8, 2, 0, tzinfo=ZoneInfo("UTC")),
                        query_used=query,
                        citations=[{"url": "https://x.com/survivor/status/333"}],
                    )
                ]
            return []

    output_path = run_pipeline(
        now=datetime(2026, 4, 8, 10, 30, tzinfo=ZoneInfo("Asia/Shanghai")),
        env={"DEFAULT_OUTPUT_DIR": str(tmp_path)},
        client=PartiallyFailingClient(),
    )
    content = output_path.read_text()
    assert "survivor" in content
    assert output_path.exists()


def test_run_pipeline_writes_header_only_for_empty_results(tmp_path: Path):
    class EmptyClient:
        def search(self, query, start_iso, end_iso):
            return []

    output_path = run_pipeline(
        now=datetime(2026, 4, 8, 10, 30, tzinfo=ZoneInfo("Asia/Shanghai")),
        env={"DEFAULT_OUTPUT_DIR": str(tmp_path)},
        client=EmptyClient(),
    )
    assert output_path.read_text().splitlines() == [
        "| User Handle (@username) | Tweet Content Summary | Pain Point Tag | Intent Score (1-10) | Intent Reason | Exact Tweet URL |",
        "| --- | --- | --- | --- | --- | --- |",
    ]


def test_run_pipeline_loads_dotenv_when_env_not_injected(tmp_path: Path, monkeypatch):
    class EmptyClient:
        def search(self, query, start_iso, end_iso):
            return []

    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text("DEFAULT_OUTPUT_DIR=custom_output\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DEFAULT_OUTPUT_DIR", raising=False)

    output_path = run_pipeline(
        now=datetime(2026, 4, 8, 10, 30, tzinfo=ZoneInfo("Asia/Shanghai")),
        env=None,
        client=EmptyClient(),
    )

    assert output_path.as_posix() == "custom_output/2026-04-08.md"


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
                "output_text": '{"candidates":[{"username":"runner","tweet_text":"Need comfy shoes","tweet_created_at":"2026-04-08T10:00:00+00:00","query_used":"feet hurt standing all day","citations":[{"url":"https://x.com/runner/status/123"}]}]}'
            }
        )


def test_grok_search_client_posts_payload_and_parses_candidates():
    http_client = DummyHttpClient()
    client = GrokSearchClient(api_key="secret", http_client=http_client)
    results = client.search(
        "feet hurt standing all day",
        "2026-04-08T00:00:00+08:00",
        "2026-04-08T23:59:59+08:00",
    )
    assert http_client.calls[0]["url"] == "https://api.x.ai/v1/responses"
    assert http_client.calls[0]["headers"]["Authorization"] == "Bearer secret"
    assert results[0].username == "runner"


def test_grok_search_client_retries_remote_disconnect_once():
    class FlakyHttpClient:
        def __init__(self):
            self.calls = 0

        def post(self, url, headers, json, timeout):
            self.calls += 1
            if self.calls == 1:
                import httpx

                raise httpx.RemoteProtocolError("Server disconnected without sending a response.")
            return DummyResponse(
                {
                    "output_text": '{"candidates":[{"username":"runner","tweet_text":"Need comfy shoes","tweet_created_at":"2026-04-08T10:00:00+00:00","query_used":"feet hurt standing all day","citations":[{"url":"https://x.com/runner/status/123"}]}]}'
                }
            )

    client = GrokSearchClient(api_key="secret", http_client=FlakyHttpClient())
    results = client.search(
        "feet hurt standing all day",
        "2026-04-08T00:00:00+08:00",
        "2026-04-08T23:59:59+08:00",
    )
    assert len(results) == 1
    assert results[0].username == "runner"


def test_cli_uses_env_and_fails_without_api_key(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("GROK_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    try:
        cli()
    except ValueError as exc:
        assert "GROK_API_KEY" in str(exc)
    else:
        raise AssertionError("cli() should require GROK_API_KEY when no client is injected")
