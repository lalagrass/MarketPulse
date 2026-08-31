from __future__ import annotations

import pytest

from marketpulse.calc import compute_snapshots
from marketpulse.themes import Theme, ThemeSet
from tests.conftest import make_bars, make_index, session_dates


def test_breadth_is_share_above_sma20() -> None:
    dates = session_dates(21)
    # SMA20 at last date uses first 20 closes if window=20 min_periods=20,
    # including today: closes[1:21] for rolling at index 20.
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
    # UP: 120 > mean(100*19 + 120)=101 → True
    # FLAT: 100 > 100 → False
    # DOWN: 80 > mean(100*19 + 80) ≈ 99 → False
    assert last["breadth"] == pytest.approx(1 / 3)
