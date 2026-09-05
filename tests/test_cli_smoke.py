"""CLI smoke: analyze → brief → radar on tmp_path (spec 003 DO-3)."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from marketpulse.cli import app
from marketpulse.data import write_normalized
from marketpulse.themes import load_themes
from tests.conftest import make_bars, make_index, session_dates


def _seed_tmp_data(tmp_path: Path, repo_themes: Path) -> tuple[Path, Path]:
    data_dir = tmp_path / "data"
    (data_dir / "normalized").mkdir(parents=True)
    (data_dir / "snapshots").mkdir(parents=True)
    (tmp_path / "reports").mkdir()

    themes = load_themes(repo_themes)
    symbols = sorted({m for th in themes.themes for m in th.members})
    # complete_sessions requires TWSE ∩ TPEx ∩ TAIEX each day.
    mid = max(1, len(symbols) // 2)
    twse = tuple(symbols[:mid])
    tpex = tuple(symbols[mid:])
    dates = session_dates(65)  # enough for rs60
    prices = {
        sym: [100.0 + (i * (1 + (n % 7) * 0.01)) for i in range(len(dates))]
        for n, sym in enumerate(symbols)
    }
    bars = make_bars(dates, prices, twse=twse, tpex=tpex)
    index = make_index(dates, [1000.0 + i for i in range(len(dates))])
    write_normalized(data_dir, bars, index)
    return data_dir, repo_themes


def test_cli_analyze_brief_radar_smoke(tmp_path: Path, monkeypatch) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    data_dir, themes_path = _seed_tmp_data(tmp_path, repo_root / "themes" / "v1.yaml")
    reports = tmp_path / "reports"
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()

    result = runner.invoke(
        app,
        ["analyze", "--data-dir", str(data_dir), "--themes-path", str(themes_path)],
    )
    assert result.exit_code == 0, result.output
    assert (data_dir / "snapshots" / "theme_daily.parquet").exists()
    assert (data_dir / "snapshots" / "market_daily.parquet").exists()

    result = runner.invoke(app, ["brief", "--data-dir", str(data_dir)])
    assert result.exit_code == 0, result.output
    assert "MarketPulse" in result.output
    assert "持續性" in result.output

    radar_out = reports / "radar.html"
    result = runner.invoke(
        app,
        [
            "radar",
            "--data-dir",
            str(data_dir),
            "--themes-path",
            str(themes_path),
            "--output",
            str(radar_out),
        ],
    )
    assert result.exit_code == 0, result.output
    assert radar_out.exists()
    html = radar_out.read_text(encoding="utf-8")
    assert "MarketPulse" in html
