I reviewed the current `dev` branch of **lalagrass/MarketPulse**. This is substantially more mature than the earlier MVP versions we looked at.

The repo currently has **130 commits**, 22 open issues, and the MVP specification explicitly considers the original MVP complete. ([GitHub][1])

## Overall verdict

**I would not expand the core signal right now.**

My rating:

| Area                  | Rating | Review                                                                                    |
| --------------------- | -----: | ----------------------------------------------------------------------------------------- |
| Product focus         |   9/10 | Very clear: Taiwan theme-rotation radar, not a fake quant platform                        |
| Architecture          | 8.5/10 | Small, understandable, appropriate for local daily batch                                  |
| Signal design         |   8/10 | Simple and defensible; importantly, no composite-score temptation                         |
| Data correctness      |   7/10 | Much improved, but still the biggest risk                                                 |
| Historical validation |   7/10 | Good foundations, but not yet enough to claim predictive usefulness                       |
| UX                    | 7.5/10 | Radar is becoming genuinely useful                                                        |
| Engineering hygiene   |   7/10 | Several known small debts remain                                                          |
| Scope discipline      |   9/10 | Excellent overall, though documentation/process is beginning to become its own complexity |

The most important conclusion is:

> **The project is now good enough that the next important question is no longer “what indicator should we add?” but “does this actually improve an investor's decision process?”**

That is a very good place to be.

---

# 1. The core architecture is now basically right

The central design is extremely clean:

`TWSE/TPEx → normalized data → 11 themes → theme aggregation → RS5/20/60 → ranks → Brief / Timeline / Radar → replay`

The primary ranking is still simply:

`RS20 = theme 20D return − TAIEX 20D return`

and `rank = cross-sectional rank(RS20)`. 

That is exactly the right degree of sophistication for this project.

I especially like that the repo explicitly refuses:

* rotation score
* weighted rank composites
* alpha score
* confidence score
* ML prediction
* generic backtest framework
* custom TA implementations

Those are all classic ways this kind of project slowly turns into an unmaintainable science project. 

### Keep this.

I would actually make this the strongest product principle:

> **MarketPulse is a measurement and observation system, not an optimization system.**

---

# 2. The three-horizon rank display is better than I initially expected

The current `R5 · #R20 · R60` representation is a good compromise.

You are not constructing:

`0.2 × RS5 + 0.5 × RS20 + 0.3 × RS60`

Instead you're exposing three independent ranks and forcing the user to interpret the shape. 

Example:

`3 · #1 · 7`

means:

* short-term: #3
* primary 20D: #1
* long-term: #7

That is much more informative than a single mysterious score.

And it aligns with the actual empirical observation that rank persistence decays rapidly with horizon. The repo's latest measured result shows roughly:

* k=1: 0.9307
* k=5: 0.7167
* k=20: 0.1404

with the 20-day result about +2.84σ over its circular-shift null. 

This is one of the strongest pieces of work in the repo because it prevents the product from accidentally pretending that theme leadership is stable.

---

# 3. The biggest product risk is no longer the ranking formula

It's **theme taxonomy + constituent data quality**.

The current theme file is intentionally frozen at 11 themes and explicitly says historical replay is using today's taxonomy, not reconstructing historical knowledge. 

That is honest.

But it creates an important limitation:

### A historical replay can tell us

> "If I apply today's definition of AI server to 2025 data, this is what the ranking would have looked like."

It cannot tell us:

> "An investor in 2025, using the information available at that time, would have seen AI server as this theme."

The repo already acknowledges this distinction. 

For visualization, that's fine.

For **forward-performance validation**, it becomes much more important.

So I think the current backlog item:

> `as-of 成分股仍缺`

is actually one of the few genuinely important future pieces. 

Not because the MVP needs it.

Because **your future research results will eventually depend on it**.

---

# 4. The next major technical issue: adjusted-price effects

This is more important than adding another indicator.

The current theme returns are calculated directly from close prices. 

And your own backlog has already identified the ex-rights/ex-dividend issue.

That matters because a theme with several stocks undergoing ex-dividend or ex-right adjustments can look artificially weak even though economically the underlying holdings didn't suddenly collapse.

You already have the correct instinct:

> **measure the size of the distortion before changing the methodology.**

