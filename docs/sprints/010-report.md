# Sprint 010 — 報告（驗收 `sprint/010-say-what-we-know`，已併入 `dev@874302d`）

分支自 `dev@73faf49`。驗收時 `dev` 尾端 = `73faf49`。
本報告由規劃端寫，**驗收看 diff 與實際輸出，不看實作端的自述**。
**測試結果規劃端驗證不了**（本機跑不了 `uv run pytest`）——`228 passed in 48.07s`
（`dev` 上是 213，+15 條）的唯一來源是 `010-evidence.md` 貼上來的輸出。

---

## 1. 做到的

| 項 | 判定 | 我自己驗到的物證 |
|---|---|---|
| DO-1 品質行改寫（四小項） | **通過** | `quality.py` diff：`entry is None` 分支裡 `_fmt_corr(market_row.get("rank_persistence_20"))` **整行刪除**，改 `持續性 {NO_BASELINE_TEXT}`。A1 是結構上成立，不是靠測試名字宣稱 |
| DO-1 A2 `market_row is None` | **通過** | 該支只 `return "持續性 n/a   換手 n/a   離散 n/a"`，後面的 footnote append 不會執行 |
| DO-1 A3 compute 層不動 | **通過，我獨立驗過** | `git diff dev..branch --stat -- marketpulse/calc.py momentum.py data.py themes.py themes/ narratives/ data/ docs/product/` **全空**；`quality.py` 的 diff 裡 `_percentile`、`compute_market_quality`、`persistence_null_test` 一行未動。實作端另外做了 ast body 比對＋parquet content-hash，**比我要求的還嚴** |
| DO-1 無門檻 | **通過** | `CHURN_PCT_DIRECTION`／`DISPERSION_PCT_DIRECTION` 是無條件常數，永遠印。D10 沒有從側門進來 |
| DO-2 B1／B2 | **通過** | `_freshness_line` 四種狀態字串都貼在 evidence；`freshness=None` → 標頭與 `dev` 逐字元相同 |
| DO-2 B3 終端機字串不變 | **通過** | `format_ops_status` 只把欄位換成 `st.*`；`caught_up` 由 `else` 分支內移到 `ops_status()` 並加上 `attempt is not None`，在該分支內等價 |
| DO-3.1 兩個「被講過」定義統一 | **通過** | `_mention_lookup` 先讀 `overlay.mention_dates`，缺席才回退——與 `radar._narrative_date_label` 同一個回退寫法。今天可見效果為零，**spec 事先就這樣寫了，evidence 也照實回報** |
| DO-3.2 溢出提示 | **通過** | `pending_snapshots` 改回傳全部、`render_pending_snapshots` 才套 cap 並算 overflow；`RECENT_EVENTS_LIMIT` 同理。cap 本身未動 |
| **測試名稱不承載目視宣稱** | **通過** | 15 個新測試名逐一看過，沒有 `align`／`readable`／`一眼`／`好懂`。**009 提出的那條新預設值第一次上路就守住了** |

### 要替實作端更正一項：那不是放寬，是收緊

它把「兩條 spec-005 測試從 `endswith(HORIZON_FOOTNOTE)` 改成 `in`」列在第 3 類，
自述為放寬。**淨效果相反。**新增的
`test_do1_d6_gloss_follows_the_horizon_footnote` 直接釘住兩行的相對位置：

```python
assert line.split("\n").index(D6_GLOSS) == line.split("\n").index(HORIZON_FOOTNOTE) + 1
```

`endswith` 只保證「是最後一行」，新測試保證「D6_GLOSS 緊接在 HORIZON_FOOTNOTE 之後」。
spec 005 DO-3 要保護的無條件出現性完好，位置約束比原本更強。誠實回報值得記一筆。

---

## 2. 沒做到的：一項，責任在規劃端

### DO-2 達成了 spec 的驗收條件，但 spec 問錯了問題

> **更正（2026-09-06，sprint 011 階段 0 加註）——本節引用的案例是假的。**
> 本節寫「當天是 09-06、09-05 週五是交易日」。**2026-09-04 是週五、09-05 是週六。**
> 當天資料並沒有落後，radar 標頭「資料到 2026-09-04」是對的。
> `caught_up` 偵測不到「我根本沒試過」這個**結構性論點仍然成立**，但它從此沒有
> 真實案例支撐，所以「新鮮度改成距今 N 個交易日」在 011 被降級為 UNKNOWN 而不是 DO。
> 逐日星期輸出見 `011-evidence.md` 第 1 節。
> **這是規劃端的第二個錯，疊在它自己承認的第一個錯上面。**
>
> **同節第 5 段「拍板 5：TPEx 89 天補齊，排 011」也是錯的——那 89 天早在 sprint 004
> 就補齊了**（`004-evidence.md` 第 79–90 行）。現場 twse/tpex 各 441 檔、日期集合相同。
> 011 不做這一項，backlog 該列已刪除。

