# Sprint 010 — 把已經算出來、但沒有送到畫面上的東西接上去

狀態：已完成 2026-09-06（併入 `dev@874302d`）
契約：`CLAUDE.md` 與 `docs/coding-contract.md` 全數適用
層次：**全部是顯示層**。第一層的數字不動一格，第二層的 YAML 不動一個字。

## Appetite

- **可動檔案：**`quality.py`、`product.py`、`radar.py`、`narratives.py`、`cli.py`，加 `tests/`。
- **不新增相依**（研究結論見報告：離散度沒有值得裝的套件；`arch` 要動 compute 層，不是本輪）。
- **不新增資料**：不補 TPEx 那 89 天、不動 `themes/v1.yaml`、不動 as-of 成分。
- **不動 compute 層——本輪唯一的硬邊界：**`theme_daily.parquet` 與
  `market_daily.parquet` 的 schema 與內容前後必須完全相同。三項 DO 全部是
  「讀已經算好的值，換一種講法」。
- **推翻預設值一條：**「預設只動一層」不適用——本輪同時碰第一層診斷顯示與第二層
  判定顯示，但都不進 compute。分層是防止「換了資料又換了方法分不清誰造成的」，
  本輪連方法都沒換。追加超出這個範圍就是 011。

## 目標

**產品現在算得出來的事，讀的人看不出來。**本輪把三個「已經算好、但沒送到畫面上，
或送到了卻讀不懂」的東西接上去，不新增任何計算。

## PO 的前提決定

本輪建立在「使用者卡在讀端不是寫端」這個判斷上。物證：`narratives/2026-09-06.yaml`
是使用者手寫的 EP694 真實摘要（層二有在用），但 `data/raw` 只到 `2026-09-04`，
09-05 週五收盤沒抓——**`refresh` 從週五以後沒跑過**，那份快照卡在「尚未生效」。
故本輪不做 `narrate add`，先修讀端。若 PO 改判摩擦在寫端，DO-1／DO-2 仍成立
（讀端的獨立缺陷），DO-3 要重寫成 `narrate add`。

---

## 要做的

### DO-1　品質行改寫成讀得懂的樣子（交付功能）

**背景。**現行輸出這一行：

```text
持續性 .14† 虛無 .06±.03 +2.8σ 0/1000   換手 12 (90%)   離散 15.8pp (18%)
月尺度：可偵測≠穩定；短端遠強於長端；凍結成分偏高估（D6）。
```

`quality.py:96` 的 `_percentile` 是 `rolling(60).rank(pct=True)`，所以括號裡是
**「今天在近 60 個交易日裡的位置」**。也就是說 `離散 …(18%)` 已經在說「今天族群
之間的差距落在近 60 日的後五分之一，今天的名次差異資訊量偏低」——**那句話從來
沒印出來過。**階段 1「只看輸出」角色（未讀任何文件）第 1 條逐字指出：
「`15.8pp (18%)` 前後兩個數字是同一件事還是兩件事，看不出關係」。

**做什麼。**只改講法，不改數字，不加數字，不加門檻：

1. 每個括號百分位旁邊寫清楚它是「近 60 個交易日的第 N 百分位」，並註明方向。
   **不得出現任何條件式警語或門檻**——「離散低於 20% 才印提醒」是 D10 要擋的
   可調把手，本輪明確不做。
2. `†` 目前無註腳。補一行說明它是「持續性那組數字量到 `sample_end`，不是今天」
   （語意見 `quality.py:504–509` 的 docstring）。
3. `D6` 在畫面上無對應。改成讀者不必查文件也懂的一句；是否保留代號由實作端決定，
   但畫面上不得只剩一個沒有指涉的代號。
4. **`entry is None` 那一支（`quality.py:527–533`）改印「無基準」**，不再印單日
   `rank_persistence_20`——那是 008 B6 剛修掉的誤導的無旁證版本。踩得到的路是
   新 clone／刪 `data/processed/`／bump `NULL_METHOD_VERSION`。（009 未決 1 順延，見拍板 2。）
5. 一行還是多行見拍板 1；PO 未答前照**展開**做。

**驗收條件。**

- A1（可測）：`quality_line` 在 `entry is None` 時輸出不含任何持續性數字，含「無基準」。
- A2（可測）：`market_row` 為 `None` 時仍走原本的 `持續性 n/a   換手 n/a   離散 n/a`
  那一支，不受本輪影響。
- A3（可測）：`compute_market_quality` 與 `_percentile` 與
  `persistence_null_test` 的 `git diff` 為空。`market_daily.parquet` 內容不變。
- A4（**目視驗證，不得以測試通過為證據**）：把改寫後的品質行**原文貼進**
  `docs/sprints/010-evidence.md`，來自一次真實 `uv run marketpulse refresh` 的輸出，
  不是 fixture。旁邊寫一句「這一行現在在說什麼」，交 PO 判讀。
  **測試名稱不得出現「好懂／看得出來／可讀」等字眼。**

