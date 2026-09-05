"""Small CLI: download, validate, analyze, brief, chart, radar, replay, refresh."""

from __future__ import annotations

import json
import webbrowser
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import typer

from marketpulse import RANK_DISCLOSURE, REPLAY_DISCLOSURE, __version__
from marketpulse.calc import (
    DataGapError,
    check_data_gaps,
    compute_snapshots,
    compute_stock_metrics,
    replay_snapshots,
    snapshots_equal,
)
from marketpulse.baskets import compute_basket_metrics, render_basket_panel
from marketpulse.data import (
    coverage_report,
    download_range,
    last_complete_session,
    last_raw_attempt,
    normalize_all,
    parse_yyyymmdd,
    read_normalized,
    validate_normalized,
    write_normalized,
)
from marketpulse.narratives import load_as_of
from marketpulse.product import (
    chart_window,
    default_chart_path,
    effective_rank_period,
    render_brief,
    render_persistence_chart,
    render_timeline,
)
from marketpulse.quality import (
    MARKET_COLUMNS,
    NULL_TEST_ITER,
    compute_market_quality,
    load_null_baseline,
    null_baseline_path,
    persistence_null_test,
    write_null_baseline,
)
from marketpulse.radar import RADAR_HTML_NAME, render_radar, write_radar_html
from marketpulse.themes import load_themes

app = typer.Typer(no_args_is_help=True, help="MarketPulse: Taiwan theme-rotation radar")

DEFAULT_DATA = Path("data")
DEFAULT_THEMES = Path("themes/v1.yaml")
DEFAULT_REPORTS = Path("reports")


def _parse_date(value: str) -> date:
    text = value.strip()
    if "/" in text or len(text) == 8 and text.isdigit():
        return parse_yyyymmdd(text.replace("-", "").replace("/", ""))
    return datetime.strptime(text, "%Y-%m-%d").date()


def _load_snapshot(data_dir: Path) -> pd.DataFrame:
    path = data_dir / "snapshots" / "theme_daily.parquet"
    if not path.exists():
        raise FileNotFoundError("snapshot missing; run analyze first")
    frame = pd.read_parquet(path)
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    return frame


def _write_snapshot_meta(
    parquet_path: Path,
    *,
    classification_version: str,
    rows: int,
    as_of: date | None = None,
) -> Path:
    """Tiny provenance next to the parquet. Not an immutable ledger."""
    meta_path = parquet_path.with_name(parquet_path.stem + ".meta.json")
    payload: dict[str, object] = {
        "classification_version": classification_version,
        "algorithm_version": __version__,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rows": rows,
    }
    if as_of is not None:
        payload["as_of"] = as_of.isoformat()
    meta_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return meta_path


def _write_snapshot(
    data_dir: Path,
    snapshot: pd.DataFrame,
    *,
    classification_version: str,
) -> Path:
    path = data_dir / "snapshots" / "theme_daily.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    snapshot.to_parquet(path, index=False)
    as_of = max(snapshot["date"]) if not snapshot.empty else None
    _write_snapshot_meta(
        path,
        classification_version=classification_version,
        rows=len(snapshot),
        as_of=as_of,
    )
    return path


def _write_market_daily(
    data_dir: Path,
    market: pd.DataFrame,
    *,
    classification_version: str,
) -> Path:
    """Sibling of _write_snapshot for market_daily.parquet (spec 001 DO-2,
    unresolved question 1). classification_version is required in the meta:
    the three quality stats are derived from theme_daily, so they shift with
    the theme YAML."""
    path = data_dir / "snapshots" / "market_daily.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    market.to_parquet(path, index=False)
    as_of = max(market["date"]) if not market.empty else None
    _write_snapshot_meta(
        path,
        classification_version=classification_version,
        rows=len(market),
        as_of=as_of,
    )
    return path


def _load_market_daily(data_dir: Path) -> pd.DataFrame:
    path = data_dir / "snapshots" / "market_daily.parquet"
    if not path.exists():
        return pd.DataFrame(columns=MARKET_COLUMNS)
    frame = pd.read_parquet(path)
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    return frame


def _market_row(market: pd.DataFrame, as_of: date) -> pd.Series | None:
    day = market.loc[market["date"] == as_of]
    if day.empty:
        return None
    return day.iloc[0]


