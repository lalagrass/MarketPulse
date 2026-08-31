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


def _fmt_pct(value: float | None, digits: int = 1) -> str:
    if value is None or pd.isna(value):
        return "   n/a"
    return f"{value * 100:6.1f}%"


def _fmt_delta(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "  n/a"
    number = int(value)
    return f"{number:+4d}"


def _fmt_rank(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "  n/a"
    return f"{int(value):4d}"


def _vislen(text: str) -> int:
    return sum(2 if ord(ch) > 0x2E80 else 1 for ch in text)


def _ljust(text: str, width: int) -> str:
    return text + " " * max(0, width - _vislen(text))


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
        f"{_ljust('Theme', 16)} {'Rank':>4} {'Δ5':>5} {'RS20':>8} {'Value%':>8} {'Breadth':>8}  Status",
        "-" * 70,
    ]
    for rec in day.itertuples(index=False):
        lines.append(
            f"{_ljust(str(rec.theme_name), 16)} "
            f"{_fmt_rank(rec.rank)} "
            f"{_fmt_delta(rec.rank_delta_5)} "
            f"{_fmt_pct(rec.rs20)} "
            f"{_fmt_pct(rec.value_share)} "
            f"{_fmt_pct(rec.breadth)}  "
            f"{rec.status}"
        )
    lines.extend(["", REPLAY_DISCLOSURE, RANK_DISCLOSURE])
    return "\n".join(lines) + "\n"


def render_timeline(snapshot: pd.DataFrame, path: Path) -> Path:
    frame = snapshot.copy()
    frame = frame.dropna(subset=["rank"])
    if frame.empty:
        raise ValueError("no ranked rows to chart")

    plt.rcParams["font.sans-serif"] = ["PingFang TC", "Heiti TC", "Arial Unicode MS", "sans-serif"]
    plt.rcParams["axes.unicode_minus"] = False

    fig, ax = plt.subplots(figsize=(14, 8))
    names = (
        frame.drop_duplicates("theme_id")
        .set_index("theme_id")["theme_name"]
        .to_dict()
    )
    colors = plt.cm.tab20.colors
    ordered = [tid for tid in THEME_ORDER if tid in set(frame["theme_id"])]
    extra = [tid for tid in frame["theme_id"].unique() if tid not in ordered]
    for i, theme_id in enumerate(ordered + extra):
        series = frame.loc[frame["theme_id"] == theme_id].sort_values("date")
        ax.plot(
            pd.to_datetime(series["date"]),
            series["rank"],
            label=names.get(theme_id, theme_id),
            color=colors[i % len(colors)],
            linewidth=2,
        )
    n_themes = frame["theme_id"].nunique()
    ax.set_ylim(n_themes + 0.5, 0.5)
    ax.set_yticks(list(range(1, n_themes + 1)))
    ax.set_ylabel("Rank (1 = strongest RS20)")
    ax.set_xlabel("Date")
    ax.set_title("MarketPulse Theme Rank Timeline")
    ax.grid(True, axis="y", linestyle=":", alpha=0.5)
    ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=False)
    fig.text(
        0.01,
        0.01,
        f"{REPLAY_DISCLOSURE}\n{RANK_DISCLOSURE}",
        fontsize=8,
        wrap=True,
    )
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return path
