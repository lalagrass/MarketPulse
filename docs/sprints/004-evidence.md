# Sprint 004 — 物證

分支：`sprint/004-narrative-shape`（從 `dev` 開，未 merge）
執行日：2026-09-06

## Commit hash（每項各自 commit）

| DO | commit | 標題 |
|---|---|---|
| DO-3 | `9814796` | feat(calc): DO-3 refuse to compute rolling windows across a data hole |
| DO-1 | `8e0dfc1` | feat(narratives): DO-1 additive schema — stage, revisit, log, branches, history() |
| DO-2 | `9849b26` | feat(baskets): DO-2 branch-basket strength panel |

執行順序照 spec「執行順序」節：DO-3 → 補 TPEx → 再 analyze → validate-signal → DO-1 → DO-2。

## `uv run pytest` 實際摘要行

```
128 passed in 17.43s
```

（本輪之前 `dev` 為 `109 passed`；新增 test_data_gaps.py 6、test_narratives.py +7、test_baskets.py 6 = +19。）

## `git diff dev --stat`

```
 marketpulse/baskets.py     | 211 ++++++++++++++++++++++++++++++++++
 marketpulse/calc.py        |  89 +++++++++++++++
 marketpulse/cli.py         |  78 ++++++++++++-
 marketpulse/narratives.py  | 188 ++++++++++++++++++++++++++++--
 narratives/2026-09-06.yaml |  93 +++++++++++++++
 tests/test_baskets.py      | 276 +++++++++++++++++++++++++++++++++++++++++++++
 tests/test_data_gaps.py    | 121 ++++++++++++++++++++
 tests/test_narratives.py   | 228 ++++++++++++++++++++++++++++++++++++-
 8 files changed, 1275 insertions(+), 9 deletions(-)
```

`data/` 全程未 commit（`.gitignore:13,19` 涵蓋 `data/raw/*`、`data/processed/*`）。

---

## 抓取來源出處（清理時的 TWSE 2025 缺口）

`data/raw/twse/` 往前補到 `2024-12-27` 的那批（sprint 004 前一輪分支清理落地），
來源是 GitHub Actions egress 抓回的 tarball，繞過 HiNetCDN 對 urllib 的 307：

```
scratch/twse-2025-gap.tar.gz  sha256 12d08451a8d9ad65c0472962fef68a8401c5c47a068dde5a0320da1518814d7e
download-summary.json         {"ok": 246, "empty": 18, "fail": 0}
```

本輪的 TPEx 89 天補齊不經 tarball，直接用 `uv run marketpulse download`（見下）。

---

## DO-3 — 資料空窗檢查

### 驗收條件 1（造中間挖 30 個交易日的資料 → raise，訊息含起訖日期）

`check_data_gaps` 對 120 個交易日、中間挖掉 30 個（`dates[45:75]`）的面板實際拋出：

```
session gap: 30 weekday(s) with no data between 2026-03-06 and 2026-04-20 (limit 10)
```

CLI 層 `test_analyze_cli_raises_on_thirty_session_hole`：`analyze` exit code 1，
輸出含 `2026-03-06` 與 `2026-04-20`，且 `theme_daily.parquet` 未被寫出。

### 驗收條件 2（拿現在的本機真實資料跑 analyze → 必須 raise，指出 TPEx 缺 89 天）

補 TPEx **之前**，`uv run marketpulse analyze` 的實際輸出（stderr），exit code 1：

```
data gap: raw data incomplete: TPEx missing for 89 session(s) that TWSE has: 2024-12-27 -> 2025-04-30 [2024-12-27, 2024-12-30, 2024-12-31, 2025-01-01, 2025-01-02, 2025-01-03, ... (89 total)]
```

（未造任何假資料——這是 `data/raw/twse` 440 檔 / `data/raw/tpex` 351 檔的真實狀態。）

### 補 TPEx 89 天

```
uv run marketpulse download --start 2024-12-27 --end 2025-04-30
```

