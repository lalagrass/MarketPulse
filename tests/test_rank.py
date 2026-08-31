from __future__ import annotations

from marketpulse.calc import compute_snapshots
from marketpulse.themes import Theme, ThemeSet
from tests.conftest import make_bars, make_index, session_dates, two_theme_set


def test_rank_orders_by_rs20_descending() -> None:
    dates = session_dates(21)
    bars = make_bars(
        dates,
        {
            "AAA": [100.0] * 20 + [120.0],
            "BBB": [100.0] * 21,
            "CCC": [100.0] * 20 + [110.0],
        },
        twse=("AAA", "BBB"),
        tpex=("CCC",),
    )
    index = make_index(dates, [1000.0] * 21)
    snap = compute_snapshots(bars, index, two_theme_set(), thin_min=1)
    last = snap[snap["date"] == dates[-1]].set_index("theme_id")
    assert last.loc["alpha", "rank"] == 1
    assert last.loc["beta", "rank"] == 2


def test_rank_ties_break_by_theme_id() -> None:
    dates = session_dates(21)
    themes = ThemeSet(
        classification_version="test",
        taxonomy_frozen_at="2026-01-01",
        notes="test",
        themes=(
            Theme("zeta", "Zeta", ("ZZZ",)),
            Theme("alpha", "Alpha", ("AAA",)),
        ),
    )
    bars = make_bars(
        dates,
        {
            "AAA": [100.0] * 20 + [110.0],
            "ZZZ": [100.0] * 20 + [110.0],
            "TPX": [100.0] * 21,
        },
        twse=("AAA", "ZZZ"),
        tpex=("TPX",),
    )
    index = make_index(dates, [1000.0] * 21)
    snap = compute_snapshots(bars, index, themes, thin_min=1)
    last = snap[snap["date"] == dates[-1]].set_index("theme_id")
    assert last.loc["alpha", "rs20"] == last.loc["zeta", "rs20"]
    assert last.loc["alpha", "rank"] == 1
    assert last.loc["zeta", "rank"] == 2
