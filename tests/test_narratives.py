from __future__ import annotations

import textwrap
from datetime import date
from pathlib import Path

import pytest

from marketpulse.narratives import (
    COVERAGE_COVERED,
    COVERAGE_DECLARED,
    COVERAGE_PARTIAL,
    COVERAGE_UNCOVERED,
    COVERAGE_UNKNOWN,
    EMPTY_LIST,
    NARRATIVE_MISSING,
    STAGE_OPEN,
    TITLE_RECENT_EVENTS,
    TITLE_REVISIT_CONDITIONAL,
    TITLE_REVISIT_DUE,
    TITLE_STORY_PROGRESS,
    Branch,
    Narrative,
    NarrativeSnapshot,
    history,
    load_as_of,
    load_as_of_lenient,
    out_of_classification_symbols,
    pending_snapshots,
    render_pending_snapshots,
    parse_revisit_date,
    render_revisit_due,
    render_story_progress,
    story_last_changed,
    theme_last_mention_dates,
    theme_mention_dates,
    unknown_either_way_theme_ids,
    unknown_theme_ids,
    weak_rank_threshold,
)
from marketpulse.narratives import coverage_report as narrative_coverage_report
from marketpulse.themes import Theme, ThemeSet, load_themes

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
    assert story.branches[0].if_true == ("1234",)  # legacy `basket:` → if_true (014 F2)


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


# ── sprint 007 DO-1: theme mention dates (inverse of coverage_report) ──


def test_weak_rank_threshold_is_ceil_half() -> None:
    assert weak_rank_threshold(11) == 6
    assert weak_rank_threshold(10) == 5
    assert weak_rank_threshold(1) == 1
    assert weak_rank_threshold(0) == 0


def test_theme_mention_dates_real_snapshot_mixes_declared_and_named() -> None:
    """Sprint 008 DO-1: on the real 2026-09-06 snapshot, optical_cpo now
    carries `theme_ids: [optical_cpo]` so it is mentioned by declaration;
    foundry_advanced is still mentioned only through the named_symbols
    fallback (nvhbm names 2330). 2454 (asic_xpu) still hits nothing."""
    themes = load_themes(REPO_ROOT / "themes" / "v1.yaml")
    snapshot = load_as_of(date(2026, 9, 6), REPO_ROOT / "narratives")
    dates = theme_mention_dates(snapshot, themes)
    assert dates["foundry_advanced"] == date(2026, 9, 6)  # named_symbols fallback
    assert dates["optical_cpo"] == date(2026, 9, 6)  # theme_ids declaration
    assert dates["memory"] is None
    assert dates["ai_server"] is None
    mentioned = {tid for tid, when in dates.items() if when is not None}
    assert mentioned == {"foundry_advanced", "optical_cpo"}


def test_theme_mention_dates_pit_empty_when_snapshots_postdate_as_of() -> None:
    themes = load_themes(REPO_ROOT / "themes" / "v1.yaml")
    snapshot = load_as_of(date(2026, 9, 3), REPO_ROOT / "narratives")
    assert snapshot.snapshot_date is None
    dates = theme_mention_dates(snapshot, themes)
    assert all(when is None for when in dates.values())


def test_load_as_of_lenient_broken_file_returns_message(tmp_path: Path) -> None:
    (tmp_path / "2026-09-06.yaml").write_text("this is not: [valid yaml: {{", encoding="utf-8")
    snapshot, error = load_as_of_lenient(date(2026, 9, 6), tmp_path)
    assert snapshot.narratives == ()
    assert snapshot.snapshot_date is None
    assert error is not None
    assert error.startswith("narrative 讀取失敗：")


def test_load_as_of_lenient_missing_dir_is_empty(tmp_path: Path) -> None:
    missing = tmp_path / "no-such"
    snapshot, error = load_as_of_lenient(date(2026, 9, 6), missing)
    assert error is None
    assert snapshot.narratives == ()
    assert snapshot.snapshot_date is None


# ── sprint 007 DO-2: revisit due (read-only) ──


def _fingerprint(dir_: Path) -> dict[str, tuple[int, bytes]]:
    out: dict[str, tuple[int, bytes]] = {}
    for path in sorted(dir_.glob("*.yaml")):
        st = path.stat()
        out[path.name] = (st.st_mtime_ns, path.read_bytes())
    return out


def _narrative(
    nid: str,
    *,
    revisit: str,
    claim: str = "claim text here",
    branches: tuple[Branch, ...] = (),
    note: str = "note",
) -> Narrative:
    return Narrative(
        narrative_id=nid,
        name=nid,
        first_noted=date(2026, 9, 1),
        source="self",
        source_ref="x",
        stance="new",
        named_symbols=(),
        inferred_symbols=(),
        note=note,
        revisit=revisit,
        branches=branches,
    )


def test_parse_revisit_date_iso_only_no_nlp() -> None:
    assert parse_revisit_date("2026-10-15") == date(2026, 10, 15)
    assert parse_revisit_date("2026-10-15 或 Broadcom 下一次財報電話會議（以先到者為準）") is None
    assert parse_revisit_date("台積電 2026-10 法說") is None
    assert parse_revisit_date("2026-10-01；若 optical_cpo 主題 rank 跌出前 3 則提前重評") is None
    assert parse_revisit_date("") is None