- `--force` 未加。`should_fetch` 對已存在且可用的 TWSE 檔回 `False` → TWSE 全數 `cached`
  跳過，只抓缺的 TPEx。實際 label：`twse=cached×78 / twse=holiday×11`，
  `tpex=ok×78 / tpex=empty×11`，`downloaded 89 weekday requests`，exit 0。
- 沒有 307 問題（003 報告記載一致）。耗時約 1 分鐘（TWSE 全跳過，故無 `TWSE_SLEEP_SEC` 停頓）。
- 補完 `data/raw/tpex` = 440 檔，與 `data/raw/twse` 440 檔對齊；
  `comm -3 <(ls twse) <(ls tpex)` 兩邊為空（日期集合完全相同）。
  `validate` 後 `sessions: 407  2024-12-27 → 2026-09-03`。

### 驗收條件 3（補齊後 analyze 恢復正常，brief 逐字元相同）

補 TPEx 後 `uv run marketpulse analyze`，exit 0：

```
wrote data/snapshots/theme_daily.parquet  rows=4477  themes=11  classification=theme-v0.2.0-eleven
歷史回放使用現行族群定義，用來把過去的輪動畫清楚，不代表當時已知這份名單。
wrote data/snapshots/market_daily.parquet  rows=387
```

`brief` 於「落資料之前」與「落資料之後、analyze 之後」逐字元相同：

```
$ diff -u brief_before.txt brief_after_backfill.txt
IDENTICAL
sha256 79e332f4f47415410dceaf995ff1828b0b00ae26fb42b8b251660d7543a7dede  （兩者相同）
```

多出的 ~78 個交易日早期歷史，未擾動最新日（2026-09-03）的快照。

---

## 第 4 步（回報，不是驗收條件）— `validate-signal`

**第二層閘門打開了。** 樣本從 329 → ~367+ 個交易日後，`retained_fraction=69.25%`
高於 DO-5 的 `MIN_RETAINED_FRACTION=0.5` 半圈護欄——三個 k 的虛無檢定現在**都跑得起來**，
不再 raise。以下為追加項的新輸出格式（σ 距離 ＋ 超越計數，取代會飽和的 percentile），
三個 k 對齊在同一份 367 天樣本（`sample=2024-12-27→2026-09-03`）：

```
$ uv run marketpulse validate-signal --k 1
k=1   observed=0.9307  n_days_used=386  null_mean=0.0590  null_std=0.0254  null>=obs=0/1000  dist=+34.36σ  seed=0  n_candidates=268  retained_fraction=69.25%  sample=2024-12-27→2026-09-03
$ uv run marketpulse validate-signal --k 5
k=5   observed=0.7167  n_days_used=382  null_mean=0.0602  null_std=0.0258  null>=obs=0/1000  dist=+25.44σ  seed=0  n_candidates=268  retained_fraction=69.25%  sample=2024-12-27→2026-09-03
$ uv run marketpulse validate-signal --k 20
k=20  observed=0.1404  n_days_used=367  null_mean=0.0637  null_std=0.0270  null>=obs=0/1000  dist=+2.84σ   seed=0  n_candidates=268  retained_fraction=69.25%  sample=2024-12-27→2026-09-03
```

讀法：`null>=obs=0/1000` = 1000 個虛無抽樣中沒有一個 ≥ observed；`dist` = observed
距虛無平均幾個虛無標準差。**percentile 不再是主要數字**（三個 k 的 percentile 都是
100.0，看起來跟 DO-5 要擋的退化虛無一樣，人分不出來）；它仍留在
`data/processed/signal_quality_null.json` 的每個 entry 裡。

k=20 = `+2.84σ`、0/1000。k=1 / k=5 在拉長樣本上仍是壓倒性（`+34σ` / `+25σ`）。
如何解讀 20 日尺度是 PO 的事，本步只回報。

**沒有為了讓它過去動任何常數**（D10）。`MAX_SESSION_GAP_BDAYS`、`MIN_RETAINED_FRACTION`、
`_null_min_lag`、`NULL_METHOD_VERSION` 全部原封不動；閘門是因為資料變長而開，不是因為調參。

