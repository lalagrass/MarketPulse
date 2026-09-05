"""Signal-quality descriptive stats: is today's theme ranking worth reading.

Three independent daily statistics computed from the existing `theme_daily`
snapshot. Per contract R1, these are never combined into a single score —
callers display the three numbers separately.

rank_persistence_k uses Series/DataFrame ``.corr(method="pearson")`` on the
already rank-encoded `rank` column rather than ``method="spearman"``: this
pandas build's "spearman" path imports scipy internally, and scipy is not a
project dependency. Pearson correlation of two vectors that are already
ranks (no ties, since `rank` is 1..N within a session) is numerically
identical to the Spearman rank correlation of the underlying `rs20` values,
so no dependency is added and no new one needed. See docs/sprints/001-spec.md
DO-2.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

PERSISTENCE_LAGS = (1, 5, 20)
PERCENTILE_WINDOW = 60
NULL_TEST_ITER = 1000
# Stale marker for a null-baseline file whose sample_end differs from the
# latest snapshot date. Must not collide with status_mark glyphs (* MISSING,
# ~ THIN, · INSUFFICIENT_HISTORY) or the rank-triplet separator · (U+00B7).
STALE_MARKER = "†"
NULL_BASELINE_FILENAME = "signal_quality_null.json"
DISPLAY_NULL_K = 20  # quality_line shows persistence_20; pair with k=20 null

MARKET_COLUMNS = [
    "date",
    "rank_persistence_1",
    "rank_persistence_5",
    "rank_persistence_20",
    "rank_churn",
    "rank_churn_pct",
    "dispersion",
    "dispersion_pct",
]


def _pivot(snapshot: pd.DataFrame, column: str) -> pd.DataFrame:
    return (
        snapshot.pivot_table(index="date", columns="theme_id", values=column, aggfunc="first")
        .sort_index()
    )


def _dispersion_row(values: pd.Series) -> float:
    """Top-half minus bottom-half mean RS20 (Counterpoint Global definition).

    With an odd theme count the middle theme is excluded from both halves,
    same as any top-vs-bottom spread over an odd universe.
    """
    valid = values.dropna()
    n = len(valid)
    if n < 2:
        return float("nan")
    ordered = valid.sort_values(ascending=False)
    half = n // 2
    top = ordered.iloc[:half]
    bottom = ordered.iloc[-half:]
    return float(top.mean() - bottom.mean())


def _rank_persistence_series(ranks: pd.DataFrame, k: int) -> pd.Series:
    """Row t vs row t-k, Pearson-on-ranks (see module docstring for why not
    method="spearman"). Shared by compute_market_quality and
    persistence_null_test so both use the same definition of the statistic.
    """
    return ranks.corrwith(ranks.shift(k), axis=1, method="pearson")


def _percentile(series: pd.Series) -> pd.Series:
    """Percentile of each value within its own trailing window (incl. itself).

    NaN before `PERCENTILE_WINDOW` sessions of history — never backfilled
    from a shorter window (DO-2 acceptance 4).
    """
    return series.rolling(PERCENTILE_WINDOW, min_periods=PERCENTILE_WINDOW).rank(pct=True)


def compute_market_quality(snapshot: pd.DataFrame) -> pd.DataFrame:
    """Daily, market-level signal-quality stats. Never uses T+k data for T (R2).

    rank_persistence_k uses corrwith's default pairwise-complete handling: a
    theme with a NaN rank on either side of the pair is dropped from that
    day's correlation. Different days can therefore correlate over different
    numbers of themes (e.g. during INSUFFICIENT_HISTORY warm-up), so the
    coefficient is not strictly apples-to-apples across days.
    """
    if snapshot.empty:
        return pd.DataFrame(columns=MARKET_COLUMNS)

    ranks = _pivot(snapshot, "rank")
    rs20 = _pivot(snapshot, "rs20")

    out = pd.DataFrame(index=ranks.index)
    for k in PERSISTENCE_LAGS:
        out[f"rank_persistence_{k}"] = _rank_persistence_series(ranks, k)

    churn = (ranks - ranks.shift(1)).abs().sum(axis=1, skipna=True, min_count=1)
    out["rank_churn"] = churn
    out["rank_churn_pct"] = _percentile(churn)

    dispersion = rs20.apply(_dispersion_row, axis=1)
    out["dispersion"] = dispersion
    out["dispersion_pct"] = _percentile(dispersion)

    out.index.name = "date"
    return out.reset_index()[MARKET_COLUMNS]


def _row_wise_pearson(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Per-row Pearson correlation of two (rows, cols) arrays. A NaN in
    either side drops that column from that row's correlation only,
    mirroring corrwith's pairwise-complete handling."""
    mask = ~(np.isnan(a) | np.isnan(b))
    out = np.full(a.shape[0], np.nan)
    for i in range(a.shape[0]):
        cols = mask[i]
        if cols.sum() < 2:
            continue
        x = a[i, cols]
        y = b[i, cols]
        if x.std() == 0 or y.std() == 0:
            continue
        out[i] = np.corrcoef(x, y)[0, 1]
    return out


