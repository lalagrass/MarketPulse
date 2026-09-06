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

import math
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
# Sprint 008 DO-1: a fifth state, alongside the four above, not replacing them.
# It means "the narrative named its theme(s) directly via theme_ids", so the
# named_symbols membership test was never consulted for this narrative.
COVERAGE_DECLARED = "declared"

DEFAULT_NARRATIVES_DIR = Path("narratives")

# Display copy locked by spec 007 / 008. Do not rewrite from the numbers (D10).
TITLE_STRONG_UNCOVERED = "強但沒人講"
TITLE_COVERED_WEAK = "有人講但弱"
TITLE_REVISIT_DUE = "到期重看"
TITLE_REVISIT_CONDITIONAL = "條件型（無法判斷是否到期）"
TITLE_OUT_OF_CLASSIFICATION = "分類外代號"  # sprint 008 DO-1
TITLE_STORY_PROGRESS = "故事進度"  # sprint 008 DO-2
TITLE_RECENT_EVENTS = "最近事件"  # sprint 008 DO-2
UNKNOWN_THEME_ID_NOTE = "未知 theme_id（不在 themes/v1.yaml）"  # sprint 008 DO-1
NARRATIVE_COL_HEADER = "敘事"
NARRATIVE_MISSING = "—"
EMPTY_LIST = "（無）"
GAP_LIST_LIMIT = 5
CLAIM_PREVIEW_LEN = 30
STRONG_RANK_MAX = 3
REVISIT_SEP = " · "
RECENT_EVENTS_LIMIT = 3  # sprint 008 DO-2
EVENT_TEXT_PREVIEW_LEN = 40  # sprint 008 DO-2

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
    # Sprint 008 DO-1: optional, defaults to empty. A story can name the
    # theme(s) it is about before its symbols converge. Does not touch the
    # meaning of named_symbols / inferred_symbols — those stay symbol records.
    theme_ids: tuple[str, ...] = ()
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


@dataclass(frozen=True)
class NarrativeOverlay:
    """Read-only PIT view for display. Never written back to narratives/."""

    snapshot: NarrativeSnapshot
    themes: ThemeSet
    error: str | None = None
    # Sprint 008 DO-3 B2: theme_id → the latest snapshot_date <= as_of that
    # mentioned it, across every snapshot file (theme_last_mention_dates()).
    # None means "not computed" — display falls back to the single-snapshot
    # theme_mention_dates(). Not part of PIT correctness, just the label.
    mention_dates: dict[str, date] | None = None
    # Sprint 008 addendum A: does narratives/ hold at least one snapshot file?
    # The 分類外代號 / 故事進度 / 最近事件 blocks gate on THIS, not on whether
    # the PIT filter kept any narrative — so a dir with files but an early
    # as_of still shows the headers with （無） rather than vanishing.
    has_snapshot_files: bool = False


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
        theme_ids=tuple(str(t) for t in (body.get("theme_ids") or [])),
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
    if not narratives_dir.exists():
        return []
    return sorted(narratives_dir.glob("*.yaml"))


def has_snapshot_files(narratives_dir: Path = DEFAULT_NARRATIVES_DIR) -> bool:
    """True if narratives_dir holds at least one dated snapshot file (spec
    008 addendum A). Independent of the PIT filter — a file dated after
    as_of still counts."""
    return bool(_snapshot_files(narratives_dir))


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
        if narrative.theme_ids:
            # Sprint 008 DO-1: theme_ids explicit > named_symbols test. This
            # narrative declared its theme(s); the four-state logic below is
            # left exactly as it was for every narrative that did not.
            report[narrative.narrative_id] = COVERAGE_DECLARED
            continue
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


def load_as_of_lenient(
    as_of: date,
    narratives_dir: Path = DEFAULT_NARRATIVES_DIR,
) -> tuple[NarrativeSnapshot, str | None]:
    """load_as_of that never raises: a broken file becomes an empty snapshot
    plus one message. Layer 1 still has to print (spec 007 DO-1 acceptance 4).
    """
    empty = NarrativeSnapshot(snapshot_date=None, narratives=())
    try:
        return load_as_of(as_of, narratives_dir), None
    except Exception as exc:
        return empty, f"narrative 讀取失敗：{exc}"


def weak_rank_threshold(n_themes: int) -> int:
    """rank >= ceil(n_themes / 2). Spec 007 unresolved question 2; do not tune."""
    if n_themes <= 0:
        return 0
    return math.ceil(n_themes / 2)


def _member_sets(themes: ThemeSet) -> dict[str, set[str]]:
    return {theme.theme_id: set(theme.members) for theme in themes.themes}


