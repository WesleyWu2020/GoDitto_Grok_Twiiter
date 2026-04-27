# FitVille Recall Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand recall for FitVille-aligned lead segments across query coverage, hard-filter vocabulary, and downstream scoring while preserving existing anti-spam guardrails.

**Architecture:** Keep the current pipeline structure intact. Broaden candidate intake in `query_builder.py`, make conservative vocabulary-only acceptance changes in `filters.py`, and add explicit FitVille-fit scoring signals plus regression coverage in `tests/`.

**Tech Stack:** Python 3, pytest, dataclasses, rule-based text heuristics

---

## File Structure

- Modify: `src/grok_x_lead_monitor/query_builder.py`
  Adds FitVille-aligned query themes for width, medical, swelling, and work-shoe segments.
- Modify: `src/grok_x_lead_monitor/filters.py`
  Expands relevance and pain/fit hint vocabularies without weakening promo or commentary blocking.
- Modify: `src/grok_x_lead_monitor/scoring.py`
  Adds explicit FitVille-fit scoring signals and combination bonuses.
- Modify: `tests/test_query_builder.py`
  Verifies the expanded query pack and specific new search strings.
- Modify: `tests/test_filters.py`
  Verifies candidate acceptance for new FitVille segments and rejection of noisy false positives.
- Modify: `tests/test_scoring.py`
  Verifies score uplift for wide-fit, bunion, diabetic/swelling, and work-shoe scenarios.

### Task 1: Expand FitVille Query Coverage

**Files:**
- Modify: `src/grok_x_lead_monitor/query_builder.py`
- Test: `tests/test_query_builder.py`

- [ ] **Step 1: Write the failing query-pack tests**

```python
from grok_x_lead_monitor.query_builder import build_query_pack


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_query_builder.py::test_build_query_pack_v1_contains_fitville_recall_themes tests/test_query_builder.py::test_build_query_pack_v1_contains_fitville_queries -v`
Expected: FAIL because the new themes and queries do not exist in `QUERY_PACKS["v1"]`.

- [ ] **Step 3: Write the minimal query expansion**

```python
QUERY_PACKS: dict[str, list[QuerySpec]] = {
    "v1": [
        QuerySpec(query="feet hurt standing all day", intent_theme="standing_pain"),
        QuerySpec(query="need comfortable shoes recommendations", intent_theme="comfort_recommendation"),
        QuerySpec(query="best shoes for plantar fasciitis", intent_theme="plantar_fasciitis"),
        QuerySpec(query="best shoes for wide feet foot pain", intent_theme="wide_feet"),
        QuerySpec(query="need narrow fit shoes for foot pain", intent_theme="narrow_fit"),
        QuerySpec(query="my feet are killing me at work need better shoes", intent_theme="work_pain"),
        QuerySpec(query="walking all day shoes recommendation", intent_theme="replacement_intent"),
        QuerySpec(query="best extra wide shoes for foot pain", intent_theme="extra_wide_fit"),
        QuerySpec(query="wide toe box shoes for bunions", intent_theme="bunions"),
        QuerySpec(query="diabetic shoes recommendations", intent_theme="diabetic_footwear"),
        QuerySpec(query="swollen feet shoes", intent_theme="swollen_feet"),
        QuerySpec(query="non slip work shoes foot pain", intent_theme="slip_resistant_work"),
    ]
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_query_builder.py -v`
Expected: PASS with the original and new query-pack assertions succeeding.

- [ ] **Step 5: Commit**

```bash
git add src/grok_x_lead_monitor/query_builder.py tests/test_query_builder.py
git commit -m "feat: expand FitVille recall queries"
```

### Task 2: Widen Filter Vocabulary Without Weakening Guardrails

**Files:**
- Modify: `src/grok_x_lead_monitor/filters.py`
- Test: `tests/test_filters.py`

- [ ] **Step 1: Write the failing filter tests**