副作用：這一步重寫了 `data/processed/signal_quality_null.json`。`brief` / `radar` 第二行
的持續性虛無基準格式隨追加項改為 `.06±.03 +2.8σ 0/1000`（見下）。
`data/processed/` 為 gitignore，未 commit。DO-3 驗收條件 3 的 `brief` 逐字元檢查在此步
之前、虛無基準未動時已通過，與這裡的格式改動無關。

---

## 追加項（sprint 004 follow-up）

| 項 | commit | 標題 |
|---|---|---|
| 1（顯示改 σ ＋ 計數） | `3d812c4` | feat(quality): report null exceedance count + σ distance, not a percentile |
| 2（樣本範圍不符即不顯示） | `095f79c` | feat(quality): hide a null entry whose sample window != the file's |

**都沒有改常數、沒有改門檻。**

### 追加項 1 — 顯示層與 evidence 不再用會飽和的 percentile

- `persistence_null_test` 回傳新增 `n_ge_observed`（虛無抽樣 ≥ observed 的個數）與
  `sigma`（`(observed − null_mean) / null_std`）。`percentile` 保留在 dict 與 JSON。
- `write_null_baseline` 每個 entry 多寫 `n_ge_observed` / `sigma`。
- `validate-signal` CLI：`percentile=100.0` → `null>=obs=0/1000  dist=+2.84σ`（見上）。
- `_fmt_null_baseline`（`brief` / `radar` 的持續性那行）：`p{pct}` → `{±sigma}σ {n_ge}/{n_iter}`。
  新的 `brief` 第二行實測：

  ```
  持續性 .11 虛無 .06±.03 +2.8σ 0/1000   換手 10 (80%)   離散 14.1pp (7%)
  ```

- 測試：`test_null_test_reports_exceedance_count_and_sigma_distance`
  （k=1 → `n_ge_observed==0`、`sigma>3`、`percentile` 仍在）；
  `test_quality_line_null_baseline_present_appends_numbers_only` 改為斷言
  `+0.6σ` / `190/1000` 出現、`p81` 不出現。

### 追加項 2 — 樣本範圍不符即降級為「不顯示」

`data/processed/signal_quality_null.json` 一份檔頂層只有一組 `sample_start`/`sample_end`，
每次 `validate-signal` 重寫；先前 k=20 是 367 天樣本、k=1/k=5 還是 304/308 天的舊樣本，
但頂層被覆寫成 `2024-12-27`，三者 `method_version` 又都是 1，`_entry_method_current`
全部放行。

- `_entry_sample_matches_file(entry, payload)`：entry 自己的 `sample_start`/`sample_end`
  必須等於檔案頂層。不符 → `_null_entry_for_display` 回 `None`，
  **走 DO-6 既有的「treat as absent」路徑**（跟 `method_version` 不符同一條），
  不新增第三種顯示狀態。
- 測試：`test_quality_line_entry_from_a_different_sample_matches_absent_byte_for_byte`
  （不符 entry 的 `quality_line` 輸出 == null-absent 輸出，逐字元）；
  `test_null_entry_for_display_rejects_entry_from_other_sample`（直接單元測試）。
- 然後把 k=1 / k=5 用現在的 367 天樣本重跑，三個 k 對齊（見上三行輸出）。
  對齊後的 `signal_quality_null.json`：三個 entry 的 `sample_start`/`sample_end`
  都是 `2024-12-27` / `2026-09-03`，與頂層一致；每個 entry 都有 `n_ge_observed=0`、
  `sigma`（`+34.36` / `+25.44` / `+2.84`）。

### 追加項後的全套測試

```
131 passed in 24.75s
```

（DO-3/1/2 的 128 → +1（追加項 1）+2（追加項 2）= 131。）

`git diff dev --stat` 追加項部分：`marketpulse/quality.py`、`marketpulse/cli.py`、
`tests/test_quality.py` 三檔（`quality.py` 原不在 sprint 004 權限邊界內，
依本輪 follow-up 指示放行——見報告）。

