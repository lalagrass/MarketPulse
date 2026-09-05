# Sprint 004 — 讓一條故事有「還在等什麼」

狀態：待實作
契約：CLAUDE.md 與 docs/coding-contract.md 全數適用
層次：第二層（故事）＋ 一格工程

## Appetite

- 模組：動 `marketpulse/narratives.py`，新增至多一個模組（籃子面板）。**不動 `calc.py` 的排名邏輯**。
- 相依：**不新增任何套件**（burst detection、embedding、Argdown 全部不裝，理由見 open-questions Q9）。
- 資料量：不增加。不新增任何外部資料源。
- 層：只動第二層 ＋ 一項第一層正確性修補（DO-3，它是 DO-2 的前置）。

超出即為下一輪。

## 目標

讓「一條故事」從「某天說過的一段話」變成「一個還在跑、知道自己在等什麼的東西」。

## PO 的前提決定

本輪建立在五個尚未拍板的選擇上。**任一個改選，對應項目要重寫：**

1. ~~**sprint 003 的四條分支先併進 `dev`。**~~ **本項作廢——規劃端寫錯了，2026-09-05 當日更正。**
   寫這份 spec 時只看了 `git rev-list --count dev..<branch>`（顯示各分支領先 31–40 個 commit），
   就推論成果未併。**實際查證後：`git diff dev <branch> -- marketpulse/ tests/` 對四條分支全部為空**
   ——003 的產品碼與測試早就在 `dev` 上（commit `4ea9a02`、`c33ed68`、`d5b53c1`、`eb8f94d`、`12a7573`）。
   那 31–40 個 commit 是**分支自己的歷史**，不是未併的成果。
   分支上唯一與 `dev` 不同的文件是**舊一輪的版本**（還寫著已被 DO-4/DO-5 撤回的
   「百分位 81、與雜訊不可區分」）。**併它們會讓文件倒退。**
   **更正後的前提：`dev` 就是基準，直接從 `dev` 開 004 分支。無前置動作。**
2. **第二層閘門開一半。** 已知第一層正確性問題有兩項：`above_count` 邊界 NaN 塌成 0、
   `calc.py` 無資料空窗檢查。後者本輪修（DO-3），前者不影響 rank，押後。
   改選「閘門不開」→ 本輪只剩 DO-3，DO-1/2 押到下一輪。
3. **籃子只並列、不排名、不進主排名池。** 這繞開 open-questions Q6（雙池）而不是回答它。
   改選「籃子要進排名」→ Q6 必須先拍板，DO-2 全部重寫。
4. **籃子歷史用 as-of 成員（Q5 結論），restated 需明確標註。**
   改選 restated 為預設 → DO-2 的驗收條件 2 反轉。
5. **schema 用「快照內含事件列」而不是事件流。** 全狀態快照仍是權威、仍不原地修改，
   只是每則 narrative 內多一個 `log:` 陣列。改選事件流（append-only + reducer）
   → DO-1 全部重寫，且要正面推翻 D9。

## 要做的

### DO-1 — narrative schema：支線、事件列、成熟度、回頭日期　[L2・交付功能]

**背景。**`narratives/2026-09-04.yaml` 的 `nvhbm` 自己寫了「橫跨既有主題的論點，
不是一個新的成分股籃子——目前 schema 無法完整表達」。而 EP694 的博通段落
（Hock Tan 首度正面點名聯發科）是 `asic_xpu` 的**進度推進**，
`narratives.py:21-22` 只有 `STANCE_NEW` / `STANCE_CONFIRMING` 兩個值，兩個都不是它。
使用者聽完 EP694 沒有寫快照，直接來提改 schema——那就是 schema 擋住了使用。

**做什麼。**`Narrative` 增加四個欄位，既有欄位一個都不刪（舊檔必須照樣讀得起來）：

- `stage`：`open`（論點在、標的未收斂）／`mapped`（標的收斂，追進度）／
  `parked`（講完或沒發酵，等條件重開）。**缺欄位時預設 `open`。**
- `revisit`：**必填**，日期或條件字串。缺這欄位 → loader raise，不是警告。
  （理由：沒有回頭日期的故事會靜靜地爛掉。這條與 skill 對 UNKNOWN 的要求同形。）
- `log`：帶日期的事件列，每則 `{date, source_ref, kind, text, bears_on?}`。
  `kind` ∈ `claim`（新論點）／`evidence`（證據）／`schedule`（提早或遞延）／
  `price`（第一層動了）／`close`（收掉）。`bears_on` 是 branch_id 列表。
- `branches`：支線列表，每則 `{branch_id, claim, basket, watch, status?}`。
  `basket` 是股票代號列表（可空）。`status` ∈ `live`／`weakened`／`dead`，預設 `live`。

