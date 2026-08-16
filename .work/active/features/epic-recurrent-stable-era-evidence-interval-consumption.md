---
id: epic-recurrent-stable-era-evidence-interval-consumption
kind: feature
stage: done
tags: [analytics, advisory, testing]
parent: epic-recurrent-stable-era-evidence
depends_on: [epic-recurrent-stable-era-evidence-certification]
release_binding: null
gate_origin: null
created: 2026-08-16
updated: 2026-08-16
---

# Exact interval consumption and evidence decomposition

## Brief

Replace scalar-window eligibility at the analytical seam with normalized disjoint half-open interval
sets. Matchup evidence is admissible only inside the exact intersection of the subject and opponent
certificate sets, further bounded by explicit `data_until` and `knowledge_as_of` contracts. Excluded
gaps remain excluded throughout match scanning, matrix construction, parent/camp parity, and ranking
measurement.

Expose typed current-only, certified-expanded, and added-history views with certificate/component
provenance, event/source concentration, and effective support. Preserve the existing scalar
`stable_since` path as the explicit current-only/no-certificate adapter while retiring it as a
parallel interpretation. Prevent admitted historical observations from also entering a
pre-disturbance prior.

## Epic context

- Parent epic: `epic-recurrent-stable-era-evidence`
- Position in epic: shared evidence-selection seam consumed by amplification, reporting, and
  validation.

## Inherited design decisions

- Both matchup sides govern eligibility through exact interval intersection.
- Expanded evidence remains diagnostic and decomposed from direct current evidence.
- `data_until` and `knowledge_as_of` are independent clocks.
- Camps remain current-only until independently certified.

## Research briefs

- `.research/analysis/campaigns/recurrent-era-intervals/parent.md` — interval algebra and evidence
  view contract.
- `.research/analysis/campaigns/recurrent-era-intervals/specialists/consume-validate.md` — exact
  consumption, provenance, concentration, and temporal semantics.
- `docs/analysis/best-call-ranking.md` — current ranking ledger and honesty contract.

## Foundation references

- `docs/VISION.md` — compatible historical pockets with named provenance.
- `docs/SPEC.md` — current/expanded/added-history reporting.
- `docs/ARCHITECTURE.md` — single interval-set eligibility seam and matchup integration.

## Design decisions

- **One interval-set authority:** every analytical path obtains an `EntityEligibility` and derives
  pair eligibility through the same interval algebra. The existing `stable_since` resolution is an
  input adapter that emits exactly one current component; it is not a second window engine. Existing
  `PairWindow` fields remain a compatibility projection only when the resulting pair set is a single
  component and must never be used to reconstruct a disjoint set.
- **Atomic normalized components preserve provenance:** normalization uses a sweep over every
  endpoint, emits sorted non-empty non-overlapping half-open atoms, and retains the complete source
  tuple covering each atom. Adjacent atoms merge only when their source/provenance tuples are
  identical. It never bridges an excluded gap or discards a certificate boundary merely to create a
  wider scalar range.
- **Both sides are load-bearing:** a pair component exists only for an exact subject-component ×
  opponent-component overlap, further intersected with the caller's requested lower bound and the
  exclusive `data_until`. Each selected match names both entity components, both certificate ids
  when historical, and the derived pair-component id. One-sided admission is invalid input, not a
  fallback.
- **Two clocks answer different questions:** `data_until` is the exclusive upper bound on match
  outcomes. `knowledge_as_of` is the inclusive upper bound on certificate/configuration/fact
  artifacts allowed to select those outcomes. A retrospective current-model query may use knowledge
  acquired after `data_until`, but records that mode explicitly. An as-known-then query must prove
  artifact availability at or before `knowledge_as_of`; it never pretends today's certificate was
  known then.
