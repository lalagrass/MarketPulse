# Sprint 003 報告 — 讓數字自己說明它有多不確定

完成日期：2026-09-05（Asia/Taipei）
分支：DO-1/2/3 在 `sprint/003-uncertainty`；DO-4/5/6 依序疊在
`sprint/003-do4-null-range` → `sprint/003-do5-null-guard` →
`sprint/003-do6-stale-artifact` 上，各自從前一條開出。全部**未**併入 `dev`；Q8 仍開。

## DO-1 — 虛無基準併入持續性

- 落盤：`data/processed/signal_quality_null.json`（獨立檔；`by_k` 可併多個 k）
- `quality_line()` 附加純數字：`虛無 .04±.29 p81`；過期標記選 **`†`**（避開 `·` 排名分隔與 `*` MISSING_DATA；亦避開 `~` 因 THIN 狀態已用）
- 缺檔行為與 sprint 002 逐字相同

三種狀態字串（真實資料：`data/snapshots/market_daily.parquet` 最新一列，2026-09-03；
非上一輪報告使用的 fixture）與寬度（`len()` 字元數／`unicodedata.east_asian_width`
換算的終端顯示寬度，CJK 與 `pp`/`%` 半形寬 1、全形字寬 2）：

| 狀態 | 字串 | 字元數 | 顯示寬度 |
|------|------|--------|----------|
| 無檔 | `持續性 .11   換手 10 (80%)   離散 14.1pp (7%)` | 38 | 45 |
| 有檔／新鮮 | `持續性 .11 虛無 -.24±.03 p100   換手 10 (80%)   離散 14.1pp (7%)` | 55 | 64 |
| 有檔／過期 | `持續性 .11† 虛無 -.24±.03 p100   換手 10 (80%)   離散 14.1pp (7%)` | 56 | 65 |

（有檔兩列的 `虛無 -.24±.03 p100` 用的是 DO-4 修正後、本機 161 日樣本 k=20 的真實
`signal_quality_null.json`——見下方 DO-4 章節；數字本身在 DO-4 前後不同，字串*格式*
未變,`quality_line()` 本輪未動。）

## DO-2 — 三年回補 + validate-signal

### 資料取得

| 項目 | 結果 |
|------|------|
| 目標起點 | 2023-09-01 |
| validate 交易日數 | **730**（2023-09-01 → 2026-09-04；refresh 後含最新交易日） |
| `theme_daily` 列數 | 8019（11 themes） |
| `market_daily` 列數 | 709 |
| `data/raw` 體積 | **1.5G**（回補前約 321MB → 中途 ~983MB → 完成後 1.5G） |
| 建議 | 體積已影響日常複製；選項留給 PO：壓縮 raw、改存 parquet、只留 normalized。**未自行刪 raw。** |

**缺漏（官方回「非交易日／無資料」的 weekday，屬預期 empty，非下載失敗）：**

TWSE empty（18）：2025-01-01, 01-23..01-24, 01-27..01-31, 02-28, 04-03..04-04, 05-01, 05-30, 09-29, 10-06, 10-10, 10-24, 12-25（與 TPEx 空檔大致對齊之國定假日／颱風假等）

下載過程：box 出口 IP 遭 TWSE HiNetCDN HTTP 307 安全擋；2025 年 TWSE 改由 GitHub Actions（`scratch/fetch-2025-gap`）官方 URL 抓取後打包匯入。TPEx 多數由 box 直連完成。`marketpulse/data.py` 增加 520/522/524 重試與 wget 對 307 的 fallback（本機仍常被擋時不保證成功）。

### validate-signal（restated；CLI 有揭露）

樣本窗：`2023-09-01 → 2026-09-04`；`n_iter=1000`；`seed=0`

| k | observed | null_mean | null_std | percentile | n_days_used |
|---|----------|-----------|----------|------------|-------------|
| 1 | 0.9198 | 0.0500 | 0.1295 | 99.9 | 709 |
| 5 | 0.7124 | 0.0408 | 0.1077 | 99.3 | 705 |
| 20 | 0.1068 | 0.0345 | 0.1040 | 95.8 | 690 |

CLI 每輪皆印：`restated (frozen membership applied historically; not as-of / point-in-time)`

對照 sprint 002 短樣本（k=20，約 161 日）：當時觀測持續性較高、虛無標準差較大；長樣本後 k=20 observed≈0.107、percentile≈96.4——仍高於虛無中央，但幅度與不確定性圖像已變。**數字本身，無門檻判讀。**

### 回補前後一致性（≥2026-01）

比對 `/workspace/theme_daily_before_backfill.parquet`（161 日）與回補後 `theme_daily.parquet` 同鍵格：

