from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from grok_x_lead_monitor.main import run_pipeline
from grok_x_lead_monitor.models import Candidate


class FakeClient:
    def search(self, query: str, start_iso: str, end_iso: str):
        if "plantar" in query:
            return [
                Candidate(
                    username="walker01",
                    tweet_text="After every shift my feet are killing me at work and I need comfortable shoe recommendations asap.",
                    tweet_created_at=datetime(2026, 4, 8, 8, 0, tzinfo=ZoneInfo("UTC")),
                    query_used=query,
                    citations=[{"url": "https://x.com/walker01/status/111111"}],
                )
            ]
        if "standing" in query:
            return [
                Candidate(
                    username="promo_bot",
                    tweet_text="Use code SAVE20 for best shoes #ad #deal",
                    tweet_created_at=datetime(2026, 4, 8, 8, 5, tzinfo=ZoneInfo("UTC")),
                    query_used=query,
                    citations=[{"url": "https://x.com/promo_bot/status/222222"}],
                )
            ]
        return []


def main() -> None:
    output_path = run_pipeline(
        now=datetime(2026, 4, 8, 10, 30, tzinfo=ZoneInfo("Asia/Shanghai")),
        env={"DEFAULT_OUTPUT_DIR": "output/leads"},
        client=FakeClient(),
    )
    print(output_path)


if __name__ == "__main__":
    main()
