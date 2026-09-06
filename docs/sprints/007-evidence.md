# Sprint 007 — Evidence

Branch: `sprint/007-narrative-loop` (from `dev@0ed4697`; not merged)
As of: 2026-09-06

## Commits

| DO | Hash | Subject |
|---|---|---|
| DO-1 | `0caff6280a082d83cd988e6973654af8760f3133` | feat(product): DO-1 narrative coverage in brief and radar |
| DO-1 fix | `66b382426bb9c9b9104d5e2aa0f1e61a79f717b9` | fix(radar): no extra blank line when narrative overlay is off |
| DO-2 | `c5ea251e0d3c590abecbc8cfc78d01dcc9d6a2cf` | feat(narratives): DO-2 print due revisit at end of brief |
| DO-3 | `3cf6647a4062a4d6a6d426975fc955f434592686` | docs: DO-3 RRG superseded, D14, D2 rank-ic note, backlog sweep |

DO-1 fix is the HTML error-slot newline that made `--no-narratives` HTML differ from `dev` by one blank line. Caught while gathering acceptance 2.

## pytest

```text
168 passed in 45.94s
```

Command: `uv run pytest` (after `uv sync --extra dev`; `UV_CACHE_DIR=$PWD/.uv-cache`).

`dev` was 150 passed. +18 in `tests/test_narratives.py` / `test_product.py` / `test_radar.py`. The two tightened Rank-IC tests still pass (see DO-3).

## `git diff dev --stat`

```text
 docs/design-v0.2.md       |   7 ++
 docs/product/backlog.md   |  36 +++++---
 docs/product/non-goals.md |  22 +++++
 marketpulse/cli.py        | 110 +++++++++++++++++++++--
 marketpulse/narratives.py | 129 +++++++++++++++++++++++++++
 marketpulse/product.py    |  67 ++++++++++++++
 marketpulse/radar.py      |  79 ++++++++++++++---
 tests/test_narratives.py  | 152 ++++++++++++++++++++++++++++++++
 tests/test_product.py     | 220 ++++++++++++++++++++++++++++++++++++++++++++++
 tests/test_radar.py       |  66 ++++++++++++++
 tests/test_rank_ic.py     |  18 ++--
 11 files changed, 871 insertions(+), 35 deletions(-)
```

No change to `calc.py`, `quality.py`, `themes/v1.yaml`, narrative schema, `persistence_null_test`, `compute_rank_ic`, or `rank_ic_null_test`.

---

## DO-1 — 敘事覆蓋進 brief 與 radar

### 實際 brief 片段（as_of=2026-09-03，預設開）

Command: `uv run marketpulse brief --data-dir data`  
Snapshot: `theme_daily.parquet` as_of=2026-09-03, 11 themes. Narratives dir = `narratives/`.

主表之後（文案為 spec 鎖定字串；區塊未省略）：

```text
強但沒人講
光通訊/CPO  #1
散熱/液冷  #2
高速材料/CCL  #3

有人講但弱
（無）
```

PIT：`load_as_of(2026-09-03)` 回空快照——兩份 narrative 檔的 `snapshot_date` 是 2026-09-04 與 2026-09-06，都晚於最新價量日。覆蓋為空是對的，不是 bug。

### radar「敘事」欄（Momentum 之後、最右）

Command: `uv run marketpulse radar --data-dir data --output /tmp/mp-007-on-radar.html`  
（不寫 `reports/`。）

```text
Sector                    1D       5D      20D     RS20  Breadth  Volume  Rank R5·R20·R60  Rot  Momentum  敘事
------------------------------------------------------------------------------------------------------------------
 光通訊/CPO             -5.6%    +4.0%   +26.5%   +23.7%     9/10    1.1x  3·#1·4           →    Weakening  —
 散熱/液冷              -3.1%    +6.1%   +20.8%   +18.0%      4/5    0.8x  1·#2·2           ↑    Weakening  —
 高速材料/CCL           -4.6%    -7.5%   +19.2%   +16.5%      2/4    0.5x  10·#3·1          ↓    Weakening  —
 先進製程               -1.6%    -0.2%    +6.4%    +3.6%      2/6    0.8x  5·#4·3           ↑↑   Weakening  —
 …
 AI伺服器               -3.5%    -8.7%    -4.1%    -6.9%     3/10    1.0x  11·#11·7         →    Weak  —
```

全 `—`。同一 PIT 原因。HTML 主表同樣在 Momentum 之後加 `<th>敘事</th>`，不著色、不參與排序。

### 驗收條件 2 — 關掉新欄位後與 `dev@0ed4697` 逐字元相同

開關是渲染參數 `show_narratives`（預設開），CLI 為 `--narratives/--no-narratives`。**不是 sed 砍欄位。**

