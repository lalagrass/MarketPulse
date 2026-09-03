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

## Documents

- `docs/design-v0.2.md` — replacement MVP design（產品規格；與此衝突時以它為準）
- `docs/coding-contract.md` — replacement coding contract
- `docs/reuse-plan.md` — OSS reuse boundary
- `docs/marketpulse-methodology.md` — 觀測方法論（不是規格；與設計衝突時以設計為準）

## OSS

- pandas-ta-classic: https://github.com/xgboosted/pandas-ta-classic
- pandas-ta: https://github.com/JameRawlings/pandas-ta
- RRG-Lite: https://github.com/BennyThadikaran/RRG-Lite

## Run

Daily update (after official EOD is published):

```text
uv sync --extra dev
uv run marketpulse refresh
uv run pytest
```

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

`chart` with no `--start` overwrites `reports/rotation_latest.png`. Dated PNGs require `--start`.

Daily Brief groups the same RS20 ranks into **領先 / 改善 / 轉弱 / 落後** (改善 first). Classification uses only Rank and Δ5; `value_thrust` and `breadth` are annotations.

Sector Radar Rank is still RS20. **Rotation** is rank vs the previous session. **Momentum** is a display-only Strong / Improving / Stable / Weakening / Weak label from 5D, Breadth, Volume, and Rank Δ5 (Unknown if that 5-session history is missing). It is not a score and does not change Rank.

The Rank Timeline is a **step plot** of daily RS20 rank (rank 1 at the top). The title shows the **effective** RS20 window (after the 20-session lookback), not the raw download start. The last session is labeled `theme + RS20 + Δ5` so you do not have to match colors in a legend.

`MISSING_DATA` still computes RS20 from valid members, but Brief prefixes `*` and Timeline uses a hollow marker. Treat those rows as incomplete, not a full-theme signal.

Raw official JSON is stored locally under `data/raw/` and is not redistributed.

## Important

These documents intentionally replace the previous design.

Do not merge the old architecture back into the MVP incrementally.