- **Cross-item certification correction:** the certification design at `b0afc95` exposes
  `certification_as_of`, the source-evidence cutoff, but no separate artifact availability time.
  Certification implementation must add an immutable `knowledge_available_at` UTC timestamp to the
  durable exact-run envelope (or an equivalent persisted availability field with the same
  semantics). It is set once on first successful persistence and cannot move on an idempotent
  rewrite; it need not alter the evidence-content run id. Consumption validates it against
  `knowledge_as_of`. Until that contract exists,
  `as-known-then` returns typed `knowledge-provenance-unavailable`; only explicit
  `retrospective-current-model` use may consume the exact run. The consumer does not infer
  availability from row insertion time, file mtime, or `certification_as_of`.
- **Exact certificate run, never latest:** the request carries a concrete `certificate_run_id`.
  Only final `EraCertificate.status == "certified"` components from that exact validated run enter
  history. `rejected`, `inconclusive`, malformed, future-knowledge, profile-candidate, camp, or
  absent evidence contributes no historical atom and yields a named abstention reason. The current
  reference component is still added explicitly from `EntityCertificationResult`.
- **Camps stay current-only:** labels present in `camp_parent` are resolved through the scalar
  current adapter using their own/parent/ban horizon as today, but parent certificates are never
  consulted or copied. A future independent camp certificate needs an explicit contract revision;
  this feature does not infer it from naming or parent membership.
- **Three views form an exact partition:** `current_only` selects the pairwise intersection of the
  two current components; `certified_expanded` selects all certified pair components; and
  `added_history` is the exact match-id set difference `expanded - current`. Therefore current is a
  subset of expanded, current and added are disjoint, and their union equals expanded. Empty added
  history is a typed zero-support view, not a missing field or fabricated effect.
- **Concentration is first-class evidence:** each view reports W-L-n, distinct events, dates,
  available pilots, source composition, component composition, maximum event/source/component
  shares, pilot availability, and effective event support
  `(sum(n_event)^2 / sum(n_event^2))`. Raw `n` remains visible but never stands alone as evidence
  quality. Match records retain event ids rather than attempting to reconstruct them from aggregate
  counters.
- **Admitted history is direct evidence, never its own prior:** expanded and added-history cells use
  the normal hierarchy/weak-prior chain built from their selected corpus, but never call the
  pre-disturbance cross-era prior. A `PriorEvidenceAudit` records the observation and prior match-id
  digests and requires empty intersection. Current-only scalar behavior may retain the existing
  pre-disturbance prior because its pre-boundary rows are disjoint from current observations.
- **Diagnostic expansion cannot silently promote authority:** current-only remains the production
  ranking source for this feature. Expanded and added-history cells are additive typed diagnostics
  for later amplification/reporting features. Thin/concentrated/missing-provenance expansion remains
  present with an abstention/degrade reason and cannot replace current evidence by clearing a raw-n
  threshold.
- **Direct-read design:** local discovery/certification contracts, match extraction, matrix builders,
  ranking measurement, tests, foundation docs, and approved research resolved the design. No new UI
  is introduced, so mockups are not required.
- **Review policy:** effective review weight is `standard`. Child stories close on verification; the
  integrated feature receives one independent standard review.

## Architectural choice

Three integration shapes were considered. Issuing one SQL range query per certified interval would
exclude gaps correctly, but it would duplicate matches where components overlap, lose exact row
provenance during aggregation, and scale with cells × components. Querying one bounding range and
trusting aggregate subtraction would be faster to write, but a missing middle gap cannot be removed
from already-aggregated W-L counts. Keeping the scalar matrix as production authority and building a
separate interval matrix would invite inevitable selection and prior drift.

The chosen design adds one cardinality-safe resolved-match record scan bounded only by provenance,
the earliest needed lower bound, and `data_until`, then applies the pure normalized pair predicate to
each row before aggregation. Scalar fallback and certificates both compile into the same
`EntityEligibility`; current, expanded, and added views all derive from one selected-row ledger. The
existing aggregate API is reimplemented as an adapter over that ledger so there remains one join,
parse, ambiguity, split-label, mirror, and outcome path. This preserves the heavy-DB-once/pure-core
pattern while making gap exclusion and match-id disjointness directly testable.

