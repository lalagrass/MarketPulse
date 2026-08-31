from __future__ import annotations

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
