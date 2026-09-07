"""Sector Rotation Radar: ranking table + sector drill-down. Rank is still RS20."""

from __future__ import annotations

import html
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:  # avoid a runtime import cycle (cli imports radar)
    from marketpulse.cli import OpsStatus

from marketpulse import RANK_DISCLOSURE, REPLAY_DISCLOSURE
from marketpulse.calc import (
    DAILY_LIMIT,
    LIMIT_WINDOW,
    ROLE_FOLLOWER,
    ROLE_LAGGARD,
    ROLE_LEADER,
    impossible_returns_in_window,
)
from marketpulse.momentum import (
    DIR_DOWN,
    DIR_MARK,
    MOM_MARK,
    MOM_UNKNOWN,
    MomentumEvidence,
    momentum_evidence,
)
from marketpulse.narratives import (
    NARRATIVE_COL_HEADER,
    NARRATIVE_COL_WIDTH,
    NARRATIVE_MISSING,
    NarrativeOverlay,
    theme_mention_dates,
)
from marketpulse.product import (
    NAME_WIDTH,
    RANK_TRIPLET_HEADER,
    RANK_TRIPLET_SEP,
    _fmt_rank_num,
    _fmt_signed_pct,
    _fmt_signed_pct_col,
    _ljust,
    _vislen,
    fmt_rank_triplet,
    status_mark,
)
from marketpulse.quality import quality_line

ROT_RISING = "Rising"
ROT_FALLING = "Falling"
ROT_STABLE = "Stable"
RADAR_HTML_NAME = "radar.html"

RADAR_NOTE = (
    "Rank = RS20 排序（族群 20 日報酬 − 大盤）。不是綜合分數。"
    " Breadth = 收盤價 > SMA20 的檔數。Volume = 成交量 / 20 日均量。"
)
RADAR_MOM_NOTE = (
    "Rotation = 相對前一交易日的名次。"
    " Momentum = 5D / Breadth / Volume / Rank Δ5 的方向，不是分數。"
)
# spec 011 DO-3 C1: the four votes and the label rule, on screen. Constants
# are printed as the rule's facts, not knobs (D10: do not change them).
RADAR_MOM_RULE = (
    "Momentum 標籤由四票計出（5D / Breadth / Volume / Rank Δ5），不是名次變化本身。"
    " 同樣 Δ5 +3 可以是 Strong 或 Weakening，另外三票不同。"
    " 5D ↓ 在 5D 報酬仍為正時代表「比五日前的 5D 少了 ≥2pp」，不是正負號。"
    " 計票：20D>0 且 ↓≥2 → Weakening；"
    " rank≤3 且 20D>0 且 ↓=0 且 5D↑ → Strong；"
    " rank≤3 且 20D>0 且 ↑>↓ 且 5D 非↓ → Strong；"
    " 非強位 且 ↑≥2 且 ↑>↓ 且 5D↑ → Improving；"
    " rank≥8 且 ↑<2 → Weak；"
    " 20D≤0 且 5D↓ → Weak；其餘 → Stable。"
)
FIVE_DAY_DROP_NOTE = "（比五日前回落 ≥2pp）"

# spec 012 DO-1. `Momentum` was the only ASCII column without a width, so the
# 敘事 column that follows it moved from row to row and the header rule was
# shorter than the data rows (011-report §4). The widest cell is the longest
# state label plus four votes, each vote possibly "n/a" instead of an arrow.
# Derived from the labels themselves so it cannot go stale; the cell CONTENT
# is unchanged (011 DO-3 四票原樣保留), only its padding is new.
MOM_COL_WIDTH = max(
    _vislen(f"{state} 5D{mark} Br{mark} Vol{mark} Δ5{mark}")
    for state in MOM_MARK
    if state != MOM_UNKNOWN
    for mark in DIR_MARK.values()
)


def format_limit_window_line(count: int, n: int = LIMIT_WINDOW) -> str:
    """A4: trailing-n session count of closes outside the exchange limit price.
    Always printed when the caller handed us a scan result — including 0."""
    return (
        f"不可能的單日報酬：近 {n} 個交易日 {count} 筆"
        f"（超出交易所漲跌停價；±{DAILY_LIMIT:.0%} 依檔位捨去／進位）"
    )

