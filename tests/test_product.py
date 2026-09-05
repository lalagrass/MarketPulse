from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pandas as pd

from marketpulse import RANK_DISCLOSURE, REPLAY_DISCLOSURE
from marketpulse.calc import compute_snapshots
from marketpulse.product import (
    CLASSIFICATION_NOTE,
    DEFAULT_CHART_SESSIONS,
    MISSING_NOTE,
    STATE_IMPROVING,
    STATE_LAGGING,
    STATE_LEADING,
    STATE_WEAKENING,
    brief_state,
    chart_window,
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
    assert CLASSIFICATION_NOTE in text
    assert "Value%" not in text
    assert "領先 / 改善 / 轉弱 / 落後" in text


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


def test_brief_state_predicates() -> None:
    assert brief_state(1, 0) == STATE_LEADING
    assert brief_state(3, 1) == STATE_LEADING
    assert brief_state(4, 2) == STATE_IMPROVING
    assert brief_state(11, 3) == STATE_IMPROVING
    assert brief_state(1, -2) == STATE_WEAKENING
    assert brief_state(3, -3) == STATE_WEAKENING
    assert brief_state(2, -1) == STATE_LAGGING
    assert brief_state(4, 1) == STATE_LAGGING
    assert brief_state(5, -1) == STATE_LAGGING
    assert brief_state(3, -1) == STATE_LAGGING
    assert brief_state(float("nan"), 2) == STATE_LAGGING
    assert brief_state(1, float("nan")) == STATE_LAGGING
    assert brief_state(None, 0) == STATE_LAGGING
    assert brief_state(1, None) == STATE_LAGGING


def _theme_row(
    theme_id: str,
    theme_name: str,
    rank: float | None,
    delta: float | None,
    *,
    rs20: float = 0.1,
    thrust: float = 0.0,
    breadth: float = 0.5,
    status: str = "OK",
) -> dict:
    return {
        "date": date(2026, 8, 31),
        "theme_id": theme_id,
        "theme_name": theme_name,
        "return_20": 0.12,
        "rs20": rs20,
        "rank": rank,
        "rank_delta_5": delta,
        "rank_delta_20": 0,
        "value_share": 0.08,
        "breadth": breadth,
        "value_thrust": thrust,
        "member_count": 5,
        "missing_count": 0,
        "status": status,
    }


def test_brief_groups_improving_first_and_omits_empty_blocks() -> None:
    snap = pd.DataFrame(
        [
            _theme_row("optical_cpo", "光通訊/CPO", 1, 1, rs20=0.428, thrust=-0.043, breadth=1.0),
            _theme_row("high_speed_materials", "高速材料/CCL", 2, -1, rs20=0.392, thrust=-0.046, breadth=0.5),
            _theme_row("thermal", "散熱/液冷", 3, 0, rs20=0.235, thrust=0.021, breadth=0.8),
            _theme_row("passive_components", "被動元件", 6, 3, rs20=0.145, thrust=0.110, breadth=0.571),
            _theme_row("foundry_advanced", "先進製程", 8, 2, rs20=0.056, thrust=0.003, breadth=0.667),
        ]
    )
    text = render_brief(snap, date(2026, 8, 31))
    blocks = [ln for ln in text.splitlines() if ln in {
        STATE_IMPROVING,
        STATE_LEADING,
        STATE_WEAKENING,
        STATE_LAGGING,
    }]
    assert blocks == [STATE_IMPROVING, STATE_LEADING, STATE_LAGGING]
    assert text.index("被動元件") < text.index("先進製程")
    assert text.index("被動元件") < text.index("光通訊/CPO")
    assert "高速材料/CCL" in text.split("\n落後\n", 1)[1]
    assert "Value%" not in text
    assert "thrust" in text
    assert "breadth" in text
    assert "rotation_score" not in text


def test_chart_window_defaults_to_last_n_ranked_dates() -> None:
    rows = []
    start = date(2026, 1, 5)
    dates = session_dates(50, start=start)
    for i, session in enumerate(dates):
        rows.append(
            {
                "date": session,
                "theme_id": "alpha",
                "theme_name": "Alpha",
                "rank": 1,
                "rs20": 0.1,
                "status": "OK",
            }
        )
        rows.append(
            {
                "date": session,
                "theme_id": "beta",
                "theme_name": "Beta",
                "rank": 2,
                "rs20": 0.0,
                "status": "OK",
            }
        )
    snap = pd.DataFrame(rows)
    window = chart_window(snap, None, None)
    kept = sorted(set(window["date"]))
    assert len(kept) == DEFAULT_CHART_SESSIONS
    assert kept[-1] == dates[-1]
    assert kept[0] == dates[-DEFAULT_CHART_SESSIONS]


def test_chart_window_explicit_start_is_not_clipped() -> None:
    dates = session_dates(50)
    snap = pd.DataFrame(
        [{"date": session, "theme_id": "alpha", "rank": 1, "rs20": 0.1} for session in dates]
    )
    window = chart_window(snap, dates[0], dates[-1])
    assert sorted(set(window["date"])) == dates


def test_brief_rank2_delta_minus1_is_lagging() -> None:
    snap = pd.DataFrame(
        [
            _theme_row("leader", "領先族", 1, 0),
            _theme_row("almost", "高速材料/CCL", 2, -1),
        ]
    )
    text = render_brief(snap, date(2026, 8, 31))
    after_lagging = text.split("\n落後\n", 1)[1]
    assert "高速材料/CCL" in after_lagging
    before_lagging = text.split("\n落後\n", 1)[0]
    assert "高速材料/CCL" not in before_lagging


def test_brief_unbroken_when_null_baseline_missing() -> None:
    """spec 003 DO-1: missing null-baseline file must not break Brief layout."""
    snap, dates = _snap_ok()
    text = render_brief(snap, dates[-1], market_row=None, null_baseline=None)
    assert "MarketPulse" in text
    assert "持續性 n/a" in text
    assert "虛無" not in text
    assert "†" not in text
    # Same as calling without the new kwarg (sprint-002 call shape).
    assert text == render_brief(snap, dates[-1])
