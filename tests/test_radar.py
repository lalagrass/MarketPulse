from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from marketpulse.calc import (
    ROLE_FOLLOWER,
    ROLE_LAGGARD,
    ROLE_LEADER,
    assign_roles,
    compute_snapshots,
    compute_stock_metrics,
)
from marketpulse.radar import (
    ROT_FALLING,
    ROT_RISING,
    ROT_STABLE,
    _format_rank_history_html,
    _rank_history,
    render_radar,
    render_radar_detail,
    render_radar_html,
    rotation_mark,
    rotation_state,
)
from marketpulse.themes import Theme, ThemeSet
from tests.conftest import make_bars, make_index, session_dates, two_theme_set


def test_assign_roles_terciles() -> None:
    assert assign_roles(0) == []
    assert assign_roles(1) == [ROLE_LEADER]
    assert assign_roles(2) == [ROLE_LEADER, ROLE_LAGGARD]
    assert assign_roles(3) == [ROLE_LEADER, ROLE_FOLLOWER, ROLE_LAGGARD]
    assert assign_roles(6) == [
        ROLE_LEADER,
        ROLE_LEADER,
        ROLE_FOLLOWER,
        ROLE_FOLLOWER,
        ROLE_LAGGARD,
        ROLE_LAGGARD,
    ]


def test_theme_1d_and_5d_equal_weight_returns() -> None:
    dates = session_dates(21)
    aaa = [100.0] * 16 + [100.0, 100.0, 100.0, 100.0, 110.0]
    bbb = [100.0] * 21
    ccc = [100.0] * 16 + [102.0, 102.0, 102.0, 102.0, 102.0]
    bars = make_bars(
        dates,
        {"AAA": aaa, "BBB": bbb, "CCC": ccc},
        twse=("AAA", "BBB"),
        tpex=("CCC",),
    )
    index = make_index(dates, [1000.0] * 21)
    snap = compute_snapshots(bars, index, two_theme_set(), thin_min=1)
    last = snap[snap["date"] == dates[-1]].set_index("theme_id")
    assert last.loc["alpha", "return_1"] == pytest.approx(0.05)
    assert last.loc["alpha", "return_5"] == pytest.approx(0.05)
    assert last.loc["alpha", "return_20"] == pytest.approx(0.05)
    assert last.loc["beta", "return_1"] == pytest.approx(0.0)
    assert last.loc["beta", "return_5"] == pytest.approx(0.01)


def test_breadth_count_is_close_above_sma20() -> None:
    dates = session_dates(21)
    flat = [100.0] * 21
    up = [100.0] * 20 + [120.0]
    down = [100.0] * 20 + [80.0]
    themes = ThemeSet(
        classification_version="test",
        taxonomy_frozen_at="2026-01-01",
        notes="test",
        themes=(Theme("mix", "Mix", ("UP", "FLAT", "DOWN")),),
    )
    bars = make_bars(
        dates,
        {"UP": up, "FLAT": flat, "DOWN": down, "TPX": flat},
        twse=("UP", "FLAT", "DOWN"),
        tpex=("TPX",),
    )
    index = make_index(dates, [1000.0] * 21)
    snap = compute_snapshots(bars, index, themes, thin_min=1)
    last = snap[snap["date"] == dates[-1]].set_index("theme_id").loc["mix"]
    assert last["above_count"] == pytest.approx(1)
    assert last["member_count"] == pytest.approx(3)
    assert last["breadth"] == pytest.approx(1 / 3)
    text = render_radar(snap, dates[-1])
    assert "1/3" in text


def test_volume_ratio_is_trading_value_over_sma20() -> None:
    dates = session_dates(21)
    prices = {"AAA": [100.0] * 21, "BBB": [100.0] * 21, "CCC": [100.0] * 21}
    bars = make_bars(dates, prices, twse=("AAA", "BBB"), tpex=("CCC",))
    bars.loc[bars["date"] == dates[-1], "volume"] = 1800.0
    bars["trading_value"] = bars["close"] * bars["volume"]
    snap = compute_snapshots(bars, make_index(dates, [1000.0] * 21), two_theme_set(), thin_min=1)
    last = snap[snap["date"] == dates[-1]].set_index("theme_id")
    # 2 members: 19 days * 2000 + last 3600, SMA20 = 2080; ratio = 3600 / 2080
    assert last.loc["alpha", "volume_ratio"] == pytest.approx(3600 / 2080)
    assert last.loc["beta", "volume_ratio"] == pytest.approx(3600 / 2080)
    assert "1.7x" in render_radar(snap, dates[-1])


