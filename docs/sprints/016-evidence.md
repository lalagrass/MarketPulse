# Sprint 016 — 物證

分支 `sprint/016-make-errors-loud`，自 `dev@480e869`。未 merge。

| DO | commit | 內容 |
|----|--------|------|
| DO-1 | `0ee7891` | `scripts/acceptance-check.sh` |
| DO-2 | `7459408` | `_ljust` 溢出時截斷並留下記號 |
| DO-3 | `a34088e` | 斷點清單排序；「不區辨」提示移到區塊底下 |

## `uv run pytest`

```text
350 passed in 61.24s (0:01:01)
```

`dev` 上是 340 passed。新增 10 筆：`tests/test_product.py` 5 筆（DO-2）、
`tests/test_baskets.py` 5 筆（DO-3）。

## `git diff dev --stat`

```text
 marketpulse/baskets.py      |  67 +++++++++----
 marketpulse/product.py      |  29 +++++-
 scripts/acceptance-check.sh | 222 ++++++++++++++++++++++++++++++++++++++++++++
 tests/test_baskets.py       |  99 ++++++++++++++++++++
 tests/test_product.py       |  49 ++++++++++
 5 files changed, 449 insertions(+), 17 deletions(-)
```

（`docs/` 下另有三個檔案在開工前就已經是 modified，不屬於本輪，未動也未提交。）

## H1 — 腳本吃 `docs/sprints/015-spec.md`

```text
docs/sprints/015-spec.md:59: [A1] 驗收條件 G5 不含 WHEN … THEN …（標「（目視）」的也不設例外）
docs/sprints/015-spec.md:28: [A3] 引用 calc.py:216 是 basename，要寫完整路徑（同名檔案會讓解析出錯）
docs/sprints/015-spec.md:106: [A6] 驗收條件代號共 10 個（G1 G2 G3 G4 G5 G6 G7 G8 G9 G10），超過上限 8
docs/sprints/015-spec.md: 3 violations
exit=1
```

**H1 達成。**A3（line 28 的 basename）與 A6 都被指出並印出行號，退出碼非零。

兩處與 spec 的字面不同，都往「腳本抓得更多」的方向：

- **A6 的數字是 10，不是 spec 寫的 9。**spec 的 9 來自我開工前自檢時用的
  `grep -cE "^- [A-Z][0-9]+ —"`，那個式子漏掉 `G5（目視）—`（代號與破折號之間
  沒有空格）。**這個數字是我提供的，錯的是我。**腳本的 `^- [A-Z][0-9]+[^ ]* ?—`
  兩種寫法都收得到。
- **多抓到一條 A1：`G5` 沒有 WHEN … THEN。**真陽性，而且正是 016 的 H8 被修掉的
  同一類。H1 要求「指出兩處」，這是第三處，不影響 H1 的兩項都被指出。

`015-spec.md` 被 A6 判超標是真陽性，但上限是 015 之後才立的（兔子洞已註明），
沒有回頭改 `015-spec.md`。

## H2 — 腳本吃 `docs/sprints/016-spec.md`

```text
docs/sprints/016-spec.md:78: [A3] 引用 calc.py:216 是 basename，要寫完整路徑（同名檔案會讓解析出錯）
docs/sprints/016-spec.md: 1 violations
exit=1
```

**H2 未達成。**退出碼 1，不是 0。

原因是一處，且是真陽性：`016-spec.md` line 78 在 H1 的條文裡引用了
`` `calc.py:216` `` ——那是 015 的違反處，被當成例子寫進 016 的驗收條件，
位置在任何 fenced code block 之外，A3 分不出「引用」與「引述別人的壞引用」。

我沒有為它加例外。A3 的判準是 spec 寫定的（basename 視為違反），為了讓本檔
通過而放寬它，正是這一輪要防的事。兩種修法都在規劃端：

1. `016-spec.md` line 78 改寫成不含 `path:line` 形式，例如
   「line 28 那條 basename 引用（A3）」；或
2. 把 H1 的細節移進 fenced code block（總則已經跳過那裡）。

改完再跑一次就會是 `exit=0`。

## 判準會不會誤殺 —— 跑過全部 16 份 spec

```text
000-spec.md      rc=0  docs/sprints/000-spec.md: OK（spec，0 violations）
001-spec.md      rc=1  docs/sprints/001-spec.md: 3 violations
002-spec.md      rc=0  docs/sprints/002-spec.md: OK（spec，0 violations）
003-spec.md      rc=1  docs/sprints/003-spec.md: 2 violations
004-spec.md      rc=1  docs/sprints/004-spec.md: 3 violations
005-spec.md      rc=0  docs/sprints/005-spec.md: OK（spec，0 violations）
006-spec.md      rc=0  docs/sprints/006-spec.md: OK（spec，0 violations）
007-spec.md      rc=1  docs/sprints/007-spec.md: 1 violations
008-spec.md      rc=1  docs/sprints/008-spec.md: 3 violations
009-spec.md      rc=1  docs/sprints/009-spec.md: 2 violations
010-spec.md      rc=1  docs/sprints/010-spec.md: 12 violations
011-spec.md      rc=1  docs/sprints/011-spec.md: 8 violations
012-spec.md      rc=1  docs/sprints/012-spec.md: 6 violations
014-spec.md      rc=1  docs/sprints/014-spec.md: 4 violations
015-spec.md      rc=1  docs/sprints/015-spec.md: 3 violations
016-spec.md      rc=1  docs/sprints/016-spec.md: 1 violations
```

