# Sprint 014 — 一則故事三個籃子

狀態：已完成 2026-09-08
契約：`CLAUDE.md` 與 `docs/coding-contract.md` 全數適用
層次：第二層（故事）
分支：`sprint/014-three-baskets`，自 `dev`

## Appetite

- 模組：只動 `marketpulse/narratives.py` 與 `marketpulse/baskets.py`
- 相依：不新增
- 資料：不新增目錄、不新增檔案格式
- 層次：只動第二層。`theme_daily.parquet` 與 `market_daily.parquet`
  前後**逐字元不變**是硬邊界
- 超出以上任何一項就是下一輪

## 目標

一句話：**讓一則故事說得出「誰在對面」與「誰不管怎樣都賺」，並把三者的強弱並排印出來。**

回答主排名回答不了的問題：11 個主題的名次不會告訴你「這條故事的對立面在漲還是在跌」。

## PO 的前提決定

1. **裁判交給價格，不交給分析師。**本輪不做「每則證據標支持／削弱」（`bears_on` 加方向）。
   那需要人先判斷證據對誰有利；三籃只需要人說得出誰在對面。方向欄押後到 015。
2. **不設門檻。**「強」「弱」不由程式判定。面板只按固定順序印三行 ＋ 表頭一次字面鎖定的
   讀法短註。任何 `if rs20 > X` 的分支都是 D10 要擋的把手。
3. **第三籃收 `theme_ids`，不收代號。**11 個主題裡 7 個本質是賣鏟子層；主題成分是凍結的，
   讓第三籃天然穩定。前兩籃收代號。
4. **不動 `narratives/` 的內容。**既有三則的籃子怎麼填是 PO 的判斷。本輪只改解析與顯示。

若 PO 改選別的：推翻 (1) 則 DO-1 的 schema 要重寫；推翻 (2) 則 DO-2 全部重寫；
推翻 (3) 則 DO-1 的 `either_way` 型別要改。

## 要做的

### DO-1 — 支線的籃子從一個變三個

**背景。**`narratives.py:105` 的 `Branch.basket` 是單一 tuple。`narratives/2026-09-06.yaml`
的 `xpu_not_squeezing_gpu` 支線 `basket: []`，因為它想表達的那一群沒有地方放。

**交付功能。**

`branches[].baskets` 收三個鍵：`if_true`（代號）、`if_false`（代號）、
`either_way`（`theme_ids`）。舊的 `branches[].basket:` 繼續解析，讀成 `if_true`。

**驗收條件**

- F1 — WHEN 載入 `narratives/2026-09-04.yaml` 與 `narratives/2026-09-06.yaml`
  THEN 不 raise，且每條支線的成員與本輪之前相同
- F2 — WHEN 一條支線只寫舊的 `basket:` THEN 那些代號出現在 `if_true`，另兩組為空
- F3 — WHEN 在 DO-1 的 commit 上對現有 `narratives/` 執行 `uv run marketpulse baskets`
  THEN 輸出與 `dev` 逐字元相同（DO-2 才改輸出）
- F4 — WHEN `either_way` 寫了不在 `themes/v1.yaml` 的 theme_id
  THEN 那個 id 在畫面上被指名，不被靜默吞掉

**會動到的檔案。**`marketpulse/narratives.py`（`Branch`、`_parse_branch`）、
`marketpulse/baskets.py`（讀 `Branch` 的地方）。

**必須新增的測試。**舊格式向下相容、三鍵各自解析、`either_way` 的未知 theme_id 可見、
三鍵皆空的支線不 raise。

**本項不做。**不動 `named_symbols` / `inferred_symbols`；不動 `stage` / `status`；
不新增 `dir`；不改 `narratives/` 裡任何一個字。

### DO-2 — 面板一條支線印三行

**背景。**`baskets.py:185` 的 `render_basket_panel` 一條支線印一行。
三個籃子之後，讀的人需要同時看到三組數字才能讀出方向。

**交付功能。**

一條 live 支線印三行，**固定順序：`either_way` 在最上，然後 `if_true`、`if_false`**。
每行照現有欄位印 `n / RS5 / RS20 / RS60 / breadth / val%`。
表頭多印一次**字面鎖定**的讀法短註（兩步、n 小的提醒），文字由本 spec 給定、
不得由數字生成。另外印**重疊檔數**，以及當同一組 `theme_ids` 出現在兩則以上故事的
`either_way` 時的「這條上游不區辨」提示。

**驗收條件**

- F5 — WHEN 一條 live 支線三個籃子都有成員
  THEN 面板上這條支線佔三行，順序是 `either_way`、`if_true`、`if_false`
- F6 — WHEN 某一籃沒有成員 THEN 該行仍然出現，印既有的 `無標的`，不消失
- F7 — WHEN `if_true` 與 `if_false` 有共同代號 THEN 面板上看得到共同的檔數
- F8 — WHEN 同一組 `theme_ids` 出現在兩則以上故事的 `either_way`
  THEN 面板上看得到「這條上游不區辨」的提示
- F9 — WHEN 面板被印出 THEN 表頭有讀法短註，且短註文字不隨當日數字改變
- F10（目視）— 三行對齊、欄位右緣一致、一眼看得出三行屬於同一條支線。
  **目視驗證，貼原文，不得以測試通過為證據；測試名稱不得承載該宣稱。**

**會動到的檔案。**`marketpulse/baskets.py`。

