"""Narrative context layer: hand-maintained, dated snapshots, no lookahead.

This is not a data source and not a measurement — it is a manually curated
diary of what a podcast/hot-list/self-source said, and when, kept as one
full-state YAML file per change (never edited in place, mirroring how S&P
500 constituent-point reconstructions are kept). See docs/sprints/001-spec.md
DO-3.

Sprint 004 DO-1 makes the schema additive: a narrative gains `stage`,
`revisit`, `log` (a dated event list) and `branches` (sub-threads with their
own basket). Every field added before still parses; a file written under the
old schema still loads (see REVISIT_REQUIRED_FROM for the one grandfather).
No narrative strength / RS20 / rank / chart lives here (contract R3).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path

import yaml

from marketpulse.themes import ThemeSet

STANCE_NEW = "new"
STANCE_CONFIRMING = "confirming"

STAGE_OPEN = "open"          # claim stands, symbols not yet converged
STAGE_MAPPED = "mapped"      # symbols converged, tracking progress
STAGE_PARKED = "parked"      # said and done, or never caught — waiting to reopen
STAGES = (STAGE_OPEN, STAGE_MAPPED, STAGE_PARKED)

LOG_CLAIM = "claim"          # a new argument
LOG_EVIDENCE = "evidence"    # supporting / discriminating evidence
LOG_SCHEDULE = "schedule"    # brought forward or pushed back
LOG_PRICE = "price"          # layer 1 moved
LOG_CLOSE = "close"          # closed out
LOG_KINDS = (LOG_CLAIM, LOG_EVIDENCE, LOG_SCHEDULE, LOG_PRICE, LOG_CLOSE)

BRANCH_LIVE = "live"
BRANCH_WEAKENED = "weakened"
BRANCH_DEAD = "dead"
BRANCH_STATUSES = (BRANCH_LIVE, BRANCH_WEAKENED, BRANCH_DEAD)

COVERAGE_COVERED = "covered"
COVERAGE_PARTIAL = "partial"
COVERAGE_UNCOVERED = "uncovered"
COVERAGE_UNKNOWN = "unknown"

DEFAULT_NARRATIVES_DIR = Path("narratives")

# `revisit` is required — a story with no date to come back to rots quietly
# (sprint 004 DO-1, mirrors the skill's UNKNOWN rule). Snapshots written
# before the field existed are grandfathered: enforcement starts at the
# snapshot_date the schema landed. Every file from here on must carry it.
REVISIT_REQUIRED_FROM = date(2026, 9, 6)


@dataclass(frozen=True)
class LogEntry:
    date: date
    source_ref: str
    kind: str
    text: str
    bears_on: tuple[str, ...]


@dataclass(frozen=True)
class Branch:
    branch_id: str
    claim: str
    basket: tuple[str, ...]
    watch: str
    status: str


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
    stage: str = STAGE_OPEN
    revisit: str = ""
    log: tuple[LogEntry, ...] = ()
    branches: tuple[Branch, ...] = ()


@dataclass(frozen=True)
class NarrativeSnapshot:
    snapshot_date: date | None
    narratives: tuple[Narrative, ...]


@dataclass(frozen=True)
class NarrativeVersion:
    """One dated version of a narrative, as returned by history()."""

    snapshot_date: date
    narrative: Narrative


def _as_date(value: object) -> date:
    return value if isinstance(value, date) else date.fromisoformat(str(value))


def _parse_branch(body: dict, *, narrative_id: str) -> Branch:
    branch_id = str(body.get("branch_id") or "").strip()
    if not branch_id:
        raise ValueError(f"narrative {narrative_id!r}: a branch is missing 'branch_id'")
    status = str(body.get("status") or BRANCH_LIVE)
    if status not in BRANCH_STATUSES:
        raise ValueError(
            f"narrative {narrative_id!r} branch {branch_id!r}: status {status!r} "
            f"not one of {BRANCH_STATUSES}"
        )
    return Branch(
        branch_id=branch_id,
        claim=str(body.get("claim") or "").strip(),
        basket=tuple(str(s) for s in (body.get("basket") or [])),
        watch=str(body.get("watch") or "").strip(),
        status=status,
    )


def _parse_log_entry(body: dict, *, narrative_id: str, branch_ids: set[str]) -> LogEntry:
    kind = str(body.get("kind") or "")
    if kind not in LOG_KINDS:
        raise ValueError(
            f"narrative {narrative_id!r} log entry: kind {kind!r} not one of {LOG_KINDS}"
        )
    bears_on = tuple(str(b) for b in (body.get("bears_on") or []))
    for ref in bears_on:
        if ref not in branch_ids:
            raise ValueError(
                f"narrative {narrative_id!r} log entry bears_on unknown branch_id {ref!r} "
                f"(known: {sorted(branch_ids)})"
            )
    return LogEntry(
        date=_as_date(body["date"]),
        source_ref=str(body.get("source_ref") or "").strip(),
        kind=kind,
        text=str(body.get("text") or "").strip(),
        bears_on=bears_on,
    )


def _parse_narrative(body: dict, *, enforce_revisit: bool) -> Narrative:
    narrative_id = str(body["narrative_id"])

    stage = str(body.get("stage") or STAGE_OPEN)
    if stage not in STAGES:
        raise ValueError(
            f"narrative {narrative_id!r}: stage {stage!r} not one of {STAGES}"
        )

    revisit = str(body.get("revisit") or "").strip()
    if enforce_revisit and not revisit:
        raise ValueError(
            f"narrative {narrative_id!r}: missing required field 'revisit' "
            "(a date or a condition string; a story with no date to come back to rots)"
        )

    branches = tuple(
        _parse_branch(b, narrative_id=narrative_id) for b in (body.get("branches") or [])
    )
    branch_ids = {b.branch_id for b in branches}
    log = tuple(
        _parse_log_entry(e, narrative_id=narrative_id, branch_ids=branch_ids)
        for e in (body.get("log") or [])
    )

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
        stage=stage,
        revisit=revisit,
        log=log,
        branches=branches,
    )


def _parse_snapshot_file(path: Path) -> tuple[date, tuple[Narrative, ...]]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    snapshot_date = _as_date(payload["snapshot_date"])
    enforce_revisit = snapshot_date >= REVISIT_REQUIRED_FROM
    raw_narratives = payload.get("narratives") or []
    narratives = tuple(
        _parse_narrative(n, enforce_revisit=enforce_revisit) for n in raw_narratives
    )
    return snapshot_date, narratives


def _snapshot_files(narratives_dir: Path) -> list[Path]:
    return sorted(narratives_dir.glob("*.yaml"))


def _pit_filter(narrative: Narrative, as_of: date) -> Narrative:
    """Drop log entries dated after as_of. The snapshot_date and per-narrative
    first_noted gates are applied by the caller; this is the same discipline
    carried down to the dated event list (contract R2 / §7). Branches carry no
    independent date, so those two gates are their whole PIT story."""
    kept = tuple(e for e in narrative.log if e.date <= as_of)
    return narrative if kept == narrative.log else replace(narrative, log=kept)


def load_as_of(as_of: date, narratives_dir: Path = DEFAULT_NARRATIVES_DIR) -> NarrativeSnapshot:
    """The latest snapshot with snapshot_date <= as_of; narratives with
    first_noted > as_of are dropped, and surviving narratives have their `log`
    trimmed to entries dated <= as_of. If every snapshot file postdates
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
    filtered = tuple(
        _pit_filter(n, as_of) for n in best_narratives if n.first_noted <= as_of
    )
    return NarrativeSnapshot(snapshot_date=best_date, narratives=filtered)


