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

**分支殘骸（2026-09-05 查證，同日更正一次——見下）：**
`sprint/003-{uncertainty,do4-null-range,do5-null-guard,do6-stale-artifact}` 是一條線性鏈，
`uncertainty → do4 → do5 → do6`，前三條都是 `do6` 的祖先（`git merge-base --is-ancestor` 確認，
且 `git rev-list --count do6..<branch>` 全為 0）。**鏈尾 `do6` 的產品碼與測試與 `dev` 逐字元相同**
（`git diff dev sprint/003-do6-stale-artifact -- marketpulse/ tests/` 為空）。
`dev` 的 `4ea9a02` 是把 DO-1…DO-6 整條鏈**合併成單一 commit** 落下的，所以沒有一條能 fast-forward。

**更正：**本節初版寫「四條的產品碼與測試與 `dev` 逐字元相同」。**那句話是錯的，只有 `do6` 是。**
其餘三條對 `dev` 的 `marketpulse/`＋`tests/` diff 分別是 493／372／211 行——
但每一行都是 `dev` 後來修訂過的**舊版本**（`uncertainty` 缺 DO-4 的位移範圍修正、
`do4` 再缺 DO-5 的 `MIN_RETAINED_FRACTION` 護欄、`do5` 再缺 DO-6 的 `NULL_METHOD_VERSION`），
加上一個過期的 `_null_payload` fixture。**沒有任何一條帶著 `dev` 缺的東西。**
初版的錯在於：只驗了鏈尾就寫成四條都驗過。**正確的判準是「鏈尾對 `dev` 為空 ＋ 其餘三條是鏈尾的祖先」**，
不是「四條各自對 `dev` 為空」——後者在 `dev` 用合併 commit 落地時本來就不可能成立。

文件方向則是反的：分支上的文件比 `dev` **舊一輪**，還帶著已被 DO-4/DO-5 撤回的
「百分位 81、與雜訊不可區分」（`do6` 的 `CLAUDE.md:21`、`README-MVP.md:41`，`dev` 兩處都已改掉）。
**併它們會讓文件倒退**。正確動作是刪分支，不是 merge。
`scratch/fetch-2025-gap` 另有一顆 16.6MB 的 TWSE 2025 缺口 tarball（由 GitHub Actions 出口抓取，
繞過 307），那顆要解進本機 `data/raw/` 而不是留在 git 裡。

## 索引

| 編號 | 主題 | 狀態 |
|---|---|---|
| `past-refresh-ops` | 日常 refresh、空回應快取修正 | 已完成 |
| `past-momentum-visibility` | 雷達動能狀態、排名歷史 | 已完成 |
| `000` | 文件整地：分離已完成的建置期指令 | 已完成 2026-09-04 |
| `001` | 訊號品質三數、breadth 修正、脈絡層結構 | 已完成 2026-09-04 |
| `002` | 長尺度持續性檢定、多時間窗 RS 並列 | 已完成 2026-09-05 |
| `003` | 虛無基準進 Brief、資料窗回補至三年、工程債一格 | 已完成 2026-09-05・成果已在 `dev` |
| `004` | 第二層：支線／事件列／回頭日期，籃子強弱面板 | 待實作 |
