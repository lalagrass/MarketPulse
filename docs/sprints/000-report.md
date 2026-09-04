# Sprint 000 報告 — 文件整地

日期：2026-09-04　分支：`sprint/000-doc-hygiene`　對應 spec：`000-spec.md`

## 做到的

1. **coding-contract.md 加狀態標註** — 開頭新增 STATUS 區塊，說明 MVP 已完成、
   哪些條款仍然有效（§1、§3–§9、§12）。§2、§10、§13 標記
   *[BUILD PHASE — COMPLETE]*，§13 改為「已達成的建置期停止條件」並指明後續由
   sprint spec 管轄。原文全部保留在引用區塊內。
2. **design-v0.2.md §26 標註 DoD 已達成** — 加註達成日期與佐證。原文未刪。
   另註明「先用產品再加功能」那半句不是建置期限制，仍然成立。
3. **統一 sprint 報告位置** — `SPRINT_REPORT.md` → `docs/sprints/past-momentum-visibility.md`；
   `docs/handoff-po.md` → `docs/sprints/past-refresh-ops.md`；新增 `docs/sprints/README.md`。
   兩檔均以 `git mv` 搬移，歷史保留。搬移前已確認無任何程式碼或文件引用。
4. **CLAUDE.md 檔案位置表更新** — 補上 `docs/reuse-plan.md`、`docs/sprints/`、
   `docs/product/open-questions.md`；新增分支慣例與 MVP 狀態說明。
5. **建立待決清單** — `docs/product/open-questions.md`，Q1–Q4。

## 沒做到的

無。spec 五項全數完成。

## 做了但 spec 沒要求的

**一項，需要揭露：** spec 撰寫時假設主幹是 `main`。實際檢查發現本 repo 只有
`dev`，沒有 `main`。因此在 CLAUDE.md 的檔案位置表下方補了一段分支慣例說明，
並在 `docs/sprints/README.md` 記錄同一件事。這超出 spec 第 4 項的字面範圍
（「更新檔案位置表」），但屬於同一次發現，且不加註會讓後續 sprint 的
「不動主幹」規則指向一個不存在的分支。

## 未提交的既有改動

`README-MVP.md` 在本輪開始前即有未提交改動（新增 "Interpretation Boundary"
一節）。非本輪產出，**已刻意排除在 commit 之外**，保持在工作區。

## 環境限制

本輪由 Cowork 端執行，該環境無法取得 Python，`uv run pytest` 跑不起來。
本輪零程式碼變更，無測試可跑，故不構成問題——但這是為什麼往後的實作
交給本機的 Claude Code。

## 交給 sprint 001

`docs/product/open-questions.md` 的 Q1–Q4 需在 bootstrap 階段逐條決定：
RRG 條款矛盾、pandas-ta-classic 漂移、§8 還原股價禁令、完整回測是否寫入 non-goals。
