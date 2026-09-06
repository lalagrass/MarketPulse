from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pandas as pd

from marketpulse import RANK_DISCLOSURE, REPLAY_DISCLOSURE
from marketpulse.calc import compute_snapshots
from marketpulse.quality import HORIZON_FOOTNOTE
from marketpulse.narratives import (
    EMPTY_LIST,
    TITLE_COVERED_WEAK,
    TITLE_OUT_OF_CLASSIFICATION,
    TITLE_REVISIT_CONDITIONAL,
    TITLE_REVISIT_DUE,
    TITLE_STRONG_UNCOVERED,
    UNKNOWN_THEME_ID_NOTE,
    Narrative,
    NarrativeOverlay,
    NarrativeSnapshot,
)
from marketpulse.product import (
    CLASSIFICATION_NOTE,
    DEFAULT_CHART_SESSIONS,
    MISSING_NOTE,
    STATE_IMPROVING,
    STATE_LAGGING,
    STATE_LEADING,
    STATE_WEAKENING,
    brief_state,
    chart_window,
    effective_rank_period,
    format_end_label,
    render_brief,
    render_timeline,
    status_mark,
)
from marketpulse.themes import Theme, ThemeSet
from tests.conftest import make_bars, make_index, session_dates, two_theme_set


def _snap_ok():
    dates = session_dates(21)
    bars = make_bars(
        dates,
        {
            "AAA": [100.0] * 20 + [110.0],
            "BBB": [100.0] * 21,
            "CCC": [100.0] * 20 + [105.0],
        },
        twse=("AAA", "BBB"),
        tpex=("CCC",),
    )
    index = make_index(dates, [1000.0] * 21)
    snap = compute_snapshots(bars, index, two_theme_set(), thin_min=1)
    return snap, dates


def test_brief_discloses_visualization_replay_and_hides_score() -> None:
    snap, dates = _snap_ok()
    text = render_brief(snap, dates[-1])
    assert "MarketPulse" in text
    assert "RS20" in text
    assert REPLAY_DISCLOSURE in text
    assert RANK_DISCLOSURE in text
    assert "rotation_score" not in text
    assert "rank_momentum" not in text
    assert MISSING_NOTE not in text
    assert CLASSIFICATION_NOTE in text
    assert "Value%" not in text
    assert "領先 / 改善 / 轉弱 / 落後" in text


def test_brief_marks_missing_data_without_hiding_rank() -> None:
    dates = session_dates(21)
    bars = make_bars(
        dates,
        {
            "AAA": [100.0] * 20 + [120.0],
            "BBB": [100.0] * 21,
            "CCC": [100.0] * 21,
        },
        twse=("AAA", "BBB"),
        tpex=("CCC",),
    )
    bars = bars[~((bars["symbol"] == "BBB") & (bars["date"] == dates[-1]))]
    index = make_index(dates, [1000.0] * 21)
    snap = compute_snapshots(bars, index, two_theme_set(), thin_min=1)
    text = render_brief(snap, dates[-1])
    last = snap[snap["date"] == dates[-1]].set_index("theme_id")
    assert last.loc["alpha", "status"] == "MISSING_DATA"
    assert "*" in text
    assert "MISSING_DATA" in text
    assert MISSING_NOTE in text
    assert "RS20" in text
    assert "rotation_score" not in text


def test_status_mark() -> None:
    assert status_mark("OK") == " "
    assert status_mark("MISSING_DATA") == "*"
    assert status_mark("THIN") == "~"
    assert status_mark("INSUFFICIENT_HISTORY") == "·"


def test_effective_rank_period_uses_ranked_rows_only() -> None:
    snap, dates = _snap_ok()
    lo, hi = effective_rank_period(snap)
    assert hi == dates[-1]
    ranked = snap.dropna(subset=["rank"])
    assert lo == min(ranked["date"])


