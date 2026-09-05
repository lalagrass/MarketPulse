from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from marketpulse.quality import (
    MARKET_COLUMNS,
    NULL_METHOD_VERSION,
    STALE_MARKER,
    _null_shift_candidates,
    compute_market_quality,
    load_null_baseline,
    persistence_null_test,
    quality_line,
    write_null_baseline,
)

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


# --- persistence_null_test (spec 002 DO-1) -----------------------------------

PN_THEME_IDS = [f"t{i:02d}" for i in range(11)]
# DO-5's MIN_RETAINED_FRACTION guard (>= 1/2 of the shift circle) needs
# n >= 236 for k=20 (L=60) to pass at all - see
# test_null_test_minimum_session_count_uses_retained_fraction_boundary.
# 300 clears that with room for the various k/n_iter combinations below.
PN_N_DAYS = 300


def _pn_dates(n: int = PN_N_DAYS) -> list[date]:
    start = date(2026, 1, 5)
    return [start + timedelta(days=i) for i in range(n)]


def _ranks_from_scores(scores: np.ndarray) -> pd.DataFrame:
    """scores: (n_days, n_themes). Rank 1 = highest score that day."""
    rows: list[dict] = []
    for day_idx, day in enumerate(_pn_dates(scores.shape[0])):
        order = np.argsort(-scores[day_idx])
        ranks = np.empty(scores.shape[1], dtype=int)
        ranks[order] = np.arange(1, scores.shape[1] + 1)
        for theme_idx, theme in enumerate(PN_THEME_IDS):
            rows.append({"date": day, "theme_id": theme, "rank": int(ranks[theme_idx])})
    return pd.DataFrame(rows)


def _persistent_snapshot() -> pd.DataFrame:
    """A slow random walk per theme: adjacent days are highly correlated
    (real short-lag persistence), unlike a fixed permutation repeated every
    day, which would make every possible pairing - including null shifts -
    trivially perfectly correlated and thus uninformative as a fixture."""
    rng = np.random.default_rng(1)
    scores = np.cumsum(rng.normal(scale=1.0, size=(PN_N_DAYS, 11)), axis=0)
    return _ranks_from_scores(scores)


def _random_snapshot() -> pd.DataFrame:
    """An independent random permutation each day: no genuine persistence
    at any lag."""
    rng = np.random.default_rng(11)
    rows: list[dict] = []
    for day in _pn_dates(PN_N_DAYS):
        perm = rng.permutation(11) + 1
        for theme_idx, theme in enumerate(PN_THEME_IDS):
            rows.append({"date": day, "theme_id": theme, "rank": int(perm[theme_idx])})
    return pd.DataFrame(rows)


def test_null_test_sanity_check_k1_is_far_above_noise() -> None:
    """Acceptance 1: k=1 must be obviously significant (percentile > 99) -
    if it isn't, the implementation itself is broken, since day-to-day
    persistence is essentially always real."""
    result = persistence_null_test(_persistent_snapshot(), k=1, n_iter=500, seed=1)
    assert result["percentile"] > 99
    assert result["n_days_used"] == PN_N_DAYS - 1


def test_null_test_independent_permutations_are_not_extreme() -> None:
    """No genuine persistence by construction: the observed statistic should
    land somewhere unremarkable in the null distribution, not near either
    tail."""
    result = persistence_null_test(_random_snapshot(), k=5, n_iter=500, seed=2)
    assert 1 < result["percentile"] < 99


def test_null_test_is_reproducible_with_a_fixed_seed() -> None:
    snapshot = _persistent_snapshot()
    first = persistence_null_test(snapshot, k=20, n_iter=200, seed=99)
    second = persistence_null_test(snapshot, k=20, n_iter=200, seed=99)
    assert first == second


def test_null_test_rejects_degenerate_self_pairing_regime() -> None:
    """DO-4 acceptance 1. Pre-fix, the shift range [k, n-k) collapses to the
    single value s = k when n = 2k+1 - and s = k pairs every current row
    with itself (partner index == current index), which is a mathematical
    corr(x, x) == 1.0, not a draw from anything resembling a null. Fixed
    code must refuse this input outright (n = 41 is far below what k=20
    needs - both by DO-4's own bare candidates.size > 0 check and by DO-5's
    stricter MIN_RETAINED_FRACTION guard added afterwards) rather than
    silently returning that degenerate, self-paired null.

    Confirmed against the pre-fix implementation (this exact call): it does
    NOT raise. It returns null_mean=1.0, null_std=0.0 - every one of the 50
    draws was the self-pairing. See docs/sprints/003-report.md for the
    captured output."""
    snapshot = _persistent_snapshot()
    k = 20
    n = 2 * k + 1
    trimmed = snapshot.loc[snapshot["date"] < _pn_dates()[n]]
    with pytest.raises(ValueError):
        persistence_null_test(trimmed, k=k, n_iter=50, seed=1)


