# Sprint 015 — 物證

由實作端寫。格式見 `015-spec.md`「回報時必須附的物證」。
分支 `sprint/015-price-resets`，自 `dev@3bc1805`（014 併入之後的 hotfix）。**未併入。**

---

## §1 commit hash

| DO | hash | 標題 |
|---|---|---|
| DO-1 | `9b04812` | feat(015 DO-1): 籃子窗內有價格斷點就在面板上標出來 |
| DO-2 | `01c8e84` | chore(015 DO-2): 買資訊 — 價格斷點分「回得去／回不去」 |
| DO-3 | `e19ca2a` | fix(015 DO-3): F8 判準改成「單一 theme_id 跨兩則以上故事」 |

## §2 `uv run pytest` 的實際摘要行

在 `e19ca2a`（分支尖端）上執行 `uv run pytest`：

```text
340 passed in 61.80s (0:01:01)
```

同一台機器、同一份 `data/`，`dev@3bc1805` 上是：

```text
326 passed in 63.70s (0:01:03)
```

新增 14 個測試，零 skip、零 xfail、零 fail。

## §3 `git diff dev --stat`

```text
 marketpulse/baskets.py          | 226 +++++++++++++++++++++++++----
 scripts/price_break_recovery.py | 156 ++++++++++++++++++++
 tests/test_baskets.py           | 314 +++++++++++++++++++++++++++++++++++++++-
 3 files changed, 665 insertions(+), 31 deletions(-)
```

`marketpulse/calc.py` 不在清單裡 —— `impossible_daily_returns` 只被讀取。
`cli.py` 也不在：`compute_basket_metrics` 本來就收到 `bars` 與 `themes`，
偵測在函式內部用同一份 as-of 過的 `work` 跑，不必再從 CLI 傳一次。
spec 的「會動到的檔案」把 `cli.py` 列進去，實際上不需要動。

## §4 G3／G4 — 本輪前後 `uv run marketpulse baskets` 的輸出與 diff

兩份都是 `uv run marketpulse baskets --as-of 2026-09-08`。
「前」＝ `dev@3bc1805`；「後」＝ DO-1 之後（`9b04812`，尚未含 DO-3 的提示改動，
這樣 diff 只反映 DO-1）。

### 前（`dev@3bc1805`）全文

```text
支線籃子強弱  as-of 2026-09-08  （成員用 snapshot_date ≤ 2026-09-08 的最新一份；並列，不排名）
怎麼讀：① 先看「誰贏都賺」——這條故事還有沒有人在花錢
        ② 再看「成真」與「反面」的相對位置——市場往哪邊走
        n 小的時候，一籃的強弱就是那一檔的股價。強弱由你自己定，這裡不判。
branch                              籃子        n       RS5      RS20      RS60   breadth     val%
asic_xpu/mediatek_asic_share        誰贏都賺    8     +1.4%     +5.8%     -5.6%     75.0%    10.9%
                                    成真        1     +8.8%    +12.8%     +6.0%    100.0%     2.9%
                                    反面      無標的

asic_xpu/xpu_not_squeezing_gpu      誰贏都賺   16     -3.2%     +3.9%     -4.6%     56.2%    12.4%
                                    成真        3    -24.2%    -24.0%    -21.3%     33.3%     4.3%
                                    反面      無標的

nvhbm/hbm4_base_die_tsmc            誰贏都賺    9     -0.7%     +1.8%     +0.7%     55.6%     5.4%
                                    成真        1     +0.9%     -1.3%     +0.3%    100.0%     6.7%
                                    反面        3     +3.7%     -1.3%     +5.8%    100.0%     8.4%

optical_cpo/laser_inp_tight         誰贏都賺    4     -5.6%     +3.0%    +17.6%     25.0%     2.3%
                                    成真        3     -6.9%    +34.9%    +44.5%     66.7%     1.4%
                                    反面        3     -0.4%     +9.5%     -7.8%     66.7%     1.2%

memory_passthrough/nand_price_passthrough誰贏都賺    5     +3.2%     +0.8%    -12.9%     80.0%     3.0%
                                    成真        5     +1.8%     -2.2%     -0.7%     80.0%     9.4%
                                    反面        5    -15.9%    -15.0%    -14.6%     20.0%     4.8%
```

