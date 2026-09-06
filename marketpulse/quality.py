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
# Fixed B+C horizon reading (spec 005 DO-3). Locked Chinese string — do not
# rewrite from IC / persistence magnitude (D10).
HORIZON_FOOTNOTE = "月尺度：可偵測≠穩定；短端遠強於長端；凍結成分偏高估（D6）。"
# spec 010 DO-1 item 3: HORIZON_FOOTNOTE carries a bare "（D6）" with nothing
# on screen to resolve it. This line spells it out in plain language so a
# reader does not have to open docs/product/non-goals.md. Not a verdict, not
# a threshold — a fixed gloss, printed right after HORIZON_FOOTNOTE whenever
# that note is printed.
D6_GLOSS = "D6：持續性是在凍結成分股（非 as-of 成分）上量的，這個偏誤的方向是高估。"
# spec 010 DO-1 item 2: the STALE_MARKER (†) on the persistence digit had no
# footnote. This explains it: the whole persistence group was measured
# through the baseline's sample_end, which is not today. {sample_end} is that
# date when known.
DAGGER_NOTE_TEMPLATE = (
    "† 持續性這一組（觀測值與虛無、σ、超出次數）量到 {sample_end}"
    "（baseline sample_end）為止，不是今天"
)
DAGGER_NOTE_NO_DATE = "† 持續性這一組量到 baseline sample_end 為止，不是今天"
# spec 010 DO-1 item 4: with no usable null baseline the persistence slot used
# to print the lone daily rank_persistence_20 — the misleading no-corroboration
# value 008 B6 removed elsewhere. Print this instead.
NO_BASELINE_TEXT = "無基準"
# spec 010 DO-1 item 1: each parenthetical percentile is a position within the
# trailing PERCENTILE_WINDOW sessions (quality.py:_percentile is
# rolling(PERCENTILE_WINDOW).rank(pct=True)). Say so, and say which way it
# points — no conditional wording, no threshold (D10 red line).
PERCENTILE_WINDOW_LABEL = f"近 {PERCENTILE_WINDOW} 個交易日"
CHURN_PCT_DIRECTION = "越高＝名次相對前一交易日洗牌越多"
DISPERSION_PCT_DIRECTION = "越低＝族群名次越擠、當日名次差異的資訊量越低"
NULL_BASELINE_FILENAME = "signal_quality_null.json"
DISPLAY_NULL_K = 20  # quality_line shows persistence_20; pair with k=20 null
NULL_METHOD_VERSION = 1
"""Identifies the null-sampling *method* a stored by_k entry was computed
with - not when it was written (DO-6, sprint 003). Bump this whenever
persistence_null_test's sampling or its guards change in a way that
changes what the output means (a new algorithm, a new rejection rule) -
not for cosmetic changes. An entry whose method_version doesn't match
(including one missing the field entirely, i.e. every file written before
DO-6) is a different measurement, not an old one: STALE_MARKER only
answers "is this current", this answers "was this computed by a method we
still stand behind". Freshness and validity are different questions - see
_null_entry_for_display, which is where a mismatch turns into "treat as
absent" rather than "print it with a warning tag" - an invalid number
doesn't earn screen space just because it's labeled (D10)."""

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


def _null_min_lag(k: int) -> int:
    """Minimum |effective lag| let into persistence_null_test's null.

    ``max(2*k, 60)``. The 60 floor is PERCENTILE_WINDOW, this module's
    existing stand-in for "a trading quarter" (already used above for the
    rolling percentile windows) - reused here rather than picked to make
    any particular k's percentile look better (contract D10: constants need
    a market/statistical reason, not a fitted one). The ``2*k`` term makes
    the excluded band strictly wider than the lag under test itself, which
    is what guarantees it also excludes effective lag -k - see
    persistence_null_test's docstring for why that shift matters too, not
    just effective lag 0.
    """
    return max(2 * k, PERCENTILE_WINDOW)


