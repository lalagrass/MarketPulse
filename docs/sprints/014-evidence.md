# Sprint 014 — 物證

由實作端寫。格式見 `014-spec.md`「回報時必須附的物證」。
分支 `sprint/014-three-baskets`，自 `dev@59c9cf1`。**未併入。**

---

## §1 commit hash

| DO | hash | 標題 |
|---|---|---|
| DO-1 | `8d956f8` | feat(014 DO-1): 支線的籃子從一個變三個 |
| DO-2 | `44cdd16` | feat(014 DO-2): 面板一條支線印三行 |
| DO-3 | `b5cb19a` | feat(014 DO-3): 回頭日期拆成日期與條件 |

## §2 `uv run pytest` 的實際摘要行

在 `b5cb19a`（分支尖端）上執行 `uv run pytest`：

```text
326 passed in 59.21s
```

同一台機器、同一份 `data/`，`dev@59c9cf1` 上是：

```text
301 passed in 60.53s (0:01:00)
```

新增 25 個測試，零 skip、零 xfail、零 fail。

## §3 `git diff dev --stat`

```text
 marketpulse/baskets.py    | 270 +++++++++++++++++++++++++++++++++++++--------
 marketpulse/cli.py        |   9 +-
 marketpulse/narratives.py | 127 ++++++++++++++++++++--
 tests/test_baskets.py     | 272 ++++++++++++++++++++++++++++++++++++++++++----
 tests/test_narratives.py  | 270 ++++++++++++++++++++++++++++++++++++++++++++-
 5 files changed, 866 insertions(+), 82 deletions(-)
```

`marketpulse/cli.py` 不在 spec 的「模組」清單內。9 行的內容與理由見 §8。
`themes/`、`narratives/`、`data/`、`docs/product/`、`calc.py`、`quality.py`、
`radar.py`、`product.py` 的 diff 全空。

---

## §4 F3 — DO-1 的輸出與 `dev` 逐字元相同

`dev@59c9cf1` 上：

```text
支線籃子強弱  as-of 2026-09-08  （成員用 snapshot_date ≤ 2026-09-08 的最新一份；並列，不排名）
branch                                n       RS5      RS20      RS60   breadth     val%
asic_xpu/mediatek_asic_share          1     +8.8%    +12.8%     +6.0%    100.0%     2.9%
asic_xpu/xpu_not_squeezing_gpu      無標的
nvhbm/hbm4_base_die_tsmc              1     +0.9%     -1.3%     +0.3%    100.0%     6.7%
```

在 DO-1 commit `8d956f8` 上重跑同一指令，`diff` 兩份輸出：

```text
$ uv run marketpulse baskets > baskets_do1.txt
$ diff baskets_dev.txt baskets_do1.txt && echo "F3 OK: byte-identical"
F3 OK: byte-identical
```

**F3 通過。**

---

## §5 F5／F6／F7／F8／F9／F10 — `uv run marketpulse baskets` 的實際輸出全文

### §5.1 真實 `narratives/` 上的輸出（DO-2 之後，分支尖端）

```text
支線籃子強弱  as-of 2026-09-08  （成員用 snapshot_date ≤ 2026-09-08 的最新一份；並列，不排名）
怎麼讀：① 先看「誰贏都賺」——這條故事還有沒有人在花錢
        ② 再看「成真」與「反面」的相對位置——市場往哪邊走
        n 小的時候，一籃的強弱就是那一檔的股價。強弱由你自己定，這裡不判。
branch                              籃子        n       RS5      RS20      RS60   breadth     val%
asic_xpu/mediatek_asic_share        誰贏都賺  無標的
                                    成真        1     +8.8%    +12.8%     +6.0%    100.0%     2.9%
                                    反面      無標的

asic_xpu/xpu_not_squeezing_gpu      誰贏都賺  無標的
                                    成真      無標的
                                    反面      無標的

nvhbm/hbm4_base_die_tsmc            誰贏都賺  無標的
                                    成真        1     +0.9%     -1.3%     +0.3%    100.0%     6.7%
                                    反面      無標的
```

**這份輸出只證得到 F6 與 F9。**本輪不改 `narratives/`（前提決定 4），三則故事
的支線全部只寫了舊的 `basket:`，所以 `if_false` 與 `either_way` 一律是空的：

- **F6 通過**——三條支線各佔三行，空籃印 `無標的`，一行也沒有消失
- **F9 通過**——表頭三行讀法短註逐字來自 spec 附錄，是模組常數
- **F5／F7／F8 在這份資料上觸發不了**：沒有一條支線三籃都有成員（F5 的 WHEN）、
  沒有一條支線 `if_true` 與 `if_false` 有共同代號（F7 的 WHEN）、
  沒有兩則故事的 `either_way` 相同（F8 的 WHEN）。物證見 §5.2 與 §6

