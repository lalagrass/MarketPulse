有，而且這次我會反過來回答你的擔心：

> **是，我們目前的 skill 已經有「太多東西」的風險。**
>
> 但問題不是「流程太長」本身，而是**很多本來可以是方法選項的東西，被寫成了固定 ceremony**。

我看完這批實作後，最值得借的不是再加 10 個規則，而是**把 brainstorm 做成一個很小的「divergence engine」**。其中 `Spark`、`Separate-Then-Together`、`Agora`、`ideate-core` 這幾個方向特別值得參考。([GitHub][1])

## 先講我的結論

我現在會把我們的 skill 縮成：

```text
Stage 0  Understand current state
    ↓
Stage 1  Diverge
    ├─ choose a few viewpoints
    ├─ independent ideas
    └─ optional cross-pollination
    ↓
Stage 2  Validate / Research
    ↓
Stage 3  PO Decide
    ↓
Spec / NO-SPRINT
```

**不要再增加更多固定階段。**

真正應該靈活的是 Stage 1。

---

# 一、社群其實已經回答了你最重要的問題

你前面擔心：

> 「同一個 AI 換角色，還是同一套思考框架吧？」

有很直接的開源證據支持你的直覺。

`Spark` 的設計不是單純叫 3 個 agent：

> 「請你當 RD / UX / PM。」

它刻意使用**不同 worldview、哲學、詞彙與 blind spots** 的 persona，再採：

> Seed → Cross-Pollinate → Synthesize

的流程。它甚至明確把 persona divergence 當成核心，而不是單純多開幾個 agent。([GitHub][1])

更有意思的是 `Separate-Then-Together`，它把：

> **先隔離、再共享**

本身當成主要方法，而且其研究定位就是 persona-based brainstorming/planning。([GitHub][2])

`ideate-core` 更直接採用：

> Round 1 blind → dedupe → build-on rounds

並且指出 **persona 是主要的 structural lever**。([GitHub][3])

所以你的直覺基本是對的：

> **「多 agent」不是重點；「多 mental models + information isolation」才是。**

---

# 二、反而不需要 8 個 agent

這是我會修正自己上一輪建議的地方。

前面我講：

> 4–8 個角色

現在看完這些實作，我覺得對你這個 skill **偏多**。

`Agora` 這類工具本身支持可配置 panel、並行第一輪、多 provider；但它的價值在「roundtable」，不是一定要塞很多人。([GitHub][4])

而 `Spark` 也是 3 個 persona 就能形成明顯差異。([GitHub][1])

所以我會定：

> **預設 3–5 個角色。**

不是因為 5 是神奇數字，而是：

> 足以形成 mental-model diversity，又不會讓輸出爆炸。

---

# 三、你提的「0～3 個 proposal」其實非常漂亮

這個我反而會保留。

甚至我會把它變成 brainstorm 的核心 contract：

```text
每個角色：
0–3 proposals
```

因為「0」很重要。

如果每個 agent 強制：

> 三個 idea

很快就會變成：

> feature boilerplate generator。

`6-3-5` 的 brainwriting 本來就是透過**固定個人輸出量 + 後續 build-on** 來增加發散，而不是強迫所有人都辯論。([GitHub][5])

所以：

```text
RD             2
Investor       1
Listener       3
UX             0
Skeptic        1
```

完全合理。

而且這會留下很有價值的訊號：

> **哪一個 worldview 對這個問題根本沒有值得提出的東西。**

---

# 四、但我會拿掉「每輪都 Cross-Pollinate」

這是我現在最想精簡的地方。

`Spark` 的 Seed → Cross-Pollinate → Synthesize 很漂亮。([GitHub][1])

`ideate-core` 也做 blind round → sharing rounds。([GitHub][3])

但對 MarketPulse，我認為：

> **Cross-pollination 應該是 optional，而不是每輪必做。**

原因：

有時第一輪已經有：

```text
12 ideas
```

而且彼此差異很大。

再做一輪，可能只是：

> A + B
> A + C
> B + C

最後得到 30 個變形。

這就是 brainstorm 自己開始吃自己。

所以我會改成：

### Cross-pollinate only when

> 第一輪出現幾個真正不同、而且可能互補的方向。

否則：

> 直接交給 PO。

---

# 五、真正值得借的是「角色選擇」，不是「固定角色」

這裡我很推薦 `Perspectra` 的方向。

它不是只有固定 personality，而是研究：

> **Choosing Your Experts**

也就是：

> 不同問題應該找不同 experts。([GitHub][6])

所以不要把 skill 寫成：

```text
永遠：
RD
投資人
股癌聽眾
TA
UX
```

應該是：

```text
Core:
1–2 generic perspectives

+
Question-specific:
2–3 selected perspectives
```

例如：

### 「市場故事層」

```text
Investor
Narrative consumer
Researcher
Skeptic
```

### 「數學層」

```text
Quant
TA
Data Scientist
Investor
```

### 「UX」

```text
End user
UX
Information designer
Skeptic
```

### 「工程」

```text
RD
Maintainer
Data engineer
User
```