def test_render_revisit_due_date_type_and_conditional() -> None:
    snap = NarrativeSnapshot(
        snapshot_date=date(2026, 9, 6),
        narratives=(
            _narrative(
                "due_one",
                revisit="2026-09-01",
                branches=(
                    Branch("b1", "this claim is definitely longer than thirty chars",
                           if_true=("1",), watch="w", status="live"),
                ),
            ),
            _narrative("future_one", revisit="2026-12-01"),
            _narrative("cond_one", revisit="Broadcom 下一次財報電話會議"),
        ),
    )
    text = render_revisit_due(snap, date(2026, 9, 6))
    assert TITLE_REVISIT_DUE in text
    assert TITLE_REVISIT_CONDITIONAL in text
    due, cond = text.split(TITLE_REVISIT_CONDITIONAL, 1)
    assert "due_one · b1 · 2026-09-01 · this claim is definitely longe" in due
    assert "future_one" not in due
    assert "cond_one · Broadcom 下一次財報電話會議" in cond
    assert "future_one" not in cond


def test_render_revisit_due_empty_prints_placeholder() -> None:
    snap = NarrativeSnapshot(snapshot_date=None, narratives=())
    text = render_revisit_due(snap, date(2026, 9, 6))
    assert TITLE_REVISIT_DUE in text
    assert TITLE_REVISIT_CONDITIONAL in text
    due, cond = text.split(TITLE_REVISIT_CONDITIONAL, 1)
    assert EMPTY_LIST in due
    assert EMPTY_LIST in cond


def test_revisit_due_does_not_change_narratives_mtime_or_bytes() -> None:
    """spec 007 DO-2 acceptance 3. Named so evidence can point at it."""
    n_dir = REPO_ROOT / "narratives"
    before = _fingerprint(n_dir)
    snap = load_as_of(date(2026, 9, 6), n_dir)
    render_revisit_due(snap, date(2026, 9, 6))
    render_revisit_due(snap, date(2026, 12, 31))
    load_as_of_lenient(date(2026, 9, 6), n_dir)
    after = _fingerprint(n_dir)
    assert after == before
    assert before, "narratives/ should not be empty"


# ── sprint 008 DO-1: theme_ids (declare the theme before symbols converge) ──


def _themes_ab() -> ThemeSet:
    return ThemeSet(
        classification_version="test",
        taxonomy_frozen_at="2026-01-01",
        notes="",
        themes=(
            Theme("t_a", "主題A", ("A01", "A02")),
            Theme("t_b", "主題B", ("B01", "B02")),
        ),
    )


def _narr(nid: str, *, theme_ids=(), named=()) -> Narrative:
    return Narrative(
        narrative_id=nid,
        name=nid,
        first_noted=date(2026, 9, 1),
        source="self",
        source_ref="x",
        stance="new",
        named_symbols=tuple(named),
        inferred_symbols=(),
        note="",
        theme_ids=tuple(theme_ids),
    )


def test_do1_theme_ids_declared_status_and_mention() -> None:
    """Explicit: a narrative that lists theme_ids gets coverage `declared`
    (fifth state, alongside the four), and its themes are mentioned even
    when named_symbols is empty."""
    snap = NarrativeSnapshot(
        snapshot_date=date(2026, 9, 6),
        narratives=(_narr("story", theme_ids=("t_a",)),),
    )
    themes = _themes_ab()
    assert narrative_coverage_report(snap, themes)["story"] == COVERAGE_DECLARED
    dates = theme_mention_dates(snap, themes)
    assert dates["t_a"] == date(2026, 9, 6)
    assert dates["t_b"] is None


def test_do1_empty_theme_ids_falls_back_to_named_symbols() -> None:
    """Empty theme_ids: the pre-008 named_symbols path is unchanged."""
    snap = NarrativeSnapshot(
        snapshot_date=date(2026, 9, 6),
        narratives=(_narr("story", named=("A01",)),),
    )
    themes = _themes_ab()
    assert narrative_coverage_report(snap, themes)["story"] == COVERAGE_COVERED
    assert theme_mention_dates(snap, themes)["t_a"] == date(2026, 9, 6)


def test_do1_theme_ids_beats_named_symbols_when_both_present() -> None:
    """Priority is fixed: theme_ids wins, named_symbols is not also counted."""
    snap = NarrativeSnapshot(
        snapshot_date=date(2026, 9, 6),
        narratives=(_narr("story", theme_ids=("t_a",), named=("B01",)),),
    )
    themes = _themes_ab()
    assert narrative_coverage_report(snap, themes)["story"] == COVERAGE_DECLARED
    dates = theme_mention_dates(snap, themes)
    assert dates["t_a"] == date(2026, 9, 6)
    assert dates["t_b"] is None  # B01 membership is NOT consulted


def test_do1_unknown_theme_id_is_surfaced_not_raised(tmp_path: Path) -> None:
    """Acceptance 4: a theme_id not in themes/v1.yaml does not blow up the
    load; unknown_theme_ids() reports it so the screen can show it."""
    _write(
        tmp_path,
        "2026-09-06.yaml",
        """
        snapshot_date: 2026-09-06
        narratives:
          - narrative_id: typo_story
            name: Typo
            first_noted: 2026-09-03
            source: self
            source_ref: x
            stance: new
            revisit: 2026-10-01
            theme_ids: [optical_cpo, opitcal_cpo]
            named_symbols: []
            inferred_symbols: []
            note: n/a
        """,
    )
    snap = load_as_of(date(2026, 9, 6), tmp_path)  # must not raise
    themes = load_themes(REPO_ROOT / "themes" / "v1.yaml")
    assert unknown_theme_ids(snap, themes) == {"typo_story": ("opitcal_cpo",)}
    # the real theme in the same list is still mentioned
    assert theme_mention_dates(snap, themes)["optical_cpo"] == date(2026, 9, 6)