四份（000／002／005／006）完全乾淨，退出碼 0——判準不是對所有東西都會叫。
其餘的違反抽查過，全部是規則字面上的真陽性：絕大多數是 basename 引用
（`quality.py:96`、`cli.py:212` 之類），`010-spec.md` 另有 A5 超長（222 行），
`011-spec.md` 另有兩條 A1。沒有找到誤殺。

**這也就是 hook 還不能掛的理由。**A3 一條就會讓 12 份舊 spec 全部退出碼 1；
掛成 `Stop` hook 會讓 session 停不下來。設定範例寫在腳本開頭的註解裡，
預設不啟用（前提決定 1）。

## H3 — 溢出的一格仍恰好佔宣告寬度，且留下截斷記號

面板上真的發生的那一格，`BRANCH_COL_WIDTH = 36`：

```text
dev  : memory_passthrough/nand_price_passthrough誰贏都賺    5     +3.2%
016  : memory_passthrough/nand_price_passt…誰贏都賺    5     +3.2%
       |<------------- 36 欄 ------------>|
```

`_vislen("memory_passthrough/nand_price_passt…") == 36`，`誰贏都賺` 因此
從第 37 欄起，與其他資料列同一個欄位起點。

邊界由 `tests/test_product.py` 的五筆擔保，含全形字不被切成半個：

```text
_ljust("誰贏都賺", 5) == "誰贏…"      # 2+2+1 = 5
_ljust("誰贏都賺", 4) == "誰…"  + " "  # 2+1，剩下的一欄補空白，不切出半個字
_ljust("誰贏都賺", 8) == "誰贏都賺"    # 恰好等寬，不截斷、不加記號
_ljust("abc", 1)      == "…"
_ljust("abc", 0)      == ""
```

## H4 — `brief` 與 `radar` 逐字元不變（D14）

`dev` 與本分支各跑一次，三個產物：

```text
$ diff <dev> <016> brief.txt
(no output)
$ diff <dev> <016> radar.stdout.txt
(no output)
$ diff <dev> <016> reports/radar.html
(no output)
```

三個都是空的。DO-2 一改完就先跑過一次，DO-3 之後再跑一次，兩次都空。

前提「今日無任何一格溢出」是量出來的，不是假設的：把 `_ljust` 包起來計數，
`brief` 0 次溢出、`radar` 0 次、`baskets` 恰好 1 次
（`width=36 vislen=41`）。所以 `brief` 與 `radar` 走的全是原本的 padding 分支。

## H5 — `baskets` 只有那一格

DO-2 單獨的 diff（`dev` vs `7459408`）：

```text
32c32
< memory_passthrough/nand_price_passthrough誰贏都賺    5     +3.2%     +0.8%    -12.9%*    80.0%     3.0%  這條上游不區辨（semiconductor_test 也在：asic_xpu/mediatek_asic_share、nvhbm/hbm4_base_die_tsmc）
---
> memory_passthrough/nand_price_passt…誰贏都賺    5     +3.2%     +0.8%    -12.9%*    80.0%     3.0%  這條上游不區辨（semiconductor_test 也在：asic_xpu/mediatek_asic_share、nvhbm/hbm4_base_die_tsmc）
```

一行，成因是該行第一格被截斷；右側各欄整體左移 5 欄，與其他資料列對齊了。
截斷記號用 `…`（U+2026）——`_vislen` 算 1 欄（`0x2026 < 0x2E80`），與規劃端
傾向的一致，沒有衝突，未決問題 1 照原案。

## H6／H7／H8 — `uv run marketpulse baskets` 全文