The backlog explicitly says not to change the price methodology until the impact is measured. 

I strongly agree.

### I would prioritize this over almost every new signal.

A very simple research output would be:

```text
theme
raw RS20
estimated ex-right impact
RS20 after adjustment
rank change
```

Then ask:

> Does ex-right adjustment actually change the top 3–5 themes often enough to matter?

If answer = rarely, leave the core alone.

If answer = frequently, fix it.

That is exactly the sort of evidence-driven change MarketPulse should make.

---

# 5. The Rank-IC work is useful, but don't overinterpret it

The forward Rank-IC addition was a good decision.

The current evidence roughly shows:

| Current RS window | Forward 5D | Forward 20D | Forward 60D |
| ----------------- | ---------: | ----------: | ----------: |
| RS5               |     +0.034 |      +0.084 |      +0.071 |
| RS20              | **+0.099** |  **+0.140** |  **+0.161** |
| RS60              |     +0.085 |      +0.140 |      +0.195 |

with sample sizes around a few hundred sessions. 

The repo correctly concluded this is **not enough to turn MarketPulse into a prediction product**.

That's the right interpretation.

The especially good part is that you corrected an earlier mistake where the raw IC numbers were being interpreted without an appropriate null comparison. The repo explicitly records that correction. 

### My only concern

With only **11 themes**, Rank-IC should be regarded as **diagnostic evidence**, not strong predictive evidence.

And overlapping themes make independence even murkier.

So I would not spend the next sprint improving the statistical machinery.

Instead:

> use the current Rank-IC infrastructure to answer practical questions.

For example:

**When a theme reaches rank #1, what happens over the next 5/10/20 sessions?**

That is much closer to what you actually care about as an investor.

---

# 6. The Radar has become the real product

Looking at the current code, the Radar now combines:

* 1D / 5D / 20D
* RS20
* breadth
* volume
* three-horizon rank
* rotation
* momentum state
* narrative information
* sector drill-down
* leader/follower/laggard stocks

without collapsing them into one number. 

That's good design.

The strongest design choice here is:

> **Momentum is display-only.**

The state is derived from existing evidence rather than being fed back into ranking. 

This prevents:

```text
RS20
  ↓
rank
  ↓
momentum
  ↓
momentum score
  ↓
new rank
```

which would create a circular methodology.

---

# 7. But the repo is starting to over-document itself

This is the one area where I think you should be careful.

The code is still fairly small.

But the surrounding system has become large:

* design spec
* coding contract
* methodology
* backlog
* open questions
* sprint specs
* sprint reports
* evidence
* decision history
* retro
* rule challenges
* source notes

And there are already examples where the documentation itself records mistakes, corrections, superseded interpretations, rule exceptions, etc. 

That's useful during development.

But I'm beginning to see a real risk:

> **The process surrounding MarketPulse may become more complicated than MarketPulse.**

This is exactly the concern you've raised before about having too many skills / agents / process rules.

The current repo is approaching the point where:

```text
Product complexity
    <
Process complexity
```

That is something I'd actively prevent.

### Recommendation

Keep only four authoritative layers:

```text
1. Product spec
2. Current methodology
3. Backlog
4. Sprint evidence/report
```

Everything else should be disposable/history.

Don't create another framework to manage the frameworks.

---

# 8. The current open issues are actually pretty healthy

The open issues show the project is no longer missing fundamental functionality.

The top issues are things like:

* null-baseline reporting bug
* TWSE 307 fallback documentation
* `.gitignore`
* missing LICENSE
* overlap/concentration diagnostics
* narrative UX
* i18n
* static-site packaging
* sparklines
* UI widths
* planning/merge process

rather than "we need another giant feature". ([github.com][2])

That's a strong sign.

### One issue I would fix immediately

The null-baseline issue is real:

the code now has the intended `無基準` behavior when the null baseline is unavailable, but the GitHub issue remains open. ([GitHub][3])

That should not remain hanging around because this is exactly the kind of thing that undermines trust in the report.

---

# 9. One engineering smell worth fixing later

`calc.py` is doing quite a lot.

The main pipeline currently:

* pivots data
* computes returns
* computes SMA
* aggregates themes
* computes breadth
* calculates value share
* handles missing data
* calculates ranks
* calculates rank deltas
* generates status