def test_end_label_includes_rs20_and_delta() -> None:
    rec = SimpleNamespace(
        rank=1,
        theme_name="光通訊/CPO",
        rs20=0.184,
        rank_delta_5=3,
        status="OK",
    )
    assert format_end_label(rec) == "#1 光通訊/CPO  +18.4%  Δ5 +3"
    missing = SimpleNamespace(
        rank=2,
        theme_name="記憶體",
        rs20=-0.011,
        rank_delta_5=-1,
        status="MISSING_DATA",
    )
    assert format_end_label(missing) == "#2 記憶體  -1.1%  Δ5 -1*"


def test_timeline_png_written(tmp_path) -> None:
    snap, _dates = _snap_ok()
    dest = tmp_path / "rotation.png"
    render_timeline(snap, dest)
    assert dest.exists()
    assert dest.stat().st_size > 1000


def test_brief_state_predicates() -> None:
    assert brief_state(1, 0) == STATE_LEADING
    assert brief_state(3, 1) == STATE_LEADING
    assert brief_state(4, 2) == STATE_IMPROVING
    assert brief_state(11, 3) == STATE_IMPROVING
    assert brief_state(1, -2) == STATE_WEAKENING
    assert brief_state(3, -3) == STATE_WEAKENING
    assert brief_state(2, -1) == STATE_LAGGING
    assert brief_state(4, 1) == STATE_LAGGING
    assert brief_state(5, -1) == STATE_LAGGING
    assert brief_state(3, -1) == STATE_LAGGING
    assert brief_state(float("nan"), 2) == STATE_LAGGING
    assert brief_state(1, float("nan")) == STATE_LAGGING
    assert brief_state(None, 0) == STATE_LAGGING
    assert brief_state(1, None) == STATE_LAGGING


def _theme_row(
    theme_id: str,
    theme_name: str,
    rank: float | None,
    delta: float | None,
    *,
    rs20: float = 0.1,
    thrust: float = 0.0,
    breadth: float = 0.5,
    status: str = "OK",
) -> dict:
    return {
        "date": date(2026, 8, 31),
        "theme_id": theme_id,
        "theme_name": theme_name,
        "return_20": 0.12,
        "rs20": rs20,
        "rank": rank,
        "rank_delta_5": delta,
        "rank_delta_20": 0,
        "value_share": 0.08,
        "breadth": breadth,
        "value_thrust": thrust,
        "member_count": 5,
        "missing_count": 0,
        "status": status,
    }


def test_brief_groups_improving_first_and_omits_empty_blocks() -> None:
    snap = pd.DataFrame(
        [
            _theme_row("optical_cpo", "光通訊/CPO", 1, 1, rs20=0.428, thrust=-0.043, breadth=1.0),
            _theme_row("high_speed_materials", "高速材料/CCL", 2, -1, rs20=0.392, thrust=-0.046, breadth=0.5),
            _theme_row("thermal", "散熱/液冷", 3, 0, rs20=0.235, thrust=0.021, breadth=0.8),
            _theme_row("passive_components", "被動元件", 6, 3, rs20=0.145, thrust=0.110, breadth=0.571),
            _theme_row("foundry_advanced", "先進製程", 8, 2, rs20=0.056, thrust=0.003, breadth=0.667),
        ]
    )
    text = render_brief(snap, date(2026, 8, 31))
    blocks = [ln for ln in text.splitlines() if ln in {
        STATE_IMPROVING,
        STATE_LEADING,
        STATE_WEAKENING,
        STATE_LAGGING,
    }]
    assert blocks == [STATE_IMPROVING, STATE_LEADING, STATE_LAGGING]
    assert text.index("被動元件") < text.index("先進製程")
    assert text.index("被動元件") < text.index("光通訊/CPO")
    assert "高速材料/CCL" in text.split("\n落後\n", 1)[1]
    assert "Value%" not in text
    assert "thrust" in text
    assert "breadth" in text
    assert "rotation_score" not in text