MIN_RETAINED_FRACTION = 0.5
"""persistence_null_test refuses to run below this fraction of the shift
circle retained as candidates (DO-5, sprint 003). 1/2: below half the
circle, the excluded near-lag band is *larger* than what's left, so the
null is built from a minority arc rather than a representative majority of
possible alignments - exactly the DO-4 failure mode (161 sessions kept
only 26% of the circle, all far shifts, and every k's percentile came back
100.0 regardless of how large the observed statistic actually was). This
is a property of the candidate set's shape (a majority-vs-minority split),
not a value fitted to any particular k's output - it does not change
_null_min_lag's L, only whether persistence_null_test proceeds at all for
a given (n, k)."""


def _null_shift_candidates(n: int, k: int, lag_l: int) -> np.ndarray:
    """Valid effective lags e for persistence_null_test's circular shift.

    e is the offset applied to every row's own position: partner_index =
    (current_index + e) mod n. Candidates are the full circle of distinct
    shifts, canonically e in [-(n//2), n//2] (each represents one wrap
    direction; circular distance for e in this range is |e| itself, since
    |e| <= n//2 <= n-|e|), minus the band |e| < lag_l.
    """
    half = n // 2
    e = np.arange(-half, half + 1)
    return e[np.abs(e) >= lag_l]


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

    Null: for each of n_iter draws, pick a random effective lag e (see
    _null_shift_candidates) and recompute the same mean pairing rank[T]
    with rank[(T+e) mod n] in place of rank[T-k]. Circular shift keeps each
    side's own autocorrelation intact and only scrambles the alignment
    between them - unlike an i.i.d. shuffle of rows, which would also
    destroy real day-to-day continuity and understate the null's spread
    (this is the standard technique for testing association between two
    autocorrelated series).

    e is restricted to |e| >= L = _null_min_lag(k) (DO-4, sprint 003). Two
    prior sprints (002 DO-1, `c2aaefe`; 003 unchanged) instead sampled a
    shift s from [k, n-k) with partner = rank[(T-k+s) mod n], i.e. e = s-k
    ranging over [0, n-2k). That range includes e=0 (s=k, its own lower
    bound): partner_index == current_index there, so every such draw is a
    self-comparison with corr(x, x) == 1.0 by construction, not a random
    pairing at all. Its neighbourhood (e near 0) inherits whatever real
    short-lag persistence the series has, biasing the null's right tail up
    and every reported percentile down. (A since-corrected docstring claimed
    the coincidence was at the range's ends, "never close to 0 or n" - that
    reasoning had it backwards: e=-k, i.e. s=0, is what reproduces the real
    unshifted lag-k pairing the observed statistic itself uses; e=0, i.e.
    s=k, is the self-comparison. s=0 was already excluded by the old range;
    s=k sat right at its edge.) L=max(2k, 60) is wide enough to exclude both
    e=0 and e=-k, plus every shift in between that would still read as
    "nearly the real pairing" to an autocorrelated series.

    This is explicitly a research statistic, unlike the T-vs-T-k-only
    display values elsewhere in this module (contract R2 red line): building
    the null intentionally uses a wraparound that a live per-day value never
    would, purely to construct a comparison distribution.

    L does not scale with n (DO-5, sprint 003): on a short sample it can
    exclude most of the shift circle, leaving only a handful of far-apart
    candidates. That is not merely a smaller null - it's a *biased* one
    (the retained shifts are all "far", none "medium", so the null mean
    drifts away from 0 and its spread collapses), and it fails silently: a
    161-session sample once retained only 26% of the circle and returned
    percentile 100.0 for k=1, 5, and 20 alike, regardless of how different
    their observed statistics actually were. See MIN_RETAINED_FRACTION -
    below that retained share, this function raises instead of returning a
    number that looks confident but measures the sample length, not the
    series.
    """
    ranks = _pivot(snapshot, "rank")
    n = len(ranks)
    lag_l = _null_min_lag(k)
    candidates = _null_shift_candidates(n, k, lag_l)
    retained_fraction = candidates.size / n if n else 0.0
    if retained_fraction < MIN_RETAINED_FRACTION:
        raise ValueError(
            f"sample too short to support a null test at k={k}: retained "
            f"{candidates.size}/{n} ({retained_fraction:.0%}) of the shift "
            f"circle, need >= {MIN_RETAINED_FRACTION:.0%} (L={lag_l}); "
            "this sample length cannot support a null test at this k"
        )

    values = ranks.to_numpy(dtype=float)
    positions = np.arange(k, n)
    current = values[positions]
    observed_terms = _row_wise_pearson(current, values[positions - k])
    n_days_used = int(np.count_nonzero(~np.isnan(observed_terms)))
    observed = float(np.nanmean(observed_terms)) if n_days_used else float("nan")

    rng = np.random.default_rng(seed)
    null_values = np.full(n_iter, np.nan)
    for i in range(n_iter):
        e = int(rng.choice(candidates))
        partner = values[(positions + e) % n]
        terms = _row_wise_pearson(current, partner)
        if np.any(~np.isnan(terms)):
            null_values[i] = np.nanmean(terms)

    valid_null = null_values[~np.isnan(null_values)]
    null_mean = float(np.mean(valid_null)) if len(valid_null) else float("nan")
    null_std = float(np.std(valid_null, ddof=1)) if len(valid_null) > 1 else float("nan")
    have_obs = bool(len(valid_null)) and pd.notna(observed)
    percentile = float((valid_null < observed).mean() * 100) if have_obs else float("nan")
    # Report these instead of percentile at the display layer (sprint 004
    # follow-up): a percentile saturates at 100 the moment the observed
    # statistic clears every draw, which is exactly what a degenerate
    # DO-5-style null also does - a reader can't tell the two apart. A raw
    # exceedance count and a distance in null standard deviations both keep
    # discriminating past that point. percentile stays in the dict / JSON.
    n_ge_observed = int(np.sum(valid_null >= observed)) if have_obs else 0
    sigma = (
        float((observed - null_mean) / null_std)
        if have_obs and pd.notna(null_std) and null_std > 0
        else float("nan")
    )

    return {
        "k": k,
        "observed": observed,
        "n_days_used": n_days_used,
        "null_mean": null_mean,
        "null_std": null_std,
        "percentile": percentile,
        "n_ge_observed": n_ge_observed,
        "sigma": sigma,
        "n_iter": int(len(valid_null)),
        "seed": seed,
        "n_candidates": int(candidates.size),
        "retained_fraction": retained_fraction,
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


def _fmt_ordinal_pct(value: object) -> str:
    """`第 N 百分位` for a 0..1 rolling-rank percentile (spec 010 DO-1 item 1).

    Same input as _fmt_pct — the trailing-window position from _percentile —
    just phrased as an ordinal so the parenthetical reads as a rank, not a
    second measurement of the value beside it.
    """
    if value is None or pd.isna(value):
        return "百分位 n/a"
    return f"第 {int(round(float(value) * 100))} 百分位"


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
        "method_version": NULL_METHOD_VERSION,
        "observed": result["observed"],
        "null_mean": result["null_mean"],
        "null_std": result["null_std"],
        "percentile": result["percentile"],
        "n_ge_observed": result.get("n_ge_observed"),
        "sigma": result.get("sigma"),
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


def _entry_method_current(entry: dict) -> bool:
    """DO-6: an entry computed by a method this codebase no longer stands
    behind (including one with no method_version at all - every file
    written before DO-6) is not a display candidate, regardless of how
    fresh its sample_end is."""
    return entry.get("method_version") == NULL_METHOD_VERSION


def _entry_sample_matches_file(entry: dict, payload: dict) -> bool:
    """sprint 004 follow-up: by_k entries can be left over from earlier,
    shorter samples while the file's top-level sample_start/sample_end has
    been overwritten by a later run for a different k. Such an entry is not
    from the sample the file claims to describe, so it is not a display
    candidate - same treatment as a rejected method_version (DO-6), routed
    through the same "treat as absent" path, not a new display state."""
    return (
        str(entry.get("sample_start")) == str(payload.get("sample_start"))
        and str(entry.get("sample_end")) == str(payload.get("sample_end"))
    )


def _null_entry_for_display(payload: dict | None, k: int = DISPLAY_NULL_K) -> dict | None:
    if not payload:
        return None

    def _ok(entry: dict) -> dict | None:
        return (
            entry
            if _entry_method_current(entry) and _entry_sample_matches_file(entry, payload)
            else None
        )

    by_k = payload.get("by_k")
    if isinstance(by_k, dict):
        entry = by_k.get(str(k))
        if isinstance(entry, dict):
            return _ok(entry)
    # tolerate a flat single-result file
    if payload.get("k") == k or str(payload.get("k")) == str(k):
        return _ok(payload)
    return None


def _fmt_sigma(value: object) -> str:
    if value is None or pd.isna(value):
        return "n/aσ"
    return f"{float(value):+.1f}σ"


def _fmt_exceedance(entry: dict) -> str:
    n_ge = entry.get("n_ge_observed")
    n_iter = entry.get("n_iter")
    if n_ge is None or n_iter is None or pd.isna(n_ge) or pd.isna(n_iter):
        return "n/a"
    return f"{int(n_ge)}/{int(n_iter)}"


def _fmt_null_baseline(entry: dict) -> str:
    """Pure numbers for the null reference — no adjectives (D10). Distance in
    null σ and a raw exceedance count, not a percentile: the percentile
    saturates at 100 and then can't be told apart from a degenerate null
    (sprint 004 follow-up)."""
    mean = _fmt_corr(entry.get("null_mean"))
    std = _fmt_corr(entry.get("null_std"))
    return f"虛無 {mean}±{std} {_fmt_sigma(entry.get('sigma'))} {_fmt_exceedance(entry)}"


def quality_line(
    market_row: pd.Series | None,
    *,
    null_baseline: dict | None = None,
    snapshot_as_of: date | None = None,
    oneline: bool = False,
) -> str:
    """Signal-quality readout: numbers/percentiles plus fixed horizon note.

    No verdict, no threshold-based label (D10 / acceptance 5) — the reader
    judges. Uses rank_persistence_20 rather than rank_persistence_1: the
    1-day lag answers the same question as rank_churn (today vs. yesterday),
    so pairing them would spend two of the three slots on one thing. The 20
    lag gives the line three genuinely different scales instead.

    When ``null_baseline`` (from validate-signal) is present, the persistence
    digit is that k=20 entry's ``observed`` (mean over T of corr(...)), not
    the daily ``rank_persistence_20``. null_mean / null_std / sigma /
    n_ge_observed come from the same entry (spec 009 DO-1). Daily
    rank_persistence_20 stays in market_daily.parquet; it is not printed
    here. If the entry's sample_end differs from ``snapshot_as_of`` (or
    market_row's date), appends STALE_MARKER (†) after the observed
    persistence — the marker means "this whole set was measured through
    sample_end, which is not as_of" — and a DAGGER_NOTE line spelling that
    out (spec 010 DO-1 item 2). With no usable baseline the persistence slot
    prints NO_BASELINE_TEXT (`無基準`), never the lone daily value
    (spec 010 DO-1 item 4).

    Each parenthetical percentile is written as a position within the
    trailing PERCENTILE_WINDOW sessions, with its direction (spec 010 DO-1
    item 1) — no conditional wording, no threshold.

    Whenever ``market_row`` is present, appends HORIZON_FOOTNOTE and then
    D6_GLOSS (spec 005 DO-3 / spec 010 DO-1 item 3). Absent when market_row
    is None.

    ``oneline`` keeps the three metric groups on one physical line instead
    of one per line; the footnote lines are unaffected. Layout only — spec
    010 open question 1, default expanded per its 拍板.
    """
    if market_row is None:
        # A2: no row → the original three-n/a line, nothing appended.
        return "持續性 n/a   換手 n/a   離散 n/a"
    churn = market_row.get("rank_churn")
    churn_text = "n/a" if churn is None or pd.isna(churn) else f"{int(round(float(churn)))}"
    churn_seg = (
        f"換手 {churn_text}"
        f"（{PERCENTILE_WINDOW_LABEL}{_fmt_ordinal_pct(market_row.get('rank_churn_pct'))}"
        f"；{CHURN_PCT_DIRECTION}）"
    )
    dispersion_text = _fmt_pp(market_row.get("dispersion"))
    dispersion_seg = (
        f"離散 {dispersion_text}"
        f"（{PERCENTILE_WINDOW_LABEL}{_fmt_ordinal_pct(market_row.get('dispersion_pct'))}"
        f"；{DISPERSION_PCT_DIRECTION}）"
    )

    entry = _null_entry_for_display(null_baseline, DISPLAY_NULL_K)
    dagger_note: str | None = None
    if entry is None:
        persistence_seg = f"持續性 {NO_BASELINE_TEXT}"
    else:
        persistence = _fmt_corr(entry.get("observed"))
        as_of = snapshot_as_of
        if as_of is None:
            as_of = _parse_iso_date(market_row.get("date"))
        sample_end = _parse_iso_date(
            entry.get("sample_end") or (null_baseline or {}).get("sample_end")
        )
        stale = sample_end is not None and as_of is not None and sample_end != as_of
        mark = STALE_MARKER if stale else ""
        persistence_seg = f"持續性 {persistence}{mark} {_fmt_null_baseline(entry)}"
        if stale:
            dagger_note = (
                DAGGER_NOTE_TEMPLATE.format(sample_end=sample_end.isoformat())
                if sample_end is not None
                else DAGGER_NOTE_NO_DATE
            )

    if oneline:
        lines = [f"{persistence_seg}   {churn_seg}   {dispersion_seg}"]
    else:
        lines = [persistence_seg, churn_seg, dispersion_seg]
    if dagger_note is not None:
        lines.append(dagger_note)
    lines.append(HORIZON_FOOTNOTE)
    lines.append(D6_GLOSS)
    return "\n".join(lines)


RANK_IC_WINDOWS = (5, 20, 60)
RANK_IC_RS_COLS = {5: "rs5", 20: "rs20", 60: "rs60"}
RANK_IC_NULL_COLUMNS = [
    "k",
    "h",
    "observed",
    "null_mean",
    "null_std",
    "sigma",
    "n_ge_observed",
    "n_iter",
    "n_days",
    "retained",
    "reason",
]
# Guard-fail wording is locked by tests (spec 006 DO-1 acceptance 5).
RANK_IC_GUARD_REASON_TEMPLATE = "retained {retained:.0%}<{threshold:.0%} (h={h} L={L})"
RANK_IC_PERSISTENCE_CELL = (20, 20)
RANK_IC_PERSISTENCE_MARK = "‡"
RANK_IC_PERSISTENCE_NOTE = "‡ 此格等同 rank_persistence_20，非獨立物證"


def _spearman_cross_section(left: pd.Series, right: pd.Series) -> float:
    """Spearman via Pearson-of-ranks (no scipy). Pairwise-complete."""
    paired = pd.concat([left, right], axis=1, keys=["a", "b"]).dropna()
    if len(paired) < 2:
        return float("nan")
    ra = paired["a"].rank()
    rb = paired["b"].rank()
    if float(ra.std()) == 0.0 or float(rb.std()) == 0.0:
        return float("nan")
    return float(ra.corr(rb, method="pearson"))


def _average_rank_rows(x: np.ndarray) -> np.ndarray:
    """pandas Series.rank(method='average', na_option='keep') per row."""
    if x.size == 0:
        return np.empty(x.shape, dtype=float)
    is_nan = np.isnan(x)
    xi = x[:, :, np.newaxis]
    xj = x[:, np.newaxis, :]
    nan_i = is_nan[:, :, np.newaxis]
    nan_j = is_nan[:, np.newaxis, :]
    valid = ~(nan_i | nan_j)
    n_less = np.sum((xj < xi) & valid, axis=2)
    n_equal = np.sum((xj == xi) & valid, axis=2)
    ranks = n_less + (n_equal + 1) / 2.0
    return np.where(is_nan, np.nan, ranks)


def _row_wise_spearman(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Batched Spearman matching ``_spearman_cross_section``.

    Pairwise-complete: a theme NaN on either side is dropped from *both*
    ranks for that row, then Pearson of those ranks. Ranking is not
    precomputed independently of the pairing — that would diverge from
    the scalar oracle whenever NaN masks differ.
    """
    if a.ndim != 2 or b.ndim != 2:
        raise ValueError("row-wise Spearman expects 2-d arrays")
    if a.shape != b.shape:
        raise ValueError("row-wise Spearman sides must have the same shape")
    if a.shape[1] == 0:
        return np.full(a.shape[0], np.nan)
    mask = ~(np.isnan(a) | np.isnan(b))
    a_m = np.where(mask, a, np.nan)
    b_m = np.where(mask, b, np.nan)
    return _row_wise_pearson(_average_rank_rows(a_m), _average_rank_rows(b_m))


