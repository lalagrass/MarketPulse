對，這次我覺得你抓到一個**比「多幾個 agent」更核心的問題**：

目前的 brainstorm 雖然名義上是「發散」，但如果所有 agent 都吃同一份 prompt、同一份產品模型、同一組文件，很容易只是：

> **同一個 AI 大腦，換幾個說法。**

你想做的其實比較接近：

> **讓一個 sprint 開始時，臨時組成一個小型「MarketPulse 智庫／投資委員會」，每個角色從完全不同的 mental model 提案，再由 PO 收斂。**

我查到的開源做法，確實有幾個很吻合。像 `agent-debate-skill` 已經採用「多個 sub-agents 獨立 brainstorming + 不同 framing（Conservative / Aggressive / Contrarian / First-principles / Outlier-hunter）→ synthesizer」；`llm-society` 則直接把「不同 viewpoint 的 AI personalities」當成一等概念。([GitHub][1])

而且有一個我覺得對你特別重要的研究訊號：多-agent debate 類系統常常不是單純增加 agent 數，而是**刻意製造認知差異**，例如 Optimist / Pessimist / Devil's Advocate。([GitHub][2])

---

# 我會把你現在的 Brainstorm 徹底改成「角色市場」

現在大概是：

```text
HMW
 ↓
Agent A ─┐
Agent B ─┼→ proposals
Agent C ─┘
```

問題是 A/B/C 很可能都是：

> 「一個知道很多東西的 AI」

我會改成：

```text
                     Sprint Question
                           │
              ┌────────────┴────────────┐
              │  Generate Agent Panel   │
              └────────────┬────────────┘
                           │
     ┌────────┬────────┬────────┬────────┬────────┐
     ↓        ↓        ↓        ↓        ↓
    RD      Investor  User     Quant      UX
     ↓        ↓        ↓        ↓        ↓
   0~3       0~3      0~3      0~3       0~3
 proposals proposals proposals proposals proposals
     │        │        │        │        │
     └────────┴────────┴────────┴────────┴────────┘
                           ↓
                  Raw Proposal Pool
                           ↓
                     Cluster / Dedup
                           ↓
                    PO 收斂
```

**注意：我不會讓角色互相看答案。**

這點非常重要。

第一輪的目標不是 consensus，而是：

> **最大化 proposal distribution。**

---

# 甚至不要固定「每個角色一定要提案」

你提出：

> 「每個人提 0~3 個不等的提案」

我非常喜歡。

甚至我會把它變成這個規則：

> **每個 agent 可以產生 0–3 個 proposal；0 是合法答案。**

這很重要。

因為如果規定：

> 每個角色一定三個

最後一定得到大量垃圾：

> 「我們可以改善 dashboard。」

> 「我們可以增加 filter。」

> 「我們可以優化 UX。」

反而把 brainstorm 汙染掉。

所以：

```text
Agent A → 3
Agent B → 0
Agent C → 1
Agent D → 2
Agent E → 0
```

完全正常。

**沒有 idea 本身就是訊號。**

---

# 而且我不會讓角色只有「專業」

這裡是我覺得可以比你現在再進一步的地方。

角色應該同時帶：

### 1. Domain

例如：

* RD
* 投資人
* 技術分析師
* UX
* PM
* Data Scientist

### 2. Incentive

他「在乎什麼」。

例如：

**投資人**

> 找到真正能改善投資判斷的資訊；討厭花俏功能。

**RD**

> 偏好能落地、可維護、可測試；對新增複雜 dependency 敏感。

**UX**

> 關心第一次使用能不能在 30 秒理解。

### 3. Blind spot

這反而最重要。

例如：

**技術分析師**

> 容易過度重視 technical signal，可能低估敘事與使用情境。

**投資人**

> 容易把「對投資有用」當成「一定值得做」。

**RD**

> 容易把容易實作誤認為值得實作。

**UX**

> 容易偏向可視化，而忽略分析可靠性。

這會產生真正不同的 output。

---

# 所以不是 Persona，而是「Bias Profile」

這是我從多-agent debate 類專案覺得最值得借的一點。

例如有的系統直接用：

> Optimist / Pessimist / Devil's Advocate

而不是五個「普通專家」。([GitHub][3])

因此 MarketPulse 可以變成：

| Agent          | Domain      | Bias                |
| -------------- | ----------- | ------------------- |
| RD             | Engineering | Simplicity          |
| 投資人            | Investment  | Decision usefulness |
| 股癌聽眾           | Real user   | Practicality        |
| 技術分析師          | Quant/TA    | Signal              |
| UX             | Product     | Comprehension       |
| Data Scientist | Validation  | Evidence            |
| 懷疑論者           | Red team    | Disproof            |
| 探索者            | Future      | Outlier             |

這比：

> Agent 1 / Agent 2 / Agent 3

強很多。

---

# 「股癌聽眾」這個角色尤其有意思