def test_chart_window_defaults_to_last_n_ranked_dates() -> None:
    rows = []
    start = date(2026, 1, 5)
    dates = session_dates(50, start=start)
    for i, session in enumerate(dates):
        rows.append(
            {
                "date": session,
                "theme_id": "alpha",
                "theme_name": "Alpha",
                "rank": 1,
                "rs20": 0.1,
                "status": "OK",
            }
        )
        rows.append(
            {
                "date": session,
                "theme_id": "beta",
                "theme_name": "Beta",
                "rank": 2,
                "rs20": 0.0,
                "status": "OK",
            }
        )
    snap = pd.DataFrame(rows)
    window = chart_window(snap, None, None)
    kept = sorted(set(window["date"]))
    assert len(kept) == DEFAULT_CHART_SESSIONS
    assert kept[-1] == dates[-1]
    assert kept[0] == dates[-DEFAULT_CHART_SESSIONS]


def test_chart_window_explicit_start_is_not_clipped() -> None:
    dates = session_dates(50)
    snap = pd.DataFrame(
        [{"date": session, "theme_id": "alpha", "rank": 1, "rs20": 0.1} for session in dates]
    )
    window = chart_window(snap, dates[0], dates[-1])
    assert sorted(set(window["date"])) == dates


def test_brief_rank2_delta_minus1_is_lagging() -> None:
    snap = pd.DataFrame(
        [
            _theme_row("leader", "領先族", 1, 0),
            _theme_row("almost", "高速材料/CCL", 2, -1),
        ]
    )
    text = render_brief(snap, date(2026, 8, 31))
    after_lagging = text.split("\n落後\n", 1)[1]
    assert "高速材料/CCL" in after_lagging
    before_lagging = text.split("\n落後\n", 1)[0]
    assert "高速材料/CCL" not in before_lagging


def test_brief_unbroken_when_null_baseline_missing() -> None:
    """spec 003 DO-1: missing null-baseline file must not break Brief layout."""
    snap, dates = _snap_ok()
    text = render_brief(snap, dates[-1], market_row=None, null_baseline=None)
    assert "MarketPulse" in text
    assert "持續性 n/a" in text
    assert "虛無" not in text
    assert "†" not in text
    # Same as calling without the new kwarg (sprint-002 call shape).
    assert text == render_brief(snap, dates[-1])


def test_brief_includes_horizon_footnote_when_market_row_present() -> None:
    """spec 005 DO-3: B+C fixed note on quality line when market_row exists."""
    import pandas as pd

    snap, dates = _snap_ok()
    market_row = pd.Series(
        {
            "date": dates[-1],
            "rank_persistence_20": 0.21,
            "rank_churn": 4.0,
            "rank_churn_pct": float("nan"),
            "dispersion": 0.06,
            "dispersion_pct": float("nan"),
        }
    )
    out = render_brief(snap, dates[-1], market_row=market_row, null_baseline=None)
    assert HORIZON_FOOTNOTE in out
    assert "持續性" in out


def _eleven_day() -> pd.DataFrame:
    names = [
        ("t01", "主題一", 1),
        ("t02", "主題二", 2),
        ("t03", "主題三", 3),
        ("t04", "主題四", 4),
        ("t05", "主題五", 5),
        ("t06", "主題六", 6),
        ("t07", "主題七", 7),
        ("t08", "主題八", 8),
        ("t09", "主題九", 9),
        ("t10", "主題十", 10),
        ("t11", "主題十一", 11),
    ]
    return pd.DataFrame([_theme_row(tid, name, rank, 0) for tid, name, rank in names])


def _overlay(themes: ThemeSet, named: dict[str, tuple[str, ...]], day: date) -> NarrativeOverlay:
    narratives = tuple(
        Narrative(
            narrative_id=nid,
            name=nid,
            first_noted=day,
            source="self",
            source_ref="x",
            stance="new",
            named_symbols=symbols,
            inferred_symbols=(),
            note="",
        )
        for nid, symbols in named.items()
    )
    return NarrativeOverlay(
        snapshot=NarrativeSnapshot(snapshot_date=day, narratives=narratives),
        themes=themes,
    )


