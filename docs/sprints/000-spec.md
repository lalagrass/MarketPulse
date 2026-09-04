# Sprint 000 — 文件整地

狀態：已完成 2026-09-04（由 Cowork 端直接執行，非交給 Claude Code；本輪零程式碼變更，無測試可跑）
契約：CLAUDE.md 與 docs/coding-contract.md 全數適用
層次：不適用（本輪不碰產品程式碼）

## 目標

把「已完成的建置期指令」與「現行規範」分開，讓後續讀文件的 agent 不會把過期的
STOP 條款當成現行法律套用。

## 背景

MVP 的 Definition of Done（design-v0.2.md §26）14 項全數達成，但文件仍以
「還沒蓋完」的語氣書寫：

- design-v0.2.md §26 結尾："At this point, stop. Do not add features before using the product."
- coding-contract.md §13 "Agent stop condition ... STOP."
- coding-contract.md §2 "Do not implement the whole architecture."
- coding-contract.md §10 Slice A/B/C/D "Then stop."

任何 agent 今天讀到的指令是「停下來，不要加功能」。這些規則不是錯的，是過期的。

## 要做的

### 1. coding-contract.md 加狀態標註
- 做什麼：在文件開頭加狀態區塊；在 §2、§10 標註已完成日期；§13 改為
  「MVP 建置期的停止條件（已達成，歷史保留）」，並說明後續工作由 sprint spec 管轄。
- 驗收條件：任何人讀 §13 不會再認為「現在應該停止開發」；原文語句保留可追溯。
- 會動到的檔案：docs/coding-contract.md
- 必須新增的測試：無（純文件）

### 2. design-v0.2.md §26 標註 DoD 已達成
- 做什麼：在 §26 開頭加註達成日期與佐證（哪些指令／檔案證明各項成立）。
  保留 §26 原文不刪。
- 驗收條件：讀者能看出 14 項全數達成，且「stop」那句被明確標為建置期指令。
- 會動到的檔案：docs/design-v0.2.md
- 必須新增的測試：無

### 3. 統一 sprint 報告的位置
- 做什麼：SPRINT_REPORT.md（根目錄）→ docs/sprints/past-momentum-visibility.md；
  docs/handoff-po.md → docs/sprints/past-refresh-ops.md；
  新增 docs/sprints/README.md 說明編號慣例。
- 驗收條件：根目錄不再有 sprint 報告；兩份舊報告可從 docs/sprints/README.md 找到。
- 會動到的檔案：SPRINT_REPORT.md、docs/handoff-po.md、docs/sprints/README.md
- 必須新增的測試：無
- 註：已確認這兩個檔名未被任何程式碼或文件引用。

### 4. CLAUDE.md 檔案位置表更新
- 做什麼：更新「File Locations & Conventions」反映新路徑；加入 docs/sprints/ 與
  docs/product/ 的說明。
- 驗收條件：表中所有路徑實際存在。
- 會動到的檔案：CLAUDE.md
- 必須新增的測試：無

### 5. 建立待決清單
- 做什麼：新增 docs/product/open-questions.md，記錄本輪發現但屬於「決定」而非
  「事實」的項目，交由 sprint 001 的 bootstrap 處理。
- 驗收條件：清單至少涵蓋下列四項，每項寫明衝突所在與檔案行號。
- 會動到的檔案：docs/product/open-questions.md（新增）

## 本輪明確不做

- **不解決任何矛盾，只記錄。** §11 的 RRG 條款、§3 的 pandas-ta-classic 漂移、
  §8 的還原股價禁令、L2 前瞻報酬是否解禁——這些都是決定，不是事實，
  屬於 sprint 001 的 bootstrap。理由：整地的價值在於它不需要判斷；
  一旦混入決定，就需要 PO 拍板，那就不是整地了。
- **不寫兩層架構（數學層／故事層）進 CLAUDE.md。** 同上，那是產品決定。
- **不建立 non-goals.md。** 那是 sprint 001 bootstrap 的第一件事，需要逐條確認。
- **不碰 marketpulse/、tests/、themes/。** 本輪零程式碼變更。
- **不刪除任何既有內容。** 只增加標註與搬移。舊語句保留可追溯。

## 這裡容易踩到的契約紅線

- §12「避免推測性抽象」：本輪不新增任何抽象，只動文件。
- 本 repo 沒有 main 分支，主幹是 dev。「不動主幹」在此指不動 dev。

## 留給實作者的未決問題

無。本輪全部是機械性整理。
