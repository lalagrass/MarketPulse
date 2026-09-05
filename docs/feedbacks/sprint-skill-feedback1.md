對，這次方向清楚很多。你要 brainstorm 的其實是：

> **「MarketPulse Sprint 這個 skill 自己，還能不能借鑑外面的 agent workflow / product discovery / decision-making 方法？」**

我重新看了一批目前的開源 agent workflow、Spec-Driven Development、Product Discovery、ADR、Shape Up 類做法。結論是：**有幾個真的值得吸收，而且其中兩三個我認為比我們目前的寫法更漂亮。**

---

# 1. 最大的啟發：不要把 skill 寫成「一條很長的流程」

這是我看到 `SPEC-AGENTS` 後最有感的一點。

它把流程拆成：

> `plan → capture → arrange → do → check → learn`

而且不是每次都完整跑。

簡單工作可以直接：

> `plan → do → check → learn`

只有跨多個概念、需要協調時才啟用完整流程。([GitHub][1])

這跟我們現在的 skill 有一個明顯差別：

現在比較像：

```text
0 → 1 → 2 → 3 → 4 → 5
```

而且階段 1/2 即使已經很明確，理論上還是會經過。

### 可以借來的設計

把 sprint skill 改成：

```text
                    ┌→ research ─┐
request → diagnose ─┤             ├→ decide → spec / no-sprint
                    └→ brainstorm ┘
```

也就是：

> **先診斷「現在真的需要哪種工作」，而不是每次都跑完整 ceremony。**

這很符合你前面想避免的 overengineering。

---

# 2. 「Planning 不是答案，而是可重寫的 artifact」

`Ordewell` 有一個我非常喜歡的概念：

> planner 產生的是 **typed artifact**，不是 agent 的 internal state。

而且在真正花 token 執行之前，人可以修改：

* task
* runner
* model
* dependency
* effort

整個 plan。([GitHub][2])

這給我們一個很好的想法：

### MarketPulse 的 sprint spec 可以分兩層

現在是：

> brainstorm → decision → spec

可以改成：

```text
Discovery Notes
      ↓
Candidate Set
      ↓
PO Decision Record
      ↓
Sprint Spec
```

其中真正需要持久保存的是：

> **PO Decision Record**

而不是所有 brainstorming。

這樣下一輪不用重新把整個歷史翻出來，只需要知道：

> 「上次到底為什麼選 A 而不是 B？」

---

# 3. ADR 的「Supersedes」非常適合你們

這個其實我覺得可以直接借。

`adr-tools` 的模式很簡單：

一個 decision 可以明確標記：

> supersedes previous decision

舊 decision 不刪掉，而是變成：

> superseded。([GitHub][3])

這對你們現在的：

> Rule → Default → 再次質疑

尤其適合。

現在如果：

```text
Sprint 008
Rule: never merge
```

後來：

```text
Sprint 012
降級為 default
```

我們現在是靠 report 描述。

可以更正式：

```text
DEC-008
Status: Superseded
Superseded by: DEC-012
Reason: d7975df demonstrates rule was already violated safely.
```

### 好處

下一個 agent 不需要猜：

> 哪一版才是真的？

它可以直接知道：

```text
Current decision
    ↓
Previous decision
    ↓
Reason for change
```

這跟你 skill 裡「自己說錯要明白更正」的哲學高度一致。

---

# 4. 我很喜歡「Evidence」獨立成一等公民

`SPEC-AGENTS` 的一個核心設計是：

> `EVIDENCE.md`

而且它刻意區分：

* durable knowledge
* current evidence
* current state

Fresh verified evidence 可以挑戰既有規則，但不能偷偷改掉它；要經過 plan，再記錄下來。([GitHub][4])

這跟你目前的 skill 有個很大的共鳴：

> **研究結果不能直接成為決策。**

目前我們有：

```text
研究 → report → PO 決定
```

我會考慮變成：

```text
Observation / Evidence
        ↓
Interpretation
        ↓
Decision
```

這三層分開。

例如：

```text
Evidence:
d7975df shows planning branch performed merge.

Interpretation:
"Never merge" is not enforced in practice.

Decision:
Downgrade "Never merge" from Rule to Default.
```

這會讓你的「規則演化」系統非常乾淨。

---

# 5. 其實「Rule 質疑」可以正式化成 Decision Lifecycle

你現在這段：

> 每輪質疑一條規則

我認為概念是對的，但做法還有點手工。

外面的 ADR / SPEC-AGENTS 類系統暗示了一個更好的結構：

```text
Proposed
   ↓
Accepted
   ↓
Tested by reality
   ↓
Confirmed
   ↓
Challenged
   ↓
Superseded
```

而不是：

```text
Rule
Rule
Rule
Rule
```

所以我可能會把 skill 裡的「Rule」再抽象一點：

