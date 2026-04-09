# Grok X Lead Monitor Design

## Summary

Build a scheduled local-output service that calls the Grok API to search X in a defined time window, filters for real consumers experiencing foot pain or actively asking for comfortable shoe recommendations, scores purchase intent, reconstructs the original tweet URL from citation metadata, and writes a pure Markdown table to a daily output file.

The first version is intentionally narrow:
- Output target is local Markdown files only
- Default time window mode is calendar day in `Asia/Shanghai`
- Relative windows are also supported through configuration
- Only leads with intent score `>= 60` are retained
- Any candidate without verifiable citation data and a reconstructable original URL is discarded

## Goals

- Run on a schedule without manual intervention
- Use Grok as the only upstream model/API dependency
- Restrict source evidence to live X search results obtained through Grok tool use
- Produce a deterministic Markdown table with no leading or trailing commentary
- Preserve enough local structure to extend later to other sinks such as WhatsApp or databases

## Non-Goals

- WhatsApp delivery in the first version
- Long-term lead storage in a database
- Multi-platform social listening beyond X
- Human review workflows in the first version
- Full sentiment analytics or broader market research outputs

## Operating Constraints

- The system must not trust unsupported free-form model claims as data
- The system must treat citation metadata as the minimum evidence requirement for every retained row
- If the original tweet URL cannot be reconstructed with confidence, that row is invalid
- If a run yields zero valid rows, the output file may still be created, but it must contain only the Markdown table header and zero data rows
- The exporter must never write explanatory prose outside the table

## High-Level Architecture

The service is split into five focused components plus scheduling:

1. Scheduler
   - Triggers the collection pipeline on a cron-like schedule
   - Resolves the effective time window for each run

2. Query Builder
   - Generates a curated pack of search prompts covering foot pain, long-standing discomfort, shoe comfort needs, and plantar fasciitis-related recommendation intent

3. Grok Search Client
   - Calls the Grok API
   - Instructs the model to use `x_search` as the only data source
   - Requests structured output that includes candidate tweet text, username, timestamp, and citation metadata

4. Candidate Evaluator
   - Removes spam, promotions, sweepstakes, hashtag stuffing, and non-consumer content
   - Scores the remaining candidates for purchase intent
   - Drops all results below threshold

5. URL Resolver
   - Reconstructs the physical tweet URL from citation metadata
   - Rejects any row with incomplete or unverifiable URL parts

6. Markdown Exporter
   - Writes the final pure Markdown table to a local file
   - Produces a daily canonical output file

## Time Window Model

The system supports two window modes:

1. `calendar_day` (default)
   - Uses a natural-day range in the configured timezone
   - Intended for daily archive files
   - Default timezone: `Asia/Shanghai`

2. `relative`
   - Uses a rolling lookback such as the last `24h` or `7d`
   - Intended for ad hoc or higher-frequency monitoring

Default behavior:
- Scheduled runs use `calendar_day`
- Output file path uses the resolved local date of the target day

## Query Strategy

The query builder should emit multiple semantically distinct searches so the service does not overfit to one wording pattern. Initial query groups should include:

- Foot pain from standing or walking
- Explicit comfort-shoe recommendation requests
- Plantar fasciitis shoe searches
- Work-related foot pain contexts such as nursing, retail, hospitality, warehouse, and service roles
- Dissatisfaction with existing shoes where the user implies replacement intent

Representative themes:
- `feet hurt standing all day`
- `need comfortable shoes recommendations`
- `best shoes for plantar fasciitis`
- `my feet are killing me at work need better shoes`
- `walking all day shoes recommendation`

The implementation should store these as a versioned query pack, not hardcode them inline in the scheduler.

## Grok API Contract

The Grok client should request structured JSON-like output from the model, not a presentation-ready table. Each candidate object should include at minimum:

- `username`
- `display_name` if available
- `tweet_text`
- `tweet_created_at`
- `query_used`
- `citations`
- `tweet_id` if directly exposed by citations or parsed from citation metadata
- `author_handle` if directly exposed by citations or parsed from citation metadata

The prompt contract to Grok should explicitly require:
- use of `x_search` as the only source of live tweet data
- exclusion of unsupported memory or fabricated users
- return of citation metadata for every retained candidate
- no recommendation to keep rows whose URL cannot be verified

Local code remains the final authority. The model may propose candidates, but filtering, scoring thresholds, and export cleanliness are enforced locally.

## Candidate Filtering Rules

Each returned candidate must pass a hard filter before scoring. Drop the candidate if any of the following is true:

- Contains discount code, coupon, affiliate, giveaway, or sweepstakes language
- Reads like a brand ad, retailer promotion, or campaign copy
- Shows excessive hashtag stuffing
- Is a reposted marketing template rather than a personal consumer complaint or request
- Is unrelated to foot pain, comfort footwear, or shoe recommendation intent
- Lacks citation metadata required for downstream verification

The filter is intentionally conservative. False negatives are acceptable; false positives are expensive.

## Intent Scoring Model

Intent is scored from `0` to `100`.

Thresholds:
- `85-100`: `High`
- `60-84`: `Medium`
- `<60`: discard

Scoring guidance:

High intent signals:
- Direct request for shoe recommendations
- Explicit statement of needing to buy or replace shoes
- Strong pain plus active solution-seeking behavior
- Foot pain tied to daily activity or work that creates urgency

Medium intent signals:
- Clear foot pain or discomfort
- Frustration with current shoes
- Implicit replacement interest without direct buying request