ROLE_ORDER = (ROLE_LEADER, ROLE_FOLLOWER, ROLE_LAGGARD)


def rotation_state(rank: object, rank_delta_1: object) -> str:
    """Display-only vs previous session. Positive Δ = moved up."""
    if rank is None or pd.isna(rank) or rank_delta_1 is None or pd.isna(rank_delta_1):
        return ROT_STABLE
    delta = int(rank_delta_1)
    if delta > 0:
        return ROT_RISING
    if delta < 0:
        return ROT_FALLING
    return ROT_STABLE


def rotation_mark(rank_delta_1: object) -> str:
    if rank_delta_1 is None or pd.isna(rank_delta_1):
        return "→"
    delta = int(rank_delta_1)
    if delta >= 2:
        return "↑↑"
    if delta == 1:
        return "↑"
    if delta <= -2:
        return "↓↓"
    if delta == -1:
        return "↓"
    return "→"


def _fmt_rank(value: object) -> str:
    if value is None or pd.isna(value):
        return "#n/a"
    return f"#{int(value)}"


def _fmt_x(value: object) -> str:
    if value is None or pd.isna(value):
        return "  n/a"
    return f"{float(value):4.1f}x"


def _fmt_breadth(above: object, members: object) -> str:
    if members is None or pd.isna(members) or int(members) <= 0:
        return "  n/a"
    num = 0 if above is None or pd.isna(above) else int(above)
    return f"{num}/{int(members)}"


def _fmt_prev_rank(rank: object, delta: object) -> str:
    if rank is None or pd.isna(rank):
        return "n/a"
    current = int(rank)
    if delta is None or pd.isna(delta):
        return f"#{current}"
    prev = current + int(delta)
    return f"#{prev} → #{current}"


def _fmt_delta5(value: object) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    return f"Δ5 {int(value):+d}"


def _fmt_mom_ascii(evidence: MomentumEvidence) -> str:
    """Label plus the four votes. Reconstructable from this cell + RADAR_MOM_RULE."""
    if evidence.state == MOM_UNKNOWN:
        return "n/a"
    return (
        f"{evidence.state} "
        f"5D{_dir_arrow(evidence.five)}"
        f" Br{_dir_arrow(evidence.breadth)}"
        f" Vol{_dir_arrow(evidence.volume)}"
        f" Δ5{_dir_arrow(evidence.rank)}"
    )


def _five_day_drop_note(rec, evidence: MomentumEvidence) -> str:
    """When 5D is ↓ but the 5D return is still positive, say why."""
    ret5 = getattr(rec, "return_5", None)
    if evidence.five != DIR_DOWN:
        return ""
    if ret5 is None or pd.isna(ret5) or float(ret5) <= 0:
        return ""
    return f"  {FIVE_DAY_DROP_NOTE}"


def _dir_arrow(direction: str) -> str:
    return DIR_MARK.get(direction, "n/a")


def radar_day(snapshot: pd.DataFrame, as_of: date) -> pd.DataFrame:
    day = snapshot.loc[snapshot["date"] == as_of].copy()
    if day.empty:
        return day
    if "rank_delta_1" not in day.columns:
        day["rank_delta_1"] = pd.NA
    if "above_count" not in day.columns:
        day["above_count"] = pd.NA
    day["rotation"] = [
        rotation_state(rank, delta) for rank, delta in zip(day["rank"], day["rank_delta_1"])
    ]
    return day.sort_values(["rank", "theme_id"], na_position="last")


def _narrative_date_label(
    theme_id: object,
    overlay: NarrativeOverlay | None,
) -> str:
    """DO-3 B2: the date a theme was LAST mentioned, scanning every snapshot
    (overlay.mention_dates, filled by _load_overlay). Falls back to the
    single-PIT-snapshot theme_mention_dates() when mention_dates is absent
    (e.g. a hand-built overlay in a test) — same as the pre-008 behaviour."""
    if overlay is None:
        return NARRATIVE_MISSING
    if overlay.mention_dates is not None:
        mentioned = overlay.mention_dates.get(str(theme_id))
    else:
        mentioned = theme_mention_dates(overlay.snapshot, overlay.themes).get(str(theme_id))
    if mentioned is None:
        return NARRATIVE_MISSING
    return mentioned.isoformat()


