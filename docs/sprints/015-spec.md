# Sprint 015 — 價格重設要出聲

狀態：待實作
契約：`CLAUDE.md` 與 `docs/coding-contract.md` 全數適用
層次：第一層（正確性）＋ 把結果送到第二層的畫面
分支：`sprint/015-price-resets`，自 `dev`（014 併入之後）

## Appetite

- 模組：`marketpulse/baskets.py`、`marketpulse/calc.py`（只讀既有函式，不改公式）、
  `marketpulse/cli.py`（傳參數）
- 相依：不新增
- 資料：不新增檔案、不改任何價格
- 層次：只動第一層的**揭露**與第二層的**顯示**。不改 `theme_daily.parquet`、
  不改 `market_daily.parquet`、不改 `brief` 與 `radar` 的產物（D14 本輪不推翻）
- 超出以上任何一項就是下一輪

## 目標

一句話：**籃子的數字裡有價格斷點的時候，畫面要說出來。**

回答主排名回答不了的什麼：主排名不會告訴你「這個 −24% 是市場，還是一檔的除權」。

## PO 的前提決定

1. **不改價格方法。**`docs/coding-contract.md` §8 與 open-questions Q3 維持不變：
   只量測、只揭露，不還原、不剔除、不補值。RS 數字本輪一個都不變。
2. **不重新發明偵測。**`calc.py:216 impossible_daily_returns(bars, themes)` 已經在做這件事
   （012 DO-2 之後用交易所檔位表，不是浮點比率）。本輪是把它的結果**送到籃子面板上**，
   模式與 sprint 010 相同（已經算出來、但沒有送到畫面上的東西）。
3. **不分「是哪一種公司行為」。**除權、減資、分割要查哪一種，是另一輪的事，
   而且需要外部資料。本輪只回答「這個價格水準有沒有回去」。

## 要做的

### DO-1 — 籃子的窗內有價格斷點就標出來

**背景（可重現的現象）。**2026-09-09 的 `baskets` 面板：
`asic_xpu/xpu_not_squeezing_gpu` 成真籃印 `RS20 −24.0%`，
`memory_passthrough/nand_price_passthrough` 反面籃印 `RS20 −15.0%`。
兩籃都含 `6669`，而 `data/raw/twse` 的收盤是
`08-31 7,095 → 09-02 2,610 → 09-04 2,565 → 09-08 2,340`。
物證見 `014-review.md` §5.1。

**交付功能。**

`baskets` 面板的每一格，若該籃成員在對應的 k 日窗內出現 `impossible_daily_returns`
列出的日期，該格的 RS 值旁加一個固定記號，並在該支線的區塊下方列出
「哪一檔、哪一天、`return_1`」。RS 數值本身不變。

**驗收條件**

- G1 — WHEN 某籃成員在 RS20 的窗內有 `impossible_daily_returns` 的紀錄
  THEN 該籃的 `RS20` 欄旁出現記號，且 `RS5`／`RS60` 依各自的窗獨立判定
- G2 — WHEN 記號出現 THEN 該支線下方列出造成它的（代號、日期、`return_1`），
  每筆一行
- G3 — WHEN 沒有任何成員命中 THEN 該支線的輸出與本輪之前逐字元相同
- G4 — WHEN 面板被印出 THEN 三個 RS 欄的數值與本輪之前逐字元相同（只加記號，不改數字）
- G5（目視）— 有記號的那一格，讀的人看得出「這個數字不能照字面讀」。
  **目視驗證，貼原文，不得以測試通過為證據；測試名稱不得承載該宣稱。**

**會動到的檔案。**`marketpulse/baskets.py`、`marketpulse/cli.py`（把 `bars` 與 `themes`
傳給既有函式；`baskets` 指令已經有 `--themes-path`）。

**必須新增的測試。**窗內命中／窗外不命中、三個窗各自獨立、無命中時輸出不變、
RS 數值不因記號改變、多檔命中時逐筆列出。

**本項不做。**不改價格、不剔除成員、不調整 `member_count`、不影響 `breadth` 與
`value_share`、不碰 `brief` 與 `radar`。

### DO-2 — 273 筆裡有幾筆是「回不去的」（買資訊）

**背景。**012 之後 `impossible_daily_returns` 留下 273 筆，最小 `|r|` 是 10.0287%。
這 273 筆混了三種東西（真斷點、除權息基準價、`shift(1)` 跨停牌），
backlog 早就記著要綁在一起排。6669 那一筆是第一個被證明會傷到輸出的。

**買資訊。**醜的、可丟棄的、不進 `marketpulse/`。放 `scripts/` 或直接貼輸出。

