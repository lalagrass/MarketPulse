# MarketPulse MVP Design v0.2

> **STATUS: REPLACEMENT SPECIFICATION**
>
> This document intentionally replaces the previous `docs/design-v0.1.md`.
> Do not incrementally preserve the previous architecture.
> If a previous design conflicts with this document, this document wins.
>
> **POST-MVP — READ THIS FIRST.** The MVP specified here was completed
> 2026-09-03 (§26). This document is no longer the whole current state: work
> after the MVP arrives as `docs/sprints/NNN-spec.md` and is folded back into
> the relevant section here, marked *(sprint NNN)*. Where a section carries such
> a marker, the marker is current and the surrounding original text is history.

## 0. Product Definition

MarketPulse is a **local, daily Taiwan stock theme-rotation radar**.

Its only MVP job is:

> Make relative leadership changes between a small set of Taiwan market themes visible and reproducible from daily price, trading value, and breadth data.

The product is **not** a prediction engine, trading system, quant research platform, technical-analysis library, or generic financial framework.

User intent (not an algorithm): top-down Taiwan theme observation — market regime, then themes, then rotation, then leaders inside a leading theme. Living method notes: `docs/marketpulse-methodology.md`. That file is not a spec; if it conflicts with this document, this document wins.

### MVP output

1. Daily Theme Brief
2. Theme Rank / Rotation Timeline
3. Sector Rotation Radar (ranking table + sector stock drill-down HTML)
4. Historical replay for validation of the visualization
5. Basic data-quality / future-leakage tests

### MVP deployment

- Apple Silicon Mac
- Single user
- Local execution
- Daily/end-of-day data
- No server
- No GUI requirement
- No real-time data

---

# 1. Non-Negotiable Principles

## 1.1 Reuse before implementation

Before implementing any generic financial indicator, charting method, or backtesting capability:

1. Check whether a mature open-source implementation exists.
2. Prefer reuse over reimplementation.
3. Do not invent a new formula unless it is genuinely MarketPulse-specific domain logic.
4. Do not optimize arbitrary weights or thresholds in MVP.

Preferred reuse:

- `pandas` for rolling calculations, aggregation, ranking and tabular processing.
- `pandas-ta-classic` or another selected mature TA package for standard technical indicators when needed.
- Existing RRG implementation such as RRG-Lite for optional RRG visualization.
- `matplotlib` for the MVP static Timeline if the RRG package does not provide the desired chart.

`pandas-ta-classic` is a community-maintained Python TA library with 200+ indicators and an MIT license; use it instead of writing standard indicators from scratch. See: https://github.com/xgboosted/pandas-ta-classic
`pandas-ta` is an alternative mature implementation with 130+ indicators. See: https://github.com/JameRawlings/pandas-ta

**Do not add a dependency merely because it has many features. Use the smallest useful surface.**

## 1.2 MarketPulse owns semantics, not generic mathematics

MarketPulse owns:

- Taiwan market data adapters
- Theme taxonomy
- Theme membership
- Stock → Theme aggregation
- Point-in-time/as-of rules
- Theme ranking semantics
- Rotation Timeline
- Historical replay semantics

MarketPulse does NOT own:

- SMA implementation
- generic ROC implementation
- generic momentum indicators
- RRG mathematics
- generic backtesting framework
- generic charting framework

## 1.3 No composite score in MVP

There is **no `rotation_score` in the MVP product path**.

Do not implement:

- weighted rank-of-rank score
- score weights
- score optimization
- custom factor score
- custom normalized composite

Theme strength is simply ranked by **RS20**.

---

# 2. MVP Architecture

```text
                 TWSE / TPEx official EOD data
                              |
                              v
                    +-------------------+
                    | Data Normalizer   |
                    +---------+---------+
                              |
                              v
                    +-------------------+
                    | Theme YAML        |
                    | 11 fixed themes   |
                    +---------+---------+
                              |
                              v
                    +-------------------+
                    | Theme Aggregation |
                    +---------+---------+
                              |
             +----------------+----------------+
             |                |                |
             v                v                v
        Theme Return       Breadth         Value Share
             |                |                |
             +----------------+----------------+
                              |
                              v
                    +-------------------+
                    | Existing Methods  |
                    | RS / SMA / rank   |
                    +---------+---------+
                              |
                              v
                    +-------------------+
                    | Theme Rank (RS20) |
                    +---------+---------+
                              |
                  +-----------+-----------+
                  |                       |
                  v                       v
             Daily Brief             Rank Timeline
                                          |
                                          v
                                    Optional RRG
```

