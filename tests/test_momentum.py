from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from marketpulse.calc import compute_snapshots, compute_stock_metrics
from marketpulse.momentum import (
    DIR_DOWN,
    DIR_FLAT,
    DIR_UP,
    MOM_IMPROVING,
    MOM_STABLE,
    MOM_STRONG,
    MOM_UNKNOWN,
    MOM_WEAK,
    MOM_WEAKENING,
    classify_momentum,
    momentum_evidence,
)
from marketpulse.radar import render_radar, render_radar_detail, render_radar_html
from tests.conftest import make_bars, make_index, session_dates, two_theme_set


def test_strong_top_rank_expanding() -> None:
    ev = classify_momentum(
        rank=1,
        rank_delta_5=1,
        return_5=0.145,
        return_20=0.438,
        breadth=1.0,
        volume_ratio=1.37,
        above_count=10,
        prior_return_5=0.054,
        prior_breadth=1.0,
        prior_volume_ratio=1.19,
        prior_above_count=10,
    )
    assert ev.state == MOM_STRONG
    assert ev.five == DIR_UP
    assert ev.twenty == DIR_UP
    assert ev.breadth == DIR_FLAT
    assert ev.volume == DIR_UP
    assert ev.rank == DIR_UP


def test_weakening_high_20d_but_breadth_volume_rank_fade() -> None:
    """PO example: rank #2, 20D still strong, internals fading."""
    ev = classify_momentum(
        rank=2,
        rank_delta_5=-1,
        return_5=0.027,
        return_20=0.329,
        breadth=0.5,
        volume_ratio=0.43,
        above_count=2,
        prior_return_5=-0.005,
        prior_breadth=1.0,
        prior_volume_ratio=0.96,
        prior_above_count=4,
    )
    assert ev.state == MOM_WEAKENING
    assert ev.five == DIR_UP
    assert ev.breadth == DIR_DOWN
    assert ev.volume == DIR_DOWN
    assert ev.rank == DIR_DOWN


def test_weakening_20d_positive_but_5d_and_rank_deteriorate() -> None:
    """PO example: leftover 20D, short-term and rank fading."""
    ev = classify_momentum(
        rank=11,
        rank_delta_5=-5,
        return_5=-0.035,
        return_20=0.016,
        breadth=0.8,
        volume_ratio=0.95,
        above_count=8,
        prior_return_5=-0.010,
        prior_breadth=0.7,
        prior_volume_ratio=0.71,
        prior_above_count=7,
    )
    assert ev.state == MOM_WEAKENING
    assert ev.five == DIR_DOWN
    assert ev.rank == DIR_DOWN
    assert ev.twenty == DIR_UP


def test_improving_rank_and_5d_expand() -> None:
    ev = classify_momentum(
        rank=6,
        rank_delta_5=2,
        return_5=0.066,
        return_20=0.140,
        breadth=0.43,
        volume_ratio=0.63,
        above_count=3,
        prior_return_5=-0.025,
        prior_breadth=0.43,
        prior_volume_ratio=0.62,
        prior_above_count=3,
    )
    assert ev.state == MOM_IMPROVING
    assert ev.five == DIR_UP
    assert ev.rank == DIR_UP


def test_stable_mid_rank_no_clear_move() -> None:
    ev = classify_momentum(
        rank=5,
        rank_delta_5=0,
        return_5=0.010,
        return_20=0.080,
        breadth=0.71,
        volume_ratio=1.00,
        above_count=5,
        prior_return_5=0.012,
        prior_breadth=0.71,
        prior_volume_ratio=1.00,
        prior_above_count=5,
    )
    assert ev.state == MOM_STABLE
    assert ev.five == DIR_UP
    assert ev.breadth == DIR_FLAT
    assert ev.volume == DIR_FLAT
    assert ev.rank == DIR_FLAT


def test_weak_bottom_rank_negative_returns() -> None:
    ev = classify_momentum(
        rank=10,
        rank_delta_5=0,
        return_5=-0.020,
        return_20=-0.050,
        breadth=0.40,
        volume_ratio=0.90,
        above_count=2,
        prior_return_5=-0.010,
        prior_breadth=0.40,
        prior_volume_ratio=0.90,
        prior_above_count=2,
    )
    assert ev.state == MOM_WEAK
    assert ev.five == DIR_DOWN
    assert ev.twenty == DIR_DOWN


