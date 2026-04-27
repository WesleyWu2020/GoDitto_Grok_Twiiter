import json
from pathlib import Path

from grok_x_lead_monitor.leaf_filter import classify_leaf_row, export_leaf_filter_json


def test_classify_leaf_row_drops_observer_commentary():
    result = classify_leaf_row(
        {
            "Platform": "x",
            "Posted Date": "2026-04-21T23:32:27+00:00",
            "Title": "",
            "Content": "My feet hurt looking at her... 👠",
            "Source": "Leslies_Logic",
            "Post URL": "https://x.com/i/status/1",
        }
    )

    assert result["decision"] == "drop"
    assert result["reason"] == "observer_commentary"


def test_classify_leaf_row_drops_non_shoe_medical_chatter():
    result = classify_leaf_row(
        {
            "Platform": "x",
            "Posted Date": "2026-04-16T05:47:37+00:00",
            "Title": "",
            "Content": "I think I definitely have plantar fasciitis. My foot hurts so bad.",
            "Source": "shrimpsquiggles",
            "Post URL": "https://x.com/i/status/2",
        }
    )

    assert result["decision"] == "drop"
    assert result["reason"] == "medical_without_shoe_intent"


def test_classify_leaf_row_keeps_explicit_shoe_need():
    result = classify_leaf_row(
        {
            "Platform": "x",
            "Posted Date": "2026-04-16T14:46:04+00:00",
            "Title": "",
            "Content": "Where are we getting cheap ish summer sandals that are comfy and wide toe box friendly?",
            "Source": "agreatdayinnc",
            "Post URL": "https://x.com/i/status/3",
        }
    )

    assert result["decision"] == "keep"
    assert result["reason"] == "default_keep"


def test_export_leaf_filter_json_dedupes_and_writes_summary(tmp_path: Path):
    input_path = tmp_path / "input.csv"
    input_path.write_text(
        "\n".join(
            [
                "Platform,Posted Date,Title,Content,Source,Post URL",
                'x,2026-04-16T14:46:04+00:00,,"Where are we getting cheap ish summer sandals that are comfy and wide toe box friendly?",agreatdayinnc,https://x.com/i/status/3',
                'x,2026-04-16T14:46:04+00:00,,"Where are we getting cheap ish summer sandals that are comfy and wide toe box friendly?",agreatdayinnc,https://x.com/i/status/3',
                'x,2026-04-16T05:47:37+00:00,,"I think I definitely have plantar fasciitis. My foot hurts so bad.",shrimpsquiggles,https://x.com/i/status/2',
            ]
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "filtered.json"

    export_leaf_filter_json(input_path, output_path)

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["summary"] == {
        "total_rows": 3,
        "kept_rows": 1,
        "dropped_rows": 2,
        "duplicate_rows": 1,
    }
    assert payload["records"][0]["decision"] == "keep"
    assert payload["records"][1]["reason"] == "duplicate_post_url"

