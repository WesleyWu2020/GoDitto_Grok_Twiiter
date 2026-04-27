# FitVille Recall Expansion Design

## Goal

Expand candidate recall for FitVille-aligned footwear leads without collapsing result quality. The brand fit to optimize for is:

- wide and extra-wide feet
- high instep / roomy toe-box needs
- plantar fasciitis, bunions, flat feet
- diabetic foot, swelling, edema
- long-standing work contexts
- functional work-shoe needs such as slip resistance or protective toe boxes

The primary goal for this iteration is recall growth. Precision is protected by keeping strict anti-spam filtering and by strengthening downstream scoring.

## Current Constraints

The current pipeline already has the right high-level architecture:

- `query_builder.py` defines fixed query packs
- `grok_client.py` retrieves broad X candidates through Grok `x_search`
- `filters.py` performs hard acceptance / rejection
- `scoring.py` ranks commercial intent
- `main.py` applies score thresholds and URL dedupe before export

The current weak point is narrow vocabulary. The system is biased toward generic foot pain and recommendation language, and undercovers many FitVille-relevant segments.

## Recommended Approach

Use a three-part expansion:

1. Expand `query_builder.py` with FitVille-aligned search queries
2. Lightly widen `filters.py` only for clearly relevant need signals
3. Extend `scoring.py` with explicit FitVille-fit scoring signals

This keeps recall growth mostly at the query layer, while preserving hard filter discipline and using scoring to absorb broader traffic.

## Alternatives Considered

### 1. Query-only expansion

Pros:

- smallest code change
- fastest recall improvement

Cons:

- likely to flood candidates with generic recommendations, product chatter, and non-buyer commentary

### 2. Heavy filter expansion

Pros:

- more candidates pass into scoring

Cons:

- filter layer becomes too permissive
- harder to reason about false positives
- turns acceptance logic into a loose relevance bucket instead of a buyer-need gate

### 3. Query + light filter + stronger scoring

Pros:

- best recall / quality balance
- preserves modular responsibilities
- easiest to tune incrementally

Cons:

- slightly larger change set

Recommendation: option 3.

## Query Expansion Design

Add new query themes in `query_builder.py` covering four recall buckets.

### 1. Width and shape fit

Example directions:

- `best extra wide shoes for foot pain`
- `need 4E shoes recommendations`
- `need 6E shoes recommendations`
- `wide toe box shoes for bunions`
- `high instep shoes recommendations`

### 2. Medical and chronic foot issues

Example directions:

- `best shoes for bunions walking`
- `flat feet shoes recommendations`
- `diabetic shoes recommendations`
- `swollen feet shoes`
- `foot edema shoes recommendations`

### 3. Work and long-standing contexts

Example directions:

- `best shoes for standing all day at work`
- `nurse shoes for foot pain`
- `chef shoes slip resistant comfortable`
- `non slip work shoes foot pain`
- `steel toe work shoes comfortable wide feet`

### 4. Replacement / buying intent combinations

Example directions:

- `need better work shoes for foot pain`
- `what shoes help bunions`
- `recommend shoes for swollen feet`
- `looking for extra wide work shoes`

The new queries should remain plain-English and buyer-like. Avoid overfitting them to brand language such as `FitVille`, `PropelCore`, or `Comfort+`, because the task is lead capture, not branded mention monitoring.

## Filter Expansion Design

`filters.py` should remain conservative. The objective is to admit more clearly relevant consumers, not to approve every medically adjacent tweet.

### Expand `RELEVANCE_HINTS`

Add terms such as:

- `bunion`
- `bunions`
- `diabetic`
- `swollen feet`
- `swelling`
- `edema`
- `flat feet`
- `arch support`
- `wide toe box`
- `extra wide`
- `4e`
- `6e`
- `high instep`
- `non slip`
- `slip resistant`
- `steel toe`

### Expand `PAIN_OR_FIT_HINTS`

Add terms such as:

- `bunions`
- `bunion pain`
- `swollen feet`
- `foot swelling`
- `edema`
- `toes cramped`
- `toe pain`
- `high instep`
- `flat feet`

