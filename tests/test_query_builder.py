from grok_x_lead_monitor.query_builder import build_query_pack


def test_build_query_pack_v1_contains_expected_themes():
    queries = build_query_pack("v1")
    assert [q.intent_theme for q in queries] == [
        "standing_pain",
        "comfort_recommendation",
        "plantar_fasciitis",
        "wide_feet",
        "narrow_fit",
        "work_pain",
        "replacement_intent",
    ]
    assert queries[0].query == "feet hurt standing all day"
    assert any(query.query == "best shoes for wide feet foot pain" for query in queries)
    assert any(query.query == "need narrow fit shoes for foot pain" for query in queries)
    assert all(q.language == "en" for q in queries)
