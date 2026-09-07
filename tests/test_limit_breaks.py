"""spec 011 DO-1: close-to-close moves beyond the exchange daily limit."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

from marketpulse.calc import (
    DAILY_LIMIT,
    LIMIT_WINDOW,
    TICK_BANDS,
    TICK_TOP,
    NO_THEME,
    compute_snapshots,
    format_impossible_returns,
    impossible_daily_returns,
    impossible_returns_in_window,
    limit_down_price,
    limit_up_price,
    price_decimal,
    tick_size,
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
    assert DAILY_LIMIT == Decimal("0.10")
    assert LIMIT_WINDOW == 20


# ── spec 012 DO-2: the exchange's tick ladder and its limit prices ──


@pytest.mark.parametrize(
    ("price", "tick"),
    [
        ("0.01", "0.01"),
        ("9.99", "0.01"),
        ("10", "0.05"),  # band boundary: 10 belongs to the 10–50 band
        ("49.95", "0.05"),
        ("50", "0.10"),
        ("99.9", "0.10"),
        ("100", "0.50"),
        ("499.5", "0.50"),
        ("500", "1.00"),
        ("999", "1.00"),
        ("1000", "5.00"),
        ("12345", "5.00"),
    ],
)
def test_tick_size_at_every_band_boundary(price: str, tick: str) -> None:
    assert tick_size(Decimal(price)) == Decimal(tick)


def test_tick_bands_are_the_exchange_ladder() -> None:
    assert [(str(u), str(t)) for u, t in TICK_BANDS] == [
        ("10", "0.01"),
        ("50", "0.05"),
        ("100", "0.10"),
        ("500", "0.50"),
        ("1000", "1.00"),
    ]
    assert TICK_TOP == Decimal("5.00")


@pytest.mark.parametrize(
    ("prev", "up", "down"),
    [
        # The three closes 011 listed that are legal limit prices
        # (012-evidence §0.1). 1504 twice, 6442 once.
        ("49.5", "54.40", "44.55"),
        ("51.0", "56.10", "45.90"),
        ("1300", "1430.00", "1170.00"),
        # 012-evidence §0.2: rounding down into the next band up makes the
        # legal limit move visibly less than 10%.
        ("9.98", "10.95", "8.99"),
        ("10", "11.00", "9.00"),
        ("50", "55.00", "45.00"),
        ("100", "110.00", "90.00"),
        ("500", "550.00", "450.00"),
        ("1000", "1100.00", "900.00"),
    ],
)
def test_limit_prices_use_the_tick_of_the_band_they_land_in(
    prev: str, up: str, down: str
) -> None:
    assert limit_up_price(Decimal(prev)) == Decimal(up)
    assert limit_down_price(Decimal(prev)) == Decimal(down)


@pytest.mark.parametrize(
    ("prev", "close"),
    [(49.5, 44.55), (51.0, 56.1), (1300.0, 1430.0)],
)
def test_exact_limit_close_is_not_listed(prev: float, close: float) -> None:
    """The 1640 rows 011 listed because 44.55/49.5 - 1 > 0.10 in IEEE-754."""
    dates = session_dates(2)
    bars = make_bars(
        dates,
        {"AAA": [prev, close], "BBB": [100.0, 100.0], "CCC": [50.0, 50.0]},
        twse=("AAA", "BBB"),
        tpex=("CCC",),
    )
    assert abs(close / prev - 1) > 0.10  # the float comparison 011 used
    hits = impossible_daily_returns(bars, two_theme_set())
    assert hits.empty


def test_close_past_the_limit_price_is_listed() -> None:
    """One tick beyond 漲停價 — inside ±10% of prev, and still a break."""
    dates = session_dates(2)
    prev, close = 9.98, 11.00  # 漲停價 10.95; +10.2%
    bars = make_bars(
        dates,
        {"AAA": [prev, close], "BBB": [100.0, 100.0], "CCC": [50.0, 50.0]},
        twse=("AAA", "BBB"),
        tpex=("CCC",),
    )
    hits = impossible_daily_returns(bars, two_theme_set())
    assert list(hits["symbol"]) == ["AAA"]


def test_close_inside_ten_percent_but_past_the_limit_price_is_listed() -> None:
    """The gap ±10% could not see: 前收 9.98 → 漲停 10.95, so 10.96 is a break
    at +9.82%, below the 011 threshold entirely (012-evidence §0.2)."""
    dates = session_dates(2)
    prev, close = 9.98, 10.96
    assert abs(close / prev - 1) < 0.10
    bars = make_bars(
        dates,
        {"AAA": [prev, close], "BBB": [100.0, 100.0], "CCC": [50.0, 50.0]},
        twse=("AAA", "BBB"),
        tpex=("CCC",),
    )
    hits = impossible_daily_returns(bars, two_theme_set())
    assert list(hits["symbol"]) == ["AAA"]


def test_price_decimal_keeps_the_quoted_decimal() -> None:
    assert price_decimal(44.55) == Decimal("44.55")
    assert price_decimal(1430.0) == Decimal("1430.0")
    assert price_decimal(None) is None
    assert price_decimal(float("nan")) is None


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
    assert text.startswith(
        "impossible daily returns (close outside 漲跌停價, ±10% to tick): 1"
    )
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