**做什麼。**對 273 筆的每一筆，判斷斷點之後 20 個交易日內，該檔收盤**有沒有任何一天
回到斷點前一日的收盤**。回得去 → 暫時性；回不去 → 價格水準重設。輸出兩組的筆數與清單。

**驗收條件**

- G6 — WHEN 腳本跑完 THEN 273 筆被分成「回得去」與「回不去」兩組，總數相加等於 273
  （不足 20 個交易日的另計一組並說明筆數）
- G7 — WHEN 6669 / 2026-09-02 那一筆被判定 THEN 它落在「回不去」那一組

**本項不做。**不判斷是除權、減資還是分割；不引入任何外部資料源；
不因此修改 `themes/v1.yaml` 或任何價格。**不得為了讓分組好看而調整 20 這個窗**——
它取自既有的 RS20，不是新挑的參數。

### DO-3 — F8 的判準修正（本輪 ENG 保留格）

**背景。**014 F8「這條上游不區辨」在真實資料上一次都沒觸發。
`baskets.py` 用 `frozenset(row.declared)` 比整組相等，而
`semiconductor_test` 出現在三條支線的 `either_way`，三組寫法各不相同。
**spec 的判準寫錯了，不是實作的錯**（`014-review.md` §4）。

**交付功能。**判準改成「同一個 `theme_id` 出現在兩條以上支線的 `either_way`」，
提示列出那個 id 與其他支線。

**驗收條件**

- G8 — WHEN 一個 `theme_id` 出現在兩條以上支線的 `either_way`
  THEN 那幾條支線都印出提示，且提示裡指名的是那個 id
- G9 — WHEN 在 `narratives/2026-09-08.yaml` 上執行 THEN `semiconductor_test` 的提示
  出現在 `mediatek_asic_share`、`hbm4_base_die_tsmc`、`nand_price_passthrough` 三條上
- G10 — WHEN 同一則故事的兩條支線共用同一個 id THEN 不算不區辨（014 已有此測試，行為不變）

**會動到的檔案。**`marketpulse/baskets.py`。

**必須新增的測試。**單一 id 跨兩條支線觸發、跨三條觸發、同一則故事內不觸發、
完全不共用時不觸發。

## 兔子洞

- **不要為了知道「窗內」而重算窗。**`n_day_return` 已經定義了窗；用同一個定義取日期範圍，
  不要自己數交易日。
- **`impossible_daily_returns` 掃全市場 170 萬列。**baskets 只需要籃子成員那幾檔，
  但**不要為此改那個函式的簽章**——先整份呼叫再過濾；真的慢再回報，不要先優化。
- **DO-2 的「回到斷點前收盤」要用實際收盤比較，不要用報酬率累乘。**
  跨除權的累乘會把問題本身當成答案。

## 本輪明確不做

- 還原股價、剔除異常列、補值 —— §8／Q3 不變
- 判斷是除權、減資還是分割 —— 需要外部資料，另一輪
- `US:` 前綴與「不可計價」顯示 —— 押後 016
- 把記號帶進 `brief` 與 `radar` —— D14 本輪不推翻，等 DO-1 的寫法穩定
- 擴 `themes/v1.yaml` —— 會動到第一層每一個數字

## 這裡容易踩到的契約紅線

- **§8／Q3：**只量測回報，不改價格方法。G4 就是這條的驗收。
- **R3：**第二層不得改變第一層的數字。本輪是第一層的診斷往第二層的畫面走，方向是對的。
- **D10：**DO-2 的 20 日窗取自既有的 RS20，不是新挑的參數；不得為了分組好看而調整它。
- **D14：**`brief` 與 `radar` 產物本輪不得改變。

## 權限邊界

可碰：`marketpulse/baskets.py`、`marketpulse/cli.py`、`tests/`、`scripts/`。
不可碰：`marketpulse/calc.py` 的公式（只讀 `impossible_daily_returns`）、
`quality.py`、`radar.py`、`product.py`、`themes/v1.yaml`、`narratives/`、`data/`。
**不要 merge。**PO 決定。

## 回報時必須附的物證 → `docs/sprints/015-evidence.md`

- 每項 DO 的 commit hash
- `uv run pytest` 的實際摘要行（不是「全部通過」）
- `git diff dev --stat`
- G3／G4：本輪前後 `uv run marketpulse baskets` 的輸出與 `diff`
- G1／G2：在 `narratives/2026-09-08.yaml` 上的實際面板輸出全文
- G6／G7：DO-2 的兩組筆數與 6669 那一筆的所在組
- G9：`semiconductor_test` 三條提示的實際輸出行

## 留給實作者的未決問題

1. DO-1 的記號用什麼字元？規劃端傾向 `*`（Brief 已用 `*` 表示缺值成員，語意接近
   「這個數字有事」），但若你發現會跟既有輸出混淆，換一個並在回報裡說明。
