"""Branch-basket strength panel (sprint 004 DO-2).

Second layer buys information, it does not change the first (contract R3):
this reads the same price/volume and runs the same RS_k = basket_return_k −
TAIEX_return_k that calc.py runs for a theme, on a hand-picked basket instead
of a theme. It does not rank, does not score, does not write the snapshot
parquet, and does not touch themes/v1.yaml. Baskets are printed in the order
the narratives list them.

Members are read as-of (Q5 default): the basket at session T is whatever the
latest snapshot with snapshot_date ≤ T says. restated membership is not done
here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from marketpulse.calc import (
    RETURN_5,
    RETURN_60,
    RETURN_N,
    SMA_N,
    _pivot,
    asof,
    asof_index,
    n_day_return,
    sma,
)
from marketpulse.narratives import Branch

BASKET_COLUMNS = [
    "narrative_id",
    "branch_id",
    "claim",
    "member_count",
    "rs5",
    "rs20",
    "rs60",
    "breadth",
    "value_share",
]

EMPTY_BASKET_LABEL = "無標的"


@dataclass(frozen=True)
class BasketMetrics:
    narrative_id: str
    branch_id: str
    claim: str
    basket: tuple[str, ...]
    member_count: int
    rs5: float | None
    rs20: float | None
    rs60: float | None
    breadth: float | None
    value_share: float | None

    @property
    def is_empty(self) -> bool:
        return len(self.basket) == 0


def _f(value: object) -> float | None:
    if value is None:
        return None
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    return None if pd.isna(num) else num


def _basket_rs(
    ret_k: pd.DataFrame,
    taiex_ret_k: pd.Series,
    members: list[str],
    ts: pd.Timestamp,
) -> float | None:
    """Mean member k-day return at ts minus TAIEX k-day return. None if the
    window is too short (n_day_return is NaN) — never a shorter window."""
    cols = [m for m in members if m in ret_k.columns]
    if not cols or ts not in ret_k.index:
        return None
    theme_ret = ret_k.loc[ts, cols].mean(skipna=True)
    tx = taiex_ret_k.get(ts)
    theme_ret, tx = _f(theme_ret), _f(tx)
    if theme_ret is None or tx is None:
        return None
    return theme_ret - tx


def compute_basket_metrics(
    bars: pd.DataFrame,
    index: pd.DataFrame,
    branches: list[tuple[str, Branch]],
    as_of: date,
) -> list[BasketMetrics]:
    """One BasketMetrics per (narrative_id, Branch), in the order given.
    Uses only bars/index rows with date ≤ as_of."""
    work = asof(bars, as_of)
    idx = asof_index(index, as_of)
    close = _pivot(work, "close") if not work.empty else pd.DataFrame()
    tv = _pivot(work, "trading_value") if not work.empty else pd.DataFrame()

    ts: pd.Timestamp | None = None
    if not close.empty:
        eligible = close.index[close.index <= pd.Timestamp(as_of)]
        if len(eligible):
            ts = eligible.max()

    ret_5 = n_day_return(close, RETURN_5) if ts is not None else pd.DataFrame()
    ret_20 = n_day_return(close, RETURN_N) if ts is not None else pd.DataFrame()
    ret_60 = n_day_return(close, RETURN_60) if ts is not None else pd.DataFrame()
    ma = sma(close, SMA_N) if ts is not None else pd.DataFrame()
    market_tv = tv.sum(axis=1, min_count=1) if ts is not None else pd.Series(dtype=float)

    taiex_5 = taiex_20 = taiex_60 = pd.Series(dtype=float)
    if ts is not None and not idx.empty:
        tx = idx.drop_duplicates("date").copy()
        taiex = tx.set_index(pd.to_datetime(tx["date"]))["close"].sort_index()
        taiex_5 = n_day_return(taiex, RETURN_5)
        taiex_20 = n_day_return(taiex, RETURN_N)
        taiex_60 = n_day_return(taiex, RETURN_60)

    out: list[BasketMetrics] = []
    for narrative_id, branch in branches:
        members = list(branch.basket)
        if not members or ts is None:
            out.append(
                BasketMetrics(
                    narrative_id, branch.branch_id, branch.claim, tuple(members),
                    member_count=0, rs5=None, rs20=None, rs60=None,
                    breadth=None, value_share=None,
                )
            )
            continue

        present = [m for m in members if m in close.columns and pd.notna(close.loc[ts, m])]
        member_count = len(present)

        breadth: float | None = None
        above_cols = [m for m in present if m in ma.columns and pd.notna(ma.loc[ts, m])]
        if above_cols:
            hits = [1.0 if close.loc[ts, m] > ma.loc[ts, m] else 0.0 for m in above_cols]
            breadth = sum(hits) / len(hits)

        value_share: float | None = None
        tv_cols = [m for m in present if m in tv.columns]
        mtv = _f(market_tv.get(ts))
        if tv_cols and mtv:
            basket_tv = _f(tv.loc[ts, tv_cols].sum(min_count=1))
            if basket_tv is not None:
                value_share = basket_tv / mtv

        out.append(
            BasketMetrics(
                narrative_id,
                branch.branch_id,
                branch.claim,
                tuple(members),
                member_count=member_count,
                rs5=_basket_rs(ret_5, taiex_5, present, ts),
                rs20=_basket_rs(ret_20, taiex_20, present, ts),
                rs60=_basket_rs(ret_60, taiex_60, present, ts),
                breadth=breadth,
                value_share=value_share,
            )
        )
    return out


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:+.1f}%"


def _plain_pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.1f}%"


def render_basket_panel(rows: list[BasketMetrics], as_of: date) -> str:
    """Plain-text table, one line per live branch, YAML order preserved.
    No rank column, nothing sorted (contract R1 / DO-2 red lines)."""
    head = (
        f"支線籃子強弱  as-of {as_of.isoformat()}  "
        f"（成員用 snapshot_date ≤ {as_of.isoformat()} 的最新一份；並列，不排名）"
    )
    lines = [
        head,
        f"{'branch':<36}{'n':>3}  {'RS5':>8}  {'RS20':>8}  {'RS60':>8}  "
        f"{'breadth':>8}  {'val%':>7}",
    ]
    if not rows:
        lines.append("（無 status: live 的支線）")
        return "\n".join(lines) + "\n"

    for m in rows:
        label = f"{m.narrative_id}/{m.branch_id}"
        if m.is_empty:
            lines.append(f"{label:<36}{EMPTY_BASKET_LABEL}")
            continue
        lines.append(
            f"{label:<36}{m.member_count:>3}  "
            f"{_pct(m.rs5):>8}  {_pct(m.rs20):>8}  {_pct(m.rs60):>8}  "
            f"{_plain_pct(m.breadth):>8}  {_plain_pct(m.value_share):>7}"
        )
    return "\n".join(lines) + "\n"
