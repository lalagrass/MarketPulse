# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MarketPulse is a **local Taiwan stock theme-rotation radar** that:
- Aggregates daily TWSE/TPEx data into 11 themes
- Ranks themes by RS20 (theme return – TAIEX return over 20 days)
- Produces daily briefs, rank timelines, and interactive sector radars
- Supports historical replay for validation

**Scope boundaries:**
- MVP does NOT invent new indicators—it reuses pandas, pandas-ta-classic, and established patterns
- MVP does NOT use a composite score; theme rank = cross-sectional rank of RS20
- MVP does NOT implement RRG, regime detection, backtesting, or H1-H4 analysis

**Source of truth (in order):**
1. `docs/design-v0.2.md` (product spec)
2. `docs/coding-contract.md` (implementation contract)
3. Repository code
4. Older design docs only for historical context

## Core Architecture

### Module Structure

```
marketpulse/
├── cli.py              # Entry point; commands: download, validate, analyze, brief, chart, radar, replay, refresh
├── data.py             # TWSE/TPEx adapters, normalize, local cache (data/raw/, data/normalized/)
├── themes.py           # Load 11-theme YAML from themes/v1.yaml
├── calc.py             # Core: RS20, rank, value_share, breadth, volume_ratio, snapshot snapshots
├── momentum.py         # Display-only state labels: Strong/Improving/Stable/Weakening/Weak/Unknown
├── product.py          # Brief, Timeline PNG generation
└── radar.py            # Sector Radar HTML, drill-down UI, Leader/Follower/Laggard stock sort
```

### Data Flow

```
TWSE / TPEx (JSON)
    ↓ download_range()
data/raw/{TWSE,TPEx}/{yyyymmdd}.json
    ↓ normalize_all()
data/normalized/{TWSE,TPEx}/{yyyymmdd}.parquet
    ↓ compute_snapshots()
data/snapshots/theme_daily.parquet  (11 themes × dates)
    ↓
Brief → Timeline PNG → Radar HTML
```

### Key Types & Constants

**Themes & Snapshots:**
- 11 themes defined in `themes/v1.yaml` (YAML format)
- Theme snapshot = date + theme metrics (return_1/5/20, rs20, rank, breadth, value_share, etc.)
- Snapshot stored as `data/snapshots/theme_daily.parquet` (single source of truth for product)

**Role Classification (in a theme, on a given date):**
- `Leader`: rank ≤ 4 (top 4 out of 11)
- `Follower`: rank 5–8
- `Laggard`: rank ≥ 9

**Momentum State (display-only, not a score):**
- Computed from 5D return, Breadth, Volume ratio, Rank Δ5
- Labels: `Strong`, `Improving`, `Stable`, `Weakening`, `Weak`, `Unknown`

**Data Rules (critical):**
- For signal date T: use price/volume ≤ T, but membership ≤ T-1
- Never use future data (tested in `test_future_mutation.py`)
- Raw daily close only (no adjustments in MVP)
- Missing data is computed as-is from valid members, flagged with `*` in Brief

## Development Workflow

### Setup
```bash
uv sync --extra dev
uv run pytest
```

### Daily Operations
```bash
uv run marketpulse refresh           # Download → validate → analyze → brief → chart → radar (all-in-one)
uv run marketpulse radar --open      # Open radar.html in browser
```

### Detailed Commands (use when you need explicit control)
```bash
uv run marketpulse download --start 2026-07-20 --end 2026-08-31  # Fetch TWSE/TPEx
uv run marketpulse validate                                        # Check normalization
uv run marketpulse analyze                                         # Compute snapshots
uv run marketpulse brief                                           # Print Daily Brief
uv run marketpulse chart --start 2026-07-20                       # Timeline PNG (20+ sessions)
uv run marketpulse replay --start 2026-07-20 --end 2026-08-31     # Historical replay
```

### Testing
```bash
uv run pytest                          # All tests
uv run pytest tests/test_calc.py       # Single file
uv run pytest tests/test_rs.py -v      # Verbose
```

`uv run pytest` (after `uv sync --extra dev`) is the only supported test command. A bare `pytest` invoked outside the uv-managed venv (e.g. `PYTHONPATH=. pytest`) skips `uv sync` and will not have `pyarrow` or other dependencies installed, producing `to_parquet`/import failures that look like repo bugs but are just missing dependencies — not a code issue.

### Common Tasks

**Add a theme or update membership:**
- Edit `themes/v1.yaml`
- Re-run `refresh` to recompute all snapshots