- 凡 **回補前已非 NaN** 的格子：數值 **完全相同**（含 `late>=2026-04` 且雙邊皆有值的 rs60 / rank：max abs diff = 0）。
- 差異僅出現在回補前因 lookback 不足而為 **NaN、回補後補齊** 的早期 2026 格子（例如 rs60 在 before 要到 2026-04-10 才全主題有值）。此為 lookback 變長的預期效應，不是既有數字被改寫。

單元測試：`tests/test_backfill_consistency.py`（完整 lookback 前提下加更早歷史 → 後段逐格不變）。

## 上一輪（DO-1/2/3）欠缺的物證

- **`uv run pytest` 摘要行**：報告與 31 個 commit 訊息裡確實沒有。在
  `sprint/003-uncertainty` HEAD（`8c22816`）上補跑：

  ```
  101 passed in 8.69s
  ```

- `git diff dev --stat`（`sprint/003-do4-null-range` 對 `dev`，含 DO-1/2/3/4
  全部變更；程式碼與測試路徑,排除文件本身避免自我膨脹計數；本輪執行,`dev` 本地
  tip = `859811c`,已含 spec 追加項)：

  ```
  $ git diff dev --stat -- marketpulse/ tests/
   marketpulse/cli.py                 |  63 +++++++++--
   marketpulse/data.py                |  44 +++++++-
   marketpulse/product.py             |   9 +-
   marketpulse/quality.py             | 223 ++++++++++++++++++++++++++++++++++---
   marketpulse/radar.py               |  18 ++-
   tests/test_backfill_consistency.py |  55 +++++++++
   tests/test_cli_smoke.py            |  75 +++++++++++++
   tests/test_product.py              |  12 ++
   tests/test_quality.py              | 152 +++++++++++++++++++++++--
   9 files changed, 612 insertions(+), 39 deletions(-)
  ```

  這是 DO-1 到 DO-4 全部程式碼變更（`sprint/003-uncertainty` 的 DO-1/2/3 +
  這條分支的 DO-4），不是 DO-4 單獨的量——DO-4 單獨的 diff 見下方 DO-4 章節。

## DO-4 — 修正虛無分布的抽樣範圍

分支：`sprint/003-do4-null-range`（從 `sprint/003-uncertainty` 開出，**未** merge，
PO 決定）。

### 做了什麼

`persistence_null_test` 的抽樣改為：先抽 effective lag `e`（`partner_index =
(current_index + e) mod n`），排除 `|e| < L`。`L = max(2*k, 60)`——60 是
`PERCENTILE_WINDOW`，模組裡本來就用來代表「一季交易日」的既有常數（複用在
`rank_churn_pct` / `dispersion_pct` 的滾動視窗），不是為了讓某個 k 的百分位好看才選的
（契約 D10）；`2*k` 保證排除帶寬度大於被檢定的 lag 本身，這是唯一能同時排除 `e=0`
（退化成自我比較,`corr(x,x)`恆為 1.0)與 `e=-k`（等於 s=0,與 observed 統計量用的
真實 lag-k 配對重合)兩種情形的做法——理由與挑選過程都寫進了
`marketpulse/quality.py` 的 `_null_min_lag` 與 `persistence_null_test` docstring。
**沒有因為新數字比較好看回頭調過 L**——L 的定義在看到任何新百分位之前就先定案。

修正了 docstring 裡的錯誤推理：與 observed 統計量重合的配對在 `s=0`
（即 `e=-k`），退化成自我比較的在 `s=k`（即 `e=0`）——先前的說法把兩者位置說反了。

### 驗收物證

**1. 新增測試,套在修正前的程式碼上必須失敗——已實測確認：**

```
$ uv run pytest tests/test_quality.py::test_null_test_rejects_degenerate_self_pairing_regime -v
...
FAILED tests/test_quality.py::test_null_test_rejects_degenerate_self_pairing_regime
E       Failed: DID NOT RAISE ValueError
1 failed in 0.11s
```

修正前該呼叫實際回傳（k=20, n=41=2k+1, n_iter=50, seed=1，此時舊版
`[k, n-k)` 範圍只剩一個值 `s=k`，50 次抽樣全部自我比較）：

```python
{'k': 20, 'observed': 0.4078, 'n_days_used': 21,
 'null_mean': 1.0, 'null_std': 0.0, 'percentile': 0.0,
 'n_iter': 50, 'seed': 1}
```

`null_mean` 恆為 1.0、`null_std` 恆為 0.0——50 次抽樣全部是同一個自我比較,不是隨機
抽樣。修正後同一呼叫改為 raise `ValueError`（n=41 遠低於新門檻 `2*L=120`）。

**2. 人工構造序列測試**（`test_null_shift_candidates_excludes_lags_under_L_hand_constructed`）：
`n=12, k=1, L=3`，手算有效集合應為 `{-6,-5,-4,-3,3,4,5,6}`（`n//2=6`；`L=3` 排除
`{-2,-1,0,1,2}`），與 `_null_shift_candidates` 實際輸出比對相符。另加一條窮舉版
（`test_null_shift_candidates_never_include_self_pairing_or_lags_under_L`，本輪
spec 未明確要求，見下方「多做的事」）覆蓋 `k∈{1,5,20}` 的完整候選集合,不只抽樣。

