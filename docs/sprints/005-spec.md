# Sprint 005 — 尺度可複核：Rank-IC ＋ above_count ＋ B＋C 短註

狀態：已完成 2026-09-06
契約：CLAUDE.md 與 docs/coding-contract.md 全數適用
層次：第一層（數學）＋ 一格使用／工程

## Appetite

- 模組：最多動 `marketpulse/quality.py`、`marketpulse/calc.py`、`marketpulse/cli.py`、`marketpulse/product.py`（或 `radar.py` 若 brief 共用 helper）。**不新增模組檔**除非 CLI 註冊需要；寧願函數放進 `quality.py`。
- 相依：**不新增任何套件**。
- 資料量：不增加；不回補；不改 `themes/v1.yaml`。
- 層：只動第一層數字正確性／診斷／顯示文案。**不動第二層 schema、不動主排名公式（仍 RS20）。**
- 超出即為下一輪：換 primary、IBD 加權、Elo、composite、as-of 成分、雙池。

## 目標

把「短端信、長端打折」從文件主張變成**可複核的前向 Rank-IC 數字**；顺手修掉邊界 `above_count` 假 0；讓 Brief 持續性旁看得到 B＋C 一句話。

## PO 的前提決定

1. **不換 primary rank**（2026-09-06 再確認；backlog 橫斷面盤點維持）。改選「換主排名」→ 本 spec 作廢。
2. **k=20 讀法維持 B＋C**（文件已寫）。本輪只把同一句搬到產品輸出，不發明新詮釋。
3. **Rank-IC 是買資訊，不是交付策略。** 不設顯著性門檻、不依 IC 改 rank、不進 daily `refresh`。
4. **籃子／敘事／Q5／Q6 本輪不動。**

## 要做的

### DO-1 — 前向 Rank-IC 視窗矩陣　[L1・買資訊]

**背景。**004 量到 persistence 梯度 k=1/+34σ → k=5/+25σ → k=20/+2.84σ。社群再查後結論是問題在尺度不在統計量。缺的是**前向**物證：過去的 RS 排名跟未來超額報酬橫斷面相關多強。

**做什麼。**新增 CLI 子命令（建議名 `rank-ic`）：

- 對每個交易日 T（樣本內、兩端裁切使 T+h 存在），在主題橫斷面上算  
  `Spearman( RS_k[T] , 未來 h 日主題超額報酬[T→T+h] )`  
  其中超額＝主題窗報酬 − 同窗 TAIEX（與現有 RS 定義一致）。
- `(k,h) ∈ {5,20,60} × {5,20,60}`（9 格）。
- 輸出：每格的 **mean IC、n_days、IC 的簡單標準誤（樣本 sd/√n）**。純數字，無形容詞、無「顯著」字樣（D10／判讀留給 PO）。
- 可選 `--as-of`；預設用現有 processed 快照最新日。
- **不**寫入 `signal_quality_null.json`；**不**掛上 `refresh`。

**驗收條件。**

1. `uv run marketpulse rank-ic`（或定名）印出 3×3 表；九格皆有 mean／n／se。
2. 同一輸入跑兩次，九格數字逐字元相同（決定性）。
3. 測試：人造三主題、已知單調關係 → 對應格子 IC 接近 +1；打亂橫斷面 → 接近 0（容許小數誤差）。
4. `refresh`／`brief`／`radar` 路徑的 diff 不因本命令而變（本命令不寫那些產物）。

**會動到的檔案。**`marketpulse/quality.py`（或鄰近純函數）、`marketpulse/cli.py`、`tests/test_quality.py`（或新 `tests/test_rank_ic.py`）。

**本項不做。**不改 RS 定義、不 composite 多窗 IC、不依 IC 自動調窗口。

### DO-2 — `above_count` 全 NaN 列回 NaN　[L1・交付正確性]

**背景。**backlog：序列起點缺 SMA20 時 `sum(skipna=True)` 把全 NaN 塌成 0，與 breadth 假 0 同類。

**做什麼。**當列上參與的 `above` 全為 NaN 時，`above_count`（及若同邏輯的 breadth 衍生）應為 NaN，不是 0。有任何非 NaN 時維持現況（skipna 求和）。

**驗收條件。**

1. 單元測試：全 NaN 列 → `above_count` 為 NaN；混有 False/True → 計數正確。
2. 不改 rank／RS20 公式本體。

**會動到的檔案。**`marketpulse/calc.py`、對應測試。

### DO-3 — Brief／radar 持續性旁的 B＋C 短註　[使用]

**背景。**文件已寫 B＋C；產品 `quality_line` 只有數字。使用者打開 brief 仍可能把 +2.8σ 讀成「月排名很穩」。

**做什麼。**在既有持續性／虛無那一行**下方或同行尾**加一句**固定中文短註**（字面鎖定，不得依數字改寫）：

> 月尺度：可偵測≠穩定；短端遠強於長端；凍結成分偏高估（D6）。

數字格式維持 004 的 σ＋超越計數。無新閾值、無顏色語義新增。

**驗收條件。**

1. `brief` 輸出含上述短註原文。
2. 測試断言短註字串存在；缺 null baseline 時短註仍可出現或明確省略策略寫進 evidence（二選一，選定後測死）。
3. 目視：貼一段實際 brief 片段進 evidence（「人讀得懂」屬目視，不以綠燈代替）。

**會動到的檔案。**`marketpulse/product.py` 及／或 `quality.py` 的 `quality_line`；若 radar 共用則一併；測試。

## 兔子洞

- 前向報酬與 RS 窗對齊時的 off-by-one／含未來：必須 as-of 嚴格，T 日只用 ≤T 資料算 RS；前向窗 (T, T+h]。
- 主題數少（11）→ IC 噪音大：這正是買資訊要看見的，不要為了好看平滑。
- 動 `calc.py` 時勿順手重構 rolling／空窗邏輯。

## 本輪明確不做

- 換 primary／IBD 加權／Elo／RRG／residual momentum 當主序
- as-of 成分股、雙池（Q5／Q6）
- `arch.bootstrap`、除權息方法變更
- 第二層 burst／PTT 掃描
- merge 進 `dev`（本輪分支上實作；merge 另候 PO）

## 這裡容易踩到的契約紅線

- **不做綜合評分**：九格 IC 並列，不合成「總分」。
- **不用未來資料**算當日 RS。
- **D10**：短註固定文案；不依 IC 大小改措辭。
- **R3**：不因故事改第一層數字。

## 權限邊界

- 分支：`sprint/005-horizon-ic`（自 `dev@42c3522`）。
- 可碰：上列模組與 `docs/sprints/005-*`、`docs/product/backlog.md`（掃除已完工列）。
- 不可碰：`themes/v1.yaml`、顏色／簽章常數、第二層 schema、`dev` merge。
- 規劃端本輪**兼**實作（使用者明示要求端到端）；報告須註明帽子切換。

## 回報時必須附的物證 → `docs/sprints/005-evidence.md`

- 每項 DO 的 commit hash
- `uv run pytest` 實際摘要行
- `git diff dev --stat`
- DO-1：實際 3×3 表輸出
- DO-2：測試名與失敗→通過的對照（或新測片段）
- DO-3：brief 片段含短註

## 留給實作者的未決問題

1. 子命令英文名：`rank-ic` vs `validate-ic`？預設用 `rank-ic`。
2. DO-3 短註在「無 null baseline」時：預設仍顯示（它是尺度讀法，不是虛無數字）。
