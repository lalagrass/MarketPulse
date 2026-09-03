# MarketPulse 市場觀測方法論

> **文件定位：方法論說明，不是產品規格。**
>
> 本文件描述 MarketPulse 背後的市場觀測框架：要觀察什麼、為什麼觀察，以及哪些內容刻意不納入系統。
>
> 實際產品公式、資料規則與 CLI 行為，以 `docs/design-v0.2.md` 為準。若兩者衝突，以產品設計文件為準。

**產品定位：**

> MarketPulse 是一個以收盤後資料為基礎、採用 Human-in-the-loop（人在迴路）的市場觀測工具，協助投資人理解**市場環境、主題廣度、相對強弱與資金輪動**。

它不是交易機器人、價格預測器，也不是自動投資組合管理工具。

---

## 0. 如何閱讀本文件

| 問題                    | 對應章節  |
| --------------------- | ----- |
| MarketPulse 的核心方法是什麼？ | §2–§3 |
| 系統觀察哪些市場現象？           | §4    |
| 哪些概念已經進入產品？           | §5–§6 |
| 哪些東西刻意不做？             | §7    |
| 新的投資研究應該如何加入？         | §9    |

核心原則：

> **先觀察，再解讀，最後才做決策。**

MarketPulse 的責任是把市場結構與變化呈現出來，而不是假裝一個固定公式可以取代投資人的判斷。

系統主要回答：

> **目前市場的領導力量集中在哪裡？哪些主題正在轉強？哪些正在轉弱？資金輪動正在往哪裡發生？**

而不是：

> **現在應該買哪一檔？**

---

# 1. 研究來源與方法論的分離

MarketPulse 的方法論受到公開投資討論、市場評論與社群研究中反覆出現的市場觀察所啟發，包括：

* 市場環境（Market Regime）
* 類股／主題輪動（Sector / Theme Rotation）
* 相對強弱（Relative Strength）
* 動能（Momentum）
* 市場廣度（Breadth）
* 資金輪動（Capital Rotation）
* 領導股／領先主題（Leadership）
* 流動性與市場容量（Liquidity & Market Capacity）
* 基本面確認（Fundamental Confirmation）
* 回撤與曝險管理（Drawdown & Exposure Management）

這些概念並不屬於任何單一投資人或評論來源，而是金融市場分析中普遍存在的概念。

因此，MarketPulse 的產品方法論應該使用**一般金融與投資研究領域的語言**，而不是綁定特定人物、節目或內容來源。

---

## 1.1 研究來源應獨立保存

原始研究來源、Podcast、文章、社群討論、逐字稿與歷史筆記，應保留在本機的 research / provenance 區域：

```text
docs/research/
```

這層**不進 git**。產品文件只使用通用金融術語。

這些資料的用途是：

1. 保存方法論形成的背景。
2. 方便日後追溯某個設計決策的來源。
3. 避免產品方法論與單一來源產生耦合。

因此：

```text
Research Source
      ↓
觀察與歸納
      ↓
通用金融概念
      ↓
MarketPulse Methodology
      ↓
Product Design
```

而不是：

```text
某個人的說法
      ↓
直接變成產品公式
```

---

# 2. 一句話描述 MarketPulse 方法論

> **先判斷市場環境，再觀察主題廣度與資金輪動；透過相對強弱辨識領先與改善中的主題，最後在強勢主題內尋找領導標的，而不是單純追逐跌深反彈。**

整體流程：

```text
市場環境
  ↓
主題廣度
  ↓
相對強弱
  ↓
資金輪動
  ↓
主題領導
  ↓
人工判斷
```

MarketPulse 刻意採用：

> **觀測（Observation）而非預測（Prediction）**

---

# 3. MarketPulse 市場觀測流程

## 3.1 市場環境（Market Regime）

首先判斷整體市場環境。

同一個「相對強勢」訊號，在不同市場環境下可能代表完全不同的事情。

例如：

```text
大盤上漲
+
某主題大幅上漲
=
真正的市場領導

大盤下跌
+
某主題跌得比較少
=
相對抗跌，但不一定代表 Risk-on
```

因此：

> **相對強弱不能脫離市場環境解讀。**

MarketPulse 使用 TAIEX 作為主要市場基準。

---

## 3.2 主題廣度（Theme Breadth）

判斷一個主題是否是「整體在動」，而不是只有單一股票上漲。