---

## DO-1 — narrative schema

### 驗收條件 1（現行 2026-09-04.yaml 一個字不改仍能載入）

`narratives/2026-09-04.yaml` 未改（`git status` 無此檔）。
`test_do1_existing_2026_09_04_file_still_loads_unchanged`：
`load_as_of(2026-09-04)` 回三則 narrative，`stage` 全為 `open`（無欄位 → 預設），
`log` / `branches` 全為 `()`，`coverage_report` == `{asic_xpu: uncovered, nvhbm: covered, optical_cpo: unknown}`
（與本輪前逐字元相同）。

### 驗收條件 2（缺 revisit → load_as_of raise，訊息含 narrative_id）

`test_do1_missing_revisit_raises_with_narrative_id`：`snapshot_date` 2026-09-10 的檔
缺 `revisit` → `ValueError`，`match="rotting_story"`。實際訊息形如：

```
narrative 'rotting_story': missing required field 'revisit' (a date or a condition string; a story with no date to come back to rots)
```

### 驗收條件 3（history 依 as_of 回版本序列）

`test_do1_history_returns_versions_up_to_as_of`：兩份 tmp 快照（2026-09-04、2026-09-06，
後者對 `asic_xpu` 多一則 2026-09-05 的 `log`）。
`history("asic_xpu", as_of=2026-09-05)` → `[2026-09-04]`，該版本 `log == ()`。
`history("asic_xpu", as_of=2026-09-06)` → `[2026-09-04, 2026-09-06]`，
後者 `log` 長度 1、`kind == "evidence"`。

### 驗收條件 4（bears_on 指到不存在的 branch_id → raise）

`test_do1_bears_on_unknown_branch_id_raises`：`bears_on: [ghost_branch]` 而 branch 只定義
`real_branch` → `ValueError`，`match="ghost_branch"`。

### `history()` 回傳型別（未決問題 2）

回 `tuple[NarrativeVersion, ...]`，`NarrativeVersion = (snapshot_date, narrative)`，
按 `snapshot_date` 升冪。**是完整版本序列，不是差異序列**——docstring 已寫明理由：
「幾次 / 間隔多久」直接 `len()` 與日期就有；要 field-level diff 的呼叫端自己比相鄰兩個。

---

## `narratives/2026-09-06.yaml` 實際內容（EP694 寫成的第一個真實樣本）

