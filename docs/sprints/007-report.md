# Sprint 007 — Report

驗收對象：`sprint/007-narrative-loop`（`1eeb125`，自 `dev@0ed4697`，未併）
驗收日：2026-09-06　撰寫：規劃端（Cowork），階段 0
物證：`docs/sprints/007-evidence.md`；本報告另有規劃端自行讀 diff 得到的三項發現。

**規劃端不跑測試。**`168 passed in 45.94s`、三份 `diff -u` 為空、三個 sha1 —
唯一來源是實作端貼進 evidence 的輸出，本報告不為其背書。
規劃端能獨立確認的是：開關是渲染參數而非 `sed`、第一層模組在 diff 裡一行未動、
18 個新測試名與 `150 → 168` 的增量對得上。

---

## 一、做到的

**DO-1（敘事覆蓋進 brief 與 radar）** 五條驗收條件全數對得上。

- 文案字面鎖進常數（`narratives.py:54-66`：`TITLE_STRONG_UNCOVERED` 等），不從數字改寫（D10）。
- 驗收條件 2 走渲染參數 `show_narratives`（預設開）＋ CLI `--narratives/--no-narratives`，
  **不是手工 sed** —— 這正是 spec「兔子洞」點名最容易做壞的地方，沒做壞。
- 無檔案／壞檔案：`load_as_of_lenient()` 吞例外回空快照＋一行訊息，第一層照印。
- 覆蓋走既有 `coverage_report()`，沒有另寫一套主題↔標的比對（spec 明令）。

**DO-2（revisit 到期）** 四條對得上。日期型只吃純 ISO、不解析自然語言；
`（無）` 佔位；mtime／bytes 斷言存在
（`test_revisit_due_does_not_change_narratives_mtime_or_bytes`、
`test_brief_render_does_not_change_narratives_mtime_or_bytes`）；不走 `refresh`。

**DO-3（文件矛盾與 backlog 掃除）** 四項逐一讀過 diff，全部落地。

1. `design-v0.2.md` §16 加 `[SUPERSEDED 2026-09-04 → non-goals.md D3]`，內文保留。
2. `non-goals.md` D2 補一句（`rank-ic` 是買資訊的診斷），**沒有並存第二版本**；D14 新增。
3. backlog 刪三項。**規劃端查證一次：**`backlog.md:70` 仍有 `above_count` 一列，
   但那在「Sprint 005 已排入」的歷史區塊，不是待排；待排那一列確實被刪。
   這是查證結果，不是指控。
4. `test_rank_ic.py`：`.any() → .all()`、`iloc[0] →` 全 passing 列。沒有調鬆斷言。

**Appetite 守住。**不新增模組檔、不新增套件、不改 `themes/v1.yaml`、不改 narrative schema。
`calc.py`／`quality.py`／`momentum.py`／`themes.py` 在 diff 裡零改動 —— 第一層數字沒動，
不可污染原則（R3）沒破。禁區檔（`persistence_null_test`、`compute_rank_ic`、
`rank_ic_null_test`）未碰。未 merge。

---

## 二、沒做到的 / 有偏差的

**B1. DO-2 在 `refresh` 裡不在結尾。**
spec 寫「`refresh` 與 `brief` 結尾各印一段」。實作掛在 `render_brief()` 結尾，
而 `refresh` 的輸出順序是 brief → chart → radar ASCII → radar 路徑 → ops status
（`cli.py:587-632`）。所以在 `refresh` 裡「到期重看」被埋在中段。
實作端有揭露並給了理由（避免重複印）。理由成立，但**結果與 spec 字面不同**，
且 `refresh` 是每天真的會跑的那個指令 —— 到期提醒被三段輸出蓋掉，等於半個鬧鐘。