def test_do1_out_of_classification_lists_named_symbols_in_no_theme() -> None:
    """Acceptance 3: asic_xpu's 2454 is in no theme → listed. nvhbm's 2330
    is in foundry_advanced → not listed. Declared themes are irrelevant here
    (this block is about named_symbols)."""
    themes = load_themes(REPO_ROOT / "themes" / "v1.yaml")
    snap = load_as_of(date(2026, 9, 6), REPO_ROOT / "narratives")
    pairs = out_of_classification_symbols(snap, themes)
    assert ("asic_xpu", "2454") in pairs
    assert all(nid != "nvhbm" for nid, _ in pairs)


def test_do1_optical_cpo_real_file_declares_its_theme() -> None:
    """The one real-file edit this sprint: optical_cpo now carries
    theme_ids: [optical_cpo]. nvhbm (no theme_ids) still falls back to 2330
    → foundry_advanced. asic_xpu still uncovered."""
    themes = load_themes(REPO_ROOT / "themes" / "v1.yaml")
    snap = load_as_of(date(2026, 9, 6), REPO_ROOT / "narratives")
    report = narrative_coverage_report(snap, themes)
    assert report["optical_cpo"] == COVERAGE_DECLARED
    assert report["nvhbm"] == COVERAGE_COVERED
    assert report["asic_xpu"] == COVERAGE_UNCOVERED


# ── sprint 008 DO-2: 故事進度 / 最近事件 (facts and dates only) ──

_SNAP_0904 = """
snapshot_date: 2026-09-04
narratives:
  - narrative_id: s1
    name: S1
    first_noted: 2026-09-03
    source: self
    source_ref: x
    stance: new
    named_symbols: ["2454"]
    inferred_symbols: []
    note: first
"""

_SNAP_0906 = """
snapshot_date: 2026-09-06
narratives:
  - narrative_id: s1
    name: S1
    first_noted: 2026-09-03
    source: self
    source_ref: x
    stance: new
    stage: mapped
    revisit: 2026-10-15
    named_symbols: ["2454"]
    inferred_symbols: []
    note: second
    log:
      - date: 2026-09-05
        source_ref: EP694
        kind: evidence
        text: >
          this is a fairly long event text that should be truncated to forty chars
        bears_on: []
"""


def test_do2_story_last_changed_two_snapshots(tmp_path: Path) -> None:
    _write(tmp_path, "2026-09-04.yaml", _SNAP_0904)
    _write(tmp_path, "2026-09-06.yaml", _SNAP_0906)
    assert story_last_changed("s1", date(2026, 9, 6), tmp_path) == date(2026, 9, 6)


def test_do2_story_last_changed_single_snapshot_is_none(tmp_path: Path) -> None:
    _write(tmp_path, "2026-09-04.yaml", _SNAP_0904)
    assert story_last_changed("s1", date(2026, 9, 6), tmp_path) is None


def test_do2_render_story_progress_two_snapshots(tmp_path: Path) -> None:
    _write(tmp_path, "2026-09-04.yaml", _SNAP_0904)
    _write(tmp_path, "2026-09-06.yaml", _SNAP_0906)
    snap = load_as_of(date(2026, 9, 6), tmp_path)
    text = render_story_progress(snap, date(2026, 9, 6), tmp_path)
    assert TITLE_STORY_PROGRESS in text
    assert TITLE_RECENT_EVENTS in text
    assert "s1 · mapped · 1代號 · 2026-09-06" in text
    event = [ln for ln in text.splitlines() if ln.startswith("s1 · 2026-09-05")][0]
    # narrative_id · date · 40 chars of text, whitespace-collapsed
    assert event == "s1 · 2026-09-05 · this is a fairly long event text that sh"


def test_do2_render_story_progress_single_snapshot_prints_dash(tmp_path: Path) -> None:
    _write(tmp_path, "2026-09-04.yaml", _SNAP_0904)
    snap = load_as_of(date(2026, 9, 6), tmp_path)
    text = render_story_progress(snap, date(2026, 9, 6), tmp_path)
    assert f"s1 · open · 1代號 · {NARRATIVE_MISSING}" in text
    # no log entries yet
    recent = text.split(TITLE_RECENT_EVENTS, 1)[1]
    assert EMPTY_LIST in recent


def test_do2_render_story_progress_no_narratives_prints_placeholder() -> None:
    text = render_story_progress(NarrativeSnapshot(None, ()), date(2026, 9, 6))
    assert TITLE_STORY_PROGRESS in text and TITLE_RECENT_EVENTS in text
    prog, recent = text.split(TITLE_RECENT_EVENTS, 1)
    assert EMPTY_LIST in prog and EMPTY_LIST in recent


def test_do2_story_progress_has_no_heat_or_trend_words(tmp_path: Path) -> None:
    """兔子洞: facts and dates only — no 熱度 / 爆發 / 加速 / 轉強 / arrow / score."""
    _write(tmp_path, "2026-09-04.yaml", _SNAP_0904)
    _write(tmp_path, "2026-09-06.yaml", _SNAP_0906)
    snap = load_as_of(date(2026, 9, 6), tmp_path)
    text = render_story_progress(snap, date(2026, 9, 6), tmp_path)
    for banned in ("熱", "爆發", "加速", "轉強", "↑", "↓", "→", "分數", "score"):
        assert banned not in text