`named_symbols` / `inferred_symbols` 的分離**維持不變**（non-goals R3）。
`basket` 的來源是人，與 `inferred_symbols` 同級——不得由程式推論填入。

**loader 新增 `history(narrative_id, as_of)`**：把所有 `snapshot_date ≤ as_of` 的檔案中
同一個 `narrative_id` 的版本按日期串成序列。現行 `load_as_of` 只回傳最新一份、
把歷史丟掉，所以「這條故事被講過幾次、間隔多久、支線何時分岔」目前全都算不出來——
而 backlog 的「敘事提及次數導數」「敘事提及量 × RS20 落後互相關」都靠它。

**驗收條件。**

1. 現行 `narratives/2026-09-04.yaml` **一個字不改**仍能載入，三則 narrative 的
   `stage` 全部是 `open`，`coverage_report()` 的輸出與本輪之前逐字元相同。
   （這條是回歸測試，證明 schema 是加法。）
2. 一份缺 `revisit` 的 YAML 讓 `load_as_of` raise，錯誤訊息含 `narrative_id`。
3. 給兩份快照（`2026-09-04`、`2026-09-06`，後者對 `asic_xpu` 多一則 `log`），
   `history("asic_xpu", as_of=2026-09-05)` 只回傳第一份的版本；`as_of=2026-09-06` 回傳兩份。
4. `bears_on` 指到不存在的 `branch_id` → raise。

**會動到的檔案。**`marketpulse/narratives.py`、`tests/test_narratives.py`、
`narratives/2026-09-06.yaml`（新檔，把 EP694 寫進去當第一個真實樣本）。

**必須新增的測試。**上列四條各一。

**本項不做。**不做圖結構、不做傳遞閉包、不引入 networkx（D11 維持，規則帳見 non-goals D11）。
不做自動從逐字稿抽 narrative。不做 LLM。

### DO-2 — 支線籃子的強弱面板　[L2・買資訊]

**背景。**使用者的原話：「把有興趣的第二層的故事，在第一層也追蹤強弱」。
現在第二層與第一層之間唯一的連結是 `coverage_report()`——它只回答
「這些代號在不在既有 11 主題裡」，不回答強弱。

**做什麼。**新增 CLI 子命令，對 `as_of` 當下每條 `status == live` 的支線籃子輸出一行：
成員數、RS5／RS20／RS60、breadth、value_share。**純文字表格，不畫圖。**

**四條紅線，違反任一條就是本項失敗：**

- **不排名。**不產生 `rank`、不 `cumcount()`、不排序（照 YAML 順序印）。
- **不進主排名池。**不寫進 `theme_daily.parquet`，不進 `themes/v1.yaml`。
- **不合成。**沒有籃子分數、沒有加權（R1）。
- **成員用 as-of。**T 日的籃子成員取 `snapshot_date ≤ T` 中最新那份（Q5 預設讀法）。
  restated 讀法本輪不做。

**驗收條件。**

1. 跑完面板後，`uv run marketpulse brief` 與 `reports/radar.html` 的輸出
   **與跑之前逐字元相同**（`diff` 貼進 evidence）。這是 R3 的可測試版本。
2. 新增一份 `snapshot_date` 較晚、把某支線籃子加一檔股票的 YAML，
   面板對**較早**的 `as_of` 輸出不變。（`tests/test_future_mutation.py` 的同形檢查。）
3. 籃子歷史不足 20 個交易日時 RS20 印 `n/a`，**不補值、不用較短窗口代替**。
4. 空籃子（`basket: []`，例如 `gpu_squeezed`）印一行「無標的」，不是被略過。

**會動到的檔案。**新模組（建議 `marketpulse/baskets.py`）、`marketpulse/cli.py`、對應測試。

**本項不做。**不畫籃子的 timeline、不加進 radar、不做籃子的 momentum 四態標籤。
第一層的顯示一個像素都不動。

### DO-3 — `calc.py` 的資料空窗檢查　[ENG]

**背景。**backlog 2026-09-05 回補驗收記錄：rolling window 跨 session 不跨日曆，
資料若不連續，60 日窗會直接跨過空窗算出假數字，**完全無警告**。
上次靠實作端目視發現並手動刪檔。

**為什麼在這一輪。**它是 DO-2 的前置——籃子若用同一套 rolling 計算，
空窗就會同樣靜默地產出假的籃子強弱，而籃子的資料窗比主題更短更容易破碎。

**做什麼。**`calc.py` 在計算 rolling 之前檢查日期序列的連續性，
發現超過門檻的空窗時 raise（不是印警告、不是回 NaN）。
門檻用交易日曆或「連續 N 個日曆日無資料」都可以，實作端決定並在 evidence 說明選了哪個、為什麼。