inside one fairly large computation path. 

For this MVP, that's acceptable.

I would **not refactor it now just because it looks long**.

The backlog itself identifies things like `missing_count` loops and duplicate formatting helpers, but correctly says some should wait until they have real evidence of cost. 

That is the correct engineering philosophy here:

> **Don't refactor because code can theoretically be cleaner. Refactor when the architecture is blocking the next meaningful product change.**

---

# 10. The most interesting unused asset: narratives

I think this may eventually be more important than another technical indicator.

The repo now has a narrative layer and real dated snapshots.

And the backlog is already considering branch/basket structures such as:

```text
if_true
if_false
either_way
```

so that one event can be interpreted as:

```text
scenario A beneficiaries
scenario B beneficiaries
common upstream beneficiaries
```

That's actually quite powerful.

It could eventually turn MarketPulse into:

```text
Theme strength
      ↓
What is leading?
      ↓
Why might it be leading?
      ↓
Who benefits under each scenario?
      ↓
Does price confirm the narrative?
```

That is much more interesting than:

```text
RS20 → RSI → MACD → Bollinger → another score
```

And importantly, it remains compatible with the project's philosophy because the narrative layer can remain **separate from the primary quantitative rank**.

I would pursue this, but slowly.

---

# 11. What I would NOT build next

I would explicitly reject these for now:

**RRG**

The repo already correctly killed this as a non-goal. Good.

**More technical indicators**

KD, RSI, MACD, Bollinger, etc. are not solving the core problem.

**Composite score**

Definitely not.

**AI prediction**

Way too early.

**Generic backtesting framework**

Also unnecessary for the current product.

**Real-time dashboard**

Not aligned with the current use case.

The design document's non-goals already make most of these explicit. 

---

# 12. What I would do next

I would shift the project from:

> **MVP construction**

to:

> **MVP usefulness validation**

The next development arc should look like this:

### Phase A — Clean up trust issues

Fix:

1. null-baseline reporting
2. raw-data manifest / reproducibility
3. timezone / trading-calendar edge cases
4. stale/dead code
5. small UX issues that directly affect reading

The repo already has evidence for these problems. 

### Phase B — Measure data distortions

Especially:

```text
ex-right / ex-div impact
theme overlap concentration
missing data
theme membership concentration
```

But these should remain **diagnostics**, not new ranking inputs.

### Phase C — Answer the investor question

This is the one I would make the next **real L1 priority**:

> **When MarketPulse says a theme is strong, what tends to happen afterwards?**

Not a trading strategy.

Just produce evidence like:

```text
Theme reaches #1

5D forward:
+X%

10D:
+Y%

20D:
+Z%

Probability positive:
A%

Compared with:
market
rank #2
rank #3
```

Then slice it by:

```text
#1 + improving
#1 + weakening
#2 → #1
#5 → #2
R5 #1 / R20 #6
R5 #6 / R20 #1
```

This is vastly more valuable than adding another indicator.

---

# My biggest recommendation

I would make the next milestone:

> **“Can MarketPulse reliably identify an interesting theme transition early enough to be useful to a human investor?”**

Not:

> “Can we make the score smarter?”

That distinction is important.

Right now the system already has enough raw ingredients to answer the first question:

* multi-horizon relative strength
* rank movement
* breadth
* volume
* stock drill-down
* historical replay
* forward Rank-IC
* narrative overlays

The missing piece is **bringing these together into a controlled historical observation study**, without turning them into another composite score.

That is where I think the project can go from **“well-built analytics MVP” → “actually useful investment tool.”**

And I would resist adding much more infrastructure until that experiment tells us what information is genuinely useful. 

[1]: https://github.com/lalagrass/MarketPulse "GitHub - lalagrass/MarketPulse · GitHub"
[2]: https://github.com/lalagrass/MarketPulse/issues?q=is%3Aissue+is%3Aopen "Issues · lalagrass/MarketPulse · GitHub"
[3]: https://github.com/lalagrass/MarketPulse/issues/23 "[bug] 無 null baseline 時品質行勿印無旁證單日持續性 · Issue #23 · lalagrass/MarketPulse · GitHub"