### diff（前 → 後）

```diff
@@ -3,22 +3,35 @@
         ② 再看「成真」與「反面」的相對位置——市場往哪邊走
         n 小的時候，一籃的強弱就是那一檔的股價。強弱由你自己定，這裡不判。
 branch                              籃子        n       RS5      RS20      RS60   breadth     val%
-asic_xpu/mediatek_asic_share        誰贏都賺    8     +1.4%     +5.8%     -5.6%     75.0%    10.9%
+asic_xpu/mediatek_asic_share        誰贏都賺    8     +1.4%     +5.8%     -5.6%*    75.0%    10.9%
                                     成真        1     +8.8%    +12.8%     +6.0%    100.0%     2.9%
                                     反面      無標的
+                                    * 窗內有價格斷點：這一格的漲跌幅有一部分不是市場給的，不能照字面讀
+                                      2449  2026-07-28  return_1 -14.5%
 
-asic_xpu/xpu_not_squeezing_gpu      誰贏都賺   16     -3.2%     +3.9%     -4.6%     56.2%    12.4%
-                                    成真        3    -24.2%    -24.0%    -21.3%     33.3%     4.3%
+asic_xpu/xpu_not_squeezing_gpu      誰贏都賺   16     -3.2%     +3.9%     -4.6%*    56.2%    12.4%
+                                    成真        3    -24.2%*   -24.0%*   -21.3%*    33.3%     4.3%
                                     反面      無標的
+                                    * 窗內有價格斷點：這一格的漲跌幅有一部分不是市場給的，不能照字面讀
+                                      2449  2026-07-28  return_1 -14.5%
+                                      6669  2026-09-02  return_1 -66.5%
 
-nvhbm/hbm4_base_die_tsmc            誰贏都賺    9     -0.7%     +1.8%     +0.7%     55.6%     5.4%
+nvhbm/hbm4_base_die_tsmc            誰贏都賺    9     -0.7%     +1.8%     +0.7%*    55.6%     5.4%
                                     成真        1     +0.9%     -1.3%     +0.3%    100.0%     6.7%
                                     反面        3     +3.7%     -1.3%     +5.8%    100.0%     8.4%
+                                    * 窗內有價格斷點：這一格的漲跌幅有一部分不是市場給的，不能照字面讀
+                                      2449  2026-07-28  return_1 -14.5%
 
 optical_cpo/laser_inp_tight         誰贏都賺    4     -5.6%     +3.0%    +17.6%     25.0%     2.3%
-                                    成真        3     -6.9%    +34.9%    +44.5%     66.7%     1.4%
-                                    反面        3     -0.4%     +9.5%     -7.8%     66.7%     1.2%
+                                    成真        3     -6.9%    +34.9%    +44.5%*    66.7%     1.4%
+                                    反面        3     -0.4%     +9.5%     -7.8%*    66.7%     1.2%
+                                    * 窗內有價格斷點：這一格的漲跌幅有一部分不是市場給的，不能照字面讀
+                                      2455  2026-06-26  return_1 -10.4%
+                                      3163  2026-07-28  return_1 -21.5%
 
-memory_passthrough/nand_price_passthrough誰贏都賺    5     +3.2%     +0.8%    -12.9%     80.0%     3.0%
+memory_passthrough/nand_price_passthrough誰贏都賺    5     +3.2%     +0.8%    -12.9%*    80.0%     3.0%
                                     成真        5     +1.8%     -2.2%     -0.7%     80.0%     9.4%
-                                    反面        5    -15.9%    -15.0%    -14.6%     20.0%     4.8%
+                                    反面        5    -15.9%*   -15.0%*   -14.6%*    20.0%     4.8%
+                                    * 窗內有價格斷點：這一格的漲跌幅有一部分不是市場給的，不能照字面讀
+                                      2449  2026-07-28  return_1 -14.5%
+                                      6669  2026-09-02  return_1 -66.5%
```

