# MarketPulse 設計衝突／不一致／改寫備忘

- **日期：** 2026-08-30
- **用途：** 後續評估、改規格、或回看「為什麼不照 GPT 稿做／為什麼不照 r1 做」時用。**不是**實作規格。實作以設計文件為準。
- **設計文件（現行 r3.26，凍結）：** `docs/design-v0.1.md`  
- **實作契約：** `docs/coding-contract.md`
- **審查筆記：** `/var/folders/k3/f9js6pcj02xclk75ds1nhzl40000gn/T/grok-chenyuying/grok-design-review-cc86276c.md`
- **工作區：** `/Users/chenyuying/workspace/MarketPulse`（`dev` freeze r3.25；本輪 r3.26 只收人眼顯示）

本檔記錄三份來源之間的**衝突**、r1 內部**不一致**、以及 r2／r3 **改寫了什麼**。若之後要推翻某一列，改這張表並同步設計文件，不要只改程式。

---

## 1. 三份來源

| 來源 | 一句話 | 要回答的問題 |
|---|---|---|
| **A. 使用者原始需求** | 仿股癌，從族群趨勢／類股輪動出發，先在 Mac 跑 MVP | 盤後能不能看出錢在哪個族群、輪到哪、族群裡誰強？ |
| **B. Grok 設計 r1** | 台股 TWSE+TPEx、題材 YAML、成交值加權、Streamlit 熱力、12 個 PR | 兩週內做出可看的盤後掃描器 |
| **C. 使用者貼的 GPT v0.1 實作提示** | 美股、GICS、CLI、as-of replay、凍結快照、基準對照、GO/NO-GO | 在日期 T 當時已知的資訊下，輪動有沒有遠期超額？ |

r2 的合成一句話：

> **產品意圖用 A（台股＋股癌語言＋成交值佔比）；工程骨架用 C（replay／快照／基準／不製造顯著性）；B 的 GUI 與 12-PR 節奏往後推。**

---

## 2. 衝突總表（A × B × C）

處分欄是 r2 已做的決定。後續若評估分析要改，從這裡動手。

### 2.1 產品／宇宙

| 議題 | A 原始需求 | B 設計 r1 | C GPT v0.1 | r2 處分 | 後續可再評估的點 |
|---|---|---|---|---|---|
| 市場 | 股癌 → 隱含台股 | TWSE+TPEx 普通股 | **US only**，SPY/QQQ | **拒絕美股 MVP**；`market` 欄位預留 | 若台股資料源不穩，是否用美股當「研究引擎」沙盒、台股當第二市場？目前否。 |
| 分類 | 族群／題材（AI、重電…） | 官方產業 + 主題 overlay（16 主題種子） | GICS sector **與** industry 兩層 | **保留雙層**；v0.1 只手維護 **5** 個主題；官方層**不進 replay**（非 PIT） | 5 個是否太少、官方層要不要另找歷史產業表 |
| 語言 | 主流／落後補漲／輪動 | 主流延續／剛轉強／落後補漲／過熱轉弱／落後持續 | LEADING / IMPROVING / WEAKENING / LAGGING | **修改**：對內可 1:1 map，對外只股癌中文。**落後補漲是第五態**，GPT 沒有 | 落後補漲是否該進 composite GO 籃子（r2 預設：**不進**，日報另欄） |
| 使用方式 | Mac 先跑起來 | Streamlit 四～五頁 + launchd | CLI，無 GUI，無 web backend | **修改**：v0.1 = CLI + Markdown 日報；Streamlit = Phase 1.5（replay 非 NO-GO 後） | 若操作者堅持每天要圖，可否把 ASCII／matplotlib 放進 report 而不開 Streamlit |
| 自動交易 | 未要求 | 明確非目標 | 明確禁止 | 一致：**不做** | — |
| AI／敘事 | 未要求 | 非 v0.1 | 明確禁止 | 一致：**不做** | 長期願景 C 有 Narrative Engine，與股癌「聽題材」較近，列 Phase 2+ |

### 2.2 研究問題 vs 掃描器

這是最大的方向衝突。

| | B r1 | C GPT | r2 |
|---|---|---|---|
| 第一個「有用」里程碑 | ASCII／Streamlit 熱力圖 | 歷史 replay 能說 GO/ITERATE/NO-GO | **PR 4 熱力**給人看；**PR 6 verdict** 決定要不要 GUI |
| 成功標準 | 主流延續×強勢股 20 日 `hit_rate ≥ 55%` | 複合分數相對 random／SPY／momentum／RS-only 有沒有多資訊；不製造顯著性 | **刪 55% 門檻**；H1–H5 + GO/ITERATE/NO-GO |
| 評估物件 | 熱門族群裡挑強勢股 | **as-of 產業籃子**（不讓未來選股污染） | **主假設 = 主題等權籃子**；H-leaders 當第二實驗 |
| 基準 | 幾乎只有「落後持續隨機抽 5 檔」 | Random industry、SPY、20D mom、RS-only、composite | TAIEX、random theme、mom20、RS-only、thrust-only、composite |
| 風險 | 熱力很好看，但不知道輪動有沒有用 | 科學較完整，但做成美股 GICS 會背離股癌 | 先證明「族群輪動」再決定「強勢股 overlay」 |

**後續評估時要記得：** 若 H-rotation NO-GO，不要把 H-leaders 做好看當過關。若 H-rotation GO 但 H-leaders 差，產品仍可只出族群日報、不推個股。

### 2.3 聚合與量能（股癌核心）

| 議題 | B r1 | C GPT | r2 處分 | 為何衝突 |
|---|---|---|---|---|
| 族群報酬 | lag-1 成交值加權（公式成員時點不一致，見 §3） | 不只要市值加權；要 performance **+ breadth**；不要一檔權值股主宰 | **訊號**維持成交值加權（「錢在哪」）；**評估籃子改等權**；另算 `concentration_top3` | GPT「去權值」是為了統計乾淨；股癌看的是資金。r2 拆成兩個用途，避免 2330 假通過。 |
| 量能 | 成交值佔比 + 週轉率（欄位用錯，見 §3） | `volume / 20D avg`，組內加總且防 mega-cap | **成交值佔比 = v0.1 量能主指標**；週轉率暫不進分數 | 台股「錢」是成交金額不是股數。GPT 的相對量在美股較合理。 |
| 權值股 | 風險表有寫 2330 | 「不要讓一檔完全主宰」當設計原則 | 訊號保留權值效應；評估用等權對沖 | 若之後發現訊號層也被 2330 綁架，可加 `ex-2330` 主題（Open Q #2） |

### 2.4 技術棧

| 項目 | B r1 | C GPT | r2 | 可行性備註 |
|---|---|---|---|---|
| 語言／工具 | Python、pandas、SQLite WAL、Streamlit、可能 launchd | Python 3.12+、**uv**、Polars、DuckDB、PyArrow、Pydantic、Typer、pytest、Parquet | **uv + Typer + pydantic**；pandas ingest；SQLite = 可變快取；**Parquet = 凍結 run**；Streamlit optional | 台股 ~2k 檔 × 5 年，pandas+SQLite 夠用。Replay 全日掃過慢再加 Polars/DuckDB，不擋 v0.1。 |
| 禁止清單 | 無雲、無 K8s | 明確禁 Docker/K8s/Postgres/Redis/Kafka/Airflow/Celery/vector DB/微服務/web backend/auth | 對齊禁止清單 | 可行 |
| 資料源 | TWSE MI_INDEX + TPEx（URL 未釘死）+ FinMind 還原 + yfinance stub | yfinance prototype、Provider Protocol、不鎖廠商 | **Provider Protocol 採納**；主路徑官方 dated JSON；FinMind 還原 **非 v0.1 輸入**；yfinance 預設關 | 見 §3 TPEx／FinMind。美股 yfinance 對 C 可行；對台股成交金額不夠。 |

### 2.5 時序／範圍

| | B r1 | C GPT | r2 |
|---|---|---|---|
| PR 數 | 12，熱力（PR9）在 replay（PR12）之前 | Milestone 1–8，dashboard 最後 | **8 個 PR**：資料→族群→訊號→replay→評估→日報→（可選）GUI |
| 兩週範圍 | ingest + 16 主題 + 五頁 GUI + launchd + 回測 | 無 GUI；科學引擎完整 | 縮小主題到 5 個；拿掉 launchd；GUI 不進 v0.1 DoD |
| 盤中 | 非目標 | 未做 | 一致不做 |

---

## 3. r1 內部不一致／不可實作處（審查 16 則）與 r2 改寫

這些是「同一份設計自己打自己」或「寫了但做不出來」，與 GPT 衝突無關，但評估時很容易再踩。