**B2. 敘事欄的語意與 spec 字面不同。**
spec：「該主題**最近一次**被 narrative 提及的日期」。
實作 `theme_mention_dates()` 回的是 **PIT 快照本身的 `snapshot_date`** ——
所有被提及的主題印同一個日期。等於一個穿著日期外衣的布林值。
`narratives/` 只有兩份檔時看不出來；快照累積之後，這一欄會**看起來**在說
「這個主題多久沒人提」，而它其實只在說「有沒有出現在最新那一份」。
docstring 老實寫了這件事，但畫面上看不到 docstring。

---

## 三、做了但 spec 沒要求的

實作端自報四項，逐項確認：

| 項目 | 判定 |
|---|---|
| CLI `--narratives/--no-narratives` | **正當。**spec 只要渲染參數；有 CLI 旗標，驗收條件 2 的比對指令才不用 sed |
| `66b3824` HTML 空行 | **正當，且是必要修正。**`error_p` 插槽在關掉時仍換行，不修則 HTML 差一行 |
| 到期重看掛 `render_brief` | 見 B1 —— 這是偏差不是加料 |
| `themes_path` 缺失時 overlay 不 raise | **有問題，見 F1** |

---

## 四、規劃端自己讀 diff 查到的三件事

### F1 — `themes_path` 不存在時靜默給出錯答案（建議修）

`cli.py::_load_overlay`：`themes_path` 不存在 → 回 `_empty_theme_set()`，**且 `error=None`**。
`theme_mention_dates()` 對空 `ThemeSet` 回 `{}` → 每個主題都被判成沒人講 →
「強但沒人講」照印前三名、敘事欄全 `—`、**畫面上沒有任何訊息**。

壞 YAML 那條路會印「narrative 讀取失敗：…」，這條不會。
兩者同樣是「覆蓋資料讀不到」，一條會說、一條不會說 —— 而不會說的那條印出來的是
一個看起來很有自信的錯誤結論。建議這條也塞進 `overlay.error`。

### F2 — 覆蓋判定讓三則 narrative 有兩則永遠對不上主題（本輪最重要）

規劃端自己對 `themes/v1.yaml` 與 `narratives/2026-09-06.yaml` 逐一比對：

| narrative | `named_symbols` | 對得上的主題 | `coverage_report` |
|---|---|---|---|
| `optical_cpo` | `[]` | — | `unknown` |
| `asic_xpu` | `["2454"]` | **無** —— 2454 不在 11 個主題的任何成分裡 | `uncovered` |
| `nvhbm` | `["2330"]` | `foundry_advanced` | `covered` |

後果：**光通訊/CPO（rank #1）會出現在「強但沒人講」，而使用者明明寫了一則叫
`optical_cpo` 的故事。**「強但沒人講」現在的失敗方向是**假陽性** ——
它會對著使用者上週才寫過的主題說沒人講。

這不是門檻問題（門檻那件事實作端量過了，結論成立：被講到的主題不夠弱，不是門檻永遠空）。
這是 `named_symbols` 沒填、或填了不在任何主題成分裡。
**spec 明令「用既有 `coverage_report()`，不要自己重寫主題↔標的比對」，實作端照做了。
問題在 spec，不在實作。**

### F3 — radar 分隔線寬度（外觀，小）

開新欄時 `"-" * 114`（`radar.py:184`），但表頭實際顯示寬度是 110。
關掉時是 104 對 100，本來就短 4；現在變成長 4。114 是憑空的數字，不是算出來的。

---

## 五、閘門與其他

- **006-review B4 未結。**006-review 要求「005-report 的『對角線隨天期上升』要在
  005-report 裡明白更正」。`docs/sprints/005-report.md:108` 現在仍是原句。
  007 spec 沒排它（合理，不在本輪範圍），但這是上一輪未回答的決定，會擋下一輪的閘門。
- **沒有 `006-report.md`**，只有 `006-review.md`；索引已把 006 標成已完成。
- evidence 的 `git diff dev --stat` 是 11 檔 871 行，現在實際是 12 檔 1177 行 ——
  差的是 evidence 檔自己（`1eeb125` 在統計之後才 commit）。正常，不是漏報。