diff 裡只有兩種變化：**某些 RS 值後面多了一個 `*`**，以及**每個支線區塊底下多了斷點清單**。
沒有任何一個數字改變。

### G4 的機械驗證

把「後」的 `*` 換成空白、刪掉斷點清單那幾行、兩邊都去掉行尾空白之後：

```bash
sed 's/\*/ /g' panel_after.txt | grep -v "窗內有價格斷點\|return_1" \
  | sed 's/[ \t]*$//' > a.txt
sed 's/[ \t]*$//' panel_before.txt > b.txt
diff b.txt a.txt
```

```text
（無輸出）
```

逐字元相同。實作上的理由：記號吃掉 RS 欄之間兩個空白的其中一個
（`_rs_cell()` 一律回傳 8＋1＋1 ＝ 10 個字元），所以有記號與沒記號的格子等寬，
欄位不位移。測試 `test_do1_the_mark_adds_nothing_but_the_mark` 用
`dataclasses.replace` 把 breaks 清空再 render，斷言兩份輸出相等。

G3（無命中時逐字元相同）另有 `test_do1_no_hit_leaves_the_branch_block_untouched`：
同一份資料下，乾淨支線單獨 render 的那一行，與旁邊有支線帶記號時 render 出來的
那一行，是同一串 bytes。

## §5 G1／G2 — `narratives/2026-09-08.yaml` 上的實際面板輸出全文

`uv run marketpulse baskets --as-of 2026-09-08`，在 `e19ca2a` 上（含 DO-3）：

```text
支線籃子強弱  as-of 2026-09-08  （成員用 snapshot_date ≤ 2026-09-08 的最新一份；並列，不排名）
怎麼讀：① 先看「誰贏都賺」——這條故事還有沒有人在花錢
        ② 再看「成真」與「反面」的相對位置——市場往哪邊走
        n 小的時候，一籃的強弱就是那一檔的股價。強弱由你自己定，這裡不判。
branch                              籃子        n       RS5      RS20      RS60   breadth     val%
asic_xpu/mediatek_asic_share        誰贏都賺    8     +1.4%     +5.8%     -5.6%*    75.0%    10.9%  這條上游不區辨（semiconductor_test 也在：nvhbm/hbm4_base_die_tsmc、memory_passthrough/nand_price_passthrough）
                                    成真        1     +8.8%    +12.8%     +6.0%    100.0%     2.9%
                                    反面      無標的
                                    * 窗內有價格斷點：這一格的漲跌幅有一部分不是市場給的，不能照字面讀
                                      2449  2026-07-28  return_1 -14.5%

asic_xpu/xpu_not_squeezing_gpu      誰贏都賺   16     -3.2%     +3.9%     -4.6%*    56.2%    12.4%
                                    成真        3    -24.2%*   -24.0%*   -21.3%*    33.3%     4.3%
                                    反面      無標的
                                    * 窗內有價格斷點：這一格的漲跌幅有一部分不是市場給的，不能照字面讀
                                      2449  2026-07-28  return_1 -14.5%
                                      6669  2026-09-02  return_1 -66.5%

nvhbm/hbm4_base_die_tsmc            誰贏都賺    9     -0.7%     +1.8%     +0.7%*    55.6%     5.4%  這條上游不區辨（high_speed_materials 也在：optical_cpo/laser_inp_tight）  這條上游不區辨（semiconductor_test 也在：asic_xpu/mediatek_asic_share、memory_passthrough/nand_price_passthrough）
                                    成真        1     +0.9%     -1.3%     +0.3%    100.0%     6.7%
                                    反面        3     +3.7%     -1.3%     +5.8%    100.0%     8.4%
                                    * 窗內有價格斷點：這一格的漲跌幅有一部分不是市場給的，不能照字面讀
                                      2449  2026-07-28  return_1 -14.5%

optical_cpo/laser_inp_tight         誰贏都賺    4     -5.6%     +3.0%    +17.6%     25.0%     2.3%  這條上游不區辨（high_speed_materials 也在：nvhbm/hbm4_base_die_tsmc）
                                    成真        3     -6.9%    +34.9%    +44.5%*    66.7%     1.4%
                                    反面        3     -0.4%     +9.5%     -7.8%*    66.7%     1.2%
                                    * 窗內有價格斷點：這一格的漲跌幅有一部分不是市場給的，不能照字面讀
                                      2455  2026-06-26  return_1 -10.4%
                                      3163  2026-07-28  return_1 -21.5%

memory_passthrough/nand_price_passthrough誰贏都賺    5     +3.2%     +0.8%    -12.9%*    80.0%     3.0%  這條上游不區辨（semiconductor_test 也在：asic_xpu/mediatek_asic_share、nvhbm/hbm4_base_die_tsmc）
                                    成真        5     +1.8%     -2.2%     -0.7%     80.0%     9.4%
                                    反面        5    -15.9%*   -15.0%*   -14.6%*    20.0%     4.8%
                                    * 窗內有價格斷點：這一格的漲跌幅有一部分不是市場給的，不能照字面讀
                                      2449  2026-07-28  return_1 -14.5%
                                      6669  2026-09-02  return_1 -66.5%
```