def render_radar(
    snapshot: pd.DataFrame,
    as_of: date,
    market_row: pd.Series | None = None,
    null_baseline: dict | None = None,
    *,
    show_narratives: bool = True,
    overlay: NarrativeOverlay | None = None,
    limit_breaks: pd.DataFrame | None = None,
) -> str:
    day = radar_day(snapshot, as_of)
    if day.empty:
        return f"MarketPulse — {as_of.isoformat()}\n\nNo snapshot for this date.\n"
    # spec 012 DO-1: one leading space for the status-mark column the data
    # rows carry (STATUS_MARK["OK"] is itself a space), so header and rows are
    # the same width and the rule below can be measured from either.
    header = (
        f" {_ljust('Sector', NAME_WIDTH)} "
        f"{'1D':>7}  {'5D':>7}  {'20D':>7}  {'RS20':>7}  "
        f"{'Breadth':>7}  {'Volume':>6}  {RANK_TRIPLET_HEADER:<15}  Rot  "
        f"{_ljust('Momentum', MOM_COL_WIDTH)}"
    )
    if show_narratives:
        header = f"{header}  {_ljust(NARRATIVE_COL_HEADER, NARRATIVE_COL_WIDTH)}"
    lines = [
        f"MarketPulse — {as_of.isoformat()}",
        quality_line(market_row, null_baseline=null_baseline, snapshot_as_of=as_of),
    ]
    if limit_breaks is not None:
        window = impossible_returns_in_window(
            limit_breaks, snapshot["date"], as_of, LIMIT_WINDOW
        )
        lines.append(format_limit_window_line(len(window), LIMIT_WINDOW))
    lines.extend(
        [
        "",
        "Sector Rotation",
        RADAR_NOTE,
        RADAR_MOM_NOTE,
        RADAR_MOM_RULE,
        "Rotation: ↑ Rising  ↓ Falling  → Stable  (vs previous session)",
        "Momentum: Strong  Improving  Stable  Weakening  Weak  (5D / Breadth / Volume / Rank Δ5)",
        "",
        header,
        # DO-3 F3 (008): measure the rule, do not hand-type it. spec 012 DO-1:
        # measure it in BOTH modes — the narratives-off case was a hand-typed
        # 100 that is now shorter than the rows it underlines.
        "-" * _vislen(header),
        ]
    )
    for rec in day.itertuples(index=False):
        mark = status_mark(rec.status)
        ret1 = rec.return_1 if hasattr(rec, "return_1") else None
        ret5 = rec.return_5 if hasattr(rec, "return_5") else None
        above = rec.above_count if hasattr(rec, "above_count") else None
        vol = rec.volume_ratio if hasattr(rec, "volume_ratio") else None
        delta = rec.rank_delta_1 if hasattr(rec, "rank_delta_1") else None
        mom = momentum_evidence(snapshot, rec)
        rank_triplet = fmt_rank_triplet(
            getattr(rec, "rank_rs5", None), rec.rank, getattr(rec, "rank_rs60", None)
        )
        row = (
            f"{mark}{_ljust(str(rec.theme_name), NAME_WIDTH)} "
            f"{_fmt_signed_pct_col(ret1)}  "
            f"{_fmt_signed_pct_col(ret5)}  "
            f"{_fmt_signed_pct_col(rec.return_20)}  "
            f"{_fmt_signed_pct_col(rec.rs20)}  "
            f"{_fmt_breadth(above, rec.member_count):>7}  "
            f"{_fmt_x(vol):>6}  "
            f"{rank_triplet:<15}  "
            f"{rotation_mark(delta):<3}  "
            f"{_ljust(_fmt_mom_ascii(mom), MOM_COL_WIDTH)}"
        )
        if show_narratives:
            row = (
                f"{row}  "
                f"{_ljust(_narrative_date_label(rec.theme_id, overlay), NARRATIVE_COL_WIDTH)}"
            )
        lines.append(row)
    if show_narratives and overlay is not None and overlay.error:
        lines.extend(["", overlay.error])
    lines.extend(["", REPLAY_DISCLOSURE, RANK_DISCLOSURE])
    return "\n".join(lines) + "\n"


