"""DO-3 (sprint 004): calc refuses to compute across a data hole."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from typer.testing import CliRunner

from marketpulse.calc import DataGapError, check_data_gaps
from marketpulse.cli import app
from marketpulse.data import write_normalized
from marketpulse.themes import load_themes
from tests.conftest import make_bars, make_index, session_dates

REPO_ROOT = Path(__file__).resolve().parents[1]


def _clean_panel(n: int = 120):
    dates = session_dates(n)
    prices = {
        "AAA": [100.0 + i * 0.2 for i in range(n)],
        "BBB": [90.0 + i * 0.1 for i in range(n)],
        "CCC": [70.0 + i * 0.15 for i in range(n)],
    }
    bars = make_bars(dates, prices, twse=("AAA", "BBB"), tpex=("CCC",))
    index = make_index(dates, [1000.0 + i for i in range(n)])
    return dates, bars, index


def test_clean_paired_data_does_not_raise() -> None:
    dates, bars, index = _clean_panel()
    check_data_gaps(
        bars, index, raw_twse_dates=set(dates), raw_tpex_dates=set(dates)
    )


def test_continuity_gap_of_thirty_sessions_raises_with_bracket_dates() -> None:
    """Acceptance 1: a middle hole of 30 trading days must raise, and the
    message must carry the start and end of the hole."""
    dates, bars, index = _clean_panel(120)
    drop = set(dates[45:75])  # 30 consecutive sessions
    last_before, first_after = dates[44], dates[75]
    bars = bars[~bars["date"].isin(drop)].copy()
    index = index[~index["date"].isin(drop)].copy()

    with pytest.raises(DataGapError) as excinfo:
        check_data_gaps(bars, index)
    msg = str(excinfo.value)
    assert last_before.isoformat() in msg
    assert first_after.isoformat() in msg


def test_analyze_cli_raises_on_thirty_session_hole(tmp_path: Path, monkeypatch) -> None:
    """Acceptance 1 at the command level: `analyze` exits non-zero and says
    where the hole is."""
    themes_path = REPO_ROOT / "themes" / "v1.yaml"
    themes = load_themes(themes_path)
    symbols = sorted({m for th in themes.themes for m in th.members})
    mid = max(1, len(symbols) // 2)
    twse, tpex = tuple(symbols[:mid]), tuple(symbols[mid:])

    dates = session_dates(120)
    drop = set(dates[45:75])
    last_before, first_after = dates[44], dates[75]
    prices = {s: [100.0 + i * 0.1 for i in range(len(dates))] for s in symbols}
    bars = make_bars(dates, prices, twse=twse, tpex=tpex)
    index = make_index(dates, [1000.0 + i for i in range(len(dates))])
    bars = bars[~bars["date"].isin(drop)].copy()
    index = index[~index["date"].isin(drop)].copy()

    data_dir = tmp_path / "data"
    (data_dir / "normalized").mkdir(parents=True)
    (data_dir / "snapshots").mkdir(parents=True)
    write_normalized(data_dir, bars, index)
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(
        app, ["analyze", "--data-dir", str(data_dir), "--themes-path", str(themes_path)]
    )
    assert result.exit_code == 1, result.output
    assert last_before.isoformat() in result.output
    assert first_after.isoformat() in result.output
    assert not (data_dir / "snapshots" / "theme_daily.parquet").exists()


def test_raw_pairing_gap_names_missing_side_range_and_count() -> None:
    """Acceptance 2 shape: TWSE has 89 sessions TPEx never got. The check
    runs on raw file dates, so a never-fetched session (which normalizes to
    zero rows) is still caught."""
    twse_dates = set(session_dates(200))
    tpex_dates = set(sorted(twse_dates)[89:])  # first 89 missing on TPEx
    missing = sorted(twse_dates - tpex_dates)

    with pytest.raises(DataGapError) as excinfo:
        check_data_gaps(
            make_bars(sorted(twse_dates), {"AAA": [1.0] * len(twse_dates)}, twse=("AAA",)),
            make_index(sorted(twse_dates), [1.0] * len(twse_dates)),
            raw_twse_dates=twse_dates,
            raw_tpex_dates=tpex_dates,
        )
    msg = str(excinfo.value)
    assert "TPEx missing for 89 session(s)" in msg
    assert missing[0].isoformat() in msg
    assert missing[-1].isoformat() in msg


def test_pairing_check_skipped_when_no_raw_dates_supplied() -> None:
    dates, bars, index = _clean_panel(40)
    # No raw_*_dates: only continuity is checked, and this panel is contiguous.
    check_data_gaps(bars, index)


def test_backfilled_pairing_passes(tmp_path: Path) -> None:
    """Acceptance 3 shape: once TPEx is filled in for every TWSE session, the
    pairing check goes green."""
    dates, bars, index = _clean_panel(60)
    check_data_gaps(
        bars, index, raw_twse_dates=set(dates), raw_tpex_dates=set(dates)
    )