### Policy lifecycle

```text
DEFAULT
PROVISIONAL
CONFIRMED
CHALLENGED
SUPERSEDED
```

不一定真的要全部實作成文件。

但**概念上非常有用**。

---

# 6. Shape Up 有一招，我覺得超適合你的 skill：Appetite

這個不是 AI 專用，但非常適合防止 MarketPulse scope creep。

Shape Up 的 pitch 不是：

> 「這功能需要幾天？」

而是：

> **「我們願意花多少時間？」**

而且 pitch 固定包含：

* Problem
* Appetite
* Solution
* Rabbit holes
* No-gos ([Basecamp][5])

尤其：

> **No-gos**

跟你現在 spec 裡：

> 「本輪明確不做」

幾乎完全同方向。

### 我會借的其實只有兩個東西

#### Appetite

每輪不要只說：

> 可以做 X。

還要說：

> **這輪最多願意投入多少複雜度。**

不一定要是時間。

MarketPulse 可以用：

* 只動一個資料來源
* 只動第一層
* 不新增 dependency
* 最多改 3 個模組

也就是：

> **Complexity appetite**

這可能比「三個 DO」更有用。

#### Rabbit holes

這個也很棒：

> 哪些細節一碰就會讓 sprint 爆掉？

例如：

```text
Rabbit hole:
Theme membership automation
→ eventually requires historical point-in-time universe
→ outside this sprint
```

這能非常早阻止 agent scope creep。

---

# 7. Product Discovery 有一招值得吸收：先找「最危險假設」

開源 `product-discovery` skill 基本上是：

> idea → assumptions → riskiest assumption → cheapest experiment

而不是：

> idea → build feature。([GitHub][6])

這對 MarketPulse 很適合。

例如我們想：

> 「rank migration 有價值。」

不要直接做。

先寫：

```text
Hypothesis:
Rank migration provides information that static rank misses.

Riskiest assumption:
There are recurring situations where rank acceleration
contains useful information before static rank does.

Cheapest test:
Replay historical observations without changing product.
```

這甚至可能把「research」變得更精準。

---

# 8. 「Research → Build」中間可以多一個 Experiment

這是我認為現版 skill 真正缺的一層。

現在：

```text
brainstorm
→ research
→ PO decide
→ build
```

但很多東西其實不值得直接 build。

可以改：

```text
brainstorm
→ research
→ experiment?
→ decide
→ build
```

而 Experiment 不一定是 code。

例如：

> 把過去 6 個月資料跑一次。

或者：

> 手工抽 20 個案例。

或者：

> 用現有 report 做 retrospective。

也就是：

> **先用最便宜的方法買資訊。**

這正是 product discovery 強調的 cheapest test first。([GitHub][6])

---

# 9. 我很喜歡 SuperSpec 的「小任務不需要多 agent」

這個跟我們目前「彼此看不到、平行 agent」有直接關係。

SuperSpec 的做法是：

> 多 agent 只在真的需要時使用；兩個 task 以下甚至直接 quick mode。([GitHub][7])

所以我們現在：

> 每輪至少幾隻 agent independently brainstorm

其實可能太 ceremony-heavy。

更漂亮的規則是：

### Independent exploration only when disagreement matters

也就是：

> **只有當答案高度不確定、anchor risk 高、或不同專業視角可能導致不同結論時，才平行 agent。**

其他時候：

> 單 agent 多視角就夠。

這個我會列為**值得直接改**。

---

# 10. 「多 agent」最好不要固定角色，而是固定「異議維度」

這是我從幾個 repo 拼起來後覺得很漂亮的改法。

不要：

```text
Agent A = Quant
Agent B = User
Agent C = Engineer
```

因為久了會變成固定 ritual。

改成：

```text
Perspective 1: What would make this idea true?
Perspective 2: What would make this idea fail?
Perspective 3: What existing solution makes this unnecessary?
Perspective 4: What is the cheapest way to know?
```

這比較接近真正的 red-team。

而且很適合你的「跟使用者吵」。

---

# 11. `plan-bender` 的「thin vertical slices」也值得拿

`plan-bender` 故意把每個 issue 的 points 上限壓得非常小，用 tracer-bullet / thin vertical slices 讓工作保持很小。([GitHub][8])

這跟你的：

> DO 最多 3 個

很接近。

但我會做一個重要修正：

### 不要限制「數量」，限制「可完成閉環」

例如不要：

> 最多三項

而是：

> **每個 DO 必須形成一個完整可驗證閉環。**

例如：

```text
BAD

DO-1 backend
DO-2 frontend
DO-3 report
```

這三個其實都不能獨立驗證。

更好：

```text
DO-1
Show RS rank migration in report
+ tests
+ acceptance
```

這就是 thin vertical slice。

---

