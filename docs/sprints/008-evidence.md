# Sprint 008 — Evidence

Branch: `sprint/008-theme-ids` (from `dev@fad2018`; **not merged**)
As of: 2026-09-06

## Commits (full hashes)

| DO | Hash | Subject |
|---|---|---|
| DO-1 | `25c313054f4c951cd2e742f840747f285e8eacee` | feat(narratives): DO-1 theme_ids — a story can name its theme before symbols converge |
| DO-2 | `4ed1cac95c19faa9602707813020a683fbc49f21` | feat(narratives): DO-2 故事進度 / 最近事件 — make stage and "what moved" visible |
| DO-3 | `972a1270c939c0619a41d750ee4ca753ae019a49` | fix: DO-3 — F1 silent overlay failure, B2 narrative-date semantics, F3 rule width, B4 correction |

## `uv run pytest` (actual summary line)

```text
196 passed in 43.19s
```

Command: `UV_CACHE_DIR=$PWD/.uv-cache uv run pytest` (after `uv sync --extra dev`).
`dev` was `168 passed`. +28: `test_narratives.py` (+18), `test_product.py` (+8),
`test_radar.py` (+2), `test_cli_smoke.py` (F1 assertion added to the smoke test,
no new test function).

## `git diff dev --stat`

```text
 docs/sprints/005-report.md |   9 ++
 marketpulse/cli.py         |  20 ++-
 marketpulse/narratives.py  | 225 +++++++++++++++++++++++++++---
 marketpulse/product.py     |  37 +++++
 marketpulse/radar.py       |  17 ++-
 narratives/2026-09-06.yaml |   1 +
 tests/test_cli_smoke.py    |  14 +-
 tests/test_narratives.py   | 334 +++++++++++++++++++++++++++++++++++++++++++--
 tests/test_product.py      | 177 ++++++++++++++++++++++++
 tests/test_radar.py        |  68 +++++++++
 10 files changed, 868 insertions(+), 34 deletions(-)
```

No change to `calc.py`, `quality.py`, `momentum.py`, `themes/v1.yaml`,
`persistence_null_test`, `compute_rank_ic`, `rank_ic_null_test`. Layer-1
numbers untouched (R3).

---

## PIT note that shapes every "real data" run below

`data/snapshots/theme_daily.parquet` ends at **2026-09-03**; the two narrative
files are dated **2026-09-04** and **2026-09-06**. There is no date with both a
theme snapshot row and a PIT-visible narrative, so:

- a real `marketpulse brief` (as_of=2026-09-03) has an **empty** narrative
  overlay — the DO-1/DO-2 blocks are gated on a loaded snapshot and do not
  appear. This is what makes acceptance 5 pass (below).
- the DO-1/DO-2 "real narrative" outputs are produced by pairing the newest
  theme day (2026-09-03) with the newest narrative snapshot
  (`load_as_of(2026-09-06)`) — the same counterfactual technique
  `007-evidence.md` used for its "反事實" column. Flagged wherever used.

---

## DO-1 — theme_ids

### The one real-file edit

```diff
--- a/narratives/2026-09-06.yaml
+++ b/narratives/2026-09-06.yaml
@@ optical_cpo
     stance: confirming
     stage: mapped
     revisit: 2026-10-01；若 optical_cpo 主題 rank 跌出前 3 則提前重評
+    theme_ids: [optical_cpo]
     named_symbols: []
     inferred_symbols: []
```

### Acceptance 1 + 3 — the three coverage blocks, BEFORE vs AFTER

theme day = 2026-09-03, narrative overlay = real `load_as_of(2026-09-06)`
(counterfactual; see PIT note). "BEFORE" = the `theme_ids` line reverted via
`git stash`.