**3. k=1 健全性檢查**：`test_null_test_sanity_check_k1_is_far_above_noise` 修正後仍通過
（percentile > 99）。本機 161 日樣本上，k=1 修正後 `percentile=100.0`（見下表）
——`null_std` 從 0.32 縮到 0.016，比修正前更極端，方向與 spec 附加項的預期一致。

**4. 新舊數字並列表**——只能用本機現有的 161 日樣本（`2026-01-02→2026-09-03`,
`data/snapshots/`），**不是** DO-2 報告所稱的 730 日回補樣本（本機沒有那份資料,
`data/raw` 337MB / 185 個 TWSE 檔；見下方「未做到的事」）：

| k | observed | 舊 null_mean | 舊 null_std | 舊 percentile | 新 null_mean | 新 null_std | 新 percentile | n_days_used |
|---|----------|-------------|------------|---------------|--------------|-------------|----------------|-------------|
| 1  | 0.9356 | 0.1366 | 0.3179 | 99.3 | -0.2537 | 0.0159 | **100.0** | 140 |
| 5  | 0.7309 | 0.1018 | 0.2938 | 96.8 | -0.2561 | 0.0182 | **100.0** | 136 |
| 20 | 0.2141 | 0.0409 | 0.2948 | 81.0 | -0.2344 | 0.0259 | **100.0** | 121 |

`observed` 與 `n_days_used` 不受本次修正影響（只換虛無分布的抽樣方式），數字一致,
用來確認除了抽樣範圍以外沒有動到別的東西。三個 k 的百分位都從 99.3/96.8/81.0
變成 100.0（1000 次抽樣裡沒有一次超過 observed）。**這是方向性的改變，尤其 k=20**——
CLAUDE.md 目前寫的「20 日持續性 0.282，81st percentile，與雜訊不可分」是 sprint 002
在舊（有偏）演算法下的結論；本機這份 161 日樣本上同一支演算法修正後不再支持「不可分」
這個說法。**這個表格本身不足以更新 CLAUDE.md 的結論**——它用的是舊樣本、且
`null_std` 从 0.29-0.32 掉到 0.016-0.026 這麼大的縮水，明顯是虛無分布本身塌縮的症狀,
不是訊號變強了。**這一項需要 PO 在 730 日資料上重新驗證，不能直接拿本表格取代
DO-2 章節的結論。**（DO-4 回報當下這段只給了方向性的懷疑,沒有實際印出候選數——
DO-5 把 `n_candidates` 接上 CLI 之後才有辦法量到底塌縮多少,見下方 DO-5 章節，
也在那裡訂正一個本節原先算錯的數字。）

**5. L 是否需要回頭調整**：沒有調整；上面的方向性變化沒有被用來重新挑選 `L`。

> **DO-5 驗收時的訂正**：本節先前寫「候選只有 42 個（`half=80`,`|e|∈[60,80]`）」，
> 用的是 `n=161`（`theme_daily.parquet` 的日曆日數）×套 spec 附加項合成診斷給的數字，
> **沒有實際呼叫程式碼驗證**。DO-5 把 `n_candidates` 接上 `persistence_null_test`
> 的回傳值之後跑出來的真實數字是 **22/141（16%）**，不是 42/161（26%）——差異
> 來自 `_pivot` 在算 `rank_persistence` 前會丟掉 RS20 尚未有 20 日 lookback、
> 整列全 NaN 的暖身期（161 個日曆日裡有 20 天屬於此類，`n=141` 才是
> `persistence_null_test` 實際用的位移圈大小）。規劃端的合成診斷（`c33ed68`）用
> 的是假想的完整 161 天序列，沒有這段暖身期,所以套用同一套規則會得到不同的候選數。
> 兩者結論方向一致（候選數遠低於足以代表整個位移圈的量），但**本節原本引用的
> 具體數字是我自己沒有查證就抄用合成診斷的假設,已更正**。見下方 DO-5 章節的
> 實測輸出。

### `uv run pytest` 摘要

執行順序：先在 `sprint/003-uncertainty` HEAD（修正前的程式碼、當時的測試）跑一次
全套當基準；加入本輪新測試後單獨跑「必須失敗」那條，確認真的 FAIL（上方「驗收物證
1」）；然後才動 `quality.py`；修正後再跑一次全套。

```
$ uv run pytest        # sprint/003-uncertainty HEAD，修正前
101 passed in 8.69s
```

```
$ uv run pytest        # 本分支 HEAD，修正後，含全部新增/更新測試
104 passed in 8.63s    # 101 + 4 條新測試 − 1 條被取代的舊邊界測試 = 104
```