def _momentum_lines(rec, evidence: MomentumEvidence) -> list[str]:
    return [
        f"Momentum  {evidence.label}",
        f"  5D       {_dir_arrow(evidence.five):<3}  {_fmt_signed_pct(getattr(rec, 'return_5', None))}"
        f"{_five_day_drop_note(rec, evidence)}",
        f"  20D      {_dir_arrow(evidence.twenty):<3}  {_fmt_signed_pct(rec.return_20)}",
        f"  Breadth  {_dir_arrow(evidence.breadth):<3}  "
        f"{_fmt_breadth(getattr(rec, 'above_count', None), rec.member_count)}",
        f"  Volume   {_dir_arrow(evidence.volume):<3}  {_fmt_x(getattr(rec, 'volume_ratio', None)).strip()}",
        f"  Rank     {_dir_arrow(evidence.rank):<3}  {_fmt_rank(rec.rank)}  "
        f"{_fmt_delta5(getattr(rec, 'rank_delta_5', None))}",
    ]


def render_sector_block(rec, stocks: pd.DataFrame, evidence: MomentumEvidence | None = None) -> str:
    members = stocks.loc[stocks["theme_id"] == rec.theme_id].copy()
    lines = [
        str(rec.theme_name),
        "",
        f"Sector Strength  {_fmt_rank(rec.rank)}  {rotation_mark(getattr(rec, 'rank_delta_1', None))}  "
        f"{_fmt_prev_rank(rec.rank, getattr(rec, 'rank_delta_1', None))}",
        f"1D        {_fmt_signed_pct(getattr(rec, 'return_1', None))}",
        f"5D        {_fmt_signed_pct(getattr(rec, 'return_5', None))}",
        f"20D       {_fmt_signed_pct(rec.return_20)}",
        f"RS20      {_fmt_signed_pct(rec.rs20)}",
        f"Breadth   {_fmt_breadth(getattr(rec, 'above_count', None), rec.member_count)}",
        f"Volume    {_fmt_x(getattr(rec, 'volume_ratio', None)).strip()}",
    ]
    if evidence is not None:
        lines.append("")
        lines.extend(_momentum_lines(rec, evidence))
    lines.extend(["", "Stocks"])
    if members.empty:
        lines.append("  (no members with a close on this date)")
        return "\n".join(lines)
    for role in ROLE_ORDER:
        block = members.loc[members["role"] == role]
        if block.empty:
            continue
        lines.append(role)
        for stock in block.itertuples(index=False):
            label = f"{stock.symbol} {stock.name}".strip()
            lines.append(
                f" {label:<16} "
                f"{_fmt_signed_pct_col(stock.return_1)}  "
                f"{_fmt_signed_pct_col(stock.return_5)}  "
                f"{_fmt_signed_pct_col(stock.return_20)}  "
                f"RS {_fmt_signed_pct_col(stock.rs20)}  "
                f"{_fmt_x(stock.volume_ratio)}"
            )
    return "\n".join(lines)


def render_radar_detail(snapshot: pd.DataFrame, stocks: pd.DataFrame, as_of: date, theme_id: str) -> str:
    day = radar_day(snapshot, as_of)
    block = day.loc[day["theme_id"] == theme_id]
    if block.empty:
        return f"MarketPulse — {as_of.isoformat()}\n\nUnknown sector {theme_id}.\n"
    rec = next(block.itertuples(index=False))
    evidence = momentum_evidence(snapshot, rec)
    return (
        f"MarketPulse — {as_of.isoformat()}\n\n"
        f"{render_sector_block(rec, stocks, evidence)}\n\n"
        f"{REPLAY_DISCLOSURE}\n{RANK_DISCLOSURE}\n"
    )