def _rank_ic_terms(left: np.ndarray, right: np.ndarray, h: int, e: int = 0) -> np.ndarray:
    """Spearman(left[i], right[(i + h + e) mod n]) for i in 0..n-h-1.

    e=0 is the observed pairing (no wrap: i+h stays inside 0..n-1).
    Nonzero e circular-shifts the forward side, which is the default
    displacement side (spec 006 open question 1).
    """
    n = left.shape[0]
    if n <= h:
        return np.empty(0, dtype=float)
    i = np.arange(n - h)
    j = (i + h + e) % n
    return _row_wise_spearman(left[i], right[j])


def _mean_ic_and_n(terms: np.ndarray) -> tuple[float, int]:
    valid = terms[~np.isnan(terms)]
    n_days = int(valid.size)
    if n_days == 0:
        return float("nan"), 0
    return float(valid.mean()), n_days


def _rank_ic_rs_matrices(
    snapshot: pd.DataFrame,
    as_of: date | None,
) -> tuple[list[date], dict[int, np.ndarray]]:
    """Daily RS values as (n_days × n_themes) float arrays, NaN preserved.

    Column order is sorted theme_id so every k shares the same alignment.
    """
    if snapshot.empty:
        return [], {}
    work = snapshot.copy()
    work["date"] = pd.to_datetime(work["date"]).dt.date
    dates = sorted(work["date"].unique())
    if as_of is not None:
        dates = [d for d in dates if d <= as_of]
        work = work.loc[work["date"].isin(dates)]
    if not dates:
        return [], {}
    theme_ids = sorted(work["theme_id"].unique())
    matrices: dict[int, np.ndarray] = {}
    n_themes = len(theme_ids)
    for k, col in RANK_IC_RS_COLS.items():
        if col in work.columns:
            frame = _pivot(work, col).reindex(index=dates, columns=theme_ids)
            matrices[k] = frame.to_numpy(dtype=float)
        else:
            matrices[k] = np.full((len(dates), n_themes), np.nan)
    for k in RANK_IC_WINDOWS:
        if k not in matrices:
            matrices[k] = np.full((len(dates), n_themes), np.nan)
    return dates, matrices