def persistence_null_test(
    snapshot: pd.DataFrame,
    k: int = 20,
    n_iter: int = NULL_TEST_ITER,
    seed: int | None = None,
) -> dict:
    """Circular-shift test: is rank_persistence_k distinguishable from noise?

    Observed statistic: mean over T of corr(rank[T], rank[T-k]) - the same
    quantity compute_market_quality stores per day, just averaged. T ranges
    over positions k..n-1 of the date-sorted rank matrix (n sessions); a T
    whose pair can't be correlated at all (e.g. INSUFFICIENT_HISTORY
    warm-up) contributes no term, and how many did is reported as
    n_days_used (spec 002 DO-1 acceptance 3).

    Null: for each of n_iter draws, pick a random additional shift s and
    recompute the same mean using rank[(T-k+s) mod n] in place of
    rank[T-k]. Circular shift keeps each side's own autocorrelation intact
    and only scrambles the alignment between them - unlike an i.i.d.
    shuffle of rows, which would also destroy real day-to-day continuity
    and understate the null's spread (this is the standard technique for
    testing association between two autocorrelated series). s is sampled
    from [k, n-k) so it is never close to 0 or n, where the wrapped pairing
    would coincide with (or nearly coincide with) the real, unshifted
    lag-k pairing (acceptance 2).

    This is explicitly a research statistic, unlike the T-vs-T-k-only
    display values elsewhere in this module (contract R2 red line): building
    the null intentionally uses a wraparound that a live per-day value never
    would, purely to construct a comparison distribution.
    """
    ranks = _pivot(snapshot, "rank")
    n = len(ranks)
    if n <= 2 * k:
        raise ValueError(f"need more than 2*k={2 * k} sessions, got {n}")

    values = ranks.to_numpy(dtype=float)
    positions = np.arange(k, n)
    current = values[positions]
    observed_terms = _row_wise_pearson(current, values[positions - k])
    n_days_used = int(np.count_nonzero(~np.isnan(observed_terms)))
    observed = float(np.nanmean(observed_terms)) if n_days_used else float("nan")

    rng = np.random.default_rng(seed)
    lo, hi = k, n - k
    null_values = np.full(n_iter, np.nan)
    for i in range(n_iter):
        s = int(rng.integers(lo, hi))
        partner = values[(positions - k + s) % n]
        terms = _row_wise_pearson(current, partner)
        if np.any(~np.isnan(terms)):
            null_values[i] = np.nanmean(terms)

    valid_null = null_values[~np.isnan(null_values)]
    null_mean = float(np.mean(valid_null)) if len(valid_null) else float("nan")
    null_std = float(np.std(valid_null, ddof=1)) if len(valid_null) > 1 else float("nan")
    percentile = (
        float((valid_null < observed).mean() * 100)
        if len(valid_null) and pd.notna(observed)
        else float("nan")
    )

    return {
        "k": k,
        "observed": observed,
        "n_days_used": n_days_used,
        "null_mean": null_mean,
        "null_std": null_std,
        "percentile": percentile,
        "n_iter": int(len(valid_null)),
        "seed": seed,
    }


def _fmt_corr(value: object) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    text = f"{float(value):.2f}"
    if text.startswith("0."):
        return text[1:]
    if text.startswith("-0."):
        return "-" + text[2:]
    return text


def _fmt_pct(value: object) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    return f"{int(round(float(value) * 100))}%"


def _fmt_pp(value: object) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    return f"{float(value) * 100:.1f}pp"


def null_baseline_path(data_dir: Path) -> Path:
    """Independent JSON beside the daily snapshots (spec 003 DO-1)."""
    return Path(data_dir) / "processed" / NULL_BASELINE_FILENAME


def load_null_baseline(path: Path) -> dict | None:
    """Return parsed payload or None if the file is absent / unreadable."""
    path = Path(path)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _parse_iso_date(value: object) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    text = str(value).strip()
    if not text:
        return None
    return date.fromisoformat(text[:10])