因為它不是：

> 「股癌本人」

而是：

> **一個熟悉這類市場資訊產品、實際想拿 MarketPulse 來輔助投資的人。**

這個差別很重要。

Prompt 可以是：

> 你是一位長期使用市場資訊、產業敘事與技術面的投資者。你不是產品經理，也不是工程師。你只關心：「這個東西會不會讓我更快發現市場正在發生什麼？」對漂亮但不影響判斷的功能沒有興趣。

這會跟 RD 的輸出自然不同。

---

# 我甚至會讓角色池「不是固定的」

這是我覺得可以讓 skill 變得非常有趣的一步。

不要永遠：

```text
RD
Investor
UX
TA
User
```

而是：

```text
Core roles
+
Sprint-specific roles
```

例如這輪主題是：

> 第一層 breadth

系統自動組：

```text
Quant
Technical Analyst
Data Scientist
Investor
UX
Skeptic
```

如果是：

> narrative layer

則：

```text
Investor
Podcast Listener
Researcher
Information Architect
Data Scientist
Skeptic
```

如果是：

> architecture

則：

```text
RD
SRE
Data Engineer
Security
Maintainer
Future Contributor
```

所以不是：

> 固定一支 agent team。

而是：

> **每個問題臨時組一支 team。**

這跟 `llm-society` 那種「指定 viewpoints，再生成相應 personalities」的思路非常接近。([GitHub][4])

---

# 更棒的是：可以讓一部分角色「刻意不懂」

我很推薦。

例如「股癌聽眾」不要把：

* coding-contract
* architecture
* implementation details

全塞給他。

他只知道：

> 產品現在能做什麼。

因為真實使用者不會知道 repo 怎麼設計。

反過來：

### RD Agent

可以讀：

* CLAUDE
* coding-contract
* design
* repo

### User Agent

只能看：

* current product
* screenshots / reports
* product docs

### Investor Agent

主要看：

* product behavior
* historical reports
* use case

### Research Agent

可以看：

* external research
* OSS

這其實是非常重要的：

> **Context isolation。**

否則所有 agent 最後都會說：

> 「考量到 coding-contract……」

那就又變回同一個腦袋了。

---

# 我會把 brainstorm 分成兩輪，但只有第二輪才互相看

## Round 1 — Blind Ideation

每個 agent：

> 看自己的 context + sprint question。

不知道其他人的答案。

輸出：

```text
0–3 proposals
```

每個 proposal 只要求：

```text
Title
What
Why
```

不要：

* priority
* feasibility
* score
* vote

**這一輪只產生想法。**

---

# Round 2 — Cross-pollination

這時才把所有 proposals 丟回去。

讓 agent 看：

> 「其他角色想了什麼？」

但這次任務不是重新提案，而是：

```text
你看到了哪些：
1. 可以組合的
2. 你之前沒想到的
3. 你不同意的
4. 被忽略的重要角度
```

這叫做：

> **Cross-pollination**

而不是 debate。

我很喜歡這個 distinction。

因為你現在需要的是：

> **divergence → synthesis**

不是：

> divergence → 一堆 AI 開始爭論誰對。

---

# Debate 不應該放在 Brainstorm 前面

這是我從 community / open-source 做法看到後，反而會很明確的一個結論。

有些 multi-agent system 是：

> proposal → critique → rebuttal → judge

例如 MIT 的 multi-agent-debate 就是 researcher / critic / synthesizer / judge 的形式。([GitHub][5])

這適合：

> 「A 還是 B？」

不適合：

> 「我們到底可以做什麼？」

因為太早 critique：

```text
Agent A: 想到 X
Agent B: X 不可行
```

X 就死掉。

所以 MarketPulse 應該：

```text
Divergence
   ↓
Cross-pollination
   ↓
PO
```

而不是：

```text
Divergence
   ↓
Debate
   ↓
Consensus
```

---

# 還有一個我非常想加的角色：Outlier Hunter

`agent-debate-skill` 已經採用 Outlier-hunter 這種 framing，目的就是不要只找多數意見。([GitHub][1])

它可以有非常特殊的指令：

> **不要提出看起來最合理的想法。找一個大多數人不會想到、但如果成立會顯著改變 MarketPulse 的想法。**

最多一個。

這個 agent 的價值不是：

> 提案品質最高。

而是：

> **增加探索空間。**

---

# 再加一個「Killers」角色

但注意：

它不是在 Round 1 kill ideas。

它在最後才進來。

輸入：

```text
所有 proposals
```

輸出：

```text
哪些 proposal 看起來特別像：
- scope creep
- duplicate
- premature abstraction
- fake sophistication
- hidden scoring
- second layer contaminating first layer
```

然後交給 PO。

它不能直接刪。

這個很符合你現在的原則：

> agent 提供 evidence，PO 決定。

---

# 所以最後會長這樣

