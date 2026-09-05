"""Backfill must not change numbers for existing dates after 2026-01 (spec 003 DO-2)."""

from __future__ import annotations

from datetime import date

import pandas as pd

from marketpulse.calc import compute_snapshots
from tests.conftest import make_bars, make_index, session_dates, two_theme_set


def test_earlier_history_does_not_mutate_post_2026_snapshot_rows() -> None:
    """When post-2026 rows already had full lookback, adding earlier sessions
    must leave every post-2026-01 cell unchanged (DO-2 acceptance 3)."""
    dates = session_dates(300, start=date(2025, 6, 2))
    assert min(dates) < date(2026, 1, 1) <= max(dates)

    n = len(dates)
    prices = {
        "AAA": [100.0 + i * 0.3 for i in range(n)],
        "BBB": [100.0 + (i % 5) * 0.1 for i in range(n)],
        "CCC": [100.0 + i * 0.15 for i in range(n)],
    }
    bars_full = make_bars(dates, prices, twse=("AAA", "BBB"), tpex=("CCC",))
    index_full = make_index(dates, [1000.0 + i for i in range(n)])

    mid = date(2025, 8, 1)
    bars_before = bars_full[bars_full["date"] >= mid].copy()
    index_before = index_full[index_full["date"] >= mid].copy()
    assert bars_before["date"].min() < date(2026, 1, 1)
    assert bars_full["date"].min() < bars_before["date"].min()

    themes = two_theme_set()
    snap_before = compute_snapshots(bars_before, index_before, themes, thin_min=1)
    snap_after = compute_snapshots(bars_full, index_full, themes, thin_min=1)

    post = date(2026, 1, 1)
    a = (
        snap_before[snap_before["date"] >= post]
        .sort_values(["date", "theme_id"])
        .reset_index(drop=True)
    )
    b = (
        snap_after[snap_after["date"] >= post]
        .sort_values(["date", "theme_id"])
        .reset_index(drop=True)
    )
    assert not a.empty
    assert a["rs60"].notna().all()
    pd.testing.assert_frame_equal(a, b, check_dtype=False)
