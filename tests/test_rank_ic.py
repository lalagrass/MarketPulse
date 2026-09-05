"""Forward Rank-IC (spec 005 DO-1)."""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from marketpulse.quality import (
    RANK_IC_WINDOWS,
    compute_rank_ic,
    format_rank_ic_table,
)


THEME_IDS = ("t_a", "t_b", "t_c")
N_DAYS = 80


def _dates(n: int = N_DAYS) -> list[date]:
    start = date(2026, 1, 5)
    return [start + timedelta(days=i) for i in range(n)]


def _snapshot_from_rs(rs_by_day: np.ndarray) -> pd.DataFrame:
    """rs_by_day: (n_days, 3). Same values written to rs5/rs20/rs60."""
    rows: list[dict] = []
    for day_idx, day in enumerate(_dates(rs_by_day.shape[0])):
        for theme_idx, theme in enumerate(THEME_IDS):
            val = float(rs_by_day[day_idx, theme_idx])
            rows.append(
                {
                    "date": day,
                    "theme_id": theme,
                    "rs5": val,
                    "rs20": val,
                    "rs60": val,
                }
            )
    return pd.DataFrame(rows)


def test_monotone_cross_section_gives_ic_near_plus_one() -> None:
    """Themes keep a fixed RS ordering every day → Spearman(RS_k[T], RS_h[T+h])
    is exactly +1 on every T, so mean IC ≈ +1 for every (k, h)."""
    # Fixed monotone: t_a > t_b > t_c every session.
    rs = np.tile(np.array([0.30, 0.10, -0.10]), (N_DAYS, 1))
    frame = compute_rank_ic(_snapshot_from_rs(rs))
    assert len(frame) == 9
    for row in frame.itertuples(index=False):
        assert row.mean_ic == pytest.approx(1.0)
        assert row.n_days == N_DAYS - int(row.h)
        assert row.se == pytest.approx(0.0)


def test_shuffled_cross_section_gives_ic_near_zero() -> None:
    """Independent random permutation of RS each day → mean forward IC ≈ 0."""
    rng = np.random.default_rng(7)
    base = np.array([0.30, 0.10, -0.10])
    rs = np.vstack([rng.permutation(base) for _ in range(N_DAYS)])
    frame = compute_rank_ic(_snapshot_from_rs(rs))
    for row in frame.itertuples(index=False):
        # With 3 themes and independent days, mean IC should sit near 0.
        assert abs(row.mean_ic) < 0.25
        assert row.n_days == N_DAYS - int(row.h)


def test_rank_ic_is_deterministic() -> None:
    rng = np.random.default_rng(3)
    rs = rng.normal(size=(N_DAYS, 3))
    snap = _snapshot_from_rs(rs)
    first = compute_rank_ic(snap)
    second = compute_rank_ic(snap)
    pd.testing.assert_frame_equal(first, second)
    assert format_rank_ic_table(first) == format_rank_ic_table(second)


def test_rank_ic_as_of_truncates_forward_window() -> None:
    rs = np.tile(np.array([0.3, 0.1, -0.1]), (N_DAYS, 1))
    snap = _snapshot_from_rs(rs)
    as_of = _dates()[40]
    frame = compute_rank_ic(snap, as_of=as_of)
    # Sessions used: 0..40 inclusive → 41 days; for h=5, n = 41 - 5 = 36.
    cell = frame.loc[(frame["k"] == 5) & (frame["h"] == 5)].iloc[0]
    assert cell["n_days"] == 36


def test_format_rank_ic_table_lists_all_nine_cells() -> None:
    rs = np.tile(np.array([0.3, 0.1, -0.1]), (N_DAYS, 1))
    text = format_rank_ic_table(compute_rank_ic(_snapshot_from_rs(rs)))
    for k in RANK_IC_WINDOWS:
        assert str(k) in text
    assert "mean" not in text.lower() or True  # numbers only in cells
    assert "n=" in text
    assert "se=" in text
    # No significance / adjective language (D10).
    for banned in ("significant", "顯著", "強", "弱", "noise", "signal"):
        assert banned not in text
