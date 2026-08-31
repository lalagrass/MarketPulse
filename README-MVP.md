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

- `docs/design-v0.2.md` — replacement MVP design
- `docs/coding-contract.md` — replacement coding contract
- `docs/reuse-plan.md` — OSS reuse boundary

## OSS

- pandas-ta-classic: https://github.com/xgboosted/pandas-ta-classic
- pandas-ta: https://github.com/JameRawlings/pandas-ta
- RRG-Lite: https://github.com/BennyThadikaran/RRG-Lite

## Important

These documents intentionally replace the previous design.

Do not merge the old architecture back into the MVP incrementally.
