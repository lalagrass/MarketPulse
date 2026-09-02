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
RS20 + Value Share + Breadth
    ↓
Theme Rank
    ↓
Daily Brief + Rotation Timeline
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
- `docs/gooaye-method.md` — 股癌觀測方法筆記（不是規格；如何更新見文內 §8）

## OSS

- pandas-ta-classic: https://github.com/xgboosted/pandas-ta-classic
- pandas-ta: https://github.com/JameRawlings/pandas-ta
- RRG-Lite: https://github.com/BennyThadikaran/RRG-Lite

## Run

```text
uv sync --extra dev
uv run marketpulse download --start 2026-07-20 --end 2026-08-31
uv run marketpulse validate
uv run marketpulse analyze
uv run marketpulse brief
uv run marketpulse chart
uv run marketpulse replay --start 2026-07-20 --end 2026-08-31
uv run pytest
```

Daily Brief groups the same RS20 ranks into **領先 / 改善 / 轉弱 / 落後** (改善 first). Classification uses only Rank and Δ5; `value_thrust` and `breadth` are annotations.

The Rank Timeline is a **step plot** of daily RS20 rank (rank 1 at the top). The title shows the **effective** RS20 window (after the 20-session lookback), not the raw download start. The last session is labeled `theme + RS20 + Δ5` so you do not have to match colors in a legend.

`MISSING_DATA` still computes RS20 from valid members, but Brief prefixes `*` and Timeline uses a hollow marker. Treat those rows as incomplete, not a full-theme signal.

Raw official JSON is stored locally under `data/raw/` and is not redistributed.

## Important

These documents intentionally replace the previous design.

Do not merge the old architecture back into the MVP incrementally.
