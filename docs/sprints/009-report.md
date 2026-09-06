# Sprint 009 — 報告（驗收 `sprint/009-match-yardstick`，未併）

分支：`sprint/009-match-yardstick`，自 `dev@d428807`。驗收時 `dev` 尾端 = `origin/dev` = `d428807`。
本報告由規劃端寫，**驗收看 diff 與實際輸出，不看實作端的自述**。
**測試結果規劃端驗證不了**（本機 VM 跑不了 `uv run pytest`）——`213 passed in 45.61s`
的唯一來源是 `009-evidence.md` 貼上來的輸出。

---

## 1. 做到的

| 項 | 判定 | 我自己驗到的物證 |
|---|---|---|
| DO-1 品質行改印 baseline `observed` | **通過**（5/5） | `quality.py:528/535` — `entry is None` 走日值、有 entry 走 `entry["observed"]`。`git diff` 證實 `persistence_null_test`／`compute_market_quality`／`_rank_persistence_series`／`signal_quality_null.json` 零改動 |
| DO-1 驗收 2 的不變式測試 | **通過，且不是同義反覆** | `tests/test_quality.py` 斷言 `token == _fmt_corr(entry["observed"])` **且** `daily not in line`；fixture 的日值 `-1.00` 與 `observed=.1404` 異號，正負號矛盾在結構上不可能 |
| DO-2 `尚未生效` | **通過**（4/4） | `_snapshot_date_only` 只 `yaml.safe_load` 後取 `snapshot_date`，其餘一律丟；`render_pending_snapshots` 不回傳任何內容欄位。位置照未決 2 預設 |
| DO-3.2 F5 `declared` | **通過** | `coverage_report` 與 `_mentioned_theme_ids` 同用 `_valid_declared_theme_ids`；`unknown_theme_ids` 未動，008 的未知 id 訊息仍在 |
| DO-3.3 F6 一份成員判定 | **通過，等價性我自己證過** | 舊碼用 `all_members`（全主題成員聯集），新碼 `_named_symbols_in_themes` 用「被命中主題的成員聯集」。兩者等價：任一落在 `all_members` 的代號必屬某主題，該主題必被 `named & members` 命中，故其成員全進聯集。「對外行為不得改變」成立，不是測試碰巧沒抓到 |

---

## 2. 沒做到的

### DO-3.1 F4 驗收條件未達成，且實作端歸錯類

spec 驗收條件白紙黑字：「第 1 項貼表頭＋分隔線＋一列 `—`＋一列日期的實際字串，**四者右緣對齊**」。
實作端把這件事寫在回報的第 3 類「spec 沒要求、但量到的」。**那是 spec 要求的**，
所以正確判定是「沒做到」，不是「額外發現」。

實際輸出（`009-evidence.md`，真實 refresh）四者右緣不齊，因為 `Momentum` 也沒有欄寬：
`Stable` 6／`Weakening` 9／`Weak` 4／`Strong` 6／`Improving` 9／表頭 `Momentum` 8。
（實作端寫「Improving 10」——**是 9**，數錯了一格。不影響結論。）

**更根本的問題：這一項的淨效果是零可見改變。**`敘事` 是最後一欄，給最後一欄補右側空白
只會產生尾隨空白；分隔線從 110 拉到 116，比任何可見內容多出 6 格。
真正的病灶是 **`敘事` 欄的左緣隨 Momentum 標籤浮動，所以它根本不是一欄**——那一個字都沒修。

規劃端自己造成的部分：**spec 開錯了藥。**F4 說「它是全表唯一沒有欄寬的欄」，這句話是錯的，
`Momentum` 也沒有。實作端照 spec 吃了藥，誠實回報藥沒效——這一段的責任在規劃端。

### 測試名稱承載了 body 不驗證的宣稱

`test_do3_f4_narrative_column_is_width_10_and_right_edges_align`：
名字裡的 `right_edges_align` 沒有任何斷言支持，body 的註解自己承認
「full-line vislen still varies with the Momentum label」。
另外這三行是同義反覆——在測 `_ljust`，不是在測 `render_radar`：

```python
assert _vislen(header_cell) == _vislen(date_cell) == _vislen(blank_cell) == 10
```

真正有效的是 `header.endswith(header_cell)` 那三行。
**下一輪讀到這個測試名的人會以為對齊已解決。**這比對齊本身更該修。

---

## 3. 做了但 spec 沒要求的