def _mentioned_theme_ids(
    narrative: Narrative,
    member_sets: dict[str, set[str]],
) -> set[str]:
    """The theme ids one narrative mentions.

    Sprint 008 DO-1 priority, fixed: explicit `theme_ids` win outright; only
    when a narrative has none do we fall back to the named_symbols ∩ members
    test (the same test coverage_report uses — uncovered / unknown fall out
    of it as the empty set by construction). No merge, no vote. theme_ids
    that name no real theme are dropped here and surfaced separately by
    unknown_theme_ids().
    """
    if narrative.theme_ids:
        return {tid for tid in narrative.theme_ids if tid in member_sets}
    if not narrative.named_symbols:
        return set()
    named = set(narrative.named_symbols)
    return {tid for tid, members in member_sets.items() if named & members}


def theme_mention_dates(
    snapshot: NarrativeSnapshot,
    themes: ThemeSet,
) -> dict[str, date | None]:
    """theme_id → snapshot_date of the PIT snapshot if that theme is mentioned.

    A theme is mentioned when some narrative in the snapshot declares it via
    `theme_ids`, or (no theme_ids) names a symbol that sits in that theme.
    inferred_symbols and branch baskets are not consulted.

    Date shown is the snapshot_date of this PIT snapshot (spec 007: latest
    snapshot_date <= as_of), not first_noted and not a log date. For the
    "most recent time this theme was mentioned" across the whole PIT history
    (spec 008 DO-3 B2), use theme_last_mention_dates().
    """
    dates: dict[str, date | None] = {theme.theme_id: None for theme in themes.themes}
    if snapshot.snapshot_date is None or not snapshot.narratives:
        return dates
    member_sets = _member_sets(themes)
    for narrative in snapshot.narratives:
        for theme_id in _mentioned_theme_ids(narrative, member_sets):
            dates[theme_id] = snapshot.snapshot_date
    return dates


def theme_last_mention_dates(
    as_of: date,
    themes: ThemeSet,
    narratives_dir: Path = DEFAULT_NARRATIVES_DIR,
) -> dict[str, date | None]:
    """theme_id → the latest snapshot_date <= as_of on which any snapshot
    mentioned that theme (spec 008 DO-3 B2: the narrative column showed the
    PIT snapshot_date for every mentioned theme — a boolean wearing a date.
    This scans every snapshot file, so the column can say when a theme was
    genuinely last talked about).

    Same mention test as theme_mention_dates (theme_ids first, then
    named_symbols ∩ members), applied per snapshot. first_noted > as_of and
    log-after-as_of trimming are handled by _parse; first_noted is re-checked
    here. No cache layer — there are two files (contract #6).
    """
    dates: dict[str, date | None] = {theme.theme_id: None for theme in themes.themes}
    member_sets = _member_sets(themes)
    if not narratives_dir.exists():
        return dates
    for path in _snapshot_files(narratives_dir):
        snapshot_date, narratives = _parse_snapshot_file(path)
        if snapshot_date > as_of:
            continue
        for narrative in narratives:
            if narrative.first_noted > as_of:
                continue
            for theme_id in _mentioned_theme_ids(narrative, member_sets):
                current = dates.get(theme_id)
                if current is None or snapshot_date > current:
                    dates[theme_id] = snapshot_date
    return dates


def unknown_theme_ids(
    snapshot: NarrativeSnapshot,
    themes: ThemeSet,
) -> dict[str, tuple[str, ...]]:
    """narrative_id → the theme_ids it lists that are not in themes/v1.yaml.

    Spec 008 DO-1 acceptance 4: a typo in theme_ids must be visible on the
    screen, never silently swallowed. Whether load should also raise is spec
    unresolved question 1 — this function is the "make it visible" half and
    is independent of that decision.
    """
    known = {theme.theme_id for theme in themes.themes}
    out: dict[str, tuple[str, ...]] = {}
    for narrative in snapshot.narratives:
        bad = tuple(t for t in narrative.theme_ids if t not in known)
        if bad:
            out[narrative.narrative_id] = bad
    return out


def out_of_classification_symbols(
    snapshot: NarrativeSnapshot,
    themes: ThemeSet,
) -> list[tuple[str, str]]:
    """(narrative_id, symbol) for every named_symbol that is in no theme's
    membership (spec 008 DO-1: the `分類外代號` block). This is the display of
    a classification gap, not an auto-fix — the symbol is not slotted into
    any theme. Narrative order, then the order symbols are listed.
    """
    all_members = {m for theme in themes.themes for m in theme.members}
    out: list[tuple[str, str]] = []
    for narrative in snapshot.narratives:
        for symbol in narrative.named_symbols:
            if symbol not in all_members:
                out.append((narrative.narrative_id, symbol))
    return out


