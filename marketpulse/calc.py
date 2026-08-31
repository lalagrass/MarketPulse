"""Theme aggregation, RS20, rank, value share, breadth.

Generic SMA / N-day return use pandas rolling and shift.
RS20 = theme_return_20 - TAIEX_return_20 is the only MarketPulse-owned formula.
There is no composite score. Rank is cross-sectional rank of RS20.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from marketpulse.themes import ThemeSet

RETURN_N = 20
SMA_N = 20
THIN_MIN = 4
RANK_N5 = 5
RANK_N20 = 20

SNAPSHOT_COLUMNS = [
    "date",
    "theme_id",
    "theme_name",
    "return_20",
    "rs20",
    "rank",
    "rank_delta_5",
    "rank_delta_20",
    "value_share",
    "breadth",
    "value_thrust",
    "member_count",
    "missing_count",
    "status",
]


def _as_dates(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series).dt.date


def _pivot(bars: pd.DataFrame, column: str) -> pd.DataFrame:
    frame = bars.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame["symbol"] = frame["symbol"].astype(str)
    return (
        frame.pivot_table(
            index="date",
            columns="symbol",
            values=column,
            aggfunc="first",
        )
        .sort_index()
    )


def n_day_return(prices: pd.DataFrame | pd.Series, n: int = RETURN_N) -> pd.DataFrame | pd.Series:
    """close[T] / close[T-n] - 1 over the trading-day index."""
    return prices / prices.shift(n) - 1


def sma(series: pd.DataFrame | pd.Series, n: int = SMA_N) -> pd.DataFrame | pd.Series:
    """Standard simple moving average via pandas rolling mean."""
    return series.rolling(window=n, min_periods=n).mean()


def complete_sessions(bars: pd.DataFrame, index: pd.DataFrame) -> list[date]:
    if bars.empty or index.empty:
        return []
    bars = bars.copy()
    bars["date"] = _as_dates(bars["date"])
    index = index.copy()
    index["date"] = _as_dates(index["date"])
    twse = set(bars.loc[bars["market"] == "TWSE", "date"])
    tpex = set(bars.loc[bars["market"] == "TPEx", "date"])
    taiex = set(index["date"])
    return sorted(twse & tpex & taiex)


def asof(bars: pd.DataFrame, as_of: date) -> pd.DataFrame:
    frame = bars.copy()
    frame["date"] = _as_dates(frame["date"])
    return frame.loc[frame["date"] <= as_of].copy()


def asof_index(index: pd.DataFrame, as_of: date) -> pd.DataFrame:
    frame = index.copy()
    frame["date"] = _as_dates(frame["date"])
    return frame.loc[frame["date"] <= as_of].copy()


def compute_snapshots(
    bars: pd.DataFrame,
    index: pd.DataFrame,
    themes: ThemeSet,
    *,
    start: date | None = None,
    end: date | None = None,
    thin_min: int = THIN_MIN,
) -> pd.DataFrame:
    """Equal-weight theme return, RS20 rank, overlapping value share, SMA breadth.

    Uses only bars/index rows with date <= each session T.
    Frozen YAML members apply to every T (visualization replay).
    """
    if bars.empty or index.empty:
        return pd.DataFrame(columns=SNAPSHOT_COLUMNS)

    work = bars.copy()
    work["date"] = _as_dates(work["date"])
    work["symbol"] = work["symbol"].astype(str)
    idx = index.copy()
    idx["date"] = _as_dates(idx["date"])

    sessions = complete_sessions(work, idx)
    if end is not None:
        sessions = [d for d in sessions if d <= end]
    if not sessions:
        return pd.DataFrame(columns=SNAPSHOT_COLUMNS)

    # Rank Δ / value_thrust need sessions before `start`. Slice after ranking.
    history_bars = work[work["date"] <= max(sessions)]
    history_idx = idx[idx["date"] <= max(sessions)]

    close = _pivot(history_bars, "close")
    tv = _pivot(history_bars, "trading_value")
    ret_n = n_day_return(close, RETURN_N)
    ma = sma(close, SMA_N)
    above = close > ma

    taiex_frame = history_idx.drop_duplicates("date").copy()
    taiex = taiex_frame.set_index(pd.to_datetime(taiex_frame["date"]))["close"].sort_index()
    taiex_ret = n_day_return(taiex, RETURN_N)

    market_tv = tv.sum(axis=1, min_count=1)
    session_ts = pd.to_datetime(sessions)

    rows: list[dict] = []
    for theme in themes.themes:
        members = [m for m in theme.members]
        present_cols = [m for m in members if m in close.columns]
        ret_cols = [m for m in present_cols if m in ret_n.columns]
        tv_cols = [m for m in present_cols if m in tv.columns]
        above_cols = [m for m in present_cols if m in above.columns]

        theme_ret = (
            ret_n[ret_cols].mean(axis=1, skipna=True)
            if ret_cols
            else pd.Series(np.nan, index=close.index)
        )
        theme_tv = (
            tv[tv_cols].sum(axis=1, min_count=1)
            if tv_cols
            else pd.Series(np.nan, index=close.index)
        )
        share = theme_tv / market_tv
        breadth = (
            above[above_cols].mean(axis=1, skipna=True)
            if above_cols
            else pd.Series(np.nan, index=close.index)
        )
        member_count = close[present_cols].notna().sum(axis=1) if present_cols else 0
        if isinstance(member_count, int):
            member_count = pd.Series(0, index=close.index)

        aligned = pd.DataFrame(
            {
                "return_20": theme_ret,
                "taiex_ret": taiex_ret.reindex(theme_ret.index),
                "value_share": share,
                "breadth": breadth,
                "member_count": member_count,
            }
        )
        aligned["rs20"] = aligned["return_20"] - aligned["taiex_ret"]
        aligned = aligned.reindex(session_ts)

        missing_count = []
        for ts in aligned.index:
            have = set()
            if ts in close.index:
                have = {
                    m
                    for m in members
                    if m in close.columns and pd.notna(close.at[ts, m])
                }
            missing_count.append(len(members) - len(have))
        aligned["missing_count"] = missing_count

        status = []
        for _, rec in aligned.iterrows():
            if pd.isna(rec["rs20"]):
                status.append("INSUFFICIENT_HISTORY")
            elif rec["missing_count"] > 0:
                status.append("MISSING_DATA")
            elif rec["member_count"] < thin_min:
                status.append("THIN")
            else:
                status.append("OK")
        aligned["status"] = status
        aligned["theme_id"] = theme.theme_id
        aligned["theme_name"] = theme.name
        aligned["date"] = [ts.date() for ts in aligned.index]
        rows.append(aligned.reset_index(drop=True))

    out = pd.concat(rows, ignore_index=True)
    out["value_thrust"] = (
        out.groupby("theme_id")["value_share"].transform(lambda s: s / s.rolling(SMA_N, min_periods=SMA_N).mean() - 1)
    )

    ranked = out.loc[out["rs20"].notna(), ["date", "theme_id", "rs20"]].copy()
    ranked = ranked.sort_values(["date", "rs20", "theme_id"], ascending=[True, False, True])
    ranked["rank"] = ranked.groupby("date").cumcount() + 1
    out = out.merge(ranked[["date", "theme_id", "rank"]], on=["date", "theme_id"], how="left")

    out = out.sort_values(["theme_id", "date"])
    out["rank_delta_5"] = out.groupby("theme_id")["rank"].shift(RANK_N5) - out["rank"]
    out["rank_delta_20"] = out.groupby("theme_id")["rank"].shift(RANK_N20) - out["rank"]
    if start is not None:
        out = out.loc[out["date"] >= start]
    out = out.sort_values(["date", "rank", "theme_id"], na_position="last").reset_index(drop=True)
    return out[SNAPSHOT_COLUMNS]


def replay_snapshots(
    bars: pd.DataFrame,
    index: pd.DataFrame,
    themes: ThemeSet,
    start: date,
    end: date,
    *,
    thin_min: int = THIN_MIN,
) -> pd.DataFrame:
    """Day-by-day as-of replay. Never reads bars after T when computing T."""
    sessions = [d for d in complete_sessions(bars, index) if start <= d <= end]
    pieces: list[pd.DataFrame] = []
    for session in sessions:
        piece = compute_snapshots(
            asof(bars, session),
            asof_index(index, session),
            themes,
            start=session,
            end=session,
            thin_min=thin_min,
        )
        pieces.append(piece)
    if not pieces:
        return pd.DataFrame(columns=SNAPSHOT_COLUMNS)
    return pd.concat(pieces, ignore_index=True).sort_values(
        ["date", "rank", "theme_id"], na_position="last"
    ).reset_index(drop=True)


def snapshots_equal(left: pd.DataFrame, right: pd.DataFrame) -> bool:
    cols = SNAPSHOT_COLUMNS
    a = left[cols].sort_values(["date", "theme_id"]).reset_index(drop=True)
    b = right[cols].sort_values(["date", "theme_id"]).reset_index(drop=True)
    return a.equals(b)
