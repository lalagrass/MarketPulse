# Sprint 001 — 讓第一層可信，替第二層打地基

狀態：已完成 2026-09-04
契約：CLAUDE.md 與 docs/coding-contract.md 全數適用（注意 §3、§11 已於 2026-09-04 修訂）
層次：DO-1、DO-2 為第一層（數學）；DO-3 為第二層（故事）的資料結構，本輪不做任何量測

## 目標

讓使用者打開雷達時，能先知道「今天這張排名值不值得看」；並用不帶前視偏誤的方式，
開始累積脈絡記錄。

## 要做的

### DO-1　修正 breadth 把短歷史成分股算成「跌破 SMA20」

**做什麼**
`marketpulse/calc.py:163` 目前是 `above = close > ma`。pandas 中 NaN 的比較回傳
`False` 而非 NaN，所以缺收盤價或尚無 SMA20 的成分股會被計為「未站上均線」，
後面的 `above[cols].mean(skipna=True)` 沒有 NaN 可跳過。改為先遮罩：

```python
above = (close > ma).where(close.notna() & ma.notna())
```

`breadth` 與 `above_count` 都應只計入「有收盤價且已有 SMA20」的成分股。

**驗收條件**
1. 一個三成員的主題，其中一員只有 10 天歷史（SMA20 為 NaN）：`breadth` 的分母為 2 而非 3。
2. 同上情境，`above_count` 不把該成員計為 0/未站上，而是完全排除。
3. 全員皆有完整歷史時，`breadth` 數值與修改前完全相同（既有 `tests/test_breadth.py` 必須原封不動通過）。

**會動到的檔案**：`marketpulse/calc.py`

**必須新增的測試**：`tests/test_breadth.py` 增一個案例，成員中含一支歷史不足 20 天者，
斷言 breadth 為「合格成員中站上均線的比例」。

**本項不做**：不改 `status` 的語意。目前 `member_count` 只檢查收盤價存在與否，
不檢查是否滿 20 天，因此這類主題仍會標為 `OK`。是否要新增狀態值是產品決定，
留給下一輪。

---

### DO-2　訊號品質三數（每日，市場層級）

回答「今天這張排名值不值得看」。三個各自獨立的描述統計，**不得合併成單一分數**。

**做什麼**
新增 `marketpulse/quality.py`，對既有 `theme_daily` 快照計算下列三個每日數值：

1. `rank_persistence_k`（k = 1, 5, 20）
   T 日的 11 檔名次向量與 T−k 日名次向量的 Spearman 相關係數。
   用 pandas 內建 `Series.corr(method="spearman")`，**不新增任何相依套件**。
   接近 +1 = 排名穩定；接近 0 = 每天重洗。

2. `rank_churn`
   `sum(|rank(T) − rank(T−1)|)` 跨 11 個主題。
   **同時輸出它在自身過去 60 個交易日分布中的百分位**。

3. `dispersion`
   RS20 排名前半主題的平均 RS20，減去後半主題的平均 RS20。
   （Morgan Stanley Counterpoint Global 的 top-half-minus-bottom-half 定義。）
   數值大 = 主題之間真的有差別；數值小 = 排名在區分雜訊。
   **同時輸出它在自身過去 60 個交易日分布中的百分位**，與 `rank_churn` 共用同一個
   helper。理由：8.4pp 是寬還是窄，沒有基準的人看不出來；而 `rank_persistence`
   是有界的（−1 到 1，1 = 順序未變、0 = 等同重洗），本身就會講話，不需要百分位。

輸出寫入 `data/snapshots/market_daily.parquet`，並在 Daily Brief 表頭與 radar 表頭各顯示一行。

**驗收條件**
1. 給定一組手工 fixture（11 個主題、連續 25 個交易日、名次已知），三個數值皆可與
   手算結果比對相符。
2. 排名完全不變的兩日，`rank_persistence_1 == 1.0` 且 `rank_churn == 0`。
3. 排名完全顛倒的兩日，`rank_persistence_1 == -1.0`。
4. 歷史不足 60 日時，`rank_churn` 的百分位欄位為 NaN 而非以較短窗口填充。
5. **顯示的是原始數值與百分位，不是任何「今天可不可信」的布林旗標。**（見紅線 3）
6. **理解驗收（非像素驗收）：**打開 `reports/radar.html`，**兩秒內**能判斷今天這張排名
   值不值得細看。這條沒有自動化測試——實作完請自己開起來看一次，並在交回時
   說明你怎麼安排這三個數字、以及為什麼那個安排能在兩秒內被讀懂。
   如果做不到兩秒，**回報做不到**，不要調整措辭讓它聽起來像做到了。

   **版面由實作者決定**（位置、順序、留白都可以是答案），但下列三條會被打回票：
   - **順序**：這行回答「我要不要繼續讀」，必須在主題列表**之前**。放在底部
     等於讀完排名才知道能不能信。
   - **份量**：位置優先但視覺次要。排名才是標題，這行是閘門——小、安靜、在上面，
     不是一條大橫幅。
   - **不得有結論**：只給數字與百分位，不准出現「今天不用看」這類判定字樣（D10）。

   **驗收的主體是使用者，不是實作者。**截圖給自己看不是人類兩秒瞄一眼的代理，
   所以實作者要回報的是：怎麼排、為什麼這樣排讀得懂、以及實際長相；
   最終判定留給使用者。

