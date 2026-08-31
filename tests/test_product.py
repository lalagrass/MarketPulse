from __future__ import annotations

from marketpulse import RANK_DISCLOSURE, REPLAY_DISCLOSURE
from marketpulse.calc import compute_snapshots
from marketpulse.product import render_brief
from tests.conftest import make_bars, make_index, session_dates, two_theme_set


def test_brief_discloses_visualization_replay_and_hides_score() -> None:
    dates = session_dates(21)
    bars = make_bars(
        dates,
        {
            "AAA": [100.0] * 20 + [110.0],
            "BBB": [100.0] * 21,
            "CCC": [100.0] * 20 + [105.0],
        },
        twse=("AAA", "BBB"),
        tpex=("CCC",),
    )
    index = make_index(dates, [1000.0] * 21)
    snap = compute_snapshots(bars, index, two_theme_set(), thin_min=1)
    text = render_brief(snap, dates[-1])
    assert "MarketPulse" in text
    assert "RS20" in text
    assert REPLAY_DISCLOSURE in text
    assert RANK_DISCLOSURE in text
    assert "rotation_score" not in text
    assert "rank_momentum" not in text
