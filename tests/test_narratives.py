from __future__ import annotations

from datetime import date
from pathlib import Path

from marketpulse.narratives import (
    COVERAGE_UNCOVERED,
    COVERAGE_UNKNOWN,
    load_as_of,
)
from marketpulse.narratives import coverage_report as narrative_coverage_report
from marketpulse.themes import load_themes

REPO_ROOT = Path(__file__).resolve().parents[1]


def _write(dir_: Path, name: str, content: str) -> None:
    (dir_ / name).write_text(content, encoding="utf-8")


def test_load_as_of_picks_the_latest_snapshot_not_exceeding_d(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "2026-01-01.yaml",
        """
        snapshot_date: 2026-01-01
        narratives:
          - narrative_id: early
            name: Early
            first_noted: 2026-01-01
            source: self
            source_ref: x
            stance: new
            named_symbols: []
            inferred_symbols: []
            note: n/a
        """,
    )
    _write(
        tmp_path,
        "2026-02-01.yaml",
        """
        snapshot_date: 2026-02-01
        narratives:
          - narrative_id: mid
            name: Mid
            first_noted: 2026-02-01
            source: self
            source_ref: x
            stance: new
            named_symbols: []
            inferred_symbols: []
            note: n/a
        """,
    )
    _write(
        tmp_path,
        "2026-03-01.yaml",
        """
        snapshot_date: 2026-03-01
        narratives:
          - narrative_id: late
            name: Late
            first_noted: 2026-03-01
            source: self
            source_ref: x
            stance: new
            named_symbols: []
            inferred_symbols: []
            note: n/a
        """,
    )
    # D falls between the 2nd and 3rd file: must pick 2026-02-01, not the
    # newest file on disk and not the oldest.
    snapshot = load_as_of(date(2026, 2, 15), tmp_path)
    assert snapshot.snapshot_date == date(2026, 2, 1)
    assert [n.narrative_id for n in snapshot.narratives] == ["mid"]


def test_load_as_of_filters_out_narratives_noted_after_d(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "2026-08-01.yaml",
        """
        snapshot_date: 2026-08-01
        narratives:
          - narrative_id: seen_early
            name: Seen Early
            first_noted: 2026-07-01
            source: self
            source_ref: x
            stance: new
            named_symbols: []
            inferred_symbols: []
            note: n/a
          - narrative_id: seen_late
            name: Seen Late
            first_noted: 2026-08-12
            source: self
            source_ref: x
            stance: new
            named_symbols: []
            inferred_symbols: []
            note: n/a
        """,
    )
    # The look-ahead test: first_noted (2026-08-12) is one day after D
    # (2026-08-11) but still within the same snapshot file's coverage
    # window (snapshot_date 2026-08-01 <= D). The per-narrative filter,
    # not just the per-file filter, must exclude it.
    snapshot = load_as_of(date(2026, 8, 11), tmp_path)
    ids = [n.narrative_id for n in snapshot.narratives]
    assert "seen_early" in ids
    assert "seen_late" not in ids


def test_load_as_of_returns_empty_when_every_snapshot_postdates_d(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "2026-05-01.yaml",
        """
        snapshot_date: 2026-05-01
        narratives:
          - narrative_id: future
            name: Future
            first_noted: 2026-05-01
            source: self
            source_ref: x
            stance: new
            named_symbols: []
            inferred_symbols: []
            note: n/a
        """,
    )
    snapshot = load_as_of(date(2026, 1, 1), tmp_path)
    assert snapshot.snapshot_date is None
    assert snapshot.narratives == ()


def test_symbol_types_are_strings_like_themes_yaml(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "2026-01-01.yaml",
        """
        snapshot_date: 2026-01-01
        narratives:
          - narrative_id: codes
            name: Codes
            first_noted: 2026-01-01
            source: self
            source_ref: x
            stance: new
            named_symbols: ["2330", "2454"]
            inferred_symbols: ["2317"]
            note: n/a
        """,
    )
    snapshot = load_as_of(date(2026, 1, 1), tmp_path)
    narrative = snapshot.narratives[0]
    assert all(isinstance(s, str) for s in narrative.named_symbols)
    assert all(isinstance(s, str) for s in narrative.inferred_symbols)
    assert narrative.named_symbols == ("2330", "2454")


def test_coverage_report_against_real_narratives_and_themes() -> None:
    """The spec's own worked example: 2454 (asic_xpu) is not in any theme
    (uncovered); optical_cpo names nothing, so it's unknown, not covered."""
    themes = load_themes(REPO_ROOT / "themes" / "v1.yaml")
    snapshot = load_as_of(date(2026, 9, 4), REPO_ROOT / "narratives")
    report = narrative_coverage_report(snapshot, themes)
    assert report["asic_xpu"] == COVERAGE_UNCOVERED
    assert report["optical_cpo"] == COVERAGE_UNKNOWN


def test_coverage_report_partial_and_covered() -> None:
    from marketpulse.narratives import COVERAGE_COVERED, COVERAGE_PARTIAL, Narrative, NarrativeSnapshot
    from marketpulse.themes import Theme, ThemeSet

    themes = ThemeSet(
        classification_version="test",
        taxonomy_frozen_at="2026-01-01",
        notes="",
        themes=(Theme("t1", "T1", ("AAA", "BBB")),),
    )
    covered = Narrative(
        narrative_id="covered",
        name="Covered",
        first_noted=date(2026, 1, 1),
        source="self",
        source_ref="x",
        stance="new",
        named_symbols=("AAA",),
        inferred_symbols=(),
        note="",
    )
    partial = Narrative(
        narrative_id="partial",
        name="Partial",
        first_noted=date(2026, 1, 1),
        source="self",
        source_ref="x",
        stance="new",
        named_symbols=("AAA", "ZZZ"),
        inferred_symbols=(),
        note="",
    )
    snapshot = NarrativeSnapshot(snapshot_date=date(2026, 1, 1), narratives=(covered, partial))
    report = narrative_coverage_report(snapshot, themes)
    assert report["covered"] == COVERAGE_COVERED
    assert report["partial"] == COVERAGE_PARTIAL