| ID | 嚴重度 | 不一致／缺陷 | r2 改寫 |
|---|---|---|---|
| I1 | major | 沒有對 GPT 稿的採納／拒絕表 | 設計文件新增對照表（亦摘要於本檔 §2） |
| I2 | major | 12 PR；Streamlit 在 replay 前；兩週過載 | 8 PR；replay（PR5–6）在 Streamlit（PR8）前 |
| I3 | major | `group_bar`/`rotation_signal` PK 覆寫；無 `run_id`／版本；`scan` 讀整庫會前視；FinMind adj 向後改寫歷史 | 工作表 vs **Parquet 凍結快照**分開；`WHERE date <= as_of`；mutate-future pytest；adj 不當穩定欄 |
| I4 | major | 55% hit_rate 把「輪動」和「強勢股濾網」綁在一起；基準不足 | 兩層：H-rotation 必做、H-leaders 附錄；GO/ITERATE/NO-GO |
| I5 | major | pandas+SQLite 一句話打發 Polars+DuckDB+Parquet | 寫明：SQLite 快取 vs Parquet 快照；FinMind 回 pandas 是 ingest 邊界 |
| I6 | major | TPEx OpenAPI **沒有 date 參數**，不能當歷史主路徑 | 主 URL 釘死 `stk_quote_result.php?d={ROC}/MM/DD&o=json`；OpenAPI = 今日；TWSE 依**表名**解析；PR2 必須 spike |
| I7 | major | FinMind `Trading_turnover` 被當成週轉率，實際是**成交筆數**；流通股無 PIT | 改名 `trade_count`；v0.1 **不算週轉率**；量能用成交值佔比 |
| I8 | major | `w` 用 t−1 成員、`r_g` 用 t 成員 → 權重和 ≠ 1；`N_g=1` 除零；ties 未定；Δs 定義了沒用；SMA 含不含 t 不一致 | 成員與權重皆 **t−1**，有報酬者重新正規化；`N_g<2` → score NULL；ties 平均；SMA 慣例進 YAML |
| I9 | major | 五個體制可同時觸發；Q1 非整數；防禦收斂要「金融 RS」但沒有 bucket bar；漲跌停 9.5% 誤判處置／無漲跌停 | 單一 if/elif；**改 `rank_pct >= top_pct`（0.75），刪 Q1=0.25N，不用 ceil-Q**；金融 RS 從 v0.1 防禦規則拿掉（只用 ad_ratio）；漲跌停改官方漲跌證券數表；數字全進 YAML |
| I10 | major | 只有主題 as-of；`instrument.official_industry` 是現況；YAML `as_of` 回寫會前視 | `valid_to = sync_date`；官方層標明 **非 PIT、不進 replay** |
| I11 | major | 16 空殼主題 + GUI + launchd + 回測同一週；FinMind adj 是否免費未 spike | v0.1 五主題手維護、禁止空殼 auto-fill；adj 選配 |
| I12 | major | 無 Provider Protocol、無 `validate` CLI、壞列處理不明 | `BarProvider`；`validate`；不默默丟列 |
| I13 | minor | adj 個股 vs 未還原 TAIEX；52w 用 raw high 但 RS 用 adj | v0.1 **全程 raw-vs-raw** |
| I14 | minor | Key Decisions 沒覆蓋快照／評估物件／成功框架 | 新增 D17–D22 |
| I15 | minor | 無 `scan_run`；rollback 會刪唯一歷史訊號 | `scan_run`；rollback 只重建工作表、保留 snapshot |
| I16 | nit | 四頁 vs 五頁；`etr` vs `etn`；pin 語意；52w 三個數字；聯電在先進製程 | 五頁 Phase 1.5；`etn`；獨立 pin 表；`lookback_52w: 252`；2303 移出 `foundry_advanced` |

---

## 4. r1 → r2 規格改寫對照（實作時最容易改錯的地方）

### 4.1 評估

| | r1 | r2 |
|---|---|---|
| 通過線 | 持有 20 日 hit_rate ≥ 55% | **刪除**。描述統計可報 hit_rate，不作門檻 |
| 主物件 | 熱門族群 × 強勢股 | as-of **主題等權籃子**（成員 = 訊號同一 \(G_{t-1}\) 交集，不事後選股） |
| 遠期窗 | 偏 20 日 | +5 / +10 / +20 / +60 交易日 |
| 基準 | 落後持續隨機 5 檔 | TAIEX、random theme、20D momentum、RS-only、value_thrust-only、composite |
| 結論 | 不明 | GO / ITERATE / NO-GO，禁止用 p 值「製造顯著性」 |
| 案例 | 2023 AI、2024–25 重電當通過證據 | 只當**敘事重播**；membership 用標了「重建」的 `v2023.yaml` |

### 4.2 資料

| | r1 | r2 |
|---|---|---|
| TPEx 歷史 | `stk_quote_result` **或** OpenAPI（誤） | 僅 dated `stk_quote_result.php`；OpenAPI 今日 |
| 週轉率 | FinMind `Trading_turnover` | 該欄 = 成交筆數；v0.1 不計算週轉率 |
| 還原價 | FinMind adj 當 RS 輸入 | **不進 v0.1**；全程 raw |
| 主題數 | 16（含空殼） | 5 個手維護；禁止用官方產業自動填滿空殼 |
| 先進製程 | 可能含 2303 聯電 | 2303 移出 core |

### 4.3 公式／體制

| | r1 | r2 |
|---|---|---|
| `r_{g,t}` | 權重 t−1、求和成員 t | 權重與成員皆 t−1，交集重新正規化 |
| 體制 | 可重疊，優先順序未寫 | 單一 if/elif，每日一個主標籤 |
| 門檻 | 散落正文 | 全部 `configs/settings.yaml` |
| 官方產業 | 假裝 ingest 有快照 | 承認沒有歷史；日報可顯示但加註；replay 不用 |

### 4.4 介面與 PR

| | r1 | r2 |
|---|---|---|
| CLI | ingest / sync_groups / scan / brief / run / dashboard / backtest | download / validate / sync-groups / analyze / replay / report / brief / doctor |
| GUI | v0.1 四／五頁 Streamlit | v0.1 零 GUI；Phase 1.5 五頁且依賴 PR6 非 NO-GO |
| 排程 | launchd 18:30 | v0.1 手動；launchd 在 Phase 1.5 |
| PR | 12，熱力先於 replay | 8：`1→2→3→4→5→6`，**PR7 依賴 PR5**（可與 6 平行），PR8 最後 |

對內狀態 map（避免之後有人把 GPT 四態直接畫進日報）：

| 內部 enum（可與 GPT 對） | 日報／股癌語言 | 備註 |
|---|---|---|
| LEADING | 主流延續 | |
| IMPROVING | 剛轉強 | |
| （無對應） | **落後補漲** | 本產品第五態；進日報、**不進** composite GO |
| WEAKENING | 過熱轉弱 | |
| LAGGING | 落後持續 | |

---

## 5. 可行性（之後評估「能不能做完」用）

### 5.1 現在看起來可行

- Mac 單機、uv、Typer、SQLite、pytest：一人可維護。
- TWSE `MI_INDEX?date=` 全市場盤後 JSON：免費、可回補。
- 主題 YAML 五檔手維護：比 16 空殼可執行。
- CLI 日報：不依賴 Streamlit，盤後當天就有輸出。
- Parquet 快照 + mutate-future 測試：防止「熱力圖看起來對、回測其實前視」。

### 5.2 仍取決於 spike（做之前不要承諾）

| 項目 | 風險 | r2 預設退路 |
|---|---|---|
| TPEx dated JSON 是否穩、欄位是否變 | 上櫃五年回補可能做不到 | 上櫃只從今日累積；`doctor` 降級；**不准**用無日期 OpenAPI 假裝有歷史 |
| FinMind token／Adj 是否真免費 | 文件互相矛盾 | v0.1 不用 Adj |
| 全日 replay 2000 檔 × 5 年 × pandas | 可能慢 | 先做；慢再加 Polars/DuckDB，不改產品 |
| 主題成員主觀 | 2023 AI 案例若用今天的名單 = 前視 | 重建檔必須標「重建」；評估不把案例當 GO 證據 |
| 存活者偏差 | 免費源多半是今天還在的股票 | 報告必須寫「非無偏」；不宣稱 bias-free |

### 5.3 不建議在 v0.1 再加的（即使 GPT 或股癌聽起來都要）

- 美股平行宇宙（會把資料／基準／分類全部叉開）
- 完整 RRG 數學
- 自動最佳化權重（與 walk-forward「權重固定」衝突）
- 盤中、券商下單、LLM 讀節目／新聞
- 用官方產業當歷史回測（沒有 PIT）
- 把 55% 或 p < 0.05 寫進 CI

---

## 6. 建議的後續評估順序

評估分析時不要一次比「整份 GPT」vs「整份股癌」。拆開：

1. **資料能不能 as-of 重播？**（PR2–3、I3/I6/I10）  
   失敗 → 任何輪動結論都不能信。