def history(
    narrative_id: str,
    as_of: date,
    narratives_dir: Path = DEFAULT_NARRATIVES_DIR,
) -> tuple[NarrativeVersion, ...]:
    """Every dated version of one narrative, oldest first.

    Return type: a tuple of NarrativeVersion (snapshot_date, narrative) — the
    whole parsed narrative from each snapshot file with snapshot_date <= as_of
    that contains `narrative_id`, in ascending snapshot_date order. Not a diff
    sequence: keeping full versions means "how many times / how far apart" is
    just `len()` and the dates, and a caller wanting field-level change diffs
    adjacent members itself. Each version gets the same PIT trim as
    load_as_of (first_noted > as_of drops the version; log entries dated after
    as_of are removed).
    """
    versions: list[NarrativeVersion] = []
    for path in _snapshot_files(narratives_dir):
        snapshot_date, narratives = _parse_snapshot_file(path)
        if snapshot_date > as_of:
            continue
        for narrative in narratives:
            if narrative.narrative_id != narrative_id:
                continue
            if narrative.first_noted > as_of:
                continue
            versions.append(
                NarrativeVersion(snapshot_date, _pit_filter(narrative, as_of))
            )
    versions.sort(key=lambda v: v.snapshot_date)
    return tuple(versions)


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