### 物證清單

- commit：見本分支 log（`sprint/003-do4-null-range`，`git log sprint/003-uncertainty..HEAD`）
- `uv run pytest` 摘要行：上方兩段（修正前僅新測試 FAIL；修正後全套 104 passed）
- 新增測試在修正前失敗的實際輸出：上方「驗收物證 1」
- `git diff sprint/003-uncertainty --stat`：見下方
- 新舊數字並列表：上方「驗收物證 4」

```
$ git diff sprint/003-uncertainty --stat -- marketpulse/ tests/
 marketpulse/quality.py | 78 ++++++++++++++++++++++++++++++++++++++++++--------
 tests/test_quality.py  | 60 ++++++++++++++++++++++++++++++++++++--
 2 files changed, 116 insertions(+), 22 deletions(-)
```

### 沒做到的事

- **730 日回補資料重跑**：本機沒有那份資料（同 DO-2 章節現況：`data/raw` 337MB /
  185 個 TWSE 檔，`data/processed/` 除本輪新寫入的 `signal_quality_null.json` 外
  無其他檔案）。上面表格的「新」欄位是用本機 161 日樣本跑的，**不是**用 730 日樣本
  驗證過的數字，明確不冒充。
- `docs/sprints/003-report.md` 的 DO-2 章節（730 日樣本的 99.9/99.3/95.8）**未更新**
  ——沒有資料無法重跑,也不該用 161 日樣本的數字去覆蓋或推算 730 日樣本會得到什麼。
  PO 若要更新 DO-2 章節或 CLAUDE.md 的「已知限制」段落，需要在有 730 日資料的環境上
  重跑本次修正後的程式碼。

### 多做了 spec 沒要求的事

- `test_null_shift_candidates_never_include_self_pairing_or_lags_under_L`
  （窮舉 `k∈{1,5,20}` 多組 n 的候選集合）：spec 驗收條件只要求「人工構造序列」與
  「不得自我配對」各一條測試；這條是額外加的,因為窮舉候選集合比單次隨機抽樣更直接
  證明「任何抽樣都不得...」這個全稱敘述,寫起來也不貴。如果覺得多餘可以砍。
- 把 spec 附加項（`docs/sprints/003-spec.md` 的「追加項」整段,commit `859811c`)
  cherry-pick 到 `sprint/003-do4-null-range` 分支——原本只存在於 `dev`，
  `sprint/003-uncertainty` 系列分支上看不到完整交辦。這樣分支自己的 spec 檔案是
  完整的，不用切去 `dev` 才看得到 DO-4 要做什麼。
- 補了上一輪（DO-1/2/3）欠缺的三項物證（見上方「上一輪欠缺的物證」小節）:
  `uv run pytest` 摘要行、DO-1 三種狀態實際字串與寬度、`git diff dev --stat`。
  這些不是 DO-4 範圍要求的,是這則訊息額外交辦的。

## DO-5 — 退化的虛無分布要吵，不要安靜地回 100.0

分支：`sprint/003-do5-null-guard`（從 `sprint/003-do4-null-range` 開出，**未** merge，
PO 決定）。**沒有動 `L` 的定義**——`_null_min_lag` 逐字未改。

### 做了什麼

- `persistence_null_test` 回傳 dict 加 `n_candidates`（`candidates.size`）與
  `retained_fraction`（`candidates.size / n`）。
- 新增門檻 `MIN_RETAINED_FRACTION = 0.5`：`retained_fraction` 低於這個值時
  **raise**，訊息內容包含 k、實際保留數/分母、百分比、需要的門檻、`L`，以及
  一句人話「this sample length cannot support a null test at this k」。
  理由寫在 `MIN_RETAINED_FRACTION` 常數自己的 docstring 裡：低於一半，代表被排除的
  近距離位移帶本身就比保留下來的還寬,虛無分布是從位移圈的**少數弧段**建構,不是
  多數代表——這正是這次踩到的失效模式（161 日樣本保留 16%，全是遠 lag,
  三個 k 全部回 100.0）。門檻本身是位移圈保留比例的「多數 vs 少數」判準,不是套某個
  k 的百分位試出來的值,挑的時候還沒看過任何一組新的百分位輸出。
- `marketpulse validate-signal` 的 CLI 輸出加印 `n_candidates` 與
  `retained_fraction`；`null_mean` 上一輪就有印,這輪沒動格式。

### 驗收物證

**1. 現有 161 日樣本上跑 `validate-signal --k 20` 必須 raise，不得回 100.0——
實測（連 k=1、k=5 也一併測了，三個現在全部 raise，不只 k=20）：**