### §5.2 三籃填滿時的輸出（示範資料，**不進版控**）

把 §5.1 那三則故事複製到一個暫存目錄、填上三個籃子（含一個故意打錯的
`opitcal_cpo`），以同一個真實 `data/` 執行同一個指令：

```text
$ uv run marketpulse baskets --narratives-dir /tmp/…/demo_narratives
支線籃子強弱  as-of 2026-09-08  （成員用 snapshot_date ≤ 2026-09-08 的最新一份；並列，不排名）
怎麼讀：① 先看「誰贏都賺」——這條故事還有沒有人在花錢
        ② 再看「成真」與「反面」的相對位置——市場往哪邊走
        n 小的時候，一籃的強弱就是那一檔的股價。強弱由你自己定，這裡不判。
branch                              籃子        n       RS5      RS20      RS60   breadth     val%
asic_xpu/mediatek_asic_share        誰贏都賺   16     -6.6%     +9.3%     +0.7%     56.2%     6.8%  這條上游不區辨（同一組 theme_ids 也在：nvhbm）
                                    成真        2     +1.4%     +5.1%     -1.2%    100.0%     3.5%
                                    反面        2     -2.6%     -1.9%     -4.1%    100.0%     7.3%  成真／反面共同 1 檔

asic_xpu/xpu_not_squeezing_gpu      誰贏都賺    5     -3.6%     -8.0%    -18.5%     20.0%     1.1%  未知 theme_id（不在 themes/v1.yaml）: opitcal_cpo
                                    成真      無標的
                                    反面      無標的

nvhbm/hbm4_base_die_tsmc            誰贏都賺   16     -6.6%     +9.3%     +0.7%     56.2%     6.8%  這條上游不區辨（同一組 theme_ids 也在：asic_xpu）
                                    成真        1     +0.9%     -1.3%     +0.3%    100.0%     6.7%
                                    反面      無標的
```

示範資料用的籃子（`asic_xpu/mediatek_asic_share`）：

```yaml
baskets:
  if_true:  ["2454", "3661"]
  if_false: ["2330", "3661"]      # 3661 兩邊都在 → 共同 1 檔
  either_way: [optical_cpo, pcb]  # 與 nvhbm/hbm4_base_die_tsmc 同一組
```

- **F5 通過**——三籃都有成員的那條支線佔三行，順序 `誰贏都賺`→`成真`→`反面`
- **F7 通過**——`3661` 兩邊都在，面板印 `成真／反面共同 1 檔`
- **F8 通過**——`{optical_cpo, pcb}` 同時是兩則故事的 `either_way`，兩行都印
  `這條上游不區辨`，並指名另一則
- **F4 上畫面通過**——`opitcal_cpo` 被指名，那一籃剩下的 `ai_power` 5 檔照算，
  不會整籃看起來像空的

這份 YAML 是示範，**沒有寫進 `narratives/`**。要讓 §5.1 長成 §5.2 的樣子，
需要 PO 決定每條支線的三個籃子怎麼填（前提決定 4 已把這件事留給 PO）。

### §5.3 F10 目視

**這一項我不判定。**貼的是排法與實際長相，判定是 PO 的。

排法：支線名只印在第一行（`asic_xpu/mediatek_asic_share`），下面兩行左側留白
到同一欄，三行之間空一行收尾。`籃子` 欄固定 10 個顯示欄寬（最長標籤 `誰贏都賺`
佔 8 欄），其後 `n / RS5 / RS20 / RS60 / breadth / val%` 沿用 004 的欄寬未動。
中文字寬用 `product.py:_vislen/_ljust` 算，不是 `str.ljust`，所以中英混排的右緣
對得齊——§5.1 與 §5.2 的 `n` 欄與各百分比欄右緣可以直接目測。

尾註（`這條上游不區辨` / `成真／反面共同 N 檔` / `未知 theme_id`）掛在 `val%`
之後，長度不定，所以它們**不在**任何右緣對齊的欄位裡。這是刻意的：欄位是數字，
尾註是文字。

沒有任何測試名稱承載「對齊」「一眼看得出」這類宣稱。
`test_do2_two_branches_are_visually_separated` 釘的是可測的那一半——三行連續、
中間空一行——它的 docstring 明寫「是否一眼讀得出來是 PO 的判斷，不是這個測試的」。

---

## §6 F11–F14 — fixture 的實際輸出字串

`revisit` 相關 fixture（每則只有一個 narrative `n1`，`note: note text`）：