The trickiest boundary is knowledge time: certification evidence time and artifact availability are
not interchangeable. The second is marginal/prior assembly: every hierarchical input must be
computed from the same view's rows, while any outcome rows used as direct expanded evidence are
forbidden from the pre-disturbance prior. Those invariants are represented in types and audits rather
than comments around an otherwise unconstrained aggregate.

## Implementation Units

### Unit 1: Normalized interval algebra and certificate adapter

**Files**: `src/legacy_engine/analytics/eras/consume.py`,
`src/legacy_engine/analytics/eras/certification_run.py`,
`tests/analytics/eras/test_interval_consumption.py`
**Story**: `epic-recurrent-stable-era-evidence-interval-algebra`

```python
from datetime import date, datetime
from typing import Literal

from legacy_engine.models.base import LegacyEngineModel

KnowledgeMode = Literal["retrospective-current-model", "as-known-then"]
EligibilitySource = Literal["current-reference", "certified-history", "scalar-current"]

class AnalysisClock(LegacyEngineModel):
    data_until: date                 # exclusive outcome bound
    knowledge_as_of: datetime        # inclusive artifact bound
    knowledge_mode: KnowledgeMode

class EligibilitySourceRef(LegacyEngineModel):
    source: EligibilitySource
    entity: str
    segment_id: str | None
    certificate_id: str | None
    certificate_run_id: str | None

class EligibilityAtom(LegacyEngineModel):
    component_id: str
    start: date | None               # None means -infinity for scalar fallback only
    end: date                        # always finite and exclusive
    sources: tuple[EligibilitySourceRef, ...]

class EntityEligibility(LegacyEngineModel):
    entity: str
    current: tuple[EligibilityAtom, ...]       # exactly one atom
    expanded: tuple[EligibilityAtom, ...]      # normalized current + certified history
    certificate_run_id: str | None
    clock: AnalysisClock
    status: Literal["certified-expanded", "current-only", "abstained"]
    reasons: tuple[str, ...]

def normalize_atoms(atoms: tuple[EligibilityAtom, ...]) -> tuple[EligibilityAtom, ...]: ...
def intersect_atoms(
    left: tuple[EligibilityAtom, ...],
    right: tuple[EligibilityAtom, ...],
) -> tuple[EligibilityAtom, ...]: ...
def build_entity_eligibility(
    con,
    entity: str,
    *,
    clock: AnalysisClock,
    certificate_run_id: str | None,
    requested_since: date | None = None,
    camp_parent: dict[str, str] | None = None,
    provenance: str | None = None,
) -> EntityEligibility: ...
```

**Implementation notes**:

- Reuse the certification feature's public `HalfOpenInterval`, `CertificationRun`,
  `EntityCertificationResult`, and exact-id reader; do not copy its models or parse ledger JSON in
  the consumer. Validate run/result/certificate entity identity, immutable ids, final status,
  promoted calibration authority, interval/reference ids,
  `certification_as_of <= knowledge_as_of.date()` for as-known-then source evidence, and
  `knowledge_available_at <= knowledge_as_of`.
- A retrospective query permits `data_until < certification_as_of` because it explicitly asks what
  today's model says about earlier outcomes; all intervals are still clipped at `data_until`.
  As-known-then refuses an unavailable/future artifact. Both modes persist both clocks and the exact
  run id in every downstream view.
- Add the current `reference_interval` exactly once, even when there are no certificates or all are
  refused. If the exact result/reference is unavailable, call existing `era_horizons` and compile
  its scalar `since` into `[since, data_until)` (or `[-infinity, data_until)`). Mark this
  `scalar-current`; do not mix scalar history with certified history.
- Camp detection uses explicit `camp_parent`, never string-prefix inference when a map exists. A camp
  always takes the scalar-current branch and emits `camp-current-only`, regardless of a parent run.
- Canonical ids hash entity, exact half-open bounds, ordered source refs, clock, and run id. Reject
  inverted/empty intervals, overlapping atoms with contradictory sources, duplicate certificate ids,
  mismatched reference intervals, and unknown enums. Open-ended starts are allowed only for
  `scalar-current`; certificate intervals are finite.

