"""DO-2 (sprint 004): branch-basket strength panel. Reads layer 1, never
writes it (contract R3); no rank, no score (R1)."""

from __future__ import annotations

import textwrap
from dataclasses import replace
from datetime import date
from pathlib import Path

import pandas as pd
from typer.testing import CliRunner

from marketpulse.baskets import (
    BASKET_LABEL,
    BASKET_ORDER,
    EMPTY_BASKET_LABEL,
    OVERLAP_NOTE,
    PANEL_READING_NOTE,
    PRICE_BREAK_HEADER,
    PRICE_BREAK_LINE,
    PRICE_BREAK_MARK,
    SHARED_UPSTREAM_NOTE,
    compute_basket_metrics,
    overlap_counts,
    render_basket_panel,
    resolve_either_way,
    shared_upstream,
    window_dates,
)
from marketpulse.calc import _pivot, n_day_return
from marketpulse.cli import app
from marketpulse.data import write_normalized
from marketpulse.narratives import (
    BASKET_EITHER_WAY,
    BASKET_IF_FALSE,
    BASKET_IF_TRUE,
    UNKNOWN_THEME_ID_NOTE,
    Branch,
    load_as_of,
)
from marketpulse.themes import Theme, ThemeSet, load_themes
from tests.conftest import make_bars, make_index, session_dates

REPO_ROOT = Path(__file__).resolve().parents[1]
THEMES = load_themes(REPO_ROOT / "themes" / "v1.yaml")


def _branch(
    bid: str,
    basket: tuple[str, ...] = (),
    status: str = "live",
    *,
    if_false: tuple[str, ...] = (),
    either_way: tuple[str, ...] = (),
) -> Branch:
    return Branch(
        branch_id=bid,
        claim=f"claim {bid}",
        if_true=basket,
        if_false=if_false,
        either_way=either_way,
        watch="w",
        status=status,
    )


def _kind(rows, branch_id: str, kind: str):
    (row,) = [r for r in rows if r.branch_id == branch_id and r.kind == kind]
    return row


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
    rows = compute_basket_metrics(
        bars, index, [("n1", _branch("b", ("AAA",)))], dates[-1], THEMES
    )
    m = _kind(rows, "b", BASKET_IF_TRUE)
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
    rows = compute_basket_metrics(bars, index, branches, dates[-1], THEMES)
    assert len(rows) == 6  # two branches, three baskets each
    empty = _kind(rows, "empty", BASKET_IF_TRUE)
    assert empty.is_empty and empty.member_count == 0
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
    before = compute_basket_metrics(bars, index, live, as_of, THEMES)

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
    after = compute_basket_metrics(bars, index, live2, as_of, THEMES)

    assert before == after
    assert _kind(before, "b", BASKET_IF_TRUE).basket == ("AAA",)


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
    rows = compute_basket_metrics(bars, index, branches, dates[-1], THEMES)
    assert [m.branch_id for m in rows] == ["weak_first"] * 3 + ["strong_second"] * 3
    weak = _kind(rows, "weak_first", BASKET_IF_TRUE)
    strong = _kind(rows, "strong_second", BASKET_IF_TRUE)
    assert weak.rs20 < strong.rs20  # strength ignored for ordering


# ── Q3: value_share denominator is whole-market trading value ──


def test_value_share_denominator_is_whole_market() -> None:
    dates = session_dates(25)
    prices = {"AAA": [100.0] * 25, "BBB": [200.0] * 25, "CCC": [50.0] * 25}
    bars = make_bars(dates, prices, twse=("AAA", "BBB"), tpex=("CCC",))
    index = make_index(dates, [1000.0] * 25)
    # make_bars sets trading_value = close * 1000
    rows = compute_basket_metrics(
        bars, index, [("n1", _branch("b", ("AAA",)))], dates[-1], THEMES
    )
    m = _kind(rows, "b", BASKET_IF_TRUE)
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
        ["baskets", "--data-dir", str(data_dir), "--narratives-dir", str(tmp_path / "narratives"),
         "--themes-path", str(themes_path), "--as-of", "2026-01-05"],
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


# ── sprint 014 DO-2: one branch, three rows ──

# A tiny ThemeSet over the synthetic symbols, so an `either_way` basket has
# members that actually have bars. Built directly rather than through
# load_themes (which enforces the real 11).
FAKE_THEMES = ThemeSet(
    classification_version="test",
    taxonomy_frozen_at="",
    notes="",
    themes=(
        Theme("t_up", "up", ("AAA",)),
        Theme("t_down", "down", ("BBB",)),
        Theme("t_mixed", "mixed", ("AAA", "CCC")),
    ),
)


