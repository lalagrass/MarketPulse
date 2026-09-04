from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pytest

from marketpulse.quality import MARKET_COLUMNS, compute_market_quality, quality_line

THEME_IDS = [f"t{i:02d}" for i in range(1, 12)]
N_DAYS = 25
REVERSE_AT = 20  # 0-indexed session where ranks flip (session #21)


def _dates(n: int = N_DAYS) -> list[date]:
    start = date(2026, 1, 5)
    return [start + timedelta(days=i) for i in range(n)]


def _rank_map(reversed_: bool) -> dict[str, int]:
    if reversed_:
        return {theme: 12 - i for i, theme in enumerate(THEME_IDS, start=1)}
    return {theme: i for i, theme in enumerate(THEME_IDS, start=1)}


def _fixture_snapshot(n_days: int = N_DAYS) -> pd.DataFrame:
    """25 consecutive sessions, 11 themes, ranks known by construction:
    normal (rank_i = i) through session 20 (0-indexed 19), then flipped
    (rank_i = 12 - i) from session 21 onward. rs20 = (12 - rank) * 0.01,
    so the RS20 *set* of values {0.01..0.11} is identical every session —
    only which theme holds which value changes — which makes dispersion
    hand-calculable as a constant.
    """
    rows: list[dict] = []
    normal = _rank_map(reversed_=False)
    flipped = _rank_map(reversed_=True)
    for day_idx, day in enumerate(_dates(n_days)):
        ranks = flipped if day_idx >= REVERSE_AT else normal
        for theme in THEME_IDS:
            rank = ranks[theme]
            rows.append(
                {
                    "date": day,
                    "theme_id": theme,
                    "rank": rank,
                    "rs20": (12 - rank) * 0.01,
                }
            )
    return pd.DataFrame(rows)


def test_hand_calc_churn_and_dispersion_at_the_flip() -> None:
    snapshot = _fixture_snapshot()
    market = compute_market_quality(snapshot)
    dates = _dates()

    # Day of the flip: rank_i (i=1..11) -> 12-i. churn = sum(|12-2i|) for i=1..11 = 60.
    flip_row = market.loc[market["date"] == dates[REVERSE_AT]].iloc[0]
    assert flip_row["rank_churn"] == pytest.approx(60.0)

    # rs20 set is {0.01..0.11} every session by construction: top-5 mean
    # (0.11+0.10+0.09+0.08+0.07)/5=0.09, bottom-5 mean
    # (0.05+0.04+0.03+0.02+0.01)/5=0.03, dispersion = 0.06, every day.
    for day in dates:
        row = market.loc[market["date"] == day].iloc[0]
        assert row["dispersion"] == pytest.approx(0.06)

    # persistence_20 at the flip compares to session 0 (also "normal"):
    # normal vs flipped over the same 11-value permutation -> -1.0.
    assert flip_row["rank_persistence_20"] == pytest.approx(-1.0)
    # persistence_5 at the flip compares to session 15, still "normal" too.
    assert flip_row["rank_persistence_5"] == pytest.approx(-1.0)


def test_unchanged_ranks_give_persistence_1_and_zero_churn() -> None:
    snapshot = _fixture_snapshot()
    market = compute_market_quality(snapshot)
    dates = _dates()
    # Session index 1: still within the "normal" run, unchanged from index 0.
    row = market.loc[market["date"] == dates[1]].iloc[0]
    assert row["rank_persistence_1"] == pytest.approx(1.0)
    assert row["rank_churn"] == pytest.approx(0.0)


def test_reversed_ranks_give_persistence_1_of_negative_one() -> None:
    snapshot = _fixture_snapshot()
    market = compute_market_quality(snapshot)
    dates = _dates()
    row = market.loc[market["date"] == dates[REVERSE_AT]].iloc[0]
    assert row["rank_persistence_1"] == pytest.approx(-1.0)


def test_percentile_is_nan_below_60_sessions_of_history() -> None:
    snapshot = _fixture_snapshot(N_DAYS)  # only 25 sessions, well under 60
    market = compute_market_quality(snapshot)
    assert market["rank_churn_pct"].isna().all()
    assert market["dispersion_pct"].isna().all()
    # Not filled with a shorter-window percentile - the raw values are still
    # present (except session 0, which has no T-1 to churn against).
    assert market["rank_churn"].iloc[1:].notna().all()
    assert market["dispersion"].notna().all()


def test_percentile_appears_once_enough_history_exists() -> None:
    # 70 sessions, all "normal" (churn == 0 throughout) except one spike.
    rows: list[dict] = []
    normal = _rank_map(reversed_=False)
    dates = _dates(70)
    for day_idx, day in enumerate(dates):
        ranks = _rank_map(reversed_=True) if day_idx == 65 else normal
        for theme in THEME_IDS:
            rank = ranks[theme]
            rows.append({"date": day, "theme_id": theme, "rank": rank, "rs20": (12 - rank) * 0.01})
    snapshot = pd.DataFrame(rows)
    market = compute_market_quality(snapshot)
    spike = market.loc[market["date"] == dates[65]].iloc[0]
    assert pd.notna(spike["rank_churn_pct"])
    # It's the single largest churn value in its trailing 60-session window -> top percentile.
    assert spike["rank_churn_pct"] == pytest.approx(1.0)


def test_quality_line_shows_numbers_only_no_verdict() -> None:
    snapshot = _fixture_snapshot()
    market = compute_market_quality(snapshot)
    dates = _dates()
    row = market.loc[market["date"] == dates[REVERSE_AT]].iloc[0]
    line = quality_line(row)
    # Raw values/percentiles are present...
    assert "60" in line
    assert "8.4pp" not in line  # sanity: not asserting an unrelated number
    assert "6.0pp" in line
    # ...and no threshold-derived verdict language leaks in (contract D10 / R1).
    for banned in ("不用看", "不可信", "值得看", "OK", "NG", "可信", "警示"):
        assert banned not in line


def test_quality_line_handles_missing_row() -> None:
    assert "n/a" in quality_line(None)


def test_future_session_does_not_change_earlier_days() -> None:
    """Appending a trading day at the tail must not change any earlier day's
    three numbers (contract R2 / DO-2 acceptance test)."""
    base = _fixture_snapshot(N_DAYS)
    market_before = compute_market_quality(base)

    extra_rows = []
    extra_day = _dates(N_DAYS + 1)[N_DAYS]
    flipped = _rank_map(reversed_=True)
    for theme in THEME_IDS:
        rank = flipped[theme]
        extra_rows.append(
            {"date": extra_day, "theme_id": theme, "rank": rank, "rs20": (12 - rank) * 0.01}
        )
    extended = pd.concat([base, pd.DataFrame(extra_rows)], ignore_index=True)
    market_after = compute_market_quality(extended)

    merged = market_before.merge(
        market_after, on="date", suffixes=("_before", "_after"), how="left"
    )
    for col in MARKET_COLUMNS:
        if col == "date":
            continue
        left = merged[f"{col}_before"]
        right = merged[f"{col}_after"]
        pd.testing.assert_series_equal(left, right, check_names=False, check_dtype=False)


def test_empty_snapshot_returns_empty_frame_with_expected_columns() -> None:
    empty = pd.DataFrame(columns=["date", "theme_id", "rank", "rs20"])
    market = compute_market_quality(empty)
    assert list(market.columns) == MARKET_COLUMNS
    assert market.empty