def _rank_ic_guard_reason(*, h: int, retained: float, lag_l: int) -> str:
    return RANK_IC_GUARD_REASON_TEMPLATE.format(
        retained=retained,
        threshold=MIN_RETAINED_FRACTION,
        h=h,
        L=lag_l,
    )


def compute_rank_ic(
    snapshot: pd.DataFrame,
    *,
    as_of: date | None = None,
) -> pd.DataFrame:
    """Forward Rank-IC matrix: Spearman(RS_k[T], forward h-day excess[T→T+h]).

    Excess over (T, T+h] equals ``rs_h`` observed at session T+h — the same
    theme n-day return minus TAIEX n-day return already stored on the
    snapshot. Session lag is in trading days (snapshot date index), not
    calendar days. Returns one row per (k, h) with mean_ic, n_days. Pure
    numbers; no adjectives. The mean is the same statistic
    ``rank_ic_null_test`` reports as ``observed``.
    """
    cols = ["k", "h", "mean_ic", "n_days"]
    dates, matrices = _rank_ic_rs_matrices(snapshot, as_of)
    if not dates:
        return pd.DataFrame(columns=cols)

    rows: list[dict] = []
    for k in RANK_IC_WINDOWS:
        for h in RANK_IC_WINDOWS:
            terms = _rank_ic_terms(matrices[k], matrices[h], h, e=0)
            mean_ic, n_days = _mean_ic_and_n(terms)
            rows.append({"k": k, "h": h, "mean_ic": mean_ic, "n_days": n_days})
    return pd.DataFrame(rows, columns=cols)