def test_brief_gap_lists_no_narratives_top_three_and_empty_weak() -> None:
    snap = _eleven_day()
    text = render_brief(snap, date(2026, 8, 31), overlay=None)
    assert TITLE_STRONG_UNCOVERED in text
    assert TITLE_COVERED_WEAK in text
    strong, rest = text.split(TITLE_STRONG_UNCOVERED, 1)[1].split(TITLE_COVERED_WEAK, 1)
    assert "主題一  #1" in strong
    assert "主題二  #2" in strong
    assert "主題三  #3" in strong
    assert "主題四  #4" not in strong
    assert EMPTY_LIST in rest.split(REPLAY_DISCLOSURE, 1)[0]


def test_brief_gap_lists_rank_boundary_three_vs_four() -> None:
    """rank=3 uncovered is in 強但沒人講; rank=4 uncovered is not (spec 007)."""
    snap = _eleven_day()
    text = render_brief(snap, date(2026, 8, 31), overlay=None)
    strong = text.split(TITLE_STRONG_UNCOVERED, 1)[1].split(TITLE_COVERED_WEAK, 1)[0]
    assert "主題三  #3" in strong
    assert "主題四  #4" not in strong


def test_brief_gap_lists_covered_and_uncovered() -> None:
    themes = ThemeSet(
        classification_version="test",
        taxonomy_frozen_at="2026-01-01",
        notes="",
        themes=tuple(Theme(f"t{i:02d}", f"主題{i}", (f"S{i:02d}",)) for i in range(1, 12)),
    )
    # t01 rank 1 covered → not 強但沒人講. t06 rank 6 covered → 有人講但弱.
    # t11 rank 11 covered → 有人講但弱. t03 rank 3 uncovered → 強但沒人講.
    overlay = _overlay(
        themes,
        {"n_top": ("S01",), "n_mid": ("S06",), "n_last": ("S11",)},
        date(2026, 8, 31),
    )
    text = render_brief(_eleven_day(), date(2026, 8, 31), overlay=overlay)
    strong = text.split(TITLE_STRONG_UNCOVERED, 1)[1].split(TITLE_COVERED_WEAK, 1)[0]
    weak = text.split(TITLE_COVERED_WEAK, 1)[1].split(REPLAY_DISCLOSURE, 1)[0]
    assert "主題一  #1" not in strong
    assert "主題二  #2" in strong
    assert "主題三  #3" in strong
    assert "主題六  #6" in weak
    assert "主題十一  #11" in weak
    assert "主題五  #5" not in weak  # covered would need rank >= 6; t05 is uncovered anyway


def test_brief_show_narratives_false_ignores_overlay_byte_identical() -> None:
    themes = ThemeSet(
        classification_version="test",
        taxonomy_frozen_at="2026-01-01",
        notes="",
        themes=(Theme("t01", "主題一", ("S01",)),),
    )
    overlay = _overlay(themes, {"n": ("S01",)}, date(2026, 8, 31))
    snap = _eleven_day()
    off_none = render_brief(snap, date(2026, 8, 31), show_narratives=False, overlay=None)
    off_overlay = render_brief(
        snap, date(2026, 8, 31), show_narratives=False, overlay=overlay
    )
    assert off_none == off_overlay
    assert TITLE_STRONG_UNCOVERED not in off_none
    assert TITLE_COVERED_WEAK not in off_none
    assert TITLE_REVISIT_DUE not in off_none
    assert TITLE_REVISIT_CONDITIONAL not in off_none
    on = render_brief(snap, date(2026, 8, 31), show_narratives=True, overlay=overlay)
    assert TITLE_STRONG_UNCOVERED in on
    assert off_none != on


def test_brief_broken_narrative_prints_message_and_keeps_layer1(tmp_path) -> None:
    (tmp_path / "2026-09-06.yaml").write_text("{ not yaml", encoding="utf-8")
    from marketpulse.narratives import load_as_of_lenient
    from marketpulse.themes import load_themes
    from pathlib import Path

    themes = load_themes(Path(__file__).resolve().parents[1] / "themes" / "v1.yaml")
    snapshot, error = load_as_of_lenient(date(2026, 8, 31), tmp_path)
    overlay = NarrativeOverlay(snapshot=snapshot, themes=themes, error=error)
    snap = _eleven_day()
    text = render_brief(snap, date(2026, 8, 31), overlay=overlay)
    assert error is not None
    assert error in text
    assert "主題一" in text
    assert "RS20" in text
    assert TITLE_STRONG_UNCOVERED in text
    assert EMPTY_LIST in text.split(TITLE_COVERED_WEAK, 1)[1]


