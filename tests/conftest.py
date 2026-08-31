from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from marketpulse.themes import Theme, ThemeSet

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def twse_fixture() -> Path:
    return FIXTURES / "twse_mi_index.json"


@pytest.fixture
def tpex_fixture() -> Path:
    return FIXTURES / "tpex_daily_quotes.json"


def session_dates(n: int = 30, start: date = date(2026, 1, 5)) -> list[date]:
    return [ts.date() for ts in pd.bdate_range(start, periods=n)]


def make_bars(
    dates: list[date],
    prices: dict[str, list[float]],
    *,
    twse: tuple[str, ...] = (),
    tpex: tuple[str, ...] = (),
) -> pd.DataFrame:
    rows = []
    for i, session in enumerate(dates):
        for symbol, series in prices.items():
            close = float(series[i])
            market = "TPEx" if symbol in tpex else "TWSE"
            if twse and symbol not in twse and symbol not in tpex:
                market = "TWSE"
            rows.append(
                {
                    "date": session,
                    "market": market,
                    "symbol": symbol,
                    "name": symbol,
                    "open": close,
                    "high": close,
                    "low": close,
                    "close": close,
                    "volume": 1000.0,
                    "trading_value": close * 1000.0,
                }
            )
    return pd.DataFrame(rows)


def make_index(dates: list[date], closes: list[float]) -> pd.DataFrame:
    return pd.DataFrame({"date": dates, "close": closes})


def two_theme_set() -> ThemeSet:
    return ThemeSet(
        classification_version="test",
        taxonomy_frozen_at="2026-01-01",
        notes="test",
        themes=(
            Theme("alpha", "Alpha", ("AAA", "BBB")),
            Theme("beta", "Beta", ("BBB", "CCC")),
        ),
    )