例如：

```text
單一股票大漲
    ≠
整個主題轉強

多數成分股同步上漲
+
相對強弱提升
=
更強的主題級訊號
```

可以觀察：

* 主題報酬
* 上漲／下跌參與度
* 成交值占比
* 成交值動能

MarketPulse 的主題並不一定等同交易所正式產業分類，而是以投資故事、供應鏈與市場主題建立。

例如：

* AI
* 光通訊
* 散熱
* CCL
* 半導體設備

主題可以重疊。

---

## 3.3 相對強弱（Relative Strength）

相對強弱是 MarketPulse 的核心排序概念。

目前：

```text
RS20 = 主題 20 日報酬 - TAIEX 20 日報酬
```

`RS20` 是目前主要排序訊號。

其核心思想：

> **不要只問一個資產漲了多少，而要問它相對於市場表現得多好。**

因此：

* 上漲很多 → 可能是強勢
* 下跌很少 → 可能是抗跌
* 長期跌深 → 不代表即將反轉
* 低價 → 不等於便宜
* 跌幅很大 → 不應自動轉化成正面分數

MarketPulse 因此偏向：

> **Momentum / Relative Strength**

而不是：

> **Mean Reversion / 抄底**

---

## 3.4 資金輪動（Capital Rotation）

市場領導不是靜態的。

今天領先的主題，可能在幾週後轉弱；原本落後的主題，也可能開始改善。

MarketPulse 目前使用四種狀態：

| 狀態               | 意義               |
| ---------------- | ---------------- |
| **領先 Leading**   | 相對強勢，且持續維持市場領導   |
| **改善 Improving** | 相對強弱正在改善，可能形成新領導 |
| **轉弱 Weakening** | 過去強勢，但相對表現正在惡化   |
| **落後 Lagging**   | 持續弱於市場           |

重點不是預測「下一個一定會漲什麼」。

而是讓使用者看到：

> **市場領導力量正在如何變化。**

其中一個重要觀察是：

> **改善中的主題值得持續觀察，因為輪動是一個過程，而不是單日排名。**

---

## 3.5 主題領導（Theme Leadership）

在確認強勢主題後，再進一步觀察主題內的個股。

核心順序：

```text
市場
  ↓
主題
  ↓
主題內領導
  ↓
個股
```

而不是：

```text
先掃所有股票
  ↓
找今天漲最多的
  ↓
再解釋它屬於哪個主題
```

在強勢主題中，仍然應該優先觀察相對強勢、具領導特徵的標的。

目前由 Sector Radar 的主題下鑽提供：成分股按個股 RS20 分成 Leader / Follower / Laggard。這是觀測列表，不是買進清單。主題 Rank 仍只由主題 RS20 決定。

---

## 3.6 流動性與市場容量（Liquidity & Market Capacity）

「強勢」不等於「可以承接大量資金」。

某些小型標的可能具有非常強的價格動能，但：

* 市值較小
* 成交值較低
* 市場深度有限
* 大型資金難以進出

因此：

> **Strength ≠ Capacity**

可作為背景資訊的觀察包括：

* 成交值
* 成交值占比
* 市值
* 流動性
* 主題成交值集中程度

目前 MVP 已有：

```text
value_share
value_thrust
```

這些屬於輔助資訊。

它們不應在沒有研究驗證的情況下，偷偷加入 `RS20` 成為另一個複合分數。

---

## 3.7 基本面確認（Fundamental Confirmation）

MarketPulse 的核心是**市場行為觀測**，不是基本面估值系統。

基本面主要扮演：

> **確認市場行情是否具有基本面支撐**

的角色。

概念上：

```text
價格 / 成交量
      +
主題結構
      +
基本面證據
      ↓
更完整的投資研究假設
```

可能的基本面證據包括：

* 營收成長
* EPS / 獲利成長
* 財測
* 產業需求
* 供需狀況
* 產能擴張
* 訂單能見度

但 MarketPulse 不應在 MVP 中試圖計算：

* 合理價
* 目標價
* 內在價值
* 自動估值
* EPS-based Buy/Sell Score

這些屬於另一個產品問題。

---

## 3.8 趨勢與動能（Trend & Momentum）

MarketPulse 使用少量、可解釋的價格與量價訊號。

目的不是建立完整的技術分析平台。

目前主要觀察：