```text
支線籃子強弱  as-of 2026-09-08  （成員用 snapshot_date ≤ 2026-09-08 的最新一份；並列，不排名）
怎麼讀：① 先看「誰贏都賺」——這條故事還有沒有人在花錢
        ② 再看「成真」與「反面」的相對位置——市場往哪邊走
        n 小的時候，一籃的強弱就是那一檔的股價。強弱由你自己定，這裡不判。
branch                              籃子        n       RS5      RS20      RS60   breadth     val%
asic_xpu/mediatek_asic_share        誰贏都賺    8     +1.4%     +5.8%     -5.6%*    75.0%    10.9%
                                    成真        1     +8.8%    +12.8%     +6.0%    100.0%     2.9%
                                    反面      無標的
                                    這條上游不區辨（semiconductor_test 也在：nvhbm/hbm4_base_die_tsmc、memory_passthrough/nand_price_passthrough）
                                    * 窗內有價格斷點：這一格的漲跌幅有一部分不是市場給的，不能照字面讀
                                      2449  2026-07-28  return_1 -14.5%

asic_xpu/xpu_not_squeezing_gpu      誰贏都賺   16     -3.2%     +3.9%     -4.6%*    56.2%    12.4%
                                    成真        3    -24.2%*   -24.0%*   -21.3%*    33.3%     4.3%
                                    反面      無標的
                                    * 窗內有價格斷點：這一格的漲跌幅有一部分不是市場給的，不能照字面讀
                                      6669  2026-09-02  return_1 -66.5%
                                      2449  2026-07-28  return_1 -14.5%

nvhbm/hbm4_base_die_tsmc            誰贏都賺    9     -0.7%     +1.8%     +0.7%*    55.6%     5.4%
                                    成真        1     +0.9%     -1.3%     +0.3%    100.0%     6.7%
                                    反面        3     +3.7%     -1.3%     +5.8%    100.0%     8.4%
                                    這條上游不區辨（high_speed_materials 也在：optical_cpo/laser_inp_tight）
                                    這條上游不區辨（semiconductor_test 也在：asic_xpu/mediatek_asic_share、memory_passthrough/nand_price_passthrough）
                                    * 窗內有價格斷點：這一格的漲跌幅有一部分不是市場給的，不能照字面讀
                                      2449  2026-07-28  return_1 -14.5%

optical_cpo/laser_inp_tight         誰贏都賺    4     -5.6%     +3.0%    +17.6%     25.0%     2.3%
                                    成真        3     -6.9%    +34.9%    +44.5%*    66.7%     1.4%
                                    反面        3     -0.4%     +9.5%     -7.8%*    66.7%     1.2%
                                    這條上游不區辨（high_speed_materials 也在：nvhbm/hbm4_base_die_tsmc）
                                    * 窗內有價格斷點：這一格的漲跌幅有一部分不是市場給的，不能照字面讀
                                      3163  2026-07-28  return_1 -21.5%
                                      2455  2026-06-26  return_1 -10.4%

memory_passthrough/nand_price_passt…誰贏都賺    5     +3.2%     +0.8%    -12.9%*    80.0%     3.0%
                                    成真        5     +1.8%     -2.2%     -0.7%     80.0%     9.4%
                                    反面        5    -15.9%*   -15.0%*   -14.6%*    20.0%     4.8%
                                    這條上游不區辨（semiconductor_test 也在：asic_xpu/mediatek_asic_share、nvhbm/hbm4_base_die_tsmc）
                                    * 窗內有價格斷點：這一格的漲跌幅有一部分不是市場給的，不能照字面讀
                                      6669  2026-09-02  return_1 -66.5%
                                      2449  2026-07-28  return_1 -14.5%
```

**H6 達成。**`asic_xpu/xpu_not_squeezing_gpu` 與
`memory_passthrough/nand_price_passthrough` 兩個區塊各有兩筆，
第一行都是 `6669 −66.5%`（`dev` 上是 `2449 −14.5%`）；
`optical_cpo/laser_inp_tight` 是 `3163 −21.5%` 在 `2455 −10.4%` 之前。

**H7 達成。**四條支線各自的「不區辨」提示都自成一行，落在該區塊三行數字之下、
與斷點清單同一個縮排；資料列上不再有這段文字。`nvhbm/hbm4_base_die_tsmc`
那一行從 317 字元降到 100 字元，與其他資料列同寬。

**H8 未由我判定。**這是目視題，上面的全文就是要看的原文，交 PO 判。
測試名稱沒有承載這個宣稱：DO-3 的四個測試名是
`..._leads_with_the_largest_absolute_return`、
`..._equal_sizes_keep_the_session_order_underneath`、
`..._is_not_on_a_data_row`、`..._gets_its_own_line_after_the_three_rows`、
`..._prints_the_same_lines_as_before`，都只講結構，沒有一個說「讀得出」。

我能報的是排法本身：三行數字之下先接提示、再接斷點清單，兩者都縮排到
`籃子` 欄起點（36 欄），而三行數字的 `n`／RS 欄從第 46 欄起——所以附註與數字
不在同一組欄位上。區塊之間仍以空行分隔，沒有提示的支線一行都不會多。
會不會被誤讀成第四個籃子，我判不了。

## 腳本對自己這份 evidence 說了什麼

第一版 evidence 寫完後跑 `./scripts/acceptance-check.sh docs/sprints/016-evidence.md`：

```text
docs/sprints/016-evidence.md:1: [B2] spec 的驗收條件 H3 沒有出現在 evidence 裡
exit=1
```

真陽性。H3 的內容當時混在 H5 那一段裡沒有單獨交代，補上「H3 —」那一節之後
`exit=0`。**這是本輪唯一一次腳本抓到我自己的漏，值得記下來**——它抓的正是
「驗收條件沒有逐條交代」這一類，而那類漏很難靠自己重讀發現。

順帶：`docs/sprints/015-evidence.md` 也少了 `G8`（同樣是真陽性，未回頭補）。