2. **主題等權籃子有沒有遠期超額？**（PR6 H-rotation，對 TAIEX / random / RS-only）  
   NO-GO → 不要做 GUI，回頭改主題定義或承認假說不成立。
3. **成交值加權訊號 vs 等權評估是否敘事一致？**  
   若兩者長期相反，要決定產品到底聽「錢」還是聽「廣度」。
4. **第五態「落後補漲」單獨的遠期表現**（日報分欄；**不進** composite，已由使用者確認）  
   只評估要不要在 brief 裡強調，不再討論進 GO 籃子。
5. **H-leaders overlay**  
   只有 2–4 有訊號才值得做個股頁。

---

## 7. Open Questions 狀態

### 已由使用者確認（2026-08-30）— 見 §10

1. FinMind token：選配；v0.1 raw；有 token 只拉日曆／Info；Adj 要 spike 才進 Phase 1.5。
2. 2330 留在 `foundry_advanced`；不做 ex-2330。
3. 落後補漲進日報分欄，**不進** composite GO。

### 規格預設（未再詢問）

4. 創新板：可存、不進 leader／籃子。
5. TPEx dated URL spike 失敗：上櫃只從今日累積。

已關閉、不要再當未決：自動交易、盤中、美股 MVP、等權當訊號主聚合、55% hit_rate 過關、ex-2330、落後補漲進 composite。

---

## 8. 檔案關係

```text
原始需求（對話）
    ├─ Grok 設計 r1  ──審查 16 issues──►  r2 ──審查 17–23──► r3 ──Q1–3 確認──► r3.1  ← 實作以這份為準
    └─ GPT v0.1 提示 ──採納／修改／拒絕表─┘
                                              │
                                              ▼
                         本檔 docs/design-delta-gpt-vs-grok.md
                         （衝突、不一致、改寫；給後續評估）
```

若實作中發現本表與設計文件打架：**改設計文件，並在本檔加一節「rN 變更」**，不要只在程式裡默默改。

---

## 9. r3 變更（Issues 17–23）

實作規格仍以設計文件 r3 為準。本節只記「改了什麼、為什麼」，避免之後評估又把 r2 的草稿當現行。

| Issue | 嚴重度 | 改了什麼 | 刻意沒改 |
|---|---|---|---|
| 17 | major | **選 (b)**：維持 `thin_min_members: 4`。先進製程加到 6 檔（2330/3711/6488/3532/6239/2449），記憶體 7 檔，PCB 8 檔（高於 floor，單檔停牌不會整組 thin）。pytest：每個 v1 theme `len(members) >= thin_min_members`。 | **沒有**把門檻降成 2（那會讓兩檔組永遠過關、concentration 失控）。仍不含 2303。 |
| 18 | major | 拆 **`daily_run_id`**（`data/snapshots/<id>/`，`scan_run`，無 verdict）與 **`campaign_id`**（`reports/replay_<id>/`，`replay_run`，才有 GO）。重用規則 = 版本元組 `(algorithm_version, config_version, classification_version, price_mode)` **全等**。CLI：`report --campaign-id`。 | 沒有讓同一個 id 身兼單日與戰役。 |
| 19 | major | `replay` 若 `start < yaml.as_of` → abort，除非 `--allow-reconstructed` **且** notes 含「重建」。官方 H1 = v1 從 `as_of`（2026-01-01）到資料末日（樣本短 → 第一次 ITERATE 是預期）。重建戰役 `verdict=APPENDIX`，**不能 GO/NO-GO**。Happy-path 範例改成 2026 窗口。 | 沒有把 v2023 重建檔升格成官方戰役。 |
| 20 | minor | `random_theme`：無放回抽 `k=\|L_T\|`，優先補集 `U\L_T`；補集不夠則從全體抽並 `baseline_degraded=true`；再不夠該日 vs random = NULL。單一 seed，寫進 manifest。 | 不做 k=100 Monte Carlo。 |
| 21 | minor | 評估籃子 = 訊號同一 \(I_t \subseteq G_{t-1}\)（+ 流動性）。`summary.md` 印 `basket_membership: g_t_minus_1`。 | 不用「decision-time T」另一套成員。 |
| 22 | minor | PR 7 **依賴 PR 5**。brief **只讀 Parquet**。刪除未實作的 `group_bar_working`。 | 不為 brief 另開可變訊號表。 |
| 23 | nit | YAML 加 `expand_mkt_value_ratio_min: 1.0` 與 `expand_taiex_ret20_min` / `rotate_taiex_ret20_min` / `defend_taiex_ret20_max`。**本檔 I9 改為 rank_pct／top_pct=0.75，刪 Q 用 ceil。** | **沒有**把設計改回 ceil-Q。 |

未重開：美股-only、等權當訊號主聚合、55% hit_rate。

---

## 10. r3.1 使用者確認（2026-08-30）

Open Questions 1–3 由使用者拍板，視為最終決定，實作與後續評估不得再討論替代方案。設計文件 Open Questions 已改標「已由使用者確認」。規格副本：`docs/design-v0.1.md`。

| # | 問題 | 使用者決定 |
|---|------|------------|
| 1 | FinMind token | **選配。** v0.1 用 raw 價，RS 不依賴 Adj。Token 若有只用於日曆／Info。Adj 須 live spike 證明免費才進 Phase 1.5。 |
| 2 | 2330 與先進製程 | **留在 `foundry_advanced`。** 評估用等權降低權重。不做 ex-2330，不把 2330 移出該主題。 |
| 3 | 落後補漲 | **進日報分欄，不進 composite GO 籃子。** composite 僅主流延續 ∪ 剛轉強。 |

Questions 4–5 未再詢問，維持預設：創新板可存但不進籃子；TPEx dated URL spike 失敗則上櫃只從今日累積。

---

## 11. r3.2 第二輪 GPT 設計回饋（2026-08-30）

來源：使用者貼的對 `design-v0.1.md` 的評分稿（8.5/10，建議 coding 前小修）。**實作規格已改 r3.2。** 本節記錄處分，避免之後把「建議改 score 數學／加 DuckDB」當成未決。

| GPT 點 | 處分 | 寫進規格的內容 |
|---|---|---|
| 一、eval 流動性時點不明（TV_T vs TV_{T-1}） | **採納 P0** | \(I_T = G_{T-1} \cap\) 流動性\(_{T-1} \cap\) 宇宙\(_T \cap\) close_T>0。訊號與評估同一宇宙。 |
| 二、random_theme 名不副實 | **採納 P1** | 改名 `random_exclusive_theme`：等基數、排除 \(L_T\) 的負向對照，不是全市場隨機。 |
| 三、5 theme 統計很粗 | **採納定位，拒絕擴 theme** | 文件寫死：engine validation seed，不是完整 taxonomy。 |
| 四、rank-of-rank 丟掉距離 | **採納註解，拒絕改公式** | 加「score distance 無經濟意義」；v0.1 維持現 rank。 |
| 五、survivorship 應升 HIGH | **採納並切兩層** | 風險升 HIGH。DoD：`universe_member(T)`=當日看板。**不**買下市庫。2026 有看板則偏差較小；v2023 主題種子仍是存活者。 |
| 六、sync-groups 生效日 | **修改（不採用 next_trading_day）** | `valid_from = sync_date`；報酬／籃子用 \(G_{T-1}\)。不加第三套時鐘。 |
| 七、市場體制容易「不明」 | **採納保留** | 明文禁止把不明塞進某個 regime。 |
| 八、raw 價除權息污染評估 | **採納 P1** | `data_quality` 只標記、不剔除。 |
| 九、H-leaders 拆出主假設 | **維持** | 不改。 |
| 十、GO 加 min n | **採納 P0** | `min_primary_observations_per_half: 30`；不足 → ITERATE，不得 NO-GO。 |
| 十一、TPEx spike 升 Gate 0 | **採納 P0** | PR 0：20–30 日 dated spike，阻擋 PR 2 多年回補。 |
| 十二、不要 DuckDB/Polars/AI | **採納** | 瓶頸是分類品質／as-of／評估，不是 2k×5y。 |

**刻意沒改：** rotation_score 數學、五主題名單、CHOP/不明、H-leaders、raw 價、自動交易、美股、ML。

**起步授權：** 只做 Gate 0 + PR 1 + PR 2，不要一次實作完整 MVP。

---

## 12. r3.3 第三輪 GPT coding prompt（Rotation Timeline）

使用者對 **Rotation Timeline** 有興趣。這份 prompt 可當實作說明的口氣，**不能整份覆蓋本規格**。衝突已在設計 r3.3 處分：