def test_unknown_when_rank_delta_5_missing() -> None:
    ev = classify_momentum(
        rank=1,
        rank_delta_5=float("nan"),
        return_5=0.10,
        return_20=0.20,
        breadth=1.0,
        volume_ratio=1.4,
        above_count=10,
    )
    assert ev.state == MOM_UNKNOWN


def test_unknown_when_rank_missing() -> None:
    ev = classify_momentum(
        rank=float("nan"),
        rank_delta_5=0,
        return_5=0.10,
        return_20=0.20,
    )
    assert ev.state == MOM_UNKNOWN


def test_unknown_when_return_5_missing() -> None:
    ev = classify_momentum(
        rank=1,
        rank_delta_5=0,
        return_5=float("nan"),
        return_20=0.20,
    )
    assert ev.state == MOM_UNKNOWN


def test_one_fade_does_not_make_leader_weakening() -> None:
    ev = classify_momentum(
        rank=1,
        rank_delta_5=0,
        return_5=0.08,
        return_20=0.30,
        breadth=0.90,
        volume_ratio=1.4,
        above_count=9,
        prior_return_5=0.07,
        prior_breadth=1.0,
        prior_volume_ratio=1.3,
        prior_above_count=10,
    )
    assert ev.state == MOM_STRONG
    assert ev.breadth == DIR_DOWN


def test_5d_drop_of_two_points_counts_as_deteriorating() -> None:
    ev = classify_momentum(
        rank=2,
        rank_delta_5=0,
        return_5=0.03,
        return_20=0.25,
        breadth=0.80,
        volume_ratio=1.0,
        above_count=8,
        prior_return_5=0.06,
        prior_breadth=1.0,
        prior_volume_ratio=1.0,
        prior_above_count=10,
    )
    assert ev.five == DIR_DOWN
    assert ev.breadth == DIR_DOWN
    assert ev.state == MOM_WEAKENING


def test_rank_still_not_used_as_a_score() -> None:
    ev = classify_momentum(
        rank=1,
        rank_delta_5=1,
        return_5=0.10,
        return_20=0.30,
        volume_ratio=1.4,
        above_count=10,
        prior_above_count=10,
        prior_volume_ratio=1.3,
        prior_return_5=0.08,
    )
    assert ev.state == MOM_STRONG
    assert not hasattr(ev, "score")


def test_end_to_end_unknown_without_five_ranked_sessions() -> None:
    dates = session_dates(21)
    bars = make_bars(
        dates,
        {"AAA": [100.0] * 20 + [120.0], "BBB": [100.0] * 21, "CCC": [100.0] * 21},
        twse=("AAA", "BBB"),
        tpex=("CCC",),
    )
    snap = compute_snapshots(bars, make_index(dates, [1000.0] * 21), two_theme_set(), thin_min=1)
    last = snap[snap["date"] == dates[-1]].iloc[0]
    ev = momentum_evidence(snap, last)
    assert ev.state == MOM_UNKNOWN
    text = render_radar(snap, dates[-1])
    assert "n/a" in text
    assert "Momentum" in text


def test_end_to_end_strong_and_weakening_from_history() -> None:
    dates = session_dates(26)
    # Alpha pulls ahead then keeps expanding; beta leads early then fades.
    aaa = [100.0] * 20 + [108.0, 110.0, 112.0, 114.0, 116.0, 125.0]
    bbb = [100.0] * 26
    ccc = [100.0] * 20 + [120.0, 119.0, 118.0, 116.0, 114.0, 112.0]
    bars = make_bars(
        dates,
        {"AAA": aaa, "BBB": bbb, "CCC": ccc},
        twse=("AAA", "BBB"),
        tpex=("CCC",),
    )
    # Last-day volume dry for beta (CCC), hot for alpha.
    bars.loc[(bars["date"] == dates[-1]) & (bars["symbol"] == "AAA"), "volume"] = 2000.0
    bars.loc[(bars["date"] == dates[-1]) & (bars["symbol"] == "CCC"), "volume"] = 200.0
    snap = compute_snapshots(bars, make_index(dates, [1000.0] * 26), two_theme_set(), thin_min=1)
    last = snap[snap["date"] == dates[-1]].set_index("theme_id")
    assert last.loc["alpha", "rank"] == 1
    assert last.loc["beta", "rank"] == 2
    alpha = momentum_evidence(snap, last.loc["alpha"])
    beta = momentum_evidence(snap, last.loc["beta"])
    assert alpha.state == MOM_STRONG
    assert beta.state == MOM_WEAKENING
    text = render_radar(snap, dates[-1])
    assert "Strong" in text
    assert "Weakening" in text
    stocks = compute_stock_metrics(bars, make_index(dates, [1000.0] * 26), two_theme_set(), dates[-1])
    page = render_radar_html(snap, stocks, dates[-1])
    assert "Momentum" in page
    assert "🔥 Strong" in page
    assert "⚠️ Weakening" in page
    assert "momentum_score" not in page
    assert "rotation_score" not in page
    detail = render_radar_detail(snap, stocks, dates[-1], "beta")
    assert "Weakening" in detail
    assert "5D" in detail
    assert "Breadth" in detail