def _pct_class(value: object) -> str:
    if value is None or pd.isna(value):
        return "na"
    if float(value) > 0:
        return "up"
    if float(value) < 0:
        return "down"
    return "flat"


def _html_pct(value: object) -> str:
    if value is None or pd.isna(value):
        text = "n/a"
    else:
        text = _fmt_signed_pct(value)
    return f'<td class="{_pct_class(value)}">{html.escape(text)}</td>'


def _rank_history(snapshot: pd.DataFrame, theme_id: str, as_of: date, n: int = 20) -> list[tuple[date, int | None]]:
    """Last n sessions of rank for a theme, ending at as_of. Returns (date, rank) tuples."""
    hist = snapshot.loc[
        (snapshot["theme_id"] == theme_id) & (snapshot["date"] <= as_of)
    ].sort_values("date")
    if hist.empty:
        return []
    result = []
    for _, row in hist.tail(n).iterrows():
        rank = row["rank"]
        rank_val = int(rank) if rank is not None and not pd.isna(rank) else None
        result.append((row["date"], rank_val))
    return result


def _format_rank_history_html(history: list[tuple[date, int | None]]) -> str:
    """Format rank history as compact HTML text."""
    if not history:
        return "<p class='empty'>No historical data available.</p>"

    lines = []
    for d, rank in history:
        rank_str = f"#{rank}" if rank is not None else "#n/a"
        lines.append(f"{d.isoformat():<12} {rank_str}")

    return (
        "<div class='rank-history'><div style='font-family: monospace; font-size: 0.9rem; "
        "color: #333; line-height: 1.4;'>"
        + "<br>".join(lines)
        + "</div></div>"
    )


def _html_dir_class(direction: str) -> str:
    if direction == "up":
        return "up"
    if direction == "down":
        return "down"
    return "flat"


def _html_evidence_item(label: str, direction: str, value: str) -> str:
    arrow = html.escape(_dir_arrow(direction))
    return (
        f"<div><span>{html.escape(label)}</span>"
        f"<strong class='{_html_dir_class(direction)}'>"
        f"{arrow} {html.escape(value)}</strong></div>"
    )


def _freshness_line(freshness: "OpsStatus | None") -> str | None:
    """One line of the ops freshness facts for the radar.html header
    (spec 010 DO-2). Same fields `format_ops_status` prints: the data date,
    the last raw fetch attempt with its per-market status, and — only when
    not caught up — that a retry is pending. No new computation; renders
    what cli.ops_status already worked out. Returns None when no freshness
    was passed (tests / callers that don't have it), leaving the header
    byte-identical to before."""
    if freshness is None:
        return None
    as_of = getattr(freshness, "as_of", None)
    attempt = getattr(freshness, "attempt", None)
    caught_up = bool(getattr(freshness, "caught_up", False))
    as_of_text = as_of.isoformat() if as_of else "none"
    if attempt is None:
        return f"資料到 {as_of_text} · raw last attempt: none"
    tail = "" if caught_up else " · 尚未追上，refresh 會重試"
    return (
        f"資料到 {as_of_text} · raw last attempt {attempt['date'].isoformat()}"
        f"（twse={attempt['twse']} tpex={attempt['tpex']}）{tail}"
    )