這樣 skill 會變成：

> **選角色的 skill**

而不是：

> **角色清單 skill**。

---

# 六、但我甚至不建議寫「角色名稱」太多

我現在會更偏好：

```text
Role = Domain + Lens + Blind Spot
```

例如：

```text
Investor
Lens: decision usefulness
Blind spot: may overvalue actionability

RD
Lens: simplicity / maintainability
Blind spot: may reject useful ideas because implementation looks expensive

User
Lens: real-world usefulness
Blind spot: may not understand system constraints

Skeptic
Lens: falsification
Blind spot: may kill novel ideas too early
```

這樣比：

> 「你現在是 UX designer」

更有用。

因為真正造成 diversity 的是 **bias profile**。

---

# 七、我非常建議「context isolation」

這是現在 skill 最值得增加的一個小規則，但同時可以刪掉很多其他東西。

例如：

### RD

知道：

* CLAUDE.md
* coding contract
* repo structure
* current implementation

### Investor

知道：

* product output
* reports
* user objective

但不需要知道：

> 某個 class 是怎麼實作。

### UX

知道：

* screenshot
* current flow
* report
* user-facing behavior

### Skeptic

知道：

* proposal
* evidence
* known failure modes

但不要看到其他 agent 的原始 reasoning。

---

# 八、這比「請不同 agent 換個角色」重要很多

因為如果所有角色都讀：

```text
CLAUDE.md
coding-contract
design
backlog
open questions
all previous reports
current repo
research
```

然後問：

> 「你是投資人，請想三個點子。」

它最後通常會變成：

> 「考慮目前 architecture constraint……」

然後大家開始說一模一樣的話。

所以我會把 brainstorm 真正的核心寫成一句：

> **Diversity comes from different lenses and different context, not from multiplying identical prompts.**

這才是你這個 skill 真正值得留下來的方法論。

---

# 九、還有一個我很喜歡：不要先讓 agent 評估

這一點你現在其實已經做對了。

`Separate-Then-Together` 就是先：

> Separate → divergence

再：

> Together → convergence。([GitHub][2])

所以 Round 1：

**禁止：**

* feasibility
* priority
* scoring
* ranking
* critique

只准：

> 「有什麼可能？」

這應該保留。

---

# 十、但「SCAMPER」不要變成每輪固定流程

這也是「不要太多」的一個好例子。

`lateral-thinking` 把 SCAMPER 做成獨立 skill，定位非常清楚：

> **已有 idea → 做 transformation**

而不是 blank-page ideation。([GitHub][7])

這其實提供我們一個很好的原則：

> **不同 brainstorming technique 應該是工具箱，不是 pipeline。**

也就是：

```text
Brainstorm
 ├── Persona divergence
 ├── SCAMPER
 ├── inversion
 ├── random stimulus
 └── 6-3-5
```

Sprint 只選**一種最適合目前問題的方式**。

不要：

```text
每輪：
Persona
→ SCAMPER
→ inversion
→ six-three-five
→ red-team
→ debate
```

那一定爆炸。

---

# 十一、我會甚至把你的「至少 12 ideas」拿掉

這是我現在比上一版更進一步的看法。

你現在：

> 預設至少 12 個。

我會直接改成：

> **目標是產生足夠的候選，而不是達到固定數字。**

理由很簡單。

如果：

```text
4 agents × 0–3
= 0–12
```

這本身就已經很自然。

如果 agent 已經產生：

```text
7 個 genuinely different ideas
```

就不要為了：

> 「至少 12」

逼出五個垃圾。

所以真正的 exit criterion 應該是：

> **多數新增 proposal 已開始重複既有方向。**

這比 12 更合理。

---

# 十二、我會給 brainstorm 一個超簡單的「Stop Condition」

這可能是整份 skill 最值得增加的東西。

> **當新增角色 / 新思考 lens 不再產生 materially different ideas，就停止發散。**

也就是：

```text
RD         → 3 new
Investor   → 2 new
User       → 2 new
UX         → 1 new
TA         → 0
```

下一個 agent 產生：

```text
same as A
same as B
same as C
```

就：

> STOP.

不需要：

> 再來 3 個。

---

# 十三、我現在反而不推薦「第二輪 Debate」

這點很明確。

`brainstorm-mcp`、`Agora`、一些 debate framework 都會進入多輪討論。([GitHub][4])

但你的 PO skill 最終不是要：

> agent consensus。

你要的是：

> **proposal space → human decision**

所以我會：

```text
Round 1
Independent

Optional Round 2
Cross-pollinate

Then STOP.
```

不要：

```text
Round 3
Debate

Round 4
Rebuttal

Round 5
Consensus
```

否則 PO 最後拿到的是：

> AI 自己決定的 consensus。

跟你的產品哲學相反。

---

# 十四、這也解決「skill 太多」的問題

我現在會把整個 brainstorm 壓成 **五個 primitive**：

### ① Select

選 3–5 個不同 worldview。

### ② Isolate

讓他們只看到自己的必要 context。

### ③ Seed

