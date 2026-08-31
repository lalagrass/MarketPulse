# MarketPulse v0.1 coding contract

THIS FILE IS AN IMPLEMENTATION CONTRACT.  
The full design `docs/design-v0.1.md` (r3.31) is the source of truth.  
This file is the subset a coding agent must not violate.

```text
SOURCE OF TRUTH ORDER
  1. Freeze / conflict rules (this file + design Freeze section)
  2. Invariants
  3. Explicit formulas
  4. Acceptance tests / DoD
  5. Earlier narrative text
If ambiguous: STOP and report. Do not invent behavior.
```

## Current slice only

**Gate 0 → PR1 → PR2.**  
Do not write `signals/`, `eval/`, `rotation.py`, `replay.py`, `chart.py`, Streamlit, leaders, or watchlist in this slice.  
Do not start a five-year backfill until Gate 0 passes.

### Before the first useful Timeline, DO NOT build

Streamlit, DuckDB, Polars, TA-Lib, VectorBT, FinMind abstraction, provider framework, generic indicator framework, portfolio, leader scoring, watchlist, alert, LLM, H3, H4, random_exclusive, economic materiality, sophisticated statistical significance, five-year backfill, PIT taxonomy / `valid_from` membership history, reconstructed snapshot YAML, campaign machinery, a second theme_state.

H1 persistence and the RS20 baseline stay SECONDARY after PR7. They are not product-MVP completion.

## Product vs research

PRIMARY = Daily Brief + Rotation Timeline (radar).  
SECONDARY = H1–H4 (lab). Not a product-MVP completion criterion.  
H1 FAIL ≠ radar useless. A→B = relative leadership transition, never capital flow.

Product MVP job-to-be-done (D103): who is strong, who is strengthening, who is weakening, is relative leadership rotating A→B. Data support = `signal_status` badge, not a Coverage %. If a feature does not help those questions, it is not product MVP.

Two leakages (D105). Price / volume / universe / liquidity looking ahead = a correctness bug. Using the current theme YAML on historical dates = a research-interpretation limit. Product replay = historical visualization replay. Report MUST print that limitation. Do not claim the April chart means we would have known Optical in April.

```text
Build the smallest end-to-end system that can take official
dated TWSE/TPEx daily boards, apply 11 frozen themes from the
current YAML, compute the frozen price / trading-value /
breadth fields with windows ≤ T, and produce a Daily Brief +
Rotation Timeline from immutable snapshots. Historical replay
uses the current taxonomy to visualize rotation; it does not
simulate what theme definitions were known at that time.
Do not implement stock ranking, AI, notifications, Streamlit,
portfolio, generic TA, a vendor bake-off, DuckDB, PIT taxonomy,
H3/H4, random_exclusive, or H1–H4 as product completion.
First slice remains Gate 0 → PR1 → PR2.
```  
Human label for H1 = Persistence Test. Identifier stays `H1`.  
Human GO line = `RESEARCH STATUS: CONTINUE`. Identifier stays `verdict=GO`.  
Human alias = `RESEARCH VERDICT` (same values as PRODUCT VERDICT). Not a second gate. No `PRODUCT: PASS`.  
Daily Brief (PR7, not this slice) MUST open with ROTATION TODAY: Strengthening / Leading / Weakening / Data issue, derived from existing regime + `signal_status`. Not a new classifier.  
Then THEME ROTATION table with Pos / Δ5D / Δ20D / RS20 / Thrust / Breadth / State. Δ is display of existing `rotation_rank`, not a new signal.  
Timeline is a Rotation Map, not a Strength Chart. The five fields (relative_position, RS20, value_thrust, breadth, regime) MUST appear together. Do not ship a position-only line. Do not replace it with a swimlane chart.  
`signal_status` is a badge, not an analysis dimension. MISSING_DATA MUST NOT print as `LEADING ⚠`.  
CA extras (`H1_ex_jump`, `H1_ex_future_ca`) live in `eval/` only; they MUST NOT change the primary signal.

MarketPulse v0.1 is a daily Taiwan stock theme-rotation radar, not a Quant Research Platform. digest / campaign / H1–H4 are reproducibility guards, not the product.

## Invariants

1. Never use future **prices or volume**. Mutating T+1 bars must not change T's snapshot.  
2. Product-MVP membership = frozen YAML members. No `valid_from`/`valid_to` history before the first Timeline.  
3. Liquidity = TV_(T-1).  
4. Universe = universe_member(T).  
5. Detect missing **before** building I_T:

```text
G_T = frozen YAML members of the classification
E_T = G_T ∩ universe(T) ∩ liquidity_(T-1)
M_T = E_T members missing close_T or TV_T
I_T = E_T - M_T
M_T non-empty → MISSING_DATA (not a partial ranked signal)
FORBIDDEN: filter close.notnull() first, then look for missing.
FORBIDDEN: implement membership_asof history before the first Timeline.
```

6. Any incomplete required component → no `rotation_score`. No `skipna`.  
7. Only `signal_status=OK` participates in ranking.  
8. `relative_position` uses fixed K of the classification.  
9. Timeline / brief / chart read frozen snapshots only. Daily Brief / ASCII / Timeline PNG MUST NOT print `rotation_score`. Timeline v1 must answer: who is strong, who is strengthening, who is weakening. Brief MUST include ROTATION TODAY and Rank Δ5/Δ20. Timeline PNG MUST include a today-strip of the five fields, not a position-only line. When `verdict=GO`, human report MUST print `RESEARCH VERDICT: GO` and `RESEARCH STATUS: CONTINUE`; do not rename the identifier. MISSING_DATA MUST NOT appear as Leading.  
10. A→B persist M = immediately preceding M trading sessions; A and B OK on every session. A hole resets the window.  
11. Do not add indicators, themes, leaders, watchlist, GUI, baselines, ML, Adj, DuckDB, Polars, VectorBT-as-core, TA-Lib, FinMind-as-primary, twmarketdata-as-primary, or new GO gates.  
12. YAML `algorithm_version` must equal package `ALGORITHM_VERSION` at startup or abort.  
13. Reuse generic libraries (pandas, numpy, httpx, SQLite, PyArrow, matplotlib, Typer, pytest). Own domain semantics. MarketPulse owns market semantics, not infrastructure. Do not invent a Data / TA / Research / Chart framework. `BarProvider` is a Protocol, not a plugin platform. httpx to official dated JSON is the ingest path, not a crawler, and not a reason to switch to a vendor SDK.

## Status precedence

```text
MISSING_DATA > UNRELIABLE > INSUFFICIENT_HISTORY > THIN > OK
```

UNRELIABLE (as-of-T CA, frac ≥ 0.25) is product data-quality: not ranked, not Timeline main line, not A→B. Raw row kept. No Adj.

MISSING_DATA: diagnostic fields MAY stay; `rotation_score`, `rotation_rank`, `relative_position`, `regime` = NULL. Not eval, not A→B.  
Brief MUST print expected/received/missing `stock_id`. Timeline MUST keep a gap+× marker. FORBIDDEN: silently drop the theme.

## Canonical time APIs

`load_bars` / `get_signal_context` / `get_entry_date` / `get_forward_horizon` only.  
Entry = next session close. No `entry_lag_sessions`.

## Snapshot

First product path only needs: `run_id`, `as_of`, `algorithm_version`, `classification_version`.  
`daily_run_id` ≠ `campaign_id`.  
MATCH = (algorithm_version, config_version, classification_version, classification_digest, schema_version, price_mode) is snapshot metadata at PR5, not a first-slice subsystem.  
Parquet is immutable. SQLite is a working cache.  
`content_digest` = data-bearing columns only.  
campaign data identity = dates + versions + ordered `content_digest[]`. Do not hash `daily_run_id`.  
Do not build campaign / digest / provenance machinery before the first Timeline.

`canonical_json`: UTF-8, `sort_keys=True`, `ensure_ascii=False`, `separators=(',', ':')`, `stock_id` always string.

## Two ranks

component `rank_pct`: pandas `rank(method="average")`.  
`rotation_rank`: integer 1..n_ranked, `score DESC, theme_id ASC`. Never 1.5 / 95.

## CLI this slice

`download` / `validate` / `doctor` (+ skeleton `--help`).  
`chart` later: snapshot-only; never download/analyze/replay.