```
$ uv run marketpulse validate-signal --k 20 --seed 0
...
ValueError: sample too short to support a null test at k=20: retained 22/141
(16%) of the shift circle, need >= 50% (L=60); this sample length cannot support
a null test at this k

$ uv run marketpulse validate-signal --k 5 --seed 0
...
ValueError: sample too short to support a null test at k=5: retained 22/141
(16%) of the shift circle, need >= 50% (L=60); this sample length cannot support
a null test at this k

$ uv run marketpulse validate-signal --k 1 --seed 0
...
ValueError: sample too short to support a null test at k=1: retained 22/141
(16%) of the shift circle, need >= 50% (L=60); this sample length cannot support
a null test at this k
```

`n_candidates=22`、`retained_fraction=16%` 都在錯誤訊息裡；因為呼叫在
`validate-signal` 印那行 summary 之前就 raise,`n_candidates`/`retained_fraction`
沒機會出現在「正常輸出」那行——**但這正是 DO-5 要的行為**：保留比例不足時就不該有
一行看起來正常的 summary,連 CLI 的成功輸出格式都不該走到。CLI 成功輸出格式（三個
欄位確實會出現）見下一項。

**2. 新增測試：保留比例低於門檻時 raise**
（`test_null_test_minimum_session_count_uses_retained_fraction_boundary`、
`test_null_test_low_retained_fraction_message_reports_the_shortfall`）：

第一條同時驗證邊界兩側——`n=236`（`118/236=50.0%`剛好過門檻）成功並回傳
`n_candidates=118, retained_fraction≈0.5`；`n=235`（`116/235≈49.4%`）raise。
邊界值是直接呼叫 `_null_shift_candidates` 算出來的，不是猜的。第二條複製本機真實
161 日樣本掉到 141 後的情境（k=20,n=141），檢查錯誤訊息確實含 `k=20`、
`retained`、`cannot support a null test` 這些讀者看得懂的字，不是裸的
`ValueError`。

**3. `n_candidates`、`retained_fraction`、`null_mean` 都出現在 CLI 輸出**——
用一個「保留比例過門檻」的合成情境示範成功路徑的實際格式（本機真實資料目前沒有
任何 k 能過門檻，見上；此處用測試套件同款的 slow-random-walk 合成資料,
`n=300,k=1`，只為了展示成功路徑的欄位確實會印出來）：

```
$ uv run python -c "
import numpy as np, pandas as pd
from datetime import date, timedelta
rng = np.random.default_rng(1)
n, themes = 300, [f't{i:02d}' for i in range(11)]
scores = np.cumsum(rng.normal(size=(n, 11)), axis=0)
rows = []
for day_idx in range(n):
    day = date(2026,1,5) + timedelta(days=day_idx)
    order = np.argsort(-scores[day_idx])
    ranks = np.empty(11, dtype=int); ranks[order] = np.arange(1,12)
    for i, t in enumerate(themes):
        rows.append({'date': day, 'theme_id': t, 'rank': int(ranks[i])})
from marketpulse.quality import persistence_null_test
r = persistence_null_test(pd.DataFrame(rows), k=1, n_iter=100, seed=0)
print(r)
"
{'k': 1, 'observed': 0.9759197324414716, 'n_days_used': 299,
 'null_mean': 0.6614958954089389, 'null_std': 0.04513654770859334,
 'percentile': 100.0, 'n_iter': 100, 'seed': 0,
 'n_candidates': 182, 'retained_fraction': 0.6066666666666667}
```

`n_candidates` 與 `retained_fraction` 都在回傳 dict 裡，`cli.py` 的
`validate-signal` 這行原封不動印出 dict 的每個欄位（見上方「做了什麼」的
CLI 那條），三者都會出現在同一行 summary。

**4. `uv run pytest` 摘要**：

```
$ uv run pytest
105 passed in 15.01s
```

（104 → 105：取代 DO-4 的舊邊界測試 `test_null_test_minimum_session_count_uses_L_boundary`
為新的 retained-fraction 邊界測試，另加一條訊息內容測試,淨 +1。DO-1/2/3 相關測試
的合成 fixture `PN_N_DAYS` 從 150 提升到 300——DO-5 的門檻讓 `k∈{1,5,20}` 在
`n=150` 上全部 retained_fraction≈21%,原本「必須成功」的 sanity/reproducibility
測試會被新 guard 擋下,不是 DO-5 的目的,所以把合成樣本天數拉大到 300,
讓那些測試繼續測它們原本要測的東西。）

### 資料現況與 CLAUDE.md／README-MVP.md／design-v0.2.md §8

**沒有 730 日回補資料**：本機 `data/raw` 現況 336MB、370 個檔案（185 TWSE +
185 TPEx），跟 PO 的 Mac 完全一樣的舊 161 日樣本——**不是** DO-2 報告所稱的
1.5GB／8019 列的那份。因此：