def test_rank_still_orders_by_rs20() -> None:
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
    snap = compute_snapshots(bars, make_index(dates, [1000.0] * 21), two_theme_set(), thin_min=1)
    last = snap[snap["date"] == dates[-1]].set_index("theme_id")
    assert last.loc["alpha", "rs20"] > last.loc["beta", "rs20"]
    assert last.loc["alpha", "rank"] == 1
    assert last.loc["beta", "rank"] == 2


def test_rank_change_rising_falling_stable() -> None:
    dates = session_dates(22)
    aaa = [100.0] * 20 + [110.0, 100.0]
    bbb = [100.0] * 22
    ccc = [100.0] * 20 + [100.0, 120.0]
    bars = make_bars(
        dates,
        {"AAA": aaa, "BBB": bbb, "CCC": ccc},
        twse=("AAA", "BBB"),
        tpex=("CCC",),
    )
    snap = compute_snapshots(bars, make_index(dates, [1000.0] * 22), two_theme_set(), thin_min=1)
    prev = snap[snap["date"] == dates[-2]].set_index("theme_id")
    last = snap[snap["date"] == dates[-1]].set_index("theme_id")
    assert prev.loc["alpha", "rank"] == 1
    assert prev.loc["beta", "rank"] == 2
    assert last.loc["alpha", "rank"] == 2
    assert last.loc["beta", "rank"] == 1
    assert last.loc["alpha", "rank_delta_1"] == pytest.approx(-1)
    assert last.loc["beta", "rank_delta_1"] == pytest.approx(1)
    assert rotation_state(last.loc["alpha", "rank"], last.loc["alpha", "rank_delta_1"]) == ROT_FALLING
    assert rotation_state(last.loc["beta", "rank"], last.loc["beta", "rank_delta_1"]) == ROT_RISING
    assert rotation_state(1, 0) == ROT_STABLE
    assert rotation_state(1, float("nan")) == ROT_STABLE
    assert rotation_mark(2) == "↑↑"
    assert rotation_mark(-2) == "↓↓"
    text = render_radar(snap, dates[-1])
    assert "↑" in text
    assert "↓" in text


def _six_theme() -> ThemeSet:
    return ThemeSet(
        classification_version="test",
        taxonomy_frozen_at="2026-01-01",
        notes="test",
        themes=(Theme("mix", "Mix", ("A1", "A2", "A3", "A4", "A5", "A6")),),
    )


def test_stock_roles_follow_rs20_order() -> None:
    dates = session_dates(21)
    prices = {
        "A1": [100.0] * 20 + [130.0],
        "A2": [100.0] * 20 + [120.0],
        "A3": [100.0] * 20 + [110.0],
        "A4": [100.0] * 21,
        "A5": [100.0] * 20 + [95.0],
        "A6": [100.0] * 20 + [90.0],
    }
    bars = make_bars(dates, prices, twse=("A1", "A2", "A3", "A4", "A5"), tpex=("A6",))
    index = make_index(dates, [1000.0] * 21)
    stocks = compute_stock_metrics(bars, index, _six_theme(), dates[-1])
    ordered = list(stocks.sort_values(["rs20", "symbol"], ascending=[False, True])["symbol"])
    assert ordered == ["A1", "A2", "A3", "A4", "A5", "A6"]
    by_sym = stocks.set_index("symbol")
    assert by_sym.loc["A1", "role"] == ROLE_LEADER
    assert by_sym.loc["A2", "role"] == ROLE_LEADER
    assert by_sym.loc["A3", "role"] == ROLE_FOLLOWER
    assert by_sym.loc["A4", "role"] == ROLE_FOLLOWER
    assert by_sym.loc["A5", "role"] == ROLE_LAGGARD
    assert by_sym.loc["A6", "role"] == ROLE_LAGGARD
    assert by_sym.loc["A1", "return_20"] == pytest.approx(0.30)
    assert by_sym.loc["A1", "rs20"] == pytest.approx(0.30)
    assert by_sym.loc["A1", "volume_ratio"] == pytest.approx(1.0)
    second = compute_stock_metrics(bars, index, _six_theme(), dates[-1])
    pd.testing.assert_frame_equal(stocks, second)