def test_brief_empty_block_is_not_omitted() -> None:
    snap = _eleven_day()
    text = render_brief(snap, date(2026, 8, 31), overlay=None)
    weak_block = text.split(TITLE_COVERED_WEAK, 1)[1]
    first = weak_block.strip().splitlines()[0]
    assert first == EMPTY_LIST


def test_brief_ends_with_revisit_due_and_conditional() -> None:
    themes = ThemeSet(
        classification_version="test",
        taxonomy_frozen_at="2026-01-01",
        notes="",
        themes=(Theme("t06", "主題六", ("S06",)),),
    )
    overlay = NarrativeOverlay(
        snapshot=NarrativeSnapshot(
            snapshot_date=date(2026, 8, 31),
            narratives=(
                Narrative(
                    narrative_id="due_n",
                    name="due_n",
                    first_noted=date(2026, 8, 1),
                    source="self",
                    source_ref="x",
                    stance="new",
                    named_symbols=("S06",),
                    inferred_symbols=(),
                    note="a note",
                    revisit="2026-08-30",
                ),
                Narrative(
                    narrative_id="cond_n",
                    name="cond_n",
                    first_noted=date(2026, 8, 1),
                    source="self",
                    source_ref="x",
                    stance="new",
                    named_symbols=(),
                    inferred_symbols=(),
                    note="",
                    revisit="Broadcom 下一次財報電話會議",
                ),
            ),
        ),
        themes=themes,
    )
    text = render_brief(_eleven_day(), date(2026, 8, 31), overlay=overlay)
    assert text.index(TITLE_STRONG_UNCOVERED) < text.index(TITLE_REVISIT_DUE)
    assert TITLE_REVISIT_DUE in text
    assert TITLE_REVISIT_CONDITIONAL in text
    assert "due_n · — · 2026-08-30 · a note" in text
    assert "cond_n · Broadcom 下一次財報電話會議" in text


# ── sprint 008 DO-1: theme_ids in the brief ──


def _eleven_theme_set() -> ThemeSet:
    return ThemeSet(
        classification_version="test",
        taxonomy_frozen_at="2026-01-01",
        notes="",
        themes=tuple(Theme(f"t{i:02d}", f"主題{i}", (f"S{i:02d}",)) for i in range(1, 12)),
    )


def _overlay_with(narratives: tuple[Narrative, ...]) -> NarrativeOverlay:
    return NarrativeOverlay(
        snapshot=NarrativeSnapshot(snapshot_date=date(2026, 8, 31), narratives=narratives),
        themes=_eleven_theme_set(),
    )


def _n(nid: str, *, theme_ids=(), named=()) -> Narrative:
    return Narrative(
        narrative_id=nid,
        name=nid,
        first_noted=date(2026, 8, 1),
        source="self",
        source_ref="x",
        stance="new",
        named_symbols=tuple(named),
        inferred_symbols=(),
        note="",
        theme_ids=tuple(theme_ids),
    )


def test_do1_declared_theme_leaves_strong_uncovered() -> None:
    """Acceptance 1: a narrative that declares t01 via theme_ids pulls the
    rank-1 theme out of 強但沒人講; t02 / t03 (nobody declared them) stay."""
    overlay = _overlay_with((_n("n_optical", theme_ids=("t01",)),))
    text = render_brief(_eleven_day(), date(2026, 8, 31), overlay=overlay)
    strong = text.split(TITLE_STRONG_UNCOVERED, 1)[1].split(TITLE_COVERED_WEAK, 1)[0]
    assert "主題一  #1" not in strong
    assert "主題二  #2" in strong
    assert "主題三  #3" in strong


