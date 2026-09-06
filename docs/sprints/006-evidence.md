# Sprint 006 — Evidence

Branch: `sprint/006-ic-null` (from `sprint/005-horizon-ic`; not merged to `dev`)
As of: 2026-09-06

## Commits

| DO | Hash | Subject |
|---|---|---|
| DO-3 | `767f85dcde1e01641c09c6d47b58f3c0c9f1ecbe` | fix(calc): above_count NaN when no members in above columns |
| DO-1 | `d2607f8bd34c64ae93a5e61223abce6c28e603d4` | feat(quality): circular-shift null for each Rank-IC cell |
| DO-2 | `d2607f8bd34c64ae93a5e61223abce6c28e603d4` | (same commit: ‡ mark, cyclic lag test, tautology removed) |
| docs | *(this file)* | docs: 006-evidence |

DO-1 and DO-2 share one commit because the table rewrite, the ‡ mark, and the cyclic pairing live in the same `format_rank_ic_table` / `_rank_ic_terms` change.

## pytest

```text
150 passed in 43.27s
```

Command: `uv run pytest`

(005 was `140 passed`. +9 in `tests/test_rank_ic.py`, +1 in `tests/test_breadth.py`.)

## `git diff sprint/005-horizon-ic --stat`

```text
 marketpulse/calc.py    |   2 +-
 marketpulse/cli.py     |  14 ++-
 marketpulse/quality.py | 324 +++++++++++++++++++++++++++++++++++++++++--------
 tests/test_breadth.py  |  36 ++++++
 tests/test_quality.py  |   6 +-
 tests/test_rank_ic.py  | 252 +++++++++++++++++++++++++++++++++++---
 6 files changed, 558 insertions(+), 76 deletions(-)
```

(After this evidence commit, `docs/sprints/006-evidence.md` is also in the diff.)

`persistence_null_test` is not in the diff hunks. The new path calls `_null_min_lag`, `_null_shift_candidates`, `MIN_RETAINED_FRACTION`, and `_row_wise_pearson`; it does not change them.

## DO-1 — nine-cell output (default `n_iter=1000`, seed=0)

Command: `uv run marketpulse rank-ic --data-dir /Users/chenyuying/workspace/MarketPulse/data`  
Snapshot: `theme_daily.parquet` 2024-12-27 → 2026-09-03, 407 sessions, as_of=2026-09-03.  
Wall clock: **67s** (`real 66.97`). Under the 5-minute report-and-stop line. `n_iter` default left at `NULL_TEST_ITER=1000`.

```text
restated (frozen membership applied historically; not as-of / point-in-time)
forward Rank-IC  Spearman(RS_k[T], excess_h[T→T+h])
circular-shift null on the forward side; seed=0
k\h                   5                                 20                                 60                
5     +0.0338                            +0.0840                            n/a retained 41%<50% (h=60 L=120)
      null +0.0138±0.0270                null +0.0245±0.0240                n=342                            
      +0.74σ  250/1000                   +2.48σ  11/1000                                                     
      n=397 ret=70.8%                    n=382 ret=70.8%                                                     

20    +0.0985                            +0.1404‡                           n/a retained 41%<50% (h=60 L=120)
      null +0.0263±0.0267                null +0.0460±0.0368                n=327                            
      +2.70σ  0/1000                     +2.57σ  0/1000                                                      
      n=382 ret=70.8%                    n=367 ret=70.8%                                                     

60    +0.0851                            +0.1402                            n/a retained 41%<50% (h=60 L=120)
      null +0.0487±0.0323                null +0.1084±0.0862                n=287                            
      +1.13σ  112/1000                   +0.37σ  249/1000                                                    
      n=342 ret=70.8%                    n=327 ret=70.8%                                                     

‡ 此格等同 rank_persistence_20，非獨立物證
as_of=2026-09-03  cells=9  n_iter=1000  seed=0
```

Output contains no `se=`, no `percentile`, no `顯著` / `significant`.

**Guard-fail cells.** Column h=60: `n/a retained 41%<50% (h=60 L=120)`. Locked template `retained {retained:.0%}<{threshold:.0%} (h={h} L={L})` with `L=_null_min_lag(h)=max(2h,60)=120`. n=407, retained 168/407 ≈ 41.3% < 50%. Observed n_days is still printed (`n=342` / `327` / `287`); null_mean / sigma / n_ge are not.

**Displacement side (open question 1).** Forward side, as the spec default. Vectorised ranking is fast enough (67s) that the other side was not tried.

**Observed identity (acceptance 2), real snapshot.** `rank_ic_null_test(..., n_iter=2).observed == compute_rank_ic(...).mean_ic` for all nine cells, including the three guard-fail ones (observed is still computed; only the null is withheld). Bit-identical, including `(20,20) = 0.14037651721575425`.