def write_null_baseline(
    path: Path,
    result: dict,
    *,
    sample_start: date,
    sample_end: date,
    generated_at: datetime | None = None,
) -> Path:
    """Persist / merge one validate-signal result into the null-baseline file.

    Multiple k values share one file under ``by_k``; sample window and
    generated_at are refreshed on every write (the diagnostic is re-run over
    the current snapshot).
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = load_null_baseline(path) or {}
    by_k = existing.get("by_k") if isinstance(existing.get("by_k"), dict) else {}
    k = int(result["k"])
    entry = {
        "k": k,
        "observed": result["observed"],
        "null_mean": result["null_mean"],
        "null_std": result["null_std"],
        "percentile": result["percentile"],
        "n_days_used": result["n_days_used"],
        "n_iter": result["n_iter"],
        "seed": result["seed"],
        "sample_start": sample_start.isoformat(),
        "sample_end": sample_end.isoformat(),
    }
    by_k[str(k)] = entry
    when = generated_at or datetime.now(timezone.utc)
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    payload = {
        "generated_at": when.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sample_start": sample_start.isoformat(),
        "sample_end": sample_end.isoformat(),
        "by_k": by_k,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _null_entry_for_display(payload: dict | None, k: int = DISPLAY_NULL_K) -> dict | None:
    if not payload:
        return None
    by_k = payload.get("by_k")
    if isinstance(by_k, dict):
        entry = by_k.get(str(k))
        if isinstance(entry, dict):
            return entry
    # tolerate a flat single-result file
    if payload.get("k") == k or str(payload.get("k")) == str(k):
        return payload
    return None


def _fmt_null_baseline(entry: dict) -> str:
    """Pure numbers for the null reference — no adjectives (D10)."""
    mean = _fmt_corr(entry.get("null_mean"))
    std = _fmt_corr(entry.get("null_std"))
    pct = entry.get("percentile")
    if pct is None or pd.isna(pct):
        pct_text = "n/a"
    else:
        pct_text = f"{int(round(float(pct)))}"
    return f"虛無 {mean}±{std} p{pct_text}"


def quality_line(
    market_row: pd.Series | None,
    *,
    null_baseline: dict | None = None,
    snapshot_as_of: date | None = None,
) -> str:
    """Compact one-line signal-quality readout: numbers and percentiles only.

    No verdict, no threshold-based label (D10 / acceptance 5) — the reader
    judges. Uses rank_persistence_20 rather than rank_persistence_1: the
    1-day lag answers the same question as rank_churn (today vs. yesterday),
    so pairing them would spend two of the three slots on one thing. The 20
    lag gives the line three genuinely different scales instead.

    When ``null_baseline`` (from validate-signal) is present, appends the
    k=20 null reference as pure numbers. If its sample_end differs from
    ``snapshot_as_of`` (or market_row's date), appends STALE_MARKER (†) after
    the observed persistence — visible, not silent. Missing file / None
    baseline keeps the sprint-002 string byte-for-byte.
    """
    if market_row is None:
        base = "持續性 n/a   換手 n/a   離散 n/a"
        # Still allow a stale/present null marker only when there is something
        # to attach to; without a row there is no persistence digit.
        return base
    persistence = _fmt_corr(market_row.get("rank_persistence_20"))
    churn = market_row.get("rank_churn")
    churn_text = "n/a" if churn is None or pd.isna(churn) else f"{int(round(float(churn)))}"
    churn_pct = _fmt_pct(market_row.get("rank_churn_pct"))
    dispersion_text = _fmt_pp(market_row.get("dispersion"))
    dispersion_pct = _fmt_pct(market_row.get("dispersion_pct"))

    entry = _null_entry_for_display(null_baseline, DISPLAY_NULL_K)
    if entry is None:
        return (
            f"持續性 {persistence}   "
            f"換手 {churn_text} ({churn_pct})   "
            f"離散 {dispersion_text} ({dispersion_pct})"
        )

    as_of = snapshot_as_of
    if as_of is None:
        as_of = _parse_iso_date(market_row.get("date"))
    sample_end = _parse_iso_date(entry.get("sample_end") or (null_baseline or {}).get("sample_end"))
    stale = sample_end is not None and as_of is not None and sample_end != as_of
    mark = STALE_MARKER if stale else ""
    null_text = _fmt_null_baseline(entry)
    return (
        f"持續性 {persistence}{mark} {null_text}   "
        f"換手 {churn_text} ({churn_pct})   "
        f"離散 {dispersion_text} ({dispersion_pct})"
    )