def test_null_test_minimum_session_count_uses_retained_fraction_boundary() -> None:
    """DO-5 acceptance 1 & 2: below MIN_RETAINED_FRACTION (1/2) of the shift
    circle, persistence_null_test must raise rather than return a null built
    from a biased minority of the circle - regardless of how many candidate
    shifts that minority contains (DO-4's candidates.size > 0 alone is not
    enough; this is what actually happened on the real 161-session/k=20
    case: 22 candidates, size > 0, but only 16% of the circle).

    n=236 is the smallest k=20 (L=60) session count with retained_fraction
    >= 0.5 exactly (118/236); n=235 (116/235 ~= 49.4%) must be rejected.
    Computed directly against _null_shift_candidates, not guessed."""
    snapshot = _persistent_snapshot()
    k = 20
    lag_l = max(2 * k, 60)
    n_ok = 236
    n_short = 235
    assert _null_shift_candidates(n_ok, k, lag_l).size / n_ok == pytest.approx(0.5)
    assert _null_shift_candidates(n_short, k, lag_l).size / n_short < 0.5

    trimmed_ok = snapshot.loc[snapshot["date"] < _pn_dates()[n_ok]]
    result = persistence_null_test(trimmed_ok, k=k, n_iter=10, seed=1)  # must not raise
    assert result["n_candidates"] == 118
    assert result["retained_fraction"] == pytest.approx(0.5)

    trimmed_too_short = snapshot.loc[snapshot["date"] < _pn_dates()[n_short]]
    with pytest.raises(ValueError, match="cannot support a null test"):
        persistence_null_test(trimmed_too_short, k=k, n_iter=10, seed=1)


def test_null_test_low_retained_fraction_message_reports_the_shortfall() -> None:
    """DO-5 acceptance 3 (message content): the error must state the actual
    retained fraction and the sample-too-short reason a reader can act on,
    not a bare 'ValueError'. Uses the real 161-session sample's k=20 case
    (the exact scenario DO-5 was written to catch)."""
    # n=141 mirrors the real local 161-calendar-session sample after
    # _pivot drops the ~20 RS20 warm-up rows (see docs/sprints/003-report.md
    # DO-5 section for the actual validate-signal run this reproduces).
    snapshot = _persistent_snapshot()
    k = 20
    trimmed = snapshot.loc[snapshot["date"] < _pn_dates()[141]]
    with pytest.raises(ValueError) as excinfo:
        persistence_null_test(trimmed, k=k, n_iter=10, seed=1)
    message = str(excinfo.value)
    assert "k=20" in message
    assert "retained" in message
    assert "cannot support a null test" in message


def test_null_shift_candidates_excludes_lags_under_L_hand_constructed() -> None:
    """DO-4 acceptance 2, hand-constructed case: n=12, k=1, L=3. Effective
    lags range over the full circle [-6, 6] (n // 2 = 6); L=3 excludes
    {-2,-1,0,1,2}, leaving exactly {-6,-5,-4,-3,3,4,5,6} - verified by hand
    against _null_shift_candidates, the exact sampling frame
    persistence_null_test draws from."""
    candidates = sorted(_null_shift_candidates(n=12, k=1, lag_l=3).tolist())
    assert candidates == [-6, -5, -4, -3, 3, 4, 5, 6]


def test_null_shift_candidates_never_include_self_pairing_or_lags_under_L() -> None:
    """DO-4 acceptance 1 & 2, checked exhaustively over the full sampling
    frame (not just a handful of random draws) for the k values this
    project actually reports: e=0 (self-pairing) must never appear, and no
    |e| may be under L."""
    for k in (1, 5, 20):
        lag_l = max(2 * k, 60)
        for n in (2 * lag_l, 2 * lag_l + 1, 2 * lag_l + 50, 400):
            candidates = _null_shift_candidates(n=n, k=k, lag_l=lag_l)
            assert candidates.size > 0
            assert not np.any(candidates == 0)
            assert np.all(np.abs(candidates) >= lag_l)


# --- null baseline beside quality_line (spec 003 DO-1) ---------------------


def _sample_market_row() -> pd.Series:
    snapshot = _fixture_snapshot()
    market = compute_market_quality(snapshot)
    return market.loc[market["date"] == _dates()[REVERSE_AT]].iloc[0]


_OMIT = object()  # sentinel: _null_payload(method_version=_OMIT) drops the field entirely


def _null_payload(
    *, sample_end: date, k: int = 20, method_version: object = NULL_METHOD_VERSION
) -> dict:
    entry = {
        "k": k,
        "observed": 0.2141,
        "null_mean": 0.0409,
        "null_std": 0.2948,
        "percentile": 81.0,
        "n_days_used": 121,
        "n_iter": 1000,
        "seed": 0,
        "sample_start": "2026-01-05",
        "sample_end": sample_end.isoformat(),
    }
    if method_version is not _OMIT:
        entry["method_version"] = method_version
    return {
        "generated_at": "2026-09-05T00:00:00Z",
        "sample_start": "2026-01-05",
        "sample_end": sample_end.isoformat(),
        "by_k": {str(k): entry},
    }