`caught_up` 比的是 `last_raw_attempt.date == as_of`，而 `last_raw_attempt`
（`data.py:401`）讀的是 `data/raw/` **裡最新的那一天**，不是「上次跑 refresh 的時間」。
所以驗收當天：資料到 2026-09-04、最新 raw 也是 09-04 → `caught_up=True` → 頁面印

```text
資料到 2026-09-04 · raw last attempt 2026-09-04（twse=ok tpex=ok）
```

看起來完全正常，而當天是 09-06、09-05 週五是交易日。
**「使用者從週五之後就沒跑過 refresh」正是這條線結構上偵測不到的情境**——
而那正是 010-spec「PO 的前提決定」那一段自己寫下的立案理由。
`caught_up` 是一個自我一致性檢查，不可能知道「我根本沒試過」。

spec 只要求「這份頁面的資料到哪一天」與「上一次抓取是成功還是失敗」，
**實作端 100% 照做了。藥開錯了。**

**這是 009 DO-3.1 同一個病的第二次發作：**spec 描述了症狀的鄰居，沒描述症狀。
009 那次是「說 `敘事` 是唯一沒欄寬的欄」（`Momentum` 也沒有）；這次是
「問資料到哪一天」（該問的是「距今差幾個交易日」）。
**兩次都是規劃端把一個可觀察的表面現象當成病灶寫進 spec。**

修法不是純接線：repo 裡目前沒有任何地方拿 `date.today()` 跟 `as_of` 比
（`last_complete_session` 也是讀磁碟），要加「距今 N 個交易日」需要一個交易日概念。
排 011，見第 6 節。

---

## 3. 做了但 spec 沒要求的

1. **`quality_line(oneline=…)` 參數。**spec 要它「兩種都貼一次讓 PO 挑」，它做成
   版面參數而不是拋棄式片段。**不是 D10 把手**：純版面、不改任何數字、兩種版面都
   顯示全部資訊、沒有「挑好看的那個」的空間。接受，留著。
2. **`D6_GLOSS` 的位置連帶改了兩條 005 測試。**見上，淨收緊，接受。
3. **`radar.py` 新增 `TYPE_CHECKING` import `cli.OpsStatus`。**這是新的模組依賴
   方向：`cli` 執行期 import `radar`，`radar` 僅型別 import `cli`。目前用
   `TYPE_CHECKING` 擋住循環，且 `_freshness_line` 內部用 `getattr` duck typing，
   所以那個 import 其實只服務註解。**可留，記一筆**——下次動這兩個檔要記得方向已經雙向。
4. **`pending_snapshots` 的公開契約改了**（不再截斷）。為了拿 overflow 計數非得如此，
   caller 只有 `render_pending_snapshots`，測試已同步。合理，屬「好的那種」第 3 類。

---

## 4. 一個措辭問題（實質，因為那一行的存在理由就是精確）

```text
離散 15.8pp（近 60 個交易日第 18 百分位；越低＝族群名次越擠、當日名次差異的資訊量越低）
```

`dispersion` 是 top-half 減 bottom-half 的**平均 RS20**（`quality.py:71 _dispersion_row`，
Counterpoint Global 定義），單位是百分點，量的是**強弱差距**。
名次永遠是 1..11，不會「擠」。建議改成「族群之間的強弱差距越小」。
**規劃端不改產品程式碼**，排 011（見第 6 節）。

---

## 5. 五個拍板的裁決（PO 2026-09-06 全數採用規劃端建議）

| # | 決定 | 狀態 |
|---|---|---|
| 1 | 品質行**維持展開**（6 行）。`oneline=True` 留著隨時可翻 | 已是出貨預設 |
| 2 | `entry is None` **印「無基準」**，不印單日持續性。009 未決 1 結案 | 已實作 |
| 3 | DO-3 那格**留給 2×2 定義統一**；`Momentum` 欄寬續留 backlog | 已實作 |
| 4 | Momentum 的 display-only 豁免**收窄**為「必須可還原」 | 本輪寫入 `non-goals.md` D16 |
| 5 | TPEx 那 89 天**採讀法 A：補齊**（偏誤方向已知且單向；樣本量不足是 k=20 讀數最大的未載明不確定；且 A 可逆、B 幾乎不可逆） | 排 011，見第 6 節 |