def test_do1_named_symbols_fallback_still_covers_when_no_theme_ids() -> None:
    """Acceptance 2: with no theme_ids, S01 in t01's members still covers t01
    (the pre-008 path is intact)."""
    overlay = _overlay_with((_n("n_named", named=("S01",)),))
    text = render_brief(_eleven_day(), date(2026, 8, 31), overlay=overlay)
    strong = text.split(TITLE_STRONG_UNCOVERED, 1)[1].split(TITLE_COVERED_WEAK, 1)[0]
    assert "主題一  #1" not in strong


def test_do1_out_of_classification_block_lists_unclassified_named_symbol() -> None:
    """Acceptance 3: a named symbol in no theme shows in 分類外代號 as
    `narrative_id · symbol`; it is not auto-slotted anywhere."""
    overlay = _overlay_with((_n("n_gap", named=("9999",)),))
    text = render_brief(_eleven_day(), date(2026, 8, 31), overlay=overlay)
    block = text.split(TITLE_OUT_OF_CLASSIFICATION, 1)[1]
    assert "n_gap · 9999" in block.splitlines()[1]


def test_do1_out_of_classification_block_empty_prints_placeholder() -> None:
    overlay = _overlay_with((_n("n_ok", named=("S01",)),))
    text = render_brief(_eleven_day(), date(2026, 8, 31), overlay=overlay)
    assert TITLE_OUT_OF_CLASSIFICATION in text
    block = text.split(TITLE_OUT_OF_CLASSIFICATION, 1)[1]
    assert block.splitlines()[1] == EMPTY_LIST


def test_do1_unknown_theme_id_message_appears_in_brief() -> None:
    """Acceptance 4: an unknown theme_id is visible on screen (not raised,
    not silently dropped). The valid sibling id still classifies."""
    overlay = _overlay_with((_n("n_typo", theme_ids=("t01", "bogus_id")),))
    text = render_brief(_eleven_day(), date(2026, 8, 31), overlay=overlay)
    assert UNKNOWN_THEME_ID_NOTE in text
    line = [ln for ln in text.splitlines() if UNKNOWN_THEME_ID_NOTE in ln][0]
    assert "n_typo" in line and "bogus_id" in line
    strong = text.split(TITLE_STRONG_UNCOVERED, 1)[1].split(TITLE_COVERED_WEAK, 1)[0]
    assert "主題一  #1" not in strong  # t01 still declared despite the typo sibling


def test_do1_no_narratives_adds_no_new_blocks() -> None:
    """Acceptance 5 (byte-identity precondition): with no narrative snapshot
    loaded, none of the DO-1 additions render."""
    text_none = render_brief(_eleven_day(), date(2026, 8, 31), overlay=None)
    empty_overlay = NarrativeOverlay(
        snapshot=NarrativeSnapshot(snapshot_date=None, narratives=()),
        themes=_eleven_theme_set(),
    )
    text_empty = render_brief(_eleven_day(), date(2026, 8, 31), overlay=empty_overlay)
    for text in (text_none, text_empty):
        assert TITLE_OUT_OF_CLASSIFICATION not in text
        assert UNKNOWN_THEME_ID_NOTE not in text


def test_brief_render_does_not_change_narratives_mtime_or_bytes() -> None:
    """spec 007 DO-2 acceptance 3 via the brief renderer, not refresh."""
    from pathlib import Path

    n_dir = Path(__file__).resolve().parents[1] / "narratives"
    before = {
        p.name: (p.stat().st_mtime_ns, p.read_bytes()) for p in sorted(n_dir.glob("*.yaml"))
    }
    themes = ThemeSet(
        classification_version="test",
        taxonomy_frozen_at="2026-01-01",
        notes="",
        themes=(Theme("t01", "主題一", ("S01",)),),
    )
    from marketpulse.narratives import load_as_of

    overlay = NarrativeOverlay(
        snapshot=load_as_of(date(2026, 9, 6), n_dir),
        themes=themes,
    )
    render_brief(_eleven_day(), date(2026, 8, 31), overlay=overlay)
    after = {
        p.name: (p.stat().st_mtime_ns, p.read_bytes()) for p in sorted(n_dir.glob("*.yaml"))
    }
    assert after == before
