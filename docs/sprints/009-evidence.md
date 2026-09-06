# Sprint 009 — Evidence

Branch: `sprint/009-match-yardstick` (from `dev@d428807`; **not merged**)
As of: 2026-09-06

## Commits (full hashes)

| DO | Hash | Subject |
|---|---|---|
| DO-1 | `2f238bd5a4839c6426dc93237456bbd7706cf982` | fix(quality): DO-1 quality_line prints the baseline entry's observed |
| DO-2 | `c914571b1f2f78973d7e253fa0ea899ef56367af` | feat(narratives): DO-2 尚未生效 — show snapshots PIT has not taken in |
| DO-3 | `4664b2b86ad54bd48ae781e03c777acc10fd1f6d` | fix: DO-3 F4 敘事 width 10, F5 declared, F6 one membership test |

## `uv run pytest` (actual summary line)

```text
213 passed in 45.61s
```

Command: `UV_CACHE_DIR=$PWD/.uv-cache uv run pytest` (after `uv sync --extra dev`).

## `git diff dev --stat`

```text
 marketpulse/narratives.py | 138 ++++++++++++++++++++++++----
 marketpulse/product.py    |   9 ++
 marketpulse/quality.py    |  19 ++--
 marketpulse/radar.py      |   8 +-
 tests/test_narratives.py  | 226 ++++++++++++++++++++++++++++++++++++++++++++++
 tests/test_product.py     |  96 +++++++++++++++++++-
 tests/test_quality.py     |  24 +++++
 tests/test_radar.py       |  60 +++++++++++-
 8 files changed, 548 insertions(+), 32 deletions(-)
```

No change to `calc.py`, `momentum.py`, `themes/v1.yaml`, `signal_quality_null.json`,
`persistence_null_test`, `compute_market_quality`, `_rank_persistence_series`,
`compute_rank_ic`, `rank_ic_null_test`. Layer-1 **numbers** untouched; DO-1 only
changes which already-computed number `quality_line` prints.

---

## Open questions (measured, not decided)

### 1. `entry is None` — 持續性那格印什麼？

**Live daily ops on this machine never hit it.** After the 008 B refresh,
`data/processed/signal_quality_null.json` exists, `method_version=1` matches
`NULL_METHOD_VERSION`, k=20 is present, and the entry's `sample_start` /
`sample_end` match the file top-level. `_null_entry_for_display` returns the
k=20 entry. `refresh` **does not** run `validate-signal` and does not write or
delete this file (cli.py:395–398: "not part of `refresh`").

`†` is a different path: `sample_end=2026-09-03` ≠ `as_of=2026-09-04`, so the
marker fires, but `entry` is still not None.

Paths that **do** hit None, none of which is today's refresh:

| Path | How |
|---|---|
| Tests | `null_baseline=None` / rejected `method_version` / sample-window mismatch (DO-6 "treat as absent") |
| Missing file | `data/processed/*` is gitignored. A new clone, or deleting the file, plus never running `validate-signal`, loads None |
| Method bump | raising `NULL_METHOD_VERSION` without re-running `validate-signal` |

So the question is **not empty** for a first machine / a deleted processed dir.
It **is** empty for the PO's current daily `refresh` / `brief` / `radar`.

**Not decided.** The `entry is None` branch still prints daily
`rank_persistence_20` without 虛無 (pre-009). Spec default `n/a` was **not**
applied.

### 2. `尚未生效` 放哪？

Measured current order (008, as_of=2026-09-04):

```text
強但沒人講 → 有人講但弱 → 分類外代號
[replay / rank disclosures]
故事進度 → 最近事件 → 到期重看
```

Spec default: after `分類外代號`, before `故事進度`. Implemented that default.
Live brief (below) has `分類外代號` → `尚未生效` → disclosures → `故事進度`.

### 3. F5 — 全部 `theme_ids` 無效時回哪一態？

Measured the 008 inconsistency **before** changing anything:

```text
theme_ids=("bogus",) named=("A01",)
  coverage_report     → declared
  _mentioned_theme_ids → set()          # drops the unknown id, does not fall back
  unknown_theme_ids    → {n: ('bogus',)}
```

Four-state named-only was already consistent (`partial` ↔ mentioned `{t_a}`).
Implemented spec default: all-invalid ≡ field absent → named_symbols four-state.
`unknown_theme_ids` unchanged; the 008 unknown-id line still prints.

---

## DO-1 — 品質行改印樣本平均值

### The one important picture (acceptance 1)

