"""Sprint 015 DO-2 — 買資訊，不是產品。

`calc.impossible_daily_returns` 留下一批「交易所自己的算術解釋不了」的收盤跳動。
它們混了至少三種東西：真的斷點、除權息基準價、`shift(1)` 跨停牌。本腳本只回答
其中一個問題，而且是最便宜的那個：

    斷點之後 20 個交易日內，這檔的收盤有沒有任何一天回到斷點前一日的收盤？

回得去 → 暫時性；回不去 → 價格水準重設（除權／減資／分割一類，未還原）。
**不判斷是哪一種公司行為**（要外部資料，不是本輪的事），不改任何價格，
不改 `themes/v1.yaml`，不寫進 `marketpulse/`。跑完可以丟。

20 這個窗取自既有的 RS20，不是新挑的參數（non-goals D10）：問的就是
「這個斷點會不會污染一個 RS20 窗」。不得為了讓分組好看而調整它。

比較的是**實際收盤**，不是報酬率累乘 —— 跨除權的累乘會把問題本身當成答案。

    uv run python scripts/price_break_recovery.py
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

from marketpulse.calc import impossible_daily_returns
from marketpulse.data import read_normalized
from marketpulse.themes import load_themes

WINDOW = 20  # = calc.RETURN_N. Not a tuned parameter; see the docstring.

RECOVERED = "回得去"
RESET = "回不去"


@dataclass(frozen=True)
class Verdict:
    symbol: str
    name: str
    date: date
    return_1: float
    prev_close: float
    break_close: float
    sessions_after: int          # trading days available after the break
    recovered_on: date | None    # first close back at the pre-break level
    group: str

    @property
    def censored(self) -> bool:
        """Fewer than WINDOW sessions of history after the break — the verdict
        stands on what exists, and can still be overturned by more data."""
        return self.group == RESET and self.sessions_after < WINDOW


def classify(
    closes: pd.Series,          # one symbol, indexed by date, sorted
    break_date: date,
) -> tuple[int, date | None]:
    """`(sessions_after, first_recovery_date)` for one break.

    Recovery is a close that reaches back to the close of the session *before*
    the break, in the direction the break moved away from it: a drop must
    close at or above it again, a jump at or below. Actual closes, compared
    directly — no cumulative returns (spec 015 rabbit hole).
    """
    pos = closes.index.get_loc(break_date)
    if pos == 0:
        return 0, None
    prev_close = float(closes.iloc[pos - 1])
    broke_down = float(closes.iloc[pos]) < prev_close
    after = closes.iloc[pos + 1 : pos + 1 + WINDOW]
    for day, close in after.items():
        back = float(close) >= prev_close if broke_down else float(close) <= prev_close
        if back:
            return len(after), day
    return len(after), None


def main(data_dir: Path, themes_path: Path) -> int:
    bars, _ = read_normalized(data_dir)
    themes = load_themes(themes_path)
    hits = impossible_daily_returns(bars, themes)
    if hits.empty:
        print("no impossible daily returns in", data_dir)
        return 0

    frame = bars.copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    frame["symbol"] = frame["symbol"].astype(str)
    by_symbol = {
        symbol: group.sort_values("date").set_index("date")["close"]
        for symbol, group in frame.groupby("symbol", sort=False)
    }

    verdicts: list[Verdict] = []
    for row in hits.itertuples(index=False):
        closes = by_symbol[str(row.symbol)]
        pos = closes.index.get_loc(row.date)
        sessions_after, recovered_on = classify(closes, row.date)
        verdicts.append(
            Verdict(
                symbol=str(row.symbol),
                name=str(row.name),
                date=row.date,
                return_1=float(row.return_1),
                prev_close=float(closes.iloc[pos - 1]) if pos else float("nan"),
                break_close=float(closes.iloc[pos]),
                sessions_after=sessions_after,
                recovered_on=recovered_on,
                group=RECOVERED if recovered_on else RESET,
            )
        )

    recovered = [v for v in verdicts if v.group == RECOVERED]
    reset = [v for v in verdicts if v.group == RESET]
    censored = [v for v in reset if v.censored]

    print(f"資料 {data_dir}  最後一個 session {max(frame['date'])}")
    print(f"impossible_daily_returns 共 {len(verdicts)} 筆")
    print(f"窗 = {WINDOW} 個交易日（取自 RS20，不是新挑的參數）")
    print(f"判準：斷點後 {WINDOW} 個交易日內，收盤是否回到斷點前一日的收盤（實際收盤比較）")
    print()
    print(f"{RECOVERED}（暫時性）        {len(recovered):>4} 筆")
    print(f"{RESET}（價格水準重設）    {len(reset):>4} 筆")
    print(f"{'合計':<18} {len(verdicts):>4} 筆")
    print()
    print(
        f"其中窗未滿 {WINDOW} 天而判為「{RESET}」的：{len(censored)} 筆 —— "
        "資料尾端還沒長出 20 個 session，這幾筆是暫時判定，會被之後的資料推翻"
    )
    print()

    for title, group in ((RESET, reset), (RECOVERED, recovered)):
        print(f"── {title}  {len(group)} 筆 " + "─" * 40)
        print(
            f"{'symbol':<8}{'name':<10}{'date':<12}{'return_1':>10}"
            f"{'prev_close':>12}{'close':>10}{'after':>7}  回到"
        )
        for v in sorted(group, key=lambda x: (x.date, x.symbol)):
            back = v.recovered_on.isoformat() if v.recovered_on else "—"
            flag = "  (窗未滿)" if v.censored else ""
            print(
                f"{v.symbol:<8}{v.name:<10}{v.date.isoformat():<12}"
                f"{v.return_1 * 100:>9.1f}%{v.prev_close:>12.2f}{v.break_close:>10.2f}"
                f"{v.sessions_after:>7}  {back}{flag}"
            )
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main(Path("data"), Path("themes/v1.yaml")))