def _three_basket_panel(n: int = 30):
    dates = session_dates(n)
    prices = {
        "AAA": [100.0 * 1.02**i for i in range(n)],
        "BBB": [100.0 * 0.99**i for i in range(n)],
        "CCC": [50.0 + i for i in range(n)],
    }
    bars = make_bars(dates, prices, twse=("AAA", "BBB"), tpex=("CCC",))
    index = make_index(dates, [1000.0 + i for i in range(n)])
    return dates, bars, index


def _body_lines(panel: str) -> list[str]:
    """The basket rows: everything after the column header, blanks dropped."""
    lines = panel.splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.startswith("branch")) + 1
    return [ln for ln in lines[start:] if ln.strip()]


def test_do2_three_rows_in_fixed_order() -> None:
    """F5: a live branch with all three baskets filled occupies three rows,
    ordered either_way, if_true, if_false."""
    dates, bars, index = _three_basket_panel()
    branch = _branch("b", ("AAA",), if_false=("BBB",), either_way=("t_mixed",))
    rows = compute_basket_metrics(bars, index, [("n1", branch)], dates[-1], FAKE_THEMES)
    assert [r.kind for r in rows] == [BASKET_EITHER_WAY, BASKET_IF_TRUE, BASKET_IF_FALSE]
    assert [r.kind for r in rows] == list(BASKET_ORDER)
    assert [r.member_count for r in rows] == [2, 1, 1]

    body = _body_lines(render_basket_panel(rows, dates[-1]))
    assert len(body) == 3
    assert BASKET_LABEL[BASKET_EITHER_WAY] in body[0]
    assert BASKET_LABEL[BASKET_IF_TRUE] in body[1]
    assert BASKET_LABEL[BASKET_IF_FALSE] in body[2]
    # the branch names itself once, on the first of its three rows
    assert body[0].startswith("n1/b")
    assert body[1].startswith(" ") and body[2].startswith(" ")


def test_do2_empty_basket_still_gets_its_row() -> None:
    """F6: a basket with no members keeps its line and prints 無標的."""
    dates, bars, index = _three_basket_panel()
    branch = _branch("b", ("AAA",))  # if_false and either_way empty
    rows = compute_basket_metrics(bars, index, [("n1", branch)], dates[-1], FAKE_THEMES)
    assert len(rows) == 3
    body = _body_lines(render_basket_panel(rows, dates[-1]))
    assert len(body) == 3
    assert EMPTY_BASKET_LABEL in body[0]   # either_way
    assert EMPTY_BASKET_LABEL not in body[1]
    assert EMPTY_BASKET_LABEL in body[2]   # if_false


def test_do2_overlap_between_if_true_and_if_false_is_visible() -> None:
    """F7: symbols on both sides are counted and the count reaches the panel."""
    dates, bars, index = _three_basket_panel()
    branch = _branch("b", ("AAA", "BBB"), if_false=("BBB", "CCC"))
    rows = compute_basket_metrics(bars, index, [("n1", branch)], dates[-1], FAKE_THEMES)
    assert overlap_counts(rows) == {("n1", "b"): 1}
    assert OVERLAP_NOTE.format(n=1) in render_basket_panel(rows, dates[-1])


def test_do2_disjoint_sides_print_no_overlap_note() -> None:
    dates, bars, index = _three_basket_panel()
    branch = _branch("b", ("AAA",), if_false=("BBB",))
    rows = compute_basket_metrics(bars, index, [("n1", branch)], dates[-1], FAKE_THEMES)
    assert overlap_counts(rows) == {("n1", "b"): 0}
    assert OVERLAP_NOTE.format(n=0) not in render_basket_panel(rows, dates[-1])


def test_do2_same_either_way_in_two_stories_prints_the_hint() -> None:
    """F8: the same set of theme_ids as two stories' upstream means that
    upstream cannot tell the two apart, and the panel says so."""
    dates, bars, index = _three_basket_panel()
    branches = [
        ("n1", _branch("b1", ("AAA",), either_way=("t_up", "t_down"))),
        ("n2", _branch("b2", ("BBB",), either_way=("t_down", "t_up"))),  # same set
        ("n3", _branch("b3", ("AAA",), either_way=("t_mixed",))),
    ]
    rows = compute_basket_metrics(bars, index, branches, dates[-1], FAKE_THEMES)
    assert shared_upstream(rows) == {("n1", "b1"): ("n2",), ("n2", "b2"): ("n1",)}
    panel = render_basket_panel(rows, dates[-1])
    assert SHARED_UPSTREAM_NOTE.format(others="n2") in panel
    assert SHARED_UPSTREAM_NOTE.format(others="n1") in panel
    assert SHARED_UPSTREAM_NOTE.format(others="n3") not in panel