**Acceptance criteria**:

- [ ] Unsorted, overlapping, nested, and repeated inputs normalize deterministically into sorted,
  disjoint atoms; adjacent equal-provenance atoms merge, while distinct provenance boundaries and
  every positive gap remain exact.
- [ ] Intersection is commutative in geometry, clips to the exclusive `data_until`, retains both
  ordered source identities, and never turns `[a,b) U [c,d)` with `b < c` into `[a,d)`.
- [ ] Only final promoted `certified` components from the requested exact run expand history; every
  refusal/abstention names its reason while preserving one current component.
- [ ] As-known-then rejects absent/future knowledge availability; retrospective mode records its
  later-knowledge use without moving `data_until`.
- [ ] Camps never inherit a parent certificate. Missing certification produces the same scalar
  current interval as today's `era_horizons`, through the common interval-set authority.

### Unit 2: Match-record selection and gap-proof provenance

**Files**: `src/legacy_engine/analytics/match_results.py`,
`src/legacy_engine/analytics/eras/consume.py`,
`tests/test_match_results.py`, `tests/analytics/eras/test_interval_consumption.py`
**Story**: `epic-recurrent-stable-era-evidence-interval-selection`

```python
from typing import Literal

class ResolvedMatch(LegacyEngineModel):
    match_id: str                    # canonical event + pairing identity
    event_id: str
    event_date: date
    provenance: str
    subject: str
    opponent: str
    subject_player_id: str | None
    opponent_player_id: str | None
    subject_won: bool
    mirror: bool

class PairEligibility(LegacyEngineModel):
    subject: str
    opponent: str
    current: tuple[EligibilityAtom, ...]
    expanded: tuple[EligibilityAtom, ...]
    clock: AnalysisClock

class SelectedMatch(LegacyEngineModel):
    match: ResolvedMatch
    view: Literal["current-only", "certified-expanded"]
    pair_component_id: str
    subject_component_id: str
    opponent_component_id: str
    subject_certificate_ids: tuple[str, ...]
    opponent_certificate_ids: tuple[str, ...]

def resolve_match_records(...) -> tuple[ResolvedMatch, ...]: ...
def intersect_pair_eligibility(
    subject: EntityEligibility,
    opponent: EntityEligibility,
) -> PairEligibility: ...
def select_pair_matches(
    records: tuple[ResolvedMatch, ...],
    pair: PairEligibility,
) -> tuple[SelectedMatch, ...]: ...
def aggregate_match_records(records: tuple[ResolvedMatch, ...]) -> MatchResults: ...
```

**Implementation notes**:

- Extract the existing `_JOIN_SQL` outcome resolution into one record-producing function without
  changing cardinality guards, bye/draw/ambiguous/unmatched handling, directed symmetry, split
  labeling, mirrors, or provenance filtering. `compute_match_results` becomes an adapter that scans
  records, applies its half-open scalar request as one interval, and calls the shared aggregate.
- `match_id` is deterministic from the event id and stable round/pairing identity. If the rounds
  schema lacks a stable row key, include a canonical duplicate ordinal after sorting the complete
  pairing tuple; do not collapse legitimate repeat pairings and do not use iteration order.
- Pair intersection is performed separately for current and expanded sets. A row qualifies only when
  `event_date` is inside a derived pair atom and before `data_until`; boundary equality at an end is
  excluded. Binary search/sweep over normalized atoms is acceptable, but no bounding-range shortcut
  may skip the membership predicate.
- For parent-level opponents in the multi-split path, camp rows pool only after exact subject-camp ×
  parent-opponent eligibility has selected them. Pooling labels must not erase row/component ids.

**Acceptance criteria**:

- [ ] A row in a certified interval for only one side is excluded; a row in a shared gap is excluded;
  and an exact endpoint row follows `[start,end)` semantics.
- [ ] Every admitted row carries both sides' component/certificate provenance and one deterministic
  pair-component id; no match id appears twice within a view.
