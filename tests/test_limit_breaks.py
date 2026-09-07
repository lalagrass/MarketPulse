"""spec 011 DO-1: close-to-close moves beyond the exchange daily limit."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from marketpulse.calc import (
    LIMIT_MOVE,
    LIMIT_WINDOW,
    NO_THEME,
    compute_snapshots,
    format_impossible_returns,
    impossible_daily_returns,
    impossible_returns_in_window,
)
from marketpulse.radar import format_limit_window_line, render_radar, render_radar_html
from marketpulse.themes import Theme, ThemeSet
from tests.conftest import make_bars, make_index, session_dates, two_theme_set

REPO_ROOT = Path(__file__).resolve().parents[1]
BARS_PATH = REPO_ROOT / "data" / "normalized" / "bars.parquet"


def _break_panel() -> tuple[list[date], pd.DataFrame, ThemeSet]:
    """Three sessions. AAA 100 → 105 (inside the limit) → 30 (−71.4%)."""
    dates = [date(2026, 8, 31), date(2026, 9, 2), date(2026, 9, 3)]
    bars = make_bars(
        dates,
        {
            "AAA": [100.0, 105.0, 30.0],
            "BBB": [100.0, 100.0, 100.0],
            "CCC": [50.0, 50.0, 50.0],
        },
        twse=("AAA", "BBB"),
        tpex=("CCC",),
    )
    return dates, bars, two_theme_set()


def test_limit_move_is_the_exchange_ten_percent() -> None:
    assert LIMIT_MOVE == 0.10
    assert LIMIT_WINDOW == 20


def test_impossible_return_names_date_symbol_and_magnitude() -> None:
    dates, bars, themes = _break_panel()
    hits = impossible_daily_returns(bars, themes)
    assert len(hits) == 1
    row = hits.iloc[0]
    assert row["date"] == dates[-1]
    assert row["symbol"] == "AAA"
    assert row["return_1"] == pytest.approx(30.0 / 105.0 - 1)
    assert "Alpha" in row["themes"]


def test_impossible_return_includes_theme_name() -> None:
    _dates, bars, themes = _break_panel()
    hits = impossible_daily_returns(bars, themes)
    assert hits.iloc[0]["themes"] == "Alpha"


def test_unthemed_symbol_gets_em_dash() -> None:
    dates = session_dates(3)
    bars = make_bars(
        dates,
        {"ZZZ": [100.0, 100.0, 40.0], "BBB": [100.0, 100.0, 100.0], "CCC": [50.0, 50.0, 50.0]},
        twse=("ZZZ", "BBB"),
        tpex=("CCC",),
    )
    empty = ThemeSet("t", "2026-01-01", "", (Theme("solo", "Solo", ("BBB", "CCC")),))
    hits = impossible_daily_returns(bars, empty)
    assert list(hits["symbol"]) == ["ZZZ"]
    assert hits.iloc[0]["themes"] == NO_THEME


def test_move_inside_the_limit_is_not_listed() -> None:
    dates, bars, themes = _break_panel()
    # dates[1] is AAA 100 → 105.
    hits = impossible_daily_returns(bars, themes)
    assert dates[1] not in set(hits["date"])


def test_just_over_ten_percent_is_listed() -> None:
    dates = session_dates(2)
    bars = make_bars(
        dates,
        {"AAA": [100.0, 110.1], "BBB": [100.0, 100.0], "CCC": [50.0, 50.0]},
        twse=("AAA", "BBB"),
        tpex=("CCC",),
    )
    hits = impossible_daily_returns(bars, two_theme_set())
    assert len(hits) == 1
    assert hits.iloc[0]["symbol"] == "AAA"
    assert hits.iloc[0]["return_1"] == pytest.approx(0.101)


def test_scan_covers_every_session_in_bars() -> None:
    dates = session_dates(4)
    # Breaks on first interval and last interval.
    bars = make_bars(
        dates,
        {
            "AAA": [100.0, 50.0, 50.0, 20.0],
            "BBB": [100.0, 100.0, 100.0, 100.0],
            "CCC": [50.0, 50.0, 50.0, 50.0],
        },
        twse=("AAA", "BBB"),
        tpex=("CCC",),
    )
    hits = impossible_daily_returns(bars, two_theme_set())
    assert set(hits["date"]) == {dates[1], dates[3]}
    assert len(hits) == 2


def test_scan_does_not_mutate_input_bars() -> None:
    _dates, bars, themes = _break_panel()
    before = bars.copy()
    impossible_daily_returns(bars, themes)
    pd.testing.assert_frame_equal(bars, before)


def test_format_lists_every_row_and_total() -> None:
    _dates, bars, themes = _break_panel()
    text = format_impossible_returns(impossible_daily_returns(bars, themes))
    assert text.startswith("impossible daily returns (|close-to-close| > 10%): 1")
    assert "AAA" in text
    assert f"{(30.0 / 105.0 - 1) * 100:+.1f}%" in text
    assert "Alpha" in text


def test_window_count_uses_trailing_sessions_not_calendar() -> None:
    dates = session_dates(25)
    # 100×4 then 40×20 then 15: first break at dates[4] (outside last 20),
    # second at dates[-1] (inside). Flat 40 in between so no rebound hit.
    prices = {
        "AAA": [100.0] * 4 + [40.0] * 20 + [15.0],
        "BBB": [100.0] * 25,
        "CCC": [50.0] * 25,
    }
    bars = make_bars(dates, prices, twse=("AAA", "BBB"), tpex=("CCC",))
    hits = impossible_daily_returns(bars, two_theme_set())
    assert len(hits) == 2
    window = impossible_returns_in_window(hits, dates, dates[-1], n=20)
    assert len(window) == 1
    assert window.iloc[0]["date"] == dates[-1]


def test_radar_omits_limit_line_when_arg_is_absent() -> None:
    dates = session_dates(21)
    bars = make_bars(
        dates,
        {"AAA": [100.0] * 20 + [120.0], "BBB": [100.0] * 21, "CCC": [100.0] * 21},
        twse=("AAA", "BBB"),
        tpex=("CCC",),
    )
    snap = compute_snapshots(bars, make_index(dates, [1000.0] * 21), two_theme_set(), thin_min=1)
    text = render_radar(snap, dates[-1])
    assert "不可能的單日報酬" not in text
    page = render_radar_html(snap, pd.DataFrame(), dates[-1])
    assert "不可能的單日報酬" not in page


def test_radar_limit_line_counts_trailing_sessions() -> None:
    dates = session_dates(21)
    prices = {"AAA": [100.0] * 21, "BBB": [100.0] * 21, "CCC": [100.0] * 21}
    prices["AAA"][-1] = 40.0
    bars = make_bars(dates, prices, twse=("AAA", "BBB"), tpex=("CCC",))
    snap = compute_snapshots(bars, make_index(dates, [1000.0] * 21), two_theme_set(), thin_min=1)
    hits = impossible_daily_returns(bars, two_theme_set())
    text = render_radar(snap, dates[-1], limit_breaks=hits)
    line = format_limit_window_line(1, LIMIT_WINDOW)
    assert line in text
    page = render_radar_html(snap, pd.DataFrame(), dates[-1], limit_breaks=hits)
    assert line in page


def test_radar_limit_line_zero_still_prints() -> None:
    dates = session_dates(21)
    bars = make_bars(
        dates,
        {"AAA": [100.0] * 21, "BBB": [100.0] * 21, "CCC": [100.0] * 21},
        twse=("AAA", "BBB"),
        tpex=("CCC",),
    )
    snap = compute_snapshots(bars, make_index(dates, [1000.0] * 21), two_theme_set(), thin_min=1)
    empty = impossible_daily_returns(bars, two_theme_set())
    text = render_radar(snap, dates[-1], limit_breaks=empty)
    assert format_limit_window_line(0, LIMIT_WINDOW) in text


@pytest.mark.skipif(not BARS_PATH.exists(), reason="normalized bars not on this machine")
def test_live_bars_include_6669_on_2026_09_02() -> None:
    """A1 against the local cache. Inclusion, not an exact-equals of the
    whole scan — adding another corporate action must not fail the suite."""
    from marketpulse.data import read_normalized
    from marketpulse.themes import load_themes

    bars, _index = read_normalized(REPO_ROOT / "data")
    themes = load_themes(REPO_ROOT / "themes" / "v1.yaml")
    hits = impossible_daily_returns(bars, themes)
    keyed = set(zip(hits["date"], hits["symbol"].astype(str)))
    assert (date(2026, 9, 2), "6669") in keyed
    row = hits[(hits["date"] == date(2026, 9, 2)) & (hits["symbol"] == "6669")].iloc[0]
    # 08-31 close 7095 → 09-02 2610 was −63.2% before 09-01 was restored;
    # with 09-01 at 7800 the same print is −66.5%. Either way it is far
    # past ±10%. Pin the date/symbol, not a frozen prev-close.
    assert row["return_1"] < -0.50
    assert "AI伺服器" in row["themes"]
    text = format_impossible_returns(hits)
    assert "2026-09-02  6669" in text
    mag = f"{float(row['return_1']) * 100:+.1f}%"
    assert mag in text