| Prompt 條款 | 處分 | 說明 |
|---|---|---|
| Dual question：research + daily reading | **採納** | v0.1 同時要 GO 報告與人眼可讀輸出 |
| Rotation Timeline 靜態 PNG + 背後 parquet | **採納** | Y 軸 = `relative_position`（名次變換），標題寫明非經濟距離 |
| `get_signal_context` / `get_entry_date` / `get_forward_horizon` | **採納** | 擴充既有 `asof.py`，評估器不得自訂日期 |
| 報告拆 CORE / REGIME / LEADER | **採納** | 不改產品 GO 規則 |
| brief 可能輪動 A → B | **修改** | 僅當過熱轉弱、剛轉強各恰好 1 個才畫箭頭；否則只列兩側 |
| \(r_g\) 改等權連乘（prompt §8） | **拒絕** | 訊號維持 lag-1 成交值加權；等權只給評估籃子 |
| snapshot 目錄 `YYYY-MM-DD/` | **拒絕** | 維持 `daily_run_id`；日期當 key 會覆寫 |
| 必備 CLI `freeze`/`evaluate` | **修改** | 不增冗餘；加 `chart` |
| 光學→被動→主動 當新主題 | **拒絕** | 五個 seed 就能畫位移；不加主題 |
| Polars 當預設、互動圖、Streamlit | **拒絕** | matplotlib 靜態圖即可 |
| 「先貼這份 prompt 給 OpenCode」 | **拒絕整份覆蓋** | agent 以 `docs/design-v0.1.md` 為準。此 prompt 當口吻與 Timeline 需求，不當第二份規格 |

Timeline 落在 **PR 7**（依賴 PR 5 快照，可與 PR 6 平行）。起步仍是 Gate 0 + PR 1 + PR 2。

---

## 13. r3.4 第四輪 GPT：classification 時序矛盾（P0）

這輪指出的 P0 **成立**：`v1.yaml as_of: 2026-01-01` 當官方戰役起點，與 `sync-groups valid_from = 今天` 不能同時真。八月第一次 sync 會讓 1–7 月 membership 全空，H1 變成假 ITERATE。

| 點 | 處分 |
|---|---|
| 拆 provenance / effective_from / valid_from | **採納** |
| v1.yaml = contemporaneous，從首次 sync 起 | **採納** |
| 2026-01-01 → today 改 reconstructed APPENDIX | **採納** |
| 不要硬把 2026-01-01 當 official GO | **採納** |
| 等每天維護名單再累積真正 GO 樣本 | **採納** |
| CA sensitivity report-only（H1_ex_jump） | **採納 P1**。不改 raw 價、不進 GO |
| theme overlap 診斷 | **採納 P1**。不進 score |
| rotation_score 降級為人眼附錄 | **採納 P2**。公式不改 |
| random_exclusive 保留但別解讀成 alpha | **維持**。GO 規則不拆掉 vs exclusive，報告同時印 vs TAIEX |
| min_effect_threshold 現在亂選 | **採納** 設 null，只報告分位 |
| PR4 先不做 leader | **採納** |
| 不要再設計兩三輪、開工 Gate0→PR1→PR2 | **採納** |

**沒改：** 成交值加權訊號、Timeline、mutate-future、Gate 0、H1–H5 架構、Streamlit 延後。五主題改為凍結 baseline（見 r3.5）。

---

## 14. r3.5 2026 座標系擴成 10 theme

使用者要看見今年 A→B→C（光通／被動／CCL），不是只盯 AI 基礎建設五條線。

| 建議 | 處分 |
|---|---|
| 主引擎加光通訊/CPO、被動、CCL、測試、AI電力、散熱 | **採納**（10 theme） |
| 上限 8–10，不要 15–20 | **採納** |
| Theme = 可獨立輪動的資金籃子 | **採納** |
| 保留 5-theme 當 baseline，做 H-tax 對照 | **採納** |
| 不覆蓋舊五主題 YAML | **採納** |
| IC 設計／AI 軟體／生技 | **拒絕（v0.1）** |
| ABF、HVDC、BBU、UPS 再拆 | **拒絕（v0.1）** |
| 把 10-theme 套回 2026-01-01 當官方 GO | **拒絕**（仍是 reconstructed APPENDIX） |

順手修正：6274=台燿，台表科=6278。3017 以 thermal 為主、可 overlap AI 伺服器。

起步仍是 Gate 0 + PR1 + PR2。主題 YAML 在 PR3 才落地。

---

## 15. r3.6 小修（文字殘留 + 解讀風險）

GPT 認為可開工，但要先釘死「跑得出來卻解讀錯」的點。**採納小修，不再開設計大輪。**

| 點 | 處分 |
|---|---|
| 全文 5 vs 10 語義殘留（rollout 仍寫五主題） | **採納** 改 10-theme 主引擎 |
| PIT-safe ≠ research-unbiased | **採納** manifest 必印 hindsight_note |
| rotation_score rank-of-rank | **不改公式**；加 `score_rank_correlation`；H2 升 CORE DIAGNOSTIC、不進 GO |
| H1 穩定性 | **採納** hit_rate/p25/p75/worst_10pct 只報告 |
| overlap matrix | **採納** report-only |
| random_exclusive 別當市場基準 | **維持** 負向對照用語 |
| market_regime 不進 score | **採納** + pytest |
| raw 價 RS reliability | **採納** brief 標 NORMAL/DEGRADED |
| PK `(date, market, stock_id)` | **採納** |
| `auto` = 完整雙市場交易日 | **採納** |
| ingest 空表狀態碼 | **採納** NOT_PUBLISHED vs PARSE_ERROR… |
| Gate 0 九條 PASS | **採納** |
| Timeline 箭頭 deterministic + 持續 M 日 | **採納** |
| 同一 I_T pytest | **採納** |

**下一步授權：Gate 0 → PR1 → PR2，然後停下來 review。不要 implement 整份 MarketPulse。**

---

## 16. r3.7 hardening（停設計、開始跑資料）

GPT 8.5/10：架構 GO，訊號「可以做但不要預先相信」。只 hardening、不再開大輪。

| 點 | 處分 |
|---|---|
| Timeline Y 用當日非 thin 數會假位移 | **採納 P0**。K=分類檔主題數，thin 不重縮座標 |
| n=60 被當成獨立樣本 | **採納 P0**。每張 H1 表印 overlapping_forward_returns |
| CA 只 warning 仍進 GO | **採納 P0**。UNRELIABLE（≥25% 成員 jump）踢出 H1/H3；DEGRADED 仍進 |
| `all_theme` baseline | **採納 P1**。不進 GO |
| `top_value_share` | **採納** 診斷基準，不進 GO |
| component redundancy / RS20 雙重計入 | **採納 P1** 只報告；**不改權重** |
| extra random seeds | **採納** 3 條 sensitivity，不改 GO |
| unique value share | **採納** report-only |
| TAXONOMY BIAS 醒目區塊 | **採納** |
| 再改訊號公式／15 theme／ML／GUI | **拒絕** |
| leader／watchlist 再降優先 | **維持** PR7，不擋 core |

**停止設計。下一步 Gate 0（20–30 日）→ PR1 → PR2，然後 review 真實列數與成交金額單位。**

---

## 17. r3.8 最後五點（Approve with changes → 實作）

GPT：8.5/10，blocker 級 3 個 + diagnostic 2 個。**修完停止設計。**

| 點 | 處分 |
|---|---|
| overlapping n=30 假獨立 | **採納 P0-1**。`raw_n` + `non_overlapping_n`（步長=20）。不改 GO |
| random seed 卡住 GO | **採納 P0-2**。單一 seed 決定 GO；sensitivity → `direction_consistent` / `baseline_fragile` |
| PARTIAL 當完整市場 | **採納 P0-3**。`coverage_ratio >= 0.99` 才算 auto 完整日 |
| snapshot 空白無法 debug | **採納 P1-1**。`signal_status`：OK/THIN/INSUFFICIENT_HISTORY/MISSING_DATA/UNRELIABLE |
| overlap≠相關 | **採納 P1-2**。`theme_return_corr_60d` report-only |
| incremental RS+thrust+… | **採納** H2 診斷，不進 GO |
| GO ≠ 值得交易 | **採納** `ECONOMIC MATERIALITY` 分列 |
| leader/watchlist 再降 | **採納** 整包改 Phase 1.5 |
| Newey-West / 改 composite 公式 / 15 theme | **拒絕** |

**Verdict：停止設計。下一步 Gate 0 → PR1 → PR2，review 資料後再 PR3–7（無 leader）。**

---

## 18. r3.9 Freeze（11-theme + version 邊界）

明確規格矛盾：全文寫 10-theme，YAML 有 11 個 id。**不刪 theme，改定義為 11。**

| 點 | 處分 |
|---|---|
| 10 vs 11 | **採納 11。** 不合併 AI電力與重電，不砍 optical/CCL/passive/thermal |
| classification 與 config 混 hash | **採納。** config=settings only；classification_digest=成員語意 only |
| schema_version | **採納** `"1"` |
| taxonomy_frozen_at | **採納** 2026-08-30；改名單開新 version |
| Negative Control 命名 | **採納** report 用語 |
| EVIDENCE HEALTH | **採納** 不改 GO |
| 不改 A→B 四層 filter | **維持保守** |
| 不再加 indicator | **凍結** |
| v0.1 不建 leaders.py / watchlist.py | **採納** |