- [ ] Aggregate results over a one-component scalar interval are field-for-field equal to the current
  `compute_match_results(since, until)` contract, including camps, mirrors, coverage, and event/month
  counts.
- [ ] Reordering DB rows or interval inputs cannot change selected ids, W-L-n, or provenance; a
  duplicate real pairing remains distinct through its canonical ordinal.
- [ ] `data_until` reaches the SQL scan and the pure predicate, while `knowledge_as_of` affects only
  eligibility authority and never filters outcomes by accident.

### Unit 3: Typed evidence views, concentration, and prior isolation

**Files**: `src/legacy_engine/analytics/eras/consume.py`,
`src/legacy_engine/analytics/matchup.py`, `src/legacy_engine/models/matchup.py`,
`tests/analytics/eras/test_interval_evidence_views.py`, `tests/test_matchup.py`
**Story**: `epic-recurrent-stable-era-evidence-view-decomposition`

```python
class EvidenceConcentration(LegacyEngineModel):
    raw_n: int
    distinct_events: int
    distinct_dates: int
    distinct_pilots: int | None
    pilot_identity_available: bool
    effective_events: float
    max_event_id: str | None
    max_event_share: float | None
    max_source: str | None
    max_source_share: float | None
    max_component_id: str | None
    max_component_share: float | None
    event_counts: dict[str, int]
    source_counts: dict[str, int]
    component_counts: dict[str, int]

class PriorEvidenceAudit(LegacyEngineModel):
    policy: Literal["pre-disturbance", "hierarchy-only"]
    observation_match_ids_sha256: str
    prior_match_ids_sha256: str | None
    overlap_n: int
    reason: str

class MatchupEvidenceView(LegacyEngineModel):
    kind: Literal["current-only", "certified-expanded", "added-history"]
    cell: MatchupCell
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
```

**Implementation notes**:

- Construct added history from match-id set difference, then assert the exact subset/disjoint-union
  laws before computing any rate. Its W-L-n and estimate come from those rows, not by subtracting
  rounded probabilities or posterior parameters.
- Reuse `build_cell` for all three views with the same weak/hierarchical prior family. Expanded and
  added-history force `hierarchy-only`; current-only retains today's thin-cell cross-era behavior
  only when its observation and pre-disturbance match-id sets are provably disjoint. Any overlap is a
  hard invariant failure, never a warning or deduplication after estimation.
- Compute hierarchy marginals and camp leave-one-out inputs from the exact selected view. Do not feed
  full-corpus/current marginals into an expanded cell or expanded rows back into a current cell.
  Structural/superarchetype borrowing stays separately labeled and must pass the same no-overlap
  audit when it carries outcome rows.
- Concentration uses decisive match records. Effective events is zero for no rows; single-event
  support is one regardless of match duplication. Pilot counts are nullable and carry an explicit
  availability flag rather than treating missing identity as zero pilots.
- `available/thin/concentrated/abstained` does not hide numeric diagnostics. Floors/caps are supplied
  by the later amplification profile; this unit emits the facts and conservative built-in integrity
  abstentions (missing provenance, invalid certificate, clock mismatch).

**Acceptance criteria**:

- [ ] `current_ids` is a subset of `expanded_ids`, `added_ids` is exactly their difference, all three
  W-L-n tallies agree with their ids, and `current + added == expanded` at the raw-count level.
- [ ] A one-event duplication raises raw n without raising effective-event support; dominant event,
  source, and component shares identify the exact cluster, including unavailable pilot identity.
- [ ] Expanded/admitted historical rows never appear in a pre-disturbance prior. A deliberate overlap
  fixture fails before cell construction and records no apparently valid estimate.
- [ ] Current-only no-certificate results and priors remain numerically compatible with the scalar
  baseline, while expanded/added results use their own exact hierarchy inputs.
- [ ] Empty added history is a typed n=0 view with reasons and provenance, not `None`; thin or
  concentrated history cannot silently promote an expanded estimate to current authority.

### Unit 4: Adaptive matrix and ranking-ledger consumption