**驗收條件。**

1. 造一份中間挖掉三十個交易日的資料，`analyze` raise，訊息含空窗的起訖日期。
2. 現有本機真實資料跑 `analyze` 行為不變（不得誤報）——貼 `brief` 的前後 diff。

**本項不做。**不修 `above_count` 的邊界 NaN（押後，它不影響 rank）。不加 lint／CI。

## 兔子洞

- **`themes/v1.yaml` 與籃子的重疊。**`asic_xpu` 的籃子會跟既有主題大量重疊。
  不要試圖去重、不要算「剝除重疊後的貢獻」——那是 backlog 裡的另一項，撞到就回報。
- **資料窗只有 141 個交易日。**新故事的籃子幾乎必然 RS60 全是 `n/a`。那是正確行為，
  不要為了讓面板好看去回補資料——回補綁著 D6，是另一輪的事。
- **想幫使用者「自動」從逐字稿抽 narrative。**不要。本輪逐字稿只由人讀。
- **想給籃子一個「熱度」數字。**Kleinberg burst detection 有 `s` 與 `gamma` 兩個可調參數，
  是 D10 要擋的把手；且 `nmarinsek/burst_detection` 授權為 non-commercial。本輪不碰。

## 本輪明確不做

| 砍掉的 | 理由 |
|---|---|
| 籃子進排名池 / 雙池 | Q6 未拍板。並列顯示已回答使用者九成需求，排名可以等 |
| 圖結構表達上下游 | D11 維持。撞到的是「缺多對多欄位」不是「缺圖」，YAML list 就夠 |
| PTT / 論壇每日掃描 | 撞 D7（排程）。且討論量的量測陷阱未解，見 backlog |
| burst detection | 授權 non-commercial（nmarinsek）或未維護（pybursts）；且參數是 D10 的把手 |
| narrative-maps / embedding 抽故事線 | 一週一集 podcast，樣本量不支持自動抽取。新增相依 |
| 每週自填「下週誰會強」＋ Brier 計分 | 方向對，但要先有 DO-1 的紀錄累積才有東西可計分 |
| restated 籃子讀法 | as-of 先用著；restated 需要標註設計，等真的有人要問「如果一開始就這樣定義」 |

## 這裡容易踩到的契約紅線

- **R3**：籃子決定「量哪一組股票」，不得改變「怎麼量」。DO-2 驗收條件 1 就是這條的測試。
- **R1**：籃子不得有分數。並列印出，不合成。
- **R2 / §7 PIT**：`log` 的 `date` 與快照的 `snapshot_date` 是兩回事。
  `first_noted > as_of` 的過濾（`narratives.py:98`）必須同樣套用到 `log` 條目與 `branches`。
- **D9**：`log`／`branches` 是欄位，不是框架。不要為它建 registry、reducer 或 event bus。

## 權限邊界

- 分支：從 `dev` 開 `sprint/004-narrative-shape`（前提決定 1 成立時）。
- 可碰：`marketpulse/narratives.py`、新的籃子模組、`marketpulse/cli.py`、`marketpulse/calc.py`（僅 DO-3）、`tests/`、`narratives/`。
- 不可碰：`themes/v1.yaml`、`calc.py` 的排名邏輯、`product.py`／`radar.py` 的版面、`quality.py`。
- **Never merge。**（CLAUDE.md 通則，本輪不例外。）

## 回報時必須附的物證 → 寫進 `docs/sprints/004-evidence.md`

- 每項 DO 的 commit hash
- `uv run pytest` 的實際摘要行（不是「全部通過」）
- `git diff dev --stat` 的輸出
- DO-2 驗收條件 1 的 `diff` 實際輸出（必須是 `IDENTICAL` 或空）
- DO-3 驗收條件 1 的實際錯誤訊息字串
- `narratives/2026-09-06.yaml` 的實際內容（EP694 寫成的第一個真實樣本）

## 留給實作者的未決問題

1. DO-3 的空窗門檻要用交易日曆還是「連續 N 個日曆日」？**能自己量的先量**——
   看現有 `data/` 的日期序列實際長什麼樣，再決定，並在 evidence 說明。
2. `history()` 回傳什麼型別？（版本序列？還是差異序列？）實作端看得到型別成本，自己決定，但要在 docstring 寫明。
3. 籃子面板的 `value_share` 分母是什麼？主題的 value_share 分母是全市場；籃子若沿用同一個分母，
   數字可以直接跟主題比。**傾向沿用**，但若實作上發現不成立，回報不要硬幹。
