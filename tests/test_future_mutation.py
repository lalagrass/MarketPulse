from __future__ import annotations

from marketpulse.calc import compute_snapshots, snapshots_equal
from marketpulse.themes import Theme, ThemeSet
from tests.conftest import make_bars, make_index, session_dates, two_theme_set


def _panel():
    dates = session_dates(23)
    bars = make_bars(
        dates,
        {
            "AAA": [100.0 + i for i in range(23)],
            "BBB": [80.0 + 0.5 * i for i in range(23)],
            "CCC": [60.0 + 0.2 * i for i in range(23)],
        },
        twse=("AAA", "BBB"),
        tpex=("CCC",),
    )
    index = make_index(dates, [1000.0 + i for i in range(23)])
    return dates, bars, index


def test_future_bar_mutation_does_not_change_t() -> None:
    dates, bars, index = _panel()
    t = dates[-2]
    themes = two_theme_set()
    before = compute_snapshots(bars, index, themes, start=t, end=t, thin_min=1)
    mutated = bars.copy()
    mutated.loc[mutated["date"] == dates[-1], "close"] *= 10
    mutated.loc[mutated["date"] == dates[-1], "trading_value"] *= 10
    after = compute_snapshots(mutated, index, themes, start=t, end=t, thin_min=1)
    assert snapshots_equal(before, after)


def test_stock_visible_only_after_t_does_not_change_t() -> None:
    dates = session_dates(23)
    t = dates[-2]
    themes = ThemeSet(
        classification_version="test",
        taxonomy_frozen_at="2026-01-01",
        notes="test",
        themes=(
            Theme("alpha", "Alpha", ("AAA", "DDD")),
            Theme("beta", "Beta", ("CCC",)),
        ),
    )
    prices = {
        "AAA": [100.0 + i for i in range(23)],
        "CCC": [60.0 + 0.2 * i for i in range(23)],
        "DDD": [50.0] * 23,
    }
    bars = make_bars(dates, prices, twse=("AAA", "DDD"), tpex=("CCC",))
    bars.loc[bars["symbol"] == "DDD", "close"] = float("nan")
    bars.loc[bars["symbol"] == "DDD", "trading_value"] = float("nan")
    bars.loc[(bars["symbol"] == "DDD") & (bars["date"] == dates[-1]), "close"] = 999.0
    bars.loc[(bars["symbol"] == "DDD") & (bars["date"] == dates[-1]), "trading_value"] = 999_000.0
    index = make_index(dates, [1000.0 + i for i in range(23)])
    before = compute_snapshots(bars, index, themes, start=t, end=t, thin_min=1)
    mutated = bars.copy()
    mutated.loc[(mutated["symbol"] == "DDD") & (mutated["date"] == dates[-1]), "close"] = 1.0
    after = compute_snapshots(mutated, index, themes, start=t, end=t, thin_min=1)
    assert snapshots_equal(before, after)
    alpha = before.set_index("theme_id").loc["alpha"]
    assert alpha["missing_count"] >= 1