def rank_ic_null_test(
    snapshot: pd.DataFrame,
    *,
    as_of: date | None = None,
    n_iter: int = NULL_TEST_ITER,
    seed: int | None = 0,
) -> pd.DataFrame:
    """Circular-shift null for every (k, h) Rank-IC cell.

    Observed statistic: mean over T of Spearman(RS_k[T], RS_h[T+h]), the
    same quantity ``compute_rank_ic`` stores as ``mean_ic``. Null: circular-
    shift the *forward* side by a random effective lag e drawn from
    ``_null_shift_candidates`` (same lag floor and retained-fraction guard
    as ``persistence_null_test``; L = ``_null_min_lag(h)`` because h is the
    pairing lag being scrambled) and recompute the mean.

    Cells that fail the retained-fraction guard keep the observed mean
    internally (so it still matches ``compute_rank_ic``) but carry a
    ``reason`` string; ``format_rank_ic_table`` prints n/a rather than a
    null that the sample cannot support. Does not raise — unlike
    ``persistence_null_test`` — because eight neighbouring cells may still
    be valid.

    Does not write a file. seed defaults to 0 (reproducible).
    """
    dates, matrices = _rank_ic_rs_matrices(snapshot, as_of)
    if not dates:
        return pd.DataFrame(columns=RANK_IC_NULL_COLUMNS)

    n = len(dates)
    rows: list[dict] = []
    for k in RANK_IC_WINDOWS:
        for h in RANK_IC_WINDOWS:
            left = matrices[k]
            right = matrices[h]
            terms_obs = _rank_ic_terms(left, right, h, e=0)
            observed, n_days = _mean_ic_and_n(terms_obs)

            lag_l = _null_min_lag(h)
            candidates = _null_shift_candidates(n, h, lag_l)
            retained = candidates.size / n if n else 0.0
            if retained < MIN_RETAINED_FRACTION:
                rows.append(
                    {
                        "k": k,
                        "h": h,
                        "observed": observed,
                        "null_mean": float("nan"),
                        "null_std": float("nan"),
                        "sigma": float("nan"),
                        "n_ge_observed": 0,
                        "n_iter": 0,
                        "n_days": n_days,
                        "retained": retained,
                        "reason": _rank_ic_guard_reason(
                            h=h, retained=retained, lag_l=lag_l
                        ),
                    }
                )
                continue

            rng = np.random.default_rng(seed)
            null_values = np.full(n_iter, np.nan)
            for draw in range(n_iter):
                e = int(rng.choice(candidates))
                terms = _rank_ic_terms(left, right, h, e=e)
                if np.any(~np.isnan(terms)):
                    null_values[draw] = np.nanmean(terms)

            valid_null = null_values[~np.isnan(null_values)]
            null_mean = float(np.mean(valid_null)) if len(valid_null) else float("nan")
            null_std = (
                float(np.std(valid_null, ddof=1)) if len(valid_null) > 1 else float("nan")
            )
            have_obs = bool(len(valid_null)) and pd.notna(observed)
            n_ge_observed = int(np.sum(valid_null >= observed)) if have_obs else 0
            sigma = (
                float((observed - null_mean) / null_std)
                if have_obs and pd.notna(null_std) and null_std > 0
                else float("nan")
            )
            rows.append(
                {
                    "k": k,
                    "h": h,
                    "observed": observed,
                    "null_mean": null_mean,
                    "null_std": null_std,
                    "sigma": sigma,
                    "n_ge_observed": n_ge_observed,
                    "n_iter": int(len(valid_null)),
                    "n_days": n_days,
                    "retained": retained,
                    "reason": "",
                }
            )
    return pd.DataFrame(rows, columns=RANK_IC_NULL_COLUMNS)