```yaml
# 脈絡快照。每次變更寫一個新的帶日期檔，不原地修改（D9：全狀態快照仍是權威）。
# named_symbols  = 來源自己講出來的代號
# inferred_symbols = 我們自己推論的，必須分開存放（non-goals R3）
# basket（branches 內）= 人指定的支線籃子，與 inferred_symbols 同級，不得由程式推論填入
#
# 本檔是 sprint 004 DO-1 新 schema 的第一個真實樣本，把股癌 EP694（2026-09-05 播出）
# 的博通電話會議段落寫成 asic_xpu 的一則 log ＋ 兩條支線。
snapshot_date: 2026-09-06

narratives:
  - narrative_id: asic_xpu
    name: 客製化 ASIC / XPU
    first_noted: 2026-09-03
    source: podcast
    source_ref: 股癌 EP693
    stance: new
    stage: open
    revisit: 2026-10-15 或 Broadcom 下一次財報電話會議（以先到者為準）
    named_symbols: ["2454"]
    inferred_symbols: []
    note: >
      聯發科發行約 39 億美元 ECB，輝達認購 35 億、票息 0%、溢價約 15%。
      Alphabet 亦參與，兩者各自獨立入股而非三方結盟。論點是 XPU 興起並未壓縮
      GPU 廠，而是整體 TAM 膨脹，輝達改賣機櫃內外互聯／網通／儲存整套方案。
      對照：2454 目前不屬於任何既有主題，無 ASIC/IC 設計類主題。
    branches:
      - branch_id: mediatek_asic_share
        claim: 聯發科在雲端客製 ASIC 拿到實質份額，被晶片王者認可為真正競爭對手
        basket: ["2454"]
        watch: 下一季 Broadcom / NVDA 電話會議是否再點名；聯發科法說是否單獨揭露 ASIC 營收
        status: live
      - branch_id: xpu_not_squeezing_gpu
        claim: XPU 興起擴大整體 TAM，未壓縮 GPU 廠的營收與毛利
        basket: []
        watch: NVDA 資料中心毛利率、機櫃互聯／網通方案營收占比
        status: live
    log:
      - date: 2026-09-05
        source_ref: 股癌 EP694
        kind: evidence
        text: >
          Broadcom FY 電話會議：Hock Tan 首度正面點名聯發科為真正的競爭對手（過去多以
          「Ankle Biters」或「Talk Shit」帶過）。同場提到六大客製晶片客戶中，Anthropic
          與 OpenAI 因尚未上市、信評較弱，Broadcom 與 NVIDIA 均出手協助確保硬體開出。
          Fabric／光通訊／互聯 Guidance 均佳。一則證據兩個方向：支持「聯發科拿到份額」，
          同時削弱「XPU 壓縮 GPU 廠」（王者仍在擴大合作而非防守）。
        bears_on: [mediatek_asic_share, xpu_not_squeezing_gpu]

  - narrative_id: nvhbm
    name: NVHBM / 記憶體架構變革
    first_noted: 2026-09-03
    source: podcast
    source_ref: 股癌 EP693
    stance: new
    stage: open
    revisit: 台積電 2026-10 法說（HBM4 base die 代工客戶／資本支出揭露）
    named_symbols: ["2330"]
    inferred_symbols: []
    note: >
      記憶體控制器由運算晶片移入 HBM 的 base die，HBM4 世代 base die 規劃由
      台積電以先進製程代工。這是一個橫跨既有主題（記憶體、先進製程、高速材料）
      的論點，schema 加入 branches 後可分別掛籃子追蹤。
    branches:
      - branch_id: hbm4_base_die_tsmc
        claim: HBM4 base die 由台積電先進製程代工，價值往代工端移轉
        basket: ["2330"]
        watch: 台積電法說是否確認 HBM base die 訂單；記憶體三雄 HBM4 時程
        status: live
    log: []

  - narrative_id: optical_cpo
    name: 光通訊 / CPO
    first_noted: 2026-09-03
    source: podcast
    source_ref: 股癌 EP693
    stance: confirming
    stage: mapped
    revisit: 2026-10-01；若 optical_cpo 主題 rank 跌出前 3 則提前重評
    named_symbols: []
    inferred_symbols: []
    note: >
      僅以「相關類股持續強勢」帶過，屬對既有走勢的確認而非新論點。
      對照：optical_cpo 於 2026-09-02 為 rank #1、RS20 +37.4%——數字早已知道。
      EP694 的博通 Fabric／光通訊 Guidance 佳，屬同向確認，不另立支線。
    branches: []
    log:
      - date: 2026-09-05
        source_ref: 股癌 EP694
        kind: evidence
        text: >
          Broadcom 在 Fabric、光通訊與互聯架構的 Guidance 給得極佳，屬對既有強勢的
          同向確認，不帶新資訊。
        bears_on: []
```

---

## DO-2 — 支線籃子的強弱面板

### 驗收條件 1（跑面板後 brief 與 radar.html 逐字元相同）— R3 的可測試版本

repo 層實測（先存基準、跑 `baskets --as-of 2026-09-06`、再取一次）：

```
$ diff -u do2_brief_before.txt  do2_brief_after.txt   → BRIEF IDENTICAL
$ diff -u do2_radar_before.html do2_radar_after.html  → RADAR IDENTICAL
brief sha256 3b7ca322a463cbfa072478fd4899fdbb1395f7593a7b13b79f8623d1de2c0736  （前後相同）
radar sha256 d4e9931e970b829e45a1197b30c533829dd42c0290ca16169af673a7fe52665d  （前後相同）
```

