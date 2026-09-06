# Sprint 009 — 讓門面的數字不再自相矛盾

狀態：已完成 2026-09-06
契約：CLAUDE.md 與 docs/coding-contract.md 全數適用
層次：第一層（正確性）＋ 第二層（使用）＋ 一格工程
起因：`docs/sprints/008-report.md` 的 **B6**（品質行把兩個不同統計量並排）、
F7 末段（週末寫的 narrative 完全不可見）、F4／F5／F6。
**階段 1／2 跳過**：範圍由 008 驗收決定，且三項都不需要外部方法。

## Appetite

- 模組：`marketpulse/quality.py`、`narratives.py`、`product.py`、`radar.py`、`cli.py` 與對應測試。不新增模組檔。
- 相依：**不新增任何套件。**gazetteer（`pyahocorasick` ＋ 凍結 ISIN 表）**排到 010**——
  它同時是新相依、新資料、第二層寫入端，與本輪 DO-1 的第一層正確性混在一輪會爆掉
  Appetite，也違反「同一輪不要既換資料又換方法」。
- 資料：**不重算任何第一層數字**、不回補、不改 `themes/v1.yaml`、不改 narrative schema。
- 層：DO-1 動第一層的**顯示**（非計算），DO-2 動第二層顯示，DO-3 工程。
- 超出即為下一輪：gazetteer、`narrate add`、改主題成分、momentum 標籤、重算 baseline。

## 目標

讓 brief 第二行說的話是真的。

## 規則質疑（本輪這一條）

```text
條文：新功能關掉之後，產物與基準逐字元相同
起因：004 DO-2 → 007 驗收條件 2 → 008 DO-1 驗收條件 5 → 008 addendum A 條件 1
物證：008-report 第七節第 4 點。同一句型在 008 一輪內造成三次互斥：
      (a) B1——「逐字元相同」與「區塊不省略」不可能同時成立
      (b) F4——「分隔線改成從表頭算」，但表頭不是最寬的列
      (c) addendum A 條件 1——要求 radar ASCII 與 dev 相同，
          而 F3 就是同一輪故意改掉那條分隔線的
詮釋：它是有效的回歸護欄，問題不在它存在，在於它每次都被寫成
      「**全部**輸出／三份產物」，而同一輪往往有另一個 DO 故意改動產物。
      規劃端連寫三次同樣的錯，這不是手誤，是句型本身在誘導。
決定：保留為預設值，但**收窄**——寫這類條件時必須指名
      「哪一份產物、對哪一個 commit、在哪一個開關狀態」，
      禁止寫成「全部輸出」；且寫完要逐條對照本輪其他 DO 檢查互斥。
重看：009 驗收後
```

## PO 的前提決定

1. **B6 走「改印樣本平均值」**（2026-09-06 拍板）。否決：兩個數字分開顯示
   （品質行已被嫌看不懂，再加一格更糟）、保留現狀只改註解
   （要求讀者記住註解才不誤讀，且 D10 要求文案固定）。
   **若改選別條，DO-1 整項重寫，DO-2／3 不受影響。**
2. 008 已由 PO 併入 `dev@2d92270`（索引 `dd6405f`）。009 自 `dev` 當前尾端開分支。
3. **不重算 baseline。**`signal_quality_null.json` 的內容一個字都不動；本輪只改怎麼讀它。

## 要做的

### DO-1 — 品質行改印樣本平均值　[L1・交付]

**背景。**008-report B6。真實 brief 第二行目前是：

```text
持續性 -.05† 虛無 .06±.03 +2.8σ 0/1000
```

`-.05` 是 `market_daily.parquet` 的**單日** `rank_persistence_20`（T=2026-09-04）；
`.06±.03 / +2.8σ / 0/1000` 描述的是 `signal_quality_null.json` 裡 k=20 的
**367 天平均值**（`observed=0.1404`，`quality.py:206`：「mean over T of corr(...)」）。
畫面因此在說「-.05 比虛無高出 +2.8σ」——量不對、尺規不對、正負號也不對。
單日值一直在跳（`.11` → `-.05`），σ 永遠釘在 `+2.8`；今天第一次翻負才看得出來。

**做什麼。**

- `quality_line()` 的持續性那一格，改印 **baseline entry 自己的 `observed`**，
  與同一行的 `null_mean` / `null_std` / `sigma` / `n_ge_observed` 出自**同一筆 entry**。
- 單日 `rank_persistence_20` **從這一行拿掉**。它仍在 `market_daily.parquet` 裡，
  要用的人查得到。**本輪不另外找地方放它**——那是新功能，不是修正。