def test_momentum_thresholds_unchanged() -> None:
    """spec 011 DO-3: the six constants are not this sprint's knobs (D10)."""
    from marketpulse.momentum import (
        RET5_DROP,
        RET5_FLAT,
        STRONG_RANK,
        VOL_CHANGE,
        VOL_DRY,
        VOL_HOT,
        WEAK_RANK,
    )

    assert RET5_FLAT == 0.005
    assert RET5_DROP == 0.02
    assert VOL_HOT == 1.2
    assert VOL_DRY == 0.8
    assert VOL_CHANGE == 0.20
    assert STRONG_RANK == 3
    assert WEAK_RANK == 8


def test_momentum_cell_contains_four_direction_marks() -> None:
    from marketpulse.radar import _fmt_mom_ascii

    ev = classify_momentum(
        rank=2,
        rank_delta_5=-1,
        return_5=0.027,
        return_20=0.329,
        breadth=0.5,
        volume_ratio=0.43,
        above_count=2,
        prior_return_5=-0.005,
        prior_breadth=1.0,
        prior_volume_ratio=0.96,
        prior_above_count=4,
    )
    cell = _fmt_mom_ascii(ev)
    assert ev.state == MOM_WEAKENING
    assert cell.startswith("Weakening")
    assert "5D" in cell
    assert "Br" in cell
    assert "Vol" in cell
    assert "Δ5" in cell


def test_momentum_same_rank_delta_different_states_show_different_vectors() -> None:
    """Cold-reader case: same Δ5 +3, two labels, because the other three votes differ."""
    from marketpulse.radar import _fmt_mom_ascii

    weakening = classify_momentum(
        rank=5,
        rank_delta_5=3,
        return_5=-0.02,
        return_20=0.10,
        breadth=0.4,
        volume_ratio=0.7,
        above_count=2,
        prior_return_5=0.04,
        prior_breadth=0.8,
        prior_volume_ratio=1.0,
        prior_above_count=4,
    )
    strong = classify_momentum(
        rank=2,
        rank_delta_5=3,
        return_5=0.08,
        return_20=0.20,
        breadth=0.9,
        volume_ratio=1.4,
        above_count=9,
        prior_return_5=0.04,
        prior_breadth=0.8,
        prior_volume_ratio=1.1,
        prior_above_count=8,
    )
    assert weakening.rank == strong.rank == DIR_UP
    assert weakening.state != strong.state
    assert _fmt_mom_ascii(weakening) != _fmt_mom_ascii(strong)
    assert "Δ5↑" in _fmt_mom_ascii(weakening)
    assert "Δ5↑" in _fmt_mom_ascii(strong)


def test_momentum_note_states_positive_five_day_can_be_down() -> None:
    from marketpulse.radar import RADAR_MOM_RULE, render_radar

    dates = session_dates(21)
    bars = make_bars(
        dates,
        {"AAA": [100.0] * 20 + [120.0], "BBB": [100.0] * 21, "CCC": [100.0] * 21},
        twse=("AAA", "BBB"),
        tpex=("CCC",),
    )
    snap = compute_snapshots(bars, make_index(dates, [1000.0] * 21), two_theme_set(), thin_min=1)
    text = render_radar(snap, dates[-1])
    assert "比五日前的 5D 少了 ≥2pp" in text
    assert "不是正負號" in RADAR_MOM_RULE
    page = render_radar_html(snap, pd.DataFrame(), dates[-1])
    assert "比五日前的 5D 少了 ≥2pp" in page


