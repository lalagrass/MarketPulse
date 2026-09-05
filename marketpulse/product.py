"""Daily Brief and Rank Timeline. No composite score is printed."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from marketpulse import RANK_DISCLOSURE, REPLAY_DISCLOSURE
from marketpulse.quality import quality_line

THEME_ORDER = [
    "ai_server",
    "pcb",
    "high_speed_materials",
    "optical_cpo",
    "passive_components",
    "memory",
    "semiconductor_test",
    "ai_power",
    "thermal",
    "foundry_advanced",
    "heavy_electric",
]

# Distinct, slightly muted — end labels carry identity, not the legend.
THEME_COLORS = [
    "#4C78A8",
    "#F58518",
    "#54A24B",
    "#E45756",
    "#72B7B2",
    "#B279A2",
    "#EE8A82",
    "#9D755D",
    "#7A7A7A",
    "#D4A017",
    "#3D5A80",
]

STATUS_MARK = {
    "OK": " ",
    "MISSING_DATA": "*",
    "THIN": "~",
    "INSUFFICIENT_HISTORY": "·",
}

MISSING_NOTE = (
    "* MISSING_DATA: RS20/rank still computed from valid members; "
    "not a complete-membership signal."
)

STATE_LEADING = "領先"
STATE_IMPROVING = "改善"
STATE_WEAKENING = "轉弱"
STATE_LAGGING = "落後"

# Improving first: that is the rotation the reader should see before leaders.
STATE_ORDER = (
    STATE_IMPROVING,
    STATE_LEADING,
    STATE_WEAKENING,
    STATE_LAGGING,
)

NAME_WIDTH = 20
CLASSIFICATION_NOTE = "分類只用 Rank 與 Δ5。value_thrust、breadth 為附註。"
DEFAULT_CHART_SESSIONS = 40
LATEST_CHART_NAME = "rotation_latest.png"


def _fmt_pct(value: float | None, digits: int = 1) -> str:
    if value is None or pd.isna(value):
        return "   n/a"
    return f"{value * 100:6.1f}%"


def _fmt_signed_pct(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    return f"{value * 100:+.1f}%"


def _fmt_delta(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "  n/a"
    number = int(value)
    return f"{number:+4d}"


def _fmt_delta_short(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    return f"{int(value):+d}"


def _vislen(text: str) -> int:
    return sum(2 if ord(ch) > 0x2E80 else 1 for ch in text)


def _ljust(text: str, width: int) -> str:
    return text + " " * max(0, width - _vislen(text))


def status_mark(status: str) -> str:
    return STATUS_MARK.get(str(status), "?")


def brief_state(rank: object, rank_delta_5: object) -> str:
    """Display-only four-state label. Rank is still cross_sectional_rank(RS20)."""
    if rank is None or pd.isna(rank) or rank_delta_5 is None or pd.isna(rank_delta_5):
        return STATE_LAGGING
    position = int(rank)
    delta = int(rank_delta_5)
    if position <= 3 and delta >= 0:
        return STATE_LEADING
    if position >= 4 and delta >= 2:
        return STATE_IMPROVING
    if position <= 3 and delta <= -2:
        return STATE_WEAKENING
    return STATE_LAGGING


RANK_TRIPLET_SEP = "·"  # middle dot; single-width in _vislen and monospace
RANK_TRIPLET_HEADER = f"Rank R5{RANK_TRIPLET_SEP}R20{RANK_TRIPLET_SEP}R60"


def _fmt_rank_num(value: object) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    return str(int(value))


def fmt_rank_triplet(rank_rs5: object, rank: object, rank_rs60: object) -> str:
    """R5{sep}R20{sep}R60 in one cell, short-to-long window (spec 002 DO-2
    acceptance 5 / unresolved question 2). The information is in the
    relationship between the three, read by proximity - not in any one
    number, so they are never split into separate columns.

    `rank` (RS20-based) is the primary, contract-R1 ranking; R5/R60 are
    context, not equal-status rankings, so only `rank` keeps the `#`
    prefix (plain text has no bold). No arrow or direction mark is ever
    added here - that would collapse the three numbers back into a single
    verdict, which is exactly what R1/D10 forbid. The reader sees the raw
    shape (e.g. "1·#3·7" vs "7·#3·1") and draws their own conclusion.
    """
    return (
        f"{_fmt_rank_num(rank_rs5)}{RANK_TRIPLET_SEP}"
        f"#{_fmt_rank_num(rank)}{RANK_TRIPLET_SEP}"
        f"{_fmt_rank_num(rank_rs60)}"
    )


def _fmt_signed_pct_col(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "   n/a"
    return f"{value * 100:+6.1f}%"


def effective_rank_period(snapshot: pd.DataFrame) -> tuple[date, date]:
    ranked = snapshot.dropna(subset=["rank"])
    if ranked.empty:
        raise ValueError("no ranked rows")
    dates = list(ranked["date"])
    return min(dates), max(dates)


def chart_window(
    snapshot: pd.DataFrame,
    start: date | None,
    end: date | None,
    n: int = DEFAULT_CHART_SESSIONS,
) -> pd.DataFrame:
    """Default: last n ranked sessions. Explicit start keeps the full [start, end] span."""
    frame = snapshot.copy()
    if frame.empty:
        return frame
    hi = end if end is not None else max(frame["date"])
    if start is not None:
        return frame[(frame["date"] >= start) & (frame["date"] <= hi)].copy()
    ranked = frame.dropna(subset=["rank"])
    ranked = ranked.loc[ranked["date"] <= hi]
    dates = sorted(set(ranked["date"]))
    keep = set(dates[-n:])
    return frame[frame["date"].isin(keep)].copy()


def default_chart_path(reports_dir: Path, start: date | None, output: Path | None) -> Path | None:
    """None means dated name after effective_rank_period is known."""
    if output is not None:
        return output
    if start is None:
        return reports_dir / LATEST_CHART_NAME
    return None


def format_end_label(rec) -> str:
    rank = "n/a" if rec.rank is None or pd.isna(rec.rank) else str(int(rec.rank))
    mark = "*" if str(rec.status) == "MISSING_DATA" else ""
    return (
        f"#{rank} {rec.theme_name}  {_fmt_signed_pct(rec.rs20)}  "
        f"Δ5 {_fmt_delta_short(rec.rank_delta_5)}{mark}"
    )


def render_brief(snapshot: pd.DataFrame, as_of: date, market_row: pd.Series | None = None) -> str:
    day = snapshot.loc[snapshot["date"] == as_of].copy()
    if day.empty:
        return f"MarketPulse — {as_of.isoformat()}\n\nNo snapshot for this date.\n"
    day["state"] = [
        brief_state(rank, delta) for rank, delta in zip(day["rank"], day["rank_delta_5"])
    ]
    day = day.sort_values(["rank", "theme_id"], na_position="last")
    lines = [
        f"MarketPulse — {as_of.isoformat()}",
        quality_line(market_row),
        "",
        "Theme Rotation  領先 / 改善 / 轉弱 / 落後",
        CLASSIFICATION_NOTE,
        "",
    ]
    for state in STATE_ORDER:
        block = day.loc[day["state"] == state]
        if block.empty:
            continue
        lines.append(state)
        for rec in block.itertuples(index=False):
            mark = status_mark(rec.status)
            rank_triplet = fmt_rank_triplet(
                getattr(rec, "rank_rs5", None), rec.rank, getattr(rec, "rank_rs60", None)
            )
            lines.append(
                f"{mark}{_ljust(str(rec.theme_name), NAME_WIDTH)} "
                f"{rank_triplet:<9}  "
                f"Δ5 {_fmt_delta(rec.rank_delta_5)}  "
                f"RS20 {_fmt_signed_pct_col(rec.rs20)}"
            )
            lines.append(
                f"{' ' * (1 + NAME_WIDTH)} "
                f"thrust {_fmt_signed_pct_col(rec.value_thrust)}  "
                f"breadth {_fmt_pct(rec.breadth)}"
            )
        lines.append("")
    statuses = set(str(s) for s in day["status"])
    if "MISSING_DATA" in statuses:
        lines.extend([MISSING_NOTE, ""])
    lines.extend([REPLAY_DISCLOSURE, RANK_DISCLOSURE])
    return "\n".join(lines) + "\n"


def _theme_color(theme_id: str, extra: list[str]) -> str:
    if theme_id in THEME_ORDER:
        return THEME_COLORS[THEME_ORDER.index(theme_id) % len(THEME_COLORS)]
    if theme_id in extra:
        return THEME_COLORS[(len(THEME_ORDER) + extra.index(theme_id)) % len(THEME_COLORS)]
    return THEME_COLORS[0]


def render_timeline(snapshot: pd.DataFrame, path: Path) -> Path:
    frame = snapshot.copy()
    frame = frame.dropna(subset=["rank"])
    if frame.empty:
        raise ValueError("no ranked rows to chart")

    plt.rcParams["font.sans-serif"] = ["PingFang TC", "Heiti TC", "Arial Unicode MS", "sans-serif"]
    plt.rcParams["axes.unicode_minus"] = False

    fig, ax = plt.subplots(figsize=(15, 8))
    present = set(frame["theme_id"])
    ordered = [tid for tid in THEME_ORDER if tid in present]
    extra = [tid for tid in frame["theme_id"].unique() if tid not in ordered]

    # Hold each session's rank until the next session. Duplicate the last
    # point so the final day's rank is a visible step, not a lone vertex.
    hold = pd.Timedelta(hours=18)
    last_date = max(frame["date"])
    x_last = pd.to_datetime(last_date)

    for theme_id in ordered + extra:
        series = frame.loc[frame["theme_id"] == theme_id].sort_values("date")
        color = _theme_color(theme_id, extra)
        xs = pd.to_datetime(series["date"]).tolist()
        ys = series["rank"].tolist()
        xs.append(xs[-1] + hold)
        ys.append(ys[-1])
        ax.step(xs, ys, where="post", color=color, linewidth=1.8)
        missing = series.loc[series["status"] == "MISSING_DATA"]
        if not missing.empty:
            ax.scatter(
                pd.to_datetime(missing["date"]),
                missing["rank"],
                facecolors="none",
                edgecolors=color,
                s=42,
                linewidths=1.3,
                zorder=3,
            )

    last = frame.loc[frame["date"] == last_date].sort_values("rank")
    for rec in last.itertuples(index=False):
        color = _theme_color(rec.theme_id, extra)
        ax.annotate(
            format_end_label(rec),
            xy=(x_last + hold, rec.rank),
            xytext=(10, 0),
            textcoords="offset points",
            va="center",
            ha="left",
            fontsize=8.5,
            color=color,
            clip_on=False,
            annotation_clip=False,
        )

    n_themes = frame["theme_id"].nunique()
    ax.set_ylim(n_themes + 0.5, 0.5)
    ax.set_yticks(list(range(1, n_themes + 1)))
    ax.set_ylabel("Rank (1 = strongest RS20)")
    ax.set_xlabel("Date")
    eff_lo, eff_hi = effective_rank_period(frame)
    ax.set_title(
        "Theme Rotation — RS20 Rank\n"
        f"20-day relative strength · effective {eff_lo.isoformat()} → {eff_hi.isoformat()}",
        loc="left",
        pad=10,
    )
    ax.set_xlim(
        pd.to_datetime(min(frame["date"])) - pd.Timedelta(hours=8),
        x_last + hold,
    )
    ax.grid(True, axis="y", linestyle=":", alpha=0.45)
    footer = f"{REPLAY_DISCLOSURE}\n{RANK_DISCLOSURE}"
    if (frame["status"] == "MISSING_DATA").any():
        footer += f"\n{MISSING_NOTE} Hollow markers / trailing * = incomplete that session."
    fig.text(0.01, 0.01, footer, fontsize=8, wrap=True)
    fig.subplots_adjust(left=0.07, right=0.68, top=0.88, bottom=0.16)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return path


def render_persistence_chart(market: pd.DataFrame, path: Path, k: int = 20) -> Path:
    """Plot rank_persistence_k over time (spec 002 DO-1 acceptance 4).

    Fixed y-axis [-1, 1] with a zero line, since the statistic is bounded
    there by construction - this is not a data-driven axis choice. No
    verdict is drawn on the chart itself; reading it is left to the viewer
    (contract D10).
    """
    column = f"rank_persistence_{k}"
    frame = market.loc[market[column].notna(), ["date", column]].sort_values("date")
    if frame.empty:
        raise ValueError(f"no non-null {column} rows to chart")

    fig, ax = plt.subplots(figsize=(12, 4.5))
    ax.plot(
        pd.to_datetime(frame["date"]),
        frame[column],
        color="#4C78A8",
        linewidth=1.2,
    )
    ax.axhline(0, color="#999", linewidth=1, linestyle="--")
    ax.set_ylim(-1, 1)
    ax.set_ylabel(f"rank_persistence_{k}")
    ax.set_xlabel("Date")
    ax.set_title(
        f"Rank Persistence (k={k}) — Spearman corr. of today's rank vs. T-{k}",
        loc="left",
        pad=10,
    )
    ax.grid(True, axis="y", linestyle=":", alpha=0.4)
    fig.subplots_adjust(left=0.08, right=0.97, top=0.85, bottom=0.15)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return path
