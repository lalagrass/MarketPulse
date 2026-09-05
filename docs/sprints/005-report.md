# Sprint 005 — 規劃報告

## 上輪驗收

見 `docs/sprints/004-report.md`。004 三項 DO＋追加顯示／文件皆通過；`dev@42c3522`。

## 使用？

`narratives/2026-09-06.yaml` 有新快照 → 第二層有被用。L1 日常使用仍薄。未觸發「兩輪沒用 → 強制只用 ENG」；仍保留一格給使用（DO-3 短註）。

## 本輪改變想法的發現

1. **「換更好的 rank」再查一次仍不成立。** 市面／OSS（多窗 composite、IBD RS、12−1、residual、Elo）主序仍是相對報酬→橫斷面排名；改進多在輸入或策略層。**強化**「問題在 20 日尺度」。詳見對話研究；backlog 盤點節追加 2026-09-06 附註。
2. **缺的是前向 IC，不是新指標。** Persistence 是「排名跟自己的過去」；Rank-IC 是「排名跟未來超額」——同一尺度敘事的另一隻腳。
3. **backlog 待排仍掛已完工項** → 文件負債會害下一輪重複評估。

未改變：不綜合評分、主排名 RS20、B＋C 讀法、Q5／Q6 本輪不碰。

## Appetite

見 spec。模組 ≤4、無新相依、只動 L1、不回補。

## DO / WON'T / UNKNOWN

### DO

| # | 項 | 層 | 買資訊／交付 | 擠掉什麼 |
|---|---|---|---|---|
| 1 | 前向 Rank-IC 3×3 | L1 | 買資訊 | 擠掉「再研究換 rank」與 IBD 加權實驗 |
| 2 | above_count 全 NaN→NaN | L1 | 交付正確性 | 擠掉本輪動 bootstrap／除權息 |
| 3 | Brief B＋C 固定短註 | 使用 | 交付可讀性 | 擠掉新 UI／RRG |

### WON'T（摘要；細則進 non-goals／backlog 附註）

- 換 primary、composite、Elo、RRG、12−1 策略化
- as-of 成分／雙池
- 依 IC 自動改窗口（D10）

### UNKNOWN（≤2）

1. **Rank-IC 在 11 theme 上 mean IC 的量級會是多少？**  
   一錘定音：DO-1 跑出的表。回頭：本輪 evidence 貼表之後立刻判讀（005 收尾或 006 開場）。
2. **短註會不會讓人以為系統在「保證」衰減？**  
   一錘定音：PO 目視 brief 一週。回頭：2026-09-13。若誤導 → 下一輪改文案或移到 `--help`／文件 only。

## 規則質疑（本輪一條）

挑 **「σ 與百分位一致性自動檢查」待排 ENG 項**（起因：兩次虛無污染靠人工發現）。

```text
條文：應自動檢查 σ 距離與百分位是否一致
起因：sprint 003 回補驗收；污染虛無露出 0.59σ↔81 等不一致
重看：顯示層改為 σ＋超越計數之後（004 follow-up）
```

**物證：**百分位已離開 brief/radar 顯示；一致性檢查的對象（顯示用 percentile）已降級。  
**詮釋：**該 ENG 項的產品理由變弱；保留為「JSON 內 percentile 仍寫入時的開發期斷言」可選，但不再佔待排主列。  
**決定：**從 backlog 待排**刪除**（過期掃除），改在 WON'T／附註寫「若再顯示 percentile 再掛回」。不升格為規則。

## 等你拍板

本輪使用者要求規劃後**直接實作**，下列以預設推進（可事後撤）：

1. **是非：**採用 `rank-ic` 子命令名？預設是。
2. **是非：**DO-3 無 null 時仍顯示短註？預設是。
3. **判讀（延後到 evidence）：**IC 表出來後，是否把「長端打折」從文件升成 Brief 更長說明——等數字，不在開場拍板。

## 交給指令

在分支 `sprint/005-horizon-ic` 實作 `docs/sprints/005-spec.md` 三項 DO；物證寫入 `005-evidence.md`；不 merge `dev`。

## 帽子切換（誠實）

同一代理先寫本報告／spec（PO），再實作（tech lead），最後用 evidence 做 PO 驗收＋retro。skill 原設計分家；本輪依使用者明示覆寫，並在 retro 檢討代價。

---

## PO 驗收（2026-09-06，同一代理·規劃帽）

物證來源：`005-evidence.md`；本機複跑 `uv run pytest` → **140 passed**；`rank-ic`／`brief` 輸出與 evidence 一致。

| DO | 判定 | 說明 |
|---|---|---|
| DO-1 Rank-IC | **通過** | 3×3 表、決定性測試、合成 ±1／近 0；未掛 refresh；未寫 null JSON |
| DO-2 above_count | **通過** | 全 NaN→NaN；混合列仍計數；`min_count=1` |
| DO-3 B＋C 短註 | **通過** | 字面鎖定；brief 第二行可見；radar `pre-line` |

### 第三類（spec 沒要求）

- radar CSS `white-space: pre-line` — 合理，否則 HTML 吃掉換行。

### 沒做到／偏差

- 無功能缺口。forward excess 實作選「T+h 當日的 `rs_h`」＝窗 (T, T+h]，與 spec 一致。
- evidence 初稿 commit 表寫「*(this commit)*」；實際 hash `c17b1e4`。

### UNKNOWN-1 關閉（數字到了）

```text
k\h     5        20       60
5    +0.034    +0.084    +0.071
20   +0.099    +0.140    +0.161
60   +0.085    +0.140    +0.195
```

（n≈287–397；se≈0.018–0.022）

**物證：**對角線隨天期上升；短→短近 0，長→長約 +0.20。  
**詮釋（三種讀法）：**  
A「長窗 RS 比較有前向內容」— 成立條件：接受 11 theme、restated 成分下的小樣本 IC。  
B「IC 小，不能當預測產品」— +0.2 仍弱；與「不做策略／不依 IC 改 primary」一致。  
C「與 persistence 不矛盾」— persistence 量的是名次自相關衰減；IC 量的是 RS 與未來超額。短端名次穩≠短端有預測力。  
**PO 傾向：B＋C。** 不升格 Brief 長文；不改 primary。選錯代價：寫成 A 會滑向「改主窗／做輪動策略」。

### 驗收決定

1. 005 三項 DO **接受**；分支留 `sprint/005-horizon-ic`，**不自動 merge**（等明示）。  
2. 橫斷面「換 rank」維持結案。  
3. UNKNOWN-2（短註是否誤導）回頭日 2026-09-13 仍有效。