**Design frozen。下一步讓真實資料打臉：Gate 0 → PR1 → PR2。**

---

## 19. r3.10 開工前最後 3 個 P0

| 點 | 處分 |
|---|---|
| 殘留 `ten=10` / `5 vs 10` | **採納 P0-1** 全改 11 vs 5；pytest `len==11` |
| manifest 範例 `v1.yaml` + 2026-01-01 + eligible_for_go | **採納 P0-2** 改 `start=classification_effective_from` |
| freeze vs 同 version 改成員 | **採納 P0-3** 成員進出=同 version；加/刪 theme 或改語意=新 version；id 集合變但 version 沒升 → abort |
| signal vs value_share 時點命名 | **採納 P1** API 名稱寫死 |
| next_close 屬 algorithm | **採納 P1** |
| rotation_rank ties | **採納 P1** score DESC, theme_id ASC |
| thin 是 OR | **採納 P1** + 三個 fixture |
| auto / content_digest tests | **採納 P1** |
| Forward validation 用詞 | **採納 P1** 官方戰役不叫 historical backtest |

**Approve with P0 fixes。Design freeze。開始 Gate 0 + PR1 + PR2。不再改核心模型。**

---

## 20. r3.11 開工前最後 contract（design-v0.1(8) review）

來源：對 `design-v0.1(8)` 的最後一輪 architecture review（8.5/10；架構無須推倒；開工前修 3 個 P0/P1）。**不改核心模型。**

| 點 | 處分 |
|---|---|
| Non-Goals／Timeline 殘留「用現有五個 seed」 | **採納 P0-1**。v0.1 Timeline default = 11-theme（`v1.yaml`）。5-theme Timeline 僅 H-tax appendix。`chart` 禁止默認 `v1-five.yaml`。pytest `test_chart_default_eleven.py` |
| `coverage_ratio` 被讀成市場完整性 | **採納 P0-2**。改名 `row_coverage_vs_prior_session`；`coverage_confidence=heuristic`；`official_row_count` 無官方 expected → NULL。新增 `session_coverage` 表。Gate 0 必須量 IPO／列數跳動，禁止把 0.99 當 guaranteed completeness |
| H1 overlapping n=30 造成樣本強度錯覺 | **採納 P1，不改 GO gate**。PRODUCT VERDICT 寫死：GO = 描述性 forward edge，不是統計證明 |
| H1 與 regime/score components 耦合 | **採納 P1**。H1 = predictive persistence of theme regime classification，不是 `rotation_score` 的經濟意義 |
| raw 價 corporate action | **維持 MVP limitation**。`H1_ex_jump` 必須並排，不得省略、不得改寫 verdict |
| 長期 THIN | **採納 P2 report-only** `theme_availability_60d`。不刪 theme、不降門檻、不重縮 K |
| relative_position 被讀成強度 | **採納 P2**。中文：「相對排名位置，不代表絕對強度；位置差距不代表報酬差距。」 |
| 再加 RSI／MACD／外資／本益比 | **拒絕**。停止增加 indicator |
| 改 PR 順序／架構 | **拒絕**。仍 Gate 0 → PR1 skeleton → PR2 data → … → PR8 僅非 NO-GO |

**Verdict：Architecture GO。Approve with P0/P1 contract fixes。Design freeze at r3.11。開始 Gate 0 + PR1 + PR2。**

---

## 21. r3.12 開工前最後 contract（design-v0.1(9) review）

來源：對 `design-v0.1(9)` 的更嚴格 review（8.5/10；PIT 已閉環；4 個 P1 + 3 個可接受研究限制）。對照社群：Harvey–Liu–Zhu (2016) 統計顯著 ≠ 經濟意義；Detzel/Novy-Marx/Velikov 忽略摩擦會扭曲模型比較；random-portfolio 文獻把 random 當 **control** 不是 replicating strategy；overlapping forward returns 會膨脹 n。**不改核心模型，不開 v0.1(10)。**

| 點 | 處分 |
|---|---|
| pipeline 仍有 S9 Leaders / `leader_pick.parquet` | **採納 P0-1**。S9 = Phase 1.5 only。v0.1 freeze 輸入是 S6–S8。禁止建 `leaders.py` |
| schema 有 watchlist 但 v0.1 不做 | **採納 P0-2**。表標 Phase 1.5 reserved；v0.1 禁止 read/write；pytest 列數 = 0 |
| Gate 0 加 20–30 日 taxonomy sanity | **修改位置**。Gate 0 只回答資料源 6 問。taxonomy sanity 是 **PR 4 之後人工檢查**（需要 groups+signals）。放進 Gate 0 會逼 agent 在資料還沒通時寫完整引擎 |
| random_exclusive 會在 mega-theme bull 裡幾乎必贏 | **採納 P1**。升到 methodology 第一級：negative control，不是 benchmark。真正「比簡單規則有沒有加值」看 H2。不新增 baseline |
| rank 母體可能只剩 6 個 theme | **採納 P1**。每日印 `ranked_theme_count` / `thin_theme_count` / `unreliable_theme_count`。不改固定 K |
| overlap 膨脹宇宙 TV 分母 | **採納 P1**。分子可 overlap、分母每檔一次。pytest 鎖死 |
| GO 二元、+0.08% 也能過 | **採納 P1，不改 gate、不加 0.5% 門檻**。GO 與 ECONOMIC MATERIALITY 完全分離；後者 v0.1 永遠 N/A，只印分布 |
| H1 應印 selected theme count / basket size | **採納 P1** |
| A→B 箭頭太乾淨 | **維持 v0.1 restraint**。避免事後腦補輪動故事 |
| FinMind Adj / 更多 indicator / Streamlit | **拒絕** |
| 再開 design-v0.1(10) | **拒絕** |

**Verdict：Design Approved — Ready for Gate 0。Freeze at r3.12。下一步讓真實 TWSE/TPEx 攻擊這個設計。**

---

## 22. r3.13 開工前最後 contract（design-v0.1(10) review）

來源：對 `design-v0.1(10)` 的 architecture + research methodology review（8.8/10；無推翻核心模型的 P0；3 個 implementation-contract）。**不改核心模型，不開 v0.1(11)。**

| 點 | 處分 |
|---|---|
| GO 仍用 overlapping n，容易造成「樣本夠了」錯覺 | **採納 P1，不改 GO gate。** EVIDENCE HEALTH 升成與 PRODUCT VERDICT 並列的第二 headline，必印 Reason 一行 |
| H1 自我驗證（regime 與 score 同四個 component） | **採納。** report 固定 WHAT H1 PROVES / WHAT H2 PROVES。H1=persistence，H2=incremental value。H1 PASS ≠ alpha |
| random_exclusive 偏弱 | **維持 v0.1。** 不新增 baseline。Primary evidence 閱讀順序改為 TAIEX → mom20 → rs_only → random last |
| taxonomy 是 2026 觀看後設計 | **採納。** headline 最上面 TAXONOMY STATUS：PIT-safe YES / ex-ante unbiased NO / GO 從 first sync 起 |
| value_thrust 是相對佔比不是絕對流入 | **採納說明。** 並排 value_share / value_thrust。不改公式 |
| Timeline #1=100 在只有 6 個可排名時 | **採納。** 副標永遠 `Ranked: n / K themes` |
| coverage 0.99 假完整性 | **採納。** doctor 印 `DATA COMPLETENESS: heuristic only` |
| config hash 可能漏掉會改結果的設定 | **採納 P1。** `config_digest` 只含 data-bearing 有效設定；註解／leader.*／eval.*／paths 排除。pytest 鎖死 |
| 文件殘留 H1–H5 | **採納。** 統一 H1–H4 = v0.1；H5 = Phase 1.5 reserved |
| A→B 再做成完整 rotation story | **維持 v0.1 三條件。** 不放寬、不加 indicator |
| 再開 design-v0.1(11) / 再加 RSI 等 | **拒絕** |

**Verdict：GO TO IMPLEMENTATION。Freeze at r3.13。Gate 0 → PR1 → PR2。**

---

## 23. r3.14 開工前 2 個 P0（r3.13 design review）

來源：對 r3.13（約 2,495 行）的 implementation-contract review。核心方向批准 freeze。**2 個 P0 必修，否則 PR6 會卡住或 campaign 語意錯。不開 v0.1(11)。**