def _rank_ic_cell_lines(row: object) -> list[str]:
    """Four sub-lines for one (k, h) cell. Guard failures print n/a + reason."""
    reason = getattr(row, "reason", "") or ""
    n_days = int(row.n_days) if pd.notna(row.n_days) else 0
    k, h = int(row.k), int(row.h)
    mark = RANK_IC_PERSISTENCE_MARK if (k, h) == RANK_IC_PERSISTENCE_CELL else ""
    if reason:
        return [f"n/a{mark} {reason}", f"n={n_days}", "", ""]
    if pd.isna(getattr(row, "observed", np.nan)):
        return [f"n/a{mark}", f"n={n_days}", "", ""]
    obs = f"{float(row.observed):+.4f}{mark}"
    null_mean = row.null_mean
    null_std = row.null_std
    if pd.isna(null_mean) or pd.isna(null_std):
        null_line = "null n/a"
    else:
        null_line = f"null {float(null_mean):+.4f}±{float(null_std):.4f}"
    sigma = row.sigma
    sigma_text = "n/aσ" if pd.isna(sigma) else f"{float(sigma):+.2f}σ"
    dist = f"{sigma_text}  {int(row.n_ge_observed)}/{int(row.n_iter)}"
    retained = row.retained
    ret_text = "n/a" if pd.isna(retained) else f"{float(retained):.1%}"
    tail = f"n={n_days} ret={ret_text}"
    return [obs, null_line, dist, tail]