```python
def test_filter_keeps_bunion_request():
    candidate = build_candidate("What shoes help bunions? Need a wide toe box because my toes are cramped.")
    assert is_valid_candidate(candidate) is True


def test_filter_keeps_diabetic_or_swelling_need():
    candidate = build_candidate("Need diabetic shoes for swollen feet and foot swelling after work.")
    assert is_valid_candidate(candidate) is True


def test_filter_keeps_slip_resistant_work_need():
    candidate = build_candidate("Need non slip work shoes for kitchen shifts because my feet hurt standing all day.")
    assert is_valid_candidate(candidate) is True


def test_filter_rejects_generic_medical_commentary_without_buyer_signal():
    candidate = build_candidate("Article: diabetic foot swelling is rising and people are talking about it.")
    assert is_valid_candidate(candidate) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_filters.py::test_filter_keeps_bunion_request tests/test_filters.py::test_filter_keeps_diabetic_or_swelling_need tests/test_filters.py::test_filter_keeps_slip_resistant_work_need tests/test_filters.py::test_filter_rejects_generic_medical_commentary_without_buyer_signal -v`
Expected: At least the acceptance tests FAIL because the current hint lists do not recognize `bunion`, `swollen feet`, `diabetic shoes`, or `non slip` as strong relevance markers.

- [ ] **Step 3: Write the minimal filter expansion**

```python
PAIN_OR_FIT_HINTS = (
    " pain",
    " hurts",
    " aching",
    " sore",
    " blister",
    " plantar",
    " wide feet",
    " wide foot",
    " extra wide",
    " narrow feet",
    " narrow fit",
    " bunion",
    " bunions",
    " bunion pain",
    " swollen feet",
    " foot swelling",
    " edema",
    " toes cramped",
    " toe pain",
    " high instep",
    " flat feet",
)

RELEVANCE_HINTS = (
    "foot",
    "feet",
    "shoe",
    "shoes",
    "plantar",
    "wide feet",
    "wide foot",
    "extra wide",
    "narrow fit",
    "narrow feet",
    "comfortable",
    "walking all day",
    "standing all day",
    "better shoes",
    "bunion",
    "bunions",
    "diabetic",
    "swollen feet",
    "swelling",
    "edema",
    "flat feet",
    "arch support",
    "wide toe box",
    "4e",
    "6e",
    "high instep",
    "non slip",
    "slip resistant",
    "steel toe",
)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_filters.py -v`
Expected: PASS with the new FitVille-aligned acceptance cases and prior spam/commentary rejections intact.

- [ ] **Step 5: Commit**

```bash
git add src/grok_x_lead_monitor/filters.py tests/test_filters.py
git commit -m "feat: widen FitVille filter vocabulary"
```

### Task 3: Add FitVille-Fit Scoring Signals

**Files:**
- Modify: `src/grok_x_lead_monitor/scoring.py`
- Test: `tests/test_scoring.py`

- [ ] **Step 1: Write the failing scoring tests**

```python
def test_score_candidate_scores_bunion_request_as_fitville_lead():
    score, priority, summary, reason = score_candidate(
        build_candidate("What shoes help bunions? Need a wide toe box and better support for walking all day.")
    )
    assert score >= 70
    assert "bunion" in reason.lower()


def test_score_candidate_scores_diabetic_swelling_request_above_threshold():
    score, priority, summary, reason = score_candidate(
        build_candidate("Need diabetic shoes for swollen feet because my current shoes are not helping.")
    )
    assert score >= 60
    assert "diabetic" in reason.lower() or "swollen" in reason.lower()


def test_score_candidate_scores_slip_resistant_work_need_as_fitville_signal():
    score, priority, summary, reason = score_candidate(
        build_candidate("Need non slip work shoes for kitchen shifts. My feet hurt standing all day.")
    )
    assert score >= 70
    assert "standing all day" in reason.lower() or "work" in reason.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_scoring.py::test_score_candidate_scores_bunion_request_as_fitville_lead tests/test_scoring.py::test_score_candidate_scores_diabetic_swelling_request_above_threshold tests/test_scoring.py::test_score_candidate_scores_slip_resistant_work_need_as_fitville_signal -v`
