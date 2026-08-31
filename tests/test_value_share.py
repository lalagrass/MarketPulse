from __future__ import annotations

import pytest

from marketpulse.calc import compute_snapshots
from tests.conftest import make_bars, make_index, session_dates, two_theme_set


def test_overlap_does_not_inflate_denominator() -> None:
    dates = session_dates(21)
    prices = {
        "AAA": [100.0] * 21,
        "BBB": [100.0] * 21,
        "CCC": [100.0] * 21,
    }
    bars = make_bars(dates, prices, twse=("AAA", "BBB"), tpex=("CCC",))
    # trading_value = close * 1000 = 100_000 each; three unique stocks = 300_000
    index = make_index(dates, [1000.0] * 21)
    snap = compute_snapshots(bars, index, two_theme_set(), thin_min=1)
    last = snap[snap["date"] == dates[-1]].set_index("theme_id")
    # alpha members AAA+BBB = 200_000 / 300_000
    # beta members BBB+CCC = 200_000 / 300_000
    # overlap BBB is in both numerators, once in the denominator
    assert last.loc["alpha", "value_share"] == pytest.approx(2 / 3)
    assert last.loc["beta", "value_share"] == pytest.approx(2 / 3)
    assert last.loc["alpha", "value_share"] + last.loc["beta", "value_share"] == pytest.approx(4 / 3)
