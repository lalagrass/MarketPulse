"""Forward Rank-IC and circular-shift null (spec 005 DO-1, spec 006 DO-1/DO-2)."""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from marketpulse.quality import (
    MIN_RETAINED_FRACTION,
    RANK_IC_GUARD_REASON_TEMPLATE,
    RANK_IC_PERSISTENCE_CELL,
    RANK_IC_PERSISTENCE_MARK,
    RANK_IC_PERSISTENCE_NOTE,
    RANK_IC_WINDOWS,
    STALE_MARKER,
    _null_min_lag,
    _row_wise_spearman,
    _spearman_cross_section,
    compute_market_quality,
    compute_rank_ic,
    format_rank_ic_table,
    rank_ic_null_test,
)


THEME_IDS = ("t_a", "t_b", "t_c")
N_DAYS = 80
NULL_N_DAYS = 250


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


def _cyclic_rs(n_days: int) -> np.ndarray:
    """Every session rotates the same 3-value cross-section by one slot.

    Day 0: [0.30, 0.10, -0.10]; day 1: [0.10, -0.10, 0.30]; period 3.
    Spearman of a 3-cycle is +1 when the lag is 0 mod 3, and -0.5 otherwise.
    """
    base = np.array([0.30, 0.10, -0.10])
    return np.vstack([np.roll(base, -(d % 3)) for d in range(n_days)])


def _scored_rank_snapshot(n_days: int = N_DAYS, seed: int = 1) -> pd.DataFrame:
    """11 themes with a slow random walk. ``rank`` is descending score;
    ``rs*`` are the raw scores, so Spearman(rs) equals Pearson(rank) when
    there are no ties."""
    rng = np.random.default_rng(seed)
    scores = np.cumsum(rng.normal(scale=1.0, size=(n_days, 11)), axis=0)
    themes = [f"t{i:02d}" for i in range(11)]
    rows: list[dict] = []
    for day_idx, day in enumerate(_dates(n_days)):
        order = np.argsort(-scores[day_idx])
        ranks = np.empty(11, dtype=int)
        ranks[order] = np.arange(1, 12)
        for theme_idx, theme in enumerate(themes):
            val = float(scores[day_idx, theme_idx])
            rows.append(
                {
                    "date": day,
                    "theme_id": theme,
                    "rank": int(ranks[theme_idx]),
                    "rs5": val,
                    "rs20": val,
                    "rs60": val,
                }
            )
    return pd.DataFrame(rows)


def test_cyclic_rotation_ic_follows_mod_three_lag() -> None:
    """spec 006 DO-2: a 3-day cyclic rotation is +1 only when h ≡ 0 (mod 3).

    Replaces the old tiled-monotone fixture, which stayed +1 for any lag
    (including a pairing written as iloc[i] instead of iloc[i+h]).
    """
    frame = compute_rank_ic(_snapshot_from_rs(_cyclic_rs(N_DAYS)))
    assert len(frame) == 9
    for row in frame.itertuples(index=False):
        if int(row.h) % 3 == 0:
            assert row.mean_ic == pytest.approx(1.0)
        else:
            assert row.mean_ic == pytest.approx(-0.5)
        assert row.n_days == N_DAYS - int(row.h)


def test_shuffled_cross_section_gives_ic_near_zero() -> None:
    """Independent random permutation of RS each day → mean forward IC ≈ 0."""
    rng = np.random.default_rng(7)
    base = np.array([0.30, 0.10, -0.10])
    rs = np.vstack([rng.permutation(base) for _ in range(N_DAYS)])
    frame = compute_rank_ic(_snapshot_from_rs(rs))
    for row in frame.itertuples(index=False):
        assert abs(row.mean_ic) < 0.25
        assert row.n_days == N_DAYS - int(row.h)


def test_rank_ic_is_deterministic() -> None:
    rng = np.random.default_rng(3)
    rs = rng.normal(size=(N_DAYS, 3))
    snap = _snapshot_from_rs(rs)
    first = compute_rank_ic(snap)
    second = compute_rank_ic(snap)
    pd.testing.assert_frame_equal(first, second)


def test_rank_ic_as_of_truncates_forward_window() -> None:
    rs = _cyclic_rs(N_DAYS)
    snap = _snapshot_from_rs(rs)
    as_of = _dates()[40]
    frame = compute_rank_ic(snap, as_of=as_of)
    # Sessions used: 0..40 inclusive → 41 days; for h=5, n = 41 - 5 = 36.
    cell = frame.loc[(frame["k"] == 5) & (frame["h"] == 5)].iloc[0]
    assert cell["n_days"] == 36


