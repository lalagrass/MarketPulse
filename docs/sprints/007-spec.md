# Sprint 007 — 讓寫下來的故事出現在每天看的地方

狀態：已完成 2026-09-06（`sprint/007-narrative-loop`，未併）
契約：CLAUDE.md 與 docs/coding-contract.md 全數適用
層次：第二層（故事）＋ 顯示 ＋ 一格工程
起因：階段 1 三個彼此看不到的角色收斂到同一件事；`docs/sprints/006-review.md` 的殘留

**階段 2 研究本輪縮短。**理由：範圍由階段 1 的收斂決定，且 Q9 已結案（市場故事追蹤沒有可直接套用的開源）。本輪三項都不需要外部方法。

## Appetite

- 模組：`marketpulse/narratives.py`、`product.py`、`radar.py`、`cli.py` 與對應測試。不新增模組檔。
- 相依：**不新增任何套件。**
- 資料：不回補、不改 `themes/v1.yaml`、**不改 narrative schema**（004 的 schema 原封不動）。
- 層：只動第二層的**讀取端**與顯示。**第一層的數字一個都不改**——rank、RS、breadth、volume、momentum 標籤、品質行的數字全部不動。
- 超出即為下一輪：`narrate` 互動指令、momentum 標籤重做、品質行重寫、burst／PTT、換 primary。

## 目標

讓「寫了一則故事」這件事，在使用者每天已經在看的畫面上產生看得見的效果。

## PO 的前提決定

1. **「brief／radar 產物逐字元不變」2026-09-06 由規則降級為預設值。**規則帳寫進 `non-goals.md`：

   ```text
   條文：brief／radar 產物逐字元不變
   起因：004 DO-2，用來防止第二層污染第一層（R3）
   詮釋：不可污染原則的原文是「故事不能回頭改變第一層的數字」，
         從未說故事不能印在數字旁邊。兩件事被壓成同一條。
   決定：降級為預設值——允許只讀的敘事欄位進顯示層；
         不可污染原則本身不變　　重看：007 驗收後
   ```

2. 005／006 已併入 `dev@fe935d1`。IC 讀法維持 B＋C，不換 primary。
3. narrative schema 不動，本輪只做讀取端。
4. **寫入摩擦本輪不碰**（`narrate add`、速記檔）。先確認回饋迴路有效，再降寫入摩擦——反過來做的話，摩擦降了但寫完還是沒反應，等於白做。

## 要做的

### DO-1 — 敘事覆蓋進 brief 與 radar　[L2・交付]

**背景。**`narratives/` 只有兩個檔，最後一次寫入 2026-09-05，之後兩輪沒再寫過。階段 1 的診斷：擋住第二層的不是 YAML 難寫，是**寫完之後日常畫面沒有任何變化**——覆蓋狀態只在要主動下指令才看得到的獨立面板裡。

**做什麼。**

- **radar 主表新增一欄「敘事」**：該主題最近一次被 narrative 提及的日期（`YYYY-MM-DD`），沒有則 `—`。純文字，**不著色、不參與排序、不進任何運算**。
- **brief 在主表之後新增兩張清單**，各最多 5 行，標題字面鎖定：
  - `強但沒人講` — rank ≤ 3 且無任何 narrative 覆蓋
  - `有人講但弱` — 有 narrative 覆蓋且 `rank >= ceil(n_themes / 2)`
  - 每行只有主題名與 rank。**兩張清單不合併、不排成一張、不加箭頭或顏色、不給覆蓋率分數。**
  - 沒有符合的印 `（無）`，**不要省略整個區塊**——區塊消失會讓人以為功能壞了。
- **PIT。**narrative 快照取 `snapshot_date <= as_of` 的最新一份。覆蓋判定用既有的 `coverage_report()`，不要自己重寫一套主題↔標的比對。

**驗收條件。**

1. `brief` 與 `radar` 各出現一次上述區塊／欄位，文案為本 spec 所寫的固定字串。
2. **第一層逐字元不變**：關掉新欄位／新區塊之後的輸出，與 `dev@fe935d1` 的輸出逐字元相同。evidence 要寫清楚這個比對是怎麼做的。
3. 沒有 narrative 檔時：敘事欄全 `—`、`強但沒人講` 是全部前三名、`有人講但弱` 印 `（無）`，**不 raise**。
4. narrative YAML 壞掉時：印一行明確訊息，第一層照常輸出，**不整份炸掉**。
5. 測試涵蓋 covered／uncovered、rank 邊界（rank=3 與 rank=4）、無檔案、壞檔案。

**會動到的檔案。**`marketpulse/narratives.py`、`product.py`、`radar.py`、對應測試。

**本項不做。**不做覆蓋率分數、不著色、不把敘事欄位寫進 `theme_daily.parquet`、不依敘事改變任何排序。

### DO-2 — revisit 到期主動出現　[L2・使用]

**背景。**004 把 `revisit` 設成必填、缺了就 raise，但**沒有任何東西會在到期時提醒**。必填欄位沒有讀取端，等於一個永遠不會響的鬧鐘。

**做什麼。**`refresh` 與 `brief` 結尾各印一段，標題字面鎖定 `到期重看`：

- 可解析為日期且 `<= as_of` 的：每行 `narrative_id · branch_id · revisit 日期 · claim 前 30 字`。
- revisit 是文字條件（例如「Broadcom 下一次財報電話會議」）的另列一段 `條件型（無法判斷是否到期）`，只列 id 與原文。**不猜、不解析自然語言。**
- 無到期項時印 `（無）`。