Low intent signals to discard:
- General jokes or vague complaints
- Pure conversation without a problem to solve
- Medical discussion without footwear purchase relevance
- Third-party commentary about others

The local scorer should be rule-based in the first version so behavior is inspectable and stable.

## URL Reconstruction Rules

A valid final row requires a physical tweet URL in this format:

`https://x.com/<username>/status/<tweet_id>`

Accepted derivation sources:
- direct citation metadata containing handle and tweet id
- citation URLs from which handle and tweet id can be parsed reliably

Rejection conditions:
- missing `tweet_id`
- missing `username` or handle required for the URL path
- citation points to a search page or non-tweet artifact only
- conflicting metadata where the physical tweet URL cannot be resolved with confidence

If URL reconstruction fails, the row is dropped even if the text otherwise looks valuable.

## Data Model

Internal normalized lead record:

```json
{
  "username": "string",
  "tweet_text": "string",
  "tweet_summary": "string",
  "tweet_created_at": "ISO-8601 string",
  "intent_score": 0,
  "intent_priority": "High|Medium",
  "original_url": "https://x.com/.../status/...",
  "query_used": "string",
  "citation_payload": {}
}
```

The normalized model is internal only. The exporter uses only the fields required by the final Markdown table.

## Output Contract

The output must be a pure Markdown table with exactly these columns:

| Username (用户名) | Intent Score (意图评分: 0-100) | Intent Priority (优先级: High/Medium) | Tweet Summary (推文核心诉求高度浓缩) | Original URL (推文原链接) |

Rules:
- No prose before the table
- No prose after the table
- The summary must be concise and reflect the core need only
- The exporter must escape pipe characters and preserve valid Markdown
- Rows should be sorted by descending intent score, then by newest timestamp

Output path:
- `output/leads/YYYY-MM-DD.md`

Run behavior:
- For `calendar_day`, multiple runs for the same date overwrite the same file so the date has a single latest view

## Error Handling

Failure policy by stage:

- Query generation failure
  - Fail the run and log the reason

- Grok API failure
  - Fail the run and log the reason
  - Do not emit a misleading partial report unless explicitly configured later

- Malformed model response
  - Attempt structured parse recovery once
  - If still invalid, fail the run

- Candidate-level citation gaps
  - Drop only the affected rows

- URL reconstruction failure
  - Drop only the affected rows

- Zero surviving rows
  - Write an empty table with header only, or optionally no rows under the header

The first version should prefer correctness and traceability over maximizing row count.

## Configuration

Recommended environment variables:

- `GROK_API_KEY`
- `DEFAULT_TIMEZONE=Asia/Shanghai`
- `DEFAULT_WINDOW_MODE=calendar_day`
- `DEFAULT_OUTPUT_DIR=output/leads`
- `MIN_INTENT_SCORE=60`
- `HIGH_PRIORITY_SCORE=85`
- `QUERY_PACK_VERSION=v1`
- `LOG_LEVEL=INFO`

Optional schedule configuration can live in a local config file if needed, but the first version can also rely on external cron invocation.

## Testing Strategy

Minimum required automated tests:

1. Query builder tests
   - Confirms the expected query pack is emitted
   - Verifies mode and language metadata are attached as designed

2. Filter tests
   - Rejects promotions, giveaways, hashtag spam, and brand marketing examples
   - Keeps authentic user complaints and recommendation requests

3. Intent scorer tests
   - Correctly assigns `High`, `Medium`, and discard outcomes to representative fixtures

4. URL resolver tests
   - Builds valid `x.com/<username>/status/<tweet_id>` URLs from complete citation payloads
   - Rejects incomplete or conflicting metadata

5. Exporter tests
   - Produces exactly the required table header and rows
   - Produces no surrounding commentary
   - Correctly handles empty result sets

## Suggested Project Layout

```text
src/
  grok_x_lead_monitor/
    scheduler.py
    query_builder.py
    grok_client.py
    filters.py
    scoring.py
    url_resolver.py
    exporter.py
    models.py
    config.py
    main.py

tests/
  test_query_builder.py
  test_filters.py
  test_scoring.py
  test_url_resolver.py
  test_exporter.py

output/
  leads/

docs/
  superpowers/
    specs/
      2026-04-08-grok-x-lead-monitor-design.md
```

## Implementation Notes

- Keep the Grok prompt focused on candidate discovery, not final presentation formatting
- Use local deterministic code for all final acceptance decisions
- Avoid introducing a database until lead history, deduplication beyond a daily file, or analytics actually require it
- Use `tweet_id` as the primary deduplication key within a run and within the same output day
- Keep the scheduler boundary thin so external cron can be swapped for an in-process scheduler later without touching core logic

## Open Decisions Resolved In This Design

- Delivery sink: local Markdown file only
- Default window mode: calendar day
- Alternate window mode: relative window supported through configuration
- Persistence: file-based only in v1
- Scoring authority: local deterministic rules, not model-only judgment
- URL validity requirement: mandatory for every exported row

## Acceptance Criteria

The first implementation is complete when:

- A scheduled or manually invoked run can resolve the effective time window
- The service calls Grok and requests X data through `x_search`
- Returned candidates are filtered and scored locally
- Any candidate below score `60` is dropped
- Any candidate lacking a reconstructable original tweet URL is dropped
- The final output is written to `output/leads/YYYY-MM-DD.md`
- The file content contains only the required Markdown table
- Automated tests cover the main filtering, scoring, URL reconstruction, and export rules
