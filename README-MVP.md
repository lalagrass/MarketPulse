# MarketPulse MVP v0.2

MarketPulse is a local Taiwan stock theme-rotation radar.

## MVP

```text
TWSE / TPEx
    ↓
11 Theme YAML
    ↓
Theme Aggregation
    ↓
RS20 + Value Share + Breadth + Volume Ratio
    ↓
Theme Rank
    ↓
Daily Brief + Rotation Timeline + Sector Radar
    ↓
Historical Replay
```

## Core rule

MarketPulse does not invent a new rotation score.

It uses established market-analysis concepts and focuses its own code on Taiwan theme aggregation and rotation visualization.

## Interpretation Boundary

MarketPulse describes current relative leadership; it does not predict persistence or reversal timing. A high Theme Rank indicates that the theme is currently strong relative to the other tracked themes, not that its strength will continue. Rank changes describe changes in relative position but are not trading signals. RS20, Breadth, Volume, and Momentum are supporting evidence for interpreting the current state; they do not form a predictive composite score.

**And now it is measured.** Rank persistence — the mean rank correlation between day T and day T−k — tested against a circular-shift null over 329 sessions (2025-05-02 → 2026-09-03):

```text
k     observed   null              distance   percentile
1     0.9346     0.0929 ± 0.0701     12.0 σ     100.0
5     0.7297     0.0902 ± 0.0710      9.0 σ     100.0
20    0.1613     0.0864 ± 0.0745       1.0 σ     84.6
```

**The 1- and 5-day orderings are real by any standard. The 20-day ordering sits one standard deviation above noise and clears no conventional threshold.** MarketPulse is a short-horizon instrument, and the rank triplet `R5·#R20·R60` exists so that a `10·#3·1` — 60-day leader, 5-day laggard — is visible. That shape is the norm, not an anomaly.

Two caveats worth carrying. The figure is **restated**: the current frozen membership applied backwards over 2025, which biases persistence upward, so the truth is likely lower. And an earlier version of this README reported "percentile 81.0" from a null that turned out to be contaminated by a degenerate shift — same conclusion, invalid evidence. The conclusion survived the correction; do not mistake that for the original having been right.

What this does *not* say: that RS60 is meaningless. A 60-day relative return honestly describes the last 60 days. What fails is treating a month-scale rank *ordering* as a stable structure. The `R5·#R20·R60` triplet exists so that a `10·#3·1` — 60-day leader, 5-day laggard — is visible; sprint 002's finding is that such a shape is the norm, not an anomaly.

## Documents

- `docs/design-v0.2.md` — replacement MVP design（產品規格；與此衝突時以它為準）
- `docs/coding-contract.md` — replacement coding contract
- `docs/reuse-plan.md` — OSS reuse boundary
- `docs/marketpulse-methodology.md` — 觀測方法論（不是規格；與設計衝突時以設計為準）

## OSS

Actual dependencies are in `pyproject.toml`. The list below is the *evaluation*
record — surveyed, and deliberately not adopted:

- pandas-ta-classic — https://github.com/xgboosted/pandas-ta-classic — **not a
  dependency.** SMA and N-day return are one-line pandas expressions; see
  coding-contract §3 and non-goals D8
- pandas-ta — https://github.com/JameRawlings/pandas-ta — same reason
- RRG-Lite — https://github.com/BennyThadikaran/RRG-Lite — **non-goal D3.**
  `rank` + `rank_delta_5` already cover the useful part of the two-axis idea
- alphalens — **non-goal D12.** 11 themes is too few for quantile analysis, and
  the Spearman correlation we need ships with pandas

## Run

Daily update (after official EOD is published):

```text
uv sync --extra dev
uv run marketpulse refresh
uv run pytest
```

`uv run pytest` is the only supported test command. Running a bare `pytest` (outside the uv-managed venv) skips `uv sync` and will report `pyarrow`-missing failures on `to_parquet` — that's a missing-dependency artifact of the sandbox, not a repo bug.

`refresh` fetches trailing weekdays, validates, analyzes, prints Brief, writes `reports/rotation_latest.png` (last 40 ranked sessions), prints the Sector Rotation table, and writes `reports/radar.html`. Empty too-early files are retried; holidays before the last complete session stay cached.

Open the radar (ranking table + Momentum state + click a sector for Leader / Follower / Laggard stocks):

```text
uv run marketpulse radar --open
```

First-time / explicit range:

```text
uv run marketpulse download --start 2026-07-20 --end 2026-08-31
uv run marketpulse validate
uv run marketpulse analyze
uv run marketpulse brief
uv run marketpulse radar
uv run marketpulse chart --start 2026-07-20
uv run marketpulse replay --start 2026-07-20 --end 2026-08-31
```

Signal diagnostics (one-off, deliberately not on the `refresh` path — ~4s):

```text
uv run marketpulse validate-signal
```

It runs the circular-shift null test for rank persistence and writes
`reports/persistence_20.png`. It prints the observed value, the null mean and
standard deviation, the percentile, and how many sessions were actually used.
It sets no threshold and reaches no verdict — reading the number is your job.

`chart` with no `--start` overwrites `reports/rotation_latest.png`. Dated PNGs require `--start`.

Daily Brief groups the same RS20 ranks into **領先 / 改善 / 轉弱 / 落後** (改善 first). Classification uses only Rank and Δ5; `value_thrust` and `breadth` are annotations.

Sector Radar Rank is a single cell holding three independent ranks, shortest window first: `R5·#R20·R60` (e.g. `3·#1·7`). The middle one is the primary rank and is the only one marked — bold in HTML, a `#` prefix in plain text. They are never merged into one number and never summarised by an arrow: the information is in the *shape* of the three, not in any one of them. Brief and Radar use the identical presentation. **Rotation** is rank vs the previous session — a change in relative rank, not a claim about capital flow. **Momentum** is a display-only Strong / Improving / Stable / Weakening / Weak label from 5D, Breadth, Volume, and Rank Δ5 (Unknown if that 5-session history is missing). It is not a score and does not change Rank.

Each sector's detail view also shows **Rank Trend (last 20 sessions)**: the theme's RS20 rank for each of the last 20 available sessions up to the current date, so a persistent climb or slide is visible without cross-referencing the Timeline PNG. It reuses the existing snapshot history (no new storage) and is PIT-safe — only sessions on or before the current date are shown.

The Rank Timeline is a **step plot** of daily RS20 rank (rank 1 at the top). The title shows the **effective** RS20 window (after the 20-session lookback), not the raw download start. The last session is labeled `theme + RS20 + Δ5` so you do not have to match colors in a legend.

`MISSING_DATA` still computes RS20 from valid members, but Brief prefixes `*` and Timeline uses a hollow marker. Treat those rows as incomplete, not a full-theme signal.

Raw official JSON is stored locally under `data/raw/` and is not redistributed.

## Important

These documents intentionally replace the previous design.

Do not merge the old architecture back into the MVP incrementally.