**PO 另立一條長期指示：**往後開放式問題若未答，一律照規劃端推薦的選項走，不要卡住等答覆。
已記錄。**這不改變「真正 50/50 又不可逆的決定仍要寫進『等你拍板』」**——
差別只在於沒答時預設會被執行，而不是停下來。

---

## 6. 規則質疑 — Momentum 的 display-only 豁免，收窄（已由 PO 採納）

```text
條文：Momentum 是 display-only 標籤（5D／Breadth／Volume／Rank Δ5 的方向），
      因「不改變 rank」而不受 R1「無綜合評分」約束
起因：MVP 建置期寫下（coding-contract §5、CLAUDE.md），未見量測支持
物證：009-evidence 真實輸出——光通訊/CPO rank #1、RS20 +24.8%、breadth 10/10、
      5D +5.4% → 標 `Stable`；高速材料/CCL #3、RS20 +10.0% → 標 `Weakening`。
      010 階段 1「只看輸出」角色（未讀任何文件）第 6 條獨立指出四分類與 Momentum
      「用詞太像、看起來應該對得上又對不上」。同一現象早記於
      docs/sprints/past-momentum-visibility.md
詮釋：「不改變 rank」擋住的是污染，擋不住「四個輸入塌成一個讀者無法還原的判決」。
      R1 真正要防的是後者，豁免條款讓它從側門進來
決定：收窄——豁免僅適用於「讀者能從同一列可見數字還原出該標籤」的情形。
      現行 Momentum 不滿足；011 重做時必須連帶讓它可還原，否則改成不顯示
重看：011 驗收後
```

---

## 7. 排進 011 的四項（本輪產生，已寫入 backlog）

1. **`[使用]` 新鮮度改成「距今差幾個交易日」**——本輪 DO-2 的洞，第 2 節。
2. **`[使用]` `DISPERSION_PCT_DIRECTION` 措辭改成「強弱差距」**——第 4 節，一行。
3. **`[L1]` TPEx 89 天補齊**（拍板 5）。動資料層，需自己一輪的 Appetite。
4. **`[使用]` momentum 標籤重做，且必須可還原**——本輪收窄後的第一個受約束項目。

---

## 8. 規劃端自己造成的問題

- **010-spec 222 行，超出 200 行上限 22 行**（其中 55 行空行，正文 167 行）。已在報告
  artifact 裡揭露。三項 DO 各帶物證行號，砍行號等於砍交接價值——但下一輪若還是三項，
  要嘛砍成兩項，要嘛正式把上限改成「正文 200 行」並寫進 skill。
- **DO-2 的洞（第 2 節）。**這是本輪最大的一件事，且是規劃端的。
- **git 鎖檔。**規劃端這個工作階段一開始沒有刪檔權限，`73faf49` 那次 commit 在
  `.git/objects/` 留下 9 個 `tmp_obj_*`，後續 merge 又卡在無法清除的 `.git/index.lock`
  上連續失敗四次。已向 PO 要到刪檔權限並清乾淨，`dev` 工作目錄現在是乾淨的。
  **下次規劃端要動 git 之前先確認刪檔權限，不要等它爛在中間。**
- **收尾 commit 誤把 `docs/post/` 加進版控。**`git add -A docs/` 的副作用；那兩個檔
  （`20260903.md`／`20260904.md`）從 007 起就一直是刻意未追蹤的。已 `git rm --cached`
  ＋ amend 還原（`a931387` → `161a640`），檔案還在磁碟上、狀態回到未追蹤。
  **記在這裡而不是悄悄改掉**——下次收尾要指名檔案，不要用 `-A`。

## 9. 收尾狀態

- `874302d` 以 `--no-ff` 併入 `dev`。合併前 `010-evidence.md` 曾以未追蹤檔殘留在
  工作目錄（失敗的 merge 留下的），我先與分支版本 `diff` 確認逐字元相同才刪除，
  沒有覆蓋掉任何東西。
- **`dev` 尚未推到 `origin`**（目前領先 `origin/dev` 若干 commit）。要不要推由 PO 決定。
- 分支 `sprint/009-match-yardstick`、`sprint/010-say-what-we-know` 都還在，未刪。
- `docs/post/`、`.claude/_to_delete/` 仍是 untracked，未動。