Expected: FAIL because the current scorer has no explicit `bunion`, `diabetic`, `swollen feet`, or `non slip` handling.

- [ ] **Step 3: Write the minimal scoring expansion**

```python
    target_condition_signals = (
        ("plantar fasciitis", ("plantar fasciitis", "plantar"), 20),
        ("wide feet", ("wide feet", "wide foot", "extra wide", "2e", "4e", "6e", "wide toe box"), 20),
        ("narrow fit", ("narrow feet", "narrow foot", "narrow fit"), 20),
        ("standing all day", ("standing all day", "all day standing", "every shift"), 20),
        ("walking all day", ("walking all day", "walk all day"), 15),
        ("bunions", ("bunion", "bunions", "toe pain", "toes cramped"), 20),
        ("flat feet", ("flat feet", "arch support"), 15),
        ("diabetic / swelling", ("diabetic", "diabetic shoes", "swollen feet", "foot swelling", "edema"), 20),
        ("work footwear", ("non slip", "slip resistant", "oil resistant", "steel toe"), 15),
        ("high instep", ("high instep",), 15),
    )

    explicit_buying_intent = _text_has_any(
        text,
        (
            "need comfortable shoes recommendations",
            "need comfortable shoe recommendations",
            "recommend shoes",
            "recommendations",
            "recommendation",
            "need better shoes",
            "best shoes",
            "best walking shoes",
            "looking for shoes",
            "looking for wide shoes",
            "need shoes",
            "need extra wide shoes",
            "need work shoes",
            "need diabetic shoes",
            "what shoes help",
            "anyone have suggestions",
            "anyone have recs",
            "what are some good",
            "what shoes should i",
            "wanting to try",
            "would help or hinder",
            "would help",
        ),
    )
```

Add one combination block below the existing synergy rules:

```python
    if _text_has_any(text, ("diabetic", "swollen feet", "foot swelling", "edema")) and explicit_buying_intent:
        score += 10
        reasons.append("medical footwear need with buying intent")
    if _text_has_any(text, ("wide feet", "extra wide", "4e", "6e", "wide toe box")) and _text_has_any(
        text, ("non slip", "slip resistant", "steel toe", "work", "shift")
    ):
        score += 10
        reasons.append("fit plus work-shoe need")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_scoring.py -v`
Expected: PASS with the new FitVille-aligned scoring cases and prior broad-intent behavior still valid.

- [ ] **Step 5: Commit**

```bash
git add src/grok_x_lead_monitor/scoring.py tests/test_scoring.py
git commit -m "feat: add FitVille lead scoring signals"
```

### Task 4: Run Focused Regression Across the Pipeline

**Files:**
- Test: `tests/test_query_builder.py`
- Test: `tests/test_filters.py`
- Test: `tests/test_scoring.py`
- Optional validation: `tests/test_main.py`

- [ ] **Step 1: Run the focused regression suite**

Run: `pytest tests/test_query_builder.py tests/test_filters.py tests/test_scoring.py -q`
Expected: PASS across query, filter, and scoring coverage.

- [ ] **Step 2: Run the broader pipeline smoke tests**

Run: `pytest tests/test_main.py tests/test_diagnostics.py -q`
Expected: PASS with no regressions in pipeline assembly, diagnostics, or report writing behavior.

- [ ] **Step 3: Inspect any failing assertions before editing more code**

```text
If failures appear, first classify them:
- query-pack expectation drift
- filter false positive / false negative
- score threshold mismatch
- downstream integration regression
```

- [ ] **Step 4: Commit the verified expansion**

```bash
git add src/grok_x_lead_monitor/query_builder.py src/grok_x_lead_monitor/filters.py src/grok_x_lead_monitor/scoring.py tests/test_query_builder.py tests/test_filters.py tests/test_scoring.py
git commit -m "feat: expand FitVille recall rules"
```