def format_rank_ic_table(frame: pd.DataFrame) -> str:
    """Plain 3×3 text table: observed IC plus circular-shift null per cell.

    Cells are joined with two spaces (spec 006 DO-3). Guard-fail cells print
    n/a and the locked reason string, not a null the sample cannot support.
    """
    lines = [
        "forward Rank-IC  Spearman(RS_k[T], excess_h[T→T+h])",
        "circular-shift null on the forward side; seed=0",
    ]
    if frame.empty:
        lines.append("n/a")
        lines.append(RANK_IC_PERSISTENCE_NOTE)
        return "\n".join(lines)

    by_kh = {(int(r.k), int(r.h)): r for r in frame.itertuples(index=False)}
    blocks: list[list[list[str]]] = []
    for k in RANK_IC_WINDOWS:
        row_cells: list[list[str]] = []
        for h in RANK_IC_WINDOWS:
            r = by_kh.get((k, h))
            if r is None:
                row_cells.append(["n/a", "", "", ""])
            else:
                row_cells.append(_rank_ic_cell_lines(r))
        blocks.append(row_cells)

    width = max(len(sub) for row in blocks for cell in row for sub in cell)
    width = max(width, 8)
    k_width = 6
    lines.append(
        "k\\h".ljust(k_width) + "  ".join(f"{h:^{width}d}" for h in RANK_IC_WINDOWS)
    )
    for k, row_cells in zip(RANK_IC_WINDOWS, blocks):
        padded = [[sub.ljust(width) for sub in cell] for cell in row_cells]
        for i in range(4):
            prefix = f"{k:<{k_width}}" if i == 0 else " " * k_width
            lines.append(prefix + "  ".join(cell[i] for cell in padded))
        lines.append("")
    lines.append(RANK_IC_PERSISTENCE_NOTE)
    return "\n".join(lines)