Real brief, `as_of=2026-09-04`, same `signal_quality_null.json` k=20 entry
(`observed=0.14037651721575425`, `sigma=2.837…`, `n_ge_observed=0/1000`).
Daily `rank_persistence_20` that day is `-0.0545…`.

```text
BEFORE  持續性 -.05† 虛無 .06±.03 +2.8σ 0/1000   換手 12 (90%)   離散 15.8pp (18%)
AFTER   持續性 .14† 虛無 .06±.03 +2.8σ 0/1000   換手 12 (90%)   離散 15.8pp (18%)
```

換手 / 離散 / `HORIZON_FOOTNOTE` 一字不改. `†` still there (`sample_end` 2026-09-03
≠ as_of 2026-09-04); the marker now means "this whole set was measured through
sample_end". File bytes of `signal_quality_null.json` untouched.

### Acceptance 2 — invariant test

Name: `test_quality_line_persistence_digit_equals_entry_observed`

```text
tests/test_quality.py::test_quality_line_persistence_digit_equals_entry_observed PASSED
```

The fixture's daily `rank_persistence_20` at the rank-flip is `-1.00`; the
payload `observed` is set to `0.1404` → `.14`. The test asserts the token after
`持續性 ` equals `_fmt_corr(entry["observed"])` and that the daily `-1.00` is
not on the quality line. Sign contradiction is a failed assertion, not a glance.

---

## DO-2 — 尚未生效

### The one important picture (acceptance 1)

Real `as_of=2026-09-04` (latest price day). `narratives/` has 2026-09-04.yaml
(in PIT) and 2026-09-06.yaml (`snapshot_date > as_of`). From the full refresh:

```text
尚未生效
2026-09-06 · 2026-09-06.yaml
（快照日期晚於最新價量日 2026-09-04，依 PIT 規則尚未納入）
```

### Acceptance 2 — coverage 有無未生效快照, 逐字元相同

Name: `test_do2_pending_file_does_not_change_coverage_byte_for_byte`

```text
tests/test_narratives.py::test_do2_pending_file_does_not_change_coverage_byte_for_byte PASSED
```

A PIT snapshot covering `A01` → `t_a`, then a 2026-09-06 file that would flip
the same narrative to `theme_ids: [t_b]` / `named_symbols: [B01]` if leaked.
`load_as_of` / `coverage_report` / `theme_mention_dates` /
`theme_last_mention_dates` / `story_last_changed` are `==` before and after
the future file is added (`str(coverage)` included). Only `pending_snapshots`
sees the new file.

Live as_of=2026-09-04 coverage (PIT = 09-04 file, 09-06 not consulted):

```text
{'asic_xpu': 'uncovered', 'nvhbm': 'covered', 'optical_cpo': 'unknown'}
```

optical_cpo's `theme_ids: [optical_cpo]` is still in the 09-06 file only (F7).

### Acceptance 3

No snapshot file → block absent. `test_do2_pending_no_files_brief_matches_dev_byte_for_byte`
and addendum-A state 1 now also assert `TITLE_PENDING not in text`.

### Acceptance 4

`test_brief_render_does_not_change_narratives_mtime_or_bytes` still passes.
`pending_snapshots` reads `snapshot_date` and the filename; it does not parse
narrative bodies (a future file whose `named_symbols` is `SHOULD_NOT_BE_READ`
does not appear in the rendered block).

---

## DO-3

### 1. F4 — `敘事` 欄寬 10

Diff (`4664b2b`, `marketpulse/radar.py`):

```diff
-        header = f"{header}  {NARRATIVE_COL_HEADER}"
+        header = f"{header}  {_ljust(NARRATIVE_COL_HEADER, NARRATIVE_COL_WIDTH)}"
-            row = f"{row}  {_narrative_date_label(rec.theme_id, overlay)}"
+            row = (
+                f"{row}  "
+                f"{_ljust(_narrative_date_label(rec.theme_id, overlay), NARRATIVE_COL_WIDTH)}"
+            )
```

`--no-narratives` rule stays `100`.

Live refresh, four strings (header / rule / a `—` row / the date row):

```text
Sector                    1D       5D      20D     RS20  Breadth  Volume  Rank R5·R20·R60  Rot  Momentum  敘事      
--------------------------------------------------------------------------------------------------------------------
 光通訊/CPO             +3.2%    +5.4%   +29.7%   +24.8%    10/10    1.2x  2·#1·4           →    Stable  —         
 先進製程               +2.0%    +1.1%    +7.9%    +3.0%      5/6    0.8x  5·#5·3           ↓    Weakening  2026-09-04
```

