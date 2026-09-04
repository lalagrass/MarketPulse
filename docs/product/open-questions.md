# 待決清單

Sprint 000 文件整地時發現的矛盾。**這些是決定，不是事實**——整地只負責記錄，
由 sprint 001 的 bootstrap 交給 PO 逐條處理。

在解決之前，遇到相關情境時以現行契約文字為準，並在報告中標記。

---

## ~~Q1~~ — §11 的 RRG 條款自相矛盾　**已解決 2026-09-04：確立 D3，撤回 §11 附帶條件**

`docs/coding-contract.md` §11 把 RRG 列入 "Do not implement yet"，但同段附帶條件：

> RRG may be added only after the Rank Timeline works, and should reuse an
> established implementation.

Rank Timeline 已可運作（`reports/rotation_latest.png` 每日產生），因此依契約字面
RRG 已解鎖。需要決定：正式解禁，或改寫為無條件的 non-goal 並補上理由。

參考：開源實作 RRG-Lite（GPL-3.0，CLI，吃 CSV OHLC，計算 RS-Ratio / RS-Momentum）。

## ~~Q2~~ — §3 要求 pandas-ta-classic，但專案並未使用　**已解決 2026-09-04：修訂 §3，保留現有薄包裝**

`docs/coding-contract.md` §3 明文 "Do not write your own: SMA / generic ROC /
generic momentum"，並指定使用 pandas-ta-classic。實際情況：

- `pyproject.toml` 的 dependencies 沒有 pandas-ta-classic
- 程式碼中無任何 import
- `marketpulse/calc.py:93` 自行定義 `sma()`，`calc.py:88` 自行定義 `n_day_return()`

兩者都是五行的 pandas 包裝，可能是正確取捨。需要決定：補上相依套件，或修改 §3
說明標準指標直接用 pandas，pandas-ta-classic 保留給 SMA / ROC 以外的需求。

## ~~Q3~~ — §8 禁止還原股價進入訊號路徑　**已決定 2026-09-04：只量測幅度（§8 允許 report），不改價格方法。§8 維持不變**

`docs/coding-contract.md` §8：

> Do not introduce adjusted-price data into the MVP signal path.
> If corporate actions cause visible anomalies, report them; do not silently
> change the price methodology.

台股除權息集中於七、八月，而現有資料窗口（2026-07-20 → 2026-08-31）正落在其中。
以未還原收盤價計算的 20 日報酬，會把除息當日的價格缺口計為真實下跌，可能造成
高殖利率成分股偏多的族群被系統性壓低。

**幅度尚未驗證。** §8 允許「report them」，因此量測偏移幅度不違反契約；
改變價格方法則需要先修改 §8。已知外部資料源：FinMind `TaiwanStockPriceAdj`
（還原股價）、`TaiwanStockDividendResult`（除權息結果）。

需要決定：是否量測幅度；若確認顯著，是否鬆綁 §8。註：引入 FinMind 也等於
讓目前完全本機、無外部相依的資料層接受一個外部 API 與其免費額度。

## ~~Q4~~ — §11 的 backtesting 禁令範圍　**已解決 2026-09-04：完整損益回測寫入 non-goals D2，§11 維持不變**

`docs/coding-contract.md` §11 將 "backtesting frameworks" 列為 not yet。
2026-09-04 討論中曾考慮解禁「前瞻報酬分布」（依 rank 分組，觀察未來 20 日相對
大盤報酬），PO 當下決定**不做**，理由是第一層先做好即可，前瞻留給使用者判讀。

因此 §11 現況維持不變，無需修改。此項僅記錄該決定，避免未來重複討論。
需要確認的是：是否把「完整損益回測」正式寫入 non-goals 並附理由
（避免調參 overfit），使其從「暫緩」變成「明確不做」。

---

## Q5 — 脈絡族群的成分股會演變，歷史該怎麼算？

**提出：**2026-09-04。**待拍板時機：**sprint 002 或 003，脈絡族群真的進入第一層之前。

脈絡經常一開始模糊、之後才清晰——10/15 才發現某檔屬於這條供應鏈。需求是真的：
不更新成分股，脈絡族群就永遠是錯的。

**但「更新成分股後重算全部歷史」是前視偏誤，而且是最誘人的那種。**
你會發現某檔屬於這條鏈，通常是因為它漲了、被討論了。用「後來的表現」選成分股、
再回頭量測這組成分股的表現，重算後的歷史會顯示這個脈絡從一開始就很強——
其中一部分是選出來的，不是走出來的。這比現有 replay 的限制更嚴重：
replay 是一次凍結且已揭露，動態重算則是每次更新都注入一次後見之明，而且越來越好看。

**建議解法：歷史不重算，用帶日期快照接起來。**（DO-3 的結構已經支援，不需新設計）

- **as-of 讀法（預設）**：T 日的強度用 `snapshot_date ≤ T` 之中最新那份的成分股。
  10/15 加的成員只影響 10/15 之後。歷史逐段拼接，每段都用「當時知道的」。
  誠實，但曲線會有接縫。
- **restated 讀法（例外，必須標註）**：用當前成分股跑完整段歷史。它回答
  「如果一開始就這樣定義會長怎樣」，**不是**「當時的表現」。

兩種讀法回答不同問題，**不得不標註地畫在同一張圖上**。
（等同財報資料的 point-in-time vs restated，量化界的既有處理方式。）

**附帶價值：**成分股何時被加入本身就是資料。「後來證明為真的脈絡，其成分股是否
持續擴張？」只有保留版本歷史才答得出來——快照設計自動具備。

**待決：**as-of 是否確立為預設？restated 的標註方式為何？

## Q6 — 脈絡族群與預設族群要不要放在同一個排名池？

**提出：**2026-09-04。**待拍板時機：**同 Q5，且必須早於實作。

目前 `calc.py:compute_snapshots()` 對 `themes/v1.yaml` 的所有主題做單一橫斷面排名
（`ranked.groupby("date").cumcount() + 1`）。若脈絡族群併入同一個池子：

1. **與自身近似複本競爭。**`cpo_chain` 脈絡族群與既有 `optical_cpo` 主題會大量重疊成分股。
2. **更嚴重：既有主題的名次會因為新增脈絡而改變。**11 個主題變 14 個之後，
   第一層的歷史在時間上不再可比。這比前視偏誤更麻煩，因為它靜默地污染整個第一層——
   而第一層的可比性是這個工具的根基。

**建議：兩個獨立的排名池。**預設族群自己排（穩定骨幹，跨時間可比），
脈絡族群自己排。UI 可並列呈現，排名不混。

**待決：**確立雙池？或有第三種做法（例如脈絡只算 RS20 不進排名）？

**後續研究方向：**這兩題都值得再搜一輪別人怎麼做——指數編製商處理成分股變更的
慣例、point-in-time 資料庫的設計模式、以及有無開源專案處理過「動態定義的族群」
的可比性問題。
