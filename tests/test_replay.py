from __future__ import annotations

from marketpulse.calc import compute_snapshots, replay_snapshots, snapshots_equal
from tests.conftest import make_bars, make_index, session_dates, two_theme_set


def test_replay_is_deterministic_and_asof() -> None:
    dates = session_dates(26)
    bars = make_bars(
        dates,
        {
            "AAA": [100.0 + i for i in range(26)],
            "BBB": [90.0 + 0.4 * i for i in range(26)],
            "CCC": [70.0 + 0.8 * i for i in range(26)],
        },
        twse=("AAA", "BBB"),
        tpex=("CCC",),
    )
    index = make_index(dates, [1000.0 + 2 * i for i in range(26)])
    themes = two_theme_set()
    start, end = dates[20], dates[-1]
    first = replay_snapshots(bars, index, themes, start, end, thin_min=1)
    second = replay_snapshots(bars, index, themes, start, end, thin_min=1)
    assert snapshots_equal(first, second)
    batched = compute_snapshots(bars, index, themes, start=start, end=end, thin_min=1)
    assert snapshots_equal(first, batched)
    assert set(first["date"]) <= set(dates)
    assert first["date"].min() == start
    assert first["date"].max() == end