`敘事` cells are vislen 10 (`_ljust`). Header and rule are both 116.
**Full-line right edges still follow the Momentum label** (`Stable` 6,
`Weakening` 9, `Improving` 10, `Weak` 4, header `Momentum` 8). Spec F4 called
`敘事` the only unpadded column; Momentum is also unpadded. Padding Momentum
in the shared header would change `--no-narratives` output (不可碰). Not
padded. Test: `test_do3_f4_narrative_column_is_width_10_and_right_edges_align`.

```text
tests/test_radar.py::test_do3_f4_narrative_column_is_width_10_and_right_edges_align PASSED
```

### 2. F5 — `declared` is not "I typed something"

Diff: `coverage_report` now gates on `_valid_declared_theme_ids` (at least one
id in the ThemeSet), not `if narrative.theme_ids`. All-invalid falls through
to the four-state. `unknown_theme_ids` untouched.

### 3. F6 — one membership test

`_themes_hit_by_named_symbols` is the single `named & members`.
`_mentioned_theme_ids` returns that set when nothing valid was declared.
`coverage_report` builds covered/partial/uncovered from
`_named_symbols_in_themes`, which is the same helper.

Four-state return values on named-only narratives are unchanged (checked
before merging: `partial` + named `A01,ZZZ` already agreed with mentioned
`{t_a}`). The all-invalid case **was** the F5 bug; both functions now fall
back together rather than silently picking a side.

Name: `test_do3_f6_coverage_and_mentioned_agree_on_the_same_narrative`

```text
tests/test_narratives.py::test_do3_f6_coverage_and_mentioned_agree_on_the_same_narrative PASSED
```

Eight cases (declared / mix / all-invalid+named / covered / partial /
uncovered / unknown / all-invalid+empty): `coverage_report` status and
`_mentioned_theme_ids` agree; `theme_mention_dates` matches the same set.

---

## Full `uv run marketpulse refresh` (cwd = repo root)

008 B5: the user-facing `reports/radar.html` must be written by this command,
not by a side `radar --output`.

Before: mtime `2026-09-06 12:30:16`, 41701 bytes, quality line `持續性 -.05†`.

Command: `UV_CACHE_DIR=$PWD/.uv-cache uv run marketpulse refresh`
Exit 0. Duration ~20s. Full stdout:

```text
downloaded 0 weekday requests
sessions: 408  2024-12-27 → 2026-09-04
TWSE rows: 430867
TPEx rows: 352324
TAIEX sessions: 408
validate: ok
wrote data/snapshots/theme_daily.parquet  rows=4488  themes=11  classification=theme-v0.2.0-eleven
歷史回放使用現行族群定義，用來把過去的輪動畫清楚，不代表當時已知這份名單。
wrote data/snapshots/market_daily.parquet  rows=388
MarketPulse — 2026-09-04
持續性 .14† 虛無 .06±.03 +2.8σ 0/1000   換手 12 (90%)   離散 15.8pp (18%)
月尺度：可偵測≠穩定；短端遠強於長端；凍結成分偏高估（D6）。

Theme Rotation  領先 / 改善 / 轉弱 / 落後
分類只用 Rank 與 Δ5。value_thrust、breadth 為附註。

改善
 被動元件             4·#4·11    Δ5   +2  RS20   +6.8%
                      thrust  +16.7%  breadth   71.4%
 先進製程             5·#5·3     Δ5   +3  RS20   +3.0%
                      thrust  -17.2%  breadth   83.3%
 重電                 7·#6·7     Δ5   +3  RS20   +1.5%
                      thrust  -30.4%  breadth   85.7%
 半導體測試/測試介面  3·#8·8     Δ5   +2  RS20   -3.5%
                      thrust   -8.8%  breadth   60.0%

領先
 光通訊/CPO           2·#1·4     Δ5   +1  RS20  +24.8%
                      thrust  +45.3%  breadth  100.0%
 散熱/液冷            1·#2·2     Δ5   +3  RS20  +15.9%
                      thrust   +9.0%  breadth  100.0%

轉弱
 高速材料/CCL         8·#3·1     Δ5   -2  RS20  +10.0%
                      thrust  -30.1%  breadth   50.0%

落後
 PCB                  11·#7·9    Δ5   -4  RS20   +0.5%
                      thrust  +51.5%  breadth   50.0%
 記憶體               9·#9·5     Δ5   -5  RS20   -3.7%
                      thrust  -22.6%  breadth   28.6%
 AI電力/電源          6·#10·10   Δ5   +1  RS20   -5.2%
                      thrust  -11.0%  breadth   20.0%
 AI伺服器             10·#11·6   Δ5   -4  RS20   -6.3%
                      thrust  +54.3%  breadth   70.0%

強但沒人講
光通訊/CPO  #1
散熱/液冷  #2
高速材料/CCL  #3

有人講但弱
（無）

分類外代號
asic_xpu · 2454

尚未生效
2026-09-06 · 2026-09-06.yaml
（快照日期晚於最新價量日 2026-09-04，依 PIT 規則尚未納入）

歷史回放使用現行族群定義，用來把過去的輪動畫清楚，不代表當時已知這份名單。
Rank is relative leadership over time; it does not prove capital flowed from A to B.

故事進度
asic_xpu · open · 1代號 · —
nvhbm · open · 1代號 · —
optical_cpo · open · 0代號 · —

最近事件
（無）

到期重看
（無）

條件型（無法判斷是否到期）
（無）
reports/rotation_latest.png
effective RS20 period: 2026-07-09 → 2026-09-04
歷史回放使用現行族群定義，用來把過去的輪動畫清楚，不代表當時已知這份名單。
Rank is relative leadership over time; it does not prove capital flowed from A to B.
MarketPulse — 2026-09-04
持續性 .14† 虛無 .06±.03 +2.8σ 0/1000   換手 12 (90%)   離散 15.8pp (18%)
月尺度：可偵測≠穩定；短端遠強於長端；凍結成分偏高估（D6）。

Sector Rotation
Rank = RS20 排序（族群 20 日報酬 − 大盤）。不是綜合分數。 Breadth = 收盤價 > SMA20 的檔數。Volume = 成交量 / 20 日均量。
Rotation = 相對前一交易日的名次。 Momentum = 5D / Breadth / Volume / Rank Δ5 的方向，不是分數。
Rotation: ↑ Rising  ↓ Falling  → Stable  (vs previous session)
Momentum: Strong  Improving  Stable  Weakening  Weak  (5D / Breadth / Volume / Rank Δ5)

Sector                    1D       5D      20D     RS20  Breadth  Volume  Rank R5·R20·R60  Rot  Momentum  敘事      
--------------------------------------------------------------------------------------------------------------------
 光通訊/CPO             +3.2%    +5.4%   +29.7%   +24.8%    10/10    1.2x  2·#1·4           →    Stable  —         
 散熱/液冷              +5.4%   +10.3%   +20.8%   +15.9%      5/5    0.8x  1·#2·2           →    Strong  —         
 高速材料/CCL           +2.8%    -3.5%   +14.8%   +10.0%      2/4    0.5x  8·#3·1           →    Weakening  —         
 被動元件               +8.7%    +4.1%   +11.7%    +6.8%      5/7    1.0x  4·#4·11          ↑↑   Improving  —         
 先進製程               +2.0%    +1.1%    +7.9%    +3.0%      5/6    0.8x  5·#5·3           ↓    Weakening  2026-09-04
 重電                   +1.4%    -3.0%    +6.4%    +1.5%      6/7    0.5x  7·#6·7           ↑    Weakening  —         
 PCB                    +0.2%    -7.2%    +5.3%    +0.5%      3/6    1.5x  11·#7·9          ↓↓   Weakening  —         
 半導體測試/測試介面    +0.6%    +5.3%    +1.3%    -3.5%      3/5    0.8x  3·#8·8           ↑    Improving  —         
 記憶體                 +1.9%    -4.1%    +1.1%    -3.7%      2/7    0.7x  9·#9·5           ↓↓   Weakening  —         
 AI電力/電源            +1.3%    -1.7%    -0.4%    -5.2%      1/5    0.7x  6·#10·10         →    Weak  —         
 AI伺服器               +3.4%    -6.5%    -1.5%    -6.3%     7/10    1.4x  10·#11·6         →    Weak  —         

歷史回放使用現行族群定義，用來把過去的輪動畫清楚，不代表當時已知這份名單。
Rank is relative leadership over time; it does not prove capital flowed from A to B.
reports/radar.html
raw last attempt: 2026-09-04  twse=ok  tpex=ok
bars/snapshot as_of: 2026-09-04
chart: reports/rotation_latest.png  effective 2026-07-09 → 2026-09-04
```

After: `reports/radar.html` mtime `2026-09-06 13:56:24`, 41700 bytes
(41701 → 41700 is `-.05` → `.14`, one character), title
`MarketPulse — 2026-09-04`, quality line `持續性 .14†`, `<th>敘事</th>` present.
Printed `reports/radar.html` then the ops status — the pipeline finished; it
did not stop after chart.