def test_do2_two_branches_of_one_story_are_not_a_shared_upstream() -> None:
    """`兩則以上故事` counts narratives, not branches of one narrative."""
    dates, bars, index = _three_basket_panel()
    branches = [
        ("n1", _branch("b1", either_way=("t_up",))),
        ("n1", _branch("b2", either_way=("t_up",))),
    ]
    rows = compute_basket_metrics(bars, index, branches, dates[-1], FAKE_THEMES)
    assert shared_upstream(rows) == {}
    assert "這條上游不區辨" not in render_basket_panel(rows, dates[-1])


def test_do2_reading_note_is_a_constant_carrying_no_number() -> None:
    """F9: the header note is fixed copy — no digit from the data gets into
    it, and it is byte-identical on two sessions whose numbers differ."""
    assert not any(ch.isascii() and ch.isdigit() for ch in PANEL_READING_NOTE)
    dates, bars, index = _three_basket_panel(40)
    branch = _branch("b", ("AAA",), if_false=("BBB",), either_way=("t_up",))
    early = render_basket_panel(
        compute_basket_metrics(bars, index, [("n1", branch)], dates[25], FAKE_THEMES),
        dates[25],
    )
    late = render_basket_panel(
        compute_basket_metrics(bars, index, [("n1", branch)], dates[-1], FAKE_THEMES),
        dates[-1],
    )
    assert early != late                       # the numbers did move
    assert PANEL_READING_NOTE in early and PANEL_READING_NOTE in late


def test_do2_either_way_theme_ids_expand_via_themeset() -> None:
    """Rabbit hole: membership comes from the ThemeSet, not a second table."""
    members, unknown = resolve_either_way(("optical_cpo",), THEMES)
    assert members == THEMES.members_of("optical_cpo")
    assert unknown == ()
    two, _ = resolve_either_way(("optical_cpo", "pcb"), THEMES)
    assert len(two) == len(set(two))           # overlapping themes de-duplicate
    assert two[: len(members)] == members      # ids in the order written


def test_do2_unknown_either_way_theme_id_is_named_on_the_panel() -> None:
    """F4 on screen: the id appears rather than the basket just looking empty."""
    dates, bars, index = _three_basket_panel()
    branch = _branch("b", ("AAA",), either_way=("t_up", "t_pu"))
    rows = compute_basket_metrics(bars, index, [("n1", branch)], dates[-1], FAKE_THEMES)
    either = _kind(rows, "b", BASKET_EITHER_WAY)
    assert either.unknown == ("t_pu",)
    assert either.basket == ("AAA",)           # the known half still measured
    panel = render_basket_panel(rows, dates[-1])
    assert UNKNOWN_THEME_ID_NOTE in panel and "t_pu" in panel


def test_do2_rows_are_not_reordered_by_strength() -> None:
    """R1 / D10: the weaker basket keeps its fixed slot; nothing is combined."""
    dates, bars, index = _three_basket_panel(70)   # long enough for RS60 too
    branch = _branch("b", ("BBB",), if_false=("AAA",), either_way=("t_up",))
    rows = compute_basket_metrics(bars, index, [("n1", branch)], dates[-1], FAKE_THEMES)
    assert _kind(rows, "b", BASKET_IF_TRUE).rs20 < _kind(rows, "b", BASKET_IF_FALSE).rs20
    assert [r.kind for r in rows] == list(BASKET_ORDER)
    body = _body_lines(render_basket_panel(rows, dates[-1]))
    # exactly the documented columns, no fourth number derived from the three
    assert len(body) == 3
    for line in body:
        assert line.count("%") == 5            # RS5, RS20, RS60, breadth, val%


def test_do2_two_branches_are_visually_separated() -> None:
    """F10's arrangement, stated as a fact a test can hold: the three rows of a
    branch are contiguous and a blank line closes the block. Whether it reads
    at a glance is the product owner's call, not this test's."""
    dates, bars, index = _three_basket_panel()
    branches = [
        ("n1", _branch("b1", ("AAA",))),
        ("n2", _branch("b2", ("BBB",))),
    ]
    rows = compute_basket_metrics(bars, index, branches, dates[-1], FAKE_THEMES)
    panel = render_basket_panel(rows, dates[-1])
    lines = panel.splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.startswith("branch")) + 1
    block = lines[start:]
    assert [bool(ln.strip()) for ln in block] == [True] * 3 + [False] + [True] * 3


