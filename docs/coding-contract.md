# MarketPulse MVP Coding Contract v0.2

> **REPLACEMENT CONTRACT**
>
> This contract replaces the previous coding contract.
> Do not preserve previous implementation plans merely because they are documented there.

## 1. Source of truth

Use this order:

1. `docs/design-v0.2.md`
2. this file
3. repository code
4. older design documents only as historical context

If an older document conflicts with v0.2, ignore the older document.

## 2. First implementation goal

Build the smallest end-to-end vertical slice:

```text
official data
  -> normalize
  -> 11 themes
  -> theme return
  -> RS20
  -> rank
  -> Daily Brief
  -> Timeline PNG
```

Do not implement the whole architecture.

## 3. Mandatory OSS-first behavior

Before implementing any generic indicator:

- search for a mature existing implementation;
- document the selected dependency;
- use it if it reduces implementation/validation risk.

Do not write your own:

- SMA
- generic ROC
- generic momentum
- generic TA indicator
- RRG
- generic backtest engine

Use pandas / pandas-ta-classic / an established RRG implementation where appropriate.

## 4. MarketPulse-specific code

Keep custom code focused on:

```text
data adapters
theme YAML
theme membership
theme aggregation
RS20 domain calculation
theme ranking
PIT/as-of rules
replay
Timeline
```

## 5. No composite score

Do not implement:

```text
rotation_score
rank_momentum score
weighted score
confidence score
alpha score
```

Primary rank:

```text
rank = cross_sectional_rank(RS20)
```

## 6. No premature abstraction

Do not create:

- generic provider frameworks
- plugin systems
- dependency injection containers
- generic indicator registries
- event buses
- strategy frameworks
- generic research engines

unless a concrete MVP use case requires them.

Prefer small modules and direct functions.

## 7. Data rules

For signal date T:

```text
price/volume <= T
membership <= T-1
```

Never use future data.

Do not silently substitute current membership for historical membership without following the documented replay rule.

MVP replay uses the current frozen 11-theme YAML and must disclose that this is visualization replay, not historical knowledge reconstruction.

## 8. Raw price rule

Use raw daily close consistently for MVP.

Do not introduce adjusted-price data into the MVP signal path.

If corporate actions cause visible anomalies, report them; do not silently change the price methodology.

## 9. Testing

Minimum tests:

- data normalization
- theme aggregation
- RS20 formula
- rank ordering
- value-share overlap behavior
- breadth
- future mutation
- deterministic replay

Tests should be small and deterministic.

## 10. Current implementation slices

### Slice A — Data spike

Prove:

```text
TWSE dated EOD
TPEx dated EOD
TAIEX
```

for 20–30 trading days.

Do not build the full historical downloader before this works.

### Slice B — Core calculation

Implement:

```text
theme return
RS20
rank
value share
breadth
```

### Slice C — Product output

Implement:

```text
brief
timeline
```

### Slice D — Replay

Implement historical replay and future-mutation test.

Then stop.

## 11. Do not implement yet

```text
RRG
market regime
theme regime
5-theme baseline
H1-H4
leaders
watchlist
Streamlit
notifications
scheduling
cloud
backtesting frameworks
```

RRG may be added only after the Rank Timeline works, and should reuse an established implementation.

## 12. Code quality

Prefer:

- Python 3.12+
- type hints
- small pure functions
- explicit DataFrame schemas
- deterministic output
- pytest
- uv

Avoid:

- speculative abstractions
- metaprogramming
- complex class hierarchies
- hidden global state

## 13. Agent stop condition

After Definition of Done in `design-v0.2.md` is satisfied:

**STOP.**

Do not continue implementing Phase 2 because older documents mention it.

Report:

- what was implemented
- what was reused
- what was intentionally not implemented
- how the Timeline looks
- any data-source limitations