**會動到的檔案**：新增 `marketpulse/quality.py`；`marketpulse/product.py`（Brief 表頭）；
`marketpulse/radar.py`（radar 表頭）；`marketpulse/cli.py`（`analyze` 一併產生）。

**必須新增的測試**：`tests/test_quality.py`，涵蓋上述五項驗收條件，另加一項前視測試：
在資料尾端追加一個交易日，不得改變任何既有日期的三個數值。

---

### DO-3　脈絡層的帶日期資料結構（只有結構與載入，不做量測）

**做什麼**
建立可手動維護、且結構上不可能產生前視偏誤的脈絡記錄。

採用「每次變更寫一個新的帶日期快照檔」的模式（參考 S&P 500 成分股點位重建的
既有做法），**不原地修改單一檔案**：

```
narratives/2026-09-04.yaml     # 這一天為止的完整狀態
narratives/2026-09-18.yaml     # 下次變更時的完整狀態
```

每個檔案的結構：

```yaml
snapshot_date: 2026-09-04
narratives:
  - narrative_id: asic_xpu
    name: 客製化 ASIC / XPU
    first_noted: 2026-09-03      # 這個脈絡第一次被記錄的日期
    source: podcast              # podcast | hot-list | self
    source_ref: 股癌 EP693
    stance: new                  # new | confirming
    named_symbols: ["2454"]      # 來源自己講出來的
    inferred_symbols: []         # 我們自己推論的，必須分開
    note: 聯發科 ECB，輝達認購多數
```

**`narratives/2026-09-04.yaml` 已建立**，內容取自一集真實逐字稿，可直接當測試素材。

**schema 的兩個欄位是被真實輸入逼出來的，不是預先設計的：**

1. **`named_symbols` / `inferred_symbols` 必須分開。**實際情況是來源經常一檔台股都沒點名——
   一整段論述只提到外商或技術架構。如果把「誰會受惠」推論出來塞進同一個欄位，
   那是我們的分析冒用來源的名義，而且它會回頭決定要量測什麼，直接違反 R3。
   推論可以有，但必須看得出來哪些是推論。

2. **`stance` 區分新論點與既有確認。**同一集裡「光通訊持續強勢」是對 rank #1 的確認
   （第一層早就知道了，RS20 +37.4%），而「ASIC/XPU」是第一層完全沒涵蓋的新論點。
   兩者若都記成「9/3 提到某主題」，這一層就沒有資訊量了。這個區分就是 2×2 的雛形。

新增 `marketpulse/narratives.py`，提供 `load_as_of(date)`：回傳
`snapshot_date <= date` 之中最新的那一份快照，並且**濾掉 `first_noted > date` 的脈絡**。

**驗收條件**
1. `load_as_of(D)` 回傳的快照檔，其 `snapshot_date` 是所有 ≤ D 的檔案中最大者。
2. 某脈絡 `first_noted = 2026-08-12`，則 `load_as_of(2026-08-11)` 的結果中不含它。
3. 所有快照檔日期皆晚於 D 時，回傳空集合而非最舊的檔案。
4. 成分股代號格式與 `themes/v1.yaml` 一致（字串，非整數）。

**會動到的檔案**：新增 `marketpulse/narratives.py`；新增 `narratives/2026-09-04.yaml`
（可只放一個範例脈絡，成分股由使用者後續自行填寫）。

**必須新增的測試**：`tests/test_narratives.py`，涵蓋上述四項，重點在第 2 項——
它就是防前視的那道測試。

**額外要做：涵蓋率報告（`coverage_report`）**
比對脈絡的 `named_symbols` 與 `themes/v1.yaml`，回報每個脈絡是 `covered`（成分股皆已
在既有主題中）／`partial`／`uncovered`。**這是衍生值，不存進 YAML。**

實例（已驗證）：`2454` 聯發科不在任何主題中，且無 ASIC/IC 設計類主題，
故 `asic_xpu` 為 `uncovered`——這集最大的市場論點，第一層完全沒在量。
**這個報告可能比量測脈絡強度更有價值**：它直接指出第一層的盲區在哪。

驗收條件 5：`coverage_report` 對上述 `asic_xpu` 回傳 `uncovered`，對 `optical_cpo`
（named_symbols 為空）回傳 `unknown` 而非 `covered`——空集合不等於全涵蓋。

**本項明確不做**：不計算任何脈絡的強度、RS20、排名或圖表。本輪只要結構、載入器、
涵蓋率報告。**特別不要自行填寫 `inferred_symbols`**——那是使用者的判斷，不是實作者的。