**會動到的檔案。**`marketpulse/quality.py`（`quality_line` 與常數）、
`marketpulse/radar.py:556` 那個 `<p class="sub quality">`（多行時需要處理換行）。

**必須新增的測試。**A1、A2、A3 各一。

**本項不做。**不改任何數字的算法、不加新統計量、不加門檻、不加顏色。

---

### DO-2　新鮮度送進 `radar.html`（ENG／使用，本輪的保留格）

**背景。**`cli.py:212 format_ops_status()` 已經算好「上次抓取成功／失敗」與
`caught_up`，但只印在終端機 `refresh` 尾端。`radar.py:504/556` 產生的 `radar.html`
標題只有 `as_of.isoformat()`。今天是 2026-09-06 週日、`as_of` 是 2026-09-04、
週五沒抓——**打開 `radar.html` 的人看不到任何線索說資料落後。**階段 1「只看輸出」
角色第 10 條獨立指出：「週末打開會懷疑是不是系統壞了」。

**做什麼。**把已經算好的新鮮度資訊搬一份進 `radar.html` 標頭區，至少能回答
「資料到哪一天」與「上次抓取成功還是失敗」。**不新增計算**，複用
`format_ops_status` 已有的欄位。

**驗收條件。**

- B1（可測）：`radar.html` 含 `raw last attempt` 對應的日期與 `twse=`／`tpex=` 狀態。
- B2（可測）：`caught_up` 為 `False` 時頁面上出現與終端機同一組事實（不必同一句話），
  為 `True` 時不出現誤導的落後字樣。
- B3（可測）：`format_ops_status()` 印在終端機的字串**逐字元不變**。
- B4（**目視驗證**）：貼一張或一段 `radar.html` 標頭區的實際 HTML／文字進 evidence，
  交 PO 判讀「打開來一眼知不知道資料到哪天」。

**會動到的檔案。**`marketpulse/radar.py`、`marketpulse/cli.py`。

**必須新增的測試。**B1、B2、B3 各一。

**本項不做。**不改 `refresh` 的流程、不加自動排程、不加「該跑了」的提醒。

---

### DO-3　把第二層兩處「已經算好但沉默」的地方接上（交付功能）

見拍板 3：PO 可用 `Momentum` 欄寬（009 遺留、畫面上看得到）換掉本項。

**DO-3.1　`強但沒人講` / `有人講但弱` 改用與旁邊那一欄同一個「被講過」定義。**

`cli.py:201` 已經算好 `theme_last_mention_dates(...)`（掃**全部**快照檔）並存進
`NarrativeOverlay.mention_dates`，`radar.py:149–156` 的 `敘事` 欄用的就是它。
但 `product.py:231 _mention_lookup()` **忽略 `overlay.mention_dates`**，改用
`theme_mention_dates(overlay.snapshot, ...)`——只看當前那一份 PIT 快照。
**同一個畫面上有兩個「被講過」的定義。**

做什麼：`_mention_lookup` 改為優先用 `overlay.mention_dates`，缺席時回退到現行
單快照版本（與 `radar.py:149–156` 同一個回退寫法）。

**誠實聲明：今天這一項的可見效果是零。**只有兩份快照時兩種定義取到同一組結果。
差異要到「某主題在較早快照被講過、最新快照沒再提、rank 掉到 `weak_rank_threshold`
以下」才出現——那正是產品自己定義的「太早或講錯」那一格。驗收用**構造 fixture**，
報告要寫明真實輸出今天不變。

**DO-3.2　`尚未生效` 與 `最近事件` 的溢出提示。**`narratives.py:73 PENDING_LIMIT = 3`、
`:78 RECENT_EVENTS_LIMIT = 3` 都靜默截斷；第 4 份未生效快照會再次隱形——**正是
009 DO-2 的立案理由「PIT 沒有錯，錯在沉默」**。兩處各補一行「還有 N 份／N 筆」，
截斷數字本身不動。

**驗收條件。**

- C1（可測）：fixture：主題 X 在較早快照被點名、最新快照未提、`rank` 落在
  `weak_rank_threshold` 以下 → X 出現在 `有人講但弱`。改動前該 fixture 不出現。
- C2（可測）：`overlay.mention_dates` 為 `None` 時輸出與 `dev` 逐字元相同。
- C3（可測）：4 份未生效快照 → 印 3 筆 ＋ 一行「還有 1 份」；恰好 3 份 → 不印那一行。
  `最近事件` 同理。
- C4（可測）：`load_as_of`、`theme_mention_dates`、`theme_last_mention_dates`、
  `weak_rank_threshold`、`out_of_classification_symbols` 五個函式 `git diff` 為空。
- C5：在 evidence 貼出真實 `refresh` 的 2×2 區段，**明確寫出它與 `dev` 相同或不同**。

**會動到的檔案。**`marketpulse/product.py`、`marketpulse/narratives.py`。