def test_do2_render_story_progress_does_not_write_narratives() -> None:
    """spec 008 DO-2 acceptance 5 (reuses 007's fingerprint approach)."""
    n_dir = REPO_ROOT / "narratives"
    before = _fingerprint(n_dir)
    snap = load_as_of(date(2026, 9, 6), n_dir)
    render_story_progress(snap, date(2026, 9, 6), n_dir)
    story_last_changed("optical_cpo", date(2026, 9, 6), n_dir)
    assert _fingerprint(n_dir) == before
    assert before, "narratives/ should not be empty"


def test_do2_real_snapshots_stage_and_change_date() -> None:
    """Acceptance 2 + 3 on the real 09-04 / 09-06 files."""
    n_dir = REPO_ROOT / "narratives"
    snap = load_as_of(date(2026, 9, 6), n_dir)
    stages = {n.narrative_id: n.stage for n in snap.narratives}
    assert stages == {"asic_xpu": "open", "nvhbm": "open", "optical_cpo": "mapped"}
    for nid in ("asic_xpu", "optical_cpo", "nvhbm"):
        assert story_last_changed(nid, date(2026, 9, 6), n_dir) == date(2026, 9, 6)


# ── sprint 008 DO-3 B2: theme_last_mention_dates scans every snapshot ──


def test_do3_b2_last_mention_scans_all_snapshots(tmp_path: Path) -> None:
    """Two snapshots, different themes mentioned on each → the column can now
    show different dates, not one boolean-shaped snapshot_date."""
    _write(
        tmp_path,
        "2026-09-04.yaml",
        """
        snapshot_date: 2026-09-04
        narratives:
          - narrative_id: n_a
            name: A
            first_noted: 2026-09-03
            source: self
            source_ref: x
            stance: new
            named_symbols: ["A01"]
            inferred_symbols: []
            note: n/a
        """,
    )
    _write(
        tmp_path,
        "2026-09-06.yaml",
        """
        snapshot_date: 2026-09-06
        narratives:
          - narrative_id: n_b
            name: B
            first_noted: 2026-09-03
            source: self
            source_ref: x
            stance: new
            revisit: 2026-10-01
            named_symbols: ["B01"]
            inferred_symbols: []
            note: n/a
        """,
    )
    dates = theme_last_mention_dates(date(2026, 9, 6), _themes_ab(), tmp_path)
    assert dates["t_a"] == date(2026, 9, 4)
    assert dates["t_b"] == date(2026, 9, 6)


def test_do3_b2_last_mention_takes_latest_when_theme_recurs(tmp_path: Path) -> None:
    for d in ("2026-09-04", "2026-09-06"):
        _write(
            tmp_path,
            f"{d}.yaml",
            f"""
            snapshot_date: {d}
            narratives:
              - narrative_id: n_a
                name: A
                first_noted: 2026-09-03
                source: self
                source_ref: x
                stance: new
                revisit: 2026-10-01
                named_symbols: ["A01"]
                inferred_symbols: []
                note: n/a
            """,
        )
    dates = theme_last_mention_dates(date(2026, 9, 6), _themes_ab(), tmp_path)
    assert dates["t_a"] == date(2026, 9, 6)
    assert dates["t_b"] is None


# ── sprint 009 DO-2: pending snapshots (filesystem fact, not PIT) ──