**007**（`sprint/007-narrative-loop`，cwd = repo）：

```text
uv run marketpulse brief --no-narratives --data-dir data > /tmp/mp-007-off-brief.txt
uv run marketpulse radar --no-narratives --data-dir data --output /tmp/mp-007-off-radar.html > /tmp/mp-007-off-radar.stdout
sed '$d' /tmp/mp-007-off-radar.stdout > /tmp/mp-007-off-radar.txt
```

`sed '$d'` 去掉 ASCII 最後一行 HTML 路徑（兩邊路徑本來就不同）。

**dev**（worktree `/tmp/mp-007-dev-base` @ `0ed4697`）。不能在 worktree 裡 `uv run marketpulse`——editable install 仍指向 007 工作樹。cwd 必須是 worktree，讓 `sys.path[0]` 不是 007：

```text
git worktree add /tmp/mp-007-dev-base 0ed4697
cd /tmp/mp-007-dev-base
PYTHONPATH=/tmp/mp-007-dev-base $REPO/.venv/bin/python  # render_brief / render_radar / render_radar_html
# 寫到 /tmp/mp-007-dev-brief.txt / mp-007-dev-radar.txt / mp-007-dev-radar.html
```

```text
$ diff -u /tmp/mp-007-dev-brief.txt /tmp/mp-007-off-brief.txt
$ diff -u /tmp/mp-007-dev-radar.txt /tmp/mp-007-off-radar.txt
$ diff -u /tmp/mp-007-dev-radar.html /tmp/mp-007-off-radar.html
$
```

三份 diff 都是空的。`cmp` 通過。sha1：

| 檔 | sha1 |
|---|---|
| brief（兩邊） | `1792af4beeb16dc7de7ec5d846a80a921b77fc52` |
| radar ASCII（兩邊） | `e36e8c3f7c8d79438af5ddfae9e30f39d7c8f336` |
| radar HTML（兩邊） | `f53c276ae298db6bf886e034d0210b2a05a83ecf` |

（與 006 驗收條件 6 的三個 sha1 相同：第一層產物沒動。）

第一次 HTML 比對多了一行空行（`error_p` 插槽在 `show_narratives=False` 仍換行）。修在 `66b3824`，修後上表才成立。

單元測試鎖同一個開關：`test_brief_show_narratives_false_ignores_overlay_byte_identical`、`test_radar_narrative_column_after_momentum_and_flag_off`。

### 無檔案

空 `narratives_dir`：不 raise。敘事欄全 `—`。清單：

```text
強但沒人講
光通訊/CPO  #1
散熱/液冷  #2
高速材料/CCL  #3

有人講但弱
（無）
```

### 壞檔案

`{ this is not yaml: [` → 第一層照常（`光通訊/CPO`、RS20、品質行都在），加一行：

```text
narrative 讀取失敗：while parsing a flow node
expected the node content, but found '<stream end>'
  in "<unicode string>", line 1, column 22:
    { this is not yaml: [
                         ^
```

### 「弱」門檻 — 量了，沒調

`rank >= ceil(n_themes / 2)`，11 主題 → rank ≥ 6。未改常數（D10）。

2026-09-03 名次：

| rank | theme_id | 覆蓋（PIT as_of=09-03） | 覆蓋（反事實：09-06 快照） |
|---|---|---|---|
| 1 | optical_cpo | 否 | 否（`named_symbols: []` → coverage unknown；不用 narrative_id 對 theme_id） |
| 2 | thermal | 否 | 否 |
| 3 | high_speed_materials | 否 | 否 |
| 4 | foundry_advanced | 否 | **是**（nvhbm `named_symbols: ["2330"]`） |
| 5–11 | pcb … ai_server | 否 | 否 |

- PIT：覆蓋空 → `強但沒人講` 前三名（3 行，不是永遠滿的 5、也不是空）、`有人講但弱` =（無）。
- 反事實：唯一被講到的是 rank 4 的先進製程，4 < 6 → `有人講但弱` 仍（無）。空的原因是「被講到的主題不夠弱」，不是門檻讓清單永遠空。optical_cpo 有一則同名 narrative，但 `coverage_report` 判 unknown，不算覆蓋——這是 spec 要的，沒有另寫一套比對。

沒有自己改門檻。

---

## DO-2 — revisit 到期主動出現

掛在 `render_brief` 結尾（`refresh` 印 brief，所以兩個指令都會出現；沒有在 radar／ops 之後再印一次，那會重複）。測試不走 `refresh`（會打官網）。

### 到期（日期型）

合成：`revisit: 2026-09-01`、as_of=2026-09-06、一支 branch：

```text
到期重看
due_one · b1 · 2026-09-01 · claim text for the due branch

條件型（無法判斷是否到期）
cond_one · Broadcom 下一次財報電話會議
```