def test_radar_html_links_to_sector_and_lists_leaders() -> None:
    dates = session_dates(21)
    prices = {
        "A1": [100.0] * 20 + [130.0],
        "A2": [100.0] * 20 + [120.0],
        "A3": [100.0] * 20 + [110.0],
        "A4": [100.0] * 21,
        "A5": [100.0] * 20 + [95.0],
        "A6": [100.0] * 20 + [90.0],
    }
    bars = make_bars(dates, prices, twse=("A1", "A2", "A3", "A4", "A5"), tpex=("A6",))
    index = make_index(dates, [1000.0] * 21)
    themes = _six_theme()
    snap = compute_snapshots(bars, index, themes, thin_min=1)
    stocks = compute_stock_metrics(bars, index, themes, dates[-1])
    page = render_radar_html(snap, stocks, dates[-1])
    assert "Sector Rotation" in page
    assert 'href="#mix"' in page
    assert 'id="mix"' in page
    assert "Leader" in page
    assert "A1" in page
    assert "Momentum" in page
    assert "rotation_score" not in page
    assert "momentum_score" not in page
    detail = render_radar_detail(snap, stocks, dates[-1], "mix")
    assert "Leader" in detail
    assert "A1" in detail
    assert detail.index("A1") < detail.index("A6")
    assert "Rank Trend" in page


def _rank_history_snapshot(n_sessions: int = 25) -> tuple[pd.DataFrame, list[date]]:
    dates = session_dates(n_sessions)
    flat = [100.0] * n_sessions
    bars = make_bars(dates, {"AAA": flat, "BBB": flat, "CCC": flat}, twse=("AAA", "BBB"), tpex=("CCC",))
    index = make_index(dates, [1000.0] * n_sessions)
    snap = compute_snapshots(bars, index, two_theme_set(), thin_min=1)
    return snap, dates


def test_rank_history_returns_ascending_dates_matching_snapshot_rank() -> None:
    snap, dates = _rank_history_snapshot()
    as_of = dates[-1]
    hist = _rank_history(snap, "alpha", as_of, n=5)
    assert [d for d, _ in hist] == dates[-5:]
    expected = snap[snap["date"] == as_of].set_index("theme_id").loc["alpha", "rank"]
    assert hist[-1][1] == int(expected)


def test_rank_history_truncates_to_n_sessions() -> None:
    snap, dates = _rank_history_snapshot()
    as_of = dates[-1]
    hist = _rank_history(snap, "alpha", as_of, n=3)
    assert len(hist) == 3
    assert [d for d, _ in hist] == dates[-3:]


def test_rank_history_excludes_dates_after_as_of() -> None:
    snap, dates = _rank_history_snapshot()
    as_of = dates[10]
    hist = _rank_history(snap, "alpha", as_of, n=20)
    assert all(d <= as_of for d, _ in hist)
    assert hist[-1][0] == as_of


def test_rank_history_empty_when_theme_has_no_rows() -> None:
    snap, dates = _rank_history_snapshot()
    assert _rank_history(snap, "no-such-theme", dates[-1]) == []


def test_format_rank_history_html_renders_dates_and_ranks() -> None:
    history = [(date(2026, 1, 5), 4), (date(2026, 1, 6), 2), (date(2026, 1, 7), None)]
    out = _format_rank_history_html(history)
    assert "2026-01-05" in out
    assert "#4" in out
    assert "2026-01-06" in out
    assert "#2" in out
    assert "#n/a" in out


def test_format_rank_history_html_empty_history() -> None:
    out = _format_rank_history_html([])
    assert "No historical data available." in out
