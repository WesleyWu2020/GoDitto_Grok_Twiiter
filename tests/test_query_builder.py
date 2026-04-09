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