* N 日報酬
* SMA
* 相對排名
* Breadth
* Volume ratio
* Radar Momentum State（Strong / Improving / Stable / Weakening / Weak）

刻意不因為「技術分析工具很多」就加入：

* KD / Stochastic
* MACD
* RSI
* Bollinger Bands
* K 線型態辨識

除非未來研究證明這些指標提供現有框架無法取得的資訊。

核心原則：

> **少量、可解釋、與產品問題直接相關。**

---

## 3.9 風險環境與曝險（Risk Regime & Exposure）

市場領導存在於更大的風險環境之中。

例如：

```text
強勢主題
+
市場結構惡化
+
領導快速切換
=
較高的輪動風險
```

這時 MarketPulse 的責任是：

> **讓市場結構變化變得可見。**

而不是：

> **自動要求使用者賣出。**

曝險、部位大小、避險與現金比例，屬於使用者自己的風險管理決策。

---

# 4. 核心方法論卡片

每一個市場概念都應遵循：

```text
市場原則
  ↓
要觀察什麼
  ↓
MarketPulse 如何實作
  ↓
目前狀態
```

---

## 4.1 市場環境（Market Regime）

### 市場原則

整體市場環境會影響所有相對強弱訊號的解讀。

### 觀察

* TAIEX 趨勢
* 市場報酬
* 市場廣度
* Risk-on / Risk-off 環境

### MarketPulse

目前以 TAIEX 作為主要 benchmark。

`RS20`：

```text
RS20 = Theme Return 20D - TAIEX Return 20D
```

### 狀態

**部分實作。**

RS20 已包含 benchmark-relative 概念，但 Brief 對市場環境的獨立呈現仍可加強。

---

## 4.2 主題廣度（Theme Breadth）

### 市場原則

主題內參與者越廣，主題級訊號通常越具有代表性。

### 觀察

* Theme Return
* Breadth
* Value Share
* Value Thrust

### MarketPulse

目前：

```text
11 個固定主題
+
Equal-weight Theme Return
+
Breadth
+
Value Share
```

### 狀態

**已實作。**

---

## 4.3 相對強弱（Relative Strength）

### 市場原則

相對表現通常比單純價格高低更適合辨識市場領導。

### 觀察

* Benchmark-relative Return
* Momentum
* Cross-sectional Rank

### MarketPulse

目前：

```text
RS20
```

為主要排序訊號。

### 狀態

**已實作。**

### 設計限制

不要為了增加複雜度而建立：

```text
RS20
+
Breadth
+
Volume
+
SMA
+
Value Share
=
Composite Score
```

除非未來有獨立研究證明其必要性。

---

## 4.4 資金輪動（Capital Rotation）

### 市場原則

市場領導會隨時間改變。

### 觀察

```text
領先
改善
轉弱
落後
```

以及狀態之間的轉換。

### MarketPulse

目前透過：

* Rank
* Δ5
* 四狀態分類
* Timeline

觀察輪動。

### 狀態

**已實作。**

---

## 4.5 主題領導（Theme Leadership）

### 市場原則

找到強勢主題後，再找主題內的相對強勢標的。

### 觀察

```text
Leading Theme
      ↓
Theme Constituents
      ↓
Relative Strength
      ↓
Leadership
```

### MarketPulse

`marketpulse radar` / `reports/radar.html`：點進主題後，成分股依個股 RS20 分成 Leader / Follower / Laggard。

不改變主題 RS20 排序。不是 Buy List。

### 狀態

**已實作。**

---

## 4.6 流動性與市場容量（Liquidity & Market Capacity）

### 市場原則

價格強勢不代表可以承接大量資金。

### 觀察

* Trading Value
* Market Cap
* Value Share
* Liquidity

### MarketPulse

目前使用：

```text
value_share
value_thrust
```

作為輔助資訊。

### 狀態

**部分實作。**

---

## 4.7 基本面確認（Fundamental Confirmation）

### 市場原則

價格告訴我們市場正在做什麼。

基本面可以協助理解：

> 為什麼市場可能這樣做？

### 觀察

* Revenue
* Earnings
* Guidance
* Industry Demand
* Supply / Demand
* Capacity
* Orders

### MarketPulse

目前不計算估值或 EPS 評分。

主題分類由人工維護。

### 狀態

**刻意限制。**

---

## 4.8 趨勢與動能（Trend & Momentum）

### 市場原則