# ── sprint 015 DO-1: a price break inside the window is disclosed ─────────
#
# Detection is calc.impossible_daily_returns, unchanged. These tests are about
# what reaches the panel, and about the promise that nothing else moves.


def _break_panel(n: int = 70, breaks: dict[str, int] | None = None):
    """Flat prices, plus one close-to-close drop per named symbol that the
    exchange's limit arithmetic cannot reach (100 → 50 is far outside 跌停),
    at the given session index. The level stays reset afterwards, so each
    symbol produces exactly one break."""
    dates = session_dates(n)
    breaks = breaks or {}
    prices: dict[str, list[float]] = {}
    for symbol in ("AAA", "BBB", "CCC"):
        at = breaks.get(symbol)
        prices[symbol] = [
            50.0 if at is not None and i >= at else 100.0 for i in range(n)
        ]
    bars = make_bars(dates, prices, twse=("AAA", "BBB"), tpex=("CCC",))
    index = make_index(dates, [1000.0] * n)
    return dates, bars, index


def _unmarked(panel: str) -> str:
    """The panel with the marks blanked and the break block removed — what it
    would have printed before sprint 015."""
    kept = [
        ln
        for ln in panel.splitlines()
        if PRICE_BREAK_HEADER not in ln and "return_1" not in ln
    ]
    return "\n".join(ln.replace(PRICE_BREAK_MARK, " ") for ln in kept) + "\n"


def test_do1_break_inside_every_window_marks_every_rs_column() -> None:
    """G1: a member's break three sessions back is inside RS5, RS20 and RS60."""
    dates, bars, index = _break_panel(breaks={"AAA": 67})
    branch = _branch("b", ("AAA",))
    rows = compute_basket_metrics(bars, index, [("n1", branch)], dates[-1], FAKE_THEMES)
    row = _kind(rows, "b", BASKET_IF_TRUE)
    assert [b.symbol for b in row.breaks_5] == ["AAA"]
    assert [b.symbol for b in row.breaks_20] == ["AAA"]
    assert [b.symbol for b in row.breaks_60] == ["AAA"]
    assert row.breaks_20[0].date == dates[67]
    assert row.breaks_20[0].return_1 == -0.5


def test_do1_break_outside_the_window_marks_nothing() -> None:
    """G1: a break older than the longest window is not this panel's problem."""
    dates, bars, index = _break_panel(breaks={"AAA": 5})
    branch = _branch("b", ("AAA",))
    rows = compute_basket_metrics(bars, index, [("n1", branch)], dates[-1], FAKE_THEMES)
    row = _kind(rows, "b", BASKET_IF_TRUE)
    assert (row.breaks_5, row.breaks_20, row.breaks_60) == ((), (), ())
    assert PRICE_BREAK_MARK not in render_basket_panel(rows, dates[-1])


def test_do1_the_three_windows_are_judged_independently() -> None:
    """G1: a break ten sessions back is inside RS20 and RS60 and outside RS5;
    the RS5 cell keeps its two separating spaces, the other two do not."""
    dates, bars, index = _break_panel(breaks={"AAA": 60})
    branch = _branch("b", ("AAA",))
    rows = compute_basket_metrics(bars, index, [("n1", branch)], dates[-1], FAKE_THEMES)
    row = _kind(rows, "b", BASKET_IF_TRUE)
    assert row.breaks_5 == ()
    assert [b.symbol for b in row.breaks_20] == ["AAA"]
    assert [b.symbol for b in row.breaks_60] == ["AAA"]

    line = next(ln for ln in _body_lines(render_basket_panel(rows, dates[-1]))
                if BASKET_LABEL[BASKET_IF_TRUE] in ln)
    # cells: 籃子, n, RS5, RS20, RS60, breadth, val%
    cells = line.split()
    # RS5 unmarked, RS20 and RS60 marked — the mark rides on the number's cell
    assert not cells[2].endswith(PRICE_BREAK_MARK)
    assert cells[3].endswith(PRICE_BREAK_MARK)
    assert cells[4].endswith(PRICE_BREAK_MARK)


def test_do1_window_dates_come_from_n_day_returns_own_index() -> None:
    """Rabbit hole: the window is read off the trading-day index that
    n_day_return shifts on, and is empty exactly where n_day_return is NaN."""
    dates, bars, index = _break_panel(n=30)
    close = _pivot(bars, "close")
    ts = close.index[-1]
    assert window_dates(close.index, ts, 5) == tuple(close.index[-5:])
    assert window_dates(close.index, ts, 20) == tuple(close.index[-20:])
    assert window_dates(close.index, ts, 60) == ()          # history too short
    assert pd.isna(n_day_return(close, 60).loc[ts, "AAA"])   # …and so is the RS


