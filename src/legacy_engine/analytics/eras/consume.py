"""Era-horizon adapter — the consumption seam between the persisted ``entity_eras`` ledger
(``analytics/eras/store.py``) and the two remaining regime-windowed surfaces that read it: the
adaptive matchup matrix (``analytics/matchup.py::build_adaptive_matrix``) and the global field
window (``advisory/window.py::build_advisory_inputs``). Neither consumer touches ``entity_eras``
directly — everything routes through this module's ``era_horizons``/``resolve_field_era`` so the
resolution-order semantics live in exactly one place.

**Resolution order per entity label** (epic decision):
  1. EXACT match in ``entity_eras`` — a camp's own row, or a parent archetype's own row.
  2. PARENT match — camp labels (``f"{parent} [{variant}]"``, the same convention
     ``series.build_entity_series`` and ``match_results.effective_label`` both use) fall back to
     their parent archetype's ``entity_eras`` row when the camp itself has no row of its own.
  3. BAN-ONLY fallback (``analytics.affectedness.archetype_valid_since``) when the entity —
     parent included — has no ``entity_eras`` row at all (never analyzed: below the detection
     floors, or ``eras run`` hasn't covered it).

Present-with-``None`` (an analyzed, undisturbed entity) means full history is solid — this
WIDENS that entity beyond the current regime relative to the pre-epic ban-only behavior; that
widening is the epic's intended payoff, not a bug.

**Whole-path degrade**: when ``entity_eras`` is missing/empty entirely, every label falls to
"ban-only" and one audit line names the degrade ("run `eras run`") — never a silently different
number.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from collections import Counter
from datetime import UTC, date, datetime
from hashlib import sha256
import json
from typing import Literal

import duckdb
from pydantic import model_validator

from legacy_engine.analytics.eras.store import StoredEntityEras, read_entity_eras
from legacy_engine.models.base import LegacyEngineModel
from legacy_engine.models.matchup import MatchupCell

KnowledgeMode = Literal["retrospective-current-model", "as-known-then"]
EligibilitySource = Literal[
    "current-reference",
    "certified-history",
    "scalar-current",
    "camp-current-only",
    "localized-pre-exposure",
    "localized-post-ban",
]


class AnalysisClock(LegacyEngineModel):
    data_until: date
    knowledge_as_of: datetime
    knowledge_mode: KnowledgeMode

    @model_validator(mode="after")
    def _utc(self) -> "AnalysisClock":
        if self.knowledge_as_of.tzinfo is None or self.knowledge_as_of.utcoffset() is None:
            raise ValueError("knowledge_as_of must be timezone-aware")
        object.__setattr__(self, "knowledge_as_of", self.knowledge_as_of.astimezone(UTC))
        return self


class EligibilitySourceRef(LegacyEngineModel):
    source: EligibilitySource
    entity: str
    segment_id: str | None = None
    certificate_id: str | None = None
    certificate_run_id: str | None = None
    card: str | None = None
    exposure_start: date | None = None
    ban_date: date | None = None
    boundary_provenance: Literal[
        "released-at", "corpus-first-seen", "first-material-adoption"
    ] | None = None


class EligibilityAtom(LegacyEngineModel):
    component_id: str
    start: date | None = None
    end: date
    sources: tuple[EligibilitySourceRef, ...]

    @model_validator(mode="after")
    def _bounds(self) -> "EligibilityAtom":
        if self.end is None or (self.start is not None and self.start >= self.end):
            raise ValueError("eligibility atom must be non-empty and half-open")
        if not self.sources:
            raise ValueError("eligibility atom requires provenance")
        return self


class EntityEligibility(LegacyEngineModel):
    entity: str
    current: tuple[EligibilityAtom, ...]
    expanded: tuple[EligibilityAtom, ...]
    certificate_run_id: str | None
    clock: AnalysisClock
    status: Literal["certified-expanded", "localized-expanded", "current-only", "abstained"]
    reasons: tuple[str, ...]


class EvidenceConcentration(LegacyEngineModel):
    raw_n: int
    distinct_events: int
    distinct_dates: int
    distinct_pilots: int | None
    pilot_identity_available: bool
    effective_events: float
    max_event_id: str | None = None
    max_event_share: float | None = None
    max_source: str | None = None
    max_source_share: float | None = None
    max_component_id: str | None = None
    max_component_share: float | None = None
    event_counts: dict[str, int] = {}
    source_counts: dict[str, int] = {}
    component_counts: dict[str, int] = {}


class PriorEvidenceAudit(LegacyEngineModel):
    policy: Literal["pre-disturbance", "hierarchy-only"]
    observation_match_ids_sha256: str
    prior_match_ids_sha256: str | None
    prior_match_ids: tuple[str, ...] = ()
    prior_mean: float = 0.5
    prior_source: str = "marginal (leave-cell-out)"
    overlap_n: int
    reason: str


class MatchupEvidenceView(LegacyEngineModel):
    kind: Literal["current-only", "certified-expanded", "added-history"]
    cell: MatchupCell | None = None
    match_ids: tuple[str, ...]
    pair_component_ids: tuple[str, ...]
    certificate_ids: tuple[str, ...]
    concentration: EvidenceConcentration
    prior: PriorEvidenceAudit
    status: Literal["available", "thin", "concentrated", "abstained"]
    reasons: tuple[str, ...]


class MatchupEvidenceViews(LegacyEngineModel):
    subject: str
    opponent: str
    clock: AnalysisClock
    current_only: MatchupEvidenceView
    certified_expanded: MatchupEvidenceView
    added_history: MatchupEvidenceView


def _source_key(source: EligibilitySourceRef) -> str:
    return json.dumps(source.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))


def _atom_id(start: date | None, end: date, sources: tuple[EligibilitySourceRef, ...]) -> str:
    payload = f"{start.isoformat() if start else '-inf'}|{end.isoformat()}|" + ";".join(_source_key(s) for s in sources)
    return "component-" + sha256(payload.encode()).hexdigest()[:32]


def normalize_atoms(atoms: tuple[EligibilityAtom, ...]) -> tuple[EligibilityAtom, ...]:
    """Sweep interval endpoints into disjoint atoms without bridging gaps."""
    if not atoms:
        return ()
    points = {a.start for a in atoms if a.start is not None} | {a.end for a in atoms}
    ordered = sorted(points)
    spans: list[tuple[date | None, date]] = []
    if any(a.start is None for a in atoms):
        first = ordered[0]
        spans.append((None, first))
    spans.extend((left, right) for left, right in zip(ordered, ordered[1:]) if left < right)
    result: list[EligibilityAtom] = []
    for start, end in spans:
        covering_by_key = {
            _source_key(source): source
            for atom in atoms
            if (atom.start is None or (start is not None and atom.start <= start)) and atom.end >= end
            for source in atom.sources
        }
        covering = tuple(covering_by_key[key] for key in sorted(covering_by_key))
        if not covering:
            continue
        candidate = EligibilityAtom(component_id=_atom_id(start, end, covering), start=start, end=end, sources=covering)
        if result and result[-1].end == start and result[-1].sources == candidate.sources:
            previous = result.pop()
            candidate = EligibilityAtom(component_id=_atom_id(previous.start, end, covering), start=previous.start, end=end, sources=covering)
        result.append(candidate)
    return tuple(result)


def intersect_atoms(left: tuple[EligibilityAtom, ...], right: tuple[EligibilityAtom, ...], *, data_until: date | None = None) -> tuple[EligibilityAtom, ...]:
    """Intersect two normalized sets, retaining both provenance tuples."""
    out: list[EligibilityAtom] = []
    for a in left:
        for b in right:
            start = a.start if b.start is None else b.start if a.start is None else max(a.start, b.start)
            end = min(a.end, b.end)
            if data_until is not None:
                end = min(end, data_until)
            if start is not None and start >= end:
                continue
            if start is None and end <= date.min:
                continue
            sources = tuple(sorted((*a.sources, *b.sources), key=_source_key))
            out.append(EligibilityAtom(component_id=_atom_id(start, end, sources), start=start, end=end, sources=sources))
    return normalize_atoms(tuple(out))


def localized_clean_atoms(
    entity: str,
    *,
    start: date | None,
    end: date,
    boundaries: Sequence[object],
) -> tuple[EligibilityAtom, ...]:
    """Compile clean intervals around explicit localized-ban contamination gaps."""

    relevant = tuple(
        boundary
        for boundary in boundaries
        if boundary.contaminated_start < end
        and (start is None or boundary.contaminated_end > start)
    )
    if not relevant:
        ref = EligibilitySourceRef(source="scalar-current", entity=entity)
        return (
            EligibilityAtom(
                component_id=_atom_id(start, end, (ref,)),
                start=start,
                end=end,
                sources=(ref,),
            ),
        ) if start is None or start < end else ()

    result: list[EligibilityAtom] = []
    cursor = start
    for boundary in sorted(
        relevant, key=lambda item: (item.contaminated_start, item.contaminated_end, item.cards)
    ):
        gap_start = boundary.contaminated_start
        gap_end = min(boundary.contaminated_end, end)
        if cursor is not None and gap_end <= cursor:
            continue
        clean_end = min(gap_start, end)
        if cursor is None or cursor < clean_end:
            ref = EligibilitySourceRef(
                source="localized-pre-exposure",
                entity=entity,
                card=" + ".join(boundary.cards),
                exposure_start=boundary.contaminated_start,
                ban_date=boundary.ban_date,
                boundary_provenance=boundary.provenance,
            )
            result.append(
                EligibilityAtom(
                    component_id=_atom_id(cursor, clean_end, (ref,)),
                    start=cursor,
                    end=clean_end,
                    sources=(ref,),
                )
            )
        cursor = gap_end if cursor is None else max(cursor, gap_end)
        if cursor >= end:
            break
    if cursor is None or cursor < end:
        boundary = max(
            relevant, key=lambda item: (item.contaminated_end, item.contaminated_start, item.cards)
        )
        ref = EligibilitySourceRef(
            source="localized-post-ban",
            entity=entity,
            card=" + ".join(boundary.cards),
            exposure_start=boundary.contaminated_start,
            ban_date=boundary.ban_date,
            boundary_provenance=boundary.provenance,
        )
        result.append(
            EligibilityAtom(
                component_id=_atom_id(cursor, end, (ref,)),
                start=cursor,
                end=end,
                sources=(ref,),
            )
        )
    return normalize_atoms(tuple(result))

# Field-era self-heal gate (epic design decision): below this many decks in the candidate
# [field_since, now) window, the detection-derived field era is too thin to trust — degrade back
# to the ban-regime start with a labeled banner. Decks-based (not rounds-based, unlike
# advisory/window.py's `_THIN_ROUNDS_FLOOR`) since field share is a deck/metashare concept.
_FIELD_THIN_DECKS_FLOOR: int = 500

_FIELD_MIN_SHARE_DEFAULT: float = 0.02


class PairWindow(LegacyEngineModel):
    """Outcome-blind lower bound for a current subject/opponent comparison."""

    subject: str
    opponent: str
    requested_since: str | None
    subject_since: str | None
    opponent_since: str | None
    effective_since: str | None
    clamped: bool
    reason: str


def clamp_pair_window(
    subject: str,
    opponent: str,
    *,
    subject_since: str | None,
    opponent_since: str | None,
    requested_since: str | None = None,
) -> PairWindow:
    """Clamp a comparison to the latest requested or entity-specific horizon."""
    bounds = {
        "requested lower bound": requested_since,
        f"subject horizon ({subject})": subject_since,
        f"opponent horizon ({opponent})": opponent_since,
    }
    effective = max((value for value in bounds.values() if value is not None), default=None)
    winners = [name for name, value in bounds.items() if value is not None and value == effective]
    reason = (
        "full corpus: no requested or entity horizon"
        if effective is None
        else f"clamped by {', '.join(winners)} at {effective}"
    )
    return PairWindow(
        subject=subject,
        opponent=opponent,
        requested_since=requested_since,
        subject_since=subject_since,
        opponent_since=opponent_since,
        effective_since=effective,
        clamped=effective != requested_since,
        reason=reason,
    )


def _parent_label(label: str, split_variant: str | None) -> str:
    """Strip a variant-camp suffix so a camp label resolves to its parent archetype.

    Duplicated (not imported) from ``analytics.matchup._base_archetype``: ``matchup.py`` imports
    ``era_horizons`` from this module for its own default resolution, so importing
    ``_base_archetype`` back would create an ``eras -> matchup -> eras`` import cycle. Same shape
    as ``attribution.py``'s own duplicated-constant precedent (``_BAN_AFFECT_THRESHOLD``) for the
    identical reason — a one-line rule doesn't warrant a cross-module private import.
    """
    if split_variant is not None and label.startswith(f"{split_variant} ["):
        return split_variant
    return label


def _resolve_parent(
    label: str, split_variant: str | None, camp_parent: "Mapping[str, str] | None",
) -> str:
    """The parent archetype of ``label`` — explicit ``camp_parent`` entry first, prefix rule after.

    The multi-split matrix splits MANY parents at once, and the staged registry contains both
    ``Painter`` and ``Blue Painter``: a prefix rule cannot disambiguate those, so
    ``compute_match_results`` records the camp -> parent map at relabel time (the labeler knows the
    parent) and threads it here. A label absent from the map falls through to the single-split
    prefix rule, which is the identity when ``split_variant`` is ``None``.
    """
    if camp_parent is not None:
        parent = camp_parent.get(label)
        if parent is not None:
            return parent
    return _parent_label(label, split_variant)


class EraHorizon(LegacyEngineModel):
    """One entity's resolved adaptive-matrix horizon.

    ``since``: the horizon date, or ``None`` for full history.
    ``source``: ``"era"`` (the entity's own ``entity_eras`` row) | ``"era-parent"`` (inherited via
    camp -> parent fallback) | ``"ban-only"`` (no ``entity_eras`` row at all — the pre-epic
    fallback, via ``archetype_valid_since``).
    ``trigger``: the human-readable cause of the horizon (a ban/release/unattributed detail from
    the winning boundary's attribution), or ``None`` when there is no disturbance to name
    (undisturbed entity, or a ban-only horizon with no affecting ban).
    ``alarm``: the entity's drift-alarm note when its alarm fired, else ``None``.
    ``attribution_kind``: the winning boundary's attribution kind (``"ban"`` | ``"release"`` |
    ``"unattributed"``), ``None`` when there is no era boundary behind the horizon (additive,
    epic-superarchetype-layer-chain — the young-era ladder-order rule keys on it).
    """

    since: str | None
    source: str
    trigger: str | None
    alarm: str | None
    attribution_kind: str | None = None
    stored_since: str | None = None
    affected_since: str | None = None
    clamped_by_confirmed_ban: bool = False


def _winning_boundary_attribution(stored: StoredEntityEras):
    """The stored attribution of the boundary that set ``stored.stable_since``.

    ``None`` when ``stable_since`` is ``None`` (no accepted boundary — undisturbed) or the
    winning boundary's attribution wasn't recorded (shouldn't normally happen — every accepted
    boundary is attributed by ``eras run``, even if only to "unattributed disturbance").
    """
    if stored.stable_since is None:
        return None
    for b in stored.boundaries:
        if b.bh_accepted and not b.floor_rejected and b.date == stored.stable_since:
            return b.attribution
    return None


def _winning_boundary_trigger(stored: StoredEntityEras) -> str | None:
    """The attribution DETAIL of the winning boundary (kept for external callers)."""
    attribution = _winning_boundary_attribution(stored)
    return attribution.detail if attribution is not None else None


def era_horizons(
    con: duckdb.DuckDBPyConnection,
    archetypes: Sequence[str],
    *,
    provenance: str | None = None,
    split_variant: str | None = None,
    camp_parent: "Mapping[str, str] | None" = None,
    affect_threshold: float = 0.25,
    ban_events: Sequence[tuple[object, str, str]] | None = None,
) -> tuple[dict[str, EraHorizon], tuple[str, ...]]:
    """Resolve every label in ``archetypes`` to an ``EraHorizon`` (exact -> parent -> ban-only).

    ``archetypes`` may be plain parent-archetype labels or ``f"{split_variant} [{variant}]"`` camp
    labels (``split_variant`` names which archetype's camps these are — the same convention
    ``matchup.build_adaptive_matrix`` itself uses). Returns ``(horizons, audit_preamble)`` where
    ``audit_preamble`` is empty unless ``entity_eras`` is missing/empty entirely, in which case it
    carries exactly one whole-path-degrade line.

    ``camp_parent`` (opt-in, default ``None``): an explicit ``camp label -> parent archetype`` map
    (``MatchResults.camp_parent``) used INSTEAD of the prefix rule for the labels it covers — the
    multi-split matrix splits many parents at once, where prefixes are ambiguous. Labels it does
    not cover still resolve by prefix, so ``None`` is the untouched single-split path.
    """
    from legacy_engine.analytics.affectedness import archetype_valid_since

    stored = read_entity_eras(con)
    no_era_data = not stored

    parent_for = {
        label: _resolve_parent(label, split_variant, camp_parent) for label in archetypes
    }
    try:
        affected_candidates = archetype_valid_since(
            con,
            sorted({*archetypes, *parent_for.values()}),
            provenance=provenance,
            affect_threshold=affect_threshold,
            ban_events=ban_events,
        )
    except duckdb.CatalogException as exc:
        # Era-only consumers and small unit fixtures may intentionally omit the corpus tables.
        # The old adapter resolved those rows without touching affectedness; retain that safe
        # degrade rather than turning a missing optional table into a hard failure.
        if "decks" not in str(exc).lower():
            raise
        affected_candidates = {label: None for label in {*archetypes, *parent_for.values()}}

    def affected_since_for(label: str) -> str | None:
        candidates = [affected_candidates.get(label)]
        parent = parent_for[label]
        if parent != label:
            candidates.append(affected_candidates.get(parent))
        return max((candidate for candidate in candidates if candidate is not None), default=None)

    def resolved(
        label: str,
        *,
        stored_since: str | None,
        source: str,
        trigger: str | None,
        alarm: str | None,
        attribution_kind: str | None,
    ) -> EraHorizon:
        affected_since = affected_since_for(label)
        winning_since = max(
            (candidate for candidate in (stored_since, affected_since) if candidate is not None),
            default=None,
        )
        # A confirmed ban is a clamp even when the era detector explicitly stored
        # ``stable_since: null`` (an analyzed but not-yet-settled entity).  The
        # null is not permission to discard the ban candidate or its provenance.
        clamped = (
            source != "ban-only"
            and affected_since is not None
            and (stored_since is None or affected_since > stored_since)
        )
        if clamped:
            source = "ban-clamped"
            trigger = f"ban: valid_since {affected_since}"
            attribution_kind = None
        elif stored_since is None and affected_since is not None and source == "ban-only":
            trigger = f"ban: valid_since {affected_since}"
        # Keep the untouched legacy shape byte-compatible.  Candidate fields are published when
        # a confirmed ban actually overrides a stored horizon; unaffected/full-history and
        # ban-only rows retain their original compact provenance.
        candidate_fields = {
            "stored_since": stored_since,
            "affected_since": affected_since,
            "clamped_by_confirmed_ban": clamped,
        } if clamped else {}
        return EraHorizon(
            since=winning_since,
            source=source,
            trigger=trigger,
            alarm=alarm,
            attribution_kind=attribution_kind,
            **candidate_fields,
        )

    horizons: dict[str, EraHorizon] = {}
    need_ban_only: list[str] = []

    for label in archetypes:
        entry = stored.get(label)
        if entry is not None:
            attribution = _winning_boundary_attribution(entry)
            horizons[label] = resolved(
                label, stored_since=entry.stable_since, source="era",
                trigger=attribution.detail if attribution is not None else None,
                alarm=(entry.alarm_note if entry.alarm_fired else None),
                attribution_kind=attribution.kind if attribution is not None else None,
            )
            continue

        parent = _resolve_parent(label, split_variant, camp_parent)
        parent_entry = stored.get(parent) if parent != label else None
        if parent_entry is not None:
            attribution = _winning_boundary_attribution(parent_entry)
            horizons[label] = resolved(
                label, stored_since=parent_entry.stable_since, source="era-parent",
                trigger=attribution.detail if attribution is not None else None,
                alarm=(parent_entry.alarm_note if parent_entry.alarm_fired else None),
                attribution_kind=attribution.kind if attribution is not None else None,
            )
            continue

        need_ban_only.append(label)

    if need_ban_only:
        base_labels = sorted(
            {_resolve_parent(a, split_variant, camp_parent) for a in need_ban_only}
        )
        base_valid_since = archetype_valid_since(
            con, base_labels, provenance=provenance, affect_threshold=affect_threshold,
            ban_events=ban_events,
        )
        for label in need_ban_only:
            base = _resolve_parent(label, split_variant, camp_parent)
            since = base_valid_since.get(base)
            horizons[label] = resolved(
                label, stored_since=None, source="ban-only",
                trigger=(f"ban: valid_since {since}" if since else None), alarm=None,
                attribution_kind=None,
            )

    audit: tuple[str, ...] = ()
    if no_era_data:
        audit = ("// eras: no era data — ban-only horizons; run `eras run`",)

    return horizons, audit


def build_entity_eligibility(
    con: duckdb.DuckDBPyConnection,
    entity: str,
    *,
    clock: AnalysisClock,
    certificate_run_id: str | None = None,
    requested_since: date | None = None,
    camp_parent: Mapping[str, str] | None = None,
    provenance: str | None = None,
    ban_events: Sequence[tuple[object, str, str]] | None = None,
    released_at_by_card: Mapping[str, date] | None = None,
) -> EntityEligibility:
    """Compile scalar horizons and one exact certification run into interval authority."""
    from legacy_engine.analytics.eras.certificate_store import read_certification_run

    from legacy_engine.analytics.affectedness import exposure_boundary_authorities

    parent = camp_parent.get(entity) if camp_parent else None
    is_camp = parent is not None
    horizons, _ = era_horizons(
        con, [entity], provenance=provenance, camp_parent=camp_parent,
        ban_events=ban_events,
    )
    horizon_authority = horizons[entity]
    horizon = horizon_authority.since
    current_start = date.fromisoformat(horizon) if horizon else None
    if requested_since is not None and (current_start is None or requested_since > current_start):
        current_start = requested_since
    current_source: EligibilitySource = "camp-current-only" if is_camp else "scalar-current"
    reasons: list[str] = []
    current_segment: str | None = None
    run = None
    result = None
    current_end = clock.data_until
    run_invalid = False
    localized_boundaries = ()
    if not is_camp:
        try:
            localized_boundaries = exposure_boundary_authorities(
                con,
                (entity,),
                provenance=provenance,
                ban_events=ban_events,
                released_at_by_card=released_at_by_card,
            )[entity]
        except duckdb.CatalogException as exc:
            if "decks" not in str(exc).lower() and "deck_cards" not in str(exc).lower():
                raise
    if certificate_run_id is not None and not is_camp:
        try:
            run = read_certification_run(con, certificate_run_id)
        except ValueError:
            run = None
            run_invalid = True
        result = next((item for item in run.results if item.entity == entity), None) if run else None
        valid_envelope = bool(
            run is not None
            and run.status in ("complete", "degraded")
            and run.knowledge_available_at is not None
            and run.knowledge_available_at <= clock.knowledge_as_of
            and result is not None
            and not run.manifest.calibration_profile_id.endswith("-candidate")
        )
        if valid_envelope and result is not None and result.reference_interval is not None and result.reference_segment_id:
            current_start = max(result.reference_interval.start, requested_since) if requested_since else result.reference_interval.start
            current_segment = result.reference_segment_id
            current_end = min(result.reference_interval.end, clock.data_until)
        elif result is not None:
            reasons.append("current-reference-missing")
    latest_localized = max(
        (
            boundary
            for boundary in localized_boundaries
            if current_start is not None and boundary.clean_post_ban_start == current_start
        ),
        key=lambda boundary: (boundary.ban_date, boundary.cards),
        default=None,
    )
    current_ref = EligibilitySourceRef(
        source=(
            "current-reference"
            if current_segment
            else "localized-post-ban"
            if latest_localized is not None
            else current_source
        ),
        entity=entity,
        segment_id=current_segment,
        certificate_run_id=certificate_run_id if current_segment else None,
        card=" + ".join(latest_localized.cards) if latest_localized is not None else None,
        exposure_start=(
            latest_localized.contaminated_start if latest_localized is not None else None
        ),
        ban_date=latest_localized.ban_date if latest_localized is not None else None,
        boundary_provenance=(
            latest_localized.provenance if latest_localized is not None else None
        ),
    )
    current = (EligibilityAtom(component_id=_atom_id(current_start, current_end, (current_ref,)), start=current_start, end=current_end, sources=(current_ref,)),) if current_start is None or current_start < current_end else ()
    expanded: list[EligibilityAtom] = list(current)
    if is_camp:
        reasons.append("camp-current-only")
    elif certificate_run_id is None:
        reasons.append("no-certificate-run")
    else:
        if run_invalid:
            reasons.append("certificate-run-invalid")
        elif run is None:
            run = read_certification_run(con, certificate_run_id)
        result = result or (next((item for item in run.results if item.entity == entity), None) if run else None)
        if run_invalid:
            pass
        elif run is None:
            reasons.append("certificate-run-not-found")
        elif run.status not in ("complete", "degraded"):
            reasons.append("certificate-run-not-final")
        elif run.manifest.calibration_profile_id.endswith("-candidate"):
            reasons.append("unpromoted-calibration-profile")
        elif result is None:
            reasons.append("certificate-result-not-found")
        elif run.knowledge_available_at is None:
            reasons.append("knowledge-provenance-unavailable")
        elif run.knowledge_available_at > clock.knowledge_as_of:
            reasons.append("knowledge-available-after-knowledge_as_of")
        else:
            certificate_counts = Counter(cert.certificate_id for cert in result.certificates)
            for cert in result.certificates:
                if certificate_counts[cert.certificate_id] > 1:
                    reasons.append(f"certificate-{cert.certificate_id}-duplicate")
                    continue
                if cert.calibration_profile_id != run.manifest.calibration_profile_id:
                    reasons.append(f"certificate-{cert.certificate_id}-profile-mismatch")
                    continue
                if cert.feature_schema_version != run.manifest.feature_schema_version:
                    reasons.append(f"certificate-{cert.certificate_id}-schema-mismatch")
                    continue
                if cert.status != "certified":
                    reasons.append(f"certificate-{cert.certificate_id}-status-{cert.status}")
                    continue
                if (
                    cert.semantic.disposition != "pass"
                    or cert.support.disposition != "pass"
                    or cert.context_overlap.disposition != "pass"
                    or cert.equivalence is None
                    or cert.equivalence.disposition != "pass"
                ):
                    reasons.append(f"certificate-{cert.certificate_id}-guard-mismatch")
                    continue
                if cert.entity != entity or cert.discovery_run_id != run.manifest.discovery_run_id:
                    reasons.append(f"certificate-{cert.certificate_id}-identity-mismatch")
                    continue
                if (
                    cert.reference_segment_id != result.reference_segment_id
                    or cert.reference_interval != result.reference_interval
                    or cert.certification_as_of != run.manifest.certification_as_of
                ):
                    reasons.append(f"certificate-{cert.certificate_id}-reference-mismatch")
                    continue
                if clock.knowledge_mode == "as-known-then" and cert.certification_as_of > clock.knowledge_as_of.date():
                    reasons.append(f"certificate-{cert.certificate_id}-future-source-evidence")
                    continue
                start = cert.historical_interval.start
                end = min(cert.historical_interval.end, clock.data_until)
                if requested_since is not None:
                    start = max(start, requested_since)
                if start >= end:
                    continue
                ref = EligibilitySourceRef(
                    source="certified-history", entity=entity,
                    segment_id=cert.historical_segment_id, certificate_id=cert.certificate_id,
                    certificate_run_id=run.run_id,
                )
                expanded.append(EligibilityAtom(
                    component_id=_atom_id(start, end, (ref,)), start=start, end=end, sources=(ref,),
                ))
    if localized_boundaries and not is_camp:
        localized_start = (
            date.fromisoformat(horizon_authority.stored_since)
            if horizon_authority.clamped_by_confirmed_ban
            and horizon_authority.stored_since is not None
            else None
        )
        if requested_since is not None and (
            localized_start is None or requested_since > localized_start
        ):
            localized_start = requested_since
        clean = localized_clean_atoms(
            entity,
            start=localized_start,
            end=current_end,
            boundaries=localized_boundaries,
        )
        certified_clean = intersect_atoms(
            normalize_atoms(tuple(expanded)), clean, data_until=current_end
        )
        expanded = [*clean, *certified_clean]
        reasons.extend(
            f"localized-ban-gap:{' + '.join(boundary.cards)}:"
            f"{boundary.contaminated_start.isoformat()}:"
            f"{boundary.contaminated_end.isoformat()}:"
            f"{boundary.provenance}"
            for boundary in localized_boundaries
        )
    expanded_norm = normalize_atoms(tuple(expanded))
    status: Literal[
        "certified-expanded", "localized-expanded", "current-only", "abstained"
    ] = (
        "certified-expanded" if any(any(s.source == "certified-history" for s in atom.sources) for atom in expanded_norm)
        else "localized-expanded" if any(
            any(s.source == "localized-pre-exposure" for s in atom.sources)
            for atom in expanded_norm
        )
        else "current-only"
    )
    if not current:
        reasons.append("current-reference-empty-at-data_until")
        status = "abstained"
    return EntityEligibility(
        entity=entity, current=current, expanded=expanded_norm,
        certificate_run_id=certificate_run_id, clock=clock, status=status,
        reasons=tuple(dict.fromkeys(reasons)),
    )


def _digest_ids(ids: Sequence[str]) -> str:
    return sha256("\n".join(sorted(ids)).encode()).hexdigest()


def _concentration(rows: Sequence[object]) -> EvidenceConcentration:
    event_counts: dict[str, int] = {}
    source_counts: dict[str, int] = {}
    component_counts: dict[str, int] = {}
    dates: set[date] = set()
    pilots: set[str] = set()
    pilot_available = True
    for selected in rows:
        record = selected.match
        event_counts[record.event_id] = event_counts.get(record.event_id, 0) + 1
        source_counts[record.provenance] = source_counts.get(record.provenance, 0) + 1
        component_counts[selected.pair_component_id] = component_counts.get(selected.pair_component_id, 0) + 1
        dates.add(record.event_date)
        if record.subject_player_id is None or record.opponent_player_id is None:
            pilot_available = False
        else:
            pilots.update((record.subject_player_id, record.opponent_player_id))
    raw_n = len(rows)
    def dominant(values: dict[str, int]) -> tuple[str | None, float | None]:
        if not values or not raw_n:
            return None, None
        key, count = max(sorted(values.items()), key=lambda item: item[1])
        return key, count / raw_n
    event, event_share = dominant(event_counts)
    source, source_share = dominant(source_counts)
    component, component_share = dominant(component_counts)
    effective = (raw_n * raw_n / sum(count * count for count in event_counts.values())) if raw_n else 0.0
    return EvidenceConcentration(
        raw_n=raw_n, distinct_events=len(event_counts), distinct_dates=len(dates),
        distinct_pilots=len(pilots) if pilot_available else None,
        pilot_identity_available=pilot_available, effective_events=effective,
        max_event_id=event, max_event_share=event_share, max_source=source,
        max_source_share=source_share, max_component_id=component,
        max_component_share=component_share, event_counts=event_counts,
        source_counts=source_counts, component_counts=component_counts,
    )


def _view_rows(kind: str, rows: Sequence[object]) -> tuple[object, ...]:
    current_ids = {
        row.match.match_id for row in rows if row.view == "current-only"
    }
    if kind == "current-only":
        return tuple(row for row in rows if row.view == "current-only")
    if kind == "certified-expanded":
        return tuple(row for row in rows if row.view == "certified-expanded")
    return tuple(
        row for row in rows
        if row.view == "certified-expanded" and row.match.match_id not in current_ids
    )


def _view_local_prior(
    subject: str,
    opponent: str,
    observations: Sequence[object],
    hierarchy_rows: Sequence[object],
    *,
    camp_parent: Mapping[str, str],
) -> tuple[float, str, tuple[str, ...]]:
    """Build the normal matchup hierarchy after removing this cell's own physical rows.

    The caller supplies rows already restricted to one exact evidence view.  Match ids in the
    target cell are removed before either the subject marginal or a camp's leave-camp-out parent
    cell is assembled, making the prior independent of the observations it regularizes.
    """
    from legacy_engine.analytics.matchup import beta_binomial_shrink, beta_binomial_shrink_to

    observation_ids = {row.match.match_id for row in observations}
    eligible = tuple(
        row for row in hierarchy_rows if row.match.match_id not in observation_ids
    )
    subject_rows = tuple(row for row in eligible if row.match.subject == subject)
    parent = camp_parent.get(subject)
    if parent is None:
        wins = sum(row.match.subject_won for row in subject_rows)
        return (
            beta_binomial_shrink(wins, len(subject_rows)),
            "marginal (leave-cell-out)",
            tuple(sorted({row.match.match_id for row in subject_rows})),
        )

    siblings = {camp for camp, sibling_parent in camp_parent.items() if sibling_parent == parent}
    parent_rows = tuple(row for row in eligible if row.match.subject in siblings)
    parent_wins = sum(row.match.subject_won for row in parent_rows)
    parent_prior = beta_binomial_shrink(parent_wins, len(parent_rows))
    lco_rows = tuple(
        row for row in parent_rows
        if row.match.subject != subject and camp_parent.get(row.match.opponent, row.match.opponent) == opponent
    )
    if lco_rows:
        lco_wins = sum(row.match.subject_won for row in lco_rows)
        return (
            beta_binomial_shrink_to(
                lco_wins, len(lco_rows), prior_mean=parent_prior,
            ),
            "parent cell (leave-camp-out, leave-cell-out)",
            tuple(sorted({row.match.match_id for row in parent_rows})),
        )
    wins = sum(row.match.subject_won for row in subject_rows)
    return (
        beta_binomial_shrink(wins, len(subject_rows)),
        "marginal (leave-cell-out)",
        tuple(sorted({row.match.match_id for row in subject_rows})),
    )


def build_evidence_views(
    subject: str, opponent: str, rows: Sequence[object], *, clock: AnalysisClock,
    hierarchy_rows: Sequence[object] | None = None,
    camp_parent: Mapping[str, str] | None = None,
    prior_match_ids: Sequence[str] = (),
    reasons: Sequence[str] = (),
) -> MatchupEvidenceViews:
    """Build exact views and their leave-cell-out hierarchy from one selected-row ledger."""
    current = _view_rows("current-only", rows)
    expanded = _view_rows("certified-expanded", rows)
    current_ids = {row.match.match_id for row in current}
    expanded_ids = {row.match.match_id for row in expanded}
    if not current_ids <= expanded_ids:
        raise ValueError("current evidence must be a subset of expanded evidence")
    added = _view_rows("added-history", rows)
    if len({row.match.match_id for row in added}) != len(added):
        raise ValueError("added evidence contains duplicate match ids")
    external_prior_ids = tuple(prior_match_ids)
    hierarchy_corpus = tuple(hierarchy_rows if hierarchy_rows is not None else rows)
    camp_map = camp_parent or {}
    def view(kind: Literal["current-only", "certified-expanded", "added-history"], selected: Sequence[object], policy: Literal["pre-disturbance", "hierarchy-only"]) -> MatchupEvidenceView:
        ids = tuple(row.match.match_id for row in selected)
        external_overlap = len(set(ids) & set(external_prior_ids))
        if policy == "hierarchy-only" and external_overlap:
            raise ValueError("admitted observations overlap hierarchy prior")
        local_reasons = list(reasons)
        if not selected:
            local_reasons.append("zero-support")
        concentration = _concentration(selected)
        if concentration.max_event_share is not None and concentration.max_event_share >= 0.8:
            local_reasons.append("event-concentrated")
        status: Literal["available", "thin", "concentrated", "abstained"] = "available" if selected else "thin"
        if concentration.max_event_share is not None and concentration.max_event_share >= 0.8:
            status = "concentrated"
        from legacy_engine.analytics.matchup import build_cell
        wins = sum(1 for row in selected if row.match.subject_won)
        local_hierarchy = _view_rows(kind, hierarchy_corpus)
        local_prior, prior_source, local_prior_ids = _view_local_prior(
            subject, opponent, selected, local_hierarchy, camp_parent=camp_map,
        )
        overlap = len(set(ids) & set(local_prior_ids))
        if overlap:
            raise ValueError("admitted observations overlap view-local hierarchy prior")
        view_cell = build_cell(
            subject, opponent, wins, len(selected),
            prior_mean=local_prior,
            prior_source=prior_source,
        )
        return MatchupEvidenceView(kind=kind, cell=view_cell, match_ids=ids, pair_component_ids=tuple(row.pair_component_id for row in selected), certificate_ids=tuple(sorted({certificate for row in selected for certificate in (*row.subject_certificate_ids, *row.opponent_certificate_ids)})), concentration=concentration, prior=PriorEvidenceAudit(policy=policy, observation_match_ids_sha256=_digest_ids(ids), prior_match_ids_sha256=_digest_ids(local_prior_ids) if local_prior_ids else None, prior_match_ids=local_prior_ids, prior_mean=local_prior, prior_source=prior_source, overlap_n=overlap, reason="; ".join(local_reasons) if local_reasons else "exact selected evidence"), status=status, reasons=tuple(dict.fromkeys(local_reasons)))
    return MatchupEvidenceViews(subject=subject, opponent=opponent, clock=clock, current_only=view("current-only", current, "hierarchy-only"), certified_expanded=view("certified-expanded", expanded, "hierarchy-only"), added_history=view("added-history", added, "hierarchy-only"))


def resolve_field_era(
    con: duckdb.DuckDBPyConnection,
    *,
    provenance: str | None = None,
    min_share: float = _FIELD_MIN_SHARE_DEFAULT,
) -> tuple[str | None, str]:
    """The global field-era boundary: ``max(current ban-regime start, latest accepted boundary
    among PARENT entities holding >= min_share full-corpus field share)``.

    Self-healing: when the resulting ``[field_since, now)`` window has fewer than
    ``_FIELD_THIN_DECKS_FLOOR`` decks, degrades back to the ban-regime start with a labeled
    banner rather than trust a thin detection-derived window (epic self-heal gate).

    "Parent" entities only (``entity_eras`` rows where ``parent == entity``) — field share is a
    metagame-slice concept, not a sub-camp one; folding camps in would double-count their
    parent's share. One cheap deck-count query for the share proxy (``provenance`` is NOT
    threaded through it deliberately — the field-era boundary is a global, corpus-wide gate, not
    a per-basis one; every other regime-windowed surface in this feature keeps ``provenance`` as
    a matrix/window-level filter, not a field-share one).
    """
    from legacy_engine.analytics.trends import resolve_regime

    ban_since, _ban_until = resolve_regime("current")

    stored = read_entity_eras(con)
    parent_rows = {e.entity: e for e in stored.values() if e.parent == e.entity}
    if not parent_rows:
        return ban_since, "ban regime (no era data)"

    names = sorted(parent_rows)
    placeholders = ",".join("?" for _ in names)
    total_row = con.execute("SELECT count(*) FROM decks WHERE archetype IS NOT NULL").fetchone()
    total = int(total_row[0]) if total_row else 0
    if total <= 0:
        return ban_since, "ban regime (no deck data)"

    share_rows = con.execute(
        f"""
        SELECT archetype, count(*) FROM decks
        WHERE archetype IN ({placeholders})
        GROUP BY archetype
        """,  # noqa: S608 — placeholders are '?' marks, values bound below
        names,
    ).fetchall()
    share_by_entity = {a: n / total for a, n in share_rows}

    candidates = [
        e.stable_since for e in parent_rows.values()
        if e.stable_since is not None and share_by_entity.get(e.entity, 0.0) >= min_share
    ]
    if not candidates:
        return ban_since, "ban regime (no high-share disturbance)"

    latest_boundary = max(candidates)
    if latest_boundary <= (ban_since or ""):
        return ban_since, "ban regime (no boundary later than the ban regime start)"

    field_since = latest_boundary
    count_row = con.execute(
        """
        SELECT count(*) FROM decks dk JOIN tournaments t ON t.id = dk.tournament_id
        WHERE (? IS NULL OR t.date >= ?)
        """,
        [field_since, field_since],
    ).fetchone()
    n_decks = int(count_row[0]) if count_row else 0
    if n_decks < _FIELD_THIN_DECKS_FLOOR:
        return (
            ban_since,
            f"⚠ thin field window since {field_since} ({n_decks} decks < floor "
            f"{_FIELD_THIN_DECKS_FLOOR}) — degraded to ban regime",
        )

    return field_since, f"detection-derived (latest high-share boundary {latest_boundary})"
