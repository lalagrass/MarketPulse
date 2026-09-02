# 給 PO — 日常 refresh（ops）

狀態：**已實作**。公式、四態 Brief、Timeline 幾何都沒改。
日常指令改成 `uv run marketpulse refresh`。

## 做了什麼

- 空的官方回應不再當成功快取。9/3 這種「還太早」下次會重抓；9/1 這種已完成交易日之前的空檔當假期留下。
- `refresh`：從最後完整交易日隔天抓到今天 → validate → analyze → Brief → `reports/rotation_latest.png`。
- 預設圖：最近 40 個有 rank 的交易日。YTD 長圖要自己加 `--start`。
- 結尾印 raw last attempt / snapshot as_of / chart 路徑。

## 真實輸出（2026-09-03 跑 refresh）

9/3 官方收盤檔還沒出，有重抓，仍是 empty，as_of 停在 9/2。

```text
2026-09-03  twse=empty:很抱歉，沒有符合條件的資料!  tpex=empty
downloaded 1 weekday requests
sessions: 160  2026-01-02 → 2026-09-02
validate: ok

MarketPulse — 2026-09-02

Theme Rotation  領先 / 改善 / 轉弱 / 落後
分類只用 Rank 與 Δ5。value_thrust、breadth 為附註。

改善
 被動元件             #6   Δ5   +2  RS20   +7.5%
 先進製程             #7   Δ5   +3  RS20   +2.9%

領先
 光通訊/CPO           #1   Δ5   +1  RS20  +37.4%
 散熱/液冷            #3   Δ5   +1  RS20  +21.8%

落後
 高速材料/CCL         #2   Δ5   -1  RS20  +26.4%
 PCB                  #4   Δ5   +1  RS20  +12.7%
 記憶體               #5   Δ5   -2  RS20   +7.9%
 重電                 #8   Δ5   -1  RS20   +1.5%
 半導體測試/測試介面  #9   Δ5   +0  RS20   -0.1%
 AI電力/電源          #10  Δ5   +1  RS20   -4.1%
 AI伺服器             #11  Δ5   -5  RS20   -4.9%

reports/rotation_latest.png
effective RS20 period: 2026-07-07 → 2026-09-02
raw last attempt: 2026-09-03  twse=empty  tpex=empty  (will retry)
bars/snapshot as_of: 2026-09-02
chart: reports/rotation_latest.png  effective 2026-07-07 → 2026-09-02
```

## 沒做（依計畫）

cron、通知、doctor、個股、大盤 header、RRG、改 RS20。
