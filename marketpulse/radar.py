"""Sector Rotation Radar: ranking table + sector drill-down. Rank is still RS20."""

from __future__ import annotations

import html
from datetime import date
from pathlib import Path

import pandas as pd

from marketpulse import RANK_DISCLOSURE, REPLAY_DISCLOSURE
from marketpulse.calc import ROLE_FOLLOWER, ROLE_LAGGARD, ROLE_LEADER
from marketpulse.product import NAME_WIDTH, _fmt_signed_pct, _fmt_signed_pct_col, _ljust, status_mark

ROT_RISING = "Rising"
ROT_FALLING = "Falling"
ROT_STABLE = "Stable"
RADAR_HTML_NAME = "radar.html"

RADAR_NOTE = (
    "Rank = RS20 排序（族群 20 日報酬 − 大盤）。不是綜合分數。"
    " Breadth = 收盤價 > SMA20 的檔數。Volume = 成交量 / 20 日均量。"
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


def render_radar(snapshot: pd.DataFrame, as_of: date) -> str:
    day = radar_day(snapshot, as_of)
    if day.empty:
        return f"MarketPulse — {as_of.isoformat()}\n\nNo snapshot for this date.\n"
    lines = [
        f"MarketPulse — {as_of.isoformat()}",
        "",
        "Sector Rotation",
        RADAR_NOTE,
        "↑ Rising  ↓ Falling  → Stable   (vs previous session)",
        "",
        f"{_ljust('Sector', NAME_WIDTH)} "
        f"{'1D':>7}  {'5D':>7}  {'20D':>7}  {'RS20':>7}  "
        f"{'Breadth':>7}  {'Volume':>6}  {'Rank':<4}  Rot",
        "-" * 88,
    ]
    for rec in day.itertuples(index=False):
        mark = status_mark(rec.status)
        ret1 = rec.return_1 if hasattr(rec, "return_1") else None
        ret5 = rec.return_5 if hasattr(rec, "return_5") else None
        above = rec.above_count if hasattr(rec, "above_count") else None
        vol = rec.volume_ratio if hasattr(rec, "volume_ratio") else None
        delta = rec.rank_delta_1 if hasattr(rec, "rank_delta_1") else None
        lines.append(
            f"{mark}{_ljust(str(rec.theme_name), NAME_WIDTH)} "
            f"{_fmt_signed_pct_col(ret1)}  "
            f"{_fmt_signed_pct_col(ret5)}  "
            f"{_fmt_signed_pct_col(rec.return_20)}  "
            f"{_fmt_signed_pct_col(rec.rs20)}  "
            f"{_fmt_breadth(above, rec.member_count):>7}  "
            f"{_fmt_x(vol):>6}  "
            f"{_fmt_rank(rec.rank):<4}  "
            f"{rotation_mark(delta)}"
        )
    lines.extend(["", REPLAY_DISCLOSURE, RANK_DISCLOSURE])
    return "\n".join(lines) + "\n"


def render_sector_block(rec, stocks: pd.DataFrame) -> str:
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
        "",
        "Stocks",
    ]
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
    return (
        f"MarketPulse — {as_of.isoformat()}\n\n"
        f"{render_sector_block(rec, stocks)}\n\n"
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


def render_radar_html(snapshot: pd.DataFrame, stocks: pd.DataFrame, as_of: date) -> str:
    day = radar_day(snapshot, as_of)
    rows = []
    sections = []
    for rec in day.itertuples(index=False):
        href = f"#{html.escape(str(rec.theme_id))}"
        name = html.escape(str(rec.theme_name))
        rot = rotation_state(rec.rank, getattr(rec, "rank_delta_1", None))
        rot_class = rot.lower()
        mark = rotation_mark(getattr(rec, "rank_delta_1", None))
        rows.append(
            "<tr>"
            f'<td class="name"><a href="{href}">{name}</a></td>'
            f"{_html_pct(getattr(rec, 'return_1', None))}"
            f"{_html_pct(getattr(rec, 'return_5', None))}"
            f"{_html_pct(rec.return_20)}"
            f"{_html_pct(rec.rs20)}"
            f"<td>{html.escape(_fmt_breadth(getattr(rec, 'above_count', None), rec.member_count))}</td>"
            f"<td>{html.escape(_fmt_x(getattr(rec, 'volume_ratio', None)).strip())}</td>"
            f'<td class="rank">{html.escape(_fmt_rank(rec.rank))}</td>'
            f'<td class="{rot_class}">{html.escape(mark)} {html.escape(rot)}</td>'
            "</tr>"
        )
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
            f"{stock_html}"
            '<p class="back"><a href="#top">← Sector Rotation</a></p>'
            "</section>"
        )

    table_body = "".join(rows) if rows else "<tr><td colspan='9'>No snapshot for this date.</td></tr>"
    return f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>MarketPulse — {html.escape(as_of.isoformat())}</title>
