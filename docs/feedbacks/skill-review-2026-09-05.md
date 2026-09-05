# marketpulse-sprint skill 體檢（2026-09-05）

規劃端自查 + 三份外部 feedback（`sprint-skill-feedback1~3.md`）的評估與查證。
本份未跑測試、未變更任何程式碼。artifact 版本另存於 Cowork。

## 引用查核

逐一以 WebFetch 打開 feedback 引用的 GitHub 連結，**實查 12 個，全部存在且描述與 README 相符**：
SPEC-AGENTS（六動作迴圈、`EVIDENCE.md`）、Spark（Seed/Cross-Pollinate/Synthesize）、
Separate-Then-Together（epistemic isolation）、ideate-core（blind round + 6-3-5）、
Perspectra（CHI 2026「Choosing Your Experts」）、plan-bender（`max_points: 3`）、
adr-tools（`adr new -s`）、SpecDD（Relevance Gate）、ordewell、agora、super-spec、
TerminalSkills/product-discovery。**沒有捏造的 repo。**

**一處事實錯誤：**feedback1 的評分表把 NO-SPRINT 標為「⭐⭐⭐⭐⭐ 已加入」，
但 `grep -rn "NO-SPRINT" .claude/skills/` 為空——現行 SKILL.md 完全沒有這個概念。
它是講過但沒寫進檔案的東西，正是 skill 自己警告過的失效模式。

## 三份 feedback 的共同盲點

它們讀了 SKILL.md，沒讀 `docs/sprints/`。三份約 2300 行，**約七成在改階段 1（發散）**，
但物證說階段 1 是最健康的部分：sprint 001 一輪產出 82 個候選，至今還有 15 個沒消化。
「至少 12 個」從來沒有 binding 過，feedback3 擔心的「被逼出五個垃圾」在本專案沒發生過。

真正壞掉的地方，物證都在 repo 裡：

| 物證 | 位置 |
|---|---|
| spec 行數 80 → 239 → 169 → **616**；report 46 → 104 → 94 → **585** | `docs/sprints/` `wc -l` |
| `narratives/` 只有 `2026-09-04.yaml` 一個檔，是 sprint 001 的 DO 產物，之後零新增 | `narratives/` |
| 上一輪的 `pytest` 摘要「報告與 31 個 commit 訊息裡確實沒有」，003 回頭補跑 | `003-report.md` |
| DO-4/5/6 三條分支全部未併入 `dev`，Q8 開著 | `git branch -a` |
| `data/raw` 321MB → 1.5G，無任何規則提過資料量 | `003-report.md` DO-2 |

**成因診斷（feedback1 §14 抓到症狀但認錯成因）：**它以為 context bloat 來自「讀太多檔」，
其實來自**寫太長**。skill 的兩條規則在打架——「物證而非斷言」要求貼實際輸出，
「使用者的時間預算是五分鐘」要求一頁；前者只約束 `NNN-report.md`，後者只約束發布的 artifact，
**中間沒有人管 spec**，於是 spec 長到 616 行，而階段 0 規定要讀最新一份 sprint。

**唯一一次成功的自我修復在收斂端：**ENG 連三輪進 DO 零次 → 診斷成「規則的副作用而非
優先序判斷」→ 用結構（固定保留一格）而非自制力修掉。那個模式才是這個 skill 值錢的地方。

## 逐項判定

### 採用

- **NO-SPRINT 作為階段 3 的第四個合法結果。**現行三個桶都預設「這輪要做點什麼」。
  缺這個出口，skill 永遠會生出一輪 sprint。而現在正是它該出現的時刻。
- **Appetite（複雜度預算）。**「DO 上限三項」擋不住 003——DO-4/5/6 是*追加*不是新增，
  數量規則對追加沒有約束力。Appetite 是唯一擋得住的：本輪最多動幾個模組、
  要不要新增相依、資料量上限。
- **Rabbit holes 欄位。**成本一行。003 的兩個坑事前寫得出來（TWSE 對 box 出口 IP 的 307、raw 體積）。
- **Context escalation（分級讀取）。**階段 0 現在固定讀九個來源。改兩層：
  *永遠讀* CLAUDE.md、coding-contract、最新 report 的決定段、backlog；
  *觸發才讀* design-v0.2（動到產品意圖）、open-questions（有未決題擋路）、更早 sprint（懷疑重複）。
  **單獨做無效，須配下方「spec 與物證分家」。**

### 改寫後採用

- **Evidence / Interpretation / Decision 三層。**skill 已經有它——「判讀題」四段格式就是。
  缺的是套到*規則變更*上。Q8 已自然長成這形狀（物證 `d7975df` → 詮釋「規則沒被執行」→ 決定降級），
  只是沒有固定欄位。改寫成：**每條規則旁註明「哪一輪、什麼物證、下次何時重看」**。
- **Persona panel + context isolation。**feedback2 開 8 個角色，feedback3 砍到 3–5 個，
  這裡砍到**一個**：只看得到產品輸出（Brief / radar / timeline）、看不到 repo 與 contract 的角色。
  理由不是增加點子（82 個證明夠了），是**它是「使用者從沒用過產品」的鏡像**。功能是驗收，不是發散。