- spec 寫「自 `dev@fe935d1`」，實際 base 是 `0ed4697`（spec 自己那顆 commit，
  也就是當時的 dev tip）。evidence 有寫清楚。**這是規劃端寫 spec 時的疏忽，不是實作端跑掉。**
- **使用痕跡：**`narratives/` 自 2026-09-05 起無新快照。但 `docs/post/`（未追蹤）
  有 `20260903.md`、`20260904.md` 兩份自由格式筆記 ——
  **使用者一直在寫，只是沒寫成 narrative YAML。**這是 PO 前提 4（「先確認回饋迴路有效，
  再降寫入摩擦」）下一步最直接的物證。

---

## 六、等你拍板

1. **B1** — DO-2 在 `refresh` 只出現在 brief 段落中間，可接受嗎？
   （預設：可接受，不追加；若不接受則 `refresh` 尾端補印一次）
2. **B2（判讀題）** — 敘事欄現在是「在不在最新快照」的布林，穿著日期外衣。
   要 (a) 維持現狀但改欄名為布林語意、(b) 改成真正掃全部快照的「最近一次提及日」、
   還是 (c) 留著等快照多了再說？
3. **F1** — 靜默失敗現在修（一行，塞進 `overlay.error`）還是進 backlog？（預設：現在修）
4. **F2** — 三條路：擴主題成分（2454 該進哪個主題？）／narrative 允許直接寫 `theme_ids`／
   覆蓋改看 `inferred_symbols` ＋ branch 籃子。**這是下一輪 DO 的核心，不是小修。**
5. **併不併** — 007 要不要進 `dev`？未獲授權前規劃端不動。

---

## 七、規劃端自己造成的問題

1. spec 權限邊界寫「自 `dev@fe935d1`」，寫的當下 spec 本身還沒 commit，
   實際 tip 是 `0ed4697`。實作端選對了，但 spec 那行是錯的。
2. **F2 是 spec 的錯。**spec 把「用 `coverage_report()`」寫成硬規定，
   卻沒有先檢查現有三則 narrative 有幾則實際對得上主題 —— 答案是一則。
   驗收條件 5 要求測 covered／uncovered，測試用合成資料全綠，
   而真實資料上這個功能對兩則故事是啞的。**「有測試」不等於「在真資料上有用」。**
3. spec 說敘事欄是「最近一次提及日」，卻同時要求只取 PIT 最新一份快照。
   這兩句在只有一份快照可用時不矛盾，多份時就矛盾。B2 是這個矛盾的產物，不是實作端誤讀。

---

## 八、併入紀錄（Q8 要求註明是誰按的）

**2026-09-06，由規劃端（Cowork）在 PO 明示授權下 fast-forward 併入 `dev`。**

- `dev` `0ed4697` → `537142c`（＝ `sprint/007-narrative-loop` 分支尾）
- 手法：`git update-ref refs/heads/dev <new> <old>`，非 `git merge`。
  理由：規劃端的 VM 不能 `checkout`（無法 unlink 檔案），而 `dev` 是 007 的祖先，
  fast-forward 只是移動 ref。`<old>` 當守衛，`dev` 若被動過會拒絕。
- 併前確認：`git merge-base --is-ancestor dev sprint/007-narrative-loop` 通過。
- **併入時 F1／F2／F3 都還沒修。**`dev` 上因此有一版會誤報「強但沒人講」的覆蓋清單，
  這是知情的取捨，不是遺漏——008 第一項就是修它。
- `origin/dev` 落後 6 個 commit，push 要由 PO 在 Mac 上做（規劃端 VM 對 github.com:22 封鎖）。
- 殘骸分支 `sprint/004-narrative-shape`／`005-horizon-ic`／`006-ic-null` 經查證
  `ahead of dev` 皆為 0，零未併成果，建議刪除；規劃端 VM 卡 `packed-refs.lock` 刪不掉，
  由 PO 在 Mac 上執行。
