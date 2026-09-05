"""DO-2 (sprint 004): branch-basket strength panel. Reads layer 1, never
writes it (contract R3); no rank, no score (R1)."""

from __future__ import annotations

import textwrap
from datetime import date
from pathlib import Path

from typer.testing import CliRunner

from marketpulse.baskets import compute_basket_metrics, render_basket_panel
from marketpulse.cli import app
from marketpulse.data import write_normalized
from marketpulse.narratives import Branch, load_as_of
from marketpulse.themes import load_themes
from tests.conftest import make_bars, make_index, session_dates

REPO_ROOT = Path(__file__).resolve().parents[1]


def _branch(bid: str, basket: tuple[str, ...], status: str = "live") -> Branch:
    return Branch(branch_id=bid, claim=f"claim {bid}", basket=basket, watch="w", status=status)


def _panel(n: int, symbols: dict[str, list[float]], twse, tpex):
    dates = session_dates(n)
    bars = make_bars(dates, symbols, twse=twse, tpex=tpex)
    index = make_index(dates, [1000.0 + i for i in range(n)])
    return dates, bars, index


# ── acceptance 3: short history → RS20 n/a, no shorter-window substitute ──


def test_rs20_and_rs60_are_none_when_history_too_short() -> None:
    dates, bars, index = _panel(
        12,
        {"AAA": [100.0 + i for i in range(12)], "CCC": [50.0 + i for i in range(12)]},
        twse=("AAA",),
        tpex=("CCC",),
    )
    rows = compute_basket_metrics(bars, index, [("n1", _branch("b", ("AAA",)))], dates[-1])
    (m,) = rows
    assert m.member_count == 1
    assert m.rs5 is not None          # 12 sessions is enough for a 5-day return
    assert m.rs20 is None             # not enough for 20
    assert m.rs60 is None
    assert "n/a" in render_basket_panel(rows, dates[-1])


# ── acceptance 4: empty basket prints a row, is not skipped ──


def test_empty_basket_emits_a_row_labelled_not_dropped() -> None:
    dates, bars, index = _panel(
        25,
        {"AAA": [100.0 + i for i in range(25)], "CCC": [50.0 + i for i in range(25)]},
        twse=("AAA",),
        tpex=("CCC",),
    )
    branches = [
        ("n1", _branch("has_basket", ("AAA",))),
        ("n1", _branch("empty", ())),
    ]
    rows = compute_basket_metrics(bars, index, branches, dates[-1])
    assert len(rows) == 2
    assert rows[1].is_empty and rows[1].member_count == 0
    panel = render_basket_panel(rows, dates[-1])
    assert "n1/empty" in panel
    assert "無標的" in panel


# ── acceptance 2: a later YAML adding a symbol cannot move an earlier as_of ──


def test_earlier_as_of_unaffected_by_later_membership_change(tmp_path: Path) -> None:
    (tmp_path / "2026-09-06.yaml").write_text(
        textwrap.dedent(
            """
            snapshot_date: 2026-09-06
            narratives:
              - narrative_id: n1
                name: N1
                first_noted: 2026-09-03
                source: self
                source_ref: x
                stance: new
                revisit: 2026-10-01
                named_symbols: []
                inferred_symbols: []
                note: n/a
                branches:
                  - branch_id: b
                    claim: c
                    basket: ["AAA"]
                    watch: w
            """
        ),
        encoding="utf-8",
    )
    n = 80
    dates = session_dates(n, start=date(2026, 6, 1))
    bars = make_bars(
        dates,
        {
            "AAA": [100.0 + i for i in range(n)],
            "BBB": [100.0 + 3 * i for i in range(n)],
            "CCC": [50.0 + i for i in range(n)],
        },
        twse=("AAA", "BBB"),
        tpex=("CCC",),
    )
    index = make_index(dates, [1000.0 + i for i in range(n)])
    as_of = next(d for d in dates if d >= date(2026, 9, 8))  # between the two snapshots
    snap = load_as_of(as_of, tmp_path)
    live = [(n.narrative_id, b) for n in snap.narratives for b in n.branches]
    before = compute_basket_metrics(bars, index, live, as_of)

    # A later snapshot adds BBB to the basket.
    (tmp_path / "2026-09-20.yaml").write_text(
        textwrap.dedent(
            """
            snapshot_date: 2026-09-20
            narratives:
              - narrative_id: n1
                name: N1
                first_noted: 2026-09-03
                source: self
                source_ref: x
                stance: new
                revisit: 2026-10-01
                named_symbols: []
                inferred_symbols: []
                note: n/a
                branches:
                  - branch_id: b
                    claim: c
                    basket: ["AAA", "BBB"]
                    watch: w
            """
        ),
        encoding="utf-8",
    )
    snap2 = load_as_of(as_of, tmp_path)
    live2 = [(n.narrative_id, b) for n in snap2.narratives for b in n.branches]
    after = compute_basket_metrics(bars, index, live2, as_of)

    assert before == after
    assert before[0].basket == ("AAA",)


# ── red line: YAML order preserved, nothing sorted by strength ──