**UNKNOWN (spec: measure, do not investigate).** IC null centres on this sample are **not** the persistence +0.06:

| k,h | observed | null_mean | σ | n_ge |
|---|---|---|---|---|
| 5,5 | +0.0338 | +0.0138 | +0.74 | 250/1000 |
| 5,20 | +0.0840 | +0.0245 | +2.48 | 11/1000 |
| 20,5 | +0.0985 | +0.0263 | +2.70 | 0/1000 |
| 20,20 | +0.1404 | +0.0460 | +2.57 | 0/1000 |
| 60,5 | +0.0851 | +0.0487 | +1.13 | 112/1000 |
| 60,20 | +0.1402 | +0.1084 | +0.37 | 249/1000 |
| *,60 | n/a | — | — | guard |

Persistence k=20 null was +0.0637±0.0270. IC (20,20) null is +0.0460±0.0368 — same family, not the same pairing set (T range 0..n−h−1 vs k..n−1; re-ranked RS vs snapshot `rank`; forward-side shift vs replacing T−k with T+e). Spec said not to chase why the centre is off zero.

## DO-2 — lag alignment: sabotage, then revert

Pairing lives in `_rank_ic_terms`: `j = (i + h + e) % n`. Changed to `j = (i + e) % n` (`i+h` → `i`), ran the cyclic test, then restored.

**Sabotaged (must be red):**

```text
$ uv run pytest tests/test_rank_ic.py::test_cyclic_rotation_ic_follows_mod_three_lag -q --tb=short
F                                                                        [100%]
=================================== FAILURES ===================================
________________ test_cyclic_rotation_ic_follows_mod_three_lag _________________
tests/test_rank_ic.py:106: in test_cyclic_rotation_ic_follows_mod_three_lag
    assert row.mean_ic == pytest.approx(-0.5)
E   assert 1.0 == -0.5 ± 5.0e-07
E     
E     comparison failed
E     Obtained: 1.0
E     Expected: -0.5 ± 5.0e-07
=========================== short test summary info ============================
FAILED tests/test_rank_ic.py::test_cyclic_rotation_ic_follows_mod_three_lag
```

Every (k,h) became +1 (pairing a day with itself), so the h ≢ 0 (mod 3) cells that should be −0.5 failed. The old tiled-monotone test would have stayed green.

**Restored (must be green):**

```text
$ uv run pytest tests/test_rank_ic.py::test_cyclic_rotation_ic_follows_mod_three_lag -q --tb=short
.                                                                        [100%]
```

**`(20,20)` ≡ `rank_persistence_20`.** Same snapshot:

```text
IC (20,20) mean_ic = 0.14037651721575425  n=367
rank_persistence_20 mean = 0.14037651721575425  n=367
diff = 0.0
```

Cell prints `+0.1404‡` plus the locked footnote `‡ 此格等同 rank_persistence_20，非獨立物證`. Glyph is not `†` / `*` / `~` / `·`.

## DO-3 — above_count NaN + column gap

Test: `tests/test_breadth.py::test_above_count_members_absent_from_above_is_nan_like_breadth`  
Theme members all absent from `above` columns → `above_count` and `breadth` both NaN.

Renamed: `test_quality_line_null_baseline_absent_matches_sprint002` → `test_quality_line_without_null_baseline_still_has_horizon_footnote`.

Column gap (first data line of the real table above): `+0.0338` and `+0.0840` are separated by many spaces, not `se=0.0181+0.0840`. Cells joined with `"  ".join`. Unit test: `test_format_rank_ic_table_cells_have_column_gap`.

## Notes the spec did not ask for (labelled)

1. **Tiled monotone cannot feed the “sigma ≫ 0, n_ge=0” synthetic.** A constant daily cross-section has Spearman +1 for every pairing, including every circular shift, so `null_std=0` and `sigma` is n/a. The test uses a slow random walk per theme (the same construction `persistence_null_test` uses for its k=1 sanity check). The cyclic 3-day fixture stays for lag alignment.
2. **Ranks are not precomputed independently of the pairing.** Daily RS is stored as `(n_days × n_themes)` float arrays (NaN kept). Each pairing re-ranks under the joint mask so it matches `_spearman_cross_section` bit-for-bit, including asymmetric NaNs. Independent pre-ranking is the fork acceptance 2 is there to catch.
3. **Pearson step reuses `_row_wise_pearson`** (the persistence helper, `np.corrcoef` per row). Ranking is the 11×11 broadcast. Not a second Pearson. 67s for 9×1000 on 407 sessions.