| 點 | 處分 |
|---|---|
| `same I_T` 要求各 baseline 成員集合相等 | **採納 P0-1**。改成 same eligibility universe（universe/liquidity/price/exclusions）。theme basket 可以不同。禁止 `assert selected_I_T == random_I_T` |
| campaign 只有一個 `classification_digest`，但同 version 可有 membership event | **採納 P0-2**。`classification_digest_mode=per_daily_snapshot`；manifest `classification_digests[]`。daily snapshot 才是 authority。scan_run 必存 digest |
| random 不控制 beta／流動性／basket size | **採納 P1 wording**。不新增 baseline、不做 matching |
| auto PARTIAL 模糊 | **採納 P1**。PARTIAL ≠ invalid；達標仍可當 auto 完整日。theme-level coverage 只作 diagnostic，不調高 0.99 |
| UNRELIABLE 排除有 selection bias | **採納記錄** `excluded_due_to_ca` n/fraction/theme_distribution |
| H1 可能被 agent 拿 score 排名 | **採納**。H1 選題只看 regime label |
| `definition_status` 不進 digest 易被誤解 | **採納 invariant**。status/notes 不升 version；語意定義改變即使成員碰巧不變也要升 version |
| 11-theme / lag-1 TV / 固定 K / 不再加 indicator | **維持 freeze** |
| 再開 design-v0.1(11) | **拒絕** |

**Verdict：APPROVED WITH 2 P0 FIXES。Freeze at r3.14。Gate 0 → PR1 → PR2。**

---

## 24. r3.15 開工前 CA lookahead + regime contract（r3.14 freeze review）

來源：對 r3.14 當 Design Freeze 的 review。架構 GO。真正的 P0 是 **CA reliability 用了 T+1..T+N，會改 n_H1／GO**，與 No future 衝突。

| 點 | 處分 |
|---|---|
| `ca_member_frac` 含遠期 jump | **採納 P0**。PRIMARY 只看 RS 窗 [T-19,T]。未來 CA 只進 `H1_ex_future_ca` sensitivity，不得改 n_H1／GO／snapshot。pytest `test_ca_asof_no_future.py` |
| market regime 既是 metadata 又是 eval partition | **採納 P0**。可 partition 報告；不得影響 eligibility／score／theme regime／H1／籃子。GO 不分市場體制才過關 |
| `signal_status` 同時多條件 | **採納 P1**。precedence：MISSING_DATA > UNRELIABLE > INSUFFICIENT_HISTORY > THIN > OK。THIN ≠ 資料壞掉 |
| `relative_position` 在只剩 2 條時仍 #1=100 | **不改公式。** invariant：必須與 ranked_theme_count/K 一起讀；禁止當 filter |
| H1 接近 RS20 strategy | **不改 H1。** 維持 persistence test；H2 測 incremental value |
| brief 殘留觀察清單／強勢股／52w／leader_score | **採納 P0 文件層。** v0.1 brief 刪除；Phase 1.5 only |
| 再開下一版設計／加 indicator | **拒絕** |

**Verdict：Design GO after these contract fixes。Freeze at r3.15。Gate 0 → PR1 → PR2。**

---

## 25. r3.16 開工前 H1 circularity + execution_model contract（r3.15 freeze review）

來源：對 `design-v0.1(20260830-162818)` 的開工前 review。**Architecture 9 / Anti-lookahead 9.5 / Research methodology 7.5 / MVP scope 9.5。APPROVE WITH MINOR CHANGES。不開 v0.2。**

反前瞻已經夠了，不要再加 anti-leakage framework。最大剩餘問題不是 future leakage，而是 **H1 的 definition→validation circularity**，以及 **CA exclusion 的選擇偏差**。兩者都用「寫死閱讀語意」處理，不改公式、不導入 Adj、不加 GO gate、不加 baseline。

| 點 | 處分 |
|---|---|
| H1 接近 RS20 momentum 自我驗證 | **採納 P0 wording，不改 H1。** H1 = persistence sanity check，不是 strategy validation。Circularity 承認，不「修掉」 |
| H1 PASS 被讀成模型有效 | **採納 P0。** headline：`H1 — Does the regime persist?` / `H2 — Does the regime add information beyond momentum?`。H2 才是真正研究問題，仍不進 GO |
| GO 太容易被 H1 通過 | **採納語意降級，不增加 gate。** GO = 值得進入下一階段研究。印 Interpretation + Next question = H2 |
| `entry_lag_sessions` 看起來可改 | **採納 P0 schema。** 從 YAML 刪除。進場 = `algorithm_version` 的 `next_close`。pytest `test_entry_timing_not_configurable.py` |
| CA UNRELIABLE 排除非隨機 | **採納 P1 output。** `PRIMARY DATA SELECTION WARNING`。不導入 Adj |
| `ranked_theme_count` 低但 Timeline 仍漂亮 | **採納 P1。** `< 4` → `Cross-sectional sample: THIN`。60D 印 median/min/`days_ranked_below_50%`。不進 GO |
| taxonomy sanity 只寫在 PR4 註解 | **採納 P1。** 正式升格 **Gate 1**。不問賺不賺錢。沒過不准 PR 6 |
| `thin_min_value_share=0.003` 可能太早判 THIN | **不調。** 先跑 `theme_availability_60d` |
| 再加 vol-matched / sector-neutral / propensity baseline | **拒絕。** random_exclusive 維持 negative control |
| SQLite→DuckDB、pandas→Polars、raw→Adj、11→10、加 theme／indicator／ML／leader／watchlist／Streamlit／market-regime selection | **拒絕。全部 freeze** |
| 再開 design v0.2 | **拒絕** |

**Verdict：APPROVE WITH MINOR CHANGES。Freeze at r3.16。Gate 0 → PR1 → PR2。**

---

## 26. r3.17 開工前 4 個 clarification（r3.16 freeze review）

來源：對 r3.16 Design Freeze 的開工前 review。**Architecture 8.5 / Look-ahead 9.5 / MVP scope 9 / Research validity 7.5 / Coding-agent readiness 8。APPROVE WITH 4 PRE-IMPLEMENTATION CLARIFICATIONS。不開 v0.2。不加功能。**

最大剩餘問題不是架構，而是 **H2 還不夠 operational**，以及 **GO 裡的 random_exclusive 容易被實作成真正 benchmark**。

| 點 | 處分 |
|---|---|
| H2 只有「composite ≥ rs_only」 | **採納 P0。** ΔH2 = excess(composite)−excess(rs_only)；必報 mean/median/p25/p75/non-overlapping Δ。禁止 `h2_pass` boolean。不進 GO |
| random_exclusive 語意污染 | **採納 P0 wording，不改 GO 公式、不加 baseline。** TAIEX = 唯一有方向意義的比較。vs random 必須印 `NEGATIVE CONTROL RESULT / not independent evidence` |
| H1/composite 與 RS20 高度 circular | **不改演算法。** 強制 `component_redundancy` Spearman（RS20↔rank_momentum/thrust/breadth/score）放在 H2 旁邊 |
| raw/CA 選擇偏差 | **維持。** warning 加一句 Raw-price mode may systematically exclude CA-heavy themes。不導入 Adj |
| membership event vs 語意改變 | **採納 P1 test。** `test_membership_vs_taxonomy_version.py` |
| replay determinism + data-bearing digest | **採納 P2 升為必測。** `test_replay_determinism.py`；明確 DATA-BEARING vs NON-DATA-BEARING |
| Timeline / 11-theme / lag-1 TV / raw-vs-raw / Gate 0 / 不做 leader | **維持 freeze。不要改** |
| 第一輪寫 signals/eval/chart | **拒絕。** 第一輪只准 Gate 0 + PR1 + PR2 |
| 再開 design、加 Sharpe／p-value／alpha 門檻 | **拒絕** |

**Verdict：APPROVE WITH 4 PRE-IMPLEMENTATION CLARIFICATIONS。Freeze at r3.17。Gate 0 → PR1 → PR2。**

---

## 27. r3.18 產品 vs 研究優先序（原始產品直覺回看）

來源：用最初「顯示族群輪動、以技術量價為主」回看 r3.17。**核心演算法沒有做錯；產品定義有落差。** 不要砍 H1–H4，不要重寫整份 design，不要把 Timeline 做成 Streamlit。

原始產品：

```text
今天炒什麼 → 誰變強／退潮 → 資金 A→B→C → 輪到哪
```

膨脹成的研究產品：

```text
rotation_score → hypothesis → negative control → walk-forward → GO
```

| 點 | 處分 |
|---|---|
| 11-theme + relative_position Timeline | **採納為 PRIMARY 產品。** 這是雷達，不是 PR7 附屬輸出 |
| RS / thrust / breadth 量價 | **維持。** 不是基本面 |
| rotation_score 0–100 當產品概念 | **採納。** score = 內部排序工具；人眼輸出 = position / RS / thrust / breadth / regime |
| H1–H4 太重 | **不砍。** 降成 SECONDARY 研究實驗室。驗證層不得重新定義產品 |
| H1 FAIL 讓產品失敗 | **拒絕。** Detect/visualize ≠ predict。NO-GO 只停 GUI 擴張，不拆 Brief/Timeline |
| Timeline 提前成 MVP | **採納 PR 優先序。** 合併：PR5 → PR7（產品 MVP）→ PR6（研究）。Timeline 仍只讀凍結快照，不提前到 PR4 寫 chart |
| 首頁做成 Streamlit | **拒絕。** v0.1 仍是 CLI + Markdown + 靜態 PNG |
| 第一輪寫 signals/eval/chart | **維持拒絕。** Gate 0 → PR1 → PR2 |
| 再開 v0.2 / 加 indicator | **拒絕** |