def _load_null_baseline(data_dir: Path) -> dict | None:
    return load_null_baseline(null_baseline_path(data_dir))


def format_ops_status(
    data_dir: Path,
    *,
    chart_path: Path | None = None,
    effective: tuple[date, date] | None = None,
) -> str:
    attempt = last_raw_attempt(data_dir)
    snap_path = data_dir / "snapshots" / "theme_daily.parquet"
    as_of = last_complete_session(data_dir)
    if snap_path.exists():
        frame = _load_snapshot(data_dir)
        if not frame.empty:
            as_of = max(frame["date"])
    lines: list[str] = []
    if attempt is None:
        lines.append("raw last attempt: none")
    else:
        caught_up = bool(attempt["usable"] and as_of is not None and attempt["date"] == as_of)
        suffix = "" if caught_up else "  (will retry)"
        lines.append(
            f"raw last attempt: {attempt['date'].isoformat()}  "
            f"twse={attempt['twse']}  tpex={attempt['tpex']}{suffix}"
        )
    lines.append(f"bars/snapshot as_of: {as_of.isoformat() if as_of else 'none'}")
    if chart_path is None or effective is None:
        lines.append("chart: skipped (no ranked rows)")
    else:
        lines.append(
            f"chart: {chart_path}  "
            f"effective {effective[0].isoformat()} → {effective[1].isoformat()}"
        )
    return "\n".join(lines)


def _run_validate(data_dir: Path) -> None:
    bars, index = normalize_all(data_dir)
    write_normalized(data_dir, bars, index)
    typer.echo(coverage_report(bars, index))
    issues = validate_normalized(bars, index)
    if issues:
        typer.echo("ISSUES:")
        for issue in issues:
            typer.echo(f"  - {issue}")
        raise typer.Exit(code=1)
    typer.echo("validate: ok")


def _raw_session_dates(data_dir: Path, market: str) -> set[date]:
    raw_dir = data_dir / "raw" / market
    if not raw_dir.exists():
        return set()
    out: set[date] = set()
    for path in raw_dir.glob("*.json"):
        try:
            out.add(parse_yyyymmdd(path.stem))
        except ValueError:
            continue
    return out