- `†`（`STALE_MARKER`）保留，但語意隨之改變：它現在表示
  「這一整組數字量到 `sample_end` 為止，與 `as_of` 不同日」。**文案固定（D10）。**

**驗收條件。**

1. 真實 brief（`as_of` = 目前最新價量日）的品質行，持續性數字與同一行的 σ **來自同一筆 entry**。
   貼修改前後兩份實際輸出。
2. **可測的不變式**：加一個測試，斷言品質行印出的持續性數字 == 該 entry 的 `observed`。
   **正負號矛盾在結構上不再可能發生**，不是靠人看。
3. 無 baseline（`entry is None`）時的行為見未決問題 1——**先量現況會不會踩到，再問。**
4. 除了持續性那一格與 `†` 的語意，品質行其餘部分（換手、離散、`HORIZON_FOOTNOTE`）
   **一字不改**。
5. **不重算、不改寫 `signal_quality_null.json`**；`persistence_null_test`、
   `compute_market_quality`、`_rank_persistence_series` 一行不動。

**會動到的檔案。**`marketpulse/quality.py`（只有 `quality_line`）、對應測試。

**本項不做。**不重算 baseline、不改任何第一層計算、不把單日值搬到別處、
不改 rank-ic 表格的呈現、不動 `‡`。

### DO-2 — 尚未生效的 narrative 要看得見它存在　[L2・使用]

**背景。**008-report F7 末段：`narratives/` 的 09-04／09-06 兩份檔，在
`as_of=2026-09-03` 時被 PIT 全部濾掉，畫面上**沒有任何跡象**顯示它們存在。
使用者週末寫完 narrative，要等下一個交易日的價量落地才看得到反應——
而 007 診斷出來的核心問題正是「寫完之後日常畫面沒有任何變化」。
**PIT 沒有錯，錯在沉默。**

**做什麼。**brief 新增一行，標題字面鎖定 **`尚未生效`**：

- 列出 `narratives/` 裡 `snapshot_date > as_of` 的快照檔：`snapshot_date · 檔名`，最多 3 行。
- 附一句固定文案說明為什麼：`（快照日期晚於最新價量日 <as_of>，依 PIT 規則尚未納入）`。
- 無此類檔案時印 `（無）`，**區塊不省略**。
- gate 與 008 addendum A 相同：`narratives/` 有檔才顯示這個區塊。

**這是純告知。絕對不得影響任何計算。**

**驗收條件。**

1. 真實資料上（`as_of` = 最新價量日），`尚未生效` 列出所有 `snapshot_date > as_of` 的檔。
   貼實際輸出。
2. **PIT 不變**：`load_as_of`、`coverage_report`、`theme_mention_dates`、
   `theme_last_mention_dates`、`story_last_changed` 的行為與 `dev` **完全相同**。
   加一個測試：有未生效快照存在時，覆蓋判定的結果與沒有它們時**逐字元相同**。
3. 目錄無檔時本區塊不出現，brief 與 `dev` 逐字元相同。
4. 不寫任何檔（沿用既有 mtime／bytes 斷言手法）。

**會動到的檔案。**`narratives.py`、`product.py`、對應測試。

**本項不做。**不改 PIT 規則、不讓未生效的快照參與任何判定、不預告它「會變成什麼」、
不做倒數、不改 `到期重看`。

### DO-3 — 008 留下的三個小洞　[ENG]

1. **F4 `敘事` 欄沒有欄寬。**它是全表唯一沒有欄寬的欄（其他都有 `{'RS20':>7}` 之類），
   所以表格右緣參差：表頭顯示寬 110、`—` 列 107、日期列 116。
   **給該欄固定欄寬（10 ＝ ISO 日期寬），分隔線隨之對齊。**
   `--no-narratives` 的 `100` 是 `dev` 既有值，**不要動**。
2. **F5 `declared` 是「宣稱」不是「已驗證」。**`coverage_report()` 只要 `theme_ids`
   非空就回 `declared`，不檢查那些 id 存不存在；而 `_mentioned_theme_ids()` 會把
   不存在的 id 全丟掉。一則 `theme_ids` 全打錯字的 narrative，兩個函式給出相反答案。
   **修法自行判斷**（例如全部 id 都無效時不回 `declared`），但不得改動既有四態的邏輯。
3. **F6 成員資格測試有兩份實作。**007-spec 明令「不要自己重寫一套主題↔標的比對」，
   008-spec 漏了重申，於是 `coverage_report()` 與 `_mentioned_theme_ids()` 各實作了一次
   `named & members`。**讓其中一個建立在另一個之上**，只留一份真相。
   兩者的對外行為（回傳值）**不得改變**。

