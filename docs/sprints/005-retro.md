# Sprint 005 — Retrospective

日期：2026-09-06  
分支：`sprint/005-horizon-ic`  
帽子：同一代理兼任 PO → tech lead → PO 驗收（skill 預設分家被使用者明示覆寫）

## What decision was good?

1. **不開「換 rank」sprint，改買 Rank-IC。** 用一張 3×3 關掉 UNKNOWN，比再盤一輪指標便宜且可複核。
2. **Appetite 鎖死：無新相依、不改 primary、不碰 L2。** 實作沒有滑出範圍。
3. **DO-3 用固定字串而非依數字改寫。** 守住 D10；驗收成本低。

## What assumption was wrong?

1. **潛意識把「短端 persistence 強」讀成「短端比較有用／有預測」。** IC 表顯示短→短近 0、長→長較高——兩個統計量回答不同問題。文件／短註仍正確（談的是名次結構衰減），但口頭「短端信」之後要補一句「信的是結構穩，不是前向 IC」。
2. **以為 skill 分家在本環境可硬遵守。** 使用者要端到端時，分家變成假的；應在開場就寫進報告（已寫），並接受驗收偏差風險。

## What planning ceremony was unnecessary?

- 完整階段 1 平行多角色發散：本輪範圍已被 004 數字＋rank 再研究錨定，縮短是對的。若硬跑 12 候選只會重寫 WON'T。

## What rule prevented useful work?

- 無。`quality.py` 可碰；無新套件限制沒擋到 Rank-IC（Pearson-of-ranks 即可）。

## What rule failed to prevent bad work?

- **無嚴重壞帳。** 需盯：同一代理自驗收——用 evidence 字串＋複跑 pytest／CLI 降低自賣自誇，但無法替代第二雙眼睛。下次若有爭議判讀（如本輪 IC），應把「判讀題」留到使用者拍板而非 PO 自裁傾向（本輪 B＋C 已寫傾向，merge 前仍可翻）。

## Process — 帽子合併的代價

| 代價 | 緩解 |
|---|---|
| 規劃時已預設實作路徑，發散變窄 | 開場寫明「範圍已被前輪錨定」 |
| 驗收者＝作者 | evidence 強制貼實際輸出；複跑命令 |
| skill「不寫產品碼」條文名義被破 | 報告誠實註記覆寫；不偷偷改 skill |

## Product takeaway

- Persistence 梯度 → 讀**名次結構**隨天期衰減。  
- Rank-IC 矩陣 → 讀**前向關聯**在本樣本上隨天期略增且絕對值仍小。  
- 兩者一起：**不要用短端穩去推短端可預測；不要用長端一點 IC 去換 primary。**

## Next

- PO 明示後再 merge `sprint/005-horizon-ic` → `dev`。  
- 2026-09-13 回看 Brief 短註是否誤導（UNKNOWN-2）。  
- backlog 已掃一輪假待排；as-of 成分／Q5／Q6 仍開。
