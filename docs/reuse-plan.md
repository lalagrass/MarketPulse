# MarketPulse MVP Reuse Plan v0.2

## Purpose

This file exists to prevent the coding agent from rebuilding existing financial-analysis machinery.

## Reuse policy

MarketPulse should own only Taiwan-specific theme semantics and the minimal product logic.

## Candidates

### pandas

Use for:

- DataFrame operations
- rolling windows
- aggregation
- ranking
- joins
- missing-data handling

### pandas-ta-classic

Project:
https://github.com/xgboosted/pandas-ta-classic

Use when a standard TA indicator is required.

It currently provides a broad catalog of standard indicators and is MIT licensed.

MVP expected use:

- SMA20
- standard return/momentum if convenient

Do not install its optional backtesting/data-source extras.

### pandas-ta

Project:
https://github.com/JameRawlings/pandas-ta

Alternative mature implementation.

It provides 130+ indicators.

Use either `pandas-ta-classic` or `pandas-ta`, not both.

The agent should choose one based on current Python compatibility and maintenance quality.

### RRG-Lite

Project:
https://github.com/BennyThadikaran/RRG-Lite

Potential reuse for:

- RRG calculations
- RRG visualization

RRG is optional.

Do not block MVP on it.

### matplotlib

Use for the required static Rank Timeline.

No interactive plotting framework is required.

## What not to reuse

Do not introduce a large framework merely because it exists.

Examples:

- OpenBB
- VectorBT
- Backtrader
- QuantConnect
- Streamlit

These may be useful later, but they are not necessary for the MVP.

## What MarketPulse must implement itself

### Theme taxonomy

The 11 Taiwan themes are product-specific.

### Theme aggregation

Stock-level data must be transformed into theme-level data.

### Relative Strength

```text
RS20 = theme_return_20 - TAIEX_return_20
```

This is a tiny domain calculation and does not require a specialized library.

### Theme rank

```text
rank = rank(RS20)
```

Use pandas ranking.

### Rank Timeline

This visualization is the product's key differentiator.

### PIT / replay semantics

Generic TA libraries cannot know MarketPulse's membership-as-of rules.

These must remain MarketPulse code.

## Dependency acceptance rule

Add a package only if:

1. it solves a real MVP requirement;
2. it is mature enough for the use case;
3. it reduces rather than increases validation/maintenance burden;
4. its license is compatible with the project's intended use;
5. the feature cannot be more safely implemented as a few transparent lines.

## Important

"Reuse open source" does NOT mean "import a framework for every function."

For a one-line operation, native pandas is often safer than a dependency.

The goal is:

> reuse mature algorithms; keep MarketPulse-specific semantics tiny and explicit.
