# Sprint 記錄

## 編號慣例

- `NNN-spec.md` — 事前寫的規格。由 Cowork 端的 `/marketpulse-sprint` 產出，
  交給 Claude Code 在本機實作。這份檔就是交接物本身；實作只靠它，不靠對話紀錄。
- `NNN-report.md` — 事後寫的結果。做到的、沒做到的、做了但 spec 沒要求的。
- `past-*.md` — MVP 建置期的報告，寫在編號制度建立之前，未回溯編號。

## 流程

```
Cowork  /marketpulse-sprint   → 寫出 NNN-spec.md
Claude Code（本機）            → 讀 spec，在 sprint/NNN-<slug> 分支實作
Cowork  下一輪階段 0           → 對照 spec 驗收，寫 NNN-report.md
```

主幹是 `dev`（本 repo 無 `main`）。sprint 分支不自動併入，由 PO 決定。

## 索引

| 編號 | 主題 | 狀態 |
|---|---|---|
| `past-refresh-ops` | 日常 refresh、空回應快取修正 | 已完成 |
| `past-momentum-visibility` | 雷達動能狀態、排名歷史 | 已完成 |
| `000` | 文件整地：分離已完成的建置期指令 | 已完成 2026-09-04 |
| `001` | 訊號品質三數、breadth 修正、脈絡層結構 | 已完成 2026-09-04 |