**Verdict：APPROVE 產品優先序校正。Freeze at r3.18。雷達第一、實驗室第二。Gate 0 → PR1 → PR2。**

---

## 28. r3.19 兩份開工審查：spec 矛盾 vs reuse 暫停

來源：r3.18 正式設計審查 + 「先停 coding 做 reuse audit」（FinMind / VectorBT / sector-rotation-screener / twstock-research）。

### A. 規格審查 — APPROVE WITH 2 SPEC FIXES

| 點 | 處分 |
|---|---|
| `rank_pct` average-tie vs Timeline `#1=100` | **採納 P1。** 兩套 rank 分開。component = average；`rotation_rank` = 整數 + `theme_id` ASC。pytest 禁止 1.5/95 |
| 缺列讓 value_share 假強 | **採納。** 公式不改。缺必要成員 → MISSING_DATA、不進排名。禁止 T−1 TV 填補。不發明 % 門檻。市場漏非成員大型股 = coverage heuristic 已知限制 |
| A→B 的 `N_g` | **採納 P2 一句話。** `N_g = K`。不改成 ordinal-rank 新公式 |
| 產品定位 / Timeline / 11-theme / lag-1 / H1≠H2 / 不砍研究層 | **維持** |

### B. reuse audit — 拒絕暫停開工、拒絕換核心

| 建議 | 處分 |
|---|---|
| FinMind 當主資料 | **拒絕。** 維持 D4/D5：官方 dated JSON 主路徑；FinMind 選配（日曆／Info）。Adj 前瞻、402、`Trading_turnover`≠週轉率 已踩過 |
| VectorBT 當 H1–H4 引擎 | **拒絕。** 本產品不是 stock→買賣→portfolio；會把 secondary lab 做成交易回測框架 |
| 用 sector-rotation-screener 當 pipeline | **拒絕當依賴。** US 11 檔互斥 ETF、季節性、經濟循環、Buy/Hold/Avoid、Excel/HTML。可當 **UX reference**，不是台股 overlap 題材雷達 |
| twstock-research / Plotly / Streamlit 當 MVP | **拒絕。** 個股評分＋GUI 正是 Non-Goals；v0.1 靜態 PNG |
| 80% reuse / 20% 自寫 → 縮小 PR1–PR8 30–50% | **拒絕這次砍 PR。** 真正要自寫的 overlap taxonomy、lag-1 成交值聚合、as-of snapshot、relative position **就是產品**。pandas rank/SMA 不需要 VectorBT |
| 先停 Gate 0 去做 architecture comparison | **拒絕。** 下一個資訊是 20–30 日官方資料，不是再討論套件 |

**Verdict：APPROVE 兩處 spec fix。Reuse 不當 blocker。Freeze at r3.19。Gate 0 → PR1 → PR2。**

---

## 29. r3.20 coding 前 Conditional GO（CA 產品語義）

來源：r3.19 Design Freeze review。**8.5/10 Conditional GO。不改模型、不導入 Adj、不修 H1 circularity。**

| 點 | 處分 |
|---|---|
| raw-vs-raw 除權息假訊號污染雷達 | **採納 P0 語義，不改價。** UNRELIABLE 升成產品資料品質：不進排名／Timeline 主線／A→B。raw 列保留。禁止偷偷 Adj |
| MISSING_DATA 缺一檔就整 theme 出局太粗 | **採納 P1 政策說明，不加 threshold。** 寫死 conservative：寧可 false-negative。禁止 `missing_ratio < 0.1 → OK`。Phase 1.5 才考慮 impact-weighted |
| Timeline 被讀成市場強弱 | **採納文案。** `Timeline = rotation map, not market strength meter`。不改數學 |
| H1 circularity | **維持。** 禁止為了漂亮而重定義 regime |
| 文件散落、agent 不知以哪段為準 | **採納。** SOURCE OF TRUTH ORDER：Freeze > invariants > formulas > tests > narrative |
| 11-theme / lag-1 / SQLite+Parquet / mutate-future / 產品 vs 研究 | **維持 freeze** |
| 再開 architecture / indicator / GUI | **拒絕** |

**Verdict：Conditional GO after these 3 clarifications。Freeze at r3.20。Gate 0 → PR1 → PR2。Gate 1 是最重要的產品實驗。**

---

## 30. r3.21 coding 前 2 個 P0 + 5 個 P1（A→B 語意與 identity）

來源：對 r3.20 全文件掃描。**9/10，可以 coding。不開下一輪 architecture。**

| 點 | 處分 |
|---|---|
| A→B 被讀成資金流 | **採納 P0 wording，不改公式。** 「相對領先轉換 / Possible leadership rotation」。禁止「資金從 A 流到 B」 |
| MISSING_DATA 診斷 vs 全 NULL | **採納 P0 contract。** 可觀察 raw 可留；score／rank／position／regime = NULL；不進 A→B／eval。禁止兩種極端寫法 |
| foundry 被 2330 吞噬 | **不改 2330。** brief **必留 concentration_top3** |
| algorithm_version YAML vs package | **採納 P1。** 啟動 abort，不只 pytest |
| classification_digest 序列化 | **採納 P1。** UTF-8、sort_keys、ensure_ascii=False、separators=(',', ':')、stock_id string |
| campaign identity 綁 daily_run_id | **採納 P1。** data identity = 日期＋版本＋ordered content_digest[]；run id 只是 provenance |
| A→B 五個 acceptance case | **採納。** `test_ab_arrow_conditions.py` |
| chart 偷偷重算 | **採納。** resolution order + `test_chart_snapshot_only.py` |
| 加 H6／Newey-West／z-score／Adj | **拒絕** |
| 11-theme / rank-of-rank / raw-vs-raw / 產品 vs 研究 | **維持 freeze** |

**Verdict：Freeze at r3.21。修完這兩處 P0 即可交給 coding agent。下一步 Gate 0 → PR1 → PR2。**

---

## 31. r3.22 coding 前 3 個契約 edge case + coding-contract.md

來源：r3.21 Design Freeze review。**APPROVE after 3 contract fixes。停止 design review。**

| 點 | 處分 |
|---|---|
| `I_T` 先 `close.notnull()` 導致 MISSING 偵測不到 | **採納 P0。** `G_T → E_T → M_T → I_T`。缺列在 close 過濾之前 |
| A→B persist 中間缺日 | **採納 P0。** 最近 M 個交易日、每天 A/B 都 OK；任何非 OK 打斷重置。Case 6 |
| 四個 component 有 NULL 仍 skipna 排名 | **採納 P1。** 任一必要值 NULL → INSUFFICIENT_HISTORY，不得給 score/rank/position/regime |
| 3000 行規格淹沒 agent | **採納抽取。** `docs/coding-contract.md`。完整設計仍是 source of truth |
| 11-theme / lag-1 / rank-of-rank / raw / H1-H2 / Gate 1 / PR 順序 | **維持，不再改** |

**Verdict：Freeze at r3.22。停止 design iteration。下一步 Gate 0 → PR1 → PR2。**

---

## 32. r3.23 coding 前 architecture / reuse review

來源：對 r3.22 的「最後一次 architecture / reuse review」。結論：設計方向清楚；最大風險是 agent 把基礎設施寫太漂亮。建議「底層 70–80% reuse、domain 20–30% 自寫」，並新增 twmarketdata vs 官方比較 spike。

| 點 | 處分 |
|---|---|
| 不改核心模型（11-theme、lag-1 TV、as-of、snapshot、A→B、H1/H2） | **維持 freeze** |
| D79「外部 repo = 只當 reference」太保守 | **採納 P1 政策改寫。** 基礎設施 reuse；domain semantics 自寫。reuse client ≠ outsource semantics |
| TA-Lib / pandas-ta | **採納：v0.1 不引入。** 只要 return／rolling／rank |
| VectorBT / backtesting.py | **維持拒絕當 core。** 那是 stock→PnL；本產品是 as-of theme state→forward basket |
| Polars / DuckDB | **維持拒絕。** 瓶頸不是 pandas 太慢 |
| SQLite + Parquet + matplotlib | **維持** |
| RRG | **採納 D91。** 概念參考 YES；實作依賴 NO。不用 JdK RS-Ratio。Timeline 不是 RRG 圖 |
| 不要造 Quant Platform | **採納 D92。** `BarProvider` 是 Protocol，不是 plugin 平台 |
| Gate 0 加 twmarketdata 30-session 交叉驗證 | **拒絕當 Gate 0 條件。** 查過：`twmarketdata` 是 twmarketdata.com 的付費 REST（import `twmd`），免金鑰僅 5 檔、查詢 per-ticker、定價頁寫明 TPEx history deferred、不宣稱 full-market。Gate 0 要的是全市場看板列數與 TPEx dated payload，它回答不了。與 FinMind 同類：永不當主資料、v0.1 不進 Protocol、不 `pip install` |
| 80/20 數字當砍 PR 的授權 | **拒絕。** 棧已經是 pandas／httpx／SQLite／Parquet／matplotlib。真正要自寫的 overlap／TV 聚合／PIT／relative position **就是產品**。不縮小 PR1–PR8 |
| 先停 Gate 0 做 architecture comparison | **拒絕。** 下一個資訊仍是 20–30 日官方資料 |

