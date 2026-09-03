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
