# 對 `repo-review.md` 的回覆（2026-09-07，規劃端）

**這份不是 sprint spec。**它做三件事：查證那份 review 的事實、把它的處方對照 repo 現有機制、
以及把它引出來的問題拿去外面找現成解。**沒有讀過的東西不寫。**

---

## 1. 那份 review 讀的是舊的 repo

| 它的說法 | 現況 | 差在哪 |
|---|---|---|
| 「repo 有 18 commits」 | `git rev-list --count dev` = **149** | 它讀的是 GitHub 上的 `origin/dev`，而本機 `dev` 領先 **19 個 commit**（`3be90b8` → `aa61183`） |
| 「sprint index 已一路到 009」 | 本機已完成 **010、011**，兩輪都已併入 `dev` | 010／011 從未 push，它看不到 |
| 「持續性 k=20 = 0.282」 | 367 天樣本上是 **0.1404**（+2.84σ） | 那個 0.282 是 141 天樣本的舊值，中間經 003 DO-4 撤回一次、004 重測一次 |
| 「Definition of Done 說 stop，所以不要再加」 | `design-v0.2.md:1005-1007` 已註明那是**建置期**停止條件，2026-09-03 達成 | 它引的是被註銷的那半句 |

**最重要的一條：**它的核心結論是

> 「不要 Sprint 010 又繼續加研究指標。改做 product usability / data quality visibility。」

而 010 的標題是「把已經算出來、但沒有送到畫面上的東西接上去」（三項全是顯示層，零新計算、
零新相依），011 的標題是「資料在說謊的時候，畫面要出聲」。
**它建議的那一輪，已經做完兩輪了，而且是在它寫這份 review 之前。**

---

## 2. 它開的處方，repo 裡已經有更嚴的版本

它要求產出 `PRODUCT_CORE.md` / `RESEARCH_LAB.md` / `SPRINT_CONTRACT_vNext.md`，
並把所有東西標成 CORE / RESEARCH / FREEZE。逐條對照：

| review 的處方 | repo 裡對應的東西 | 誰比較嚴 |
|---|---|---|
| 三層 Signal / Interpretation / Research，第二三層不得改第一層 | **R3**（第二層不得改變第一層的數字）＋ **D2**（rank-ic 是診斷不進產品） | repo。R3 還附了一個**具體反例**（010 階段 1 那個「程式自動判 confirmed 寫回 YAML」的提案，已駁回） |
| Interpretation 層只能解釋 | **D16**：display-only 豁免收窄成「讀者要能從同一列可見數字還原出標籤，否則不顯示」 | repo。review 只說「不能改第一層」，D16 多擋了「四個輸入塌成一個無法還原的判決」 |
| 不做 RRG / ML / composite / 個股建議 / 完整回測 | **D3 / D9 / R1 / D5 / D2**，每條都寫了「為什麼不做」 | 平手，但 repo 的每條附理由與**重看日期** |
| 「每一輪都向上看 Product Goal，不要只向後看上一 sprint」 | 每輪 spec 的 **Appetite**（可動檔案、不新增相依／資料／計算）＋ **每輪質疑一條規則** | repo。它是可執行的儀式，不是一句原則 |
| 「Sprint Contract vNext」 | `non-goals.md` 的**規則 vs 預設值**帳：`條文／起因／物證／決定／重看` 五欄 | repo。review 沒有「重看日期」這一欄，而那正是防止規則只長不縮的機制 |
| Sprint archaeology（每輪加了什麼、是否保留） | **沒有。**見第 3 節 | review |

`docs/product/` 底下三個檔（`non-goals.md` 270 行、`backlog.md` 253 行、`open-questions.md` 211 行）
review 一次都沒引用。它不是判斷錯，是**沒讀到**——那三個檔在 `origin/dev` 上是有的，
但 GitHub 的目錄瀏覽不會主動打開它們。

---

## 3. 它說對、而 repo 裡確實沒有的一件事

**Sprint archaeology。**目前每輪有 `NNN-report.md` 的自省，也有 `skill-retro`，
但沒有一張橫著看的表。而橫著看才看得到這個 pattern：