**G1 的三個窗各自判定，在真實資料上看得到：**

- `2449` 的斷點在 2026-07-28 —— 距 09-08 約 30 個 session，落在 RS60 窗內、
  RS20 窗外。所以 `誰贏都賺` 那幾列只有 `RS60` 帶記號。
- `6669` 的斷點在 2026-09-02 —— 三個窗都含它，所以
  `asic_xpu/xpu_not_squeezing_gpu` 成真籃與
  `memory_passthrough/nand_price_passthrough` 反面籃三欄全帶記號。
  這正是 `014-review.md` §5.1 指出的那兩格。

**G2：**每個支線區塊底下逐筆列出（代號、日期、`return_1`），一筆一行。
同一個 session 在同一條支線的多個籃子裡出現只列一次
（`test_do1_one_session_is_listed_once_however_many_baskets_hold_it`）。

## §6 G5（目視）— 交 PO 判定

**這一項不用測試背書。**沒有任何測試的名稱或斷言承載「讀的人看得出」這個宣稱。
以下是排版的實際安排與理由，判定權在 PO：

- 記號是 `*`（採用 spec 未決問題 1 的傾向）。面板本輪之前不含 `*`，不會混淆；
  `brief` 用 `*` 表示「這個數字有事」，語意一致。
- 記號緊貼數字（`-24.0%*`），不是獨立欄，所以視線落在數字上就會撞到它。
- 區塊底下第一行是固定文字
  `* 窗內有價格斷點：這一格的漲跌幅有一部分不是市場給的，不能照字面讀`，
  記號的意思寫在同一個區塊裡，不必回頭查圖例。
- 斷點清單縮排到「籃子」欄的位置，視覺上仍在該支線的區塊內。

**未經驗證的部分：**「兩秒內看得出」這件事我沒有辦法自己證明，也沒有嘗試用
截圖代替。請 PO 直接看 §5 的全文。

## §7 G6／G7 — DO-2 的兩組筆數與 6669 那一筆

`uv run python scripts/price_break_recovery.py`：

```text
資料 data  最後一個 session 2026-09-08
impossible_daily_returns 共 278 筆
窗 = 20 個交易日（取自 RS20，不是新挑的參數）
判準：斷點後 20 個交易日內，收盤是否回到斷點前一日的收盤（實際收盤比較）

回得去（暫時性）          37 筆
回不去（價格水準重設）     241 筆
合計                  278 筆

其中窗未滿 20 天而判為「回不去」的：29 筆 —— 資料尾端還沒長出 20 個 session，這幾筆是暫時判定，會被之後的資料推翻

── 回不去  241 筆 ────────────────────────────────────────
```

**G6：**37 ＋ 241 ＝ 278，等於 `impossible_daily_returns` 的總筆數。

spec 寫的是 273 筆；本機 `data/` 現在是 **278** 筆
（411 個 session，2024-12-27 → 2026-09-08）。差額是 spec 寫完之後又下載了資料，
不是判準造成的。分組是對本機當下的 278 筆做的。