---

# 3. Data Scope

## 3.1 Universe

MVP covers:

- TWSE listed common stocks
- TPEx listed common stocks

Exclude:

- ETFs
- ETNs
- TDRs
- warrants
- preferred shares
- other non-common instruments
- emerging-market instruments unless explicitly added later

## 3.2 Required daily fields

```text
date
market
symbol
open
high
low
close
volume
trading_value
```

TAIEX benchmark:

```text
date
close
```

## 3.3 Data source

Canonical source:

- TWSE official dated end-of-day data
- TPEx official dated end-of-day data

MVP should first prove that the required historical range can be obtained from the public official sources.

Do not introduce a paid data vendor until the official-source spike demonstrates a real blocker.

Do not use yfinance or third-party sources as the canonical Taiwan data source.

---

# 4. Storage

Keep storage simple.

Preferred:

```text
raw/
normalized/
snapshots/
```

Use Parquet for immutable analytical data.

SQLite may be used as a small local working cache if implementation benefits from it.

Do not introduce:

- PostgreSQL
- Redis
- DuckDB as a mandatory service
- Kafka
- object storage
- cloud infrastructure

The system is a local daily batch tool.

---

# 5. Theme Taxonomy

MarketPulse's primary proprietary/domain artifact is the Theme taxonomy.

Use one frozen MVP file:

```text
themes/v1.yaml
```

It contains exactly 11 themes.

Example:

```yaml
themes:
  optical:
    name: 光通訊
    members:
      - "3081"
      - "3363"

  pcb:
    name: PCB
    members:
      - "XXXX"
```

The actual membership list is maintained separately from the calculation engine.

## 5.1 Important

Theme membership is an analytical classification, not an official exchange classification.

Theme overlap is allowed.

A stock may belong to multiple themes.

---

# 6. Point-in-Time Rule

The MVP needs PIT protection only for **market data**, not historical reconstruction of today's taxonomy.

For signal date `T`:

```text
price/volume data <= T
```

Theme membership used for `T`:

```text
membership known by T-1
```

This prevents a newly added stock from contributing to the signal on the same day it was added.

## 6.1 Historical taxonomy disclosure

MVP replay uses the current frozen `themes/v1.yaml` against historical data.

This is:

> historical visualization replay

It is NOT:

> proof that the theme list was known at the historical date.

Every replay report must say so.

Do not build a historical taxonomy/event system in MVP.

---

# 7. Theme Calculations

## 7.1 Constituent return

For each member:

```text
return_N = close[T] / close[T-N] - 1
```

Use an existing standard return implementation where practical.

## 7.2 Theme return

MVP uses **equal-weight constituent return**.

```text
theme_return_N = mean(valid member return_N)
```

Why:

- simple
- transparent
- no additional market-cap dataset
- no custom weighting methodology
- easy to validate

Do not build value-weighted theme return in MVP.

Trading value is a separate signal.

---

# 8. Relative Strength

Primary strength metric:

```text
RS20 = theme_return_20 - TAIEX_return_20
```

Supporting metrics, computed and displayed alongside *(sprint 002)*:

```text
RS5  = theme_return_5  - TAIEX_return_5
RS60 = theme_return_60 - TAIEX_return_60
```

RS20 is the **only primary ranking metric**. `rank` is, and remains,
`cross_sectional_rank(RS20)`.

`rs5` and `rs60` each carry their own independent cross-sectional rank
(`rank_rs5`, `rank_rs60`). All three are displayed side by side and none is
selected over the others — the same formula at three parameters, leaving no
tunable handle. This is **not** a composite score; see coding-contract §5.

### Measured scale limitation *(sprint 002)*