```text
009  spec 的前提寫錯（「敘事是全表唯一沒有欄寬的欄」）      → 規劃端
010  兩則更正（09-05 不是週五；TPEx 89 天指向已完成的工作）  → 規劃端
011  DO-1 用錯了尺（±10% 看不見 3–8% 的除權息）             → 規劃端
011  沒把 Momentum 欄寬寫進 spec，讓 DO-3 惡化了一條舊債     → 規劃端
```

**連續三輪，出錯的都是規劃端的 spec，不是實作端的 code。**
每一輪的 report 都誠實寫了，但寫在四個不同的檔裡，所以沒有人看到它是一條線。

這一條值得做，但**它不是一輪 sprint**，是收尾時多寫一張表。
review 提議「Sprint 010 — Process Reset」的規模是錯的：reset 的產物 repo 已經有了，
缺的只是這張表。

---

## 4. 它說錯的地方

**「把 spec 壓到 100～150 行」——開錯藥。**
011 spec 是 199 行，三項全數通過；010 是 222 行，三項全數通過。
真正出錯的四次（上表）沒有一次的成因是篇幅，全部是**spec 對現況的事實宣稱沒有查證**。
正確的處方不是砍字數，是「spec 裡每一句對現況的宣稱都要帶 `檔名:行號`，且那個行號要被驗過」。
repo 的 spec 其實已經在這樣寫（`quality.py:96`、`data.py:386`、`radar.py:154-163`），
只是**沒有機制去驗那些行號是真的**——009 那句錯誤宣稱就是這樣過關的。

**「research gravity」方向對，但 repo 的偏差是反的。**
`backlog.md` 自己記著：`[ENG]` 項目三輪 sprint 進 DO 的次數是 **0**，因為進場規則
（要講得出擠掉了什麼）讓 ENG 在 `[L1]` 面前永遠輸。處理方式是「DO 固定保留一格給 ENG」。
所以研究不是在無限膨脹，是工程債在被結構性擠掉——這一條 review 完全沒看到。

---

## 5. 外面找到的東西（四項，兩項建議採用）

### 5.1 交易日曆：**採用官方 API，不裝套件**（最高價值）

**問題。**011 DO-2 的「官方休市 vs 抓取失敗」判定掛在**檔案 mtime**（`data.py:357-367`）。
32 個「官方休市」的判定全部來自 2026-08-31 那次批次回補留下的 mtime，
一次 `cp -r`／備份還原就會同時失真且不出聲（`011-report.md` §2.2）。

**查到兩條路：**