**「不足 20 個交易日」那一組：**29 筆。它們**留在「回不去」裡**而不是被抽掉，
因為 G7 要求 6669／2026-09-02 落在「回不去」，而那一筆斷點後只有 4 個 session。
兩種讀法都符合 G6 的括號，但只有這一種同時滿足 G7：兩組相加等於總數，
窗未滿的那 29 筆另外報筆數、逐行標 `(窗未滿)`，說明它們是暫時判定、
會被之後的資料推翻。

**G7：**

```text
6669    緯穎        2026-09-02      -66.5%     7800.00   2610.00      4  —  (窗未滿)
```

出現在 `── 回不去 241 筆` 區塊內（輸出第 247 行，該區塊涵蓋 12–255 行）。
前一日收盤 7,800，斷點收盤 2,610，之後 4 個 session 最高 2,565，沒有回去。

判準用**實際收盤直接比較**，不是報酬率累乘（spec 兔子洞）：
比較的是「斷點後任一日的收盤 ≥ 斷點前一日的收盤」（向下斷點）或 `≤`（向上斷點）。

## §8 G9 — `semiconductor_test` 三條提示的實際輸出行

從 §5 的面板全文摘出：

```text
asic_xpu/mediatek_asic_share        誰贏都賺    8     +1.4%     +5.8%     -5.6%*    75.0%    10.9%  這條上游不區辨（semiconductor_test 也在：nvhbm/hbm4_base_die_tsmc、memory_passthrough/nand_price_passthrough）
nvhbm/hbm4_base_die_tsmc            誰贏都賺    9     -0.7%     +1.8%     +0.7%*    55.6%     5.4%  這條上游不區辨（high_speed_materials 也在：optical_cpo/laser_inp_tight）  這條上游不區辨（semiconductor_test 也在：asic_xpu/mediatek_asic_share、memory_passthrough/nand_price_passthrough）
memory_passthrough/nand_price_passthrough誰贏都賺    5     +3.2%     +0.8%    -12.9%*    80.0%     3.0%  這條上游不區辨（semiconductor_test 也在：asic_xpu/mediatek_asic_share、nvhbm/hbm4_base_die_tsmc）
```

三條：`asic_xpu/mediatek_asic_share`、`nvhbm/hbm4_base_die_tsmc`、
`memory_passthrough/nand_price_passthrough`。提示指名的是 `semiconductor_test`
這個 id，不是整組 `either_way`。

014 的判準（整組相等）在同一份資料上觸發 0 次，因為三組寫法是
`[foundry_advanced, semiconductor_test]`／`[semiconductor_test, high_speed_materials]`／
`[semiconductor_test]`。測試
`test_do3_real_narratives_semiconductor_test_is_named_on_three_branches`
順便斷言了這三組互不相等，把「舊判準為什麼不會觸發」釘在測試裡。
該測試的 `as_of` 釘死在 `2026-09-08`、斷言用包含式（contract §9.1）。

**同一輪還多出兩條提示**（本輪之前是零條）：`high_speed_materials` 同時在
`nvhbm/hbm4_base_die_tsmc` 與 `optical_cpo/laser_inp_tight`，兩條都印。
`foundry_advanced` 在 `asic_xpu` 的兩條支線上，同一則故事，**不觸發**（G10）。

## §9 契約紅線的自我檢查

| 紅線 | 本輪狀態 |
|---|---|
| §8／Q3 只量測不改價格 | `calc.py` 未改一行；價格未還原、成員未剔除、未補值。G4 機械驗證見 §4 |
| R3 第二層不改第一層 | 方向是第一層診斷 → 第二層畫面。`theme_daily.parquet`、`market_daily.parquet` 未寫入 |
| D10 20 日窗取自 RS20 | `scripts/price_break_recovery.py` 的 `WINDOW = 20`，docstring 寫明來源，未調整 |
| D14 `brief`／`radar` 產物不變 | 未碰 `product.py`／`radar.py`；014 的 `test_running_baskets_does_not_change_brief_or_radar` 仍綠 |
| R1 不排名不評分 | 記號是揭露，不是分數；沒有門檻決定哪一格「嚴重」 |
