# Sprint 006 — 給 IC 表一個參照點

狀態：待實作
契約：CLAUDE.md 與 docs/coding-contract.md 全數適用
層次：第一層（數學）＋ 一格 ENG
起因：`docs/sprints/005-review.md` R1–R7。**先讀那份，再讀這份。**

## Appetite

- 模組：只動 `marketpulse/quality.py`、`marketpulse/calc.py`、`marketpulse/cli.py` 與對應測試。**不新增模組檔、不新增 CLI 子命令**（`rank-ic` 加旗標即可）。
- 相依：**不新增任何套件**（不引 scipy）。
- 資料：不回補、不改 `themes/v1.yaml`、**不新增任何 JSON 產物**。
- 層：只動 L1 診斷輸出。不動主排名（仍 RS20）、不動第二層、不動 `refresh`／`brief`／`radar`（DO-3 的 ENG 修正除外，且不改顯示字串）。
- 超出即為下一輪：換 primary、composite、依 IC 調窗口、as-of 成分、IC 進 daily 產物。

## 目標

讓 `rank-ic` 的九格各自有虛無基準，使「短端信、長端打折」成為可複核的判斷而不是對 0 讀出來的錯覺。

## PO 的前提決定

1. **005 三項 DO 功能面接受**，分支不 merge。006 從 `sprint/005-horizon-ic` 開分支。
2. **不換 primary rank**（維持 RS20）。IC 是買資訊，永遠不回頭改 rank。
3. **IC 表的讀法在 006 出數字之前不定案。**005-report 的「對角線隨天期上升」暫時降級為觀察。
4. 不設顯著性門檻、不寫「顯著」字樣（D10）。虛無數字並列，讀者自己判。

## 要做的

### DO-1 — 每格 IC 配一個循環位移虛無，並拿掉 se　[L1・買資訊]

**背景。**`005-review.md` R1：表只印 `mean±se`，讀者唯一基準是 0，但 `signal_quality_null.json` 顯示同族統計量的虛無中心是 +0.059～+0.064 而非 0。R4：`sd/√n` 沒扣前向窗重疊。兩條同一個修法。

**做什麼。**

- 沿用 `quality.py` 既有的循環位移機制（`persistence_null_test`、`_null_min_lag`、有效位移保留率護欄）。對每個 `(k,h)` 格：把前向那一側的日序**循環位移** e 天後重新配對，重算 mean IC，重複 `NULL_TEST_ITER` 次，`seed=0`。位移合法性與保留率護欄沿用現行常數，**不新增第二套規則**。
- 每格輸出：`observed`、`null_mean`、`null_std`、`sigma`、`n_ge_observed`、`n_iter`、`n_days`、`retained`（保留位移比例）。
- **移除 `se` 欄位**，`compute_rank_ic` 與 `format_rank_ic_table` 都不再回傳／列印它。
- **不印 percentile**（004 `3d812c4` 的教訓：飽和值不是量測值）。JSON 也不寫——本輪不產生任何檔案，只印到 stdout。
- 旗標：`--iter`（預設 `NULL_TEST_ITER`）供冒煙測試調小。`--as-of` 維持。

**驗收條件。**

1. `uv run marketpulse rank-ic` 印出九格，每格含上列八個欄位；輸出中不含 `se=`、不含 `percentile`、不含「顯著」「significant」。
2. **同一統計量只有一份實作：**測試斷言虛無路徑算出的 `observed` 與 `compute_rank_ic` 的 `mean_ic` 逐位元相等（`==`，不是 approx）。兩邊若分岔就是 bug。
3. 決定性：同一輸入跑兩次，九格所有數字逐字元相同。
4. 合成資料測試：每天橫斷面獨立亂排 → 某格 `sigma` 落在 ±3 以內；固定單調順序 → 該格 `sigma` 明顯為正且 `n_ge_observed == 0`。
5. 護欄未過（保留率不足）的格子印 `n/a` 並附原因字串，**不印一個算不準的數字**。
6. `refresh`／`brief`／`radar` 產物逐字元不變。

**會動到的檔案。**`marketpulse/quality.py`、`marketpulse/cli.py`、`tests/test_rank_ic.py`。

**本項不做。**不改 RS 定義、不合成九格總分、不依虛無結果自動調窗口、不寫 JSON。

### DO-2 — 三道防止誤讀的護欄　[L1・交付正確性]

**背景。**`005-review.md` R2／R3／R7。

**做什麼。**

1. **`(k=20,h=20)` 等同 `rank_persistence_20`** — 主 rank 是 RS20 的橫斷面排名，秩變換後兩者只差時間軸平移（物證：兩邊都是 `0.14037651721575425`、`n=367`）。在表格該格加一個固定標記（例如 `‡`）與表尾一行固定說明：`‡ 此格等同 rank_persistence_20，非獨立物證`。**字面鎖定，不依數字改寫（D10）。**
   加回歸測試：同一份 snapshot 上 `compute_rank_ic` 的 (20,20) `observed` 與 `compute_market_quality` 的 `rank_persistence_20` 平均值相等（容差 1e-12）。這條測試以後若紅，代表有人動了 rank 或 RS 定義。