**Verdict：APPROVE reuse policy wording。拒絕 twmarketdata 進 Gate 0。Freeze at r3.23。下一步仍是 Gate 0 → PR1 → PR2。**

---

## 33. r3.24 GitHub `dev` freeze review（可以開工，再守幾個產品契約）

來源：對 `dev` 上 r3.23 規格的開工審查。**8.5/10，可以開始 coding，但要先守住幾個 P0/P1。不要再開 architecture。**

| 點 | 處分 |
|---|---|
| 產品 vs 研究已分開；H1 FAIL ≠ radar useless | **維持** |
| Timeline 固定 K、11-theme、overlap 全額計入、PIT、reuse implementation own semantics | **維持 freeze** |
| Gate 0 先於任何 analysis | **維持。** 這本來就是下一刀 |
| 再做一次「減法」、把 PR 收成 PR1–PR5 | **拒絕。** 當前 slice 已經是 Gate 0→PR1→PR2。真正要自寫的 theme engine 就是產品。不縮小 PR DAG |
| MISSING_DATA 整 theme 出局太粗 | **維持 conservative 政策（D81）。** 不發明 missing_ratio 門檻 |
| MISSING_DATA 默默少一條線 | **採納 P1 可視化（D94）。** Brief 必印 expected/received/missing `stock_id`；Timeline gap+×，禁止從圖例消失 |
| `rotation_score` 不要進人類 UI | **採納收緊（D95）。** Brief／ASCII／PNG 不得印 82.3。parquet 可留。刪掉「ASCII score 可附列」 |
| Timeline 要回答三個問題，不要做成 RRG | **採納 UX（D96）。** 不改 Y 軸數學 |
| Golden Dataset 當開工 P0 | **拒絕當 Gate 0。** 官方 bars 還沒有，不能發明 expected RS20。改成 PR 4/7 `tests/fixtures/golden/`，Gate 0 之後才填 |
| mutate membership after T | **採納加測。** 既有 mutate-future 加 6b：改 T 之後的 YAML 不得改 snapshot(T) digest |
| H1 改名 Persistence Test | **採納人眼標籤。** 識別字仍 `H1`，不改公式 |
| 繼續大改 2800 行 spec | **拒絕。** 本輪只修產品契約 |

**Verdict：APPROVE 產品契約收緊。拒絕砍 PR、拒絕 golden 當 Gate 0。Freeze at r3.24。下一步仍是 Gate 0 → PR1 → PR2。**

---

## 34. r3.25 GitHub freeze 再評（研究 8.5／產品 7；批准 freeze，開始 Gate 0）

來源：對 `dev` 上 r3.24 規格的完整再讀。評語：**研究設計 8.5/10，產品 MVP 7/10，工程實作風險仍偏高。** 批准 freeze。前提：不要再改 design，開始 Gate 0。

GitHub 頁面上「1 commit」是 reviewer 當下的瀏覽快照；本機 `dev` 當時已有 r3.23 `a774d99` 與 r3.24 `afacda5`。這次仍是 **design contract review**，不是 code review。

| 點 | 處分 |
|---|---|
| 核心產品沒跑掉；PRIMARY = Brief + Timeline；score 不是產品 | **維持** |
| Future leakage / PIT honesty / immutable snapshot / conservative MISSING_DATA | **維持。不改** |
| rank-of-rank 犧牲 magnitude | **不改公式。** 收緊 D36：五欄必須一起呈現 |
| Timeline 其實仍依賴 score→position | **承認，不改數學。** 產品語意 = Rotation Map，不是 Strength Chart |
| value_thrust、overlap 分子全額／分母一次、A→B ≠ capital flow | **維持** |
| MISSING_DATA 整 theme 出局對小股與 2330 同等嚴厲 | **維持 conservative（D81）。** Phase 1.5 才考慮 impact-weighted |
| H1 circularity；GO 看起來比證據更正式 | **維持。** 不改 gate、不加 p-value。人眼顯示 D97 |
| GO 改名 CONTINUE | **採納人眼標籤（D97）。** 識別字仍 `verdict=GO`。`GO → CONTINUE`，`NO-GO → STOP` |
| ROTATION TODAY 四桶摘要 | **採納 Brief 契約（D98）。** 由既有 regime + status 衍生，不是新分類器。PR 7 才做 |
| Timeline 五欄一起、不能只看線 | **採納 D36 收緊。** today-strip，PR 7 |
| 一句話定位：輪動雷達，不是量化交易系統 | **採納。** Overview 加上；不是新產品 |
| MVP 太大、像小型量化研究平台 | **維持 D92 + 當前 slice。** digest／H1–H4 是護欄不是本體。第一輪仍只准 Gate 0→PR1→PR2 |
| 現在停止加功能，開始 Gate 0 | **維持。** 不改公式、不縮小 PR DAG、不開 v0.2 |
| Streamlit／leaders／52w／Adj／ML | **維持 P2 freeze** |
| 再做一次 architecture／改 RS 權重 | **拒絕** |

**Verdict：APPROVE 人眼顯示契約。核心模型不動。Freeze at r3.25。下一步仍是 Gate 0 → PR1 → PR2。未說開始 Gate 0 不准動手寫 ingest。**

---

## 35. r3.26 GitHub freeze 再評（產品雷達 vs 研究框架；批准 freeze，開始 Gate 0）

來源：對 `dev` 上 r3.25 規格的完整再讀。評語：**8.5/10**。方向對準「看族群輪動，不是量化預測器」。不要再大改 design；建議直接進 Gate 0。另會做 coding-agent readiness review。

| 點 | 處分 |
|---|---|
| PRIMARY = Brief + Timeline；score 不是產品；H1 FAIL ≠ radar useless | **維持** |
| 11-theme、禁止 15–20 條線、CLI-first、Streamlit 延後、pandas/SQLite/Parquet 夠用 | **維持 freeze** |
| as-of / mutate-future / immutable snapshot / daily_run_id ≠ campaign_id | **維持。即使不做 H1 也值得留** |
| 不要讓使用者感覺有隱藏總分 | **採納敘事收緊（D95）。** 禁止「AI Server = 87.2」。允許「AI Server — 主流延續；RS20 ↑」 |
| Rank Δ5 / Δ20 | **採納顯示（D99）。** 由既有 `rotation_rank` 衍生。兩端非 OK → `—`。禁止跳洞。不進 score／ranking／GO／A→B |
| Timeline 改成 LEADING/TRANSITION/WEAKENING 泳道 | **拒絕當 v0.1 圖種。** 已有 ROTATION TODAY + today-strip。線圖數學不改 |
| Theme Taxonomy Audit 新模組 | **拒絕新引擎。** = 既有 overlap matrix + `concentration_top3` + `n_members` + Gate 1 |
| status 做成分析維度 / Data Quality Score | **拒絕新分數（D100）。** 徽章：⚠ members 7/8 missing: ids |
| 缺重要成員仍顯示 LEADING ⚠ | **拒絕。** D81：整 theme MISSING_DATA，regime NULL，進 Data issue。這比「Leading 加警告」更嚴，也更符合「不能看起來像正常 Leading」 |
| GO 改名 RESEARCH_GO；PRODUCT: PASS / RESEARCH: GO | **拒絕改識別字。** 採納人眼別名 D101：`RESEARCH VERDICT` = PRODUCT VERDICT。禁止新 PRODUCT: PASS gate |
| H1–H4 瘦成四個白話問題 | **採納 headline 一句話。** p25/p50 仍留 report，不改公式、不砍假設 |
| CA 研究複雜度隔離 | **維持。** `H1_ex_*` 只在 `eval/`，不改 primary signal |
| 同名 GitHub MarketPulse 專案 | **不改產品。** 那些是行情／個股 scoring／news；本產品是台股 theme rotation |
| 現在停止加功能，開始 Gate 0 | **維持。** 不改公式、不縮小 PR DAG、不開 v0.2 |

**Verdict：APPROVE 人眼顯示契約（Rank Δ、status 徽章、RESEARCH VERDICT 別名）。核心模型不動。Freeze at r3.26。下一步仍是 Gate 0 → PR1 → PR2。未說開始 Gate 0 不准動手寫 ingest。**