**Files**: `src/legacy_engine/analytics/matchup.py`,
`src/legacy_engine/advisory/ranking_measurement.py`,
`tests/test_matchup_multi_split.py`, `tests/test_ranking_measurement.py`,
`tests/analytics/eras/test_interval_matrix_integration.py`
**Story**: `epic-recurrent-stable-era-evidence-matrix-consumption`

```python
class IntervalAdaptiveMatrix(LegacyEngineModel):
    current: AdaptiveMatrix
    evidence: dict[tuple[str, str], MatchupEvidenceViews]
    clock: AnalysisClock
    certificate_run_id: str | None
    audit_preamble: tuple[str, ...]

class RankingEvidenceSource(LegacyEngineModel):
    kind: Literal["current-only", "certified-expanded", "added-history"]
    view: MatchupEvidenceView
    authoritative: bool

def build_interval_adaptive_matrix(
    con,
    *,
    clock: AnalysisClock,
    certificate_run_id: str | None = None,
    provenance: str | None = None,
    requested_since: date | None = None,
    split_variant: str | None = None,
    split_variants: tuple[str, ...] | None = None,
    **existing_matrix_options,
) -> IntervalAdaptiveMatrix: ...
```

**Implementation notes**:

- Route `build_adaptive_matrix` and `build_adaptive_multi_split_matrix` through the interval builder.
  With no run id they project its current view back to the existing return types; no independent
  scalar scan remains. Preserve row-inclusion semantics unless a separately scoped product decision
  changes them.
- Parent matrices may expose expanded diagnostics. Every camp subject remains scalar current-only;
  parent-level opponent pooling intersects each actual opponent entity before pooling. Plain,
  single-split, and multi-split current views retain their existing parity invariants.
- Extend ranking measurement source metadata to carry both clocks, interval/component ids, evidence
  kind, certificate run/id provenance, concentration/effective support, and abstention reasons.
  Current-only remains `authoritative=True`; expanded/added are diagnostic inputs only and cannot be
  selected by the existing `n>=ground_n` fallback truth table.
- `PairWindow` and `since` serialization are available only as a lossy display projection for a
  single current component. Disjoint expanded sources serialize the complete interval list; callers
  requesting a scalar projection receive `None` plus `disjoint-intervals-not-scalar`, never the
  earliest start.

**Acceptance criteria**:

- [ ] No-certificate plain/single-split/multi-split matrices and ranking rows match the pre-feature
  current-only golden values while proving all paths used the interval authority.
- [ ] Certified parent expansion retains every middle gap through matrix, multi-split pooling, and
  ranking serialization; both sides and all component/certificate ids survive round-trip replay.
- [ ] Camp rows are current-only even when their parent expands, and single-split/multi-split current
  parity remains exact.
- [ ] Ranking replay distinguishes both clocks and all three evidence kinds; expanded raw n cannot
  clear a current measured/grounding gate or replace the authoritative current source.
- [ ] Scalar projection refuses disjoint expanded sets, and admitted-history/prior overlap is zero
  for every expanded matrix cell.

## Implementation order

1. `interval-algebra` — establish normalization, clocks, exact-run validation, and scalar adapter.
2. `interval-selection` — make resolved match ids and exact pair membership the sole aggregate seam.
3. `view-decomposition` — build the three auditable views, concentration, and no-double-count prior.
4. `matrix-consumption` — route adaptive/multi-split/ranking contracts through the shared authority.

## Testing

### Unit tests

- Table-driven interval fixtures cover open scalar starts, touching/overlapping/nested atoms,
  distinct-provenance adjacency, positive gaps, exact endpoints, clipping, and commutative geometry.
- Certificate fixtures cover exact-id reads, current-only results, every non-certified status,
  candidate versus promoted profiles, mismatched identities, future knowledge, retrospective mode,
  absent availability provenance, and parent/camp separation.
- Resolved-match fixtures cover duplicate pairings, mirrors, byes/draws, ambiguity, split labeling,
  source filters, deterministic ids, both-side intersection, and gap rows.