2. **lag 對齊測試** — 現行 `test_monotone_...` 用 `np.tile` 造固定順序，把 `iloc[i+h]` 寫成 `iloc[i]` 或 `iloc[i-h]` 都照樣 +1，抓不到 spec 005 兔子洞第一條。改用**每 3 天循環輪轉橫斷面**的合成資料：只有 `h ≡ 0 (mod 3)` 的格子接近 +1，其餘接近 −0.5。斷言這個模式。
3. 刪掉 `tests/test_rank_ic.py` 的恆真斷言 `assert "mean" not in text.lower() or True`，改成真的斷言或移除。

**驗收條件。**

1. 三條都有對應測試；第 2 條的測試在「把 `i + h` 改成 `i`」時**必須紅**——evidence 要貼刻意改壞後的失敗輸出，證明它抓得到。
2. `‡` 標記與說明字串在 `rank-ic` 輸出中出現，且不與既有 glyph（`†` STALE、`*`／`~`／`·`）衝突。

**會動到的檔案。**`marketpulse/quality.py`、`tests/test_rank_ic.py`。

**本項不做。**不移除 (20,20) 那一格（並列本身有價值），只標註。

### DO-3 — 掃掉 005 review 的三個小洞　[ENG]

**背景。**`005-review.md` R5／R6／R7。

**做什麼。**

1. `marketpulse/calc.py`：`above_cols` 為空時回 `np.nan` 而非 `pd.Series(0, ...)`。同段的 `breadth`、`theme_ret_*`、`theme_tv`、`theme_vol` 全部已是 `np.nan`，只有 `above_count` 例外 → 同一天會出現 `breadth=NaN` 但 `above_count=0`。
2. `format_rank_ic_table` 欄寬不足導致相鄰格黏在一起（物證見 `005-evidence.md` 的 `se=0.0181+0.0840`）。DO-1 換欄位後一併給足欄距。
3. `tests/test_quality.py::test_quality_line_null_baseline_absent_matches_sprint002` 已不再逐位元等於 sprint-002（005 DO-3 加了短註），測試名改成描述現行行為的名字。

**驗收條件。**

1. 單元測試：主題成員全部不在 `above` 欄位時 `above_count` 為 NaN，且與同列 `breadth` 一致為 NaN。
2. 表格任兩格之間至少兩個空白，evidence 貼實際輸出。

## 兔子洞

- **效能。**九格 × 1000 次 × 約 380 天的 11 點秩相關 ≈ 340 萬次小相關，逐日 pandas 迴圈會慢到不能用。做法：**先把每日橫斷面的秩向量預算成一個 `(n_days × n_themes)` 的 numpy 陣列**（NaN 保留），之後每次位移用向量化的 row-wise Pearson 一次算完，把 1000 次迭代降成 1000 個向量化運算。**但秩與 NaN 的處理必須與 `_spearman_cross_section` 完全一致**——這正是驗收條件 2 存在的理由：不一致就會被那條測試抓到。
- 虛無中心為什麼是 +0.06 而不是 0，本輪**不查也不修**。量到多少報多少，寫進 evidence 當 006 的 UNKNOWN。
- 別順手重構 `persistence_null_test`。它是 004 驗收過的東西，共用它的 helper，不改它的行為。
- `--iter` 調小只供冒煙，正式 evidence 必須用預設值跑。

## 本輪明確不做

- 換 primary／composite／Elo／RRG／依 IC 調窗口
- as-of 成分、雙池（Q5／Q6）
- IC 進 `refresh`／`brief`／`radar`／任何 JSON 產物
- 為 IC 設顯著性門檻或加形容詞
- merge 進 `dev`

## 這裡容易踩到的契約紅線

- **不做綜合評分**：九格並列，不合成總分。
- **不用未來資料**算當日 RS；前向窗維持 (T, T+h]。
- **D10**：`‡` 說明與既有短註都是固定文案，不依數字改寫。
- **R3**：第二層不得回頭影響本輪任何數字。

## 權限邊界

- 分支：`sprint/006-ic-null`，**自 `sprint/005-horizon-ic`**（005 尚未併入 `dev`）。
- 可碰：上列三個模組、`tests/`、`docs/sprints/006-*`、`docs/product/backlog.md`。
- 不可碰：`themes/v1.yaml`、顏色／簽章常數、第二層 schema、`persistence_null_test` 的行為、`dev`。
- **不 merge。**

## 回報時必須附的物證 → `docs/sprints/006-evidence.md`

- 每項 DO 的 commit hash（全長）
- `uv run pytest` 的實際摘要行
- `git diff sprint/005-horizon-ic --stat`
- DO-1：九格完整輸出（預設 iter），含護欄未過的格子長什麼樣
- DO-2：把 `i + h` 改成 `i` 之後的**測試失敗輸出**，再貼改回來後通過的那行
- DO-3：`above_count`／`breadth` 同為 NaN 的測試名，與修好欄距後的表格

## 留給實作者的未決問題

1. 位移側：位移前向那一側還是 RS 那一側？**預設位移前向側**（與「RS 是已知、未來是被打亂的那個」的敘事一致）。若向量化後另一側明顯更省，改了要在 evidence 說明並確認驗收條件 2 仍成立。
2. 護欄未過時的 `n/a` 原因字串措辭 — 自己定，寫進測試鎖死。
3. 效能若仍不可接受（單次跑 > 5 分鐘），**先回報再動手**，不要自行降 `n_iter` 預設值。
