"""Daily Brief and Rank Timeline. No composite score is printed."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from marketpulse import RANK_DISCLOSURE, REPLAY_DISCLOSURE

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


def _fmt_rank(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "  n/a"
    return f"{int(value):4d}"


def _vislen(text: str) -> int:
    return sum(2 if ord(ch) > 0x2E80 else 1 for ch in text)


def _ljust(text: str, width: int) -> str:
    return text + " " * max(0, width - _vislen(text))


def status_mark(status: str) -> str:
    return STATUS_MARK.get(str(status), "?")


def effective_rank_period(snapshot: pd.DataFrame) -> tuple[date, date]:
    ranked = snapshot.dropna(subset=["rank"])
    if ranked.empty:
        raise ValueError("no ranked rows")
    dates = list(ranked["date"])
    return min(dates), max(dates)


def format_end_label(rec) -> str:
    rank = "n/a" if rec.rank is None or pd.isna(rec.rank) else str(int(rec.rank))
    mark = "*" if str(rec.status) == "MISSING_DATA" else ""
    return (
        f"#{rank} {rec.theme_name}  {_fmt_signed_pct(rec.rs20)}  "
        f"Δ5 {_fmt_delta_short(rec.rank_delta_5)}{mark}"
    )


def render_brief(snapshot: pd.DataFrame, as_of: date) -> str:
    day = snapshot.loc[snapshot["date"] == as_of].copy()
    if day.empty:
        return f"MarketPulse — {as_of.isoformat()}\n\nNo snapshot for this date.\n"
    day = day.sort_values(["rank", "theme_id"], na_position="last")
    lines = [
        f"MarketPulse — {as_of.isoformat()}",
        "",
        "Theme Rotation",
        "",
        f" {_ljust('Theme', 16)} {'Rank':>4} {'Δ5':>5} {'RS20':>8} {'Value%':>8} {'Breadth':>8}  Status",
        "-" * 72,
    ]
    for rec in day.itertuples(index=False):
        mark = status_mark(rec.status)
        lines.append(
            f"{mark}{_ljust(str(rec.theme_name), 16)} "
            f"{_fmt_rank(rec.rank)} "
            f"{_fmt_delta(rec.rank_delta_5)} "
            f"{_fmt_pct(rec.rs20)} "
            f"{_fmt_pct(rec.value_share)} "
            f"{_fmt_pct(rec.breadth)}  "
            f"{rec.status}"
        )
    statuses = set(str(s) for s in day["status"])
    if "MISSING_DATA" in statuses:
        lines.extend(["", MISSING_NOTE])
    lines.extend(["", REPLAY_DISCLOSURE, RANK_DISCLOSURE])
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