def render_radar_html(
    snapshot: pd.DataFrame,
    stocks: pd.DataFrame,
    as_of: date,
    market_row: pd.Series | None = None,
    null_baseline: dict | None = None,
    *,
    show_narratives: bool = True,
    overlay: NarrativeOverlay | None = None,
    freshness: "OpsStatus | None" = None,
    limit_breaks: pd.DataFrame | None = None,
) -> str:
    day = radar_day(snapshot, as_of)
    rows = []
    sections = []
    for rec in day.itertuples(index=False):
        href = f"#{html.escape(str(rec.theme_id))}"
        name = html.escape(str(rec.theme_name))
        rot = rotation_state(rec.rank, getattr(rec, "rank_delta_1", None))
        rot_class = rot.lower()
        mark = rotation_mark(getattr(rec, "rank_delta_1", None))
        mom = momentum_evidence(snapshot, rec)
        mom_class = mom.state.lower()
        rank_triplet_html = (
            f"{html.escape(_fmt_rank_num(getattr(rec, 'rank_rs5', None)))}"
            f"{RANK_TRIPLET_SEP}<strong>{html.escape(_fmt_rank_num(rec.rank))}</strong>"
            f"{RANK_TRIPLET_SEP}{html.escape(_fmt_rank_num(getattr(rec, 'rank_rs60', None)))}"
        )
        rows.append(
            "<tr>"
            f'<td class="name"><a href="{href}">{name}</a></td>'
            f"{_html_pct(getattr(rec, 'return_1', None))}"
            f"{_html_pct(getattr(rec, 'return_5', None))}"
            f"{_html_pct(rec.return_20)}"
            f"{_html_pct(rec.rs20)}"
            f"<td>{html.escape(_fmt_breadth(getattr(rec, 'above_count', None), rec.member_count))}</td>"
            f"<td>{html.escape(_fmt_x(getattr(rec, 'volume_ratio', None)).strip())}</td>"
            f'<td class="rank">{rank_triplet_html}</td>'
            f'<td class="{rot_class}">{html.escape(mark)} {html.escape(rot)}</td>'
            f'<td class="mom {mom_class}">{html.escape(_fmt_mom_ascii(mom))}</td>'
        )
        if show_narratives:
            rows[-1] += (
                f"<td>{html.escape(_narrative_date_label(rec.theme_id, overlay))}</td>"
            )
        rows[-1] += "</tr>"
        members = stocks.loc[stocks["theme_id"] == rec.theme_id] if not stocks.empty else stocks
        stock_blocks = []
        for role in ROLE_ORDER:
            block = members.loc[members["role"] == role] if not members.empty else members
            if block.empty:
                continue
            body = []
            for stock in block.itertuples(index=False):
                label = html.escape(f"{stock.symbol} {stock.name}".strip())
                body.append(
                    "<tr>"
                    f"<td>{label}</td>"
                    f"{_html_pct(stock.return_1)}"
                    f"{_html_pct(stock.return_5)}"
                    f"{_html_pct(stock.return_20)}"
                    f"{_html_pct(stock.rs20)}"
                    f"<td>{html.escape(_fmt_x(stock.volume_ratio).strip())}</td>"
                    "</tr>"
                )
            stock_blocks.append(
                f"<h3>{html.escape(role)}</h3>"
                "<table class='stocks'><thead><tr>"
                "<th>Stock</th><th>1D</th><th>5D</th><th>20D</th><th>RS</th><th>Volume</th>"
                "</tr></thead><tbody>"
                + "".join(body)
                + "</tbody></table>"
            )
        if not stock_blocks:
            stock_html = "<p class='empty'>No members with a close on this date.</p>"
        else:
            stock_html = "".join(stock_blocks)
        evidence_html = (
            f"<div class='metrics momentum'>"
            f"<div><span>Momentum</span><strong class='{mom_class}'>"
            f"{html.escape(mom.label)}</strong></div>"
            f"{_html_evidence_item('5D', mom.five, _fmt_signed_pct(getattr(rec, 'return_5', None)) + _five_day_drop_note(rec, mom))}"
            f"{_html_evidence_item('20D', mom.twenty, _fmt_signed_pct(rec.return_20))}"
            f"{_html_evidence_item('Breadth', mom.breadth, _fmt_breadth(getattr(rec, 'above_count', None), rec.member_count))}"
            f"{_html_evidence_item('Volume', mom.volume, _fmt_x(getattr(rec, 'volume_ratio', None)).strip())}"
            f"{_html_evidence_item('Rank', mom.rank, _fmt_rank(rec.rank) + '  ' + _fmt_delta5(getattr(rec, 'rank_delta_5', None)))}"
            "</div>"
        )
        hist = _rank_history(snapshot, rec.theme_id, as_of)
        rank_hist_html = (
            "<div class='metrics rank-trend'>"
            "<div style='width: 100%;'>"
            "<span>Rank Trend (last 20 sessions)</span>"
            f"{_format_rank_history_html(hist)}"
            "</div>"
            "</div>"
        )
        sections.append(
            f'<section id="{html.escape(str(rec.theme_id))}">'
            f"<h2>{name}</h2>"
            "<div class='metrics'>"
            f"<div><span>Rank</span><strong>{html.escape(_fmt_rank(rec.rank))}</strong></div>"
            f"<div><span>Rotation</span><strong class='{rot_class}'>"
            f"{html.escape(mark)} {html.escape(rot)}</strong></div>"
            f"<div><span>1D</span><strong class='{_pct_class(getattr(rec, 'return_1', None))}'>"
            f"{html.escape(_fmt_signed_pct(getattr(rec, 'return_1', None)))}</strong></div>"
            f"<div><span>5D</span><strong class='{_pct_class(getattr(rec, 'return_5', None))}'>"
            f"{html.escape(_fmt_signed_pct(getattr(rec, 'return_5', None)))}</strong></div>"
            f"<div><span>20D</span><strong class='{_pct_class(rec.return_20)}'>"
            f"{html.escape(_fmt_signed_pct(rec.return_20))}</strong></div>"
            f"<div><span>RS20</span><strong class='{_pct_class(rec.rs20)}'>"
            f"{html.escape(_fmt_signed_pct(rec.rs20))}</strong></div>"
            f"<div><span>Breadth</span><strong>"
            f"{html.escape(_fmt_breadth(getattr(rec, 'above_count', None), rec.member_count))}</strong></div>"
            f"<div><span>Volume</span><strong>"
            f"{html.escape(_fmt_x(getattr(rec, 'volume_ratio', None)).strip())}</strong></div>"
            "</div>"
            f"{rank_hist_html}"
            f"{evidence_html}"
            f"{stock_html}"
            '<p class="back"><a href="#top">← Sector Rotation</a></p>'
            "</section>"
        )

    n_cols = 11 if show_narratives else 10
    table_body = (
        "".join(rows)
        if rows
        else f"<tr><td colspan='{n_cols}'>No snapshot for this date.</td></tr>"
    )
    narrative_th = f"<th>{html.escape(NARRATIVE_COL_HEADER)}</th>" if show_narratives else ""
    error_p = ""
    if show_narratives and overlay is not None and overlay.error:
        error_p = f"\n<p class='sub'>{html.escape(overlay.error)}</p>"
    freshness_text = _freshness_line(freshness)
    freshness_p = (
        f'\n  <p class="sub freshness">{html.escape(freshness_text)}</p>'
        if freshness_text
        else ""
    )
    limit_p = ""
    if limit_breaks is not None:
        window = impossible_returns_in_window(
            limit_breaks, snapshot["date"], as_of, LIMIT_WINDOW
        )
        limit_p = (
            f'\n  <p class="sub">{html.escape(format_limit_window_line(len(window), LIMIT_WINDOW))}</p>'
        )
    return f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>MarketPulse — {html.escape(as_of.isoformat())}</title>
