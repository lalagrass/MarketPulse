# Sprint 014 — 實作端回報（`sprint/014-three-baskets`）

分支自 `dev@59c9cf1`。**未併入 —— 由 PO 決定。**
物證全部在 `docs/sprints/014-evidence.md`；本報告只講三件事：
做了什麼、**沒**做什麼、**spec 沒要求但我做了**什麼。

| DO | commit | 狀態 |
|---|---|---|
| DO-1 支線的籃子從一個變三個 | `8d956f8` | 完成 |
| DO-2 面板一條支線印三行 | `44cdd16` | 完成（F10 待 PO 目視） |
| DO-3 回頭日期拆成日期與條件 | `b5cb19a` | 完成 |

`uv run pytest` → `326 passed in 59.21s`（`dev` 上 301）。

---

## 1. 做到的

### DO-1

`Branch.basket` 變成 `if_true` / `if_false` / `either_way` 三個欄位。
`branches[].baskets:` 收這三個鍵；舊的 `branches[].basket:` 繼續解析、讀成
`if_true`。`either_way` 收 theme_ids，經既有 `ThemeSet` 展開成成員，
沒有第二份成員表。

| 驗收 | 判定 | 物證 |
|---|---|---|
| F1 兩份真實檔載入且成員不變 | 通過 | evidence §6 末段的三行對照 |
| F2 只寫舊 `basket:` → 進 `if_true`，另兩組空 | 通過 | evidence §6 |
| F3 DO-1 commit 上輸出與 `dev` 逐字元相同 | 通過 | evidence §4，`diff` 為空 |
| F4 未知 theme_id 被指名 | 通過 | 資料面在 DO-1（`unknown_either_way_theme_ids`），**上畫面在 DO-2 commit**，evidence §5.2 |

F4 分兩個 commit 落地是被 F3 逼出來的：F3 要求 DO-1 的輸出一個位元都不能動，
所以「印到畫面上」只能等 DO-2。DO-1 提供可被指名的資料並用測試釘住。

### DO-2

一條 live 支線印三行，固定順序 `誰贏都賺`（either_way）→ `成真`（if_true）
→ `反面`（if_false）。順序寫死在 `BASKET_ORDER`，不隨強弱改變。

| 驗收 | 判定 | 物證 |
|---|---|---|
| F5 三籃都有成員 → 三行且順序正確 | 通過 | evidence §5.2 |
| F6 空籃仍出現、印 `無標的` | 通過 | evidence §5.1（真實資料上大多數籃子都是空的） |
| F7 共同代號的檔數看得見 | 通過 | evidence §5.2，`成真／反面共同 1 檔` |
| F8 同一組 theme_ids 跨兩則故事 → 提示 | 通過 | evidence §5.2，兩行都印且各自指名對方 |
| F9 表頭短註為常數、不隨數字改變 | 通過 | 逐字抄自 spec 附錄，是 `PANEL_READING_NOTE` 常數 |
| F10 目視 | **不判定 —— 交 PO** | evidence §5.3 貼了排法與原文 |

**F5／F7／F8 在真實 `narratives/` 上觸發不了。**三則故事的支線全部只有舊的
`basket:`，`if_false` 與 `either_way` 一律空。本輪不改資料（前提決定 4），
所以這三條的物證用一份跑在**真實 `data/`** 上的示範 narratives 產生
（evidence §5.2），示範 YAML 沒有進版控。

### DO-3

`revisit` 收純 ISO，條件文字移到新的 `revisit_note`。舊的自由文字 `revisit`
行為與本輪之前完全相同。

| 驗收 | 判定 |
|---|---|
| F11 ISO 且 ≤ as_of → 到期重看 | 通過 |
| F12 ISO ＋ `revisit_note` 同一行都出現 | 通過 |
| F13 舊自由文字仍落條件型、不 raise | 通過 |
| F14 空 `revisit` 仍 raise | 通過（`revisit_note` **不能**代替它） |

fixture 輸出原文在 evidence §6。

**現有三則 narrative 仍然全部落在「條件型」，`到期重看` 仍是（無）。**
點火率還是 0/3，和 spec 的預期一致——本輪給的是欄位，不是資料。
要讓它點火，PO 得把 `revisit` 拆開；`asic_xpu` 與 `optical_cpo` 的原文已帶
ISO 日期，拆得動，`nvhbm` 的「台積電 2026-10 法說」沒有日，要 PO 給一個。
`narratives/` 在「不可碰」清單上，我沒有動。

---

## 2. 沒做到 / 沒做的

- **F10 我沒有判定，也不打算判定。**我可以說欄位怎麼排、寬度怎麼算；
  「一眼看得出」是人的判斷。測試名稱沒有承載這個宣稱
  （`test_do2_two_branches_are_visually_separated` 釘的是「三行連續＋中間空一行」
  這個可測的一半，docstring 明寫另一半歸 PO）。