| 來源 | 授權／條款 | 判定 |
|---|---|---|
| TWSE 官方「市場開休市日期」JSON<br>`https://www.twse.com.tw/rwd/zh/holidaySchedule/holidaySchedule?response=json&yy=2026` | 官方、免費、與現有 EOD 同源 → **過 D13** | **採用。**已 fetch 驗證：`stat`／`queryYear`／`total`（2026 年 27 筆），每筆有 `date`／`名稱`／`說明`（例：`2026-01-01 中華民國開國紀念日 依規定放假1日`）。權威來源，mtime 降為 fallback |
| [`exchange_calendars`](https://github.com/gerrymanoim/exchange_calendars) Apache-2.0，活躍，1.11 起有 **XTAI** | 開源、可裝 | **不裝。**它把颱風假與春節加班 hardcode 成 list，而**最後的明確日期只到 2026-02**。你們 `2026-07-10` 那個颱風休市它結構上就會漏。現成實作存在，但它的資料來源比你們能直接拿到的那個差一階 |

**附帶更正：**`backlog.md` 那條「radar 新鮮度改成距今差幾個交易日」被降級為 UNKNOWN，
理由之一是「研究證實 `pandas_market_calendars` 無台灣日曆」。**那句話對
`pandas_market_calendars` 成立，但當時漏了兩條路**（官方 API、`exchange_calendars` 的 XTAI）。
那條的技術前提現在成立了，剩下的是它自己那個「沒有真實案例」的問題。

### 5.2 漲跌停檔位表：**採用，六行 dict，不裝套件**

`backlog` 的「A4 那一行改用實際漲跌停價比對」與 011 §6 的「用規則的完整形式，
不要用它的簡化版」要的就是這張表。查到並驗證了完整規則：

```text
最小跳動單位（普通股）
  價格 < 10        0.01
  10 ≤ 價格 < 50   0.05
  50 ≤ 價格 < 100  0.10
  100 ≤ 價格 < 500 0.50
  500 ≤ 價格 <1000 1.00
  價格 ≥ 1000      5.00

漲停價 = 前參考價 × 1.1，**無條件捨去**到該價位帶的檔位
跌停價 = 前參考價 × 0.9，**無條件進位**到該價位帶的檔位
  例：前收 73.20 → 上限 80.52 → 80.50；下限 65.88 → 65.90
```

檔位表一樣是交易所規則，不是 D10 的把手（011 §6 的判準已涵蓋）。
**預期效果：**1644/1909（86%）那批 `0.10 < |r| ≤ 0.101` 的偽陽性應該幾乎全部消失，
265 筆真的超出漲跌停的留下，6669 不再被埋。
不裝套件：`twstock`（MIT）沒有這個功能，FinMind 的相關資料屬 D13。

### 5.3 §27 那張「月份 → 當月贏家」圖：**不裝套件**

查到 `bumplot`、`pybumpchart`、`bump-plot-python` 三個 bump chart 套件，
全部是 matplotlib 的薄包裝，而 `rotation_latest.png` 已經是 step-plot。
§3「先找現成實作」在這裡的合格結論是**「找了，不裝」**——與 010 那次離散度套件的結論同型。

### 5.4 流程：[`spec-kit`](https://github.com/github/spec-kit)（MIT，活躍）**不導入，只抄一件事**

它的形狀跟你們的幾乎一樣：`constitution`（治理原則）→ `specify` → `plan` → `tasks` → `implement`，
外加 `analyze`（跨產物一致性與涵蓋率檢查）與 `clarify`（實作前先解含糊處）。

- **它的 constitution ≈ 你們的 `non-goals.md`**，但它沒有「起因／物證／重看日期」，
  也沒有「每輪質疑一條規則」——**它的 constitution 只會長不會縮。你們的會。**
- **它有而你們沒有的只有一件：spec 送進實作之前的機器檢查。**
- **判定：不導入工具**（會製造第二個 source of truth，`CLAUDE.md` 明文禁止），
  但把 backlog 那條 `scripts/acceptance-check.sh` 的範圍**往前推**：
  除了驗收後的機械 grep，再加一條 spec 出手前的檢查——
  **spec 裡每一個 `檔名:行號` 的宣稱，腳本去確認那個檔那個行號存在且內容相符。**
  這一條正好擋住第 4 節那四次錯裡的兩次（009 的欄寬前提、011 的 TPEx 指向）。

---

## 6. 我建議的 012（不是拍板，是提案）

| 格 | 項目 | 來源 |
|---|---|---|
| 1 | `Momentum` 欄寬（011 惡化的舊債） | backlog 已標「排 012 第一格」 |
| 2（ENG 保留格） | 交易日曆改用 TWSE 官方 `holidaySchedule`，拆掉 mtime 依賴 | 本文 5.1 ＋ `011-report.md` §2.2 |
| 3 | 檔位表取代 `LIMIT_MOVE = 0.10` | 本文 5.2 ＋ 011 §6 規則質疑 |
| 收尾 | Sprint archaeology 一張表（不佔 DO 格） | 本文 §3 |

**明確不做：**Process Reset 那一輪（產物 repo 已有）、砍 spec 字數（開錯藥）、
導入 spec-kit（第二個真理來源）、裝任何 bump chart 或日曆套件。

---

## 7. 這份 review 值得留著的一句

> 「先不要再讓它變聰明。先讓它變成一個每天真的會想打開來看 30 秒的工具。」

這句跟 `design-v0.2.md:1030` 那句「At this point, stop. Do not add features before using the
product.」是同一件事，而後者在 repo 裡被註明「這半句不是建置期限制，現在仍然成立」。
**兩個獨立來源在同一件事上收斂，這比 review 裡任何一條技術意見都值錢。**