### Expand request-style and consumer-need language only where it preserves buyer intent

Possible additions:

- `looking for wide shoes`
- `need extra wide shoes`
- `what shoes help`
- `need work shoes`
- `need diabetic shoes`

### Keep these hard constraints unchanged

- citation required
- promo / affiliate / ad blocking
- non-consumer commentary blocking
- excessive hashtag blocking

This is important. Recall growth should not come from weakening spam defense.

## Scoring Expansion Design

`scoring.py` should gain explicit FitVille-fit signals so broader recall does not lower output quality.

### Add width and fit signals

Examples:

- `wide feet`
- `extra wide`
- `4e`
- `6e`
- `wide toe box`
- `high instep`

These should increase score because they strongly align with the brand’s fit proposition.

### Add structural foot-condition signals

Examples:

- `bunion`
- `bunions`
- `flat feet`
- `plantar fasciitis`
- `arch support`

These should score above generic comfort complaints because they imply more concrete product mismatch.

### Add medical / swelling signals

Examples:

- `diabetic`
- `diabetic shoes`
- `swollen feet`
- `foot swelling`
- `edema`

These should be treated as high brand-fit signals, but only when the text still looks like an individual need or purchase consideration.

### Add work-function signals

Examples:

- `standing all day`
- `shift`
- `nurse`
- `chef`
- `warehouse`
- `non slip`
- `slip resistant`
- `oil resistant`
- `steel toe`

These indicate strong FitVille relevance for the work-shoe line.

### Add combination bonuses

High-value pairings should add extra points:

- foot condition + recommendation request
- width signal + work-shoe signal
- swelling / diabetic signal + shoe replacement request
- pain signal + non-slip / work context

### Keep scoring guardrails

- do not auto-promote every medical mention
- do not treat generic product praise as strong intent
- buyer language still matters

## Data Flow Impact

The flow remains unchanged:

1. broaden search recall at query entry
2. retain only consumer-like footwear need candidates
3. score for intent and FitVille alignment
4. enforce minimum score and URL dedupe
5. export leads and raw candidates

No architecture changes are required.

## Testing Design

Add or update tests for:

- filter acceptance of wide-fit / bunion / diabetic / swollen-feet / work-shoe consumer tweets
- filter rejection of generic chatter that mentions these terms without buyer intent
- scoring uplift for FitVille-aligned signals
- combined-signal scoring bonuses
- query pack coverage for new FitVille segments

Representative test cases should include:

- wide-foot recommendation request
- bunion pain with shoe replacement intent
- diabetic or swelling-related footwear request
- nurse / chef / warehouse standing-all-day shoe request
- false positives such as article sharing, product promotion, or third-person commentary

## Risks

### Risk: noisy medical chatter

Mitigation:

- keep consumer-need gating intact
- require recommendation / replacement / first-person context for high scores

### Risk: generic shoe recommendation spam

Mitigation:

- keep blocklist strict
- rely on combination scoring rather than single-keyword boosts

### Risk: overlap across queries creating duplicate candidates

Mitigation:

- existing URL dedupe in `main.py` is sufficient for this iteration

## Out Of Scope

- brand mention tracking for `FitVille`
- language expansion beyond current English-oriented heuristics
- machine-learned ranking
- per-segment threshold tuning
- restructuring the Grok prompt or transport layer

## Implementation Plan Shape

Implementation should be a contained ruleset update in:

- `src/grok_x_lead_monitor/query_builder.py`
- `src/grok_x_lead_monitor/filters.py`
- `src/grok_x_lead_monitor/scoring.py`
- related tests

The preferred order is:

1. update query coverage
2. expand filter vocabulary conservatively
3. extend scoring with FitVille-fit signals and bonuses
4. add regression tests for recall-focused segments

## Acceptance Criteria

- the query pack covers width, medical, swelling, and work-shoe segments
- valid consumer tweets in these segments are no longer systematically dropped
- FitVille-aligned tweets score higher than generic comfort chatter
- spam, news, and non-consumer commentary remain blocked
- existing report generation and dedupe behavior remain unchanged