- **`narratives/` 一個字沒改。**因此 F5／F7／F8 在版控內的資料上沒有正例。
- **未決問題 1（`either_way` 能不能混代號）：沒有自己加。**
  現有三則故事的上游都對得到既有主題，沒有遇到「上游不在任何主題裡」的情況，
  所以沒有理由開這個口。目前行為是：寫進 `either_way` 的股票代號不是 theme_id，
  會被 `unknown_either_way_theme_ids` 當成未知 id **指名在畫面上**，
  不會被靜默併進成員。規劃端傾向「不要混」，實作照這個傾向落地了。
- 本輪明確不做的六項（`dir`、`sources/`、時間軸、價差線、共動提名、
  `radar.py` 敘事欄）一項都沒碰。

---

## 3. spec 沒要求但我做了的

這節是重點，四項，依「可能引起異議」排序。

### 3.1 動了 `marketpulse/cli.py`（9 行）—— 踩到 Appetite 的「只動兩個模組」

`compute_basket_metrics` 需要一個 `ThemeSet` 才能展開 `either_way`
（spec 兔子洞第二條要求走既有 `ThemeSet`），但 `baskets` 指令原本不載 themes。
所以給它加了 `--themes-path`（預設 `DEFAULT_THEMES`，與其他指令同一個常數），
並更新 docstring。無行為改變、無新輸出、無新相依。

替代做法是讓 `baskets.py` 自己用寫死路徑載 YAML——那會在讀端埋一個隱藏的檔案
相依，比多一個 CLI 選項糟。**如果 PO 認為 Appetite 是硬邊界，這 9 行要退回，
DO-2 就得換做法。**

### 3.2 兩個新的 raise：`basket` 與 `baskets` 並存、`baskets` 出現未知鍵

spec 沒提這兩種情況。兩者的失敗模式和 F4 是同一種——**一整籃靜默消失**：
寫了 `if_ture:` 的人會以為籃子填好了，面板卻印 `無標的`。所以照 F4 的理由
選了 raise 而不是猜。這是新增的嚴格性，會讓某些寫法從「能載入」變成「載不進去」；
現有 `narratives/` 兩份檔都不受影響（F1 通過）。

### 3.3 支線之間空一行

spec 說「一條 live 支線印三行」。我照做了三行，但**在支線之間多印了一個空行**。
理由是 F10：沒有分隔的話，連續三條支線是九行連在一起，三行一組的邊界只靠
最左欄有沒有字來判斷。空行是最便宜的分隔。**如果 PO 覺得這違反「印三行」的
字面，拿掉是一行 code 的事。**

### 3.4 `baskets.py` 匯入 `product.py` 的 `_ljust` / `_vislen`

中文欄位用 `str.ljust` 會歪（Python 數字元，終端機數欄寬）。這兩個函式已經在
`product.py` 存在且被 `radar.py` 用過。依契約 #1「reuse before implementation」
選了匯入，而不是在 `baskets.py` 抄一份。`product.py` 一個字沒改
（它在「不可碰」清單上——匯入不算碰，但還是講明）。

---

## 4. 契約紅線自檢

| | |
|---|---|
| **R1** 三籃不得合成單一數字 | 沒有總分、價差、比值。`成真／反面共同 N 檔` 是計數，沒有被任何東西除過；`overlap_counts` 的 docstring 明寫不得長成比率 |
| **R3** 第二層不得回頭改第一層 | `baskets.py` 只讀 `read_normalized()`，沒有任何 `to_parquet`。測試釘住 snapshot mtime 不變、且不存在 `basket_daily.parquet` |
| **D10** 不得有強弱門檻 | 全檔沒有一個 `if rs...` 的分支。短註是常數 `PANEL_READING_NOTE`，測試斷言它不含 ASCII 數字，且在兩個數字不同的 session 上逐字相同 |
| **D11** 三個扁平清單 ＋ theme_ids | `Branch` 就是三個 `tuple[str, ...]`。沒有圖、沒有巢狀 |
| **D14** `brief` 與 `radar` 產物不變 | `dev` 與分支尖端各跑一次，`diff` 兩次皆空（evidence §8） |

---

## 5. 給下一輪的一句話

本輪把「一則故事三個籃子」的**欄位**做出來了，但版控裡的資料還是一則也沒填。
面板現在能說的三句話（誰贏都賺 / 成真 / 反面、共同幾檔、這條上游不區辨）
在真實資料上目前只印得出第一句的空版本。**下一輪之前需要 PO 填一次籃子**，
否則 015 會在同一個空面板上再疊功能。