Gate 0 = official dated TWSE MI_INDEX + TPEx `stk_quote_result.php` only.  
Not a twmarketdata / FinMind / yfinance comparison.  
Not a provider bake-off. `twmd.compat.finmind` existing does not change this.  
Not a golden-dataset / Timeline / H1 exercise. Golden numbers are PR 4/7 after official bars exist.  
Not a 100-stock spike. Gate 0 is the full-market board (TWSE ~900–1200, TPEx ~700–900).  
FORBIDDEN: Golden Episode expected-state YAML (e.g. `Optical: strengthening`) before official bars exist.  
Do not add `marketpulse daily`; human CLI is `brief` / `chart`.

## Reuse

```text
REUSE implementation. OWN semantics.
MarketPulse owns market semantics, not infrastructure.
Do not invent a Quant Platform.
```

REUSE: pandas, numpy, httpx+tenacity, pydantic, Typer, SQLite, PyArrow, matplotlib, pytest, uv.  
OWN: frozen theme YAML, price/volume as-of, E_T/M_T/I_T, TV-weight, breadth, thrust, RS, relative_position, regime, A→B, snapshot identity. Membership provenance and H1–H4 stay in the spec; do not implement provenance or H3/H4 before the first Timeline.  
RRG: conceptual reference only. No JdK RS-Ratio. No RRG library. Timeline is not an RRG chart.  
`rank_momentum` already encodes relative-momentum in rank space. Do not add a second JdK axis.

Formula provenance (D104/D106): reuse standard *concepts* (stock return, excess RS, A/D, % above MA, Top-3). Own the aggregation and composition (lag-1 TV-weight, value_share overlap rule, value_thrust, rank-of-rank, fixed-K position, 股癌 6-state). Do not replace that composition with RRG quadrants or with `rank(RS20)` as the only Timeline sort. Side-by-side display of RS / value share / breadth / Rank Δ is the product; the internal sort remains the four-component rank-of-rank. Do not optimize the 0.30/0.25/0.20/0.25 weights.

## Forbidden

FinMind as primary source. twmarketdata as primary / Gate 0 / v0.1 Protocol.  
VectorBT as core. TA-Lib. Streamlit/Plotly in v0.1. DuckDB. Polars.  
PostgreSQL, Redis, ClickHouse, Kafka, Celery, WebSocket, LLM.  
`docs/design-v0.2.md`. Official / FinMind / TWMD bake-off as Gate 0.  
100-stock spike. `marketpulse daily` as a new command.  
Second `theme_state` classifier. Golden Episode expected-state YAML before bars exist.  
`data_health` / `theme_health` scores. Return 5/60, RS 5/60, Above MA20 as *new* v0.1 signals.  
RRG / JdK as the rotation engine. Delete `rotation_score`.  
`relative_position` = 252d RS percentile or z-score. Theme regime = MA20/MA60.  
CMF, HHI, Breadth Thrust. Confirmation-only split that drops TV/breadth from ranking.  
Rank Timeline / `rotation_rank` by RS20 only. Shrink 6-state to four English states as the product labels. Delete `market_regime` from the v0.1 spec. Rename `value_thrust` to TVAttention.  
Treat A→B as capital flow. Make H1–H4 a product-MVP completion criterion.  
Implement PIT taxonomy / valid_from membership history / reconstructed snapshot YAML before the first Timeline.  
Add `classification_mode` CONTEMPORANEOUS / RECONSTRUCTED. Require G_T = membership_asof history as product MVP.  
Claim visualization replay means contemporaneous knowledge.  
Implement a looser informal A→B detector.  
Implement H3, H4, random_exclusive, or economic materiality before the first Timeline.  
Delete H3/H4 from the v0.1 spec.  
Treat MATCH digest layers as a first-slice subsystem.  
Telegram / LINE / Email / Push. Portfolio / P&L / execution.  
`h2_pass`. Newey-West / p-value / Sharpe. 11→10 themes. Equal-weight as the signal. Leaders / 52w / watchlist.  
Print `rotation_score` in Brief/ASCII/PNG. Silently drop MISSING_DATA themes. Print MISSING_DATA as `LEADING ⚠`. Invent a Data Quality Score. Shrink the PR DAG. Invent golden numbers before Gate 0 bars. Rename GO → CONTINUE or RESEARCH_GO as an identifier. Add `PRODUCT: PASS` as a new gate. Omit ROTATION TODAY. Omit Rank Δ5/Δ20. Skip holes when computing rank_delta. Ship a Timeline that is only a relative_position line. Replace Timeline with a swimlane chart. Invent a Taxonomy Audit engine. Invent a Quant Platform.