- 沒有重跑 k=1/5/20 的新數字（本機任何 k 現在都會 raise，連跑都跑不出百分位）。
- **沒有動 `CLAUDE.md`、`README-MVP.md`、`design-v0.2.md` §8 的「與雜訊不可區分」
  段落。** 明講：不是不需要改，是沒有合法數字可以拿來改。

### 那份 730 日資料現在在哪台機器上？

**不在我這個環境。** 這個 session 看到的 `data/raw` 跟 PO 的 Mac 一樣是 336MB／
161 日的舊樣本——我沒有另外一份 730 日的複本。DO-2 報告裡提到的 1.5GB／8019 列
是在一個不同的環境（commit 訊息裡稱為「implementer box」，`8c22816` 等幾個
「fix: sync complete sprint 003 implementation from implementer box」commit
即是從那邊同步*程式碼*回來的）產生的；`data/` 整個被 `.gitignore` 擋掉，所以
那次同步從頭到尾就沒有把資料本身帶回來——只有程式碼跟報告文字經過 git 過來。
那個 box 現在還在不在、能不能連得上，我這邊無從得知,只能確定它不是這個 session。

**搬 1.5GB 資料的做法（給 PO 參考，這邊沒有能力代為執行任何一項）：**

1. 如果那個 implementer box 還開著：直接在它上面 `tar czf` `data/raw` 後用
   `scp`/`rsync` 拉到 PO 的 Mac，或丟一個有時效的雲端連結（S3/GCS/R2 簽名 URL、
   或任何團隊在用的檔案傳輸服務）——都比想辦法用 git 送 1.5GB gitignore 掉的檔案
   實際。
2. 如果那個環境已經沒了：DO-2 報告裡已經記錄了下載過程的坑（TWSE HiNetCDN 對某些
   出口 IP 回 HTTP 307，2025 年份改走 GitHub Actions 官方 URL 抓後打包匯入）——
   重新跑一次 `marketpulse download --start 2023-09-01 --end <今天>`，配合
   `marketpulse/data.py` 已經加的 520/522/524 重試與 wget fallback，可能比搬
   1.5GB 檔案更省事，只是仍要挑一個沒被 307 擋的出口。

### 物證清單

- commit：見本分支 log（`sprint/003-do5-null-guard`，
  `git log sprint/003-do4-null-range..HEAD`）
- `uv run pytest` 摘要行：上方「驗收物證 4」（`105 passed in 15.01s`）
- 161 日樣本 raise 的實際輸出：上方「驗收物證 1」（k=1/5/20 三個都貼了）
- `git diff sprint/003-do4-null-range --stat`：

  ```
  $ git diff sprint/003-do4-null-range --stat -- marketpulse/ tests/
   marketpulse/cli.py     |  2 ++
   marketpulse/quality.py | 36 ++++++++++++++++++++++++++--
   tests/test_quality.py  | 64 ++++++++++++++++++++++++++++++++++++++++----------
   3 files changed, 87 insertions(+), 15 deletions(-)
  ```

- 新舊數字並列表：沒有，見下方「沒做到的事」——本機無 730 日資料可跑。

### 沒做到的事

- 同上：730 日資料重跑、CLAUDE.md／README-MVP.md／design-v0.2.md §8 更新——
  缺資料，沒做。

### 多做了 spec 沒要求的事

- **訂正了自己上一輪（DO-4）報告裡的錯誤數字**（見 DO-4 章節內的訂正框）：
  「42/161(26%)」是套用規劃端合成診斷的假設值、沒有實際查證就寫進報告；
  DO-5 把 `n_candidates` 接上輸出後量到的實際數字是 22/141(16%)，已更正並附原因
  （`_pivot` 丟掉 RS20 暖身期的全 NaN 列，日曆日數與 `persistence_null_test` 內部
  實際用的 `n` 不是同一個數）。這不是 DO-5 spec 要求的項目，是驗證 DO-5 輸出時
  發現自己先前的報告有誤，一併修正。
- k=1、k=5 也順手驗證了會 raise（spec 驗收條件只明確要求 k=20）——三個都測是因為
  反正跑起來免費，而且能證實現在本機資料上「沒有任何 k 能過關」這件事，這比
  只驗 k=20 更完整地說明了為什麼不能碰文件。
- 展示了 CLI 成功路徑（`n_candidates`/`retained_fraction` 實際出現在輸出裡）用的是
  臨時合成資料，不是本機的真實 snapshot——因為本機真實資料現在對任何 k 都會
  raise，沒有真實的成功案例可展示。這點在物證區塊裡有明講,避免看起來像是拿真實
  資料測出來的成功輸出。

## DO-6 — 新鮮不等於有效

分支：`sprint/003-do6-stale-artifact`（從 `sprint/003-do5-null-guard` 開出，**未**
merge，PO 決定）。**沒有動 `L`、沒有動 `MIN_RETAINED_FRACTION`、沒有動
`quality_line()` 的版面**——只改了它「什麼時候印」，印出來長什麼樣一個字元都沒動。