def test_row_wise_spearman_matches_scalar_oracle_bit_identical() -> None:
    """The batched path used by the null must match _spearman_cross_section
    bit-for-bit, including asymmetric NaNs and ties."""
    rng = np.random.default_rng(0)
    for _ in range(40):
        a = rng.normal(size=11)
        b = rng.normal(size=11)
        a[rng.choice(11, 2, replace=False)] = np.nan
        b[rng.choice(11, 2, replace=False)] = np.nan
        if rng.random() < 0.3:
            a[0] = a[1]
        expected = _spearman_cross_section(pd.Series(a), pd.Series(b))
        got = _row_wise_spearman(a[None, :], b[None, :])[0]
        if np.isnan(expected):
            assert np.isnan(got)
        else:
            assert got == expected


def test_null_observed_equals_compute_rank_ic_bit_identical() -> None:
    """spec 006 DO-1 acceptance 2: one statistic, two call sites, ``==``."""
    rng = np.random.default_rng(0)
    rs = rng.normal(size=(N_DAYS, 3))
    rs[5, 1] = np.nan
    rs[20, 0] = np.nan
    rs[40, 2] = np.nan
    snap = _snapshot_from_rs(rs)
    ic = compute_rank_ic(snap)
    null = rank_ic_null_test(snap, n_iter=2, seed=0)
    assert len(ic) == 9
    assert len(null) == 9
    for ic_row, null_row in zip(ic.itertuples(index=False), null.itertuples(index=False)):
        assert int(ic_row.k) == int(null_row.k)
        assert int(ic_row.h) == int(null_row.h)
        if pd.isna(ic_row.mean_ic):
            assert pd.isna(null_row.observed)
        else:
            assert null_row.observed == ic_row.mean_ic
        assert int(null_row.n_days) == int(ic_row.n_days)


def test_rank_ic_null_is_deterministic() -> None:
    rng = np.random.default_rng(3)
    snap = _snapshot_from_rs(rng.normal(size=(NULL_N_DAYS, 3)))
    first = rank_ic_null_test(snap, n_iter=20, seed=0)
    second = rank_ic_null_test(snap, n_iter=20, seed=0)
    pd.testing.assert_frame_equal(first, second)
    assert format_rank_ic_table(first) == format_rank_ic_table(second)


def test_shuffled_null_sigma_within_three() -> None:
    """Independent daily permutations: every passing cell has |sigma| < 3.

    006-review §規劃端自己造成的問題.1: the spec said ±3, the implementation
    used `.any()`. All passing cells, not one of them.
    """
    rng = np.random.default_rng(7)
    base = np.array([0.30, 0.10, -0.10])
    rs = np.vstack([rng.permutation(base) for _ in range(NULL_N_DAYS)])
    frame = rank_ic_null_test(_snapshot_from_rs(rs), n_iter=200, seed=0)
    passing = frame[frame["reason"].eq("")]
    assert not passing.empty
    assert bool((passing["sigma"].abs() < 3).all())


def test_persistent_null_sigma_positive_zero_exceedance() -> None:
    """Slow random walk per theme: every passing cell sits well above its null.

    A tiled constant cross-section (the 005 monotone fixture) cannot be
    used here: every pairing, including every circular shift, has Spearman
    +1, so null_std is 0 and sigma is n/a. The walk is the same construction
    persistence_null_test uses for its k=1 sanity check.

    006-review §規劃端自己造成的問題.1: check all passing rows, not iloc[0].
    """
    rng = np.random.default_rng(1)
    scores = np.cumsum(rng.normal(scale=1.0, size=(NULL_N_DAYS, 3)), axis=0)
    frame = rank_ic_null_test(_snapshot_from_rs(scores), n_iter=200, seed=0)
    passing = frame[frame["reason"].eq("")]
    assert not passing.empty
    assert bool((passing["sigma"] > 3).all())
    assert bool((passing["n_ge_observed"] == 0).all())


