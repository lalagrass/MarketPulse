from __future__ import annotations

import pytest

from marketpulse.calc import compute_snapshots
from tests.conftest import make_bars, make_index, session_dates, two_theme_set


def test_equal_weight_theme_return() -> None:
    dates = session_dates(21)
    aaa = [100.0] * 20 + [110.0]
    bbb = [100.0] * 21
    ccc = [100.0] * 21
    bars = make_bars(
        dates,
        {"AAA": aaa, "BBB": bbb, "CCC": ccc},
        twse=("AAA", "BBB"),
        tpex=("CCC",),
    )
    index = make_index(dates, [1000.0] * 21)
    snap = compute_snapshots(bars, index, two_theme_set(), thin_min=1)
    last = snap[snap["date"] == dates[-1]].set_index("theme_id")
    assert last.loc["alpha", "return_20"] == pytest.approx(0.05)
    assert last.loc["beta", "return_20"] == pytest.approx(0.0)


def test_missing_member_excluded_from_mean() -> None:
    dates = session_dates(21)
    aaa = [100.0] * 20 + [120.0]
    ccc = [100.0] * 21
    bars = make_bars(
        dates,
        {"AAA": aaa, "BBB": [100.0] * 21, "CCC": ccc},
        twse=("AAA", "BBB"),
        tpex=("CCC",),
    )
    bars = bars[~((bars["symbol"] == "BBB") & (bars["date"] == dates[-1]))]
    index = make_index(dates, [1000.0] * 21)
    snap = compute_snapshots(bars, index, two_theme_set(), thin_min=1)
    last = snap[snap["date"] == dates[-1]].set_index("theme_id")
    assert last.loc["alpha", "return_20"] == pytest.approx(0.20)
    assert last.loc["alpha", "status"] == "MISSING_DATA"
    assert last.loc["alpha", "missing_count"] == 1