**不寫檔、不改 narrative、不自動改 `stage`。**

**驗收條件。**

1. 兩個固定標題字串在輸出中出現；日期型與條件型各有測試。
2. 無到期項時印 `（無）`。
3. **不寫任何檔案**：測試斷言 `narratives/` 下所有檔的 mtime 與內容不變。
4. DO-2 的測試不走 `refresh` 的真實路徑（會打官網）。

**會動到的檔案。**`marketpulse/narratives.py`、`product.py`、`cli.py`、對應測試。

**本項不做。**不做系統通知、不排程、不自動改 stage、不做「條件型」的自然語言判斷。

### DO-3 — 文件矛盾與 backlog 掃除　[ENG]

1. **`docs/design-v0.2.md` §16（約 640–663 行）**RRG 段落加 `[SUPERSEDED 2026-09-04 → non-goals.md D3]` 標頭，內文保留當歷史。它現在還寫著「RRG is optional，整合方便就做」，而 `non-goals.md` D3 早已寫死不做、`coding-contract.md:260` 也跟著改了——**只有它沒改，而 CLAUDE.md 把它列為 source-of-truth 第一順位。**
2. **`docs/product/non-goals.md:56-57`（D2 附註）**寫「前瞻報酬分布不做，留給使用者判讀」，而 005／006 做的正是那個東西。補一句說明為什麼 `rank-ic` 不牴觸 D2（買資訊的診斷、不進產品、不改 rank），**或**改寫 D2。**擇一，不要兩個版本並存。**
3. **backlog 刪三項**（刪不是重排）：`above_count` 待排殘留（已完工）、脈絡生命週期狀態機／burst detection、PTT 每日掃描。後兩項都卡在未拍板的前提上，且沒有任何 sprint 排了去解決那些前提。
4. **收緊兩條測試**：`tests/test_rank_ic.py::test_persistent_null_sigma_positive_zero_exceedance`（`passing.iloc[0]`）與 `test_shuffled_null_sigma_within_three`（`.any()`）改成對**所有** passing 列檢查。

**驗收條件。**四項各有對應 diff；`uv run pytest` 仍全綠。**收緊後若有格子不符，回報實際數字，不要調鬆斷言去配合。**

## 兔子洞

- **DO-1 驗收條件 2 是本輪最容易做壞的地方。**「關掉新欄位後逐字元相同」需要一個乾淨的開關（例如渲染參數，預設開、測試時關），**不要用手工 sed 砍欄位去比對**。
- narrative 的 symbols 與主題成分是兩套東西。用既有 `coverage_report()`，不要重寫比對邏輯。
- 別順手改 momentum 標籤或品質行——它們在 backlog，本輪動了會讓驗收條件 2 說不清楚是誰造成的。

## 本輪明確不做

- **momentum 標籤重做**（全同向的日子無資訊；`Rank #1 · Δ5 +1 · 20D +26.5%` 卻標 `⚠️ Weakening`）→ backlog，附階段 1 物證
- **品質行可讀性重寫**（`.11 / .06±.03 / +2.8σ / 0/1000` 之間的關係、`換手 10 (80%)`、`D6` 無對應）→ backlog，附「只看輸出」角色的逐條疑問
- `narrate add` 互動指令、速記檔入口 → 下一輪
- 窮舉取代虛無抽樣、`n_iter` 一名兩義、guard-fail 格的 `n=` 位置 → backlog（006-review A1／A2／小事）
- 換 primary、composite、Elo、RRG、as-of 成分、雙池、burst、PTT

## 這裡容易踩到的契約紅線

- **不可污染原則不變**：第二層不得改變第一層的任何數字。本輪只加只讀顯示。
- **不做綜合評分**：兩張清單並列，不合併、不給覆蓋率分數。
- **不用未來資料**：narrative 快照取 `snapshot_date <= as_of` 的最新一份。
- **D10**：所有新文案固定，不依數字改寫。

## 權限邊界

- 分支：`sprint/007-narrative-loop`，自 `dev@fe935d1`。
- 可碰：上列模組、`tests/`、`docs/sprints/007-*`、`docs/product/backlog.md`、`non-goals.md`、`design-v0.2.md` 的 §16 標頭。
- 不可碰：`themes/v1.yaml`、narrative schema、第一層計算、`persistence_null_test`、`compute_rank_ic`／`rank_ic_null_test`。
- **不 merge。**
- 分支切換請在這台 Mac 上做——規劃端的 VM 不能 checkout（不能 unlink 檔案）。

## 回報時必須附的物證 → `docs/sprints/007-evidence.md`

- 每項 DO 的全長 commit hash
- `uv run pytest` 的實際摘要行
- `git diff dev --stat`
- DO-1：實際 brief 片段（含兩張清單）、radar 那一欄的截取、**驗收條件 2 的比對指令與空 diff**、無檔案與壞檔案兩種輸出
- DO-2：到期／條件型／無項目三種輸出，加上 mtime 不變的斷言名
- DO-3：四項各自的 diff 片段；收緊後兩條測試的實際輸出

## 留給實作者的未決問題

1. radar 新欄位放哪？預設 Momentum 之後、最右。
2. 「弱」的門檻用 `rank >= ceil(n_themes / 2)`（11 個主題即 rank ≥ 6）。若實作時發現這個門檻讓清單永遠滿或永遠空，**先量再回報，不要自己改門檻**。
3. brief 兩張清單放主表前還是後？預設後——放前面會擠掉每天的第一眼。