- Evidence fixtures prove exact match-set partition laws, W-L-n reconstruction, concentration and
  effective-event formulas, nullable pilot support, view-local hierarchy inputs, and empty prior
  overlap.

### Integration tests

- A file-backed DuckDB fixture contains two certified historical pockets separated by an outcome-rich
  excluded gap. The gap must not affect any expanded/additional cell, matrix, multi-split projection,
  concentration measure, or serialized ranking replay.
- Asymmetric fixtures certify only subject or opponent history and prove no row widens until both
  interval sets overlap. Boundary-date events prove the exclusive upper bound.
- No-certificate golden tests compare legacy aggregate/adaptive/multi-split/ranking values and audit
  projections; instrumentation proves the scalar adapter compiled into interval eligibility.
- Prior fixtures place the strongest historical signal in an admitted pocket and prove it contributes
  once as direct evidence, never again as the pre-disturbance anchor.
- Focused interval/matchup/ranking tests, the full era and matchup suites, Ruff, and compileall are
  required before the feature advances to review.

## Risks

- **Certification availability is underspecified:** `certification_as_of` cannot honestly answer when
  an artifact was knowable. **Fallback:** require the certification dependency to persist an
  immutable availability timestamp; abstain from as-known-then expansion until it does, while
  permitting explicitly labeled retrospective current-model analysis.
- **Record extraction can perturb mature aggregates:** moving from direct accumulation to a resolved
  row ledger touches ambiguity, mirror, camp, and coverage behavior. **Fallback:** make the legacy
  API an adapter and pin field-for-field scalar goldens before enabling certificates.
- **Disjoint sets can multiply pair atoms:** many subject/opponent components create a Cartesian
  overlap surface. **Fallback:** normalize once, use a linear two-pointer intersection and indexed
  membership, batch one bounded DB scan, and measure component counts before considering storage.
- **Hierarchy semantics can drift by view:** using convenient full-corpus marginals would contaminate
  expanded/current comparisons. **Fallback:** derive all hierarchy inputs from the exact view ledger
  and persist match-set digests in the prior audit.
- **Historical concentration can masquerade as support:** several matches from one event inflate raw
  n. **Fallback:** expose effective events and maximum event/source/component shares beside raw n;
  later amplification may abstain but may not erase the diagnostics.
- **Downstream scalar callers may silently widen gaps:** an earliest-start projection is tempting.
  **Fallback:** project only one-component current sets and make disjoint scalar requests explicitly
  unavailable.

## Other agent review

- Invoked because: exact temporal/provenance and prior-isolation contracts are consequential.
- Skipped/degraded: the active autopilot caller explicitly forbids nested agents and peeragent, so no
  design-time advisory pass was run. This is non-blocking under the advisory policy.
- Receiver judgment: approved research, foundation decisions, discovery contracts, and certification
  design support the exact-set architecture; the integrated standard feature review remains required.

## Implementation summary

Implemented the interval-consumption seam across four sequential checkpoints:

- `interval-algebra`: typed independent clocks, deterministic disjoint half-open atoms,
  provenance-preserving intersection, exact certification-run and immutable availability checks,
  and explicit scalar/camp current fallback.
- `interval-selection`: deterministic resolved match ids, exact pair membership, exclusive
  `data_until`, and selected-row component/certificate provenance.
- `view-decomposition`: current/expanded/added match-id partition, concentration/effective-event
  diagnostics, nullable pilot identity, and hierarchy-only prior overlap enforcement.
- `matrix-consumption`: current-authoritative interval wrapper, non-lossy scalar projection refusal
  for disjoint sets, and typed ranking evidence-source metadata.

## Verification evidence

- `PYTHONPATH=. .venv/bin/pytest -q tests/analytics/eras tests/test_match_results.py tests/test_matchup.py tests/test_matchup_multi_split.py tests/test_ranking_measurement.py` — 400 passed.
- `uv run ruff check src/legacy_engine/analytics/eras/consume.py src/legacy_engine/analytics/match_results.py src/legacy_engine/analytics/matchup.py src/legacy_engine/advisory/ranking_measurement.py` — passed.
- `PYTHONPATH=. .venv/bin/python -m compileall -q src/legacy_engine/analytics/eras src/legacy_engine/analytics/match_results.py src/legacy_engine/analytics/matchup.py src/legacy_engine/advisory/ranking_measurement.py` — passed.