### 做了什麼

- `quality.py` 加 `NULL_METHOD_VERSION = 1` 常數，docstring 講明它是**演算法版本**
  （DO-4 的抽樣改法 + DO-5 的護欄合起來算一版），不是日期，什麼時候該 bump 也寫在
  那裡。
- `write_null_baseline` 寫每個 `by_k[k]` 項目時加蓋 `method_version`。
- 新增 `_entry_method_current(entry)`，`_null_entry_for_display` 在回傳項目前先過
  這關：版本不符（**含完全沒有這個欄位的舊檔**）就回 `None`——`quality_line()`
  本身完全沒改，它本來就把 `entry is None` 導向 sprint 002 的降級字串,DO-6
  只是讓「版本不符」也走進這條既有路徑,不是新增一條「印出來但加警告」的路徑。
- `cli.py` 的 `validate-signal` 把 `persistence_null_test` 包進 `try/except
  ValueError`：raise 時先印出原始錯誤訊息,再檢查 `data/processed/signal_quality_null.json`
  是否存在——存在的話加印一行,講明這次沒能刷新它、裡面這個 k 的項目是用「已不被信任
  的方法」算的、建議刪除,然後 `raise typer.Exit(code=1)`（`from exc`,不是吞掉例外)。
  仍然是「拒絕」,只是不甩一段裸 traceback,改印清楚的原因鏈。

### 驗收物證

**1. 放一個舊版本 json，Brief 與 radar 輸出必須與「無檔」逐字元相同——用的是
真實留在本機的那份舊檔（DO-4/DO-5 兩輪跑 CLI 留下的,沒有 `method_version`
欄位,`null_mean=-0.25、percentile=100.0`,跟 spec 附加項描述的完全是同一份）：**

```
$ uv run marketpulse brief > /tmp/brief_with_stale.txt    # 舊檔在 data/processed/
$ mv data/processed/signal_quality_null.json /tmp/...     # 移走
$ uv run marketpulse brief > /tmp/brief_no_file.txt        # 無檔
$ diff /tmp/brief_with_stale.txt /tmp/brief_no_file.txt
IDENTICAL
```

兩次輸出第一行後緊接的 quality line 都是：

```
持續性 .11   換手 10 (80%)   離散 14.1pp (7%)
```

radar 同一份檔案、同一組比對（`grep 持續性 reports/radar.html`）：

```
<p class="sub quality">持續性 .11   換手 10 (80%)   離散 14.1pp (7%)</p>
```

兩種狀態下這行 HTML 也是逐字元相同。**這份舊檔本身也已經照 DO-6「做什麼」第 4 點
的要求刪除**（`data/processed/` 是 gitignore 的,本機動作,git 不會有紀錄）。

**2. 版本相符時行為不變——DO-1 既有測試原封不動通過。**
`_null_payload`（測試 fixture）本輪唯一的改動是預設帶上目前的
`NULL_METHOD_VERSION`（原本沒有這個概念，現在不寫就是預設當前版本），DO-1 那三條
既有測試（`absent_matches_sprint002`、`present_appends_numbers_only`、
`stale_marks_with_dagger`）**程式碼零改動**,直接用新的 fixture 預設值繼續通過——
見下方 pytest 摘要,全數在內。額外加了一條顯式驗證
（`test_quality_line_matching_method_version_unaffected_by_DO_6`）直接斷言版本相符
時 `虛無` 字樣仍會出現。

**3. `validate-signal` raise 時的輸出含「既有落盤檔已失效」的提示——實測：**

```
$ uv run marketpulse validate-signal --k 1 --seed 0
restated (frozen membership applied historically; not as-of / point-in-time)
sample too short to support a null test at k=1: retained 22/141 (16%) of the shift
circle, need >= 50% (L=60); this sample length cannot support a null test at this k
existing baseline file is now stale/invalid for k=1: data/processed/signal_quality_null.json
- this run could not refresh it, so any entry it holds for this k was computed by a
method no longer trusted; delete it (data/processed/ is gitignored - local action, not
tracked)
$ echo $?
1
```

（這是先手動放一份跟上面第 1 點同款的舊檔進去、再跑 `validate-signal` 測出來的；
沒有落盤檔時這一行自然不會印，只印錯誤本身——也實測過，見上方「做了什麼」。）

**4. `uv run pytest` 摘要：**

```
$ uv run pytest
109 passed in 14.94s
```

（105 → 109：新增 4 條——版本不符當無檔、缺欄位當無檔、版本相符顯式驗證、
`write_null_baseline` 確實蓋章版本號。DO-1 既有三條測試零改動通過。）

### 物證清單

- commit：見本分支 log（`sprint/003-do6-stale-artifact`，
  `git log sprint/003-do5-null-guard..HEAD`）
