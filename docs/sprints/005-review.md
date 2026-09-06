# Sprint 005 — 獨立複核（第二隻眼）

日期：2026-09-06　複核者：規劃端（Cowork），**與 005 的 plan／implement／self-accept 不是同一次執行**
物證來源：`git diff dev` 實際內容、`data/processed/signal_quality_null.json`、`005-evidence.md`
**不跑測試。**`140 passed` 只有 `005-evidence.md` 一個來源，本複核不重跑也不背書。

背景：005 由同一代理連寫 spec、實作、再自我驗收（`005-report.md` 有誠實註明帽子切換）。
自我驗收的結論是三項 DO 全通過。**功能面我同意**——三項都有對應 commit、測試與實際輸出。
以下全部是自我驗收沒抓到的東西，其中兩條會改變 DO-1 的讀法。

---

## R1（阻擋級）rank-ic 表沒有參照點，而這個 repo 自己量過參照點不是 0

**物證。**`format_rank_ic_table`（`marketpulse/quality.py`）每格只印 `mean±se`。
同一支 `quality.py:198` 的 `persistence_null_test` 在 `signal_quality_null.json` 留下的虛無中心是：

```text
k=1  null_mean 0.0590  null_std 0.0254
k=5  null_mean 0.0602  null_std 0.0258
k=20 null_mean 0.0637  null_std 0.0270
```

**詮釋。**同一族統計量（11 檔主題、pairwise dropna 的橫斷面秩相關再對日平均），
循環位移下的中心是 **+0.06，不是 0**。表只給 `mean±se`，讀者唯一能拿的基準就是 0。
照 0 讀：`(5,5)=+0.0338` 看起來是「弱正」，對到 +0.06 的中心它其實**低於虛無**；
`(60,60)=+0.195 se=0.0202` 看起來 ~10σ，扣掉中心只剩 ≈+0.13。

**這剛好是 004 花兩個 commit（`3d812c4`、`095f79c`）學到的那條教訓的重演**，
也違反 sprint skill 判讀題規則第 1 條：觀測值不能單獨出現，一定要附虛無或參照。

**要說清楚的界線：**+0.06 是 persistence 統計量的虛無，不是 IC 的虛無。我沒有 IC 的虛無數字，
**所以不能直接拿 0.06 去扣**——能確定的只有「對 0 讀這張表不安全」。

**建議。**006 把既有循環位移機制套到 IC 上，每格報 `observed / null_mean / σ / n_ge_observed`。
在那之前，`005-report.md` 的「對角線隨天期上升」降級為觀察，不當結論。

## R2（阻擋級）(k=20,h=20) 那格不是新物證，它就是 004 的 persistence_20

**物證。**逐位數相同：

```text
rank-ic (20,20)                     +0.1404  n=367
signal_quality_null.json by_k.20    observed 0.14037651721575425  n_days_used 367
```

**詮釋。**主 rank 是 RS20 的橫斷面排名，`_rank_persistence_series` 做的是
`corr(rank[T], rank[T-20])`；`compute_rank_ic(20,20)` 做的是 `Spearman(rs20[T], rs20[T+20])`。
秩變換之後這是同一個量、只差時間軸平移。所以 `005-report.md` 讀法 C
（「persistence 量名次自相關、IC 量與未來超額，兩者不同」）在 **k=h 的對角線上被自己的數字推翻**。

對角線 `(5,5)`、`(60,60)` 不會等於 `persistence_5/60`（那兩個用的是主 rank 而非 `rs5`／`rs60`），
所以只有 (20,20) 這一格重複——但它正是報告拿來當標題的那格。

**真正的新資訊是離對角線那六格。**順帶一個好處：(20,20) 因此是全表唯一有校準的一格（+2.84σ），
而它同時是全表最弱的幾格之一。

## R3 測試抓不到 lag 對錯，而 spec 的兔子洞第一條就是 off-by-one

