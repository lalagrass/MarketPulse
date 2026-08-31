# MarketPulse v0.1 coding contract

THIS FILE IS AN IMPLEMENTATION CONTRACT.  
The full design `docs/design-v0.1.md` (r3.25) is the source of truth.  
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

## Product vs research

PRIMARY = Daily Brief + Rotation Timeline (radar).  
SECONDARY = H1–H4 (lab).  
H1 FAIL ≠ radar useless. A→B = relative leadership transition, never capital flow.  
Human label for H1 = Persistence Test. Identifier stays `H1`.  
Human GO line = `RESEARCH STATUS: CONTINUE`. Identifier stays `verdict=GO`.  
Daily Brief (PR7, not this slice) MUST open with ROTATION TODAY: Strengthening / Leading / Weakening / Data issue, derived from existing regime + `signal_status`. Not a new classifier.  
Timeline is a Rotation Map, not a Strength Chart. The five fields (relative_position, RS20, value_thrust, breadth, regime) MUST appear together. Do not ship a position-only line.

MarketPulse v0.1 is a daily Taiwan stock theme-rotation radar, not a Quant Research Platform. digest / campaign / H1–H4 are reproducibility guards, not the product.

## Invariants

1. Never use future data. Mutating T+1 must not change T's snapshot.  
2. Membership for signal/eval = G_(T-1).  
3. Liquidity = TV_(T-1).  
4. Universe = universe_member(T).  
5. Detect missing **before** building I_T:

```text
G_T = membership_asof(T-1)
E_T = G_T ∩ universe(T) ∩ liquidity_(T-1)
M_T = E_T members missing close_T or TV_T
I_T = E_T - M_T
M_T non-empty → MISSING_DATA (not a partial ranked signal)
FORBIDDEN: filter close.notnull() first, then look for missing.
```

6. Any incomplete required component → no `rotation_score`. No `skipna`.  
7. Only `signal_status=OK` participates in ranking.  
8. `relative_position` uses fixed K of the classification.  
9. Timeline / brief / chart read frozen snapshots only. Daily Brief / ASCII / Timeline PNG MUST NOT print `rotation_score`. Timeline v1 must answer: who is strong, who is strengthening, who is weakening. Brief MUST include ROTATION TODAY. Timeline PNG MUST include a today-strip of the five fields, not a position-only line. When `verdict=GO`, human report MUST print `RESEARCH STATUS: CONTINUE`; do not rename the identifier.  
10. A→B persist M = immediately preceding M trading sessions; A and B OK on every session. A hole resets the window.  
11. Do not add indicators, themes, leaders, watchlist, GUI, baselines, ML, Adj, DuckDB, Polars, VectorBT-as-core, TA-Lib, FinMind-as-primary, twmarketdata-as-primary, or new GO gates.  
12. YAML `algorithm_version` must equal package `ALGORITHM_VERSION` at startup or abort.  
13. Reuse generic libraries (pandas, numpy, httpx, SQLite, PyArrow, matplotlib, Typer, pytest). Own domain semantics. Do not invent a Data / TA / Research / Chart framework. `BarProvider` is a Protocol, not a plugin platform.

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

`daily_run_id` ≠ `campaign_id`.  
MATCH = (algorithm_version, config_version, classification_version, classification_digest, schema_version, price_mode).  
Parquet is immutable. SQLite is a working cache.  
`content_digest` = data-bearing columns only.  
campaign data identity = dates + versions + ordered `content_digest[]`. Do not hash `daily_run_id`.

`canonical_json`: UTF-8, `sort_keys=True`, `ensure_ascii=False`, `separators=(',', ':')`, `stock_id` always string.

## Two ranks

component `rank_pct`: pandas `rank(method="average")`.  
`rotation_rank`: integer 1..n_ranked, `score DESC, theme_id ASC`. Never 1.5 / 95.

## CLI this slice

`download` / `validate` / `doctor` (+ skeleton `--help`).  
`chart` later: snapshot-only; never download/analyze/replay.

Gate 0 = official dated TWSE MI_INDEX + TPEx `stk_quote_result.php` only.  
Not a twmarketdata / FinMind / yfinance comparison.  
Not a golden-dataset / Timeline / H1 exercise. Golden numbers are PR 4/7 after official bars exist.

## Reuse

```text
REUSE implementation. OWN semantics.
Do not invent a Quant Platform.
```

REUSE: pandas, numpy, httpx+tenacity, pydantic, Typer, SQLite, PyArrow, matplotlib, pytest, uv.  
OWN: theme YAML, membership, as-of, E_T/M_T/I_T, TV-weight, breadth, thrust, RS, relative_position, regime, A→B, snapshot identity, H1–H4.  
RRG: conceptual reference only. No JdK RS-Ratio. No RRG library. Timeline is not an RRG chart.

## Forbidden

FinMind as primary source. twmarketdata as primary / Gate 0 / v0.1 Protocol.  
VectorBT as core. TA-Lib. Streamlit/Plotly in v0.1. DuckDB. Polars.  
`h2_pass`. Newey-West / p-value / Sharpe. 11→10 themes. Equal-weight as the signal. Leaders / 52w / watchlist.  
Print `rotation_score` in Brief/ASCII/PNG. Silently drop MISSING_DATA themes. Shrink the PR DAG. Invent golden numbers before Gate 0 bars. Rename GO → CONTINUE as an identifier. Omit ROTATION TODAY. Ship a Timeline that is only a relative_position line. Invent a Quant Platform.
