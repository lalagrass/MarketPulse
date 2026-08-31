"""Small CLI: download, validate, analyze, brief, chart, replay."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
import typer

from marketpulse import RANK_DISCLOSURE, REPLAY_DISCLOSURE, __version__
from marketpulse.calc import compute_snapshots, replay_snapshots, snapshots_equal
from marketpulse.data import (
    coverage_report,
    download_range,
    normalize_all,
    parse_yyyymmdd,
    read_normalized,
    validate_normalized,
    write_normalized,
)
from marketpulse.product import effective_rank_period, render_brief, render_timeline
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
) -> Path:
    """Tiny provenance next to the parquet. Not an immutable ledger."""
    meta_path = parquet_path.with_name(parquet_path.stem + ".meta.json")
    payload = {
        "classification_version": classification_version,
        "algorithm_version": __version__,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rows": rows,
    }
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
    _write_snapshot_meta(path, classification_version=classification_version, rows=len(snapshot))
    return path


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


@app.command()
def analyze(
    data_dir: Path = typer.Option(DEFAULT_DATA),
    themes_path: Path = typer.Option(DEFAULT_THEMES),
) -> None:
    """Compute equal-weight theme return, RS20, rank, value share, breadth."""
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
    snapshot = _load_snapshot(data_dir)
    lo = _parse_date(start) if start else min(snapshot["date"])
    hi = _parse_date(end) if end else max(snapshot["date"])
    window = snapshot[(snapshot["date"] >= lo) & (snapshot["date"] <= hi)]
    try:
        eff_lo, eff_hi = effective_rank_period(window)
    except ValueError:
        typer.echo("no ranked rows in this window (RS20 needs 20 trading days)")
        raise typer.Exit(code=1)
    dest = output or DEFAULT_REPORTS / f"rotation_{eff_lo.isoformat()}_{eff_hi.isoformat()}.png"
    render_timeline(window, dest)
    typer.echo(str(dest))
    typer.echo(f"effective RS20 period: {eff_lo.isoformat()} → {eff_hi.isoformat()}")
    typer.echo(REPLAY_DISCLOSURE)
    typer.echo(RANK_DISCLOSURE)


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
    _write_snapshot_meta(
        dest,
        classification_version=themes.classification_version,
        rows=len(first),
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
