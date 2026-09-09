"""Branch-basket strength panel (sprint 004 DO-2, three baskets from 014 DO-2).

Second layer buys information, it does not change the first (contract R3):
this reads the same price/volume and runs the same RS_k = basket_return_k −
TAIEX_return_k that calc.py runs for a theme, on a hand-picked basket instead
of a theme. It does not rank, does not score, does not write the snapshot
parquet, and does not touch themes/v1.yaml. Baskets are printed in the order
the narratives list them.

Sprint 014: a branch prints three rows, not one — `either_way` (the upstream
that gets paid whichever way the claim lands), then `if_true`, then `if_false`.
Fixed order, never sorted by strength. The three are never combined: no total,
no spread, no ratio (contract R1), and no threshold decides which of them is
"strong" (D10) — the header says in fixed words how to read them and stops
there.

Members are read as-of (Q5 default): the basket at session T is whatever the
latest snapshot with snapshot_date ≤ T says. restated membership is not done
here.

Sprint 015: a basket whose members took a price move the exchange's own limit
arithmetic cannot explain gets a mark beside the affected RS column, and the
branch block names the symbol, the date and the return_1 underneath. The mark
is a disclosure, not a correction — the price is not restored, the member is
not dropped and the RS number does not move (contract §8 / open-questions Q3).
The detection is `calc.impossible_daily_returns`, unchanged and only read.
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
    impossible_daily_returns,
    n_day_return,
    sma,
)
from marketpulse.narratives import (
    BASKET_EITHER_WAY,
    BASKET_IF_FALSE,
    BASKET_IF_TRUE,
    UNKNOWN_THEME_ID_NOTE,
    Branch,
)
from marketpulse.product import _ljust
from marketpulse.themes import ThemeSet

BASKET_COLUMNS = [
    "narrative_id",
    "branch_id",
    "kind",
    "claim",
    "member_count",
    "rs5",
    "rs20",
    "rs60",
    "breadth",
    "value_share",
]

# Display order, fixed by spec 014 DO-2: "誰贏都賺" first, because whether
# anyone upstream is still being paid is the question that survives being
# wrong about the claim itself.
BASKET_ORDER = (BASKET_EITHER_WAY, BASKET_IF_TRUE, BASKET_IF_FALSE)
BASKET_LABEL = {
    BASKET_EITHER_WAY: "誰贏都賺",
    BASKET_IF_TRUE: "成真",
    BASKET_IF_FALSE: "反面",
}

EMPTY_BASKET_LABEL = "無標的"

# Verbatim from spec 014 DO-2 appendix. A constant: it carries no number from
# the data and does not change with the session (F9). Do not regenerate it
# from the numbers, and do not grow an "if strong then…" branch beside it
# (non-goals D10).
PANEL_READING_NOTE = (
    "怎麼讀：① 先看「誰贏都賺」——這條故事還有沒有人在花錢\n"
    "        ② 再看「成真」與「反面」的相對位置——市場往哪邊走\n"
    "        n 小的時候，一籃的強弱就是那一檔的股價。強弱由你自己定，這裡不判。"
)

# A count of shared symbols, not a rate, an overlap ratio or a similarity
# (spec 014 rabbit hole). It says the two sides are not disjoint; it does not
# say how much they resemble each other.
OVERLAP_NOTE = "成真／反面共同 {n} 檔"
SHARED_UPSTREAM_NOTE = "這條上游不區辨（同一組 theme_ids 也在：{others}）"

# Sprint 015 DO-1. The mark eats one of the two spaces that already separate
# the RS columns, so a marked cell and an unmarked cell are the same width and
# an unmarked row is byte-identical to what the panel printed before (G3/G4).
PRICE_BREAK_MARK = "*"
PRICE_BREAK_HEADER = (
    "* 窗內有價格斷點：這一格的漲跌幅有一部分不是市場給的，不能照字面讀"
)
PRICE_BREAK_LINE = "{symbol}  {date}  return_1 {ret}"

BRANCH_COL_WIDTH = 36
KIND_COL_WIDTH = 10  # widest label 誰贏都賺 is 8 columns wide, plus a gap


@dataclass(frozen=True)
class PriceBreak:
    """One (symbol, date) whose close-to-close move is outside the exchange's
    limit prices, as `calc.impossible_daily_returns` already reports it. Not a
    judgement about which corporate action caused it — sprint 015 answers only
    "there is a break in this window", not "it was a 除權"."""

    symbol: str
    date: date
    return_1: float | None


@dataclass(frozen=True)
class BasketMetrics:
    narrative_id: str
    branch_id: str
    kind: str                      # one of BASKET_ORDER
    claim: str
    basket: tuple[str, ...]        # the symbols actually measured
    declared: tuple[str, ...]      # as written: theme_ids for either_way, else symbols
    unknown: tuple[str, ...]       # declared either_way ids not in themes/v1.yaml
    member_count: int
    rs5: float | None
    rs20: float | None
    rs60: float | None
    breadth: float | None
    value_share: float | None
    # Price breaks inside each RS window, judged per window (G1). Empty when
    # the RS itself is None: there is no window to be inside of.
    breaks_5: tuple[PriceBreak, ...] = ()
    breaks_20: tuple[PriceBreak, ...] = ()
    breaks_60: tuple[PriceBreak, ...] = ()

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


def window_dates(
    index: pd.DatetimeIndex,
    ts: pd.Timestamp,
    n: int,
) -> tuple[pd.Timestamp, ...]:
    """The sessions whose one-day move is inside `n_day_return(..., n)` at `ts`.

    `n_day_return` is `close / close.shift(n) - 1`, so the base is the close
    `n` rows earlier **on this same trading-day index** and every daily move
    after that base, up to and including `ts`, is inside the ratio. The window
    is read straight off that index — no trading day is counted by hand and no
    second definition of "20 days" is created here (spec 015 rabbit hole).

    Empty when the history is shorter than the window, which is exactly when
    `n_day_return` is NaN and the panel prints `n/a`.
    """
    if ts not in index:
        return ()
    pos = int(index.get_loc(ts))
    if pos < n:
        return ()
    return tuple(index[pos - n + 1 : pos + 1])


def _breaks_by_symbol(breaks: pd.DataFrame) -> dict[str, list[PriceBreak]]:
    """`impossible_daily_returns` output, indexed by symbol for lookup.

    The scan is run once over the whole frame and filtered afterwards; its
    signature is not changed to take a member list (spec 015 rabbit hole).
    """
    out: dict[str, list[PriceBreak]] = {}
    if breaks is None or breaks.empty:
        return out
    for row in breaks.itertuples(index=False):
        out.setdefault(str(row.symbol), []).append(
            PriceBreak(
                symbol=str(row.symbol),
                date=row.date,
                return_1=_f(row.return_1),
            )
        )
    return out


def _window_breaks(
    by_symbol: dict[str, list[PriceBreak]],
    members: list[str],
    window: tuple[pd.Timestamp, ...],
    rs: float | None,
) -> tuple[PriceBreak, ...]:
    """Breaks belonging to `members` that fall inside `window`, in (date,
    symbol) order. No mark where there is no number to mark: `rs is None`
    means the window was too short or the index was missing."""
    if rs is None or not window:
        return ()
    days = {ts.date() for ts in window}
    hits = [
        brk
        for member in members
        for brk in by_symbol.get(member, ())
        if brk.date in days
    ]
    return tuple(sorted(hits, key=lambda b: (b.date, b.symbol)))


def resolve_either_way(
    theme_ids: tuple[str, ...],
    themes: ThemeSet,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """`(members, unknown_ids)` for an `either_way` basket.

    Membership comes from the existing ThemeSet — there is no second copy of
    the member table here (spec 014 rabbit hole). Themes in the order written,
    members in theme order, de-duplicated across overlapping themes. An id
    that is not a theme_id is returned separately so the panel can name it
    rather than let it look like an empty basket (F4).
    """
    by_id = themes.by_id()
    members: list[str] = []
    seen: set[str] = set()
    unknown: list[str] = []
    for theme_id in theme_ids:
        theme = by_id.get(theme_id)
        if theme is None:
            unknown.append(theme_id)
            continue
        for member in theme.members:
            if member not in seen:
                seen.add(member)
                members.append(member)
    return tuple(members), tuple(unknown)


def compute_basket_metrics(
    bars: pd.DataFrame,
    index: pd.DataFrame,
    branches: list[tuple[str, Branch]],
    as_of: date,
    themes: ThemeSet,
) -> list[BasketMetrics]:
    """Three BasketMetrics per (narrative_id, Branch) — BASKET_ORDER within a
    branch, branches in the order given. Uses only bars/index rows with
    date ≤ as_of. `themes` resolves `either_way` theme_ids to members and is
    read-only."""
    work = asof(bars, as_of)
    idx = asof_index(index, as_of)
    close = _pivot(work, "close") if not work.empty else pd.DataFrame()
    tv = _pivot(work, "trading_value") if not work.empty else pd.DataFrame()

    ts: pd.Timestamp | None = None
    if not close.empty:
        eligible = close.index[close.index <= pd.Timestamp(as_of)]
        if len(eligible):
            ts = eligible.max()

    # Detection is not reinvented here (spec 015 前提 2): the same function
    # calc.py already runs, on the same as-of frame the RS numbers come from,
    # read and never fed back.
    by_symbol = _breaks_by_symbol(impossible_daily_returns(work, themes))
    win_5 = window_dates(close.index, ts, RETURN_5) if ts is not None else ()
    win_20 = window_dates(close.index, ts, RETURN_N) if ts is not None else ()
    win_60 = window_dates(close.index, ts, RETURN_60) if ts is not None else ()

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
        for kind in BASKET_ORDER:
            declared = getattr(branch, kind)
            if kind == BASKET_EITHER_WAY:
                members_t, unknown = resolve_either_way(declared, themes)
            else:
                members_t, unknown = declared, ()
            members = list(members_t)

            base = dict(
                narrative_id=narrative_id,
                branch_id=branch.branch_id,
                kind=kind,
                claim=branch.claim,
                basket=tuple(members),
                declared=tuple(declared),
                unknown=unknown,
            )

            if not members or ts is None:
                out.append(
                    BasketMetrics(
                        **base,
                        member_count=0, rs5=None, rs20=None, rs60=None,
                        breadth=None, value_share=None,
                    )
                )
                continue

            present = [
                m for m in members if m in close.columns and pd.notna(close.loc[ts, m])
            ]
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

            rs5 = _basket_rs(ret_5, taiex_5, present, ts)
            rs20 = _basket_rs(ret_20, taiex_20, present, ts)
            rs60 = _basket_rs(ret_60, taiex_60, present, ts)
            out.append(
                BasketMetrics(
                    **base,
                    member_count=member_count,
                    rs5=rs5,
                    rs20=rs20,
                    rs60=rs60,
                    breadth=breadth,
                    value_share=value_share,
                    breaks_5=_window_breaks(by_symbol, present, win_5, rs5),
                    breaks_20=_window_breaks(by_symbol, present, win_20, rs20),
                    breaks_60=_window_breaks(by_symbol, present, win_60, rs60),
                )
            )
    return out


def overlap_counts(rows: list[BasketMetrics]) -> dict[tuple[str, str], int]:
    """(narrative_id, branch_id) → how many symbols `if_true` and `if_false`
    have in common (spec 014 DO-2 F7). A count. It is not divided by anything
    and must not grow into a rate or a similarity (rabbit hole)."""
    sides: dict[tuple[str, str], dict[str, set[str]]] = {}
    for row in rows:
        if row.kind not in (BASKET_IF_TRUE, BASKET_IF_FALSE):
            continue
        sides.setdefault((row.narrative_id, row.branch_id), {})[row.kind] = set(row.declared)
    return {
        key: len(side.get(BASKET_IF_TRUE, set()) & side.get(BASKET_IF_FALSE, set()))
        for key, side in sides.items()
    }


def shared_upstream(rows: list[BasketMetrics]) -> dict[tuple[str, str], tuple[str, ...]]:
    """(narrative_id, branch_id) → the OTHER narrative_ids whose `either_way`
    is the same set of theme_ids (spec 014 DO-2 F8).

    When two stories name the same upstream, that upstream cannot tell them
    apart: it is paid either way in both. Saying so is the point — it is a
    warning about what the row can and cannot discriminate, not a score.
    """
    by_key: dict[frozenset[str], list[tuple[str, str]]] = {}
    for row in rows:
        if row.kind != BASKET_EITHER_WAY or not row.declared:
            continue
        by_key.setdefault(frozenset(row.declared), []).append(
            (row.narrative_id, row.branch_id)
        )
    out: dict[tuple[str, str], tuple[str, ...]] = {}
    for owners in by_key.values():
        narratives = {nid for nid, _ in owners}
        if len(narratives) < 2:
            continue
        for nid, bid in owners:
            out[(nid, bid)] = tuple(sorted(narratives - {nid}))
    return out


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:+.1f}%"


def _rs_cell(value: float | None, breaks: tuple[PriceBreak, ...]) -> str:
    """One RS column plus its separator, always the same width.

    The mark takes the place of the first of the two separating spaces, so a
    marked cell does not shift the columns and an unmarked cell is the exact
    bytes the panel printed before sprint 015 (G3/G4). The number itself is
    formatted by `_pct` and is not touched.
    """
    return f"{_pct(value):>8}" + (PRICE_BREAK_MARK if breaks else " ") + " "


def _break_lines(block: list[BasketMetrics]) -> list[str]:
    """The `(symbol, date, return_1)` behind every mark in one branch block,
    one per line (G2), de-duplicated across the three baskets and the three
    windows — a break is a fact about a session, not about a basket."""
    found: dict[tuple[str, date], PriceBreak] = {}
    for row in block:
        for brk in row.breaks_5 + row.breaks_20 + row.breaks_60:
            found[(brk.symbol, brk.date)] = brk
    if not found:
        return []
    pad = _ljust("", BRANCH_COL_WIDTH)
    lines = [pad + PRICE_BREAK_HEADER]
    for _, brk in sorted(found.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        lines.append(
            pad
            + "  "
            + PRICE_BREAK_LINE.format(
                symbol=brk.symbol,
                date=brk.date.isoformat(),
                ret=_pct(brk.return_1),
            )
        )
    return lines


def _plain_pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.1f}%"


def _row_notes(
    row: BasketMetrics,
    overlaps: dict[tuple[str, str], int],
    shared: dict[tuple[str, str], tuple[str, ...]],
) -> str:
    """Trailing notes for one row. Facts about the basket's composition, not
    about its strength — nothing here reads the RS columns."""
    key = (row.narrative_id, row.branch_id)
    notes: list[str] = []
    if row.kind == BASKET_EITHER_WAY:
        if row.unknown:
            notes.append(f"{UNKNOWN_THEME_ID_NOTE}: {'、'.join(row.unknown)}")
        others = shared.get(key)
        if others:
            notes.append(SHARED_UPSTREAM_NOTE.format(others="、".join(others)))
    if row.kind == BASKET_IF_FALSE and overlaps.get(key):
        notes.append(OVERLAP_NOTE.format(n=overlaps[key]))
    return ("  " + "  ".join(notes)) if notes else ""


def render_basket_panel(rows: list[BasketMetrics], as_of: date) -> str:
    """Plain-text table, three lines per live branch (either_way, if_true,
    if_false), YAML order preserved. No rank column, nothing sorted, no
    threshold anywhere (contract R1 / non-goals D10)."""
    head = (
        f"支線籃子強弱  as-of {as_of.isoformat()}  "
        f"（成員用 snapshot_date ≤ {as_of.isoformat()} 的最新一份；並列，不排名）"
    )
    lines = [
        head,
        PANEL_READING_NOTE,
        f"{_ljust('branch', BRANCH_COL_WIDTH)}{_ljust('籃子', KIND_COL_WIDTH)}"
        f"{'n':>3}  {'RS5':>8}  {'RS20':>8}  {'RS60':>8}  "
        f"{'breadth':>8}  {'val%':>7}",
    ]
    if not rows:
        lines.append("（無 status: live 的支線）")
        return "\n".join(lines) + "\n"

    overlaps = overlap_counts(rows)
    shared = shared_upstream(rows)

    seen: set[tuple[str, str]] = set()
    block: list[BasketMetrics] = []
    for m in rows:
        key = (m.narrative_id, m.branch_id)
        # The branch names itself once, on its first row; the two rows under
        # it are indented into the same block, and a blank line closes the
        # block, so the three read as one branch (spec 014 DO-2 F10). Sprint
        # 015: the price breaks behind the marks close the block from inside,
        # before that blank line.
        first = key not in seen
        if first and seen:
            lines.extend(_break_lines(block))
            block = []
            lines.append("")
        head_cell = f"{m.narrative_id}/{m.branch_id}" if first else ""
        seen.add(key)
        block.append(m)
        label = _ljust(head_cell, BRANCH_COL_WIDTH) + _ljust(
            BASKET_LABEL[m.kind], KIND_COL_WIDTH
        )
        notes = _row_notes(m, overlaps, shared)
        if m.is_empty:
            lines.append((label + EMPTY_BASKET_LABEL + notes).rstrip())
            continue
        lines.append(
            f"{label}{m.member_count:>3}  "
            f"{_rs_cell(m.rs5, m.breaks_5)}"
            f"{_rs_cell(m.rs20, m.breaks_20)}"
            f"{_rs_cell(m.rs60, m.breaks_60)}"
            f"{_plain_pct(m.breadth):>8}  {_plain_pct(m.value_share):>7}{notes}"
        )
    lines.extend(_break_lines(block))
    return "\n".join(lines) + "\n"