## 本輪明確不做

- **RRG**（non-goals D3，2026-09-04 確立，§11 附帶條件已撤回）。
- **多時間窗 RS（RS5 / RS20 / RS60）**——很吸引人，但它是新指標。在 DO-2 告訴我們
  RS20 本身的排名到底穩不穩之前，加更多窗口只是把不確定性乘以三。等 DO-2 有結果再談。
- **把三數合成一個「今日可信度」分數**——直接違反 R1。
- **盤中／即時的量能異常偵測**（違反 D1）、**含損益曲線的回測**（違反 D2）、
  **HMM 或任何 regime 標籤**（違反 D4）、**觀察清單或買賣建議按鈕**（違反 D5）。
- **用 networkx 或圖結構表達脈絡的上下游**——過早抽象（D9）。扁平的帶日期 YAML
  先撐一陣子；真的不夠用時它會自己顯現出來。
- **引入 alphalens 套件**——它確實有 `factor_rank_autocorrelation` 與 `quantile_turnover`
  （Apache-2.0），但 11 個主題做分位分析樣本太少，而我們需要的 Spearman 用 pandas
  內建就有。多一個相依套件換不到東西。
- **用 FinMind 的 `TaiwanStockIndustryChain` 當脈絡種子**——經查該資料集屬付費層，
  非免費層可取得。
- **爬 TPEx 產業價值鏈資訊平台**——該站回 403 且使用條款未能確認。
- **語音輸入、語音摘要、每週 GIF**——超出本輪範圍，且多屬 D7 的周邊功能。
- **除權息幅度量測**——已降 priority，留在 backlog。DO-2 的結論要記得帶著這個雜訊讀。
- **修改 `status` 的語意**（見 DO-1 註）。

## 這裡容易踩到的契約紅線

1. **R1（不做綜合評分）** — DO-2 的三個數字必須各自獨立呈現。不要算平均、不要加權、
   不要弄成一個 0–100 的「今日品質分數」。三個數字講的是不同的事。

2. **R2（不用未來資料）** — 這是本輪最容易踩到的地方。`rank_persistence_k` 在
   T 日顯示時，**只能比較 T 與 T−k**，絕不能比較 T 與 T+k。後者是研究用的統計量，
   前者是當日顯示值。兩者公式幾乎一樣但方向相反，寫錯了測試不一定抓得到——
   所以 `tests/test_quality.py` 的前視測試是必須的。

3. **D10（不調參數門檻）** — 不要設「dispersion 低於 X 就顯示雜訊日」這種門檻。
   顯示原始數值與百分位，讓使用者自己判讀。任何門檻都會變成之後被調整的對象。
   *（本輪的規則質疑對象就是 D10，見報告。）*

4. **§7 PIT** — DO-3 的 `load_as_of` 是為了讓脈絡遵守與成分股相同的 T-1 規則。
   `first_noted` 的過濾不是選配。

## 留給實作者的未決問題

1. ~~`market_daily.parquet` 放哪？~~ **已回答 2026-09-04：**
   放 `data/snapshots/market_daily.parquet`。

   - **不要修改 `_write_snapshot` 或 `_load_snapshot`**（`cli.py:50,80`）——
     它們寫死 `theme_daily.parquet` 是刻意的，為兩個呼叫點去改一個已在關鍵路徑上的
     函式並不划算。
   - 新增兄弟函式 `_write_market_daily(data_dir, frame, *, classification_version)`，
     結構與 `_write_snapshot` 同構。
   - **直接重用現有的 `_write_snapshot_meta`**（`cli.py:59`）——它的簽章
     `(parquet_path, *, classification_version, rows, as_of)` 本來就是泛用的。
   - meta 必須帶 `classification_version`：三個統計由 `theme_daily` 算出，
     換一組主題定義結果就不同，這是 provenance 的一部分。
   - 先例：`data/snapshots/` 已有三組 `replay_*.parquet` 各配一份 `.meta.json`，
     「一個目錄多種產出、每份配一個 meta」是既有慣例，非破例。
   - `.gitignore` 不需修改，`data/snapshots/*` 已全部排除。

2. ~~Brief 表頭要放三個數字全部？~~ **已回答 2026-09-04：全放，排成一行。**

   已量測：Brief 內文最寬 49–51 欄（CJK 計兩格）。三個數字一行約 42 欄，塞得下。
   建議格式（版面細節仍由你決定，見驗收條件 6）：

   ```
   持續性 .87   換手 12 (68%)   離散 8.4pp (41%)
   ```

   括號內為該值在自身過去 60 日分布中的百分位。持續性不加百分位（見上）。

3. 驗收條件 6（兩秒內看懂）刻意沒有規定版面。這是資訊設計問題，不是像素問題——
   位置、順序、留白都可以是答案。但**不要為此改動 radar 現有的顏色配置**：
   顏色之後要留給第二層編碼「數字與故事是否一致」，本輪不要先用掉。