**Debug a snapshot calculation:**
- Read `data/normalized/` (parquet files)
- Check `calc.py:compute_snapshots()` and `compute_stock_metrics()`
- Add a test in `tests/test_*.py`

**Validate historical data correctness:**
- Use `replay` command with explicit `--start` and `--end`
- Compare output against manual calc in Python REPL
- Check `test_future_mutation.py` for leakage patterns

## Key Design Rules

### 1. Reuse Before Implementation
- Use `pandas` for rolling, aggregation, ranking
- Use `pandas-ta-classic` for any standard TA indicator (SMA, ROC, etc.)
- Do **not** write custom SMA, momentum, RRG, or backtesting code

### 2. Small, Pure Functions
Prefer:
- Type-hinted pure functions (no hidden state)
- Explicit DataFrame schemas (document columns)
- Deterministic output for same input

Avoid:
- Speculative abstractions
- Complex class hierarchies
- Metaprogramming
- Global state

### 3. No Composite Score
- Theme strength = rank of RS20 (cross-sectional rank only)
- No weights, no optimization, no factor scoring
- Momentum is **display-only**; it does not change rank

### 4. Data Point-in-Time (PIT) Rules
- Signal date T uses price/volume from T and earlier
- But uses theme membership from T-1 or earlier
- Replay uses **current frozen YAML** (not historical membership)
- Document any replay limitations explicitly

### 5. Testing Coverage
Minimum tests:
- Data normalization (corrupt files, missing fields)
- Theme aggregation (membership changes)
- RS20 formula (hand-calc comparison)
- Rank ordering (cross-sectional consistency)
- Future mutation (no T+1 data leakage)
- Momentum state transitions

## File Locations & Conventions

```
themes/v1.yaml                        # 11-theme definitions
data/raw/{TWSE,TPEx}/                # Official dated JSON (fetched, cached, not redistributed)
data/normalized/                      # Normalized parquet (price, volume)
data/snapshots/theme_daily.parquet    # PRIMARY: 11 themes × dates (computed)
reports/rotation_latest.png           # 40-session rank timeline (auto-updated)
reports/radar.html                    # Interactive sector drill-down
docs/design-v0.2.md                   # Spec (read before architecture changes)
docs/coding-contract.md               # Implementation rules
docs/marketpulse-methodology.md       # Method notes (for context only)
```

## Common Pitfalls to Avoid

1. **Using future data**: Never reference T+1 price in a T snapshot. Tested.
2. **Silently changing theme membership**: Replay must disclose it uses current YAML.
3. **Composite scores**: Never add `rotation_score`, weighted `rank`, or `confidence`. Rank = RS20 rank only.
4. **Over-abstraction**: Do not build provider frameworks, plugin systems, or registries unless MVP needs it.
5. **Ignoring data rules**: Always validate PIT compliance and mark missing data, don't substitute silently.
6. **Arbitrary threshold tuning**: Do not optimize weights or thresholds; use established market concepts.

## Typical Session Patterns

**Adding a new indicator to snapshots:**
1. Add computation in `calc.py:compute_stock_metrics()` or `compute_snapshots()`
2. Add column to `SNAPSHOT_COLUMNS`
3. Update tests in `tests/test_calc.py`
4. Re-run `refresh` and verify output

**Fixing a data normalization bug:**
1. Add test case in `tests/test_download_cache.py` or `test_future_mutation.py`
2. Fix in `data.py:normalize_all()` or `calc.py`
3. Delete stale parquet files under `data/normalized/` and `data/snapshots/`
4. Re-run `download`, `validate`, `analyze`

**Updating the Daily Brief format:**
1. Modify `product.py:render_brief()`
2. Check output with `uv run marketpulse brief`
3. Add/update tests in `tests/test_product.py`

**Adding a new CLI command:**
1. Add function in `cli.py` with `@app.command()`
2. Use standard arg patterns (start/end dates via `_parse_date`, data_dir via `Path`)
3. Document in `README-MVP.md` under "Run"

## Questions to Ask Before Major Changes

- **Does this violate the coding contract?** (Check `docs/coding-contract.md` #1–#13)
- **Does this add a composite score?** (Coding contract #5: no)
- **Did I search for an OSS implementation first?** (Design #1.1: reuse before code)
- **Does this change the data PIT rules?** (Coding contract #7: no future data)
- **Am I over-engineering for a one-off task?** (Coding contract #6: no premature abstraction)

If the answer to any of the first three is "yes", pause and consult the design docs before proceeding.
