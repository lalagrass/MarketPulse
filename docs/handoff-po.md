# 給 PO — Brief 四態

狀態：**已實作**。只改 `marketpulse/product.py` 與測試；RS20、rank、Timeline 未動。
as-of **2026-08-31**，下面是 `uv run marketpulse brief` 真實輸出。

## 已鎖定規則

- 領先：rank ≤ 3 且 Δ5 ≥ 0
- 改善：rank ≥ 4 且 Δ5 ≥ +2
- 轉弱：rank ≤ 3 且 Δ5 ≤ −2
- 其餘：落後
- NaN rank 或 NaN Δ5 → 落後
- 改善列置頂，其後 領先 → 轉弱 → 落後；空塊不印
- 分類只用 Rank 與 Δ5
- value_thrust、breadth 只當附註
- rank #2 但 Δ5 = −1 → 落後

## 真實 Brief

```text
MarketPulse — 2026-08-31

Theme Rotation  領先 / 改善 / 轉弱 / 落後
分類只用 Rank 與 Δ5。value_thrust、breadth 為附註。

改善
 被動元件             #6   Δ5   +3  RS20  +14.5%
                      thrust  +11.0%  breadth   57.1%
 先進製程             #8   Δ5   +2  RS20   +5.6%
                      thrust   +0.3%  breadth   66.7%

領先
 光通訊/CPO           #1   Δ5   +1  RS20  +42.8%
                      thrust   -4.3%  breadth  100.0%
 散熱/液冷            #3   Δ5   +0  RS20  +23.5%
                      thrust   +2.1%  breadth   80.0%

落後
 高速材料/CCL         #2   Δ5   -1  RS20  +39.2%
                      thrust   -4.6%  breadth   50.0%
 PCB                  #4   Δ5   +1  RS20  +20.2%
                      thrust   -7.9%  breadth   83.3%
 記憶體               #5   Δ5   -1  RS20  +19.6%
                      thrust  +50.7%  breadth   85.7%
 AI伺服器             #7   Δ5   -1  RS20   +7.9%
                      thrust  -28.6%  breadth   80.0%
 重電                 #9   Δ5   -2  RS20   +3.6%
                      thrust  -35.9%  breadth   85.7%
 AI電力/電源          #10  Δ5   -2  RS20   -0.1%
                      thrust  -45.9%  breadth   60.0%
 半導體測試/測試介面  #11  Δ5   +0  RS20   -2.8%
                      thrust   +3.1%  breadth   60.0%

歷史回放使用現行族群定義，用來把過去的輪動畫清楚，不代表當時已知這份名單。
Rank is relative leadership over time; it does not prove capital flowed from A to B.
```

當日無「轉弱」。高速材料/CCL 是 rank #2 但 Δ5 = −1，因此在落後。

## 下一刀（未做，需另批）

1. Brief 頂欄加 TAIEX 20 日（股癌流程的「先看大盤」）
2. 領先／改善主題內列相對強個股（抓裡面最強的）
3. 才考慮成交值門檻、RRG、歷史 taxonomy