**必須新增的測試。**C1、C2、C3、C4。

**本項不做。**不引入「N 天內講過算講過」這種天數門檻（D10：可調把手）。
不動 `STRONG_RANK_MAX = 3`、不動 `weak_rank_threshold`。

---

## 兔子洞

- **多行品質行 × `radar.html`。**`radar.py:556` 把整行塞進一個 `<p>` 並 `html.escape`；
  改多行會牽動 CSS 與既有 `_vislen` 護欄測試（008 F3、009 F4）。撞到就回報，
  不要順手重排整個表頭。
- **`Momentum` 欄寬本輪不碰。**它會改 `--no-narratives` 的表頭，跟本輪的
  「逐字元相同」驗收撞在一起。
- **`data/raw`：本輪一個 byte 都不下載。**
- **真實 `narratives/` 目錄的測試。**009 被咬過一次（完全相等斷言，PO 新增一份快照
  就會紅）。新測試一律用構造 fixture 或包含式斷言。

## 本輪明確不做

- **主題間平均兩兩相關係數當「今日排名低資訊」旗標。**階段 2 研究推翻它：
  Solnik–Roulet (2000) 的 σ_d = σ_m√(1−ρ̄) 說明橫斷面離散度與平均兩兩相關是同一個
  構念的兩面，而**本專案已經在算離散度、也已經印出來了**。缺的不是指標是講法，
  那就是 DO-1。加第二個指標只會再多一個沒人看得懂的數字。
- **`arch` 的 block bootstrap 取代手刻循環位移。**研究確認可行（8.0.0、NCSA、
  維護中），但動 compute 層且新增相依。留 backlog，理由更強了。
- **月頻換手回測 / 損益曲線。**D2，無條件駁回。
- **程式依 `basket` 的 RS20 自動判定 branch `confirmed`/`refuted` 並寫回 YAML。**
  違反 R3：讓第一層回頭改變第二層。無條件駁回。
- **cron / launchd 自動排程。**D7。它暴露的成本是真的（使用者確實沒每天跑），
  但 DO-2 用便宜得多的方式回答同一個痛點。
- **`narrate add` 互動寫入指令。**第三次押後，但理由是實質的：診斷是讀端摩擦。
- **momentum 標籤重做。**證據更強了（報告第 4 節），但它會改變畫面上的判定字串，
  跟本輪的「逐字元相同」驗收衝突。排 011。
- **as-of 成分股（D6／Q5）、TPEx 89 天回補。**動 compute 層或資料層，各自需要一輪。

## 這裡容易踩到的契約紅線

- **R1 無綜合評分**：不得新增任何把多個輸入塌成一個字或一個數的東西。
- **D10 無可調把手**：「低於 X% 就印警語」「N 天內算講過」都是把手，明確不做。
- **R3 第二層不得改變第一層**：DO-3 只改讀哪一份已存在的提及紀錄，不改算法。
- **§9 目視驗收條件不得以測試通過為證據**：A4、B4 是目視項，
  **測試名稱不得承載那個宣稱**（009 DO-3.1 就是這樣失敗的）。

## 權限邊界

分支 `sprint/010-say-what-we-know`，從 `dev` 開（`dev` == `origin/dev` == `c673700`）。
每個 DO 各自 commit。**不要 merge，由 PO 決定。**
可碰 `marketpulse/{quality,product,radar,narratives,cli}.py`、`tests/`、
`docs/sprints/010-evidence.md`；不可碰 `calc.py`、`themes/v1.yaml`、
`narratives/*.yaml`、`data/`、`docs/product/*`。

## 回報時必須附的物證 → 寫進 `docs/sprints/010-evidence.md`

- 每項 DO 的 commit hash；`git diff dev --stat` 的輸出
- `uv run pytest` 的**實際摘要行**（`NNN passed in NN.NNs`），不是「全部通過」
- `compute_market_quality` / `_percentile` / `persistence_null_test` 三個函式
  `git diff dev` 為空的證明；`market_daily.parquet`／`theme_daily.parquet`
  本輪前後的 `rows=`（可行的話加 checksum）
- A1–A3、B1–B3、C1–C4 每條對應的**實際輸出字串或數字**
- A4、B4、C5：一次真實 `uv run marketpulse refresh` 的原文，
  **明確標記這是目視項、由 PO 判讀**

## 留給實作者的未決問題

1. **品質行一行還是多行？**PO 未答前照展開做，evidence 兩種都貼一次讓 PO 挑（拍板 1）。
2. **`radar.html` 的新鮮度放標題列、副標還是獨立一列？**你看得到 CSS 與既有
   `<p class="sub">` 結構，我看不到。**先量再問**：三種都排一次，貼原文，再問。
3. **`format_ops_status` 要不要拆成資料結構？**拆得乾淨且 B3 保得住就拆，
   比複用醜就別拆，回報你的判斷。