def _run_analyze(data_dir: Path, themes_path: Path) -> pd.DataFrame:
    themes = load_themes(themes_path)
    bars, index = read_normalized(data_dir)
    # DO-3 (sprint 004): refuse to compute rolling windows across a data hole.
    try:
        check_data_gaps(
            bars,
            index,
            raw_twse_dates=_raw_session_dates(data_dir, "twse"),
            raw_tpex_dates=_raw_session_dates(data_dir, "tpex"),
        )
    except DataGapError as exc:
        typer.echo(f"data gap: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    snapshot = compute_snapshots(bars, index, themes)
    path = _write_snapshot(
        data_dir,
        snapshot,
        classification_version=themes.classification_version,
    )
    typer.echo(
        f"wrote {path}  rows={len(snapshot)}  "
        f"themes={snapshot['theme_id'].nunique()}  "
        f"classification={themes.classification_version}"
    )
    typer.echo(REPLAY_DISCLOSURE)
    market = compute_market_quality(snapshot)
    market_path = _write_market_daily(
        data_dir,
        market,
        classification_version=themes.classification_version,
    )
    typer.echo(f"wrote {market_path}  rows={len(market)}")
    return snapshot


def _run_chart(
    snapshot: pd.DataFrame,
    *,
    start: date | None,
    end: date | None,
    output: Path | None,
    reports_dir: Path,
) -> tuple[Path | None, tuple[date, date] | None]:
    window = chart_window(snapshot, start, end)
    try:
        eff_lo, eff_hi = effective_rank_period(window)
    except ValueError:
        return None, None
    dest = default_chart_path(reports_dir, start, output)
    if dest is None:
        dest = reports_dir / f"rotation_{eff_lo.isoformat()}_{eff_hi.isoformat()}.png"
    render_timeline(window, dest)
    return dest, (eff_lo, eff_hi)


def _run_radar(
    snapshot: pd.DataFrame,
    data_dir: Path,
    themes_path: Path,
    as_of: date,
    reports_dir: Path,
    output: Path | None = None,
) -> Path:
    themes = load_themes(themes_path)
    bars, index = read_normalized(data_dir)
    stocks = compute_stock_metrics(bars, index, themes, as_of)
    market_row = _market_row(_load_market_daily(data_dir), as_of)
    dest = output if output is not None else reports_dir / RADAR_HTML_NAME
    write_radar_html(
        snapshot,
        stocks,
        as_of,
        dest,
        market_row,
        null_baseline=_load_null_baseline(data_dir),
    )
    return dest


@app.command()
def download(
    start: str = typer.Option(..., help="YYYY-MM-DD"),
    end: str = typer.Option(..., help="YYYY-MM-DD"),
    data_dir: Path = typer.Option(DEFAULT_DATA),
    force: bool = typer.Option(False, help="re-fetch even if raw JSON exists"),
) -> None:
    """Fetch official dated TWSE + TPEx EOD JSON. Does not pull a paid feed."""
    frame = download_range(_parse_date(start), _parse_date(end), data_dir, force=force)
    typer.echo(f"downloaded {len(frame)} weekday requests")


@app.command()
def validate(
    data_dir: Path = typer.Option(DEFAULT_DATA),
) -> None:
    """Parse raw JSON, write parquet, print coverage. Never silently drop rows."""
    _run_validate(data_dir)


@app.command()
def analyze(
    data_dir: Path = typer.Option(DEFAULT_DATA),
    themes_path: Path = typer.Option(DEFAULT_THEMES),
) -> None:
    """Compute equal-weight theme return, RS20, rank, value share, breadth."""
    _run_analyze(data_dir, themes_path)


@app.command(name="validate-signal")
def validate_signal(
    k: int = typer.Option(20, help="lag in trading sessions"),
    n_iter: int = typer.Option(NULL_TEST_ITER, help="null-distribution draws"),
    seed: int = typer.Option(0, help="RNG seed (fixed default: reproducible by default)"),
    data_dir: Path = typer.Option(DEFAULT_DATA),
    reports_dir: Path = typer.Option(DEFAULT_REPORTS),
) -> None:
    """Circular-shift null test: is rank_persistence_k distinguishable from
    noise? A one-off diagnostic (spec 002 DO-1) - not part of `refresh`, since
    it doesn't change day to day the way the daily snapshot does. Reports
    numbers only; no "signal"/"noise" verdict (contract D10). Persists the
    result beside the daily data for Brief/radar (spec 003 DO-1)."""
    snapshot = _load_snapshot(data_dir)
    # R2 / §7: this uses frozen current membership applied historically —
    # restated, not as-of. Disclosure must appear in the command output itself.
    typer.echo(
        "restated (frozen membership applied historically; not as-of / point-in-time)"
    )
    try:
        result = persistence_null_test(snapshot, k=k, n_iter=n_iter, seed=seed)
    except ValueError as exc:
        typer.echo(str(exc))
        existing = null_baseline_path(data_dir)
        if existing.exists():
            typer.echo(
                f"existing baseline file is now stale/invalid for k={k}: {existing} "
                "- this run could not refresh it, so any entry it holds for this k "
                "was computed by a method no longer trusted; delete it "
                "(data/processed/ is gitignored - local action, not tracked)"
            )
        raise typer.Exit(code=1) from exc
    sample_start = min(snapshot["date"])
    sample_end = max(snapshot["date"])
    out_path = write_null_baseline(
        null_baseline_path(data_dir),
        result,
        sample_start=sample_start,
        sample_end=sample_end,
    )
    sigma = result["sigma"]
    sigma_text = "n/a" if sigma is None or pd.isna(sigma) else f"{sigma:+.2f}σ"
    typer.echo(
        f"k={result['k']}  observed={result['observed']:.4f}  "
        f"n_days_used={result['n_days_used']}  "
        f"null_mean={result['null_mean']:.4f}  null_std={result['null_std']:.4f}  "
        f"null>=obs={result['n_ge_observed']}/{result['n_iter']}  dist={sigma_text}  "
        f"seed={result['seed']}  "
        f"n_candidates={result['n_candidates']}  "
        f"retained_fraction={result['retained_fraction']:.2%}  "
        f"sample={sample_start.isoformat()}→{sample_end.isoformat()}"
    )
    typer.echo(f"wrote {out_path}")
    market = _load_market_daily(data_dir)
    column = f"rank_persistence_{k}"
    if column not in market.columns or market[column].notna().sum() == 0:
        typer.echo(f"no {column} in market_daily.parquet; run analyze first")
        raise typer.Exit(code=1)
    dest = reports_dir / f"persistence_{k}.png"
    render_persistence_chart(market, dest, k=k)
    typer.echo(str(dest))


@app.command()
def brief(
    as_of: str | None = typer.Option(None, help="YYYY-MM-DD; default = latest snapshot date"),
    data_dir: Path = typer.Option(DEFAULT_DATA),
) -> None:
    snapshot = _load_snapshot(data_dir)
    day = _parse_date(as_of) if as_of else max(snapshot["date"])
    market_row = _market_row(_load_market_daily(data_dir), day)
    typer.echo(
        render_brief(
            snapshot,
            day,
            market_row,
            null_baseline=_load_null_baseline(data_dir),
        ),
        nl=False,
    )


@app.command()
def radar(
    as_of: str | None = typer.Option(None, help="YYYY-MM-DD; default = latest snapshot date"),
    data_dir: Path = typer.Option(DEFAULT_DATA),
    themes_path: Path = typer.Option(DEFAULT_THEMES),
    output: Path | None = typer.Option(None, help="HTML path; default reports/radar.html"),
    open_browser: bool = typer.Option(False, "--open", help="open the HTML radar in a browser"),
) -> None:
    """Sector ranking table + stock drill-down HTML. Rank is still RS20."""
    snapshot = _load_snapshot(data_dir)
    day = _parse_date(as_of) if as_of else max(snapshot["date"])
    market_row = _market_row(_load_market_daily(data_dir), day)
    null_baseline = _load_null_baseline(data_dir)
    typer.echo(
        render_radar(snapshot, day, market_row, null_baseline=null_baseline),
        nl=False,
    )
    dest = _run_radar(snapshot, data_dir, themes_path, day, DEFAULT_REPORTS, output)
    typer.echo(str(dest))
    if open_browser:
        webbrowser.open(dest.resolve().as_uri())


@app.command()
def chart(
    start: str | None = typer.Option(None),
    end: str | None = typer.Option(None),
    data_dir: Path = typer.Option(DEFAULT_DATA),
    output: Path | None = typer.Option(None),
) -> None:
    """Default: last 40 ranked sessions → reports/rotation_latest.png."""
    snapshot = _load_snapshot(data_dir)
    lo = _parse_date(start) if start else None
    hi = _parse_date(end) if end else None
    dest, effective = _run_chart(
        snapshot,
        start=lo,
        end=hi,
        output=output,
        reports_dir=DEFAULT_REPORTS,
    )
    if dest is None or effective is None:
        typer.echo("no ranked rows in this window (RS20 needs 20 trading days)")
        raise typer.Exit(code=1)
    typer.echo(str(dest))
    typer.echo(f"effective RS20 period: {effective[0].isoformat()} → {effective[1].isoformat()}")
    typer.echo(REPLAY_DISCLOSURE)
    typer.echo(RANK_DISCLOSURE)
    typer.echo(format_ops_status(data_dir, chart_path=dest, effective=effective))


@app.command()
def refresh(
    start: str | None = typer.Option(None, help="default = day after last complete session"),
    end: str | None = typer.Option(None, help="default = today"),
    data_dir: Path = typer.Option(DEFAULT_DATA),
    themes_path: Path = typer.Option(DEFAULT_THEMES),
) -> None:
    """Download trailing days, validate, analyze, Brief, latest chart, radar HTML."""
    hi = _parse_date(end) if end else date.today()
    if start:
        lo = _parse_date(start)
    else:
        last = last_complete_session(data_dir)
        if last is None:
            typer.echo("no normalized bars; pass --start YYYY-MM-DD")
            raise typer.Exit(code=1)
        lo = last + timedelta(days=1)
    if lo <= hi:
        frame = download_range(lo, hi, data_dir)
        typer.echo(f"downloaded {len(frame)} weekday requests")
    else:
        typer.echo(f"already current through {hi.isoformat()}; skip download")
    _run_validate(data_dir)
    snapshot = _run_analyze(data_dir, themes_path)
    if snapshot.empty:
        typer.echo("no snapshot rows")
        raise typer.Exit(code=1)
    day = max(snapshot["date"])
    market_row = _market_row(_load_market_daily(data_dir), day)
    null_baseline = _load_null_baseline(data_dir)
    typer.echo(
        render_brief(snapshot, day, market_row, null_baseline=null_baseline),
        nl=False,
    )
    dest, effective = _run_chart(
        snapshot,
        start=None,
        end=None,
        output=None,
        reports_dir=DEFAULT_REPORTS,
    )
    if dest is not None and effective is not None:
        typer.echo(str(dest))
        typer.echo(f"effective RS20 period: {effective[0].isoformat()} → {effective[1].isoformat()}")
        typer.echo(REPLAY_DISCLOSURE)
        typer.echo(RANK_DISCLOSURE)
    typer.echo(
        render_radar(snapshot, day, market_row, null_baseline=null_baseline),
        nl=False,
    )
    radar_path = _run_radar(snapshot, data_dir, themes_path, day, DEFAULT_REPORTS)
    typer.echo(str(radar_path))
    typer.echo(format_ops_status(data_dir, chart_path=dest, effective=effective))


@app.command()
def baskets(
    as_of: str | None = typer.Option(None, help="YYYY-MM-DD; default = last complete session"),
    data_dir: Path = typer.Option(DEFAULT_DATA),
    narratives_dir: Path = typer.Option(Path("narratives")),
) -> None:
    """Strength panel for every live branch basket (sprint 004 DO-2).

    One line per basket: member count, RS5/RS20/RS60, breadth, value_share.
    Reads price/volume only; writes nothing. Not a rank, not a score — baskets
    print in the order the narratives list them (contract R1 / R3).
    """
    bars, index = read_normalized(data_dir)
    try:
        check_data_gaps(
            bars,
            index,
            raw_twse_dates=_raw_session_dates(data_dir, "twse"),
            raw_tpex_dates=_raw_session_dates(data_dir, "tpex"),
        )
    except DataGapError as exc:
        typer.echo(f"data gap: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    if as_of:
        day = _parse_date(as_of)
    else:
        day = last_complete_session(data_dir)
        if day is None:
            typer.echo("no complete session in normalized data; pass --as-of", err=True)
            raise typer.Exit(code=1)

    snapshot = load_as_of(day, narratives_dir)
    live = [
        (n.narrative_id, b)
        for n in snapshot.narratives
        for b in n.branches
        if b.status == "live"
    ]
    rows = compute_basket_metrics(bars, index, live, day)
    typer.echo(render_basket_panel(rows, day), nl=False)


@app.command()
def replay(
    start: str = typer.Option(...),
    end: str = typer.Option(...),
    data_dir: Path = typer.Option(DEFAULT_DATA),
    themes_path: Path = typer.Option(DEFAULT_THEMES),
) -> None:
    """As-of replay. data <= T. Prints visualization-replay disclosure."""
    themes = load_themes(themes_path)
    bars, index = read_normalized(data_dir)
    lo, hi = _parse_date(start), _parse_date(end)
    first = replay_snapshots(bars, index, themes, lo, hi)
    second = replay_snapshots(bars, index, themes, lo, hi)
    dest = data_dir / "snapshots" / f"replay_{lo.isoformat()}_{hi.isoformat()}.parquet"
    dest.parent.mkdir(parents=True, exist_ok=True)
    first.to_parquet(dest, index=False)
    as_of = max(first["date"]) if not first.empty else None
    _write_snapshot_meta(
        dest,
        classification_version=themes.classification_version,
        rows=len(first),
        as_of=as_of,
    )
    typer.echo(REPLAY_DISCLOSURE)
    typer.echo(RANK_DISCLOSURE)
    typer.echo(f"wrote {dest}  rows={len(first)}")
    if not snapshots_equal(first, second):
        typer.echo("replay is not deterministic")
        raise typer.Exit(code=1)
    typer.echo("replay deterministic: ok")
    snap_path = data_dir / "snapshots" / "theme_daily.parquet"
    if snap_path.exists():
        stored = _load_snapshot(data_dir)
        window = stored[(stored["date"] >= lo) & (stored["date"] <= hi)]
        if snapshots_equal(first, window):
            typer.echo("matches analyze snapshot: ok")
        else:
            typer.echo("WARNING: replay differs from analyze snapshot")


@app.command()
def version() -> None:
    typer.echo(__version__)