# 12. Spec Kitty 有一個我們現在其實沒有的觀念：Retrospective 是 first-class

Spec Kitty 每個 mission 預設會留下 retrospective。([GitHub][9])

我們現在的 sprint report 有：

> 這輪改變想法的發現

但比較偏：

> 「發生了什麼？」

少了一個：

> **「這個 workflow 本身哪裡不好？」**

其實你的最後一句：

> 規劃端自己造成的問題也寫進報告。

已經在往這裡走了。

所以可以更明確：

### Sprint retrospective

每輪至少回答：

```text
What decision was good?
What assumption was wrong?
What planning ceremony was unnecessary?
What rule prevented useful work?
What rule failed to prevent bad work?
```

這會讓 skill 自己持續改善，而不是只改善 MarketPulse。

---

# 13. Bottega 提供另一個值得借的架構：Human at both ends

Bottega 的流程：

```text
Human
 ↓
Planning agent
 ↓
Human approve
 ↓
Implementation
 ↓
Adversarial review
 ↓
Human
 ↓
Merge
```

而不是讓 agent 自己完成整個閉環。([GitHub][10])

你現在其實已經有：

```text
Cowork
 ↓
PO
 ↓
Claude Code
```

所以我反而不想增加更多 agent。

但可以把責任界線寫得更清楚：

### Cowork owns

> **What / Why / Evidence / Decision**

### Claude Code owns

> **How / Implementation / Tests**

### User owns

> **Irreversible product decisions**

這會比單純「不寫程式」更容易讓 agent 理解角色。

---

# 14. 最值得吸收的其實是「不要把所有 context 都載入」

這點我覺得甚至比 workflow 更重要。

`SPEC-AGENTS` 明確反對：

> 每次把所有 project knowledge 都塞進 agent context。

它採：

> stable model first → 只讀這次決策需要的 evidence / records。([GitHub][1])

你目前 Stage 0：

```text
CLAUDE.md
coding-contract
design
non-goals
backlog
open-questions
latest sprint
git log
branches
```

全部讀。

這在專案小的時候沒差。

但長期下去：

> **skill 自己會成為 context bloat machine。**

我會考慮改成：

```text
Always:
CLAUDE
coding-contract
current status

Then intent-based:
design → if design affected
backlog → if prioritizing
open-questions → if decision unresolved
old sprint → only if dependency/history relevant
```

這個我認為是**非常值得改的架構性改善**。

---

# 15. 我會加入一個「Context budget / Read budget」

這可能是我們現版最大的缺口。

例如：

> 預設只讀最近 1–2 個 sprint；只有發現 conflict 才往歷史回溯。

不要：

> 永遠讀 `git log -10`

甚至 git log 都可能只是 heuristic。

可以變成：

### Context escalation

```text
Level 1
Current state

↓ conflict / unknown

Level 2
Latest sprint + relevant docs

↓ still unresolved

Level 3
Historical commits / old reports

↓ still unresolved

Level 4
Deep archaeology
```

這跟 `SPEC-AGENTS` 的「只載入當前決策需要的證據」很一致。([GitHub][1])

---

# 16. 最有趣的一個：讓「不知道」也有生命週期

你現在：

> UNKNOWN 必須有回頭日期。

這已經非常好。

但可以再借 `SPEC-AGENTS`：

> current evidence / status / durable knowledge

的概念。([GitHub][1])

把 UNKNOWN 分成：

```text
UNKNOWN
  ↓
Need Evidence X
  ↓
Experiment / Research
  ↓
Resolved
   ├─→ Decision
   └─→ WON'T
```

所以 UNKNOWN 不是 backlog 項目。

它是一個：

> **待證據解鎖的 decision state**

這會讓 backlog 乾淨很多。

---

# 17. 我反而不推薦借的東西

這點也很重要。

### 不要照抄 Spec Kitty

它很好，但它開始偏：

> software factory / worktree / task orchestration

而你的 MarketPulse skill 是：

> **PO thinking layer**

拿太多會變成平台工程。

### 不要引入完整 OKR / PRD / RICE / WSJF

這會跟你現在：

> 不做綜合評分

的精神衝突。

尤其 RICE / WSJF 很容易變成：

> AI 自己算出一個「優先級 87」。

這正是你想避免的。

### 不要讓 retrospective 變成另一份 ceremony

它應該是：

> 5 分鐘的 learning record

而不是再寫一份十頁報告。

---

# 我最後會把這些點分成四級