def parse_revisit_date(revisit: str) -> date | None:
    """ISO date or nothing. Do not parse natural language (spec 007 DO-2)."""
    text = (revisit or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _claim_preview(text: str, n: int = CLAIM_PREVIEW_LEN) -> str:
    return " ".join((text or "").split())[:n]


def render_revisit_due(snapshot: NarrativeSnapshot, as_of: date) -> str:
    """Due-revisit block. Read-only: does not write narratives/ or change stage."""
    due_lines: list[str] = []
    cond_lines: list[str] = []
    for narrative in snapshot.narratives:
        parsed = parse_revisit_date(narrative.revisit)
        if parsed is None:
            if (narrative.revisit or "").strip():
                cond_lines.append(
                    f"{narrative.narrative_id}{REVISIT_SEP}{narrative.revisit.strip()}"
                )
            continue
        if parsed > as_of:
            continue
        if narrative.branches:
            for branch in narrative.branches:
                due_lines.append(
                    f"{narrative.narrative_id}{REVISIT_SEP}"
                    f"{branch.branch_id}{REVISIT_SEP}"
                    f"{parsed.isoformat()}{REVISIT_SEP}"
                    f"{_claim_preview(branch.claim)}"
                )
        else:
            due_lines.append(
                f"{narrative.narrative_id}{REVISIT_SEP}"
                f"{NARRATIVE_MISSING}{REVISIT_SEP}"
                f"{parsed.isoformat()}{REVISIT_SEP}"
                f"{_claim_preview(narrative.note or narrative.name)}"
            )

    def _block(title: str, lines: list[str]) -> list[str]:
        return [title, *(lines if lines else [EMPTY_LIST]), ""]

    parts = _block(TITLE_REVISIT_DUE, due_lines)
    parts.extend(_block(TITLE_REVISIT_CONDITIONAL, cond_lines))
    return "\n".join(parts)


def story_last_changed(
    narrative_id: str,
    as_of: date,
    narratives_dir: Path = DEFAULT_NARRATIVES_DIR,
) -> date | None:
    """The snapshot_date of the last PIT snapshot on which this narrative
    differed from its previous version (spec 008 DO-2 "上次變動").

    Granularity, per spec unresolved question 2's default: the whole
    Narrative object — any field differing between adjacent versions counts.
    `history()` already applies the PIT trim (first_noted, log <= as_of), so
    the comparison is between the versions a reader would actually have seen.
    One version (or none) → None, rendered as `—`.
    """
    versions = history(narrative_id, as_of, narratives_dir)
    if len(versions) < 2:
        return None
    last: date | None = None
    for prev, cur in zip(versions, versions[1:]):
        if cur.narrative != prev.narrative:
            last = cur.snapshot_date
    return last


def _theme_or_symbol_count(narrative: Narrative) -> str:
    """`故事進度`'s third field: how converged the story is. theme_ids if the
    story declared them, else its named_symbols. Never both — they are a
    priority, not a sum (contract: no composite)."""
    if narrative.theme_ids:
        return f"{len(narrative.theme_ids)}主題"
    return f"{len(narrative.named_symbols)}代號"


def render_story_progress(
    snapshot: NarrativeSnapshot,
    as_of: date,
    narratives_dir: Path = DEFAULT_NARRATIVES_DIR,
) -> str:
    """`故事進度` + `最近事件` (spec 008 DO-2). Facts and dates only — no
    heat / burst / acceleration / trend, no arrow, colour, score or ordering
    weight. Read-only: never writes narratives/ and never advances `stage`.

    - 故事進度: one line per narrative,
      `narrative_id · stage · <n主題|n代號> · <上次變動日期|—>`
    - 最近事件: the most recent RECENT_EVENTS_LIMIT PIT `log` entries across
      all narratives, `narrative_id · date · text[:EVENT_TEXT_PREVIEW_LEN]`
    """
    progress: list[str] = []
    for narrative in snapshot.narratives:
        changed = story_last_changed(narrative.narrative_id, as_of, narratives_dir)
        progress.append(
            f"{narrative.narrative_id}{REVISIT_SEP}{narrative.stage}{REVISIT_SEP}"
            f"{_theme_or_symbol_count(narrative)}{REVISIT_SEP}"
            f"{changed.isoformat() if changed is not None else NARRATIVE_MISSING}"
        )

    events: list[tuple[date, str, str]] = []
    for narrative in snapshot.narratives:
        for entry in narrative.log:
            events.append((entry.date, narrative.narrative_id, entry.text))
    events.sort(key=lambda e: e[0], reverse=True)
    event_lines = [
        f"{nid}{REVISIT_SEP}{when.isoformat()}{REVISIT_SEP}"
        f"{' '.join((text or '').split())[:EVENT_TEXT_PREVIEW_LEN]}"
        for when, nid, text in events[:RECENT_EVENTS_LIMIT]
    ]

    def _block(title: str, lines: list[str]) -> list[str]:
        return [title, *(lines if lines else [EMPTY_LIST]), ""]

    parts = _block(TITLE_STORY_PROGRESS, progress)
    parts.extend(_block(TITLE_RECENT_EVENTS, event_lines))
    return "\n".join(parts).rstrip("\n")
