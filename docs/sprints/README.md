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
| `004` | 第二層：支線／事件列／回頭日期，籃子強弱面板 | 已完成 2026-09-05・成果已在 `dev` |
| `005` | 前向 Rank-IC；above_count NaN；B＋C 短註 | 已完成 2026-09-06・已在 `dev` |
| `006` | IC 每格配循環位移虛無（取代 se）；(20,20) 標註；above_count 空路徑 | 已完成 2026-09-06・已在 `dev` |
| `016` | 讓錯誤自己出聲：`acceptance-check.sh`、`_ljust` 溢出截斷、面板兩處位置修正 | **待實作** 2026-09-09・spec `016-spec.md`・分支 `sprint/016-make-errors-loud` |
| `015` | 價格重設要出聲：籃子窗內有斷點就標記、斷點分回得去／回不去、F8 判準修正 | 已完成 2026-09-09・三項全過、G5 通過・驗收見 `015-review.md`・已併入 `dev@480e869` |
| `014` | 第二層：一則故事三個籃子（成真／反面／誰贏都賺）、回頭日期拆日期與條件 | 已完成 2026-09-08・三項全過・驗收見 `014-review.md`、實作端回報見 `014-report.md`・**待併** |
| `013` | — | **NO-SPRINT** 2026-09-08・產品連續兩輪沒被使用（`design-v0.2.md` §26）。唯一動手：`data/raw/calendar/` 納入版控。重開條件見 `013-no-sprint.md` |
| `012` | `Momentum` 欄寬、檔位表取代 `LIMIT_MOVE`、休市判定改讀官方休市表 | 已完成 2026-09-08・DO-1／DO-2 通過，DO-3 的「N 明顯小於 32」未達成（N=18，**spec 的錯**：TWSE 端點只給當年度）・已併入 `dev@8318d58`，見 `012-report.md` |
| `011` | 不可能的單日報酬（緯穎斷點）、休市與抓取失敗不再長得一樣、Momentum 可還原 | 已完成 2026-09-07・三項全數通過・**已由規劃端併入 `dev@4225531`**（PO 授權），見 `011-report.md` |
| `010` | 品質行改寫成讀得懂的、radar 標頭補新鮮度、2×2 的「被講過」定義統一 | 已完成 2026-09-06・已由規劃端併入 `dev@874302d`，見 `010-report.md` |

**010-report 已加註兩則更正（2026-09-06）：**「09-05 週五是交易日」是錯的（09-04 才是週五），
以及「TPEx 89 天補齊排 011」指向的是 sprint 004 已完成的工作。詳見 `011-evidence.md` 第 1 節。
| `009` | 品質行改印樣本平均值（B6）、尚未生效的 narrative 告知、F4／F5／F6 | 已完成 2026-09-06・已由 PO 併入 `dev@566ba37` |
| `008` | narrative `theme_ids`、故事進度顯示、007 的 F1／F2／F3 收拾 | 已完成 2026-09-06・**已由 PO 併入 `dev@2d92270`**，見 `008-report.md` |
| `007` | 敘事覆蓋進 brief／radar、revisit 到期提示、文件矛盾掃除 | 已完成 2026-09-06・**已由規劃端併入 `dev@537142c`**，見 `007-report.md` |