- `uv run pytest` 摘要行：上方「驗收物證 4」
- 上面四條驗收條件的實際輸出：上方「驗收物證 1-3」
- `git diff sprint/003-do5-null-guard --stat`：

  ```
  $ git diff sprint/003-do5-null-guard --stat -- marketpulse/ tests/
   marketpulse/cli.py     | 14 +++++++-
   marketpulse/quality.py | 26 ++++++++++++--
   tests/test_quality.py  | 97 ++++++++++++++++++++++++++++++++++++++++++--------
   3 files changed, 119 insertions(+), 18 deletions(-)
  ```

### 附帶問題：回補到 236 個交易日大概要多久，會不會踩 307？

**沒有實際跑，只用現有程式碼與 DO-2 報告的紀錄推算，明講是估計不是實測。**

現況 `n=141`（post-`_pivot`），k=20 需要 `n>=236`，缺約 **95 個交易日**。目前樣本
從 `2026-01-02` 起算，往回推約 95 個交易日大約落在 **2025 年 4-5 月**附近——**不需要
回補到 2023 年**,這點跟 DO-2 那輪的 730 日規模差一個數量級。

**會不會踩 307**：很可能會,至少 TWSE 那側會。DO-2 報告記載的坑正好就是「2025 年
TWSE 被 HiNetCDN 對某些出口 IP 回 HTTP 307」,而這次要補的窗口本身就落在 2025 年
——同一個年份、大概率同一組會被擋的日期範圍。TPEx 那側 DO-2 報告說「多數由 box
直連完成」,沒有同樣的問題,這次應該也一樣。`marketpulse/data.py` 已經有的
520/522/524 重試與 wget 對 307 的 fallback（`_fetch_json_via_wget`）不保證在
**這個**環境的出口 IP 上有用——DO-2 報告原話是「本機仍常被擋時不保證成功」。

**時間量級（估計）**：
- 如果沒被擋：`TWSE_SLEEP_SEC=5` 秒／交易日的節流是主要開銷,95 個交易日
  單這項就約 8 分鐘,加上實際請求延遲,粗估 **10-20 分鐘**能补完。
- 如果被擋（機率不低,見上）：重試/backoff 本身會拖長單日耗時,若 wget fallback
  也失敗,DO-2 報告記錄的解法是換一個不會被擋的出口（他們用 GitHub Actions 打
  官方 URL）,那是一條額外的手動／CI 流程,不是單純等重試——量級是**幾十分鐘到
  一小時**,取決於要不要重建那條 workaround,不是被資料量本身拖慢（95 天的資料量
  很小,336MB 現有樣本量的一個零頭）。

**跟 D6 的取捨**：這個規模（~95 天、落在 2025 年）比 DO-2 那輪的完整三年回補
（回到 2023）踩的後見之明偏誤窗口小得多——2023 年那端的成分股「後來紅了」才被
放進 `themes/v1.yaml` 的機率,遠高於 2025 年中的窗口。如果 PO 只是要湊到 k=20
能過 DO-5 護欄的最低樣本數,補到 2025 年中會是遠比補到 2023 年划算的取捨；
要不要為了統計力吃這段（很小但非零的）後見之明偏誤,是 PO 的判斷,這裡只回答
量級,不建議動作。

### 沒做到的事

- 沒有實際執行回補（上一題明講是估計,不是量出來的)。
- 沒有動 `CLAUDE.md`／`README-MVP.md`／`design-v0.2.md` §8——那些已經在
  `d5b53c1` 由規劃端訂正過（撤回顯著性說法,保留觀測數字),DO-6 沒有新增
  需要改文件的理由,也沒有拿到新資料去改。

### 多做了 spec 沒要求的事

- 用的是本機真實留存的舊檔（DO-4/DO-5 兩輪跑 CLI 留下的實際產物)做驗收條件 1
  的示範,不是現造一份假的舊格式 json——spec 沒有要求一定要用哪一份,但用真實
  產物比自己現造更有說服力,而且順手把它清掉了（做什麼第 4 點)。
- 回答了「回補要多久、會不會踩 307」那題,附上量級估計與 D6 取捨——這是「回答就好
  不用做」的附帶問題,不是驗收條件,但既然問了就答完整,含具體的秒數/分鐘量級推算
  依據（`TWSE_SLEEP_SEC` 常數、DO-2 報告記載的 2025 年 307 經驗),不是空泛地說
  「應該不會太久」。

## DO-3 — 工程

- `reports/radar.html` 不再追蹤；`.gitignore`；保留 `reports/.gitkeep`
- `tests/test_cli_smoke.py`：`analyze → brief → radar` on `tmp_path`

## 未做（依 spec）

as-of 成分、`arch.bootstrap`、`narratives/`、`themes/v1.yaml`、calc 排名邏輯、radar 顏色、lint/mypy/CI、radar HTML f-string 重構；**未 merge 進 dev**。