使用少量趨勢與動能訊號輔助辨識市場領導。

### MarketPulse

目前使用：

* N-day Return
* SMA
* Rank
* Breadth
* Volume ratio
* Radar Momentum State

Momentum 與 Rotation 分開：Rotation 是相對前一交易日的名次；Momentum 是 5D / Breadth / Volume / Rank Δ5 的方向狀態。不是 Momentum Score，也不改變 RS20 排序。

### 狀態

**已實作。** Sector Radar 顯示 Strong / Improving / Stable / Weakening / Weak；歷史不足時為 Unknown。

---

## 4.9 人在迴路（Human-in-the-loop）

### 市場原則

市場沒有單一公式可以在所有環境下做出正確決策。

### MarketPulse

系統提供：

```text
Observation
    ↓
Classification
    ↓
Context
    ↓
Historical Comparison
```

使用者負責：

```text
Interpretation
    ↓
Investment Thesis
    ↓
Risk Assessment
    ↓
Decision
```

因此系統不應直接產生：

* 買進
* 賣出
* 必須進場
* 必須出場
* 自動部位大小
* 自動槓桿
* 自動調整投資組合

### 狀態

**已實作。**

---

# 5. MarketPulse 方法論與產品功能對照

| 市場概念                     | 意義        | 目前實作                       | 狀態     |
| ------------------------ | --------- | -------------------------- | ------ |
| Market Regime            | 大盤與整體市場環境 | TAIEX + RS20 Benchmark     | 部分     |
| Theme Breadth            | 主題參與廣度    | 11 Themes + Breadth        | 已實作    |
| Theme Return             | 主題整體表現    | Equal-weight Return        | 已實作    |
| Relative Strength        | 相對市場強弱    | RS20                       | 已實作    |
| Capital Rotation         | 市場領導轉換    | 四狀態 + Timeline             | 已實作    |
| Theme Leadership         | 主題內領導標的   | Radar Leader / Follower / Laggard | 已實作    |
| Liquidity / Capacity     | 市場容量      | Value Share / Value Thrust | 部分     |
| Fundamental Confirmation | 基本面支撐     | 人工維護 Theme Knowledge       | 刻意限制   |
| Trend & Momentum         | 趨勢與動能     | Radar Momentum State（5D / Breadth / Volume / Rank Δ5） | 已實作    |
| Historical Context       | 歷史輪動      | Timeline + Replay          | 已實作    |
| Human Decision           | 人工判斷      | Brief / Radar / CLI        | 已實作    |

---

# 6. MVP 核心縱向切片

目前 MVP 應維持非常簡單：

```text
官方 EOD 資料
      ↓
11 Themes
      ↓
Theme Returns
      ↓
RS20
      ↓
Rank
      ↓
Leading / Improving / Weakening / Lagging
      ↓
Brief
      ↓
Radar (theme table + Momentum State + stock drill-down)
      ↓
Timeline
      ↓
Replay
```

這是 MarketPulse 的 MVP spine。

目前最重要的不是加入更多指標，而是確保：

> **這條鏈能穩定、正確、可回放地描述市場輪動。**

---

# 7. 明確不納入 MVP

以下內容即使出現在投資討論中，也不應僅因為「有人提過」就加入 MarketPulse。

## 7.1 微觀結構與盤中交易

* 券商分點
* 五檔掛單
* Level 2
* 訂單牆
* 程式交易偵測
* 當沖
* 盤中交易策略
* 隔夜交易
* 期貨轉倉
* 盤中避險

---

## 7.2 融資與槓桿

* 追繳保證金預測
* 強制平倉預測
* 融資維持率策略
* 自動槓桿
* 自動部位調整
* 質押策略

---

## 7.3 公司行為套利

* 可轉債套利
* 現金增資套利
* 特殊處置股策略
* 公司行為事件交易

---

## 7.4 自動交易

* 自動停損
* 自動停利
* 自動進場
* 自動出場
* 自動再平衡
* 自動交易
* 自動槓桿

---

## 7.5 為了複雜而複雜

以下不是 MVP 的目標：

```text
更多指標
+
更多權重
+
更多分數
+
更多參數
=
更好的產品
```

MarketPulse 的目標是：

> **用最少的、可解釋的訊號，把市場輪動清楚地呈現出來。**

---

# 8. 設計原則

## 8.1 優先使用既有金融術語