```text
                   Sprint Question
                         │
                         ▼
                ┌──────────────────┐
                │  Agent Generator │
                └────────┬─────────┘
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
       Domain          Bias           Context
          │              │              │
          └──────────────┼──────────────┘
                         ▼
                 ┌─────────────┐
                 │ Round 1      │
                 │ Blind Ideas  │
                 └──────┬──────┘
                        │
                     0–3 each
                        │
                        ▼
                 Proposal Pool
                        │
                        ▼
                 Dedup / Cluster
                        │
                        ▼
                 Round 2
               Cross-pollination
                        │
              ┌─────────┴─────────┐
              ▼                   ▼
       Outlier Hunter         Red Team
              │                   │
              └─────────┬─────────┘
                        ▼
                   PO / Judge
                        │
                DO / WON'T / UNKNOWN
                        │
                        ▼
                  Sprint Spec
```

---

# 最後一個關鍵：**不要讓 agent 投票決定**

我會非常堅持這點。

一些開源 multi-agent debate framework 會做 Bayesian consensus、vote、confidence aggregation。([GitHub][6])

對 MarketPulse，我反而**不要**。

因為：

```text
5 agents 支持 A
2 agents 支持 B
```

完全不代表 A 比 B 更好。

尤其：

> **「多數 AI 都想到」可能恰恰表示這是一個 obvious / boring idea。**

反過來：

> **只有 1 個 agent 想到的怪點子，可能才是最值得 PO 看。**

所以 PO 看到的應該是：

```text
Proposal A
提出者：Investor, UX
支持理由：...

Proposal B
提出者：RD
...
 
Proposal C
提出者：Outlier Hunter
只出現 1 次
...
```

而不是：

> A confidence 83%.

這跟你現在刻意拒絕 composite score 的思想是一致的。

---

# 我會對目前 skill 做的真正大改

你原本的：

> **1b. 各自寫，再比對。**

我會整段換成：

### 1b. 組建 Sprint Agent Panel

> 根據本輪 HMW，自動選擇 4–8 個不同 domain / incentive / bias 的角色。角色不是固定名單；核心角色可以重複使用，其他角色由本輪問題決定。

### 1c. Blind Ideation

> 每個角色獨立產生 0–3 個 proposal。角色不得看到其他角色輸出。0 個是合法結果。

### 1d. Context Isolation

> 不同角色只取得與其觀點必要的 context；不要讓所有角色讀到完整 repo / contract，避免不同角色收斂成同一個 mental model。

### 1e. Cross-pollination

> 第一輪完成後才公開 proposal pool。Agent 不再大量新增想法，而是指出可組合、被忽略、衝突與意外的新方向。

### 1f. Outlier / Red-team

> 至少一個角色負責尋找少數、反直覺或容易被忽略的方向；另一個角色專門指出 scope creep、premature complexity、違反產品模型的候選。

---

我認為這會是**比單純「多開幾個 agent」高一個層次的設計**。

核心不是：

> 「讓 AI 多想幾次。」

而是：

> **刻意讓不同 AI 在不同的資訊、利益、偏見與 mental model 下想，再把結果放到同一張桌上。**

這非常適合 MarketPulse，因為你真正想要的不是「AI consensus」，而是：

> **最大化 PO 可以看到的選擇空間，同時保留少數派與怪點子。**

而這一點，恰好和目前 community 裡比較成熟的 multi-agent brainstorming / debate 實作方向相當一致。([GitHub][1])

[1]: https://github.com/MagnusTautra/agent-debate-skill?utm_source=chatgpt.com "GitHub - MagnusTautra/agent-debate-skill: Claude Code skill: orchestrate stochastic-consensus or multi-round debate across N sub-agents for non-trivial decisions. · GitHub"
[2]: https://github.com/Skytliang/Multi-Agents-Debate?utm_source=chatgpt.com "GitHub - Skytliang/Multi-Agents-Debate: MAD: The first work to explore Multi-Agent Debate with Large Language Models :D · GitHub"
[3]: https://github.com/xyma2003/multi-agent-debate?utm_source=chatgpt.com "GitHub - xyma2003/multi-agent-debate: A LangGraph multi-agent debate system with divergence detection, concession tracking, and auditable consensus reports · GitHub"
[4]: https://github.com/zzzrbx/llm-society?utm_source=chatgpt.com "GitHub - zzzrbx/llm-society: A multi-agent simulation where AI personalities debate questions from different perspectives · GitHub"
[5]: https://github.com/mit-ai-studio/multi-agent-debate?utm_source=chatgpt.com "GitHub - mit-ai-studio/multi-agent-debate: Multi-Agent Debate · GitHub"
[6]: https://github.com/arbgjr/multi-agent-debate/blob/main/README.md?utm_source=chatgpt.com "multi-agent-debate/README.md at main · arbgjr/multi-agent-debate · GitHub"