各自產生 0–3 proposal。

### ④ Cross-pollinate（optional）

只有當新組合有價值才做。

### ⑤ Stop

當新想法開始重複就停。

就這麼多。

---

# 我甚至覺得現在的 Stage 1 可以縮成這樣

```markdown
## Stage 1 — Divergence

目標不是找到答案，而是擴大候選空間。

### 1a. Select perspectives

根據本輪 HMW，選 3–5 個真正不同的
domain / incentive / blind spot。

角色不固定；每輪可不同。

### 1b. Isolate

每個角色只取得完成任務所需的 context。
不要讓所有角色共享完整 repo / prior proposals。

### 1c. Blind seed

每個角色獨立提出 0–3 個 proposal。

禁止：
- 評分
- 排名
- feasibility review
- consensus

0 個 proposal 是合法結果。

### 1d. Cross-pollinate

只有第一輪出現值得組合的不同方向時才啟動。

讓角色看去重後的 proposal pool，
尋找：
- build-on
- combination
- contradiction
- overlooked angle

不要要求再次大量產生 proposal。

### 1e. Stop

當新增 perspective 不再產生 materially different ideas，
停止發散並交給下一階段。
```

我覺得**這比我們目前那一大段漂亮很多。**

---

# 最後一個很重要的方向：把 brainstorming 方法做成「可插拔」

SpecDD 這類專案有一個非常值得借的概念：

> **不要讓 spec 內容被 methodology 綁死。**

SpecDD 明確主張「只保留對當前問題有實質影響的 sections」，而不是每次填滿 template。([GitHub][8])

我會把這個思想搬過來：

```text
marketpulse-sprint
│
├── mandatory:
│   └── PO decision
│
└── optional methods:
    ├── persona-panel
    ├── SCAMPER
    ├── inversion
    ├── red-team
    ├── historical replay
    └── external research
```

所以未來不會變成：

> 「我們的 sprint 永遠 6 個階段、14 個小階段。」

而是：

> **skill 提供一套很薄的骨架，遇到不同問題才掛不同思考工具。**

這正是我目前最推薦的方向。

---

## 所以，我現在對你這份 skill 的判斷會從「加強」改成「瘦身」

我不會再往裡面塞更多流程。

反而會砍：

**固定 agent 數 → 砍**
**固定 12 ideas → 砍**
**固定 cross-pollination → 砍**
**固定 debate → 不要**
**固定 persona list → 砍**
**每輪一定完整跑所有 stage → 弱化**

保留：

**獨立發散**
**mental-model diversity**
**context isolation**
**0–3 proposal**
**optional cross-pollination**
**PO 最終收斂**
**NO-SPRINT**

其中 `Spark` 的 Seed/Cross-Pollinate/Synthesize、`Separate-Then-Together` 的 epistemic isolation、以及 `Perspectra` 的 expert selection，三者其實已經很接近你現在真正要的架構。([GitHub][1])

**如果再繼續加，我反而會開始反對自己。**

[1]: https://github.com/mulkatz/spark?utm_source=chatgpt.com "GitHub - mulkatz/spark: Collaborative ideation through multi-persona brainstorming — a Claude Code plugin · GitHub"
[2]: https://github.com/origo-labs/separate-then-together?utm_source=chatgpt.com "GitHub - origo-labs/separate-then-together: A research-oriented multi-agent collaboration system based on the **Separate-Then-Together** framework for persona-based planning and brainstorming · GitHub"
[3]: https://github.com/Kromatic-Innovation/ideate-core?utm_source=chatgpt.com "GitHub - Kromatic-Innovation/ideate-core: Provider-agnostic ideation primitive — multi-stance generation + expansion + human-idea folding, zero-dep injectable. (cwc#1320 S2) · GitHub"
[4]: https://github.com/lagameon/agora?utm_source=chatgpt.com "GitHub - lagameon/agora: Multi-agent roundtable discussion tool — multiple AI agents discuss a topic, then a synthesizer produces a final answer. CLI + MCP server. · GitHub"
[5]: https://github.com/rastian/design-thinking-skills/blob/main/SKILL.md?utm_source=chatgpt.com "design-thinking-skills/SKILL.md at main · rastian/design-thinking-skills · GitHub"
[6]: https://github.com/yiren-liu/perspectra-multi-agent-research-ideation?utm_source=chatgpt.com "GitHub - yiren-liu/perspectra-multi-agent-research-ideation: Source code for the prototype presented in CHI26 \"Perspectra\" paper. · GitHub"
[7]: https://github.com/danium/lateral-thinking/blob/main/skills/scamper/SKILL.md?utm_source=chatgpt.com "lateral-thinking/skills/scamper/SKILL.md at main · danium/lateral-thinking · GitHub"
[8]: https://github.com/specdd/specdd?utm_source=chatgpt.com "GitHub - specdd/specdd: Spec-Driven Development framework that enables humans and AI agents to build better software by giving them small, local instructions right where the code lives. It increases productivity, reduces implementation errors, and helps keep changes aligned with the project’s intended design. · GitHub"
