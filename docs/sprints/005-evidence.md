# Sprint 005 — Evidence

Branch: `sprint/005-horizon-ic` (not merged to `dev`)
As of: 2026-09-06 02:31 CST

## Commits

| DO | Hash | Subject |
|---|---|---|
| plan | `f49b3ba` | docs(sprint-005): PO plan — Rank-IC, above_count NaN, B+C footnote |
| DO-1 | `d9479ed` | feat(quality): rank-ic forward IC matrix CLI |
| DO-2 | `9ac4ef7` | fix(calc): above_count NaN when all members NaN |
| DO-3 | `aa6b563` | feat(product): B+C horizon footnote on quality_line |
| docs | `c17b1e4` | docs: 005-evidence |

Full hashes:

- `f49b3ba44a3006e68e44fd89e8daa3da0cb1b8d5`
- `d9479ed9dfd8a2fa869bdc28c939a6106d7ecb80`
- `9ac4ef724f4e7bb1e681d4e970484eb5d568d406`
- `aa6b563dd9011e64b41280fc04a929556370d6c5`
- `c17b1e4` (evidence; full hash on git log)

## pytest

```text
140 passed in 26.10s
```

Command: `uv run pytest`

## `git diff dev --stat`

```text
 docs/product/backlog.md    |  31 +++++++---
 docs/sprints/004-report.md |  48 +++++++++++++++
 docs/sprints/005-report.md |  74 +++++++++++++++++++++++
 docs/sprints/005-spec.md   | 124 ++++++++++++++++++++++++++++++++++++++
 docs/sprints/README.md     |   1 +
 marketpulse/calc.py        |   9 ++-
 marketpulse/cli.py         |  22 +++++++
 marketpulse/quality.py     | 145 ++++++++++++++++++++++++++++++++++++++++-----
 marketpulse/radar.py       |   2 +-
 tests/test_breadth.py      |  55 +++++++++++++++++
 tests/test_product.py      |  21 +++++++
 tests/test_quality.py      |  18 ++++++
 tests/test_rank_ic.py      | 100 +++++++++++++++++++++++++++++++
 13 files changed, 626 insertions(+), 24 deletions(-)
```

(After this evidence commit, `docs/sprints/005-evidence.md` is also in the diff.)

## DO-1 — Rank-IC 3×3 (real snapshot)

Command: `uv run marketpulse rank-ic`  
Snapshot as_of: `2026-09-03` (theme_daily). Forward excess = `rs_h` at T+h (theme h-day return − TAIEX h-day return). Not on `refresh`; does not write null JSON.

```text
restated (frozen membership applied historically; not as-of / point-in-time)
forward Rank-IC  Spearman(RS_k[T], excess_h[T→T+h])
k\h                        5                    20                    60
5     +0.0338 n=397 se=0.0181+0.0840 n=382 se=0.0183+0.0712 n=342 se=0.0199
20    +0.0985 n=382 se=0.0182+0.1404 n=367 se=0.0221+0.1611 n=327 se=0.0196
60    +0.0851 n=342 se=0.0211+0.1402 n=327 se=0.0224+0.1951 n=287 se=0.0202
as_of=2026-09-03  cells=9
```

Determinism: `compute_rank_ic` / `format_rank_ic_table` covered by `tests/test_rank_ic.py::test_rank_ic_is_deterministic`. Synthetic monotone → IC ≈ +1; shuffled → |mean IC| < 0.25.

## DO-2 — above_count all-NaN → NaN

Tests (new in `tests/test_breadth.py`):

- `test_above_count_all_nan_row_is_nan_not_zero` — 10 sessions (< SMA20) → every `above_count` is NaN (was false 0).
- `test_above_count_mixed_true_false_still_counts` — mixed True/False still sums to 1.

Fix: `above[...].sum(..., skipna=True, min_count=1)` plus `pd.to_numeric` so object-dtype None becomes float NaN.

## DO-3 — B+C footnote

Locked string (literal):

```text
月尺度：可偵測≠穩定；短端遠強於長端；凍結成分偏高估（D6）。
```

Policy (spec default): always append when `market_row` is present, even without null baseline. Omitted when `market_row is None`.

Brief snippet (`uv run marketpulse brief`):

```text
MarketPulse — 2026-09-03
持續性 .11 虛無 .06±.03 +2.8σ 0/1000   換手 10 (80%)   離散 14.1pp (7%)
月尺度：可偵測≠穩定；短端遠強於長端；凍結成分偏高估（D6）。

Theme Rotation  領先 / 改善 / 轉弱 / 落後
```

## Deviations / notes

- No new dependencies; `themes/v1.yaml` and L2 schema untouched; not merged to `dev`.
- Forward IC reuses snapshot `rs5`/`rs20`/`rs60` (Spearman via Pearson-of-ranks, same no-scipy pattern as persistence).
- Radar `.quality` CSS: `white-space: pre-line` so the footnote newline renders below in HTML (terminal brief already shows a second line).
