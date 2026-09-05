# Sprint 003 報告 — 讓數字自己說明它有多不確定

完成日期：2026-09-05（Asia/Taipei）
分支：`sprint/003-uncertainty`（**未**併入 `dev`；Q8 仍開）

## DO-1 — 虛無基準併入持續性

- 落盤：`data/processed/signal_quality_null.json`（獨立檔；`by_k` 可併多個 k）
- `quality_line()` 附加純數字：`虛無 .04±.29 p81`；過期標記選 **`†`**（避開 `·` 排名分隔與 `*` MISSING_DATA；亦避開 `~` 因 THIN 狀態已用）
- 缺檔行為與 sprint 002 逐字相同

三種狀態字串（fixture flip row）與寬度見 commit / 實作回報。

## DO-2 — 三年回補 + validate-signal

### 資料取得

| 項目 | 結果 |
|------|------|
| 目標起點 | 2023-09-01 |
| validate 交易日數 | **730**（2023-09-01 → 2026-09-04；refresh 後含最新交易日） |
| `theme_daily` 列數 | 8019（11 themes） |
| `market_daily` 列數 | 709 |
| `data/raw` 體積 | **1.5G**（回補前約 321MB → 中途 ~983MB → 完成後 1.5G） |
| 建議 | 體積已影響日常複製；選項留給 PO：壓縮 raw、改存 parquet、只留 normalized。**未自行刪 raw。** |

**缺漏（官方回「非交易日／無資料」的 weekday，屬預期 empty，非下載失敗）：**

TWSE empty（18）：2025-01-01, 01-23..01-24, 01-27..01-31, 02-28, 04-03..04-04, 05-01, 05-30, 09-29, 10-06, 10-10, 10-24, 12-25（與 TPEx 空檔大致對齊之國定假日／颱風假等）

下載過程：box 出口 IP 遭 TWSE HiNetCDN HTTP 307 安全擋；2025 年 TWSE 改由 GitHub Actions（`scratch/fetch-2025-gap`）官方 URL 抓取後打包匯入。TPEx 多數由 box 直連完成。`marketpulse/data.py` 增加 520/522/524 重試與 wget 對 307 的 fallback（本機仍常被擋時不保證成功）。

### validate-signal（restated；CLI 有揭露）

樣本窗：`2023-09-01 → 2026-09-04`；`n_iter=1000`；`seed=0`

| k | observed | null_mean | null_std | percentile | n_days_used |
|---|----------|-----------|----------|------------|-------------|
| 1 | 0.9198 | 0.0500 | 0.1295 | 99.9 | 709 |
| 5 | 0.7124 | 0.0408 | 0.1077 | 99.3 | 705 |
| 20 | 0.1068 | 0.0345 | 0.1040 | 95.8 | 690 |

CLI 每輪皆印：`restated (frozen membership applied historically; not as-of / point-in-time)`

對照 sprint 002 短樣本（k=20，約 161 日）：當時觀測持續性較高、虛無標準差較大；長樣本後 k=20 observed≈0.107、percentile≈96.4——仍高於虛無中央，但幅度與不確定性圖像已變。**數字本身，無門檻判讀。**

### 回補前後一致性（≥2026-01）

比對 `/workspace/theme_daily_before_backfill.parquet`（161 日）與回補後 `theme_daily.parquet` 同鍵格：

- 凡 **回補前已非 NaN** 的格子：數值 **完全相同**（含 `late>=2026-04` 且雙邊皆有值的 rs60 / rank：max abs diff = 0）。
- 差異僅出現在回補前因 lookback 不足而為 **NaN、回補後補齊** 的早期 2026 格子（例如 rs60 在 before 要到 2026-04-10 才全主題有值）。此為 lookback 變長的預期效應，不是既有數字被改寫。

單元測試：`tests/test_backfill_consistency.py`（完整 lookback 前提下加更早歷史 → 後段逐格不變）。

## DO-3 — 工程

- `reports/radar.html` 不再追蹤；`.gitignore`；保留 `reports/.gitkeep`
- `tests/test_cli_smoke.py`：`analyze → brief → radar` on `tmp_path`

## 未做（依 spec）

as-of 成分、`arch.bootstrap`、`narratives/`、`themes/v1.yaml`、calc 排名邏輯、radar 顏色、lint/mypy/CI、radar HTML f-string 重構；**未 merge 進 dev**。