Rank persistence falls off sharply with the horizon. On 161 sessions:

```text
k=1    0.945
k=5    0.773
k=20   0.282     observed 0.2141 vs null 0.0409 +/- 0.2948 -> percentile 81.0
```

*[SUPERSEDED 2026-09-05, sprint 003 DO-4/DO-5/backfill.]* The percentile line
above was withdrawn: the null that produced it sampled shifts from a range
whose lower bound was the degenerate self-comparison (`s = k`, where the
partner index equals the current index and the correlation is exactly 1.0),
giving it a fat right tail by construction and biasing every percentile
downward.

*[SUPERSEDED 2026-09-06, sprint 004 follow-up — aligned sample + σ/exceedance
display.]* The sprint 003 corrected measurement (329 sessions, k=20 ≈ 1.0σ /
p84.6) used a shorter sample whose null width and by_k windows were not yet
aligned; display also relied on a saturating percentile. Replaced by:

**Measured result, sprint 004 follow-up, 367 sessions (2024-12-27 → 2026-09-03),
retained_fraction 69.25%:**

```text
k     observed   null              distance      exceedance   n_days_used
1     0.9307     0.0590 ± 0.0254     +34.36σ      0/1000          386
5     0.7167     0.0602 ± 0.0258     +25.44σ      0/1000          382
20    0.1404     0.0637 ± 0.0270      +2.84σ      0/1000          367
```

**讀法是 B＋C，不是「證實了」。** 20 日排名持續性 0.14，在 367 個 session 上高出其
循環位移虛無 2.8σ，1000 次位移沒有一次追上。這代表月尺度排名帶有可偵測的結構，
不代表它穩定。1 日（34σ）與 5 日（25σ）遠強於它——真正的讀數是結構隨天期急速
衰減。此數字在凍結成分股上量得（non-goals D6），該偏誤方向為高估。

RS60 still honestly describes what happened over the last 60 days; a month-scale
rank *ordering* is not a structure you can lean on. Display reports σ distance +
exceedance count, not percentile (see `docs/sprints/004-evidence.md`).

Primary ranking window: Q7 resolved as (a) — keep RS20; see
`docs/product/open-questions.md`.

No composite score.

---

# 9. Theme Rank

For each trading day:

```text
rank themes by RS20 descending
```

Example:

```text
Theme        RS20       Rank
Optical      +18.2%       1
CCL          +13.7%       2
PCB          +11.1%       3
Passive       +7.8%       4
Thermal       +6.2%       5
AI Server     +3.1%       6
```

Rank is ordinal.

Rank is not a magnitude.

Do not imply that rank #1 is "twice as strong" as rank #2.

---

# 10. Rank Movement

Display-only derived fields:

```text
rank_delta_5
rank_delta_20
```

Interpretation:

```text
positive = moved upward
negative = moved downward
```

These are not additional prediction signals in MVP.

---

# 11. Trading Value Share

For each theme:

```text
theme_value_share =
    sum(member trading_value)
    /
    sum(unique market stock trading_value)
```

A stock belonging to multiple themes is counted fully in each theme numerator.

The market denominator counts each stock once.

Therefore theme shares may sum to more than 100%.

This is intentional because the themes represent overlapping narratives.

---

# 12. Value Thrust

Optional supporting display:

```text
value_thrust =
    value_share[T] / SMA20(value_share) - 1
```

Use standard rolling mean functionality.

Value thrust does NOT influence the primary rank.

If implementation complexity becomes material, omit it from the first executable slice.

---

# 13. Breadth

Primary breadth definition:

```text
breadth =
    count(Close > SMA20(Close))
    /
    count(valid members)
```

This answers:

> Is the theme move broad, or driven by only a few stocks?

Use a standard SMA implementation.

Do not invent additional breadth formulas in MVP.

---

# 14. MVP Theme Snapshot

The minimum daily record is:

```text
date
theme_id

return_20
rs20
rank

rank_delta_5
rank_delta_20

value_share
breadth
```

Present since *(sprint 002)* — three independent ranks, side by side:

```text
rs5
rs60
rank_rs5
rank_rs60
```