## Simplifications/deviations

- Existing adaptive/multi-split internals remain the mature compatibility implementation behind the
  new interval wrapper; certificate-backed matrix population is exposed through the resolved-match
  and evidence-view seams for the next consumer integration. Current-only values remain unchanged.
- `uv.lock` was pre-existing dirty state and was intentionally not staged or modified.

## Review findings

- Effective weight: `standard`; one same-harness fresh-context independent pass reviewed frozen
  commit `7ab3ded` on 2026-08-16. Closure requires verification of the named fix set only, not a
  second independent pass.
- Blocker story: `epic-recurrent-stable-era-evidence-interval-consumption-review-corrections`.
- Required corrections: replace the parallel scalar wrapper with real interval-driven production
  consumption; filter and orient exact requested pairs; preserve interval-level component identity;
  repair open-start normalization; let the exact certificate govern the current component; compute
  three independently aggregated views; and add adversarial integration/parity tests that exercise
  every new public contract.
- Important findings absorbed into the current-cycle correction set: stable outcome-independent
  match identity, explicit scalar-projection refusal provenance, and package exports. Receiver
  judgment treats these as boundary integrity, not deferrable cleanup.
- Rejected: endpoint clock predicates are correct; current ranking authority was not silently
  promoted; supplied hierarchy-prior overlap checks catch current/added reuse. No foundation or
  applicable security finding was confirmed.

## Correction evidence

The named review correction is complete in `epic-recurrent-stable-era-evidence-interval-consumption-review-corrections`:
production interval-matrix calls now resolve exact directed rows and populate typed evidence,
component identity is interval-level, open-start provenance is isolated, and public interval APIs
are exported. Current matrix/ranking authority remains unchanged.

Correction verification additionally covers gap exclusion, stable component concentration, exact
match-id partition, and prior-overlap refusal in `tests/analytics/eras/test_interval_consumption.py`.
The follow-up correction validates certificate authority before current-reference adoption,
independently aggregates all three view cells, and returns populated parent/multi-split evidence.

Commit `339407b` closes the root verification gap recorded after `d968c19`. Exact-view
leave-cell-out hierarchy inputs now
exclude every target-cell match id and publish their audit ids/digest; the production wrapper passes
explicit camp parents, keeps camp pairs current-only, and returns a concrete typed evidence map plus
a canonical digest-bound selected-outcome ledger. Real DuckDB-backed tests exercise promoted exact
certificate reads, refusal modes, excluded gaps, reverse orientation, parent/camp/multi-split
parity, populated evidence, and typed scalar refusal. The feature is returned to `stage: review` for
root administrative verification under the existing one-review policy.

## Review (2026-08-16)

**Verdict**: Approve

**Blockers**: none
**Important**: none; stable match identity, typed scalar refusal, and exports were absorbed into the
named current-cycle correction.
**Nits**: none.
**Rejected**: endpoint clocks and unchanged current ranking authority were confirmed sound; no
foundation or applicable security issue was found.

**Notes**: Standard-weight deep feature review used one same-harness fresh-context pass over frozen
commit `7ab3ded`. The receiver rejected the parallel/dead integration and required the full named
correction set. After two insufficient handoffs, `339407b`/`a8852a6` completed the exact contract:
canonical digest-bound selected outcomes, one physical orientation, certificate-governed current
and history, real leave-cell-out view hierarchy, camp/multi-split parity, populated typed matrix
evidence, scalar refusal, and DB-backed adversarial tests. Root verification passed 239 focused and
relevant tests plus Ruff; the worker's broader era/ranking run passed 423 tests and compileall. Per
standard policy, no second independent pass was run. UI, auth/network, async, and deployed migration
lenses were inapplicable.