<style>
  :root {{ color-scheme: light; }}
  body {{ font-family: "PingFang TC", "Noto Sans TC", "Helvetica Neue", sans-serif;
         margin: 24px auto; max-width: 1180px; color: #1a1a1a; line-height: 1.45; }}
  h1 {{ font-size: 1.6rem; margin: 0 0 4px; }}
  .sub {{ color: #555; margin: 0 0 16px; font-size: 0.95rem; }}
  .quality {{ font-family: "SF Mono", Menlo, monospace; font-size: 0.82rem;
             margin-bottom: 10px; white-space: pre-line; }}
  .freshness {{ color: #444; margin: 0 0 10px; font-size: 0.85rem; }}
  .wrap {{ overflow-x: auto; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 0.92rem; }}
  th, td {{ padding: 8px 10px; text-align: right; border-bottom: 1px solid #eee; }}
  th:first-child, td:first-child, td.name {{ text-align: left; }}
  th {{ font-size: 0.75rem; letter-spacing: 0.04em; text-transform: uppercase;
       color: #666; border-bottom: 1px solid #ccc; }}
  td.rank {{ font-size: 1.05rem; }}
  td.rank strong {{ font-weight: 700; }}
  td.mom {{ white-space: nowrap; font-weight: 600; }}
  a {{ color: #123; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  .up {{ color: #1a7f37; }}
  .down {{ color: #c62828; }}
  .flat, .na {{ color: #666; }}
  .rising {{ color: #1a7f37; font-weight: 600; }}
  .falling {{ color: #c62828; font-weight: 600; }}
  .stable {{ color: #555; }}
  .strong {{ color: #c45c00; font-weight: 600; }}
  .improving {{ color: #1a7f37; font-weight: 600; }}
  .weakening {{ color: #b26a00; font-weight: 600; }}
  .weak {{ color: #c62828; font-weight: 600; }}
  .unknown {{ color: #888; }}
  section {{ margin: 36px 0; padding-top: 8px; }}
  h2 {{ margin: 0 0 12px; }}
  h3 {{ margin: 18px 0 6px; font-size: 0.95rem; color: #333; }}
  .metrics {{ display: flex; flex-wrap: wrap; gap: 12px 20px; margin-bottom: 16px; }}
  .metrics div {{ min-width: 90px; }}
  .metrics span {{ display: block; font-size: 0.75rem; color: #666; text-transform: uppercase; }}
  .metrics strong {{ font-size: 1.1rem; }}
  .metrics.momentum {{ margin-top: -4px; padding: 10px 12px; background: #fafafa;
                      border: 1px solid #eee; border-radius: 8px; }}
  .metrics.rank-trend {{ background: #f5f5f5; padding: 12px; border: 1px solid #e0e0e0;
                        border-radius: 6px; margin-top: 8px; }}
  .rank-history {{ margin-top: 6px; }}
  .back {{ margin-top: 16px; }}
  .foot {{ margin-top: 40px; color: #777; font-size: 0.8rem; }}
  .empty {{ color: #777; }}
</style>
</head>
<body>
<header id="top">
  <h1>MarketPulse</h1>
  <p class="sub">Sector Rotation · {html.escape(as_of.isoformat())}</p>{freshness_p}
  <p class="sub quality">{html.escape(quality_line(market_row, null_baseline=null_baseline, snapshot_as_of=as_of))}</p>{limit_p}
  <p class="sub">{html.escape(RADAR_NOTE)}</p>
  <p class="sub">{html.escape(RADAR_MOM_NOTE)}</p>
  <p class="sub">{html.escape(RADAR_MOM_RULE)}</p>
</header>
<div class="wrap">
<table>
  <thead>
    <tr>
      <th>Sector</th><th>1D</th><th>5D</th><th>20D</th>
      <th>RS20</th><th>Breadth</th><th>Volume</th><th>{html.escape(RANK_TRIPLET_HEADER)}</th>
      <th>Rotation</th><th>Momentum</th>{narrative_th}
    </tr>
  </thead>
  <tbody>
    {table_body}
  </tbody>
</table>
</div>{error_p}
{"".join(sections)}
<p class="foot">{html.escape(REPLAY_DISCLOSURE)}<br/>{html.escape(RANK_DISCLOSURE)}</p>
</body>
</html>
"""


def write_radar_html(
    snapshot: pd.DataFrame,
    stocks: pd.DataFrame,
    as_of: date,
    path: Path,
    market_row: pd.Series | None = None,
    null_baseline: dict | None = None,
    *,
    show_narratives: bool = True,
    overlay: NarrativeOverlay | None = None,
    freshness: "OpsStatus | None" = None,
    limit_breaks: pd.DataFrame | None = None,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        render_radar_html(
            snapshot,
            stocks,
            as_of,
            market_row,
            null_baseline=null_baseline,
            show_narratives=show_narratives,
            overlay=overlay,
            freshness=freshness,
            limit_breaks=limit_breaks,
        ),
        encoding="utf-8",
    )
    return path
