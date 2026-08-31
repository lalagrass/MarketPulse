from __future__ import annotations

from types import SimpleNamespace

from marketpulse import RANK_DISCLOSURE, REPLAY_DISCLOSURE
from marketpulse.calc import compute_snapshots
from marketpulse.product import (
    MISSING_NOTE,
    effective_rank_period,
    format_end_label,
    render_brief,
    render_timeline,
    status_mark,
)
from tests.conftest import make_bars, make_index, session_dates, two_theme_set


def _snap_ok():
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
    return snap, dates


def test_brief_discloses_visualization_replay_and_hides_score() -> None:
    snap, dates = _snap_ok()
    text = render_brief(snap, dates[-1])
    assert "MarketPulse" in text
    assert "RS20" in text
    assert REPLAY_DISCLOSURE in text
    assert RANK_DISCLOSURE in text
    assert "rotation_score" not in text
    assert "rank_momentum" not in text
    assert MISSING_NOTE not in text


def test_brief_marks_missing_data_without_hiding_rank() -> None:
    dates = session_dates(21)
    bars = make_bars(
        dates,
        {
            "AAA": [100.0] * 20 + [120.0],
            "BBB": [100.0] * 21,
            "CCC": [100.0] * 21,
        },
        twse=("AAA", "BBB"),
        tpex=("CCC",),
    )
    bars = bars[~((bars["symbol"] == "BBB") & (bars["date"] == dates[-1]))]
    index = make_index(dates, [1000.0] * 21)
    snap = compute_snapshots(bars, index, two_theme_set(), thin_min=1)
    text = render_brief(snap, dates[-1])
    last = snap[snap["date"] == dates[-1]].set_index("theme_id")
    assert last.loc["alpha", "status"] == "MISSING_DATA"
    assert "*" in text
    assert "MISSING_DATA" in text
    assert MISSING_NOTE in text
    assert "RS20" in text
    assert "rotation_score" not in text


def test_status_mark() -> None:
    assert status_mark("OK") == " "
    assert status_mark("MISSING_DATA") == "*"
    assert status_mark("THIN") == "~"
    assert status_mark("INSUFFICIENT_HISTORY") == "·"


def test_effective_rank_period_uses_ranked_rows_only() -> None:
    snap, dates = _snap_ok()
    lo, hi = effective_rank_period(snap)
    assert hi == dates[-1]
    ranked = snap.dropna(subset=["rank"])
    assert lo == min(ranked["date"])


def test_end_label_includes_rs20_and_delta() -> None:
    rec = SimpleNamespace(
        rank=1,
        theme_name="光通訊/CPO",
        rs20=0.184,
        rank_delta_5=3,
        status="OK",
    )
    assert format_end_label(rec) == "#1 光通訊/CPO  +18.4%  Δ5 +3"
    missing = SimpleNamespace(
        rank=2,
        theme_name="記憶體",
        rs20=-0.011,
        rank_delta_5=-1,
        status="MISSING_DATA",
    )
    assert format_end_label(missing) == "#2 記憶體  -1.1%  Δ5 -1*"


def test_timeline_png_written(tmp_path) -> None:
    snap, _dates = _snap_ok()
    dest = tmp_path / "rotation.png"
    render_timeline(snap, dest)
    assert dest.exists()
    assert dest.stat().st_size > 1000