**物證。**`tests/test_rank_ic.py`：
`test_monotone_...` 用 `np.tile` 造「每天橫斷面順序都一樣」→ 任何 h、甚至寫錯成 `i-h` 或 `i`，IC 都是 +1。
`test_shuffled_...` 每天獨立亂排 → 任何 lag 都 ≈0。
`test_rank_ic_as_of_truncates_forward_window` 只驗 `n_days`。

**詮釋。**驗收條件 3 照字面通過了，但這組測試對「`iloc[i + h]` 寫錯」完全不敏感。
`compute_rank_ic` 的對齊我讀過，是對的（RS 窗 (T−k, T]、前向窗 (T, T+h]，不重疊、不含未來）——
但那是我讀出來的，不是測試守住的。

**建議。**加一個每 3 天循環輪轉橫斷面的樣本：只有 h ≡ 0 (mod 3) 的格子接近 +1，其餘接近 −0.5。
這種測試在 lag 寫錯時才會紅。

## R4 se 沒扣前向窗重疊——這條是規劃端的鍋

spec 自己指定「樣本 sd/√n」，實作照做。但相鄰 T 的前向窗重疊 h−1 天，daily IC 序列自相關，
`sd/√n` 偏小。唯一能校準的還是 (20,20)：循環位移虛無的 sd 是 **0.0270**，印出的 se 是 **0.0221**，
約 1.2 倍——比 √h 的直覺小很多，但 h=60 重疊長三倍，倍數未知且必然更大。
修法跟 R1 是同一件事：用虛無取代 se，不要兩套。

## R5 表格欄距為 0（evidence 裡就看得到）

```text
+0.0338 n=397 se=0.0181+0.0840 n=382 se=0.0183+0.0712 n=342 se=0.0199
```

`format_rank_ic_table` 用 `rjust(22)`，而內容剛好 21–22 字元 → 相鄰格黏在一起。
整輪 DO-3 在講可讀性，這格漏了。欄寬給 24 或改 `" ".join` 即可。

## R6 DO-2 只補了一半的假 0

`marketpulse/calc.py`：`above_cols` 為空時仍回 `pd.Series(0, index=close.index)`，
而同一段的 `breadth`、`theme_ret_*`、`theme_tv`、`theme_vol` 全部回 `np.nan`。
→ 同一天可能出現 `breadth = NaN` 但 `above_count = 0`。
「有成員但全 NaN」的假 0 修掉了，「沒有可用成員」的假 0 原封不動，是同一類的洞。一行改成 `np.nan`。

## R7 小事（不擋驗收）

- `tests/test_rank_ic.py`：`assert "mean" not in text.lower() or True` 是恆真斷言，刪掉或寫成真的斷言。
- `test_quality_line_null_baseline_absent_matches_sprint002` 現在斷言 footnote 存在——已經不是
  「逐位元等於 sprint-002」了，測試名沒跟著改。`quality.py` docstring 有改，測試名沒有。
- `005-evidence.md` 的 `c17b1e4` 只有短 hash，其餘四顆有全長。
- 工作目錄殘留未追蹤的 `docs/post/` 與 `.claude/_to_delete/`。

---

## 複核結論

| 項 | 自我驗收 | 本複核 |
|---|---|---|
| DO-1 rank-ic | 通過 | **功能通過，讀法不通過**（R1、R2、R3、R4） |
| DO-2 above_count | 通過 | 通過，但只修一半（R6） |
| DO-3 B＋C 短註 | 通過 | 通過 |

**不建議在 R1／R2 處理掉之前把 IC 表當成「短端信、長端打折」的物證。**
目前它能支持的只有一句：離對角線六格為正、量級 0.03–0.16，**參照點未知**。
分支維持不 merge 是對的。

**規劃端自己造成的問題**（照誠實規則寫進來）：R4 的 se 是 005 spec 指定的；
R1 的「表要附虛無」是 spec 該寫而沒寫的驗收條件——004 才剛學過這條，spec 沒帶過來。
