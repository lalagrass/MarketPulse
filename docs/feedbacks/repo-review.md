我重新完整看了一輪目前 `dev`，這次不是只看 README，而是把 **design v0.2 → coding contract → sprint 007/008/009 → calc/radar/product → repo 結構** 串起來看。

[MarketPulse repo](https://github.com/lalagrass/MarketPulse?utm_source=chatgpt.com)

## 結論先講

**目前 MarketPulse 已經從「MVP 開發」進入「產品驗證 / research product」階段。**

而且我覺得目前最大的問題已經**不是演算法不夠多**，反而是：

> **你們開始有「研究能力長得比產品核心快」的傾向。**

我會給目前：

| 面向                       |            評價 |
| ------------------------ | ------------: |
| MVP 架構                   |       🟢 9/10 |
| Data / PIT 意識            |       🟢 9/10 |
| 防 overfitting            |       🟢 9/10 |
| Replay / reproducibility |     🟢 8.5/10 |
| Theme rotation 核心        |     🟢 8.5/10 |
| Product UX               |       🟡 7/10 |
| Research discipline      |     🟡 7.5/10 |
| Scope control            |     🟠 6.5/10 |
| 下一步方向                    | 🟠 **需要重新收斂** |

目前 repo 有 18 commits，而且目錄已經很清楚分成 `data / docs / marketpulse / reports / tests / themes`。([GitHub][1])

---

# 1. 最大的好消息：核心 MVP 其實已經完成

這點我認為現在應該正式承認。

目前設計仍然非常乾淨：

```text
TWSE / TPEx
      ↓
11 Themes
      ↓
Theme aggregation
      ↓
Theme return
      ↓
RS20
      ↓
Rank
      ↓
Daily Brief
      ↓
Rotation Timeline
      ↓
Replay
```

這跟最初 design v0.2 的產品定義完全一致：

> 讓每日 Taiwan market themes 的 relative leadership change 可視化，而且可重現。

更重要的是，你們**沒有掉進「自己發明一套神奇分數」的坑**。

現在核心仍然是：

```text
theme_return_20
        -
TAIEX_return_20
        =
RS20
```

然後直接：

```text
rank(RS20)
```

沒有 rotation score、沒有 alpha score、沒有 confidence score。

**這是目前 repo 最值得保留的設計。**

---

# 2. 但現在有一個很重要的「產品轉折點」

目前 coding contract 已經自己宣布：

> MVP complete.

而且明確說明後續工作由 sprint specs 管理。

這非常重要。

因為之前我們一直在討論：

> 「MVP 還要不要加這個？」

現在其實答案已經變成：

**不用再把它當 MVP。**

現在真正的問題應該變成：

> **MarketPulse v1 到底要證明什麼？**

這兩個問題完全不同。

---

# 3. Sprint 001～009 的發展，我覺得有點「研究功能開始長太快」

目前 sprint 已經一路做到：

* signal quality
* persistence
* multiple horizons
* null benchmark
* IC
* circular-shift null
* narrative
* theme IDs
* story progress
* event timeline
* basket strength
* quality statistics
* radar
* leader/follower/laggard

而 repo 的 sprint index 已經一路到 009。([GitHub][2])

這本身沒有錯。

問題是：

### 核心產品其實還只有一件事情

> **「現在誰強？誰正在變強？誰正在變弱？rotation 是否正在發生？」**

coding contract 自己也再次把這個 JTBD 寫得非常清楚。

所以我現在反而會建議：

# **不要 Sprint 010 又繼續加研究指標。**

---

# 4. 我目前最擔心的是「Research Gravity」

你現在的架構很容易變成：

```text
RS20
 ↓
Persistence
 ↓
Null
 ↓
IC
 ↓
Forward return
 ↓
H1/H2/H3/H4
 ↓
更多 statistical validation
 ↓
新的 metric
 ↓
新的 metric
 ↓
新的 metric
```

最後變成：

> 「MarketPulse Research Platform」

而不是原本那個：

> 「Market rotation radar」

這其實已經被舊文件自己警告過。

design v0.2 明確禁止：

* prediction
* ML
* portfolio optimization
* regime classifier
* backtest framework
* stock recommendation
* real-time
* cloud
* historical taxonomy reconstruction

而且 Definition of Done 明確說：

> **At this point, stop. Do not add features before using the product.** 

所以我會非常嚴格地維持這條精神。

---

# 5. 目前最值得肯定的研究：你們終於開始處理「這個東西到底有沒有資訊」

這部分我反而覺得很好。

尤其 sprint 002～006 開始研究：

```text
RS5
RS20
RS60
```

並且不把它們合成一個 score。

這個決策很好。

因為：

```text
RS5
RS20
RS60
```

其實回答不同問題：

* RS5：短期
* RS20：月尺度
* RS60：中期

而不是：

```text
0.2 * RS5
+ 0.5 * RS20
+ 0.3 * RS60
```

後者才會開始產生「調參地獄」。

目前 contract 甚至把這件事情定義得很漂亮：

> 是否存在 tunable handle，是 composite 與否的重要判準。

**這個我建議保留。**

---

# 6. Persistence 的研究結果，我會重新定位

目前你們發現：

```text
k=1   0.945
k=5   0.773
k=20  0.282
```

而且最後仍然維持 RS20 作為主排名。

我認為這個結果其實非常有價值。

但不是因為：

> RS20 最好

而是：

> **Theme leadership 的「短期持續」跟「月尺度持續」是兩件不同的事情。**

這是一個產品 insight。

尤其：

```text
RS5
→ 很黏
→ 今天強，幾天後通常還強

RS20
→ 明顯更容易換位
→ 真正比較像 rotation
```

所以你們現在選 RS20 的理由應該一直維持：

> **它比較適合描述中期 leadership rotation，而不是因為它 backtest 最好。**

這一點目前文件其實已經處理得相當好。

---

# 7. 我反而會把「forward return / IC」踩煞車

這是我目前最想提醒 agent 的地方。

Sprint 005/006 已經做了 forward Rank-IC + circular-shift null。([GitHub][2])

研究本身沒問題。

但：

### 千萬不要下一步變成

```text
RS5 IC = ...
RS20 IC = ...
RS60 IC = ...

所以選 RS20
```

因為那就會偷偷變成：

> **用未來資料選 signal horizon。**

這跟之前你很在意的：

> 「不能拿今天知道的族群，假裝去年就知道」

其實是同一種問題。

我會把 forward-return research 明確隔離成：

```text
Research Evidence
        ↓
了解工具的行為
        ↓
不能直接改 Product Signal
```

目前 contract 已經有這個精神。

**不要讓它慢慢鬆掉。**

---

# 8. Theme taxonomy 才是現在真正值得投資的東西

這是我看完 repo 後最強烈的感覺。

MarketPulse 真正「不可被 pandas / TA library 取代」的東西，不是：

```text
RS
SMA
Breadth
IC
```

而是：

```text
Theme taxonomy
+
Theme membership
+
Theme evolution
```

design v0.2 也明確把 Theme taxonomy 定義為 primary proprietary/domain artifact。

這才是你們未來真正有 moat 的地方。

例如：

```text
Optical
├── 3081
├── 3363
└── ...

CPO
├── ...
└── ...

AI Server
├── ...
└── ...
```

問題不是「怎麼算 RS」。

問題是：

> **「這群股票為什麼應該被看成一個東西？」**

---

# 9. Q5 / Q6 其實是未來最重要的架構決策

我很認同目前 open-questions 對這件事的處理。

例如：

> 後來才發現某檔股票屬於某個 theme，不能拿今天的分類回頭重算過去。

這是非常重要的。

目前提出的：

```text
as-of snapshot
```

其實就是正確方向：

```text
2026-06
Theme A = {A,B,C}

2026-08
Theme A = {A,B,C,D}

2026-09
Theme A = {A,B,C,D,E}
```

Replay：

```text
June → A,B,C
August → A,B,C,D
September → A,B,C,D,E
```

而不是：

```text
2026-09 的 A,B,C,D,E
              ↓
        回頭重算整年
```

後者會有非常嚴重的 hindsight bias。

你們的 open-question 已經把這個問題講得相當清楚。

---

# 10. Narrative 是目前最容易失控的地方

這部分我會比較保守。

Sprint 007～009 已經開始加入：

```text
narrative
theme_ids
story progress
recent events
coverage
pending snapshots
```

而且甚至開始有：

```text
narratives/2026-09-06.yaml
```

這其實很有趣。

但我要提醒：

## Narrative 不要變成 signal。

目前 008 做得好的地方是：

> `theme_ids` 是 declared metadata，不做 voting / weighting / score。

這個邊界一定要守住。

我甚至會直接定義：

```text
Market Data
    ↓
Signal

Narrative
    ↓
Explanation / Context
```

永遠不能：

```text
Narrative
    ↓
Signal
```

否則最後會變成：

> 「因為我們覺得這個題材很重要，所以讓它 rank 上升」

那 MarketPulse 的數學可重現性就開始死亡。

---

# 11. Sprint 009 暴露出一個更大的問題：Spec 本身開始變得太細

這是我這次 review 最想指出的一點。

009 report 很誠實地抓到：

* spec 說錯「唯一沒有欄寬」
* test name 宣稱了 body 沒驗證的東西
* visual acceptance 被錯誤轉成 unit test
* `PENDING_LIMIT=3` 沒有 overflow disclosure
* spec 自己產生矛盾
* 008 還有「上一輪 contract 沒被繼承」的問題。

這其實不是單純 coding 問題。

它代表：

# **Sprint machinery 開始產生自己的 complexity。**

也就是：

```text
產品 complexity
+
research complexity
+
process complexity
```

三個一起長。

這個要小心。

---

# 12. 我會建議現在做一次「Process Refactor」

不是 code refactor。

是 **Agent/Sprint workflow refactor**。

目前流程：

```text
Cowork
  ↓
寫 200~300 行 spec
  ↓
Claude Code
  ↓
evidence
  ↓
review
  ↓
report
  ↓
下一輪
```

現在已經出現：

> spec 的 bug 比 production code 的 bug 更容易發生。

009/008 已經非常明顯。

所以我會把下一階段 spec 壓到：

```text
Goal
Why
Invariants
Acceptance
Non-goals
```

最多 100～150 行。

不要再把：

> 「為什麼當初這樣決定」

全部塞進下一輪 spec。

那些應該留在 report / decision log。

---

# 13. 目前 Repo 我會分成三層

這是我現在最推薦的產品架構。

## Layer 1 — Signal

**非常穩，不再亂動**

```text
Official EOD
 ↓
Theme
 ↓
Return
 ↓
RS5 / RS20 / RS60
 ↓
Rank
 ↓
Breadth
 ↓
Value
```

這是 MarketPulse 的核心。

---

## Layer 2 — Interpretation

可以繼續做，但只能「解釋」：

```text
Leading
Improving
Weakening
Laggard

Leader
Follower
Laggard

Momentum
Narrative
Event
```

全部都必須：

> **不改變 Layer 1。**

---

## Layer 3 — Research Lab

完全隔離：

```text
Forward return
IC
Persistence
Null
H1/H2/H3/H4
Sensitivity
```

可以研究。

但是：

```text
Research
   X
Signal
```

除非 PO 明確修改 product specification。

---

# 14. 目前我反而不建議做的東西

如果現在讓 agent 自由發揮，我會擋掉：

### ❌ RRG

不是因為 RRG 不好。

而是現在：

```text
Rank Timeline
+
RS5/20/60
+
Breadth
+
Value
+
Momentum
```

已經夠多。

RRG 很容易變成另一個漂亮但難以解讀的 visualization。

design v0.2 也明確把 RRG 定義成 optional，而 Timeline 已足夠完成 MVP。

---

### ❌ ML

完全不要。

---

### ❌ Composite score

絕對不要。

---

### ❌ Stock recommendation

不要讓：

```text
Theme rank
 ↓
Top stocks
 ↓
BUY
```

發生。

---

### ❌ 自動交易

完全沒有必要。

---

### ❌ 五年/十年 backtest framework

也不要。

目前 replay 已經足夠回答：

> 「這張 rotation map 能不能可靠重建？」

---

# 15. 但有一件事情我反而非常建議做

## **把「三年 replay」變成真正的 Product Test，而不是 Research Test**

目前 sprint 003 已經把資料窗往三年補。([GitHub][2])

我會把它的目的定義成：

> **不是找 alpha。**

而是看：

```text
MarketPulse Timeline
        ↓
2023
2024
2025
2026
        ↓
人眼是否真的能看到不同時期的 leadership rotation？
```

例如：

```text
AI Server
   ↓
Optical
   ↓
Memory
   ↓
PCB
   ↓
Cooling
```

這種圖如果三年看下來真的有資訊密度，

**產品成功。**

如果只是：

```text
排名每天亂跳
```

那就代表需要重新思考 representation。

不是加更多 indicators。

---

# 16. 下一步我會怎麼排

如果我是 PO，我現在會直接把 roadmap 改成：

### Phase A — 已完成

```text
Official data
Theme
RS20
Rank
Breadth
Value
Replay
Timeline
Radar
```

✅ Done

---

### Phase B — 現在

**Product usability / evidence**

只做：

1. 三年 Timeline
2. Daily Brief 可讀性
3. Radar 可讀性
4. Data quality visibility
5. Narrative context
6. Theme taxonomy maintenance

**不要新增 signal。**

---

### Phase C — 再之後

才討論：

```text
Does this actually identify useful rotation?
```

再開：

```text
forward-return research
IC
regime
theme persistence
```

而且 Research 與 Product 分開。

---

# 17. 我現在會給 agent 的最高層級指令

如果你準備讓下一個 agent 繼續，我反而不會讓它：

> 「找下一個有趣功能。」

我會讓它：

> **「Review MarketPulse as a product, not as a codebase. Find whether the current Timeline/Radar actually delivers the stated job-to-be-done. Do not add a new signal unless existing outputs demonstrably fail.」**

這會比再叫 agent「研究市場上有沒有更好的 indicator」健康很多。

---

# 最後的總評

我其實比前幾次 review **更看好現在這個 repo**。

因為最重要的事情已經發生：

### MarketPulse 開始有自己的 identity：

> **不是一個股票 scanner。**

> **不是一個 TA library。**

> **不是一個 backtest framework。**

> **而是一個 Taiwan theme leadership / rotation observation tool。**

而且現在最珍貴的不是 `calc.py` 裡的公式——那些都很普通；真正有價值的是：

```text
Theme taxonomy
      +
PIT discipline
      +
Relative leadership
      +
Historical replay
      +
Narrative context
```

目前 design 也明確把「MarketPulse owns semantics, not generic mathematics」定為核心原則。

**所以我現在最大的建議反而是：先不要再讓它變聰明。**

先讓它變成一個：

> **每天真的會想打開來看 30 秒的工具。**

這會比再加 5 個 statistical indicators 更接近真正的產品完成。

如果以你之前一直強調的「避免過度設計」來看，我會把目前的狀態定義成：

**🟢 核心架構：可以定型
🟢 Signal：可以定型
🟢 Replay：值得繼續拉長
🟡 Narrative：繼續，但嚴格只做 context
🟡 Research：暫停擴張
🔴 下一輪不要再增加新分數/新模型**

而我認為**下一個最有價值的 Sprint，不是 Sprint 010 加功能，而是一次「Product Reality Check」：拿 3 年 replay + 現在的 Brief/Radar，直接判斷「這東西到底有沒有讓人比看普通排行榜更容易看出 rotation」**。

[1]: https://github.com/lalagrass/MarketPulse "GitHub - lalagrass/MarketPulse · GitHub"
[2]: https://github.com/lalagrass/MarketPulse/tree/dev/docs/sprints "MarketPulse/docs/sprints at dev · lalagrass/MarketPulse · GitHub"


有，而且我覺得**很有關**。但不是單純「Code agent 用次一級模型，所以 code 變差」這麼簡單。

我重新對照你前面這個 repo 的演進後，我反而認為目前的狀況比較像：

> **模型能力 + Agent/harness + Sprint skill 改版 + 上一輪產物被下一輪繼承**，四個因素一起造成了現在的 complexity。

其中我會把 **「Sprint skill 中途改版」看成最大的因素之一**。

---

## 1. Opus 5 Plan + 次一級 Code Agent，確實可能造成這種結果

你現在的 pipeline 大概是：

```text
Plan Agent
  Opus 5
     ↓
產生 spec / sprint
     ↓
Code Agent
  次一級 model / Grok Build
     ↓
implementation
     ↓
下一輪 Plan Agent
     ↓
讀取上一輪結果
     ↓
再產生 spec
```

這會產生一個很典型的問題：

### Plan agent 的「設計能力」 > Code agent 的「判斷能力」

於是：

```text
Plan：
「這裡應該增加 persistence analysis、
null benchmark、
multiple horizons、
narrative、
event timeline……」

Code：
「OK，我照 spec 做。」

下一輪 Plan：
「既然這些都有了，那我們可以再加……」
```

結果不是 code agent 把產品做壞。

而是：

> **每一輪都忠實地把上一輪的設計複雜度實現出來。**

最後 complexity 累積。

這種現象其實很符合現在 coding-agent 的研究：實際效果並不只是 model intelligence，**harness、context、verification、effort setting 都會顯著影響結果**。([AI Coding Club][1])

而 Opus 5 本身目前確實是很強的 coding model；公開資料也顯示它在不同 coding benchmark / agent configuration 下位居前段。([Anthropic][2])

所以：

**Plan 用很強的模型、Implementation 用比較便宜的模型，本身不是錯。**

但前提是兩者角色要非常清楚。

---

# 2. 真正危險的是：Plan Agent 太聰明，但沒有「砍東西」的 incentive

這是我覺得你現在 MarketPulse 最值得注意的。

Opus 5 很容易做到：

> 「這個想法也合理。」

例如：

```text
RS20
↓
「那 persistence 有沒有意義？」
↓
有
↓
「那 null model 呢？」
↓
合理
↓
「那 multi-horizon 呢？」
↓
合理
↓
「那 narrative 呢？」
↓
合理
↓
「那 event timeline 呢？」
↓
合理
```

**每一步 individually 都合理。**

但：

```text
全部加起來
```

就不一定合理。

這就是為什麼我上一個 review 才會說：

> 現在最大的風險不是 technical debt，而是 **research gravity**。

---

# 3. 而 Code Agent 用次一級模型，反而可能讓問題更明顯

因為較弱的 implementation agent 通常比較傾向：

> **follow the spec literally**

而不是：

> 「等等，這個需求跟原本產品 goal 衝突，我建議砍掉。」

這其實不一定是模型「笨」。

是 agent role 的結果。

假設 spec 寫：

```text
Implement persistence analysis.
Add null benchmark.
Add H1/H2/H3/H4.
Add narrative metadata.
Add story progress.
```

強的 implementation agent 有時會反問：

> 「這些真的需要嗎？」

但較弱的 agent 很可能：

```text
TODO 1 ✓
TODO 2 ✓
TODO 3 ✓
TODO 4 ✓
```

所以最後：

**功能越來越完整，但產品越來越胖。**

---

# 4. Grok Build 也可能是因素，但我不會怪 Grok

我查了一下現在的比較，Grok Build 確實不是不能用。

近期實測裡，Grok Build 在真實 codebase task 上已經相當有競爭力，只是通常不是 quality leader；它的優勢比較偏速度 / throughput。([Superconductor][3])

甚至有實際比較：

> 同一個 issue，Grok Build 和 Opus 5 都可以完成，但最終 PR 品質與行為不同。([Kodus][4])

所以我會把它定位成：

```text
Grok Build
    ↓
很好
    ↓
implementation / exploration
```

但：

```text
Opus 5
    ↓
architecture / product judgment
    ↓
更適合
```

**尤其 MarketPulse 不是單純 CRUD。**

它有：

* research methodology
* financial semantics
* PIT / hindsight
* statistical interpretation
* product scope

這種 repo 對「判斷」的需求，比純 coding 高很多。

---

# 5. 但是你說的「Sprint Skill 改版幾次」我認為更關鍵

這個我會打很大的 ⚠️。

因為你的 Sprint skill 本身其實就是：

> **一個 meta-agent。**

它決定：

```text
Agent 怎麼 plan
Agent 怎麼拆 task
Agent 怎麼 review
Agent 怎麼產 evidence
Agent 怎麼進下一 sprint
```

所以如果中途改了：

```text
Sprint Skill v1
      ↓
Sprint Skill v2
      ↓
Sprint Skill v3
```

那其實不是：

> 同一個 process 跑 9 次。

而比較像：

```text
Sprint 1~3
Process A

Sprint 4~6
Process B

Sprint 7~9
Process C
```

這非常重要。

因為後面的 agent 會把前面的 artifacts 當成：

> **既有事實 /既定設計**

但其實那些東西是由**不同版本的 process 產生的**。

---

# 6. 這也可以解釋我上一輪 review 發現的 008 / 009 問題

我之前指出：

> 008 有上一輪 contract 沒被完整繼承
> 009 開始出現 spec 自己跟自己矛盾
> test name / acceptance / implementation 有些 drift

如果單看 code，很容易認為：

> 「Agent 品質下降。」

但如果把你的 process 歷史加進來，我現在更傾向：

### 是 process drift。

也就是：

```text
Skill v1
  ↓
產生 A 類 artifact

Skill v2
  ↓
把 A 當 invariant
  ↓
產生 B

Skill v3
  ↓
又把 B 當 invariant
  ↓
產生 C
```

最後：

```text
C
```

已經跟最初：

```text
Product Goal
```

有一段距離。

---

# 7. 所以我現在不會直接叫你「換回 Opus 5 Code Agent」

這很重要。

我不認為：

> Plan Opus 5 + Code Opus 5

就會自動解決問題。

因為你現在的問題更像：

```text
              Model
                ↓
             Agent
                ↓
            Sprint Skill
                ↓
             Context
                ↓
          Existing artifacts
                ↓
             Next plan
```

其中任何一層 drift，都會累積。

甚至研究也開始看到：

> **同一 model 換 harness，結果就會明顯不同。**

有實驗直接發現，固定 model 後更換 scaffold/harness 仍會造成明顯差異；反過來，單純升級 model 也會帶來幾個百分點的改善。([GitHub][5])

所以真正應該控制的是：

# **Model × Harness × Skill × Context**

而不是只看 model。

---

# 8. 我現在反而會建議你做一次「Sprint archaeology」

這可能比繼續寫 Sprint 010 更有價值。

把：

```text
Sprint 001
Sprint 002
...
Sprint 009
```

做一張表：

| Sprint | Plan model | Code model | Skill version | Goal        | 新增什麼        | 最後是否保留 |
| ------ | ---------- | ---------- | ------------- | ----------- | ----------- | ------ |
| 001    | Opus       | ?          | v?            | MVP         | Theme/RS    | ✅      |
| 002    | Opus       | ?          | v?            | persistence | persistence | ?      |
| 003    | Opus       | ?          | v?            | replay      | replay      | ✅      |
| ...    |            |            |               |             |             |        |

然後再增加兩欄：

```text
Did this emerge from original product goal?
Did this create downstream complexity?
```

我懷疑你會看到一個很有意思的 pattern：

```text
原始 Product Goal
       ↓
少數核心功能
       ↓
Research curiosity
       ↓
Sprint spec
       ↓
Implementation
       ↓
「既然已有 X，那 Y 也合理」
       ↓
下一 sprint
       ↓
complexity
```

這會直接告訴我們：

> **MarketPulse 到底是哪一輪開始膨脹。**

---

# 9. 我甚至會建議把 Sprint Skill 暫時「降級」

不是模型降級。

是 **process 降級**。

目前我會讓下一版 Sprint Skill 只有：

```text
1. Re-read original product goal

2. Review current repo

3. Identify ONE user-visible problem

4. Propose smallest change

5. Explicitly list what NOT to change

6. Implement

7. Verify

8. Stop
```

尤其增加一條：

> **Every sprint must justify why the product would be worse without this sprint.**

而不是：

> 「這個 feature 很合理，所以做。」

---

# 10. 最重要的一條：每個 Sprint 都要重新對 Product Goal 做 reset

不要：

```text
Sprint 009
   ↓
Sprint 010
   ↓
Sprint 011
```

變成一條無限 inheritance chain。

應該是：

```text
                    Product Goal
                         ↑
                         |
Sprint 009 ──────────────┤
                         |
Sprint 010 ──────────────┤
                         |
Sprint 011 ──────────────┤
```

也就是：

**每一輪都向上看 Product Goal，而不是只向後看上一 Sprint。**

這會大幅降低「上一輪做了，所以這輪理所當然繼續做」的累積效應。

---

# 11. 所以我現在對 MarketPulse 的診斷會修正

上一輪我說：

> 「Research gravity」

現在加入你提供的 process 資訊後，我會改成：

### 第一層原因

**Sprint Skill 演進造成 process drift**

↓

### 第二層原因

**Plan Agent 很強，容易產生「合理但非必要」的 research scope**

↓

### 第三層原因

**Code Agent / Grok Build 比較偏 implementation，會忠實累積 scope**

↓

### 第四層原因

**下一輪 Plan 又把上一輪產物視為既定 context**

↓

### 最終結果

```text
合理的小決策
×
多輪
×
不同 process
×
不同 agent
=
現在這個有點胖的 MarketPulse
```

這其實是很典型的 **agentic development compounding effect**。

---

## 所以我會怎麼處理？

**不是重做 repo。**

也不是把所有 Sprint rollback。

我會做：

### `Sprint 010 — Process Reset`

不是 feature sprint。

目標只有：

```text
Original Product Goal
        ↓
Current Repo
        ↓
All Sprint History
        ↓
What is essential?
What is research-only?
What is accidental complexity?
        ↓
New Sprint Contract vNext
```

最後產出三個東西：

```text
PRODUCT_CORE.md
RESEARCH_LAB.md
SPRINT_CONTRACT_vNext.md
```

然後把目前所有東西標成：

```text
CORE
CONTEXT
RESEARCH
EXPERIMENTAL
DELETE / FREEZE
```

**這會比現在直接進 Sprint 010 再做一個 feature 健康非常多。**

而且你這次補充的「Plan 用 Opus 5、Code agent 混用次級模型/Grok Build、Sprint skill 中途改過幾次」，我認為確實足以改變我對目前 repo 演進的判斷：**不是單純 agent coding 品質問題，而是整個 agent pipeline 在多輪迭代後產生了累積偏移。**

如果你要繼續這個方向，我會建議下一步直接做 **Sprint archaeology + Process Reset**，而不是再 review 一次 code。

[1]: https://aicoding.club/blog/claude-opus-5-coding-agent-harness-recalibration/?utm_source=chatgpt.com "Claude Opus 5: Coding Agent Harnesses Need Recalibration | AI Coding Club"
[2]: https://www.anthropic.com/news/claude-opus-5?utm_source=chatgpt.com "Introducing Claude Opus 5 \ Anthropic"
[3]: https://www.superconductor.com/blog/grok-build-benchmark?utm_source=chatgpt.com "Grok Build is surprisingly competitive on our Personal SWE-Bench | Superconductor Blog"
[4]: https://kodus.io/en/grok-vs-opus/?utm_source=chatgpt.com "Grok 4.5 vs. Opus 5 coding comparison"
[5]: https://github.com/signalnine/thunderdome?utm_source=chatgpt.com "GitHub - signalnine/thunderdome: Benchmarks AI coding agents against 19 standardized tasks in isolated Docker containers with deterministic scoring · GitHub"