Optional:

```text
return_1
return_5
return_60
rank_delta_1
above_count
volume_ratio
value_thrust
member_count
missing_count
status
```

A second daily record, `data/snapshots/market_daily.parquet` *(sprint 001)*,
holds market-level signal-quality statistics — `rank_persistence_k`, turnover
and dispersion — one row per session. It is diagnostic output about the signal,
not an input to it, and nothing in the ranking path reads it.

`volume_ratio` = theme volume[T] / SMA20(theme volume). Display as `1.8x`.
Radar Breadth shows `above_count / member_count` (same Close > SMA20 definition as `breadth`).

Do NOT include:

```text
rotation_score
rank_momentum
market_regime
theme_regime
leader_score
alpha_score
confidence_score
```

---

# 15. Rotation Timeline

This is the primary product visualization.

X-axis:

```text
date
```

Y-axis:

```text
theme rank
```

Use fixed 11-theme ordering/scale.

Example:

```text
Rank
 1 |                         Optical
 2 |                    _____/
 3 |               PCB _/
 4 |          CCL __/
 5 |
 6 | AI Server  \________
 7 |
   +--------------------------------
      May       Jun       Jul   Aug
```

The Timeline means:

> relative leadership changed over time.

It does NOT prove:

> capital literally flowed from theme A into theme B.

The chart should make this distinction clear in accompanying text.

---

# 16. Optional RRG

RRG is an optional visualization, not the MarketPulse core algorithm.

If included:

```text
MarketPulse theme data
        |
        +--> RS
        |
        +--> RS momentum
                 |
                 v
          Existing RRG implementation
```

Prefer an existing implementation such as RRG-Lite rather than implementing RRG from scratch.

RRG-Lite:
https://github.com/BennyThadikaran/RRG-Lite

If integration is awkward or adds significant dependency complexity, skip RRG for MVP.

The Rank Timeline is sufficient for MVP completion.

---

# 17. Daily Brief

The Brief is a **display-only** grouping of the same RS20 rank table.
It does not change RS20, rank, or Timeline.

Classification uses only Rank and Δ5:

```text
領先: rank ≤ 3 and Δ5 ≥ 0
改善: rank ≥ 4 and Δ5 ≥ +2
轉弱: rank ≤ 3 and Δ5 ≤ −2
其餘: 落後
NaN rank or NaN Δ5 → 落後
```

Block order: 改善 → 領先 → 轉弱 → 落後. Omit empty blocks.
Within a block: rank ASC, then theme_id ASC.

`value_thrust` and `breadth` are annotations. They do not affect classification.
Do not print a Value% column. Do not print a composite score.

Minimum output:

```text
MarketPulse — YYYY-MM-DD

Theme Rotation  領先 / 改善 / 轉弱 / 落後
分類只用 Rank 與 Δ5。value_thrust、breadth 為附註。

改善
 被動元件            #6  Δ5   +3  RS20  +14.5%
                     thrust  +11.0%  breadth  57.1%

領先
 光通訊/CPO          #1  Δ5   +1  RS20  +42.8%
                     thrust   -4.3%  breadth 100.0%

轉弱
 ...

落後
 高速材料/CCL        #2  Δ5   -1  RS20  +39.2%
                     thrust   -4.6%  breadth  50.0%
```

A theme at rank #2 with Δ5 = −1 is 落後, not 領先.
This table should be understandable without knowing the implementation.

---

# 17.5 Sector Momentum State (Radar)

Display-only on the Sector Rotation Radar. Does **not** change RS20, Rank, Brief, or Timeline.

**Rotation** (already on the table) answers: did the sector move up or down in the ranking vs the previous session? (`rank_delta_1`)

**Momentum** answers: is the sector's current strength expanding, stable, or fading?

Reuse existing snapshot fields only. Compare the current row with the same theme 5 sessions earlier. Do not add RSI, MACD, a new indicator, or a Momentum Score.

Directions (↑ / ↓ / →) from:

```text
5D:      sign of return_5; ↓ also if return_5 dropped ≥ 2pp vs 5 sessions ago
20D:     sign of return_20 (level, shown as evidence)
Breadth: above_count vs 5 sessions ago
Volume:  volume_ratio ≤ 0.8 ↓, ≥ 1.2 ↑, or a 0.20 move vs 5 sessions ago
Rank:    sign of rank_delta_5 (positive = moved up)
```

Classification, first match:

```text
Unknown:   missing rank, return_5, return_20, or rank_delta_5
Weakening: return_20 > 0 and at least two of {5D, Breadth, Volume, Rank Δ5} are ↓
Strong:    rank ≤ 3 and return_20 > 0 and 5D is not ↓ and
           (no ↓ among those four, or more ↑ than ↓)
Improving: rank ≥ 4 and 5D is ↑ and at least two ↑ and more ↑ than ↓
Weak:      rank ≥ 8 and fewer than two ↑, or return_20 ≤ 0 and 5D is ↓
Stable:    otherwise
```

The detail section must show the state plus those five evidence arrows. Rank remains `cross_sectional_rank(RS20)`.

---

# 18. CLI

Minimum CLI:

```text
marketpulse download
marketpulse validate
marketpulse analyze
marketpulse brief
marketpulse chart
marketpulse radar
marketpulse replay
marketpulse refresh
marketpulse validate-signal
```

`refresh` is the daily local batch: fetch trailing weekdays (including unusable empty files after the last complete session), validate, analyze, print Brief, write `reports/rotation_latest.png`, print the Sector Rotation table, write `reports/radar.html`.

`radar` prints the ranking table (1D / 5D / 20D / RS20 / Breadth / Volume / Rank / Rising·Falling·Stable / Momentum) and writes `reports/radar.html` with sector drill-down. Rank is still `cross_sectional_rank(RS20)`. Momentum is the display-only Strong / Improving / Stable / Weakening / Weak / Unknown state in §17.5. `--open` opens the HTML. Stock roles (Leader / Follower / Laggard) are terciles of member RS20 inside a theme; they do not change theme rank.

`validate-signal` *(sprint 002; display restated sprint 004)* runs the
circular-shift null test for `rank_persistence_k` and writes
`reports/persistence_20.png`. It is a one-off diagnostic, deliberately **not**
on the daily `refresh` path (~4s at `n_iter=1000`). It prints observed value,
null mean, null std, σ distance, exceedance count (`null>=obs`), and the number
of sessions actually used. It sets no threshold and draws no conclusion —
reading the number is the product owner's job.

It is not a scheduler. Do not add cron, notifications, or `doctor`.

`chart` with no `--start` uses the last 40 ranked sessions and writes `reports/rotation_latest.png`.
`chart --start YYYY-MM-DD` writes a dated `reports/rotation_{effective_start}_{effective_end}.png`.

Do not build:

```text
doctor
sync-groups
campaign
research
backtest
```

unless implementation proves they are genuinely necessary.

A small CLI is preferred.

---

# 19. Replay

Replay is required for MVP validation.

```text
marketpulse replay \
  --start YYYY-MM-DD \
  --end YYYY-MM-DD
```

For each historical day `T`:

```text
data <= T
membership <= T-1
calculate theme metrics
rank by RS20
save result
```

Replay must never read future bars.

---

# 20. Future-Leakage Tests

Only a few tests are mandatory.

## Test 1: Future bar mutation

Modify T+1 price/volume.

Expected:

```text
signal(T) unchanged
```

## Test 2: Membership mutation

A stock added after T must not contribute to theme T.

## Test 3: Historical replay

Replay result at T must use only allowed data.

## Test 4: Indicator sanity

Compare standard indicators against the selected OSS implementation / known reference values.

Do not create a new statistical validation framework.

---

# 21. Data Quality

MVP statuses:

```text
OK
MISSING_DATA
INSUFFICIENT_HISTORY
THIN
```

Do not build a large data-quality state machine.

Failures must be visible.

Never silently drop invalid rows.

---

# 22. Dependencies

Preferred minimum:

```text
python >= 3.12
uv
pandas
numpy
pyyaml
pyarrow
matplotlib
pytest
```

For standard TA:

```text
pandas-ta-classic
```