def test_rows_follow_input_order_not_strength() -> None:
    dates, bars, index = _panel(
        30,
        {
            "STRONG": [100.0 * 1.05**i for i in range(30)],
            "WEAK": [100.0 * 0.98**i for i in range(30)],
            "CCC": [50.0 + i for i in range(30)],
        },
        twse=("STRONG", "WEAK"),
        tpex=("CCC",),
    )
    branches = [
        ("n1", _branch("weak_first", ("WEAK",))),
        ("n1", _branch("strong_second", ("STRONG",))),
    ]
    rows = compute_basket_metrics(bars, index, branches, dates[-1])
    assert [m.branch_id for m in rows] == ["weak_first", "strong_second"]
    assert rows[0].rs20 < rows[1].rs20  # strength ignored for ordering


# ── Q3: value_share denominator is whole-market trading value ──


def test_value_share_denominator_is_whole_market() -> None:
    dates = session_dates(25)
    prices = {"AAA": [100.0] * 25, "BBB": [200.0] * 25, "CCC": [50.0] * 25}
    bars = make_bars(dates, prices, twse=("AAA", "BBB"), tpex=("CCC",))
    index = make_index(dates, [1000.0] * 25)
    # make_bars sets trading_value = close * 1000
    rows = compute_basket_metrics(bars, index, [("n1", _branch("b", ("AAA",)))], dates[-1])
    (m,) = rows
    total = (100.0 + 200.0 + 50.0) * 1000.0
    assert abs(m.value_share - (100.0 * 1000.0) / total) < 1e-9


# ── acceptance 1: brief + radar output unchanged by running the panel ──


def _seed(tmp_path: Path) -> tuple[Path, Path]:
    themes_path = REPO_ROOT / "themes" / "v1.yaml"
    themes = load_themes(themes_path)
    symbols = sorted({m for th in themes.themes for m in th.members})
    mid = max(1, len(symbols) // 2)
    twse, tpex = tuple(symbols[:mid]), tuple(symbols[mid:])
    dates = session_dates(65)
    prices = {s: [100.0 + (i * (1 + n % 5 * 0.01)) for i in range(len(dates))] for n, s in enumerate(symbols)}
    bars = make_bars(dates, prices, twse=twse, tpex=tpex)
    index = make_index(dates, [1000.0 + i for i in range(len(dates))])
    data_dir = tmp_path / "data"
    (data_dir / "normalized").mkdir(parents=True)
    (data_dir / "snapshots").mkdir(parents=True)
    write_normalized(data_dir, bars, index)

    ndir = tmp_path / "narratives"
    ndir.mkdir()
    member = symbols[0]
    (ndir / "2026-01-05.yaml").write_text(
        textwrap.dedent(
            f"""
            snapshot_date: 2026-01-05
            narratives:
              - narrative_id: n1
                name: N1
                first_noted: 2026-01-05
                source: self
                source_ref: x
                stance: new
                revisit: 2026-02-01
                named_symbols: []
                inferred_symbols: []
                note: n/a
                branches:
                  - branch_id: b1
                    claim: c
                    basket: ["{member}"]
                    watch: w
                  - branch_id: b2
                    claim: c
                    basket: []
                    watch: w
            """
        ),
        encoding="utf-8",
    )
    return data_dir, themes_path


def test_running_baskets_does_not_change_brief_or_radar(tmp_path: Path, monkeypatch) -> None:
    data_dir, themes_path = _seed(tmp_path)
    reports = tmp_path / "reports"
    reports.mkdir()
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    assert runner.invoke(app, ["analyze", "--data-dir", str(data_dir), "--themes-path", str(themes_path)]).exit_code == 0
    brief_1 = runner.invoke(app, ["brief", "--data-dir", str(data_dir)])
    radar_out = reports / "r1.html"
    assert runner.invoke(
        app, ["radar", "--data-dir", str(data_dir), "--themes-path", str(themes_path), "--output", str(radar_out)]
    ).exit_code == 0
    radar_1 = radar_out.read_text(encoding="utf-8")
    snap_mtime = (data_dir / "snapshots" / "theme_daily.parquet").stat().st_mtime

    panel = runner.invoke(
        app,
        ["baskets", "--data-dir", str(data_dir), "--narratives-dir", str(tmp_path / "narratives"), "--as-of", "2026-01-05"],
    )
    assert panel.exit_code == 0, panel.output
    assert "n1/b1" in panel.output
    assert "無標的" in panel.output  # the empty basket still prints

    brief_2 = runner.invoke(app, ["brief", "--data-dir", str(data_dir)])
    radar_out2 = reports / "r2.html"
    runner.invoke(
        app, ["radar", "--data-dir", str(data_dir), "--themes-path", str(themes_path), "--output", str(radar_out2)]
    )
    assert brief_2.output == brief_1.output
    assert radar_out2.read_text(encoding="utf-8") == radar_1
    # panel wrote nothing under snapshots/
    assert (data_dir / "snapshots" / "theme_daily.parquet").stat().st_mtime == snap_mtime
    assert not (data_dir / "snapshots" / "basket_daily.parquet").exists()