```text
── F11 純 ISO 且 ≤ as_of  (as_of 2026-09-10) ──
到期重看
n1 · — · 2026-09-10 · note text

條件型（無法判斷是否到期）
（無）

── F11b 純 ISO 但 > as_of  (as_of 2026-09-10) ──
到期重看
（無）

條件型（無法判斷是否到期）
（無）

── F12 ISO + revisit_note  (as_of 2026-10-20) ──
到期重看
n1 · — · 2026-10-15 · note text · 或 Broadcom 下一次財報電話會議（以先到者為準）

條件型（無法判斷是否到期）
（無）

── F13 舊檔自由文字 revisit  (as_of 2026-10-20) ──
到期重看
（無）

條件型（無法判斷是否到期）
n1 · 2026-10-15 或 Broadcom 下一次財報電話會議（以先到者為準）

── F14 空 revisit（只有 revisit_note）  (as_of 2026-09-10) ──
raise ValueError: narrative 'n1': missing required field 'revisit'
                  (an ISO date; put the condition in 'revisit_note')
```

F11／F12／F13／F14 全部通過。F14 特別確認：`revisit_note` **不能**代替
`revisit`，004 的必填一格沒有放寬。

DO-1 的 F2 fixture（舊格式向下相容）：

```text
branches:
  - branch_id: b
    claim: c
    basket: ["1234", "5678"]     # 舊寫法
    watch: w
→ if_true == ("1234", "5678")   if_false == ()   either_way == ()
```

DO-1 的 F1（真實檔案，成員與本輪之前相同）：

```text
("asic_xpu", "mediatek_asic_share")  → if_true ("2454",)  if_false ()  either_way ()
("asic_xpu", "xpu_not_squeezing_gpu")→ if_true ()         if_false ()  either_way ()
("nvhbm",    "hbm4_base_die_tsmc")   → if_true ("2330",)  if_false ()  either_way ()
```

---

## §7 哪幾則現有 narrative 仍落在「條件型」

**三則全部。**本輪不改 `narratives/` 裡任何一個字，所以三則的 `revisit` 仍是
自由文字，`revisit_note` 全為空字串：

| narrative_id | `revisit` 原文 | `parse_revisit_date` | 落點 |
|---|---|---|---|
| `asic_xpu` | `2026-10-15 或 Broadcom 下一次財報電話會議（以先到者為準）` | `None` | 條件型 |
| `nvhbm` | `台積電 2026-10 法說（HBM4 base die 代工客戶／資本支出揭露）` | `None` | 條件型 |
| `optical_cpo` | `2026-10-01；若 optical_cpo 主題 rank 跌出前 3 則提前重評` | `None` | 條件型 |

`uv run marketpulse brief` 的該區塊：

```text
到期重看
（無）
```

**點火率仍是 0/3，與 spec 的預期一致。**DO-3 給的是欄位，不是資料——把上表第二欄
拆成 `revisit: 2026-10-15` ＋ `revisit_note: 或 Broadcom…` 是 PO 的編輯動作，
`narratives/` 在權限邊界的「不可碰」清單上。三則裡 `asic_xpu` 與 `optical_cpo`
拆得動（原文已經帶一個 ISO 日期），`nvhbm` 的「台積電 2026-10 法說」沒有日，
拆的時候要 PO 給一個具體日期。

---

## §8 第一層與 D14 的不變證明

`theme_daily.parquet` / `market_daily.parquet` 本輪**未被寫入**——
`baskets.py` 只讀 `read_normalized()`，沒有任何 `to_parquet`。
`tests/test_baskets.py::test_running_baskets_does_not_change_brief_or_radar`
釘住這件事（跑完面板後比對 snapshot 的 mtime，並斷言不存在
`basket_daily.parquet`）。

D14（brief / radar 產物不變）另外用 `dev` 與分支尖端各跑一次實測：

```text
$ diff brief_dev.txt brief_014.txt   && echo "brief identical"
brief identical
$ diff radar_dev.html radar_014.html && echo "radar identical"
radar identical
```

## §9 `cli.py` 的 9 行

`compute_basket_metrics` 多收一個唯讀的 `themes: ThemeSet`（`either_way` 的
theme_ids 要走既有 `ThemeSet` 展開，spec 兔子洞第二條），呼叫端因此要拿得到
它。`baskets` 指令原本不載 themes，所以加了一個 `--themes-path`
（預設 `DEFAULT_THEMES`，與其他指令同一個常數），並更新該指令的 docstring。

替代做法是讓 `baskets.py` 自己用寫死的預設路徑載 YAML，那會在讀端埋一個隱藏的
檔案相依。選了把相依放在 CLI 明面上。

`cli.py` 不在 spec 列的「可碰」也不在「不可碰」，Appetite 的「只動兩個模組」
因此被踩到一次。9 行、無行為改變、無新輸出。
