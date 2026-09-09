# Sprint 016 — 讓錯誤自己出聲

狀態：待實作
契約：`CLAUDE.md` 與 `docs/coding-contract.md` 全數適用
層次：工程（流程與顯示層），**不動任何數字**
分支：`sprint/016-make-errors-loud`，自 `dev@480e869`

## Appetite

- 模組：`marketpulse/product.py`（一個函式）、`marketpulse/baskets.py`、新增 `scripts/`
- 相依：不新增
- 資料：不新增、不修改
- 層次：只動顯示層與流程。`theme_daily.parquet`、`market_daily.parquet`、
  `brief` 與 `radar` 的產物**全部逐字元不變**
- 驗收條件總數上限 **8 條**（`skill-retro-2026-09-09.md` §4 追記的新上限，本輪首次適用）
- 超出以上任何一項就是下一輪

## 目標

一句話：**把三類會靜默發生的錯誤，變成會出聲的。**

回答主排名回答不了的什麼：本輪不回答產品問題。這是 ENG 輪，
起因是 `skill-retro-2026-09-09.md` 量到的——**規則加了七次，發作率沒降。**

## PO 的前提決定

1. **先做腳本，不做 hook。**retro §1 建議 `Stop` hook（`exit 2` 可擋住收工）。
   **規劃端本輪自己降級這個建議**：一個永遠無法滿足的 `Stop` hook 會讓 session
   停不下來。腳本先跑，證明判準不會誤殺，再談要不要掛 hook。
   hook 的設定寫成**註解範例**放在腳本裡，預設不啟用。
2. **`_ljust` 溢出用截斷處理，不是加大欄寬。**加大欄寬只是把下一次撞牆推遠；
   截斷讓溢出當場可見。
3. **不抽表格層。**retro §2 原本建議抽一層共用表格。查過之後這一輪不需要——
   病灶是 `_ljust` 一個函式，抽象是更貴的解法。若 016 之後仍有第五次，再抽。

若 PO 改選別的：推翻 (1) 則 DO-1 要加 hook 設定與逃生開關；
推翻 (2) 則 DO-2 改成調整 `BRANCH_COL_WIDTH`（規劃端不建議）。

## 要做的

### DO-1 — `scripts/acceptance-check.sh`（本輪 ENG 保留格）

**背景（可重現的現象）。**`docs/product/backlog.md` 於 2026-09-06（`5534918`）
記下這一項，至今未實作。同期間規劃端把沒複驗的機制診斷寫進文件**七次**
（`skill-retro-2026-09-09.md` §1 表格與 §4 追記）。

**交付功能。**一支腳本，吃一個 spec 檔或一個 evidence 檔的路徑，逐項檢查並列出違反處。
零判斷、零模型、純文字比對。檢查項：

```text
總則：spec 檔的檢查（A*）一律跳過 fenced code block（``` 之間），
      那裡面是範例與貼上來的輸出，不是宣稱。
      **evidence 檔的檢查（B*）不跳過**——pytest 摘要行必然在 code block 裡，
      跳過的話 B1 永遠不會過。

spec 檔
  A1  每條驗收條件含 WHEN … THEN …（含標「（目視）」的，不設例外）
  A2  含目視詞（對齊／一眼／看得出／好懂）的條件，同一段落內出現
      「目視驗證」與「不得以測試通過為證據」
  A3  形如 marketpulse/foo.py:123 的引用，檔案存在且行數足夠。
      **引用一律寫完整路徑**——basename（foo.py:123）視為違反，
      理由是同名檔案會讓解析出錯，而完整路徑對讀的人也比較好
  A5  wc -l ≤ 200
  A6  驗收條件代號的數量 ≤ 8。只數行首形如「- H1 —」的那種行

evidence 檔
  B1  含形如 `N passed in Ns` 的實際 pytest 摘要行
  B2  spec 裡每個驗收條件代號，在 evidence 裡至少出現一次