`future_one` / `2026-12-01` 不出現。ISO 以外的字串不解析（`2026-10-15 或 Broadcom…` 整段進條件型）。

### 條件型（真實 `narratives/2026-09-06.yaml`，as_of=2026-09-06）

三則 revisit 都不是純 ISO 日期：

```text
到期重看
（無）

條件型（無法判斷是否到期）
asic_xpu · 2026-10-15 或 Broadcom 下一次財報電話會議（以先到者為準）
nvhbm · 台積電 2026-10 法說（HBM4 base die 代工客戶／資本支出揭露）
optical_cpo · 2026-10-01；若 optical_cpo 主題 rank 跌出前 3 則提前重評
```

日常 `brief`（as_of=2026-09-03）因 PIT 拿不到這份快照，印的是下一欄的空狀態。

### 無項目

```text
到期重看
（無）

條件型（無法判斷是否到期）
（無）
```

兩個標題字串都在；不省略區塊。

### mtime／內容不變

斷言名：

- `tests/test_narratives.py::test_revisit_due_does_not_change_narratives_mtime_or_bytes`
- `tests/test_product.py::test_brief_render_does_not_change_narratives_mtime_or_bytes`

對 `narratives/*.yaml` 比對 `(st_mtime_ns, read_bytes())`，呼叫 `render_revisit_due` / `render_brief` / `load_as_of_lenient` 前後相同。沒有走 `refresh`。

---

## DO-3 — 文件矛盾與 backlog 掃除

四項各有 diff。

### 1. `docs/design-v0.2.md` §16

```diff
 # 16. Optional RRG
 
+> **[SUPERSEDED 2026-09-04 → non-goals.md D3]**
+>
+> Retained as history. RRG is an explicit non-goal. The former coding-contract
+> §11 conditional ("RRG may be added only after the Rank Timeline works") was
+> withdrawn on 2026-09-04 because the Timeline already works, which under that
+> wording would have unlocked RRG by default.
+
 RRG is an optional visualization, not the MarketPulse core algorithm.
```

內文保留。

### 2. `docs/product/non-goals.md` D2 + D14

D2 補一句、不另寫第二個版本：`rank-ic` 是買資訊的診斷，不進產品、不改 rank、不模擬進出場。D14 是 PO 前提 1 的原文抄入（brief／radar 逐字元不變由規則降級為預設值；R3 不變）。

### 3. backlog

刪三項（刪不是重排）：

- `above_count` 待排殘留 → 搬到已完成（005–006）
- 脈絡生命週期狀態機／burst detection
- PTT 每日掃描

「本輪明確不做」五項寫進 `### Sprint 007 明確不做（轉入 backlog，附物證）`，每項附階段 1／006-review 條號，不是一行標題。

### 4. 收緊兩條測試 — 實際輸出

```text
$ uv run pytest tests/test_rank_ic.py::test_shuffled_null_sigma_within_three \
    tests/test_rank_ic.py::test_persistent_null_sigma_positive_zero_exceedance -v
tests/test_rank_ic.py::test_shuffled_null_sigma_within_three PASSED
tests/test_rank_ic.py::test_persistent_null_sigma_positive_zero_exceedance PASSED
2 passed in 17.62s
```

`.any()` → `.all()`；`iloc[0]` → 所有 passing 列。沒有格子不符，沒有調鬆斷言。

```diff
-    assert bool((passing["sigma"].abs() < 3).any())
+    assert bool((passing["sigma"].abs() < 3).all())
-    cell = passing.iloc[0]
-    assert cell["sigma"] > 3
-    assert int(cell["n_ge_observed"]) == 0
+    assert bool((passing["sigma"] > 3).all())
+    assert bool((passing["n_ge_observed"] == 0).all())
```

---

## 沒做

- 不 merge。
- 不新增套件、不改 narrative schema、不動第一層計算。
- 006-review A1／A2／`n_iter` 改名／guard-fail `n=` 位置：寫進 backlog，程式未動（spec 不可碰 `rank_ic_null_test`）。
- momentum 標籤、品質行、`narrate add`、換 primary／composite／RRG／as-of 成分／雙池／burst／PTT：明確不做。

## spec 沒要求、但做了

- CLI `--narratives/--no-narratives`：spec 要的是渲染參數；CLI 旗標讓驗收條件 2 的比對指令可以不 sed。
- `themes_path` 不存在時 overlay 不 raise（`test_cli_smoke` 在 `tmp_path` 跑 brief）。覆蓋當成全空，第一層照印。
- `66b3824` HTML 空行：不做的話驗收條件 2 的 HTML 差一行，說不清楚。
- 到期重看掛在 `render_brief` 結尾，而不是 `refresh` 在 ops 之後再印一次。