**必須新增的測試。**三行順序、空籃仍出現、共同檔數的計算、不區辨提示的觸發、
短註為常數（不含數字）。

**本項不做。**不排名、不排序、不相減、不上色、不算任何新的統計量；
不判定強弱；不碰 `radar.py` 與 `product.py`。

### DO-3 — 回頭日期拆成日期與條件（本輪 ENG／使用保留格）

**背景。**2026-09-08 實測：現有三則 narrative 的 `revisit` **全部**落進
「條件型（無法判斷是否到期）」，`到期重看` 印的是 `（無）`。
`parse_revisit_date` 只吃純 ISO，而真實的回頭時機寫出來就是
「2026-10-15 或 Broadcom 下一次財報電話會議」。004 把 `revisit` 設成必填是為了
防故事爛掉，真實資料上的點火率是 0/3。

**交付功能。**

`revisit` 收純 ISO 日期（必填規則不變），條件文字移到新的 `revisit_note`。
舊檔的自由文字 `revisit` 繼續解析，行為與現在相同（落在條件型）。

**驗收條件**

- F11 — WHEN 一則 narrative 的 `revisit` 是純 ISO 且 ≤ as_of
  THEN 它出現在「到期重看」，不出現在「條件型」
- F12 — WHEN 一則 narrative 同時有 `revisit`（ISO）與 `revisit_note`
  THEN 兩者都出現在該則的那一行
- F13 — WHEN 一則舊檔的 `revisit` 是自由文字
  THEN 行為與本輪之前相同（落在條件型，不 raise）
- F14 — WHEN `revisit` 是空的且快照日期 ≥ `REVISIT_REQUIRED_FROM`
  THEN 仍然 raise（004 的必填不放寬）

**會動到的檔案。**`marketpulse/narratives.py`（`Narrative`、`_parse_narrative`、
`render_revisit_due`）。

**必須新增的測試。**ISO 到期進「到期重看」、ISO 未到期不進、`revisit_note` 一起顯示、
舊自由文字不 raise 且仍落條件型、空 `revisit` 仍 raise。

**本項不做。**不解析自然語言；不自動推算「下一場法說」是哪天；
不改 `REVISIT_REQUIRED_FROM`；不改 `narratives/` 裡的資料。

## 兔子洞

- **`baskets.py` 的欄位寬度。**三行之後版面會變。撞到對齊問題就照 012 DO-1 的做法
  給欄位寬度，不要重寫整個 renderer。
- **`either_way` 是 theme_ids，前兩籃是代號**——`compute_basket_metrics` 現在只吃代號。
  把 theme_id 展開成成員的那一步要走既有的 `ThemeSet`，不要另寫一份成員表。
- **重疊檔數不要往上長成重疊率、相似度或任何比值。**是計數，不是指標。

## 本輪明確不做

- `bears_on` 加方向（`dir`）——押後 015，理由見前提決定 1
- `sources/` 事件層與故事層分家——押後 015，它解的是「讀貼文」
- 故事線時間軸、來源反查——押後 015
- 兩籃相減的價差線——`non-goals` D17
- 共動提名／統計分群決定成員——`non-goals` D18
- 動 `radar.py` 的 `敘事` 欄——本輪只動終端機面板

## 這裡容易踩到的契約紅線

- **R1：**三籃不得合成任何單一數字。沒有總分、沒有價差、沒有比值。
- **R3：**第二層不得回頭改第一層。`baskets.py` 是讀端，不寫 snapshot parquet。
- **D10：**不得出現任何強弱門檻。DO-2 的短註是常數，不是由數字算出來的。
- **D11：**三籃是三個扁平清單加 `theme_ids`，落在 2026-09-05 收窄後的字面之內，
  不需要圖結構。
- **D14：**`brief` 與 `radar` 的產物本輪不得改變。

## 權限邊界

可碰：`marketpulse/narratives.py`、`marketpulse/baskets.py`、`tests/`。
不可碰：`marketpulse/calc.py`、`quality.py`、`radar.py`、`product.py`、
`themes/v1.yaml`、`narratives/`、`data/`。
**不要 merge。**PO 決定。

## 回報時必須附的物證 → `docs/sprints/014-evidence.md`

- 每項 DO 的 commit hash
- `uv run pytest` 的實際摘要行（不是「全部通過」）
- `git diff dev --stat`
- F3：DO-1 commit 上 `uv run marketpulse baskets` 的輸出，與 `dev` 的 diff（應為空）
- F5／F6／F7／F8／F9：`uv run marketpulse baskets` 的實際輸出全文
- F10：同上那份輸出，由 PO 目視判定
- F11–F14：測試用 fixture 的實際輸出字串
- 說明哪幾則現有 narrative 仍落在「條件型」（預期是三則全部，因為本輪不改資料）

## 留給實作者的未決問題

1. `either_way` 的 `theme_ids` 要不要允許同時混代號？**規劃端傾向不要**（混了就會有人
   問怎麼合併），但如果實作時發現某條故事的上游確實不在任何主題裡，回報，不要自己加。

## 附錄 — DO-2 表頭短註的字面（規劃端給定，不得改寫）

```text
怎麼讀：① 先看「誰贏都賺」——這條故事還有沒有人在花錢
        ② 再看「成真」與「反面」的相對位置——市場往哪邊走
        n 小的時候，一籃的強弱就是那一檔的股價。強弱由你自己定，這裡不判。
```

這三行是常數，不含任何當日數字，且不隨資料改變（F9）。
