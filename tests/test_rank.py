from __future__ import annotations

import pandas as pd

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


def test_rank_rs5_orders_independently_of_rank() -> None:
    """rank_rs5 must follow the same rule as rank (descending RS, theme_id
    tie-break, NaN excluded) but rank its own column - spec 002 DO-2
    acceptance 3, and the two rankings should be free to disagree
    (acceptance 5: they are shown side by side, never blended)."""
    dates = session_dates(21)
    themes = ThemeSet(
        classification_version="test",
        taxonomy_frozen_at="2026-01-01",
        notes="test",
        themes=(
            Theme("alpha", "Alpha", ("AAA",)),
            Theme("beta", "Beta", ("BBB",)),
        ),
    )
    bars = make_bars(
        dates,
        {
            # AAA: flat then a late 5D pop -> weak rs20, strong rs5.
            "AAA": [100.0] * 16 + [100.0, 102.0, 104.0, 106.0, 108.0],
            # BBB: steady climb the whole 20D window, flat over the last 5D.
            "BBB": [100.0 + i for i in range(16)] + [116.0] * 5,
            "TPX": [100.0] * 21,
        },
        twse=("AAA", "BBB"),
        tpex=("TPX",),
    )
    index = make_index(dates, [1000.0] * 21)
    snap = compute_snapshots(bars, index, themes, thin_min=1)
    last = snap[snap["date"] == dates[-1]].set_index("theme_id")
    assert last.loc["beta", "rank"] == 1
    assert last.loc["alpha", "rank"] == 2
    assert last.loc["alpha", "rank_rs5"] == 1
    assert last.loc["beta", "rank_rs5"] == 2


def test_rank_rs5_and_rank_rs60_tie_break_by_theme_id() -> None:
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
            "AAA": [100.0] * 16 + [102.0, 104.0, 106.0, 108.0, 110.0],
            "ZZZ": [100.0] * 16 + [102.0, 104.0, 106.0, 108.0, 110.0],
            "TPX": [100.0] * 21,
        },
        twse=("AAA", "ZZZ"),
        tpex=("TPX",),
    )
    index = make_index(dates, [1000.0] * 21)
    snap = compute_snapshots(bars, index, themes, thin_min=1)
    last = snap[snap["date"] == dates[-1]].set_index("theme_id")
    assert last.loc["alpha", "rs5"] == last.loc["zeta", "rs5"]
    assert last.loc["alpha", "rank_rs5"] == 1
    assert last.loc["zeta", "rank_rs5"] == 2
    # rank_rs60 is NaN here (only 21 sessions of history) for both themes -
    # excluded from ranking entirely, not ranked as a tie.
    assert pd.isna(last.loc["alpha", "rank_rs60"])
    assert pd.isna(last.loc["zeta", "rank_rs60"])
