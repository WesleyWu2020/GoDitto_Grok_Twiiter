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
        "extra_wide_fit",
        "bunions",
        "diabetic_footwear",
        "swollen_feet",
        "slip_resistant_work",
    ]
    assert queries[0].query == "feet hurt standing all day"
    assert any(query.query == "best shoes for wide feet foot pain" for query in queries)
    assert any(query.query == "need narrow fit shoes for foot pain" for query in queries)
    assert all(q.language == "en" for q in queries)


def test_build_query_pack_v1_contains_fitville_recall_themes():
    queries = build_query_pack("v1")
    themes = [q.intent_theme for q in queries]
    assert "extra_wide_fit" in themes
    assert "bunions" in themes
    assert "diabetic_footwear" in themes
    assert "swollen_feet" in themes
    assert "slip_resistant_work" in themes


def test_build_query_pack_v1_contains_fitville_queries():
    queries = build_query_pack("v1")
    assert any(q.query == "best extra wide shoes for foot pain" for q in queries)
    assert any(q.query == "wide toe box shoes for bunions" for q in queries)
    assert any(q.query == "diabetic shoes recommendations" for q in queries)
    assert any(q.query == "non slip work shoes foot pain" for q in queries)