def test_do2_pending_snapshots_lists_date_and_filename_only(tmp_path: Path) -> None:
    from marketpulse.narratives import PENDING_PIT_NOTE, TITLE_PENDING

    _write(
        tmp_path,
        "2026-09-04.yaml",
        """
        snapshot_date: 2026-09-04
        narratives:
          - narrative_id: now
            name: now
            first_noted: 2026-09-01
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
        "2026-09-06.yaml",
        """
        snapshot_date: 2026-09-06
        narratives:
          - narrative_id: future
            name: future
            first_noted: 2026-09-01
            source: self
            source_ref: x
            stance: new
            named_symbols: ["SHOULD_NOT_BE_READ"]
            inferred_symbols: []
            note: this body must not affect coverage
        """,
    )
    as_of = date(2026, 9, 4)
    assert pending_snapshots(as_of, tmp_path) == [
        (date(2026, 9, 6), "2026-09-06.yaml")
    ]
    text = render_pending_snapshots(as_of, tmp_path)
    assert text.splitlines()[0] == TITLE_PENDING
    assert text.splitlines()[1] == "2026-09-06 · 2026-09-06.yaml"
    assert text.splitlines()[2] == PENDING_PIT_NOTE.format(as_of="2026-09-04")
    assert "SHOULD_NOT_BE_READ" not in text
    assert "future" not in text.splitlines()[1]


def test_do2_pending_snapshots_empty_prints_placeholder(tmp_path: Path) -> None:
    from marketpulse.narratives import TITLE_PENDING

    _write(
        tmp_path,
        "2026-09-04.yaml",
        """
        snapshot_date: 2026-09-04
        narratives: []
        """,
    )
    text = render_pending_snapshots(date(2026, 9, 4), tmp_path)
    assert text.splitlines() == [TITLE_PENDING, EMPTY_LIST]


def test_do2_pending_file_does_not_change_coverage_byte_for_byte(tmp_path: Path) -> None:
    """Acceptance 2: a snapshot_date > as_of file must not change
    coverage_report / theme_mention_dates / theme_last_mention_dates /
    story_last_changed / load_as_of. The pending list is the only new
    surface that can see it."""
    _write(
        tmp_path,
        "2026-09-04.yaml",
        """
        snapshot_date: 2026-09-04
        narratives:
          - narrative_id: story
            name: story
            first_noted: 2026-09-01
            source: self
            source_ref: x
            stance: new
            named_symbols: ["A01"]
            inferred_symbols: []
            note: n/a
        """,
    )
    themes = _themes_ab()
    as_of = date(2026, 9, 4)
    before_snap = load_as_of(as_of, tmp_path)
    before = {
        "coverage": narrative_coverage_report(before_snap, themes),
        "mentions": theme_mention_dates(before_snap, themes),
        "last": theme_last_mention_dates(as_of, themes, tmp_path),
        "changed": story_last_changed("story", as_of, tmp_path),
        "ids": tuple(n.narrative_id for n in before_snap.narratives),
        "snap_date": before_snap.snapshot_date,
    }

    _write(
        tmp_path,
        "2026-09-06.yaml",
        """
        snapshot_date: 2026-09-06
        narratives:
          - narrative_id: story
            name: story
            first_noted: 2026-09-01
            source: self
            source_ref: x
            stance: new
            revisit: 2026-10-01
            theme_ids: [t_b]
            named_symbols: ["B01"]
            inferred_symbols: []
            note: would flip coverage if leaked
        """,
    )
    after_snap = load_as_of(as_of, tmp_path)
    after = {
        "coverage": narrative_coverage_report(after_snap, themes),
        "mentions": theme_mention_dates(after_snap, themes),
        "last": theme_last_mention_dates(as_of, themes, tmp_path),
        "changed": story_last_changed("story", as_of, tmp_path),
        "ids": tuple(n.narrative_id for n in after_snap.narratives),
        "snap_date": after_snap.snapshot_date,
    }
    assert after == before
    assert str(after["coverage"]) == str(before["coverage"])
    assert pending_snapshots(as_of, tmp_path) == [
        (date(2026, 9, 6), "2026-09-06.yaml")
    ]


def test_do2_pending_real_narratives_dir_as_of_latest_price_day() -> None:
    """Live files: as_of=2026-09-04 (latest price day as of this sprint)
    includes 2026-09-06.yaml; every listed snapshot_date is after as_of."""
    as_of = date(2026, 9, 4)
    found = pending_snapshots(as_of, REPO_ROOT / "narratives")
    assert (date(2026, 9, 6), "2026-09-06.yaml") in found
    assert all(d > as_of for d, _ in found)


# ── spec 010 DO-3.2: overflow notes for 尚未生效 / 最近事件 ──


_PENDING_EMPTY = "snapshot_date: {d}\nnarratives: []\n"


def _events_snap(n_events: int) -> str:
    head = (
        "snapshot_date: 2026-09-04\n"
        "narratives:\n"
        "  - narrative_id: s1\n"
        "    name: S1\n"
        "    first_noted: 2026-09-01\n"
        "    source: self\n"
        "    source_ref: x\n"
        "    stance: new\n"
        "    named_symbols: []\n"
        "    inferred_symbols: []\n"
        "    note: n/a\n"
        "    log:\n"
    )
    days = ["2026-09-01", "2026-09-02", "2026-09-03", "2026-09-04", "2026-09-05"]
    body = "".join(
        f"      - date: {days[i]}\n"
        f"        source_ref: r\n"
        f"        kind: evidence\n"
        f"        text: event {i}\n"
        f"        bears_on: []\n"
        for i in range(n_events)
    )
    return head + body


def test_c3_pending_snapshots_overflow_line_beyond_the_cap(tmp_path: Path) -> None:
    """C3: exactly PENDING_LIMIT pending → no overflow line; a 4th → still 3
    shown plus `還有 1 份`. The cap itself is unchanged."""
    from marketpulse.narratives import PENDING_LIMIT, PENDING_OVERFLOW_NOTE, TITLE_PENDING

    as_of = date(2026, 9, 4)
    for d in ("2026-09-05", "2026-09-06", "2026-09-07"):
        _write(tmp_path, f"{d}.yaml", _PENDING_EMPTY.format(d=d))
    text3 = render_pending_snapshots(as_of, tmp_path)
    shown3 = [ln for ln in text3.splitlines() if ln.startswith("2026-09-0")]
    assert len(shown3) == PENDING_LIMIT == 3
    assert "還有" not in text3

    _write(tmp_path, "2026-09-08.yaml", _PENDING_EMPTY.format(d="2026-09-08"))
    text4 = render_pending_snapshots(as_of, tmp_path)
    shown4 = [ln for ln in text4.splitlines() if ln.startswith("2026-09-0")]
    assert len(shown4) == 3  # cap unchanged
    assert PENDING_OVERFLOW_NOTE.format(n=1) in text4
    assert "還有 1 份" in text4
    assert text4.splitlines()[0] == TITLE_PENDING
    # newest-not-required: the three oldest pending are the ones shown
    assert shown4 == ["2026-09-05 · 2026-09-05.yaml", "2026-09-06 · 2026-09-06.yaml",
                      "2026-09-07 · 2026-09-07.yaml"]


def test_c3_recent_events_overflow_line_beyond_the_cap(tmp_path: Path) -> None:
    """C3, 最近事件 half: exactly RECENT_EVENTS_LIMIT log entries → no
    overflow line; a 4th → 3 shown plus `還有 1 筆`."""
    from marketpulse.narratives import RECENT_EVENTS_LIMIT, RECENT_EVENTS_OVERFLOW_NOTE

    _write(tmp_path, "2026-09-04.yaml", _events_snap(RECENT_EVENTS_LIMIT))
    snap3 = load_as_of(date(2026, 9, 4), tmp_path)
    text3 = render_story_progress(snap3, date(2026, 9, 4), tmp_path)
    recent3 = text3.split(TITLE_RECENT_EVENTS, 1)[1]
    assert recent3.count("s1 · 2026-09-0") == 3
    assert "還有" not in recent3

    _write(tmp_path, "2026-09-04.yaml", _events_snap(RECENT_EVENTS_LIMIT + 1))
    snap4 = load_as_of(date(2026, 9, 4), tmp_path)
    text4 = render_story_progress(snap4, date(2026, 9, 4), tmp_path)
    recent4 = text4.split(TITLE_RECENT_EVENTS, 1)[1]
    assert recent4.count("s1 · 2026-09-0") == 3
    assert RECENT_EVENTS_OVERFLOW_NOTE.format(n=1) in recent4
    assert "還有 1 筆" in recent4


def test_c4_do3_2_leaves_the_five_pinned_functions_untouched(tmp_path: Path) -> None:
    """C4: DO-3.2 must not change load_as_of / theme_mention_dates /
    theme_last_mention_dates / weak_rank_threshold /
    out_of_classification_symbols. Behavioural guard for the git-diff-empty
    claim in the evidence."""
    assert [weak_rank_threshold(n) for n in (0, 1, 10, 11)] == [0, 1, 5, 6]

    _write(
        tmp_path,
        "2026-09-02.yaml",
        """
        snapshot_date: 2026-09-02
        narratives:
          - narrative_id: early
            name: early
            first_noted: 2026-09-01
            source: self
            source_ref: x
            stance: new
            named_symbols: ["A01"]
            inferred_symbols: []
            note: n/a
        """,
    )
    _write(
        tmp_path,
        "2026-09-06.yaml",
        """
        snapshot_date: 2026-09-06
        narratives:
          - narrative_id: later
            name: later
            first_noted: 2026-09-01
            source: self
            source_ref: x
            stance: new
            revisit: 2026-10-01
            named_symbols: []
            inferred_symbols: []
            note: n/a
        """,
    )
    themes = _themes_ab()
    snap = load_as_of(date(2026, 9, 6), tmp_path)
    assert snap.snapshot_date == date(2026, 9, 6)
    assert tuple(n.narrative_id for n in snap.narratives) == ("later",)
    # latest PIT snapshot mentions no theme; the earlier one mentioned t_a
    assert theme_mention_dates(snap, themes)["t_a"] is None
    last = theme_last_mention_dates(date(2026, 9, 6), themes, tmp_path)
    assert last["t_a"] == date(2026, 9, 2)
    assert last["t_b"] is None

    ooc = NarrativeSnapshot(date(2026, 9, 6), (_narr("x", named=("ZZZ",)),))
    assert out_of_classification_symbols(ooc, themes) == [("x", "ZZZ")]


# ── sprint 009 DO-3 F5 / F6 ──


def test_do3_f5_all_invalid_theme_ids_fall_back_to_named_symbols() -> None:
    """All theme_ids unknown → not `declared`; four-state named_symbols
    path runs. unknown_theme_ids still lists the typos (008 must not
    disappear)."""
    themes = _themes_ab()
    n = _narr("typo_only", theme_ids=("bogus",), named=("A01",))
    snap = NarrativeSnapshot(date(2026, 9, 6), (n,))
    assert narrative_coverage_report(snap, themes)["typo_only"] == COVERAGE_COVERED
    assert theme_mention_dates(snap, themes)["t_a"] == date(2026, 9, 6)
    assert theme_mention_dates(snap, themes)["t_b"] is None
    assert unknown_theme_ids(snap, themes) == {"typo_only": ("bogus",)}


def test_do3_f5_all_invalid_theme_ids_without_named_is_unknown() -> None:
    themes = _themes_ab()
    n = _narr("empty_typo", theme_ids=("bogus",))
    snap = NarrativeSnapshot(date(2026, 9, 6), (n,))
    assert narrative_coverage_report(snap, themes)["empty_typo"] == COVERAGE_UNKNOWN
    assert unknown_theme_ids(snap, themes) == {"empty_typo": ("bogus",)}
    assert theme_mention_dates(snap, themes)["t_a"] is None


def test_do3_f5_mixed_valid_and_invalid_still_declared() -> None:
    """A valid sibling still counts as declared; the typo is only a notice."""
    themes = _themes_ab()
    n = _narr("mix", theme_ids=("t_a", "bogus"), named=("B01",))
    snap = NarrativeSnapshot(date(2026, 9, 6), (n,))
    assert narrative_coverage_report(snap, themes)["mix"] == COVERAGE_DECLARED
    dates = theme_mention_dates(snap, themes)
    assert dates["t_a"] == date(2026, 9, 6)
    assert dates["t_b"] is None  # named_symbols not consulted
    assert unknown_theme_ids(snap, themes) == {"mix": ("bogus",)}


def test_do3_f6_coverage_and_mentioned_agree_on_the_same_narrative() -> None:
    """spec 009 DO-3 F6: coverage_report and _mentioned_theme_ids share one
    membership test. For any one narrative, declared ↔ mentioned equals
    the valid theme_ids; four-state covered/partial ↔ mentioned equals
    named ∩ members; unknown/uncovered ↔ mentioned empty."""
    from marketpulse.narratives import _member_sets, _mentioned_theme_ids

    themes = _themes_ab()
    member_sets = _member_sets(themes)
    cases = [
        _narr("declared", theme_ids=("t_a",)),
        _narr("mix", theme_ids=("t_a", "nope"), named=("B01",)),
        _narr("fallback", theme_ids=("nope",), named=("A01",)),
        _narr("covered", named=("A01",)),
        _narr("partial", named=("A01", "ZZZ")),
        _narr("uncovered", named=("ZZZ",)),
        _narr("unknown"),
        _narr("all_bad", theme_ids=("nope", "also_nope")),
    ]
    for narrative in cases:
        snap = NarrativeSnapshot(date(2026, 9, 6), (narrative,))
        status = narrative_coverage_report(snap, themes)[narrative.narrative_id]
        mentioned = _mentioned_theme_ids(narrative, member_sets)
        via_dates = {
            tid for tid, d in theme_mention_dates(snap, themes).items() if d is not None
        }
        assert mentioned == via_dates
        if status == COVERAGE_DECLARED:
            assert mentioned == {tid for tid in narrative.theme_ids if tid in member_sets}
            assert mentioned
        elif status in (COVERAGE_UNKNOWN, COVERAGE_UNCOVERED):
            assert mentioned == set()
        elif status in (COVERAGE_COVERED, COVERAGE_PARTIAL):
            named = set(narrative.named_symbols)
            assert mentioned == {
                tid for tid, members in member_sets.items() if named & members
            }
            assert mentioned
        else:
            raise AssertionError(f"unexpected status {status} for {narrative.narrative_id}")


# ── sprint 014 DO-1: one branch, three baskets ──


def _branch_yaml(tmp_path: Path, branch_body: str, *, name: str = "2026-09-10.yaml") -> Path:
    (tmp_path / name).write_text(
        textwrap.dedent(
            f"""
            snapshot_date: 2026-09-10
            narratives:
              - narrative_id: n1
                name: N1
                first_noted: 2026-09-01
                source: self
                source_ref: x
                stance: new
                revisit: 2026-10-01
                named_symbols: []
                inferred_symbols: []
                note: n/a
                branches:
{textwrap.indent(textwrap.dedent(branch_body).strip(), " " * 18)}
            """
        ),
        encoding="utf-8",
    )
    return tmp_path


def test_do1_legacy_basket_reads_as_if_true_others_empty(tmp_path: Path) -> None:
    """F2: a branch that writes only the old `basket:` puts those symbols in
    `if_true`, and the other two baskets are empty."""
    _branch_yaml(
        tmp_path,
        """
        - branch_id: b
          claim: c
          basket: ["1234", "5678"]
          watch: w
        """,
    )
    (story,) = load_as_of(date(2026, 9, 10), tmp_path).narratives
    (branch,) = story.branches
    assert branch.if_true == ("1234", "5678")
    assert branch.if_false == ()
    assert branch.either_way == ()


def test_do1_three_keys_each_parse(tmp_path: Path) -> None:
    _branch_yaml(
        tmp_path,
        """
        - branch_id: b
          claim: c
          baskets:
            if_true: ["1234"]
            if_false: ["5678", "9012"]
            either_way: [optical_cpo, foundry_advanced]
          watch: w
        """,
    )
    (story,) = load_as_of(date(2026, 9, 10), tmp_path).narratives
    (branch,) = story.branches
    assert branch.if_true == ("1234",)
    assert branch.if_false == ("5678", "9012")
    assert branch.either_way == ("optical_cpo", "foundry_advanced")


def test_do1_all_three_baskets_empty_does_not_raise(tmp_path: Path) -> None:
    _branch_yaml(
        tmp_path,
        """
        - branch_id: b
          claim: c
          baskets: {}
          watch: w
        """,
    )
    (story,) = load_as_of(date(2026, 9, 10), tmp_path).narratives
    (branch,) = story.branches
    assert (branch.if_true, branch.if_false, branch.either_way) == ((), (), ())


def test_do1_branch_with_no_basket_field_at_all_does_not_raise(tmp_path: Path) -> None:
    _branch_yaml(
        tmp_path,
        """
        - branch_id: b
          claim: c
          watch: w
        """,
    )
    (story,) = load_as_of(date(2026, 9, 10), tmp_path).narratives
    assert story.branches[0].if_true == ()


def test_do1_unknown_either_way_theme_id_is_named_not_swallowed(tmp_path: Path) -> None:
    """F4: an id that is not in themes/v1.yaml (a typo, or a stock symbol
    written into the theme-only basket) must be reportable by id."""
    _branch_yaml(
        tmp_path,
        """
        - branch_id: b
          claim: c
          baskets:
            either_way: [optical_cpo, opitcal_cpo, "2330"]
          watch: w
        """,
    )
    snap = load_as_of(date(2026, 9, 10), tmp_path)
    themes = load_themes(REPO_ROOT / "themes" / "v1.yaml")
    assert unknown_either_way_theme_ids(snap, themes) == [
        ("n1", "b", "opitcal_cpo"),
        ("n1", "b", "2330"),
    ]


def test_do1_basket_and_baskets_together_raises_naming_the_branch(tmp_path: Path) -> None:
    _branch_yaml(
        tmp_path,
        """
        - branch_id: b
          claim: c
          basket: ["1234"]
          baskets:
            if_true: ["5678"]
          watch: w
        """,
    )
    with pytest.raises(ValueError, match="b"):
        load_as_of(date(2026, 9, 10), tmp_path)


def test_do1_unknown_basket_key_raises(tmp_path: Path) -> None:
    """A typo'd key would otherwise drop a whole basket off the panel silently."""
    _branch_yaml(
        tmp_path,
        """
        - branch_id: b
          claim: c
          baskets:
            if_ture: ["1234"]
          watch: w
        """,
    )
    with pytest.raises(ValueError, match="if_ture"):
        load_as_of(date(2026, 9, 10), tmp_path)


def test_do1_real_narratives_branch_members_unchanged() -> None:
    """F1: both real snapshot files load, and every branch keeps exactly the
    members it had before 014 (they all use the legacy `basket:`)."""
    snap = load_as_of(date(2026, 9, 6), REPO_ROOT / "narratives")
    got = {
        (n.narrative_id, b.branch_id): (b.if_true, b.if_false, b.either_way)
        for n in snap.narratives
        for b in n.branches
    }
    assert got == {
        ("asic_xpu", "mediatek_asic_share"): (("2454",), (), ()),
        ("asic_xpu", "xpu_not_squeezing_gpu"): ((), (), ()),
        ("nvhbm", "hbm4_base_die_tsmc"): (("2330",), (), ()),
    }
    assert load_as_of(date(2026, 9, 4), REPO_ROOT / "narratives").snapshot_date == date(2026, 9, 4)


# ── sprint 014 DO-3: the revisit date and its condition are two fields ──


def _revisit_yaml(tmp_path: Path, fields: str, *, snapshot_date: str = "2026-09-10") -> Path:
    (tmp_path / f"{snapshot_date}.yaml").write_text(
        textwrap.dedent(
            f"""
            snapshot_date: {snapshot_date}
            narratives:
              - narrative_id: n1
                name: N1
                first_noted: 2026-09-01
                source: self
                source_ref: x
                stance: new
                named_symbols: []
                inferred_symbols: []
                note: note text
{textwrap.indent(textwrap.dedent(fields).strip(), " " * 16)}
            """
        ),
        encoding="utf-8",
    )
    return tmp_path


def test_do3_iso_revisit_at_or_before_as_of_is_due_not_conditional(tmp_path: Path) -> None:
    """F11."""
    _revisit_yaml(tmp_path, "revisit: 2026-09-10")
    snap = load_as_of(date(2026, 9, 10), tmp_path)
    due, cond = render_revisit_due(snap, date(2026, 9, 10)).split(TITLE_REVISIT_CONDITIONAL, 1)
    assert "n1 · — · 2026-09-10" in due
    assert "n1" not in cond
    assert EMPTY_LIST in cond


def test_do3_iso_revisit_after_as_of_is_in_neither_block(tmp_path: Path) -> None:
    _revisit_yaml(tmp_path, "revisit: 2026-12-01")
    snap = load_as_of(date(2026, 9, 10), tmp_path)
    text = render_revisit_due(snap, date(2026, 9, 10))
    due, cond = text.split(TITLE_REVISIT_CONDITIONAL, 1)
    assert "n1" not in due and "n1" not in cond


def test_do3_revisit_note_rides_along_on_the_same_line(tmp_path: Path) -> None:
    """F12: the date decides the block, the note is shown next to it."""
    _revisit_yaml(
        tmp_path,
        """
        revisit: 2026-10-15
        revisit_note: 或 Broadcom 下一次財報電話會議（以先到者為準）
        """,
    )
    snap = load_as_of(date(2026, 10, 20), tmp_path)
    (story,) = snap.narratives
    assert story.revisit == "2026-10-15"
    assert story.revisit_note == "或 Broadcom 下一次財報電話會議（以先到者為準）"
    due, cond = render_revisit_due(snap, date(2026, 10, 20)).split(
        TITLE_REVISIT_CONDITIONAL, 1
    )
    (line,) = [ln for ln in due.splitlines() if ln.startswith("n1")]
    assert "2026-10-15" in line
    assert "或 Broadcom 下一次財報電話會議（以先到者為準）" in line
    assert "n1" not in cond


def test_do3_legacy_free_text_revisit_still_conditional_and_does_not_raise(
    tmp_path: Path,
) -> None:
    """F13: exactly the pre-014 behaviour for a file that never split the field."""
    _revisit_yaml(tmp_path, "revisit: 2026-10-15 或 Broadcom 下一次財報電話會議（以先到者為準）")
    snap = load_as_of(date(2026, 10, 20), tmp_path)
    assert parse_revisit_date(snap.narratives[0].revisit) is None
    due, cond = render_revisit_due(snap, date(2026, 10, 20)).split(
        TITLE_REVISIT_CONDITIONAL, 1
    )
    assert "n1" not in due
    assert "n1 · 2026-10-15 或 Broadcom 下一次財報電話會議（以先到者為準）" in cond


def test_do3_empty_revisit_still_raises_after_the_004_cutoff(tmp_path: Path) -> None:
    """F14: `revisit_note` does not satisfy the required-field rule."""
    _revisit_yaml(tmp_path, "revisit_note: Broadcom 下一次財報電話會議")
    with pytest.raises(ValueError, match="revisit"):
        load_as_of(date(2026, 9, 10), tmp_path)


def test_do3_real_narratives_are_all_still_conditional() -> None:
    """This sprint does not touch narratives/, so all three stories keep their
    free-text `revisit` and 到期重看 stays （無）."""
    snap = load_as_of(date(2026, 9, 8), REPO_ROOT / "narratives")
    assert [parse_revisit_date(n.revisit) for n in snap.narratives] == [None, None, None]
    assert [n.revisit_note for n in snap.narratives] == ["", "", ""]
    due, cond = render_revisit_due(snap, date(2026, 9, 8)).split(TITLE_REVISIT_CONDITIONAL, 1)
    assert EMPTY_LIST in due
    for nid in ("asic_xpu", "nvhbm", "optical_cpo"):
        assert nid in cond