<style>
  :root {{ color-scheme: light; }}
  body {{ font-family: "PingFang TC", "Noto Sans TC", "Helvetica Neue", sans-serif;
         margin: 24px auto; max-width: 1100px; color: #1a1a1a; line-height: 1.45; }}
  h1 {{ font-size: 1.6rem; margin: 0 0 4px; }}
  .sub {{ color: #555; margin: 0 0 16px; font-size: 0.95rem; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 0.92rem; }}
  th, td {{ padding: 8px 10px; text-align: right; border-bottom: 1px solid #eee; }}
  th:first-child, td:first-child, td.name {{ text-align: left; }}
  th {{ font-size: 0.75rem; letter-spacing: 0.04em; text-transform: uppercase;
       color: #666; border-bottom: 1px solid #ccc; }}
  td.rank {{ font-weight: 700; font-size: 1.05rem; }}
  a {{ color: #123; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  .up {{ color: #1a7f37; }}
  .down {{ color: #c62828; }}
  .flat, .na {{ color: #666; }}
  .rising {{ color: #1a7f37; font-weight: 600; }}
  .falling {{ color: #c62828; font-weight: 600; }}
  .stable {{ color: #555; }}
  section {{ margin: 36px 0; padding-top: 8px; }}
  h2 {{ margin: 0 0 12px; }}
  h3 {{ margin: 18px 0 6px; font-size: 0.95rem; color: #333; }}
  .metrics {{ display: flex; flex-wrap: wrap; gap: 12px 20px; margin-bottom: 16px; }}
  .metrics div {{ min-width: 90px; }}
  .metrics span {{ display: block; font-size: 0.75rem; color: #666; text-transform: uppercase; }}
  .metrics strong {{ font-size: 1.1rem; }}
  .back {{ margin-top: 16px; }}
  .foot {{ margin-top: 40px; color: #777; font-size: 0.8rem; }}
  .empty {{ color: #777; }}
</style>
</head>
<body>
<header id="top">
  <h1>MarketPulse</h1>
  <p class="sub">Sector Rotation · {html.escape(as_of.isoformat())}</p>
  <p class="sub">{html.escape(RADAR_NOTE)}</p>
</header>
<table>
  <thead>
    <tr>
      <th>Sector</th><th>1D</th><th>5D</th><th>20D</th>
      <th>RS20</th><th>Breadth</th><th>Volume</th><th>Rank</th><th>Rotation</th>
    </tr>
  </thead>
  <tbody>
    {table_body}
  </tbody>
</table>
{"".join(sections)}
<p class="foot">{html.escape(REPLAY_DISCLOSURE)}<br/>{html.escape(RANK_DISCLOSURE)}</p>
</body>
</html>
"""


def write_radar_html(snapshot: pd.DataFrame, stocks: pd.DataFrame, as_of: date, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_radar_html(snapshot, stocks, as_of), encoding="utf-8")
    return path
