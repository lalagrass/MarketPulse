from __future__ import annotations

import pandas as pd
import pytest

from marketpulse.calc import compute_snapshots
from tests.conftest import make_bars, make_index, session_dates, two_theme_set


def test_rs20_is_theme_return_minus_taiex() -> None:
    dates = session_dates(21)
    aaa = [100.0] * 20 + [110.0]
    bbb = [100.0] * 20 + [110.0]
    ccc = [100.0] * 21
    bars = make_bars(
        dates,
        {"AAA": aaa, "BBB": bbb, "CCC": ccc},
        twse=("AAA", "BBB"),
        tpex=("CCC",),
    )
    index = make_index(dates, [1000.0] * 20 + [1020.0])
    snap = compute_snapshots(bars, index, two_theme_set(), thin_min=1)
    last = snap[snap["date"] == dates[-1]].set_index("theme_id")
    assert last.loc["alpha", "return_20"] == pytest.approx(0.10)
    assert last.loc["alpha", "rs20"] == pytest.approx(0.08)


def test_rs5_is_theme_return_minus_taiex_over_5_days() -> None:
    """rs5 uses the same n_day_return path as rs20, only n=5 (spec 002 DO-2
    acceptance 1)."""
    dates = session_dates(21)
    # Flat for the first 16 sessions, then a move over the last 5.
    aaa = [100.0] * 16 + [102.0, 104.0, 106.0, 108.0, 110.0]
    bbb = list(aaa)
    ccc = [100.0] * 21
    bars = make_bars(
        dates,
        {"AAA": aaa, "BBB": bbb, "CCC": ccc},
        twse=("AAA", "BBB"),
        tpex=("CCC",),
    )
    index = make_index(dates, [1000.0] * 16 + [1002.0, 1004.0, 1006.0, 1008.0, 1010.0])
    snap = compute_snapshots(bars, index, two_theme_set(), thin_min=1)
    last = snap[snap["date"] == dates[-1]].set_index("theme_id")
    # theme 5D return: 110/100 - 1 = 0.10; TAIEX 5D return: 1010/1000 - 1 = 0.01
    assert last.loc["alpha", "return_5"] == pytest.approx(0.10)
    assert last.loc["alpha", "rs5"] == pytest.approx(0.09)


def test_rs60_is_theme_return_minus_taiex_over_60_days() -> None:
    """rs60 needs 60 trading days of history; NaN before that, never
    backfilled from a shorter window (acceptance 2)."""
    dates = session_dates(65)
    aaa = [100.0] * 5 + [100.0] * 60
    # Move 20% over the last 60 sessions specifically.
    aaa = [100.0] * 5 + [100.0 * (1.2 ** (i / 60)) for i in range(1, 61)]
    bbb = list(aaa)
    ccc = [100.0] * 65
    bars = make_bars(
        dates,
        {"AAA": aaa, "BBB": bbb, "CCC": ccc},
        twse=("AAA", "BBB"),
        tpex=("CCC",),
    )
    taiex = [1000.0] * 5 + [1000.0 * (1.05 ** (i / 60)) for i in range(1, 61)]
    index = make_index(dates, taiex)
    snap = compute_snapshots(bars, index, two_theme_set(), thin_min=1)

    early = snap[snap["date"] == dates[30]].set_index("theme_id")
    assert pd.isna(early.loc["alpha", "rs60"])

    last = snap[snap["date"] == dates[-1]].set_index("theme_id")
    theme_ret_60 = aaa[-1] / aaa[-61] - 1
    taiex_ret_60 = taiex[-1] / taiex[-61] - 1
    assert last.loc["alpha", "rs60"] == pytest.approx(theme_ret_60 - taiex_ret_60)