不要為了建立品牌感而重新發明市場術語。

優先使用：

```text
Market Regime
市場環境

Theme Breadth
主題廣度

Relative Strength
相對強弱

Momentum
動能

Capital Rotation
資金輪動

Leadership
領導

Liquidity
流動性

Market Capacity
市場容量

Fundamental Confirmation
基本面確認

Risk Regime
風險環境

Drawdown
回撤

Exposure
曝險
```

---

## 8.2 一個主要排序訊號

`RS20` 是目前主要排序訊號。

其他指標主要提供 context，而不是偷偷成為額外權重。

因此目前不要建立：

```text
Rotation Score
Leadership Score
Theme Score
Market Score
```

等一堆無法解釋的 composite score。

---

## 8.3 觀察優先於預測

MarketPulse 應該主要描述：

```text
發生了什麼
      ↓
什麼正在改變
      ↓
市場領導正在往哪裡移動
```

而不是：

```text
明天一定會漲
      ↓
所以應該買
```

---

## 8.4 主題優先於個股

核心順序：

```text
Market
  ↓
Theme
  ↓
Leadership
  ↓
Security
```

而不是：

```text
Security
  ↓
猜故事
  ↓
找 Theme
```

---

## 8.5 不允許未來資訊污染歷史

Replay 必須只使用當時已知資訊。

不能：

> 用今天知道的主題定義、成分股或市場分類，假裝這些資訊在過去就已經存在。

尤其要注意：

* Theme membership 的變化
* Theme taxonomy 的變化
* 後見之明產生的分類
* 事後知道的產業故事

Historical Replay 的目標是：

> **重建當時可以觀察到的市場狀態。**

而不是：

> **用今天的知識重新解釋過去。**

---

## 8.6 避免虛假的精確度

不要因為計算出小數點後兩位，就假裝模型更加準確。

例如避免：

```text
Rotation Score = 73.82
```

如果這個數字本身沒有清楚的統計意義。

相較之下：

```text
Leading
Improving
Weakening
Lagging
```

更容易理解，也更符合 MarketPulse 的用途。

---

## 8.7 人在迴路

MarketPulse 是：

> **Decision-support tool**

而不是：

> **Automated trading system**

理想流程：

```text
MarketPulse
    ↓
觀察
    ↓
理解
    ↓
研究
    ↓
人工決策
```

而不是：

```text
MarketPulse
    ↓
Signal
    ↓
Automatic Trade
```

---

# 9. 新研究如何進入 MarketPulse

方法論應該**慢慢演化，而不是看到一個新觀點就加一個新功能。**

## Step 1 — 保存研究

新的文章、Podcast、社群討論或投資觀點，首先進入本機：

```text
docs/research/
```

這層不進 git。不要直接修改產品公式。

---

## Step 2 — 找出可泛化的市場概念

例如一個來源提出：

> 「某類股開始有族群性。」

先不要直接建立：

```text
xxx_score
```

而是抽象成：

> **Theme Breadth / Participation**

---

## Step 3 — 使用一般金融術語

例如：

| 原始口語概念    | MarketPulse 術語                    |
| --------- | --------------------------------- |
| 「誰先回來」    | Relative Strength Recovery        |
| 「強勢族群」    | Leading Theme                     |
| 「輪進來」     | Improving / Emerging Leadership   |
| 「轉弱」      | Weakening                         |
| 「族群性」     | Theme Breadth / Participation     |
| 「錢跑去哪裡」   | Capital Rotation                  |
| 「買裡面最強的」  | Cross-sectional Leadership        |
| 「資金胃納」    | Liquidity & Market Capacity       |
| 「基本面安全措施」 | Fundamental Confirmation          |
| 「心法」      | Decision Framework                |
| 「看大盤」     | Market Regime                     |
| 「做強、不抄跌深」 | Momentum / Relative Strength Bias |

---

## Step 4 — 分離方法論與產品實作

如果新的研究概念需要產品改動：

```text
研究
 ↓
方法論
 ↓
Product Increment
 ↓
design-v0.2.md
 ↓
Implementation
```

不要因為一段市場評論很有道理，就直接修改 `calc.py`。

---

## Step 5 — 保留研究來源

研究來源仍然應該保存：

* 來源
* 日期
* 原始背景
* 觀察內容
* 為什麼最後被抽象成某個金融概念