def test_quality_line_null_baseline_absent_matches_sprint002() -> None:
    row = _sample_market_row()
    assert quality_line(row) == quality_line(row, null_baseline=None)
    # Exact sprint-002 shape: no 虛無, no stale marker.
    line = quality_line(row)
    assert "虛無" not in line
    assert STALE_MARKER not in line
    assert line.startswith("持續性 ")


def test_quality_line_null_baseline_present_appends_numbers_only() -> None:
    row = _sample_market_row()
    as_of = row["date"]
    payload = _null_payload(sample_end=as_of)
    line = quality_line(row, null_baseline=payload, snapshot_as_of=as_of)
    assert "虛無" in line
    assert "p81" in line
    assert STALE_MARKER not in line
    for banned in ("不顯著", "弱", "noise", "僅供參考", "OK", "NG"):
        assert banned not in line


def test_quality_line_null_baseline_stale_marks_with_dagger() -> None:
    row = _sample_market_row()
    as_of = row["date"]
    stale_end = as_of - timedelta(days=1)
    payload = _null_payload(sample_end=stale_end)
    line = quality_line(row, null_baseline=payload, snapshot_as_of=as_of)
    assert STALE_MARKER in line
    assert STALE_MARKER == "†"
    # Marker sits on the persistence token, before the null reference.
    assert f"{STALE_MARKER} 虛無" in line


def test_quality_line_wrong_method_version_matches_absent_byte_for_byte() -> None:
    """DO-6 acceptance 1. A baseline file computed by a since-rejected method
    (wrong method_version) must be treated as absent, not printed with a
    warning tag - STALE_MARKER answers "is this fresh", not "was this a
    method we still trust", so it can't carry this distinction. sample_end
    is set equal to as_of (i.e. "fresh" by the old test) specifically to
    prove the rejection is about the method, not staleness."""
    row = _sample_market_row()
    as_of = row["date"]
    payload = _null_payload(sample_end=as_of, method_version=NULL_METHOD_VERSION + 1)
    with_wrong_version = quality_line(row, null_baseline=payload, snapshot_as_of=as_of)
    absent = quality_line(row, null_baseline=None, snapshot_as_of=as_of)
    assert with_wrong_version == absent


def test_quality_line_missing_method_version_matches_absent_byte_for_byte() -> None:
    """DO-6: every file written before DO-6 has no method_version key at
    all - must be treated the same as a wrong one, not grandfathered in."""
    row = _sample_market_row()
    as_of = row["date"]
    payload = _null_payload(sample_end=as_of, method_version=_OMIT)
    assert "method_version" not in payload["by_k"]["20"]
    with_no_version_field = quality_line(row, null_baseline=payload, snapshot_as_of=as_of)
    absent = quality_line(row, null_baseline=None, snapshot_as_of=as_of)
    assert with_no_version_field == absent


def test_quality_line_matching_method_version_unaffected_by_DO_6() -> None:
    """DO-6 acceptance 2: behaviour is unchanged when method_version
    matches - the DO-1 present/stale tests above already cover this since
    _null_payload now stamps the current NULL_METHOD_VERSION by default;
    this is a direct, explicit check of the same property."""
    row = _sample_market_row()
    as_of = row["date"]
    payload = _null_payload(sample_end=as_of)
    assert payload["by_k"]["20"]["method_version"] == NULL_METHOD_VERSION
    line = quality_line(row, null_baseline=payload, snapshot_as_of=as_of)
    assert "虛無" in line


def test_write_null_baseline_stamps_current_method_version(tmp_path) -> None:
    """DO-6: write_null_baseline must stamp every new entry with the
    current NULL_METHOD_VERSION - this is what makes the version check
    meaningful going forward, not just for hand-built fixtures."""
    path = tmp_path / "processed" / "signal_quality_null.json"
    result = {
        "k": 5,
        "observed": 0.5,
        "null_mean": 0.01,
        "null_std": 0.03,
        "percentile": 90.0,
        "n_days_used": 200,
        "n_iter": 1000,
        "seed": 0,
    }
    write_null_baseline(path, result, sample_start=date(2026, 1, 2), sample_end=date(2026, 9, 3))
    loaded = load_null_baseline(path)
    assert loaded["by_k"]["5"]["method_version"] == NULL_METHOD_VERSION


def test_write_and_load_null_baseline_roundtrip(tmp_path) -> None:
    path = tmp_path / "processed" / "signal_quality_null.json"
    result = {
        "k": 20,
        "observed": 0.21,
        "null_mean": 0.04,
        "null_std": 0.29,
        "percentile": 80.0,
        "n_days_used": 100,
        "n_iter": 1000,
        "seed": 0,
    }
    write_null_baseline(
        path,
        result,
        sample_start=date(2026, 1, 2),
        sample_end=date(2026, 9, 3),
    )
    loaded = load_null_baseline(path)
    assert loaded is not None
    assert loaded["sample_end"] == "2026-09-03"
    assert loaded["by_k"]["20"]["observed"] == 0.21
