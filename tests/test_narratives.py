from __future__ import annotations

import textwrap
from datetime import date
from pathlib import Path

import pytest

from marketpulse.narratives import (
    COVERAGE_UNCOVERED,
    COVERAGE_UNKNOWN,
    STAGE_OPEN,
    history,
    load_as_of,
)
from marketpulse.narratives import coverage_report as narrative_coverage_report
from marketpulse.themes import load_themes

REPO_ROOT = Path(__file__).resolve().parents[1]


def _write(dir_: Path, name: str, content: str) -> None:
    (dir_ / name).write_text(textwrap.dedent(content), encoding="utf-8")


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


# ── sprint 004 DO-1: additive schema (stage / revisit / log / branches, history) ──


def test_do1_existing_2026_09_04_file_still_loads_unchanged() -> None:
    """Acceptance 1: the real narratives/2026-09-04.yaml, not one character
    changed, still loads; all three narratives default to stage `open`; the
    coverage report is byte-for-byte what it was before this sprint."""
    themes = load_themes(REPO_ROOT / "themes" / "v1.yaml")
    snapshot = load_as_of(date(2026, 9, 4), REPO_ROOT / "narratives")
    ids = sorted(n.narrative_id for n in snapshot.narratives)
    assert ids == ["asic_xpu", "nvhbm", "optical_cpo"]
    assert all(n.stage == STAGE_OPEN for n in snapshot.narratives)
    assert all(n.log == () and n.branches == () for n in snapshot.narratives)
    report = narrative_coverage_report(snapshot, themes)
    assert report == {
        "asic_xpu": COVERAGE_UNCOVERED,
        "nvhbm": "covered",
        "optical_cpo": COVERAGE_UNKNOWN,
    }


def test_do1_missing_revisit_raises_with_narrative_id(tmp_path: Path) -> None:
    """Acceptance 2: a post-schema snapshot (snapshot_date >= 2026-09-06)
    without `revisit` makes load_as_of raise, and the id is in the message."""
    _write(
        tmp_path,
        "2026-09-10.yaml",
        """
        snapshot_date: 2026-09-10
        narratives:
          - narrative_id: rotting_story
            name: Rotting
            first_noted: 2026-09-10
            source: self
            source_ref: x
            stance: new
            named_symbols: []
            inferred_symbols: []
            note: no revisit date here
        """,
    )
    with pytest.raises(ValueError, match="rotting_story"):
        load_as_of(date(2026, 9, 12), tmp_path)


def test_do1_history_returns_versions_up_to_as_of(tmp_path: Path) -> None:
    """Acceptance 3: two snapshots, the later one adds a log entry to
    asic_xpu. history() at 2026-09-05 sees only the first; at 2026-09-06 it
    sees both, in snapshot_date order."""
    _write(
        tmp_path,
        "2026-09-04.yaml",
        """
        snapshot_date: 2026-09-04
        narratives:
          - narrative_id: asic_xpu
            name: ASIC
            first_noted: 2026-09-03
            source: podcast
            source_ref: EP693
            stance: new
            named_symbols: ["2454"]
            inferred_symbols: []
            note: first mention
        """,
    )
    _write(
        tmp_path,
        "2026-09-06.yaml",
        """
        snapshot_date: 2026-09-06
        narratives:
          - narrative_id: asic_xpu
            name: ASIC
            first_noted: 2026-09-03
            source: podcast
            source_ref: EP693
            stance: new
            stage: open
            revisit: 2026-10-15
            named_symbols: ["2454"]
            inferred_symbols: []
            note: progress
            log:
              - date: 2026-09-05
                source_ref: EP694
                kind: evidence
                text: Hock Tan names MediaTek
                bears_on: []
        """,
    )

    early = history("asic_xpu", date(2026, 9, 5), tmp_path)
    assert [v.snapshot_date for v in early] == [date(2026, 9, 4)]
    assert early[0].narrative.log == ()

    later = history("asic_xpu", date(2026, 9, 6), tmp_path)
    assert [v.snapshot_date for v in later] == [date(2026, 9, 4), date(2026, 9, 6)]
    assert len(later[1].narrative.log) == 1
    assert later[1].narrative.log[0].kind == "evidence"


def test_do1_bears_on_unknown_branch_id_raises(tmp_path: Path) -> None:
    """Acceptance 4: a log entry whose bears_on points at a branch_id that no
    branch defines is a load error, not a silent dangling reference."""
    _write(
        tmp_path,
        "2026-09-08.yaml",
        """
        snapshot_date: 2026-09-08
        narratives:
          - narrative_id: asic_xpu
            name: ASIC
            first_noted: 2026-09-03
            source: podcast
            source_ref: EP694
            stance: new
            revisit: 2026-10-15
            named_symbols: []
            inferred_symbols: []
            note: n/a
            branches:
              - branch_id: real_branch
                claim: something
                basket: []
                watch: later
            log:
              - date: 2026-09-05
                source_ref: EP694
                kind: evidence
                text: bad ref
                bears_on: [ghost_branch]
        """,
    )
    with pytest.raises(ValueError, match="ghost_branch"):
        load_as_of(date(2026, 9, 9), tmp_path)


def test_do1_log_entries_after_as_of_are_filtered(tmp_path: Path) -> None:
    """R2 / §7: a log entry dated after as_of must not leak, the same way a
    narrative with first_noted > as_of is dropped."""
    _write(
        tmp_path,
        "2026-09-06.yaml",
        """
        snapshot_date: 2026-09-06
        narratives:
          - narrative_id: story
            name: Story
            first_noted: 2026-09-03
            source: self
            source_ref: x
            stance: new
            revisit: 2026-10-01
            named_symbols: []
            inferred_symbols: []
            note: n/a
            log:
              - date: 2026-09-05
                source_ref: a
                kind: claim
                text: past
                bears_on: []
              - date: 2026-09-20
                source_ref: b
                kind: evidence
                text: future
                bears_on: []
        """,
    )
    snap = load_as_of(date(2026, 9, 10), tmp_path)
    (story,) = snap.narratives
    assert [e.text for e in story.log] == ["past"]


def test_do1_branch_status_defaults_to_live(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "2026-09-06.yaml",
        """
        snapshot_date: 2026-09-06
        narratives:
          - narrative_id: story
            name: Story
            first_noted: 2026-09-03
            source: self
            source_ref: x
            stance: new
            revisit: 2026-10-01
            named_symbols: []
            inferred_symbols: []
            note: n/a
            branches:
              - branch_id: b1
                claim: c
                basket: ["1234"]
                watch: w
        """,
    )
    snap = load_as_of(date(2026, 9, 10), tmp_path)
    (story,) = snap.narratives
    assert story.branches[0].status == "live"
    assert story.branches[0].basket == ("1234",)


def test_do1_new_2026_09_06_sample_file_parses() -> None:
    """The real narratives/2026-09-06.yaml (EP694 written up) must load and
    exercise the new fields."""
    snap = load_as_of(date(2026, 9, 6), REPO_ROOT / "narratives")
    assert snap.snapshot_date == date(2026, 9, 6)
    by_id = {n.narrative_id: n for n in snap.narratives}
    asic = by_id["asic_xpu"]
    assert asic.revisit
    assert {b.branch_id for b in asic.branches} == {
        "mediatek_asic_share",
        "xpu_not_squeezing_gpu",
    }
    assert len(asic.log) == 1
    assert set(asic.log[0].bears_on) == {"mediatek_asic_share", "xpu_not_squeezing_gpu"}