1. **`test_do2_pending_real_narratives_dir_as_of_latest_price_day` 是定時炸彈。**
   它對真實 `narratives/` 做**完全相等**斷言：`found == [(date(2026,9,6), "2026-09-06.yaml")]`。
   PO 週末新增一份 `2026-09-07.yaml`，測試就紅——**而那正是 DO-2 存在的理由**。
   `PENDING_LIMIT=3` 也讓第 4 份未生效檔直接讓斷言失效。
   repo 已有讀真實目錄的慣例（`load_as_of(REPO_ROOT/"narratives")` 那幾條），
   但那些對「新增檔案」免疫，這一條不是。
2. 改動 008 的護欄斷言 `test_do3_f3`：`_vislen(header) == 110` → `116`。合理連帶，記一筆。
3. `docs/product/backlog.md` 本輪未更新（spec 允許碰、未要求；那是規劃端的活，本報告一併補）。

---

## 4. 三個未決問題的裁決

**Q1 `entry is None` 印什麼 — 同意實作端不套 `n/a`，但別忘。**
他先量了才問，這是對的做法。日常 `refresh`／`brief`／`radar` 踩不到
（檔在、`method_version=1` 相符、k=20 齊，且 `refresh` 不跑 `validate-signal`）；
踩得到的是新 clone／刪 `data/processed/`／bump `NULL_METHOD_VERSION` 三條。
留下的代價：那條路現在印的是**單日值且沒有旁邊的虛無**——正是 B6 剛修掉的誤導的無旁證版本。
排 010，見拍板 4。

**Q2 `尚未生效` 的位置 — 照預設，通過。**
唯一觀察：實際輸出是 `分類外代號` → `尚未生效` → 兩行 disclosure → `故事進度`，
視覺上被 disclosure 切開。可留可改，不是缺陷。

**Q3 F5 修法 — 照預設，通過。**他在改動前先量了 008 的矛盾（`declared` vs `set()`），
物證貼在 evidence。等價性見第 1 節。

---

## 5. spec 自己的洞：`PENDING_LIMIT = 3` 的靜默

spec 寫「最多 3 行」，實作照做，沒有溢出提示。第 4 份未生效快照會再次隱形——
**正是 DO-2 的立案理由「PIT 沒有錯，錯在沉默」**。
這是規劃端的洞不是實作端的洞。010 補一行「還有 N 份」。
（repo 既有慣例 `最近事件` 也是靜默截斷 3 筆，同一個病，一起修。）

---

## 6. 規則質疑 — 009 那條「逐字元相同」的收窄

```text
條文：新功能關掉之後，產物與基準逐字元相同 —— 但必須指名
      「哪一份產物、對哪一個 commit、在哪一個開關狀態」，禁止寫成「全部輸出」
起因：008 一輪內造成三次互斥（008-report 第七節第 4 點），009 spec 收窄
物證：009 DO-2 驗收 2／3 照新格式寫（指名 load_as_of / coverage_report /
      theme_mention_dates / theme_last_mention_dates / story_last_changed 五個函式，
      指名「無檔時與 dev 逐字元相同」的開關狀態）。本輪**沒有再出現互斥**。
      DO-1 驗收 4／5 同樣指名到格與函式。
詮釋：收窄有效。它擋住的不是規則本身，是「全部輸出」這個句型。
決定：保留為預設值，維持收窄後的寫法　　重看：011 驗收後
```

**但本輪長出同一個病的新形狀。**DO-3.1 的「四者右緣對齊」是一個**目視驗收條件**。
skill 階段 4 早就寫過「留意測不到的驗收條件……要標明它由目視驗證並回報樣子，
不能拿綠色的測試當證據」——結果 spec 沒標，實作端就用**測試名字**補足了那個宣稱。

**建議新增預設值（010 起適用）：**

```text
條文：驗收條件若含「對齊／看得出來／一眼／好懂」等目視詞，
      spec 必須明寫「目視驗證，貼原文，不得以測試通過為證據」；
      且測試名稱不得承載該宣稱。
起因：009 DO-3.1
物證：test_do3_f4_narrative_column_is_width_10_and_right_edges_align
      ——名字宣稱對齊，body 註解自承不對齊，三行斷言在測 _ljust
重看：010 驗收後
```

---

## 7. 收尾狀態

- 007／008 分支已刪，`dev` 已推到 `origin/dev@d428807`。核對過：`git branch -a` 只剩
  `dev`、`sprint/009-match-yardstick`、`remotes/origin/dev`。
- `docs/post/`、`.claude/_to_delete/` 仍是 untracked，未動。
- 009 spec 狀態仍為「待實作」、`docs/sprints/README.md` 索引仍為「待實作」——
  **merge 之後才改**，見拍板 5。
- 本輪未發布 artifact：拍板五項全部放進聊天回覆，一頁預算由該則回覆吸收。
