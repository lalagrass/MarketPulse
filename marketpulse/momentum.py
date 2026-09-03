"""Sector Momentum / Trend State. Display-only. Rank remains RS20.

Answers: is this sector's current strength expanding, stable, or fading?

Uses existing snapshot fields only: return_5, return_20, breadth / above_count,
volume_ratio, rank, rank_delta_5, plus the same fields from 5 sessions earlier.
No composite score. No RSI / MACD / new indicator.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

LOOKBACK_SESSIONS = 5

MOM_STRONG = "Strong"
MOM_IMPROVING = "Improving"
MOM_STABLE = "Stable"
MOM_WEAKENING = "Weakening"
MOM_WEAK = "Weak"
MOM_UNKNOWN = "Unknown"

DIR_UP = "up"
DIR_DOWN = "down"
DIR_FLAT = "flat"
DIR_UNKNOWN = "unknown"

# 5D inside ±0.5% is flat. A 2pp drop vs 5 sessions ago is deteriorating.
RET5_FLAT = 0.005
RET5_DROP = 0.02
# Volume vs own SMA20, or a 0.20 move vs 5 sessions ago.
VOL_HOT = 1.2
VOL_DRY = 0.8
VOL_CHANGE = 0.20
STRONG_RANK = 3
WEAK_RANK = 8

MOM_MARK = {
    MOM_STRONG: "🔥",
    MOM_IMPROVING: "🟢",
    MOM_STABLE: "→",
    MOM_WEAKENING: "⚠️",
    MOM_WEAK: "🔴",
    MOM_UNKNOWN: "?",
}

DIR_MARK = {
    DIR_UP: "↑",
    DIR_DOWN: "↓",
    DIR_FLAT: "→",
    DIR_UNKNOWN: "n/a",
}


def _is_na(value: object) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _num(value: object) -> float | None:
    if _is_na(value):
        return None
    return float(value)


def _dir_sign(value: object, eps: float = 0.0) -> str:
    number = _num(value)
    if number is None:
        return DIR_UNKNOWN
    if number > eps:
        return DIR_UP
    if number < -eps:
        return DIR_DOWN
    return DIR_FLAT


def _dir_compare(now: object, then: object, eps: float = 0.0) -> str:
    left = _num(now)
    right = _num(then)
    if left is None or right is None:
        return DIR_UNKNOWN
    delta = left - right
    if delta > eps:
        return DIR_UP
    if delta < -eps:
        return DIR_DOWN
    return DIR_FLAT


def dir_five(return_5: object, prior_return_5: object) -> str:
    """↑ if 5D is clearly positive; ↓ if negative or dropped ≥ 2pp vs 5 sessions ago."""
    now = _num(return_5)
    if now is None:
        return DIR_UNKNOWN
    if now < 0:
        return DIR_DOWN
    prior = _num(prior_return_5)
    if prior is not None and now <= prior - RET5_DROP:
        return DIR_DOWN
    if now > RET5_FLAT:
        return DIR_UP
    return DIR_FLAT


def dir_breadth(
    above_count: object,
    prior_above_count: object,
    breadth: object,
    prior_breadth: object,
) -> str:
    """Compare participation vs 5 sessions ago. Prefer head-count when both exist."""
    counted = _dir_compare(above_count, prior_above_count)
    if counted != DIR_UNKNOWN:
        return counted
    return _dir_compare(breadth, prior_breadth)


def dir_volume(volume_ratio: object, prior_volume_ratio: object) -> str:
    """Dry vs own SMA20, hot vs own SMA20, or a clear 5-session change."""
    now = _num(volume_ratio)
    if now is None:
        return DIR_UNKNOWN
    prior = _num(prior_volume_ratio)
    if now <= VOL_DRY:
        return DIR_DOWN
    if prior is not None and now <= prior - VOL_CHANGE and now < VOL_HOT:
        return DIR_DOWN
    if now >= VOL_HOT:
        return DIR_UP
    if prior is not None and now >= prior + VOL_CHANGE:
        return DIR_UP
    return DIR_FLAT


def dir_rank(rank_delta_5: object) -> str:
    """Positive Δ5 = rank moved up over 5 sessions."""
    return _dir_sign(rank_delta_5)


@dataclass(frozen=True)
class MomentumEvidence:
    state: str
    five: str
    twenty: str
    breadth: str
    volume: str
    rank: str

    @property
    def mark(self) -> str:
        return MOM_MARK.get(self.state, "?")

    @property
    def label(self) -> str:
        if self.state == MOM_UNKNOWN:
            return f"{self.mark} {self.state}"
        return f"{self.mark} {self.state}"


def classify_momentum(
    *,
    rank: object,
    rank_delta_5: object,
    return_5: object,
    return_20: object,
    breadth: object = None,
    volume_ratio: object = None,
    above_count: object = None,
    prior_return_5: object = None,
    prior_breadth: object = None,
    prior_volume_ratio: object = None,
    prior_above_count: object = None,
) -> MomentumEvidence:
    """Deterministic display-only state. Does not change Rank."""
    five = dir_five(return_5, prior_return_5)
    twenty = _dir_sign(return_20)
    breadth_dir = dir_breadth(above_count, prior_above_count, breadth, prior_breadth)
    volume_dir = dir_volume(volume_ratio, prior_volume_ratio)
    rank_dir = dir_rank(rank_delta_5)

    if _is_na(rank) or _is_na(return_5) or _is_na(return_20) or _is_na(rank_delta_5):
        return MomentumEvidence(
            MOM_UNKNOWN, five, twenty, breadth_dir, volume_dir, rank_dir
        )

    signals = (five, breadth_dir, volume_dir, rank_dir)
    n_up = sum(item == DIR_UP for item in signals)
    n_down = sum(item == DIR_DOWN for item in signals)
    position = int(rank)
    ret20 = float(return_20)
    strong_level = position <= STRONG_RANK and ret20 > 0
    weak_level = position >= WEAK_RANK
    has_20d = ret20 > 0

    if has_20d and n_down >= 2:
        state = MOM_WEAKENING
    elif strong_level and n_down == 0 and five == DIR_UP:
        state = MOM_STRONG
    elif strong_level and n_up > n_down and five != DIR_DOWN:
        state = MOM_STRONG
    elif (not strong_level) and n_up >= 2 and n_up > n_down and five == DIR_UP:
        state = MOM_IMPROVING
    elif weak_level and n_up < 2:
        state = MOM_WEAK
    elif (not has_20d) and five == DIR_DOWN:
        state = MOM_WEAK
    else:
        state = MOM_STABLE

    return MomentumEvidence(state, five, twenty, breadth_dir, volume_dir, rank_dir)


def _row_val(row: object, name: str) -> object:
    if row is None:
        return None
    if isinstance(row, pd.Series):
        return row[name] if name in row.index else None
    return getattr(row, name, None)


def prior_row(
    snapshot: pd.DataFrame,
    theme_id: object,
    as_of: date | None,
    n: int = LOOKBACK_SESSIONS,
) -> pd.Series | None:
    """Theme row n sessions before as_of, if the snapshot still has that history."""
    if snapshot.empty or as_of is None or theme_id is None:
        return None
    hist = snapshot.loc[
        (snapshot["theme_id"] == theme_id) & (snapshot["date"] <= as_of)
    ].sort_values("date")
    if len(hist) < n + 1:
        return None
    return hist.iloc[-(n + 1)]


def momentum_evidence(snapshot: pd.DataFrame, rec: object) -> MomentumEvidence:
    as_of = _row_val(rec, "date")
    prior = prior_row(snapshot, _row_val(rec, "theme_id"), as_of)
    return classify_momentum(
        rank=_row_val(rec, "rank"),
        rank_delta_5=_row_val(rec, "rank_delta_5"),
        return_5=_row_val(rec, "return_5"),
        return_20=_row_val(rec, "return_20"),
        breadth=_row_val(rec, "breadth"),
        volume_ratio=_row_val(rec, "volume_ratio"),
        above_count=_row_val(rec, "above_count"),
        prior_return_5=_row_val(prior, "return_5"),
        prior_breadth=_row_val(prior, "breadth"),
        prior_volume_ratio=_row_val(prior, "volume_ratio"),
        prior_above_count=_row_val(prior, "above_count"),
    )