```

**A4 已刪除（編號留空，不重排）。**原本要檢查「三位以上的裸數字寫進驗收條件時
必須標『量出來的』」。刪除的理由是機械化不了：股票代號（`6669`）、日期、行號
都會被誤殺，而**一支會亂叫的檢查器會被忽略，那才是最貴的失敗**。
這一類（把量出來的數字寫死）交給開工前自檢——2026-09-09 的實測是它命中了 `273`，
不需要腳本。

**驗收條件**

- H1 — WHEN 腳本吃 `docs/sprints/015-spec.md` THEN 它至少指出 line 28 的
  basename 引用（A3）與驗收條件代號超過上限（A6），各附行號，退出碼非零

  > **本條初稿有兩個錯，更正的全文見 `016-review.md` §4。**
- H2 — WHEN 腳本吃 `docs/sprints/016-spec.md`（本檔）THEN spec 檔的五項
  （A1／A2／A3／A5／A6）全過，退出碼 0

**會動到的檔案。**新增 `scripts/acceptance-check.sh`。不動 `marketpulse/`。

**必須新增的測試。**無——它是腳本不是產品程式碼，驗收由 H1／H2 的實際輸出擔保。

**本項不做。**不掛 hook、不改 `.claude/settings*`、不檢查語意、
不對 `docs/` 以外的檔案跑、不自動修正任何東西。

### DO-2 — `_ljust` 溢出時要出聲

**背景（可重現的現象）。**2026-09-09 的 `baskets` 面板：

```text
memory_passthrough/nand_price_passthrough誰贏都賺    5     +3.2% …
```

`marketpulse/baskets.py:112` 有 `BRANCH_COL_WIDTH = 36`；該名稱是 41 個字元；
`marketpulse/product.py:126` 的 `_ljust` 是 `text + " " * max(0, width - _vislen(text))`
——溢出時 padding 為 0，下一欄直接接上去。三個 renderer 共用這個函式。

**交付功能。**寬度不足時截斷並在末尾留一個可見的截斷記號，讓欄位永遠佔滿且不多於
宣告寬度。`_vislen` 的全形／半形計算不變。

**驗收條件**

- H3 — WHEN 任何一格的內容視覺寬度超過該欄宣告寬度
  THEN 輸出中該欄仍恰好佔宣告寬度，且該格結尾出現截斷記號
- H4 — WHEN 執行 `uv run marketpulse brief` 與 `radar`
  THEN 兩者的產物與 `dev` **逐字元相同**（D14；今日無任何一格溢出）
- H5 — WHEN 執行 `uv run marketpulse baskets` THEN 與 `dev` 的差異**只出現在
  `memory_passthrough/nand_price_passthrough` 開頭的那幾行**，且成因是該行第一格
  被截斷（截斷後右側各欄會整體左移，diff 是整行不同，這是預期效果）

**會動到的檔案。**`marketpulse/product.py`（`_ljust`，行 126）、
必要時 `marketpulse/baskets.py`（呼叫端）。

**必須新增的測試。**未溢出時行為不變、恰好等寬時不截斷、溢出時寬度等於宣告值、
全形字在邊界上不被切成半個字。

**本項不做。**不調整任何欄寬常數、不換行、不抽表格層、不碰 `radar.py` 的 HTML 路徑。

### DO-3 — 面板上兩個放錯位置的東西

**背景（可重現的現象）。**同一份面板：

- 斷點清單目前依 `(date, symbol)` 排序（`marketpulse/baskets.py:466`），
  所以 `2449 −14.5%`（07-28）排在 `6669 −66.5%`（09-02）前面。
  **更正：**本節初稿寫「依 `narratives` 的順序列出」，那是錯的——現象對，歸因錯。
- 「這條上游不區辨」接在資料列右側，`nvhbm/hbm4_base_die_tsmc` 那行帶兩個提示，
  整行 **317** 個字元（初稿寫「超過 200」，低估），讀的人先讀到提示才讀到數字。

**交付功能。**斷點清單依 `|return_1|` 由大到小排序；
「這條上游不區辨」的提示從資料列移到該支線區塊底下，與斷點清單同一區。

**驗收條件**

- H6 — WHEN 一條支線有兩筆以上斷點 THEN 清單第一行是 `|return_1|` 最大的那一筆
- H7 — WHEN 一條支線有「不區辨」提示 THEN 該提示自成一行，出現在該支線區塊底下，
  且資料列不含該提示的文字
- H8（目視）— WHEN 一條支線同時有三行數字、斷點清單與「不區辨」提示
  THEN 那三行數字仍讀成一個整體，提示與清單不會被讀成第四個籃子。
  **目視驗證，貼原文，不得以測試通過為證據；測試名稱不得承載該宣稱。**

**會動到的檔案。**`marketpulse/baskets.py`。

**必須新增的測試。**排序（含同值時保持穩定）、提示不在資料列、提示自成一行、
無提示時不留空行。

**本項不做。**不改提示文字、不改斷點記號、不加門檻、不限制清單筆數。

## 兔子洞

- **`_ljust` 是三個 renderer 共用的**——改它會同時影響 `brief`、`radar`、`baskets`。
  H4 就是為此存在；先跑 H4 再往下做。
- **全形字截斷**：`_vislen` 用 2 欄計算全形，截斷點落在全形字中間時不得產生半個字。
- **`015-spec.md` 被 A6 判超標是真陽性，但上限是 015 之後才立的。**
  H1 照跑，evidence 裡註明一句就好，不要回頭改 015-spec。

## 本輪明確不做

- **掛 `Stop` hook** —— 前提決定 1，等腳本證明判準不誤殺
- **抽共用表格層** —— 前提決定 3
- **重跑 `scripts/price_break_recovery.py` 改成三組** —— 那是已經花掉的買資訊，
  結論（`6669` 回不去）不因分組改變。真正要防的是「把量出來的數字寫進驗收條件」，
  而 2026-09-09 的實測顯示**開工前自檢就抓得到**（它命中了 `273`），不需要腳本
- **`US:` 前綴與「不可計價」顯示** —— 押後
- **改 `radar.py` 的 HTML 產物** —— D14 本輪不推翻

## 這裡容易踩到的契約紅線

- **D14：**`brief` 與 `radar` 產物逐字元不變。H4 是它的驗收。
- **R1／D10：**本輪不新增任何數字、門檻或分數。截斷記號是常數，不由資料算出。
- **§8：**不碰價格。

## 權限邊界

可碰：`marketpulse/product.py`、`marketpulse/baskets.py`、`tests/`、`scripts/`。
不可碰：`calc.py`、`quality.py`、`narratives.py`、`radar.py`、`themes/v1.yaml`、
`narratives/`、`data/`、`.claude/`。
**不要 merge。**PO 決定。

## 回報時必須附的物證 → `docs/sprints/016-evidence.md`

- 每項 DO 的 commit hash
- `uv run pytest` 的實際摘要行
- `git diff dev --stat`
- H1／H2：腳本在 `015-spec.md` 與 `016-spec.md` 上的實際輸出與退出碼
- H4：`brief` 與 `radar` 前後的 `diff`（應為空）
- H5：`baskets` 前後的 `diff`（應只有 `memory_passthrough/...` 開頭那幾行）
- H6／H7／H8：`uv run marketpulse baskets` 的輸出全文

## 留給實作者的未決問題

1. 截斷記號用什麼字元？規劃端傾向 `…`（單一字元、視覺寬度 1、面板現有輸出不含它）。
   若與 `_vislen` 的全形判定衝突，換一個並在回報裡說明。
