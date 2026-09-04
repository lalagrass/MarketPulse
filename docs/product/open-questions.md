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