- **Experiment 獨立階段。**概念對，但 `replay`、`validate-signal` 都得先寫 code 才存在，
  多一階段只多一次交接。改成 spec 的一個欄位：**「這項 DO 是買資訊還是交付功能？」**
  買資訊的可以醜、可以丟掉、不必進 `marketpulse/`。
- **0–3 提案 + stop condition 取代「至少 12 個」。**無害，順手改。
  但要說清楚它不修任何實際發生過的問題。

### 不採用

- **DEC-NNN 正式 ADR 檔案系統。**決定已散在四處（SKILL.md / non-goals.md /
  open-questions.md / report），再開第五個是淨損失。`~~Q1~~ 已解決` 已做到 supersede 的八成。
- **固定的 cross-pollination 輪次。**feedback3 自己已推翻 feedback2 這條，同意 feedback3。
- **多輪 debate / 投票 / consensus 分數。**R1 的變體。feedback2 自己也反對。
- **把 skill 拆成薄骨架 + 可插拔工具箱。**方向對，成本高於收益。
  216 行的 skill 不是問題，616 行的 spec 才是。做完下面那條再回頭看這題還在不在。

## 規劃端自己追加的一條（三份 feedback 都沒提）

**spec 與物證分家。**`NNN-spec.md` 與 `NNN-report.md` 正文各壓在 200 行以內，
所有 `pytest` 摘要、`diff --stat`、輸出字串搬到 `NNN-evidence.md`。

階段 0 讀 spec 不讀 evidence，只有驗收那一步才打開 evidence。
這樣「物證而非斷言」與「不要 context bloat」不再打架，
也讓 context escalation 真的有效——否則分級讀取只是把爆炸往後推一輪。

## 等 PO 拍板

1. **（是非）**skill 加入 NO-SPRINT？預設：加，且本輪很可能就該用。
2. **（是非）**spec／report 正文 200 行硬上限、物證另立檔？預設：設。
3. **（是非）**階段 1 只加一個「只看得到產品輸出」的角色，其餘不動？預設：是。
4. **（判讀）**「應該從第二層開始」——見下。

### 判讀題：第二層先做？

**數字。**第二層資料結構 sprint 001 就交付（帶日期 YAML + PIT-safe loader）；
一個月後 `narratives/` 有 1 個檔案。同期 backlog 待排 L1 有 9 項。
第一層可信度在 003 拿到長樣本：k=20 observed 0.107 / null mean 0.034 / percentile 95.8
（709 個交易日，restated）。

**三種讀法。**
(a) 第一層已驗證，skill 的「層次檢查」閘門開了——003 正是那個交付，只是報告沒把它
講成「第二層解鎖」。
(b) 第二層卡的不是程式碼是使用者——sprint 001 的 UNKNOWN「每週手動記錄撐不撐得住四週」
一個月沒回頭看，正是 skill 說的「沒有回頭日期的 UNKNOWN 會消失」的實例。
(c) 第一層還有九項，所以第二層永遠排不進來——跟 ENG 零次進 DO 是同一種結構偏差。

**規劃端傾向 (b)，且 (b) 與 (c) 同時成立。**要做的不是「改從第二層開始」，
是**把第二層那個 UNKNOWN 結案**；結案方式不是寫 code，是連續四週真的填 `narratives/`。
把 EP693 逐字稿放進 `docs/podcasts/` 就是第一次填。

**代價。**選 (a) 直接開發第二層功能：又一輪「做完沒人用」，可逆但再燒一輪。
選 (b) 先手動累積四週：這四週 sprint 沒有新功能——而那正好是 NO-SPRINT 存在的理由。
兩邊都可逆，但 (b) 買到的資訊 (a) 買不到。

---

## 拍板結果（2026-09-05）

PO：「skill 部分的改善不錯，let's update」。

- 是非題 1、2、3 → **全部照預設值採用**，已寫進 skill。
- 判讀題（第二層先做？）→ **未拍板，仍開著。**下一輪階段 0 要先問這題。

skill 本次實際變更（`.claude/skills/marketpulse-sprint/SKILL.md`，215 → 307 行）：

1. 新增「規則帳」——每條規則旁要有 條文／起因／重看 三格；起因填不出來就提議降級。
   merge 那條改寫成規則帳格式當範例。
2. 新增「輸出預算」硬上限表：spec / report 各 200 行，物證另立 `NNN-evidence.md`。
3. 階段 0 改成「分級讀取」：固定讀五樣（含 design-v0.2 只讀 §26–27），其餘按觸發條件。
4. 階段 1 新增「一個只看得到產品輸出的角色」；「至少 12 個」改為停止條件 + 0–3 提案。
5. 階段 2 新增「引用要實際打開過」。
6. 階段 3 新增 Appetite（複雜度預算），置於分桶之前；DO 每項新增
   「買資訊還是交付功能」；新增第四個桶 **NO-SPRINT**；層次檢查加註「這道閘門會開」。
7. 階段 4 spec 範本新增 Appetite 與「兔子洞」兩節，物證改為導向 `NNN-evidence.md`。
8. 階段 5 報告第 3 項納入 NO-SPRINT；第 6 項在 NO-SPRINT 時寫「本輪無交接」。

未採用：DEC-NNN 正式 ADR 系統、固定 cross-pollination 輪次、多輪 debate／投票、
把 skill 拆成薄骨架 + 可插拔工具箱。理由見上。
