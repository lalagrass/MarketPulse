"""Theme aggregation, RS20, rank, value share, breadth, volume ratio.

Generic SMA / N-day return use pandas rolling and shift.
RS20 = theme_return_20 - TAIEX_return_20 is the only MarketPulse-owned formula.
There is no composite score. Rank is cross-sectional rank of RS20.
volume_ratio = theme volume / SMA20(theme volume).
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from marketpulse.themes import ThemeSet

RETURN_1 = 1
RETURN_5 = 5
RETURN_N = 20
SMA_N = 20
THIN_MIN = 4
RANK_N1 = 1
RANK_N5 = 5
RANK_N20 = 20

ROLE_LEADER = "Leader"
ROLE_FOLLOWER = "Follower"
ROLE_LAGGARD = "Laggard"

SNAPSHOT_COLUMNS = [
    "date",
    "theme_id",
    "theme_name",
    "return_1",
    "return_5",
    "return_20",
    "rs20",
    "rank",
    "rank_delta_1",
    "rank_delta_5",
    "rank_delta_20",
    "value_share",
    "breadth",
    "above_count",
    "volume_ratio",
    "value_thrust",
    "member_count",
    "missing_count",
    "status",
]

STOCK_COLUMNS = [
    "date",
    "theme_id",
    "theme_name",
    "symbol",
    "name",
    "return_1",
    "return_5",
    "return_20",
    "rs20",
    "volume_ratio",
    "role",
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
    vol = _pivot(history_bars, "volume")
    ret_1 = n_day_return(close, RETURN_1)
    ret_5 = n_day_return(close, RETURN_5)
    ret_n = n_day_return(close, RETURN_N)
    ma = sma(close, SMA_N)
    above = (close > ma).where(close.notna() & ma.notna())

    taiex_frame = history_idx.drop_duplicates("date").copy()
    taiex = taiex_frame.set_index(pd.to_datetime(taiex_frame["date"]))["close"].sort_index()
    taiex_ret = n_day_return(taiex, RETURN_N)

    market_tv = tv.sum(axis=1, min_count=1)
    session_ts = pd.to_datetime(sessions)

    rows: list[dict] = []
    for theme in themes.themes:
        members = [m for m in theme.members]
        present_cols = [m for m in members if m in close.columns]
        ret1_cols = [m for m in present_cols if m in ret_1.columns]
        ret5_cols = [m for m in present_cols if m in ret_5.columns]
        ret_cols = [m for m in present_cols if m in ret_n.columns]
        tv_cols = [m for m in present_cols if m in tv.columns]
        vol_cols = [m for m in present_cols if m in vol.columns]
        above_cols = [m for m in present_cols if m in above.columns]

        theme_ret_1 = (
            ret_1[ret1_cols].mean(axis=1, skipna=True)
            if ret1_cols
            else pd.Series(np.nan, index=close.index)
        )
        theme_ret_5 = (
            ret_5[ret5_cols].mean(axis=1, skipna=True)
            if ret5_cols
            else pd.Series(np.nan, index=close.index)
        )
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
        theme_vol = (
            vol[vol_cols].sum(axis=1, min_count=1)
            if vol_cols
            else pd.Series(np.nan, index=close.index)
        )
        share = theme_tv / market_tv
        above_count = (
            above[above_cols].sum(axis=1, skipna=True)
            if above_cols
            else pd.Series(0, index=close.index)
        )
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
                "return_1": theme_ret_1,
                "return_5": theme_ret_5,
                "return_20": theme_ret,
                "taiex_ret": taiex_ret.reindex(theme_ret.index),
                "value_share": share,
                "breadth": breadth,
                "above_count": above_count,
                "theme_tv": theme_tv,
                "theme_vol": theme_vol,
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
    out["volume_ratio"] = (
        out.groupby("theme_id")["theme_vol"].transform(lambda s: s / s.rolling(SMA_N, min_periods=SMA_N).mean())
    )

    ranked = out.loc[out["rs20"].notna(), ["date", "theme_id", "rs20"]].copy()
    ranked = ranked.sort_values(["date", "rs20", "theme_id"], ascending=[True, False, True])
    ranked["rank"] = ranked.groupby("date").cumcount() + 1
    out = out.merge(ranked[["date", "theme_id", "rank"]], on=["date", "theme_id"], how="left")

    out = out.sort_values(["theme_id", "date"])
    out["rank_delta_1"] = out.groupby("theme_id")["rank"].shift(RANK_N1) - out["rank"]
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


def assign_roles(n: int) -> list[str]:
    """Tercile labels after sorting strongest-first. n=1 → Leader."""
    if n <= 0:
        return []
    n_lead = max(1, n // 3)
    n_lag = max(1, n // 3) if n >= 2 else 0
    roles = [ROLE_FOLLOWER] * n
    for i in range(n_lead):
        roles[i] = ROLE_LEADER
    for i in range(n - n_lag, n):
        if roles[i] != ROLE_LEADER:
            roles[i] = ROLE_LAGGARD
    return roles


def _empty_stocks() -> pd.DataFrame:
    return pd.DataFrame(columns=STOCK_COLUMNS)


def compute_stock_metrics(
    bars: pd.DataFrame,
    index: pd.DataFrame,
    themes: ThemeSet,
    as_of: date,
) -> pd.DataFrame:
    """Member 1D/5D/20D, RS20 vs TAIEX, volume / SMA20(volume). PIT: data <= T."""
    work = asof(bars, as_of)
    idx = asof_index(index, as_of)
    if work.empty or idx.empty:
        return _empty_stocks()

    close = _pivot(work, "close")
    vol = _pivot(work, "volume")
    if close.empty:
        return _empty_stocks()

    names = (
        work.sort_values("date")
        .drop_duplicates("symbol", keep="last")
        .set_index("symbol")["name"]
        .astype(str)
    )
    ret_1 = n_day_return(close, RETURN_1)
    ret_5 = n_day_return(close, RETURN_5)
    ret_n = n_day_return(close, RETURN_N)
    vol_ma = sma(vol, SMA_N)

    taiex_frame = idx.drop_duplicates("date").copy()
    taiex = taiex_frame.set_index(pd.to_datetime(taiex_frame["date"]))["close"].sort_index()
    taiex_ret = n_day_return(taiex, RETURN_N)

    eligible = close.index[close.index <= pd.Timestamp(as_of)]
    if len(eligible) == 0:
        return _empty_stocks()
    ts = eligible.max()
    session = ts.date()
    taiex_rs = np.nan
    if ts in taiex_ret.index and pd.notna(taiex_ret.loc[ts]):
        taiex_rs = float(taiex_ret.loc[ts])

    def _cell(frame: pd.DataFrame, symbol: str) -> float:
        if symbol not in frame.columns or ts not in frame.index:
            return np.nan
        value = frame.at[ts, symbol]
        return float(value) if pd.notna(value) else np.nan

    rows: list[dict] = []
    for theme in themes.themes:
        scored: list[dict] = []
        unscored: list[dict] = []
        for symbol in theme.members:
            if pd.isna(_cell(close, symbol)):
                continue
            r20 = _cell(ret_n, symbol)
            rs20 = (r20 - taiex_rs) if pd.notna(r20) and pd.notna(taiex_rs) else np.nan
            vol_now = _cell(vol, symbol)
            vol_avg = _cell(vol_ma, symbol)
            volume_ratio = (
                vol_now / vol_avg
                if pd.notna(vol_now) and pd.notna(vol_avg) and vol_avg != 0
                else np.nan
            )
            rec = {
                "date": session,
                "theme_id": theme.theme_id,
                "theme_name": theme.name,
                "symbol": symbol,
                "name": str(names.loc[symbol]) if symbol in names.index else symbol,
                "return_1": _cell(ret_1, symbol),
                "return_5": _cell(ret_5, symbol),
                "return_20": r20,
                "rs20": rs20,
                "volume_ratio": volume_ratio,
            }
            if pd.notna(rs20):
                scored.append(rec)
            else:
                rec["role"] = ROLE_LAGGARD
                unscored.append(rec)
        scored.sort(key=lambda r: (-float(r["rs20"]), r["symbol"]))
        for rec, role in zip(scored, assign_roles(len(scored))):
            rec["role"] = role
        rows.extend(scored)
        unscored.sort(key=lambda r: r["symbol"])
        rows.extend(unscored)

    if not rows:
        return _empty_stocks()
    out = pd.DataFrame(rows)
    return out[STOCK_COLUMNS]