def test_do1_no_hit_leaves_the_branch_block_untouched() -> None:
    """G3: a clean branch prints the same bytes whether or not another branch
    on the same panel carries a mark."""
    dates, bars, index = _break_panel(breaks={"AAA": 67})
    clean = ("n2", _branch("b2", ("BBB",)))
    alone = render_basket_panel(
        compute_basket_metrics(bars, index, [clean], dates[-1], FAKE_THEMES),
        dates[-1],
    )
    together = render_basket_panel(
        compute_basket_metrics(
            bars, index, [("n1", _branch("b1", ("AAA",))), clean], dates[-1], FAKE_THEMES
        ),
        dates[-1],
    )
    clean_block = [ln for ln in alone.splitlines() if ln.startswith("n2/b2")]
    assert clean_block
    assert clean_block[0] in together.splitlines()
    assert PRICE_BREAK_MARK not in "\n".join(
        ln for ln in together.splitlines() if ln.startswith("n2/b2")
    )


def test_do1_the_mark_adds_nothing_but_the_mark() -> None:
    """G4: blanking the marks and dropping the break block gives back exactly
    the panel that the same rows print with no breaks recorded — the RS
    numbers and every column position are the same bytes."""
    dates, bars, index = _break_panel(breaks={"AAA": 67})
    branch = _branch("b", ("AAA",), if_false=("BBB",))
    rows = compute_basket_metrics(bars, index, [("n1", branch)], dates[-1], FAKE_THEMES)
    assert any(r.breaks_20 for r in rows)
    stripped = [replace(r, breaks_5=(), breaks_20=(), breaks_60=()) for r in rows]
    assert _unmarked(render_basket_panel(rows, dates[-1])) == render_basket_panel(
        stripped, dates[-1]
    )


def test_do1_every_break_behind_a_mark_gets_its_own_line() -> None:
    """G2: two members, two dates, two lines — symbol, date, return_1."""
    dates, bars, index = _break_panel(breaks={"AAA": 67, "BBB": 65})
    branch = _branch("b", ("AAA", "BBB"))
    rows = compute_basket_metrics(bars, index, [("n1", branch)], dates[-1], FAKE_THEMES)
    panel = render_basket_panel(rows, dates[-1])
    listed = [ln for ln in panel.splitlines() if "return_1" in ln]
    assert len(listed) == 2
    assert listed[0].strip() == PRICE_BREAK_LINE.format(
        symbol="BBB", date=dates[65].isoformat(), ret="-50.0%"
    )
    assert listed[1].strip() == PRICE_BREAK_LINE.format(
        symbol="AAA", date=dates[67].isoformat(), ret="-50.0%"
    )
    assert panel.count(PRICE_BREAK_HEADER) == 1


def test_do1_one_session_is_listed_once_however_many_baskets_hold_it() -> None:
    """A break is a fact about a session, not about a basket: a symbol in both
    either_way and if_true still contributes one line to the branch block."""
    dates, bars, index = _break_panel(breaks={"AAA": 67})
    branch = _branch("b", ("AAA",), either_way=("t_up",))  # t_up is ("AAA",)
    rows = compute_basket_metrics(bars, index, [("n1", branch)], dates[-1], FAKE_THEMES)
    assert _kind(rows, "b", BASKET_EITHER_WAY).breaks_20
    assert _kind(rows, "b", BASKET_IF_TRUE).breaks_20
    panel = render_basket_panel(rows, dates[-1])
    assert len([ln for ln in panel.splitlines() if "return_1" in ln]) == 1


def test_do1_no_number_gets_no_mark() -> None:
    """An RS the panel prints as n/a has no window to be inside of: the short
    history that makes it n/a is also what makes the mark meaningless."""
    dates, bars, index = _break_panel(n=30, breaks={"AAA": 27})
    branch = _branch("b", ("AAA",))
    rows = compute_basket_metrics(bars, index, [("n1", branch)], dates[-1], FAKE_THEMES)
    row = _kind(rows, "b", BASKET_IF_TRUE)
    assert row.rs60 is None and row.breaks_60 == ()
    assert row.breaks_20 and row.breaks_5
    line = next(ln for ln in _body_lines(render_basket_panel(rows, dates[-1]))
                if BASKET_LABEL[BASKET_IF_TRUE] in ln)
    assert "n/a " in line and "n/a*" not in line