test 層 `test_running_baskets_does_not_change_brief_or_radar`：`baskets` 前後
`brief.output` 相等、`radar.html` 內容相等，`theme_daily.parquet` mtime 不變，
無 `basket_daily.parquet` 產生。

### 面板實際輸出

```
$ uv run marketpulse baskets --as-of 2026-09-06
支線籃子強弱  as-of 2026-09-06  （成員用 snapshot_date ≤ 2026-09-06 的最新一份；並列，不排名）
branch                                n       RS5      RS20      RS60   breadth     val%
asic_xpu/mediatek_asic_share          1    +10.0%     +5.7%     +1.2%    100.0%     3.5%
asic_xpu/xpu_not_squeezing_gpu      無標的
nvhbm/hbm4_base_die_tsmc              1     -1.1%     -3.4%     -1.3%      0.0%     2.9%
```

（`optical_cpo` 無 branch；`asic_xpu` 兩條、`nvhbm` 一條，皆 `status: live`。
價量資料只到 2026-09-03，故 as-of 2026-09-06 的數字是用 ≤ 2026-09-03 的最新交易日算的。）

### 驗收條件 2（較晚的 YAML 加一檔股票，較早 as_of 的輸出不變）

`test_earlier_as_of_unaffected_by_later_membership_change`：籃子在 2026-09-06 為 `["AAA"]`，
在 2026-09-20 改為 `["AAA","BBB"]`。`as_of` 取兩份之間的交易日，
`compute_basket_metrics` 加入 2026-09-20 檔前後 `before == after`，且 `basket == ("AAA",)`。

### 驗收條件 3（籃子歷史不足 20 個交易日 → RS20 印 n/a，不補值）

`test_rs20_and_rs60_are_none_when_history_too_short`：12 個交易日的面板，
`rs5` 有值、`rs20 is None`、`rs60 is None`，`render_basket_panel` 輸出含 `n/a`。
（實作上 `n_day_return` 視窗不足回 NaN → `rs20=None` → 印 `n/a`；不套較短窗口。）

### 驗收條件 4（空籃子印一行「無標的」，不是被略過）

`test_empty_basket_emits_a_row_labelled_not_dropped`：兩條 branch（一有籃子一空），
`len(rows) == 2`，`rows[1].is_empty`，面板含 `n1/empty` 與 `無標的`。
真實資料中 `asic_xpu/xpu_not_squeezing_gpu`（`basket: []`）即印 `無標的`（見上面板輸出）。

### `value_share` 分母（未決問題 3）

沿用主題的分母＝全市場當日成交值（`tv.sum(axis=1)`）。`test_value_share_denominator_is_whole_market`
驗證 `value_share == 籃子成交值 / 全市場成交值`。籃子與主題的 `value_share` 因此可直接比較。

---

## 契約紅線自查

- **R3**：`baskets.py` 只讀價量、`RS_k` 用 `calc.py` 既有的 `theme_return_k − TAIEX_return_k`，
  不寫 `theme_daily.parquet`、不動 `themes/v1.yaml`、不寫任何檔。驗收條件 1 就是這條的測試。
- **R1**：面板無 `rank` 欄、無 `cumcount`、無排序（照 YAML 順序印，`test_rows_follow_input_order_not_strength`）。
  無籃子分數、無加權。
- **R2 / §7 PIT**：`_pit_filter` 把 `log` 依 `entry.date <= as_of` 過濾（`test_do1_log_entries_after_as_of_are_filtered`）；
  `history()` 每個版本同樣套用。`branches` 無獨立日期，其 PIT 由 `snapshot_date` ＋ `first_noted` 兩道閘門涵蓋。
- **D9**：`log` / `branches` 是 dataclass 欄位，無 registry / reducer / event bus。
- **D11**：未引入 networkx；多對多用 `bears_on` 的 list，未做傳遞閉包。
- **D10**：DO-3 的 `MAX_SESSION_GAP_BDAYS=10` 有市場理由（農曆年最長休市 ≤ 9 個交易日），
  非擬合值；第 4 步未為了讓 k=20 過關動任何常數。