**驗收條件。**三項各有 diff；`uv run pytest` 全綠；
第 1 項貼表頭＋分隔線＋一列 `—`＋一列日期的實際字串，四者右緣對齊；
第 3 項要有測試證明兩個函式對同一則 narrative 的判定一致。

## 兔子洞

- **DO-1 不要順手「順便讓數字更好懂」。**本輪只做「印的東西與旁邊的尺規是同一個統計量」。
  重寫整個品質行在 backlog，不是本輪。
- **DO-2 最容易滑成預告。**「尚未生效」只講事實（有幾份、日期多少、為什麼還沒進來），
  **不得**講「它生效之後會怎樣」——那需要先算，一算就破 PIT。
- **DO-3.2 不要為了修 F5 去動四態邏輯。**四態是 004→008 一路守住的東西。
- **DO-3.3 合併兩份實作時，先確認兩者現在的回傳值真的一致**再合併；
  若發現不一致，那是一個 bug，回報，不要靜靜挑一邊。

## 本輪明確不做

- **gazetteer（`pyahocorasick` ＋ 凍結 ISIN 名稱↔代號表）→ 010。**理由見 Appetite。
- `narrate add` 互動指令、速記檔入口 → 010
- 品質行整體重寫、momentum 標籤重做 → backlog（007／008 已附物證）
- 重算 `signal_quality_null.json`、換 primary、composite、Elo、RRG、
  as-of 成分、雙池、burst、PTT

## 這裡容易踩到的契約紅線

- **R3**：DO-2 的 `尚未生效` 是純告知，不得參與任何判定。
- **不做綜合評分**：DO-1 只是換印哪一個既有數字，不新增任何計算。
- **不用未來資料**：DO-2 顯示的是「有一份晚於 as_of 的檔存在」這個**檔案系統事實**，
  **不得讀取其內容**做任何判斷——只讀 `snapshot_date` 與檔名。
- **D10**：所有新文案固定，不依數字改寫。

## 權限邊界

- 分支：`sprint/009-<slug>`，自 `dev` 當前尾端。
- 可碰：上列模組、`tests/`、`docs/sprints/009-*`、`docs/product/backlog.md`。
- 不可碰：`themes/v1.yaml`、`signal_quality_null.json`、narrative schema、
  `persistence_null_test`、`compute_market_quality`、`_rank_persistence_series`、
  `compute_rank_ic`／`rank_ic_null_test`、`show_narratives=False` 的輸出。
- **不 merge**——完成後回報，由 PO 決定；merge 由實作端在 PO 指示下執行。
- 分支切換請在 Mac 上做。

## 回報時必須附的物證 → `docs/sprints/009-evidence.md`

- 每項 DO 的全長 commit hash
- `uv run pytest` 的實際摘要行（不是「全部通過」）
- `git diff dev --stat`
- **DO-1 最重要的一張**：真實 brief 品質行，修改前 vs 後的原文兩行
- DO-1：驗收條件 2 那個不變式測試的名稱與實際輸出
- **DO-2 最重要的一張**：真實 `尚未生效` 區塊原文，以及驗收條件 2
  「有無未生效快照，覆蓋判定逐字元相同」的比對輸出
- DO-3：三項各自 diff；第 1 項的四行對齊實際字串；第 3 項一致性測試的輸出
- **完成後跑一次完整 `uv run marketpulse refresh`（cwd = repo 根目錄），
  確認 `reports/radar.html` 有重新生成**（008 B5 的教訓：改動產物格式的輪次，
  要確認產物本身重生成過，不是只確認渲染函式正確）

## 留給實作者的未決問題

1. **沒有 baseline（`entry is None`）時，持續性那格印什麼？**
   預設：印 `n/a`。理由：退回印單日值等於把剛修掉的誤導放回去，只是少了旁邊的 σ。
   但若現況根本不會發生（`signal_quality_null.json` 一直都在），這題是空的——
   **先量現在與可預見的操作流程會不會踩到，再回報。**
2. **DO-2 的 `尚未生效` 放哪？**預設：`故事進度` 之前、`分類外代號` 之後。
3. **F5 的修法**：全部 `theme_ids` 都無效時該回哪一態？預設：退回走 `named_symbols`
   的四態邏輯（等同該欄位不存在），因為「宣稱了但宣稱的東西不存在」在資訊上等於沒宣稱。
   **未知 id 的訊息仍照 008 的方式顯示，不得因此消失。**