```text
########## BEFORE (no theme_ids on any narrative) ##########
強但沒人講
光通訊/CPO  #1
散熱/液冷  #2
高速材料/CCL  #3

有人講但弱
（無）

分類外代號
asic_xpu · 2454

########## AFTER (optical_cpo: theme_ids: [optical_cpo]) ##########
強但沒人講
散熱/液冷  #2
高速材料/CCL  #3

有人講但弱
（無）

分類外代號
asic_xpu · 2454
```

- Acceptance 1: 光通訊/CPO (rank #1) leaves 強但沒人講 after the declaration. ✓
- Acceptance 2: `nvhbm` never carried `theme_ids`; `2330 → foundry_advanced`
  still resolves through the named_symbols fallback
  (`coverage_report` → `covered`; test
  `test_do1_optical_cpo_real_file_declares_its_theme`). ✓
- Acceptance 3: `asic_xpu · 2454` is in `分類外代號` both before and after —
  2454 is in no theme; it is **not** auto-slotted anywhere. ✓

### Acceptance 4 — unknown theme_id (measurement + behaviour)

**Measurement (spec: "先量現有檔案會不會踩到，再問").** The only `theme_ids`
value in the real narrative files is `[optical_cpo]`, which **is** a real theme
id in `themes/v1.yaml`. `unknown_theme_ids(load_as_of(2026-09-06), themes)`
returns `{}`. The current files do **not** hit an unknown id.

**Behaviour** — Q1 was answered 2026-09-06 (written back into the spec): keep
the default, no raise on load, one line on screen. The written-back answer
adds two requirements on that line, both met:

1. format `narrative_id · unknown_theme_id`. Synthetic
   `asic_xpu` with `theme_ids: [optical_cpo, opitcal_cpo]`, rendered in a full
   brief:

   ```text
   未知 theme_id（不在 themes/v1.yaml）：asic_xpu · opitcal_cpo
   強但沒人講
   ...
   ```

   `asic_xpu` is the narrative_id, `opitcal_cpo` the unknown id.
2. the line sits **directly above the coverage lists** it affects
   (`render_brief` prints it immediately before `render_gap_lists`), not
   adrift where later output buries it.

`load_as_of` does not raise (`test_do1_unknown_theme_id_is_surfaced_not_raised`);
the valid sibling id in the same list still classifies. On today's real files
`unknown_theme_ids()` is `{}`, so this path is currently inert — it is a
decision about a future failure mode.

### Acceptance 5 — byte-identity when nobody uses the new field

Real render, as_of=2026-09-03, empty narrative overlay, `dev@051798b` vs
`sprint/008` HEAD, identical inputs:

```text
git worktree add /tmp/mp008-dev 051798b
# render brief / radar ASCII / radar HTML from each tree's own marketpulse,
# data from the main repo, null_baseline=None on both sides
PYTHONPATH=/tmp/mp008-dev            .venv/bin/python render.py 2026-09-03 DEV
PYTHONPATH=/Users/.../MarketPulse    .venv/bin/python render.py 2026-09-03 S008
diff DEV-brief.txt  S008-brief.txt    # (empty)
diff DEV-radar.txt  S008-radar.txt    # (empty)
diff DEV-radar.html S008-radar.html   # (empty)
```

All three diffs empty. sha1 (sprint/008 side):

| file | sha1 |
|---|---|
| brief | `09d47bde6112f528a1cf1bdd4c429ff821945ea5` |
| radar ASCII | `40a1cd2598d15a4b66cb4ed42b079be7785075dc` |
| radar HTML | `e994277c2638fa7569f3775762a5eef121aca8d2` |

Unit tests locking the same: `test_do1_no_narratives_adds_no_new_blocks`,
`test_brief_show_narratives_false_ignores_overlay_byte_identical` (pre-existing,
still green).

**Caveat — the "narratives loaded, no theme_ids" reading of acceptance 5 is
NOT byte-identical.** When a narrative snapshot *is* loaded, the `分類外代號`
block (and, with DO-2, `故事進度` / `最近事件`) appear even if no narrative uses
`theme_ids` — because the spec also mandates those blocks render with `（無）`
"區塊不省略" whenever narratives exist. The two requirements are in tension;
this sprint keeps byte-identity for the **no-narratives** path (the real
default run) and lets the blocks appear once narratives are present. Called out
again in the report.

### Acceptance 6 — test coverage

`test_narratives.py`: `test_do1_theme_ids_declared_status_and_mention` (明示),
`test_do1_empty_theme_ids_falls_back_to_named_symbols` (空值退回),
`test_do1_theme_ids_beats_named_symbols_when_both_present` (並存，明示優先),
`test_do1_unknown_theme_id_is_surfaced_not_raised` (未知 theme_id),
`test_do1_out_of_classification_lists_named_symbols_in_no_theme` (分類外代號),
`test_do1_optical_cpo_real_file_declares_its_theme` (real file).
`test_product.py`: 7 brief-level tests mirroring the same cases.

---

## DO-2 — 故事進度 / 最近事件

### Acceptance 1 + 2 + 3 — real 2026-09-04 / 2026-09-06 snapshots

`render_story_progress(load_as_of(2026-09-06), 2026-09-06, narratives/)`:

```text
故事進度
asic_xpu · open · 1代號 · 2026-09-06
nvhbm · open · 1代號 · 2026-09-06
optical_cpo · mapped · 1主題 · 2026-09-06

最近事件
asic_xpu · 2026-09-05 · Broadcom FY 電話會議：Hock Tan 首度正面點名聯發科為真正的競
optical_cpo · 2026-09-05 · Broadcom 在 Fabric、光通訊與互聯架構的 Guidance 給得極
```

- Acceptance 1: both title strings present; each of the 3 real narratives has
  one `故事進度` line. ✓
- Acceptance 2: `optical_cpo` → `mapped`, `asic_xpu` / `nvhbm` → `open`
  (matches the YAML). ✓
- Acceptance 3 — "上次變動日期", **actual computed values, not tuned**:

  | narrative | 上次變動 | differing fields, 09-04 → 09-06 |
  |---|---|---|
  | `asic_xpu` | `2026-09-06` | `stage`/`revisit`/`log`/`branches` (field birth — absent in 09-04); real content: +2 branches, +1 log |
  | `optical_cpo` | `2026-09-06` | `stage`/`revisit`/`log` (field birth); real content: +1 log, `stage=mapped`, `note` rewritten |
  | `nvhbm` | `2026-09-06` | `stage`/`revisit`/`branches` (field birth); real content: +1 branch, `note` rewritten |

  All three land on `2026-09-06`. **Correction (per the written-back Q2
  answer, 2026-09-06):** the `stage` / `revisit` / empty `log` / empty
  `branches` differences do **not** count as story evolution — those fields
  were born in the 09-06 schema (`REVISIT_REQUIRED_FROM = date(2026, 9, 6)`);
  `revisit` alone would stamp all three with 09-06 even with no content
  change. The three still each had a *real* content change (branches / log /
  note, listed above), so "every narrative genuinely changed" holds — but on
  that narrower evidence. Whether the dates spread once more snapshots exist
  is a **prediction, not a measurement** (revisit date: `narratives/` at 4
  files). The whole-object granularity is kept unchanged (contract #6).

### Acceptance 4 — one snapshot only → `—`, no raise

`render_story_progress(load_as_of(2026-09-06, {only 2026-09-04.yaml}), ...)`:

```text
故事進度
asic_xpu · open · 1代號 · —
nvhbm · open · 1代號 · —
optical_cpo · open · 0代號 · —

最近事件
（無）
```

`story_last_changed` returns `None` for `< 2` versions; no exception
(`test_do2_story_last_changed_single_snapshot_is_none`,
`test_do2_render_story_progress_single_snapshot_prints_dash`).

### Placement (unresolved Q3 default)

Brief tail, counterfactual overlay:

```text
有人講但弱 → 分類外代號 → (disclosures) → 故事進度 / 最近事件 → 到期重看
```

i.e. after the two lists, before 到期重看. (`故事進度`'s "上次變動" shows `—`
in the integrated brief because that run's as_of is 2026-09-03, which predates
both narrative files — the dated values above come from `render_story_progress`
at as_of=2026-09-06.)

### Acceptance 5 — writes nothing

Assertion names:
- `tests/test_narratives.py::test_do2_render_story_progress_does_not_write_narratives`
- `tests/test_product.py::test_brief_render_does_not_change_narratives_mtime_or_bytes` (pre-existing; now also exercises the story-progress path)

Both compare `(st_mtime_ns, read_bytes())` over `narratives/*.yaml` before/after
`render_story_progress` + `story_last_changed` + `render_brief`.

### Acceptance 6 — `--no-narratives` byte-identical

Real CLI `brief --no-narratives` (sprint/008) vs `render_brief(..., show_narratives=False)`
from `dev@051798b`, same inputs (real null baseline), as_of=2026-09-03:

```text
diff dev-off-brief.txt s008-off-brief.txt   # (empty) → "OFF IDENTICAL"
```

Unit test: `test_do2_brief_no_narratives_flag_off_identical`.

### 兔子洞 guard

`test_do2_story_progress_has_no_heat_or_trend_words` asserts none of
`熱 / 爆發 / 加速 / 轉強 / ↑ / ↓ / → / 分數 / score` appear in the section.

---

## DO-3 — the three holes + one unfinished correction

### F1 — silent overlay failure (`cli._load_overlay`)

```diff
     if not themes_path.exists():
-        return NarrativeOverlay(snapshot=snapshot, themes=_empty_theme_set(), error=error)
+        return NarrativeOverlay(
+            snapshot=snapshot,
+            themes=_empty_theme_set(),
+            error=error or f"themes 讀取失敗：找不到 {themes_path}",
+        )
     try:
         themes = load_themes(themes_path)
     except Exception as exc:
-        extra = f"narrative 讀取失敗：{exc}"
+        extra = f"themes 讀取失敗：{exc}"
```

Real CLI, missing `--themes-path`:

```text
$ marketpulse brief --data-dir data --themes-path /tmp/nope.yaml
MarketPulse — 2026-09-03
...
themes 讀取失敗：找不到 /tmp/nope.yaml
...
強但沒人講
...
```

Layer 1 still prints; the message is now on screen. Test:
`test_cli_smoke.py` — `"themes 讀取失敗" in missing.output`, and the happy path
asserts `"讀取失敗" not in output`.

(The broken-YAML themes branch also had its message relabelled from
`narrative 讀取失敗` to `themes 讀取失敗`; only the `load_as_of_lenient`
narrative path keeps `narrative 讀取失敗`, still asserted by
`test_load_as_of_lenient_broken_file_returns_message`.)

### B2 — narrative column is a real "last mentioned" date

```diff
-    mentions = theme_mention_dates(overlay.snapshot, overlay.themes)
-    mentioned = mentions.get(str(theme_id))
+    if overlay.mention_dates is not None:
+        mentioned = overlay.mention_dates.get(str(theme_id))
+    else:
+        mentioned = theme_mention_dates(overlay.snapshot, overlay.themes).get(str(theme_id))
```

`_load_overlay` fills `overlay.mention_dates` from
`theme_last_mention_dates(as_of, themes, narratives_dir)`, which scans every
`snapshot_date <= as_of` file and keeps the latest date each theme was
mentioned (same theme_ids-first mention test).

**"兩份快照、不同主題、不同日期" test** —
`test_do3_b2_last_mention_scans_all_snapshots`:

```text
snapshot 2026-09-04: n_a names A01 (in theme t_a)
snapshot 2026-09-06: n_b names B01 (in theme t_b)
theme_last_mention_dates(2026-09-06, {t_a, t_b}) ==
    {"t_a": date(2026, 9, 4), "t_b": date(2026, 9, 6)}   # different themes, different dates
```

`test_do3_b2_last_mention_takes_latest_when_theme_recurs`: a theme mentioned in
both files resolves to `2026-09-06` (the later). Fallback for hand-built
overlays: `test_do3_b2_narrative_date_label_falls_back_without_mention_dates`.

(On the real repo, as_of=2026-09-03 predates both files, so every column is `—`
and the radar output is unchanged except for F3 below.)

### F3 — radar rule measured from the header

```diff
-        "-" * (100 if not show_narratives else 114),
+        "-" * (100 if not show_narratives else _vislen(header)),
```

Real CLI radar (narratives on), header line then rule line:

```text
Sector                    1D       5D      20D     RS20  Breadth  Volume  Rank R5·R20·R60  Rot  Momentum  敘事
--------------------------------------------------------------------------------------------------------------
```

`len(header)` = 108 chars, `_vislen(header)` = **110** (the two CJK chars in
`敘事` are double-width); rule is now **110** dashes, was a hand-typed 114.
`test_do3_f3_separator_width_matches_header_display_width` asserts
`len(rule) == _vislen(header) == 110`, and that the narratives-off rule is
still exactly `100` (dev's value — untouched, 007 sha1 intact; verified by a
byte-identical `--no-narratives` radar ASCII + HTML diff against `dev@051798b`).

### B4 — 005-report.md correction (in place, original kept)

```diff
 **物證：**對角線隨天期上升；短→短近 0，長→長約 +0.20。  
+
+> **更正 2026-09-06（sprint 008 DO-3.4，回應 006-review B4）。**
+> 上面那句「對角線隨天期上升」是**對 0 讀出來的假象**，就地更正、不刪原句。
+> 006 的循環位移虛無檢定證明：`(60,20)` 裸值 `+0.1402` → `+0.37σ`，
+> `(20,20)` 裸值 `+0.1404` → `+2.57σ`——**近乎相同的觀測值、相反的結論**。
+> ...
+
 **詮釋（三種讀法）：**  
```

### Acceptance — `uv run pytest` all green

`196 passed in 43.19s` (summary line above). Each of the four DO-3 items has a
diff shown here; item 2 has a "two snapshots / different themes / different
dates" test with its output; item 3 has the header + rule strings.

---

## Not done

- **Not merged.** `dev` is untouched; the PO decides the merge.
- No new package, no new module file, `themes/v1.yaml` unchanged, layer-1
  calculation untouched, forbidden files (`persistence_null_test`,
  `compute_rank_ic`, `rank_ic_null_test`) not touched.
- No gazetteer, no `narrate add`, no burst/heat/trend, no stage auto-advance,
  no `2454`-into-a-theme (all → 009 / bound to D6/Q5).

## Done that the spec did not literally ask for

1. **`render_brief` gained a `narratives_dir` parameter**, threaded from
   `brief()` and `refresh()` in `cli.py`. DO-2's "上次變動" needs `history()`,
   which needs the directory; DO-2's "會動到的檔案" listed only
   `narratives.py` / `product.py` / tests. `cli.py` is in the sprint's
   `可碰` list and DO-3 edits it anyway, so this is plumbing, not scope creep.
2. **The broken-themes error message was relabelled** `narrative 讀取失敗` →
   `themes 讀取失敗` (it was mislabelled). DO-3 F1 only asked for the
   missing-path case; the adjacent wrong label was one line away.
3. **New blocks are gated on a non-empty narrative snapshot**, so at
   as_of=2026-09-03 (empty overlay) they do not render at all. The spec says
   `分類外代號` / `故事進度` print `（無）` "區塊不省略"; taken together with
   DO-1 acceptance 5's byte-identity that is only satisfiable if the blocks
   are absent when there are no narratives. This sprint chose byte-identity
   for the no-narratives path. Needs a PO ruling if the always-on `（無）`
   behaviour was the intent.
