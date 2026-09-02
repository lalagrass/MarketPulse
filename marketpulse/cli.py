"""Small CLI: download, validate, analyze, brief, chart, replay, refresh."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import typer

from marketpulse import RANK_DISCLOSURE, REPLAY_DISCLOSURE, __version__
from marketpulse.calc import compute_snapshots, replay_snapshots, snapshots_equal
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
from marketpulse.product import (
    chart_window,
    default_chart_path,
    effective_rank_period,
    render_brief,
    render_timeline,
)
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


def _run_analyze(data_dir: Path, themes_path: Path) -> pd.DataFrame:
    themes = load_themes(themes_path)
    bars, index = read_normalized(data_dir)
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


@app.command()
def brief(
    as_of: str | None = typer.Option(None, help="YYYY-MM-DD; default = latest snapshot date"),
    data_dir: Path = typer.Option(DEFAULT_DATA),
) -> None:
    snapshot = _load_snapshot(data_dir)
    day = _parse_date(as_of) if as_of else max(snapshot["date"])
    typer.echo(render_brief(snapshot, day), nl=False)


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
    """Download trailing days, validate, analyze, print Brief, write latest chart."""
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
    typer.echo(render_brief(snapshot, day), nl=False)
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
    typer.echo(format_ops_status(data_dir, chart_path=dest, effective=effective))


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