但這些內容不應成為公開產品方法論的必要閱讀背景。

---

# 10. 後續產品演進

目前最合理的下一步不是一次增加所有功能。

## Increment 1 — 強化 Market Regime

在 Brief 顯示：

```text
TAIEX 20D Return
Market Direction
Theme Relative Strength
```

讓使用者更容易理解：

> 「Leading」到底是在什麼樣的市場環境下發生？

---

## Increment 2 — Theme Leadership

**已實作。** `reports/radar.html` 對每個主題列出 Leader / Follower / Laggard。仍是觀測工具，不是 Buy List。

---

## Increment 2b — Sector Momentum State

**已實作。** Radar 對每個主題顯示 Strong / Improving / Stable / Weakening / Weak，並在下鑽區列出 5D / 20D / Breadth / Volume / Rank Δ5 的方向。不引入 Momentum Score，不改變 RS20 Rank。

---

## Increment 3 — Liquidity / Capacity Context

增加：

* Trading Value
* Market Cap
* Liquidity Context

但仍不直接改變 `RS20`。

---

## Increment 4 — Theme Synchronization

觀察不同主題或供應鏈是否同步轉強。

例如：

```text
AI Infrastructure
      +
Optical
      +
Power
      +
Cooling
```

如果多個相關主題同步改善，可能代表更廣泛的產業資金流動。

這是未來功能，不是 MVP 必要條件。

---

## Increment 5 — Historical Rotation Analysis

進一步利用 Replay：

> 某個主題從 Lagging → Improving → Leading 的過程通常長什麼樣？

這可以逐步形成 MarketPulse 的歷史市場研究能力。

---

# 11. MarketPulse 的核心問題

MarketPulse 最終不是要回答：

> **「哪一檔股票明天會漲？」**

而是：

> **「目前市場的領導力量集中在哪裡？」**

以及：

> **「哪些主題正在變強、哪些正在變弱？」**

再進一步：

> **「這些變化是在什麼市場環境下發生的？」**

因此 MarketPulse 的核心分析鏈是：

```text
市場環境
    ↓
主題廣度
    ↓
相對強弱
    ↓
資金輪動
    ↓
領導主題
    ↓
主題內領導
    ↓
人工研究與決策
```

---

# 12. 最終方法論摘要

如果只能用一句話描述 MarketPulse：

> **MarketPulse 透過市場環境、主題廣度、相對強弱與資金輪動，辨識市場領導力量正在集中、形成或消退的位置，並將結果交給投資人進一步研究與判斷。**

核心思想：

```text
        市場環境
           │
           ▼
        主題廣度
           │
           ▼
        相對強弱
           │
           ▼
        資金輪動
           │
      ┌────┴────┐
      ▼         ▼
    領先       改善
      │         │
      └────┬────┘
           ▼
       主題領導
           │
           ▼
       人工解讀
           │
           ▼
        投資決策
```

**MarketPulse 的價值不是預測市場，而是讓市場輪動變得可觀察、可比較、可回放。**

---

# 13. 文件與命名

產品-facing 文件：

```text
docs/design-v0.2.md              產品規格
docs/coding-contract.md          工程契約
docs/reuse-plan.md               OSS 邊界
docs/marketpulse-methodology.md  觀測方法論（本文件；不是規格）
```

來源研究只留本機，不進 git：

```text
docs/research/
```

產品文件只使用通用金融術語。來源名稱、單集、文章與原始筆記留在本機 research 層。

---

# 14. 變更紀錄

| 日期         | 變更                                                                                                                                                                                                             |
| ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2026-09-03 | 將原有來源導向的投資觀察整理，抽象為 MarketPulse 通用市場觀測方法論。統一使用 Market Regime、Theme Breadth、Relative Strength、Capital Rotation、Leadership、Liquidity & Market Capacity 等金融術語。保留 RS20 為主要排序訊號，不引入 Composite Score，並明確分離研究來源與產品方法論。 |
| 2026-09-03 | 產品文件改指本檔；來源研究改為本機 `docs/research/`（不進 git）。Theme Leadership / Radar 標為已實作。 |
| 2026-09-03 | Radar 新增 Momentum / Trend State（Strong / Improving / Stable / Weakening / Weak / Unknown）。由既有 5D、Breadth、Volume、Rank Δ5 與五個交易日前的快照比較，不是新指標也不是分數。Rank 仍為 RS20。 |
