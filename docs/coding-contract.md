# MarketPulse MVP Coding Contract v0.2

> **STATUS — 2026-09-04**
>
> The MVP described by this contract is **complete**. All 14 Definition-of-Done
> items in `docs/design-v0.2.md` §26 are satisfied (Slices A–D shipped).
>
> Sections marked *[BUILD PHASE — COMPLETE]* below were instructions for
> constructing the MVP. They are retained for traceability and are **no longer
> current directives**. Do not read them as "stop working on this project."
>
> Rules that remain in force: §1, §3–§9, §12.
> Work after the MVP is governed by sprint specs under `docs/sprints/`.
> Open contradictions found during this review are listed in
> `docs/product/open-questions.md` — they are decisions, not facts, and are
> resolved by the product owner, not by whoever reads this file.
>
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

*[BUILD PHASE — COMPLETE 2026-09-03. The slice below ships and runs daily via
`uv run marketpulse refresh`. Retained for traceability.]*

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

*[AMENDED 2026-09-04 — see non-goals D8]*

Do not write your own:

- generic momentum
- generic TA indicator beyond a thin pandas wrapper
- RRG
- generic backtest engine

**Amendment:** standard series operations that are a direct pandas expression —
SMA (`rolling().mean()`) and N-day return (`shift()`) — may be written inline as
thin, tested wrappers rather than pulling in a dependency. `calc.py:88,93` are
these. pandas-ta-classic is reserved for indicators beyond that level, and is
not currently a dependency. Anything more involved than a one-line pandas
expression still requires searching for an existing implementation first.

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
radar table / sector drill-down
momentum / trend state (display-only)
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

*[CLARIFIED 2026-09-05 — sprint 002]* The same formula evaluated at several
window lengths, with **every** result displayed side by side and none selected,
is not a composite score. `rank_rs5` / `rank / rank_rs20` / `rank_rs60` are
three independent cross-sectional ranks; they are not averaged, weighted, or
collapsed into an arrow or a direction marker. The test that separates the two
cases is **whether the addition leaves a tunable handle**: parallel parameters
leave none, an invented blend is a weight by construction. Picking the
best-looking window after the fact would break this section; showing all of them
does not.

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
- volume ratio
- rank change
- leader / follower / laggard
- momentum state (Strong / Improving / Stable / Weakening / Weak / Unknown)
- future mutation
- deterministic replay
- signal-quality statistics *(sprint 001)*
- persistence null test: reproducible under a fixed seed, k=1 sanity check
  *(sprint 002)*
- all three ranks obey the same ordering rules *(sprint 002)*

Tests should be small and deterministic.

**Not coverable by tests.** Acceptance criteria about what a human sees
("the middle rank must be visually marked") pass automatically no matter what
the page renders. Sprint 002 shipped a silent failure of exactly this kind and
caught it by looking, not by testing. Such criteria are verified by eye and
reported to the product owner; do not treat a green suite as evidence for them.

### 9.1 Tests that read the real `narratives/` directory

`narratives/` is data the product owner edits. A test that asserts on it will
break whenever a new snapshot lands — which is not a regression, it is the
product being used. Two rules, both earned:

- **Pin `as_of` to a date that a future snapshot cannot overtake.** Use a date
  at or before the newest snapshot the test is about, never "today" and never
  the latest price day.
- **Assert inclusion, not equality**, unless the test's whole point is that a
  dated snapshot must never be edited in place (see below).

```text
條文：斷言真實 narratives/ 的測試，as_of 釘在不會被新快照追上的日期，斷言用包含式
起因：009 拍板 3（pending 測試脆弱，98e7198 改成 inclusion）——只修了一半
物證：014 的 test_do3_real_narratives_are_all_still_conditional 用 as_of=2026-09-08，
      PO 在同一天寫下 narratives/2026-09-08.yaml，測試立刻紅。
      同一輪的 test_do1_real_narratives_branch_members_unchanged 釘在 2026-09-06，
      新快照追不上，仍然綠
重看：下一次 PO 寫快照之後
```

**The one deliberate exception:** a test that pins an *older* snapshot with an
equality assertion is a guard for "dated snapshots are never edited in place"
(design §28.4), not a fragile test. `test_do1_real_narratives_branch_members_unchanged`
is one of these. Keep it, and say so in its docstring.

## 10. Current implementation slices

*[BUILD PHASE — COMPLETE. Slice A–D all shipped; see `docs/sprints/` for the
reports. Retained for traceability. The "Then stop" below ended the MVP build,
not the project.]*

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
refresh
radar
```

`refresh` is a local daily alias (download trailing → validate → analyze → brief → default chart → radar HTML). Not scheduling.
`radar` is the Sector Rotation table + HTML drill-down. Rank remains RS20. Leader/Follower/Laggard is stock sort inside a theme, not a new score. Momentum / Trend State is a display-only label from 5D, Breadth, Volume, and Rank Δ5; it is not a score and does not change Rank.

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
watchlist
Streamlit
notifications
scheduling
cloud
backtesting frameworks
```

*[AMENDED 2026-09-04]* The former conditional — "RRG may be added only after the
Rank Timeline works" — is **withdrawn**. The Rank Timeline does work, which under
that wording would have unlocked RRG by default. RRG is now an explicit non-goal
(see `docs/product/non-goals.md` D3): `rank` + `rank_delta_5` already cover the
useful part of the two-axis idea, and RRG adds visual complexity rather than
information. Reversing this needs a stated reason in a sprint report, like any
other default.

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

## 13. Agent stop condition (MVP build phase)

*[BUILD PHASE — COMPLETE. This condition was met on 2026-09-03. It is history,
not a current directive.]*

**Superseded by:** post-MVP work is scoped one sprint at a time by a spec under
`docs/sprints/NNN-spec.md`. An agent's stop condition is now "the current sprint
spec is satisfied" — not this section.

The original condition, retained for traceability:

> After Definition of Done in `design-v0.2.md` is satisfied:
>
> **STOP.**
>
> Do not continue implementing Phase 2 because older documents mention it.

Report:

- what was implemented
- what was reused
- what was intentionally not implemented
- how the Timeline looks
- any data-source limitations