def test_momentum_note_states_rank_delta_is_one_of_four() -> None:
    from marketpulse.radar import RADAR_MOM_RULE

    assert "不是名次變化本身" in RADAR_MOM_RULE
    assert "四票" in RADAR_MOM_RULE
    assert "同樣 Δ5 +3" in RADAR_MOM_RULE


def test_five_day_drop_note_when_return_positive() -> None:
    from types import SimpleNamespace

    from marketpulse.radar import FIVE_DAY_DROP_NOTE, _five_day_drop_note

    ev = classify_momentum(
        rank=4,
        rank_delta_5=0,
        return_5=0.054,
        return_20=0.10,
        prior_return_5=0.080,
    )
    assert ev.five == DIR_DOWN
    rec = SimpleNamespace(return_5=0.054)
    assert FIVE_DAY_DROP_NOTE in _five_day_drop_note(rec, ev)
    rec_neg = SimpleNamespace(return_5=-0.02)
    assert _five_day_drop_note(rec_neg, ev) == ""


def test_unknown_momentum_cell_is_na() -> None:
    from marketpulse.radar import _fmt_mom_ascii

    ev = classify_momentum(
        rank=None,
        rank_delta_5=None,
        return_5=None,
        return_20=None,
    )
    assert ev.state == MOM_UNKNOWN
    assert _fmt_mom_ascii(ev) == "n/a"


def test_html_momentum_cell_contains_direction_marks() -> None:
    dates = session_dates(26)
    aaa = [100.0] * 20 + [108.0, 110.0, 112.0, 114.0, 116.0, 125.0]
    bbb = [100.0] * 26
    ccc = [100.0] * 20 + [120.0, 119.0, 118.0, 116.0, 114.0, 112.0]
    bars = make_bars(
        dates,
        {"AAA": aaa, "BBB": bbb, "CCC": ccc},
        twse=("AAA", "BBB"),
        tpex=("CCC",),
    )
    snap = compute_snapshots(bars, make_index(dates, [1000.0] * 26), two_theme_set(), thin_min=1)
    page = render_radar_html(snap, pd.DataFrame(), dates[-1])
    assert "5D" in page
    assert "Br" in page
    assert "Vol" in page
    assert "Δ5" in page
    text = render_radar(snap, dates[-1])
    alpha = [ln for ln in text.splitlines() if "Alpha" in ln][0]
    assert "5D" in alpha
    assert "Δ5" in alpha


def test_momentum_does_not_change_rank_order() -> None:
    dates = session_dates(26)
    aaa = [100.0] * 20 + [108.0, 110.0, 112.0, 114.0, 116.0, 125.0]
    bbb = [100.0] * 26
    ccc = [100.0] * 20 + [120.0, 119.0, 118.0, 116.0, 114.0, 112.0]
    bars = make_bars(
        dates,
        {"AAA": aaa, "BBB": bbb, "CCC": ccc},
        twse=("AAA", "BBB"),
        tpex=("CCC",),
    )
    snap = compute_snapshots(bars, make_index(dates, [1000.0] * 26), two_theme_set(), thin_min=1)
    last = snap[snap["date"] == dates[-1]].sort_values("rank")
    text = render_radar(snap, dates[-1])
    names = [ln for ln in text.splitlines() if "Alpha" in ln or "Beta" in ln]
    assert last.iloc[0]["theme_name"] in names[0]
    assert last.iloc[1]["theme_name"] in names[1]


def test_no_narratives_rule_width_still_100() -> None:
    dates = session_dates(21)
    bars = make_bars(
        dates,
        {"AAA": [100.0] * 20 + [120.0], "BBB": [100.0] * 21, "CCC": [100.0] * 20 + [110.0]},
        twse=("AAA", "BBB"),
        tpex=("CCC",),
    )
    snap = compute_snapshots(bars, make_index(dates, [1000.0] * 21), two_theme_set(), thin_min=1)
    off = render_radar(snap, dates[-1], show_narratives=False)
    lines = off.splitlines()
    header = [ln for ln in lines if ln.startswith("Sector ") and "1D" in ln][0]
    rule = lines[lines.index(header) + 1]
    assert len(rule) == 100
    assert "Momentum" in header