Only add it if the required indicators are actually used.

For RRG:

```text
RRG-Lite or another selected mature implementation
```

Do not add VectorBT, Backtrader, OpenBB, TA-Lib, or other large frameworks merely "for future use".

---

# 23. Open-Source Reuse Matrix

| Capability | MVP ownership | Preferred implementation |
|---|---|---|
| DataFrame operations | reuse | pandas |
| SMA | reuse | pandas-ta-classic / pandas |
| Standard return | reuse | pandas / pandas-ta-classic |
| Momentum | reuse | pandas-ta-classic |
| Cross-sectional rank | reuse | pandas |
| RRG | reuse | RRG-Lite / established implementation |
| Static chart | reuse | matplotlib |
| Theme taxonomy | MarketPulse | YAML |
| Stock → Theme aggregation | MarketPulse | small custom module |
| RS20 definition | MarketPulse | one-line domain formula |
| Rank Timeline | MarketPulse | small custom chart |
| PIT/as-of | MarketPulse | small custom logic |
| Replay | MarketPulse | small custom logic |

### Rule

If an OSS package only saves a few lines but introduces a large dependency or unclear maintenance risk, use the simpler native implementation.

Reuse is a means to reduce risk, not a goal by itself.

---

# 24. Explicitly Forbidden in MVP

The following are forbidden unless this specification is intentionally revised:

```text
rotation_score
weighted signal score
rank-of-rank composite
custom factor
ML
prediction model
portfolio optimization
market regime classifier
six-state theme regime
5-theme production baseline
leader detection
52-week high filter
watchlist
stock recommendations
real-time data
broker API
Streamlit
web dashboard
cloud deployment
database server
historical taxonomy reconstruction
automatic scheduling
notification
backtest framework
custom TA indicator implementations
custom RRG implementation
```

---

# 25. Research / Phase 2

Only after the first useful Timeline exists:

```text
H1/H2/H3/H4
5-theme comparison
historical taxonomy
theme regime labels
market regime
leader overlay
forward-return analysis
sensitivity analysis
RRG enhancement
```

Research must not silently modify the MVP signal.

---

# 26. Definition of Done

> **ACHIEVED 2026-09-03.** All 14 items below are satisfied.
> Evidence: `uv run marketpulse refresh` runs the full chain end to end;
> `data/snapshots/theme_daily.parquet` plus three replay snapshots exist;
> `tests/test_replay.py` and `tests/test_future_mutation.py` cover items 11–12;
> `reports/radar.html` and `reports/rotation_latest.png` cover item 13.
>
> The closing instruction ("At this point, stop") was the **MVP build-phase**
> stop condition and has been met. Post-MVP work is scoped by
> `docs/sprints/NNN-spec.md`.

MVP is complete when all are true:

1. Official TWSE + TPEx daily data can be acquired for the required test period.
2. Data is normalized and stored locally.
3. 11-theme YAML loads successfully.
4. Theme returns calculate successfully.
5. RS20 calculates successfully.
6. Themes rank by RS20.
7. Value share calculates correctly with overlapping themes.
8. Breadth calculates correctly.
9. Daily Brief is generated.
10. Rotation Timeline PNG is generated.
11. Historical replay generates the same result deterministically.
12. Future-bar mutation does not alter earlier signals.
13. A human can look at the Timeline and answer:
   - Which themes are strong?
   - Which themes are improving?
   - Which themes are weakening?
   - Which themes have moved in rank?
14. No custom composite score is required.

**At this point, stop. Do not add features before using the product.**

*[Build-phase instruction, satisfied 2026-09-03. Note that the advice in its
second half — use the product before adding to it — was not a build-phase
constraint and still stands.]*

---

# 27. Success Criterion

The MVP is not successful because it has many metrics.

It is successful if a user can open the output and immediately see something like:

```text
May
AI Server
   ↓
June
Optical / CPO
   ↓
July
PCB / CCL
   ↓
August
Passive / Thermal
```

and then drill into the underlying:

```text
RS20
Value Share
Breadth
Rank movement
```

to understand why the visual changed.

That is MarketPulse.