| 想法                                          | 建議        |
| ------------------------------------------- | --------- |
| **Context escalation / 不要每次全讀**             | ⭐⭐⭐⭐⭐     |
| **Evidence → Interpretation → Decision 分層** | ⭐⭐⭐⭐⭐     |
| **Plan 是 artifact，可以重寫**                    | ⭐⭐⭐⭐⭐     |
| **Rule lifecycle / supersedes**             | ⭐⭐⭐⭐⭐     |
| **Experiment before build**                 | ⭐⭐⭐⭐⭐     |
| **NO-SPRINT**                               | ⭐⭐⭐⭐⭐ 已加入 |
| **Appetite + Rabbit holes**                 | ⭐⭐⭐⭐      |
| **Conditional multi-agent**                 | ⭐⭐⭐⭐      |
| **Thin vertical slice**                     | ⭐⭐⭐⭐      |
| **Retrospective**                           | ⭐⭐⭐⭐      |
| 完整 software-factory orchestration           | ⭐⭐        |
| RICE/WSJF 類 scoring                         | ⭐         |
| 再增加更多永久規則                                   | ❌         |

---

# 如果是我，我會讓下一版 skill 的架構變成

不是再把現在的 skill 拉長。

而是收斂成：

```text
                ┌──────────────┐
                │ Current State│
                └──────┬───────┘
                       ↓
                 Diagnose
                       │
          ┌────────────┼────────────┐
          ↓            ↓            ↓
      Use data      Brainstorm    Research
          │            │            │
          └────────────┼────────────┘
                       ↓
              Evidence / Options
                       ↓
                  Cheap Test?
                    /     \
                  yes      no
                   ↓        ↓
                Experiment  PO
                   └────┬────┘
                        ↓
                 DO / WON'T /
                 UNKNOWN / NO-SPRINT
                        ↓
                    Decision
                        ↓
                  Sprint Spec
                        ↓
                  Claude Code
                        ↓
                    Evidence
                        ↓
                 Retrospective
                        ↓
                 Decision history
```

這裡面最重要的是：

> **Sprint 不再是一條固定流水線，而是一個「決策系統」。**

我覺得這是這次研究後，對你這個 skill 最大的啟發。

而且它跟你原本最核心的理念完全一致：

> **不要為了「有 sprint」而做 sprint。**

外面的最佳做法其實正在往同一個方向走：agent 工作流開始把 **spec、evidence、decision、review、learning** 都變成 repository 裡的 durable artifacts，而不是依賴對話記憶。([GitHub][11])

[1]: https://github.com/yibie/SPEC-AGENTS.md?utm_source=chatgpt.com "GitHub - yibie/SPEC-AGENTS.md: Doc-Driven Development · GitHub"
[2]: https://github.com/ordewell/ordewell?utm_source=chatgpt.com "GitHub - ordewell/ordewell: Multi-agent task orchestration for coding agents. Turn one goal into an ordered plan of tasks — each with its own runner, model and mode — then execute and verify the results. · GitHub"
[3]: https://github.com/npryce/adr-tools?utm_source=chatgpt.com "GitHub - npryce/adr-tools: Command-line tools for working with Architecture Decision Records · GitHub"
[4]: https://github.com/yibie/SPEC-AGENTS.md/blob/main/README.md?utm_source=chatgpt.com "SPEC-AGENTS.md/README.md at main · yibie/SPEC-AGENTS.md · GitHub"
[5]: https://basecamp.com/shapeup/1.5-chapter-06?utm_source=chatgpt.com "Write the Pitch | Shape Up"
[6]: https://github.com/TerminalSkills/skills/blob/main/skills/product-discovery/SKILL.md?utm_source=chatgpt.com "skills/skills/product-discovery/SKILL.md at main · TerminalSkills/skills · GitHub"
[7]: https://github.com/lbk-open/super-spec/blob/main/docs/multi-agent.md?utm_source=chatgpt.com "super-spec/docs/multi-agent.md at main · lbk-open/super-spec · GitHub"
[8]: https://github.com/jasonraimondi/plan-bender?utm_source=chatgpt.com "GitHub - jasonraimondi/plan-bender: Structured planning pipeline for AI coding agents — interview, PRD, issues, review, implement, archive · GitHub"
[9]: https://github.com/Priivacy-ai/spec-kitty?utm_source=chatgpt.com "GitHub - Priivacy-ai/spec-kitty: Spec-Driven Development for serious software developers. Spec Coding with with Claude, Cursor, Gemini, Codex. Kanban dashboard, git worktrees, auto-merge and more. · GitHub"
[10]: https://github.com/vdaubry/bottega?utm_source=chatgpt.com "GitHub - vdaubry/bottega: Coding agent orchestration for engineering teams — shipped as a spec plus a working reference implementation. · GitHub"
[11]: https://github.com/zhu1090093659/spec_driven_develop?utm_source=chatgpt.com "GitHub - zhu1090093659/spec_driven_develop: Spec-driven development workflow for AI coding agents: architecture-first planning, task decomposition, GitHub Issue/PR tracking, Deep Discuss, and adaptive control for Claude Code, Codex, Cursor, and other Markdown-capable agents. · GitHub"
