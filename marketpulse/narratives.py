"""Narrative context layer: hand-maintained, dated snapshots, no lookahead.

This is not a data source and not a measurement — it is a manually curated
diary of what a podcast/hot-list/self-source said, and when, kept as one
full-state YAML file per change (never edited in place, mirroring how S&P
500 constituent-point reconstructions are kept). See docs/sprints/001-spec.md
DO-3. This sprint only ships structure, a PIT-safe loader, and a coverage
report — no narrative strength/RS20/rank/chart of any kind (see spec).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml

from marketpulse.themes import ThemeSet

STANCE_NEW = "new"
STANCE_CONFIRMING = "confirming"

COVERAGE_COVERED = "covered"
COVERAGE_PARTIAL = "partial"
COVERAGE_UNCOVERED = "uncovered"
COVERAGE_UNKNOWN = "unknown"

DEFAULT_NARRATIVES_DIR = Path("narratives")


@dataclass(frozen=True)
class Narrative:
    narrative_id: str
    name: str
    first_noted: date
    source: str
    source_ref: str
    stance: str
    named_symbols: tuple[str, ...]
    inferred_symbols: tuple[str, ...]
    note: str


@dataclass(frozen=True)
class NarrativeSnapshot:
    snapshot_date: date | None
    narratives: tuple[Narrative, ...]


def _as_date(value: object) -> date:
    return value if isinstance(value, date) else date.fromisoformat(str(value))


def _parse_narrative(body: dict) -> Narrative:
    narrative_id = str(body["narrative_id"])
    return Narrative(
        narrative_id=narrative_id,
        name=str(body.get("name") or narrative_id),
        first_noted=_as_date(body["first_noted"]),
        source=str(body.get("source") or ""),
        source_ref=str(body.get("source_ref") or ""),
        stance=str(body.get("stance") or ""),
        named_symbols=tuple(str(s) for s in (body.get("named_symbols") or [])),
        inferred_symbols=tuple(str(s) for s in (body.get("inferred_symbols") or [])),
        note=str(body.get("note") or "").strip(),
    )


def _parse_snapshot_file(path: Path) -> tuple[date, tuple[Narrative, ...]]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    snapshot_date = _as_date(payload["snapshot_date"])
    raw_narratives = payload.get("narratives") or []
    narratives = tuple(_parse_narrative(n) for n in raw_narratives)
    return snapshot_date, narratives


def _snapshot_files(narratives_dir: Path) -> list[Path]:
    return sorted(narratives_dir.glob("*.yaml"))


def load_as_of(as_of: date, narratives_dir: Path = DEFAULT_NARRATIVES_DIR) -> NarrativeSnapshot:
    """The latest snapshot with snapshot_date <= as_of; narratives with
    first_noted > as_of are dropped. If every snapshot file postdates
    as_of, returns an empty snapshot rather than the oldest file — this
    filter is not optional (contract §7 PIT)."""
    best_date: date | None = None
    best_narratives: tuple[Narrative, ...] = ()
    for path in _snapshot_files(narratives_dir):
        snapshot_date, narratives = _parse_snapshot_file(path)
        if snapshot_date > as_of:
            continue
        if best_date is None or snapshot_date > best_date:
            best_date = snapshot_date
            best_narratives = narratives
    if best_date is None:
        return NarrativeSnapshot(snapshot_date=None, narratives=())
    filtered = tuple(n for n in best_narratives if n.first_noted <= as_of)
    return NarrativeSnapshot(snapshot_date=best_date, narratives=filtered)


def coverage_report(snapshot: NarrativeSnapshot, themes: ThemeSet) -> dict[str, str]:
    """Per-narrative coverage of named_symbols against themes/v1.yaml.

    Derived, not stored — recomputed from the current theme YAML on every
    call. Empty named_symbols is `unknown`, not `covered`: nothing was
    named, so nothing has actually been verified either way.
    """
    all_members = {m for theme in themes.themes for m in theme.members}
    report: dict[str, str] = {}
    for narrative in snapshot.narratives:
        if not narrative.named_symbols:
            report[narrative.narrative_id] = COVERAGE_UNKNOWN
            continue
        present = [s for s in narrative.named_symbols if s in all_members]
        if len(present) == len(narrative.named_symbols):
            report[narrative.narrative_id] = COVERAGE_COVERED
        elif not present:
            report[narrative.narrative_id] = COVERAGE_UNCOVERED
        else:
            report[narrative.narrative_id] = COVERAGE_PARTIAL
    return report