def test_guard_failure_prints_na_and_locked_reason() -> None:
    """Short sample: every cell fails the retained-fraction guard."""
    rs = np.tile(np.array([0.30, 0.10, -0.10]), (N_DAYS, 1))
    frame = rank_ic_null_test(_snapshot_from_rs(rs), n_iter=10, seed=0)
    assert frame["reason"].ne("").all()
    text = format_rank_ic_table(frame)
    h = 5
    lag_l = _null_min_lag(h)
    expected = RANK_IC_GUARD_REASON_TEMPLATE.format(
        retained=0.0,
        threshold=MIN_RETAINED_FRACTION,
        h=h,
        L=lag_l,
    )
    assert expected == "retained 0%<50% (h=5 L=60)"
    assert expected in text
    assert "n/a" in text
    # Observed digits must not appear for a guard-fail cell.
    assert "+1.0000" not in text
    assert "se=" not in text
    assert "percentile" not in text.lower()
    for banned in ("significant", "顯著"):
        assert banned not in text


def test_format_rank_ic_table_lists_all_nine_cells() -> None:
    rs = np.tile(np.array([0.3, 0.1, -0.1]), (NULL_N_DAYS, 1))
    text = format_rank_ic_table(rank_ic_null_test(_snapshot_from_rs(rs), n_iter=20, seed=0))
    for k in RANK_IC_WINDOWS:
        assert str(k) in text
    assert "n=" in text
    assert "null" in text
    assert "se=" not in text
    assert "percentile" not in text.lower()
    for banned in ("significant", "顯著", "強", "弱", "noise", "signal"):
        assert banned not in text
    assert RANK_IC_PERSISTENCE_MARK in text
    assert RANK_IC_PERSISTENCE_NOTE in text
    assert STALE_MARKER not in text


def test_format_rank_ic_table_cells_have_column_gap() -> None:
    """spec 006 DO-3: any two cells are separated by at least two spaces."""
    rows = []
    for k in RANK_IC_WINDOWS:
        for h in RANK_IC_WINDOWS:
            rows.append(
                {
                    "k": k,
                    "h": h,
                    "observed": 0.1111 if h == 5 else 0.2222,
                    "null_mean": 0.05,
                    "null_std": 0.02,
                    "sigma": 1.0,
                    "n_ge_observed": 10,
                    "n_iter": 100,
                    "n_days": 100,
                    "retained": 0.7,
                    "reason": "",
                }
            )
    text = format_rank_ic_table(pd.DataFrame(rows))
    assert "+0.1111+0.2222" not in text
    assert "se=" not in text
    # First data line carries k=5 and both observed values, joined by >=2 spaces.
    data_line = next(line for line in text.splitlines() if line.startswith("5"))
    i1 = data_line.find("+0.1111")
    i2 = data_line.find("+0.2222")
    assert i1 != -1 and i2 != -1 and i2 > i1
    gap = data_line[i1 + len("+0.1111") : i2]
    assert gap.startswith("  ")
    assert gap.strip() == ""


def test_rank_ic_20_20_matches_rank_persistence_20() -> None:
    """spec 006 DO-2: (k=20, h=20) is rank_persistence_20, shifted. 1e-12."""
    snap = _scored_rank_snapshot(N_DAYS)
    ic = compute_rank_ic(snap)
    cell = ic.loc[(ic["k"] == 20) & (ic["h"] == 20)].iloc[0]
    market = compute_market_quality(snap)
    pers_mean = float(market["rank_persistence_20"].mean())
    assert cell["mean_ic"] == pytest.approx(pers_mean, abs=1e-12)
    assert int(cell["n_days"]) == int(market["rank_persistence_20"].notna().sum())


def test_persistence_mark_only_on_20_20() -> None:
    rs = np.tile(np.array([0.3, 0.1, -0.1]), (NULL_N_DAYS, 1))
    frame = rank_ic_null_test(_snapshot_from_rs(rs), n_iter=5, seed=0)
    text = format_rank_ic_table(frame)
    assert RANK_IC_PERSISTENCE_CELL == (20, 20)
    assert RANK_IC_PERSISTENCE_MARK == "‡"
    assert text.count(RANK_IC_PERSISTENCE_MARK) >= 2  # cell + footnote
    # Footnote is the locked D10 string.
    assert RANK_IC_PERSISTENCE_NOTE == "‡ 此格等同 rank_persistence_20，非獨立物證"
    # Does not collide with STALE_MARKER / * / ~ / ·
    assert STALE_MARKER != RANK_IC_PERSISTENCE_MARK
    for other in ("†", "*", "~", "·"):
        assert other not in RANK_IC_PERSISTENCE_MARK
        assert other not in RANK_IC_PERSISTENCE_NOTE
