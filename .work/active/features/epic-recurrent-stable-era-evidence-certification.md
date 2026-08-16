---
id: epic-recurrent-stable-era-evidence-certification
kind: feature
stage: implementing
tags: [analytics, testing]
parent: epic-recurrent-stable-era-evidence
depends_on: [epic-recurrent-stable-era-evidence-discovery]
release_binding: null
gate_origin: null
created: 2026-08-16
updated: 2026-08-16
---

# Independent equivalence certification and persistence

## Brief

Turn outcome-free recurrent candidates into versioned `certified`, `rejected`, or `inconclusive`
decisions through independent event partitions, positive practical-equivalence tests, semantic
affectedness vetoes, context/support/concentration guards, and family-wise error control. Persist
enough evidence and version identity to reproduce why each interval reunion was admitted or refused.

Certificates are derived analytical artifacts rebuilt automatically under a fixed configuration;
changing calibration, confirming format truth, or promoting methodology remains operator-controlled.
This feature does not consume matchup outcomes or publish expanded matchup estimates.

## Epic context

- Parent epic: `epic-recurrent-stable-era-evidence`
- Position in epic: decision boundary between candidate discovery and every evidence consumer.

## Inherited design decisions

- Nonsignificance is not equivalence; underpowered candidates remain inconclusive.
- Confirmed affectedness is a hard veto, while pending format-monitor candidates are not truth.
- Parent certificates never stand in for independently supported camp certificates.
- Calibration and certificate schemas are versioned, deterministic, and operator-promoted.

## Research briefs

- `.research/analysis/campaigns/recurrent-era-intervals/parent.md` — positive-equivalence burden and
  persistence contract.
- `.research/analysis/campaigns/recurrent-era-intervals/specialists/certify.md` — equivalence,
  multiplicity, support, and context guards.
- `.research/analysis/campaigns/recurrent-era-intervals/verification-checklist.md` — approved
  adversarial review.

## Foundation references

- `docs/SPEC.md` — versioned interval certification and honest abstention.
- `docs/ARCHITECTURE.md` — `EraCertificate` store and format-truth boundaries.
- `docs/PRINCIPLES.md` — confidence gating and live legality.

## Design decisions

- **Independent events are structural, not a promise:** certification v1 uses one deterministic
  hash partition over whole event ids. All decks from an event stay together. The discovery half
  alone is allowed to nominate candidates and the disjoint certification half alone is allowed to
  test them. The partition rule and both event-set digests are part of both run identities.
- **Cross-item correction:** the discovery implementation currently builds its persisted run from
  the full outcome-free corpus, despite the accepted research requiring independent event-level
  partitions. This feature corrects that seam in place by adding a partition manifest and a
  corpus-taking discovery composition function. Certification refuses any discovery run not marked
  `partition_role="discovery"` or whose source/event digests do not match the recomputed discovery
  half. Existing rows are rebuildable analytical cache, so no unsafe legacy/full-corpus
  compatibility path is retained.
- **One certificate per historical component:** each nominated historical segment is judged against
  the same current reference segment and receives its own certificate. The family-wise bootstrap
  covers every candidate/channel able to enter the run; passing one interval never lends certainty
  to another. Downstream consumers may admit only `certified` historical components.
- **Three-way interval semantics:** `certified` requires every simultaneous upper bound to fall
  strictly inside its prespecified margin and every guard to pass. `rejected` requires a confirmed
  semantic incompatibility or a simultaneous lower bound at/outside a margin. Bands that straddle a
  margin, thin/concentrated support, weak simulated power, unresolved format truth, or poor context
  overlap are `inconclusive`; non-significance never becomes equivalence.
- **Offensive but outcome-blind tests:** v1 uses interpretable board-separated/card-mixture/context
  discrepancy channels plus a fixed-bandwidth RBF MMD omnibus channel. A whole-event cluster
  bootstrap builds one simultaneous band over normalized discrepancies for strong family-wise
  control. Match/game wins, standings, conversion, ranking values, and downstream borrowing weights
  are absent from the source model and feature allowlist.
- **Context is an admission guard, not a repair:** reference-to-candidate ratios over the declared
  field/source context vocabulary expose effective support, maximum stabilized weight, and
  unsupported reference mass. Weighting is diagnostic only and can never rescue a semantic veto or
  produce the certificate estimate.
- **Pending monitor evidence is not confirmed truth:** only the curated B&R ledger and frozen
  taxonomy/legality/source-contract facts can create a hard rejection. A pending or unavailable
  format-monitor boundary crossed by a candidate makes the decision `inconclusive` with the
  observation digest and reason; it is never promoted to a fact inside certification.
- **Calibration authority stays explicit:** every margin, support floor, concentration cap, kernel
  parameter, power scenario, alpha, bootstrap count, and partition rule lives in a checked-in
  closed-schema profile. A `candidate` profile computes and persists diagnostics but caps the final
  status at `inconclusive`; only an operator-promoted profile may emit `certified`. No candidate-
  specific observed distance or outcome may tune the profile.
- **Current reference remains visible:** every discovery entity yields an
  `EntityCertificationResult`, including no-recurrence/degraded entities. Missing candidates are
  explicit current-only results rather than missing rows; camps remain structurally absent.
- **Direct-read design:** the feature is bounded to the shipped discovery contracts,
  `analytics/eras/`, curated ban/format facts, and mirrored era tests. Local inspection resolved the
  interface questions without exploratory fan-out.
- **No UI surface:** this feature emits typed analytical artifacts only. Reporting belongs to the
  later Best Call integration feature, so no mockup is required.
- **Review policy:** effective review weight is `standard` from the caller/project default. Child
  stories close on verification; the integrated feature receives one independent standard review.

## Architectural choice

Three shapes were considered. Reusing discovery fingerprints/distances as proof would be small, but
it would test on the same selected events and turn nomination thresholds into equivalence margins.
Keeping the full corpus and attempting simultaneous post-selection inference could preserve more
data, but no validated clustered deck-distribution method is available in the approved research.
An opaque recurrent latent-state model could combine selection and certification, but would weaken
auditability and is already reserved as a future challenger.

The chosen design is a deterministic whole-event sample split, followed by an ordered pure gate
pipeline and one simultaneous whole-family bootstrap over the untouched certification events. It
spends data and will abstain often, but every admitted interval has a legible proof path: exact
partition, hard facts, support/concentration, component and omnibus bands, context overlap, and a
versioned calibration. The immutable run/store mirrors discovery's content-addressed ledger and
requires exact-id reads; there is no `latest` selector that could silently move downstream evidence.

The trickiest unit is the partitioned handoff. Statistical machinery cannot recover validity if a
candidate was nominated with even one certification event, so Unit 1 repairs and adversarially tests
that boundary before any gate or bootstrap code is written. The second-most consequential unit is
the normalized simultaneous band: all discrepancies are divided by their prespecified margins
before the bootstrap maximum is taken, preventing channels with larger raw units from dominating
family-wise control.

## Implementation Units

### Unit 1: Deterministic event partition and certification corpus

**Files**: `src/legacy_engine/analytics/eras/discovery_run.py`,
`src/legacy_engine/analytics/eras/certification.py`,
`src/legacy_engine/analytics/eras/certification_source.py`,
`src/legacy_engine/config.py`, `src/legacy_engine/data/eras/certification-v1.json`,
`tests/analytics/eras/test_certification_source.py`,
`tests/analytics/eras/test_discovery_run.py`
**Story**: `epic-recurrent-stable-era-evidence-certification-partition-contract`

```python
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import Literal

import duckdb

from legacy_engine.analytics.eras.discovery import (
    DiscoveryBoundary,
    DiscoveryCalibration,
    OutcomeFreeCorpus,
    OutcomeFreeModel,
)
from legacy_engine.analytics.eras.discovery_run import DiscoveryRun

PartitionRole = Literal["discovery", "certification"]
ProfileState = Literal["candidate", "promoted"]

class EventPartitionPlan(OutcomeFreeModel):
    plan_id: str
    salt: str
    modulus: int
    discovery_buckets: tuple[int, ...]

class PartitionManifest(OutcomeFreeModel):
    plan_id: str
    rule_sha256: str
    discovery_event_ids_sha256: str
    certification_event_ids_sha256: str
    discovery_events: int
    certification_events: int

class EquivalenceMargins(OutcomeFreeModel):
    main_js: float
    side_js: float
    mixture_energy: float
    field_js: float
    source_js: float
    omnibus_mmd2: float

class CertificationCalibration(OutcomeFreeModel):
    profile_id: str
    profile_state: ProfileState
    method_id: Literal["cluster-bootstrap-equivalence-v1"]
    feature_schema_version: Literal["recurrent-certification-features-v1"]
    control_evidence_sha256: str
    partition: EventPartitionPlan
    family_alpha: float
    bootstrap_replicates: int
    power_replicates: int
    safely_inside_ratio: float
    target_power: float
    min_candidate_events: int
    min_reference_events: int
    min_time_buckets: int
    min_effective_events: float
    max_event_share: float
    max_source_share: float
    max_context_weight: float
    max_unsupported_context_share: float
    context_smoothing: float
    rbf_bandwidth: float
    margins: EquivalenceMargins

class PartitionedOutcomeFreeCorpus(OutcomeFreeModel):
    manifest: PartitionManifest
    discovery: OutcomeFreeCorpus
    certification: OutcomeFreeCorpus

def load_certification_calibration(path: Path | str) -> CertificationCalibration: ...
def partition_role(event_id: str, plan: EventPartitionPlan) -> PartitionRole: ...
def partition_outcome_free_corpus(
    corpus: OutcomeFreeCorpus,
    plan: EventPartitionPlan,
) -> PartitionedOutcomeFreeCorpus: ...
def run_discovery_corpus(
    corpus: OutcomeFreeCorpus,
    calibration: DiscoveryCalibration,
    *,
    partition: PartitionManifest,
    seed: int = 0,
) -> DiscoveryRun: ...
def load_certification_corpus(
    con: duckdb.DuckDBPyConnection,
    *,
    discovery_run: DiscoveryRun,
    calibration: CertificationCalibration,
    as_of: date,
    taxonomy_version: str,
    legality_version: str,
    semantic_boundaries: Sequence[DiscoveryBoundary] = (),
    provenance: str | None = None,
) -> tuple[OutcomeFreeCorpus, PartitionManifest]: ...
```

**Implementation notes**:

- `partition_role` hashes canonical `(plan_id, salt, event_id)` bytes and maps the integer digest
  modulo `modulus`; `discovery_buckets` is a non-empty proper subset. All decks sharing `event_id`
  are atomic. The profile loader rejects empty roles, invalid ratios, non-finite values, unknown
  keys/tokens, and any profile whose control-evidence digest is absent.
- `partition_outcome_free_corpus` creates two independently hashed corpora without changing cutoff,
  taxonomy, legality, provenance, or semantic facts. Its manifest proves disjoint event ids and
  exact union of the full cutoff corpus.
- Refactor discovery composition so `run_discovery_corpus` owns pure result/manifest construction
  and the DB wrapper loads then partitions before calling it. Extend `DiscoveryManifest` in place
  with `partition_role`, `partition_plan_id`, `partition_rule_sha256`, and
  `partition_event_ids_sha256`; only `partition_role="discovery"` is certifiable.
- `load_certification_corpus` rebuilds the full outcome-free cutoff corpus, recomputes the partition,
  and verifies discovery source/event/partition/result hashes and exact `as_of`/taxonomy/legality/
  provenance identity. A mismatch raises with the field named; it never falls back to all events.
- The certification source adapter may query only the same outcome-free tables as discovery. It
  receives the exact discovery run id, never a `latest` run, and returns no connection to the pure
  core.

**Acceptance criteria**:

- [ ] Every event and all its decks land in exactly one role; roles are disjoint, their union is the
  cutoff corpus, and the same plan/corpus is byte-deterministic across input order and process runs.
- [ ] Candidate nomination changes when discovery-role features change but is invariant to any
  certification-role feature mutation; the reverse corpus remains unavailable to discovery.
- [ ] Certification-role features may change certification evidence but cannot change the persisted
  discovery run id/candidate ids.
- [ ] A full-corpus/legacy run, wrong partition plan, event overlap, digest mismatch, post-cutoff row,
  taxonomy/legality drift, or outcome-bearing extra fails before a certificate is evaluated.
- [ ] Match results, standings, conversion, and ranking relations may be dropped or permuted without
  changing either partition, discovery run, or certification corpus.

### Unit 2: Ordered semantic, support, concentration, and context guards

**Files**: `src/legacy_engine/analytics/eras/certification.py`,
`src/legacy_engine/analytics/eras/certification_source.py`,
`tests/analytics/eras/conftest.py`, `tests/analytics/eras/test_certification.py`
**Story**: `epic-recurrent-stable-era-evidence-certification-guards-support`

```python
from collections.abc import Sequence
from datetime import date
from typing import Literal

from legacy_engine.analytics.eras.discovery import DiscoveryDeck

GateDisposition = Literal["pass", "reject", "abstain"]
CertificationStatus = Literal["certified", "rejected", "inconclusive"]
CertificationReason = Literal[
    "unpromoted-calibration",
    "confirmed-affectedness",
    "legality-incompatible",
    "taxonomy-incompatible",
    "source-contract-incompatible",
    "pending-format-truth",
    "format-truth-unavailable",
    "insufficient-candidate-events",
    "insufficient-reference-events",
    "insufficient-time-buckets",
    "effective-support-below-floor",
    "event-concentration",
    "source-concentration",
    "power-below-target",
    "context-overlap-failed",
    "equivalence-straddles-margin",
    "component-non-equivalent",
    "omnibus-non-equivalent",
]
SemanticFactState = Literal["confirmed", "pending", "unavailable"]
SemanticFactKind = Literal["affectedness", "legality", "taxonomy", "source-contract"]

class HalfOpenInterval(OutcomeFreeModel):
    start: date
    end: date  # exclusive

class SemanticFact(OutcomeFreeModel):
    fact_id: str
    kind: SemanticFactKind
    state: SemanticFactState
    effective_on: date
    affected_entities: tuple[str, ...]
    source: Literal["curated-ban-ledger", "frozen-contract", "format-monitor"]
    evidence_sha256: str
    detail: str

class CandidateCertificationInput(OutcomeFreeModel):
    entity: str
    candidate_id: str
    historical_segment_id: str
    reference_segment_id: str
    historical_interval: HalfOpenInterval
    reference_interval: HalfOpenInterval
    candidate_decks: tuple[DiscoveryDeck, ...]
    reference_decks: tuple[DiscoveryDeck, ...]
    candidate_context_decks: tuple[DiscoveryDeck, ...]
    reference_context_decks: tuple[DiscoveryDeck, ...]

class SemanticGuardEvidence(OutcomeFreeModel):
    disposition: GateDisposition
    crossed_fact_ids: tuple[str, ...]
    confirmed_veto_ids: tuple[str, ...]
    unresolved_fact_ids: tuple[str, ...]
    reasons: tuple[CertificationReason, ...]

class SupportEvidence(OutcomeFreeModel):
    disposition: GateDisposition
    candidate_decks: int
    reference_decks: int
    candidate_events: int
    reference_events: int
    time_buckets: int
    effective_events: float
    max_event_share: float | None
    max_source_share: float | None
    simulated_power: float | None
    reasons: tuple[CertificationReason, ...]

class ContextOverlapEvidence(OutcomeFreeModel):
    disposition: GateDisposition
    effective_events: float | None
    max_stabilized_weight: float | None
    unsupported_reference_share: float | None
    vocabulary_sha256: str
    reasons: tuple[CertificationReason, ...]

def build_candidate_inputs(
    discovery_run: DiscoveryRun,
    corpus: OutcomeFreeCorpus,
) -> tuple[CandidateCertificationInput, ...]: ...
def evaluate_semantic_guards(
    candidate: CandidateCertificationInput,
    facts: Sequence[SemanticFact],
) -> SemanticGuardEvidence: ...
def evaluate_support(
    candidate: CandidateCertificationInput,
    calibration: CertificationCalibration,
    *,
    seed: int,
) -> SupportEvidence: ...
def evaluate_context_overlap(
    candidate: CandidateCertificationInput,
    calibration: CertificationCalibration,
) -> ContextOverlapEvidence: ...
```

**Implementation notes**:

- `build_candidate_inputs` emits one item for every historical segment in every persisted candidate
  group, using only certification-role decks inside the exact half-open segment/reference bounds.
  It validates entity/segment/candidate ids against the immutable discovery result instead of
  recreating nomination.
- Build confirmed affectedness facts from the curated `BAN_EVENTS` ledger plus the entity's
  outcome-free pre-boundary inclusion evidence. Frozen hard taxonomy/legality/source-contract epochs
  are rechecked independently. Only confirmed facts can reject; crossed pending/unavailable monitor
  facts abstain and their digest stays visible.
- Guard order is semantic → support/concentration/power → context overlap → equivalence. A reject or
  abstention remains in the run and suppresses later magnitudes where they would imply false
  precision. The family candidate itself remains frozen for multiplicity accounting.
- Effective event support uses concentration weights over whole events, never raw deck count.
  Simulated power resamples whole events under the profile's declared safely-inside alternatives;
  a missing/failed power result is an abstention, not zero power and not a pass.
- Context ratios are computed over the closed field-parent/source vocabulary from certification
  events with profile smoothing. Record `(sum w)^2 / sum(w^2)`, maximum stabilized weight, and
  reference mass whose candidate support is below the profile floor. Ratios are never applied to
  deck/configuration discrepancies.

**Acceptance criteria**:

- [ ] A confirmed subject-affecting boundary or incompatible hard contract deterministically
  rejects the affected interval, while the same boundary does not blanket-reset a confirmed-
  unaffected entity.
- [ ] Pending/unavailable monitor evidence produces `inconclusive` evidence and never appears in
  `confirmed_veto_ids`; later confirmation changes the semantic digest/run identity.
- [ ] Event duplication cannot buy support: raw deck count may rise while effective events and the
  concentration decision stay unchanged or worsen.
- [ ] Thin candidate/reference events, too few buckets, excessive event/source concentration, and
  low simulated power each abstain with a distinct reason and no fabricated numeric pass.
- [ ] Poor field/source support yields an auditable context abstention with effective support,
  maximum weight, and unsupported share; weighting cannot override any prior guard.
- [ ] No camp label can enter `CandidateCertificationInput`, and every no-candidate/degraded parent
  remains representable in the eventual run.

### Unit 3: Positive equivalence and whole-family error control

**Files**: `src/legacy_engine/analytics/eras/certification.py`,
`tests/analytics/eras/test_certification.py`,
`tests/analytics/eras/test_certification_controls.py`,
`tests/fixtures/eras/certification-controls-v1.json`
**Story**: `epic-recurrent-stable-era-evidence-certification-family-equivalence`

```python
from collections.abc import Sequence

EquivalenceChannel = Literal[
    "main-js", "side-js", "mixture-energy", "field-js", "source-js", "omnibus-mmd2"
]

class EquivalenceBand(OutcomeFreeModel):
    channel: EquivalenceChannel
    estimate: float
    margin: float
    normalized_estimate: float
    simultaneous_lower: float
    simultaneous_upper: float
    disposition: GateDisposition

class EquivalenceEvidence(OutcomeFreeModel):
    disposition: GateDisposition
    family_id: str
    method_id: str
    family_alpha: float
    bootstrap_replicates: int
    critical_value: float
    channels: tuple[EquivalenceBand, ...]
    reasons: tuple[CertificationReason, ...]

class CandidateDecision(OutcomeFreeModel):
    candidate: CandidateCertificationInput
    semantic: SemanticGuardEvidence
    support: SupportEvidence
    context_overlap: ContextOverlapEvidence
    equivalence: EquivalenceEvidence | None
    statistical_status: CertificationStatus
    final_status: CertificationStatus
    reasons: tuple[CertificationReason, ...]

def estimate_candidate_discrepancies(
    candidate: CandidateCertificationInput,
    calibration: CertificationCalibration,
) -> dict[EquivalenceChannel, float]: ...
def certify_candidate_family(
    candidates: Sequence[CandidateCertificationInput],
    facts: Sequence[SemanticFact],
    calibration: CertificationCalibration,
    *,
    seed: int = 0,
) -> tuple[CandidateDecision, ...]: ...
```

**Implementation notes**:

- Main/side Jensen-Shannon, deck-mixture energy, field/source Jensen-Shannon, and fixed-bandwidth
  Gaussian MMD² are recomputed from certification-role samples. Reusing discovery distances or
  discovery thresholds is prohibited. The vocabulary/kernel/profile hashes are persisted.
- For every testable candidate/channel compute `z = discrepancy / margin`. Each bootstrap replicate
  resamples whole events independently within historical/reference segments, recomputes all `z`,
  and contributes the maximum absolute centered deviation across the frozen run family. The
  `(1 - family_alpha)` quantile is one shared critical value; simultaneous bounds are
  `max(0, z-q)` and `z+q`.
- A candidate is statistically `certified` only when every upper bound is `< 1`; it is `rejected`
  when at least one lower bound is `>= 1` (component and omnibus reasons remain distinct); otherwise
  it is `inconclusive`. A semantic rejection wins, any abstaining prerequisite caps the result at
  inconclusive, and a candidate profile changes an otherwise-certified final status to
  `inconclusive/unpromoted-calibration` while preserving `statistical_status` for audit.
- The candidate family is frozen from the exact discovery results before any guard is evaluated.
  Guarded-out members stay listed in family evidence and cannot be removed adaptively to improve the
  critical value. Seeded `numpy.random.Generator` use must be order-independent via canonical ids.
- The checked-in controls include stable event-boundary splits, semantic/sideboard/mixture/context
  breaks, one-event duplication, and overlapping candidates. Profile evidence records the fixture
  digest and three-state confusion matrix; tests do not tune against matchup outcomes.

**Acceptance criteria**:

- [ ] A well-supported stable positive control certifies only when every simultaneous component and
  omnibus upper bound is inside its margin; ordinary equality-test non-rejection is never read.
- [ ] Main-equal/side-shift, equal-average/mixture-shift, context-shift, and semantic negative
  controls reject or abstain through the named channel rather than averaging into a pass.
- [ ] A confidence band crossing a margin is `inconclusive`; a lower bound outside is `rejected`;
  insufficient power remains `inconclusive` even when the point estimate is small.
- [ ] Adding another eligible candidate/component cannot narrow any existing simultaneous band, and
  candidate input ordering cannot change ids, critical values, bands, or decisions.
- [ ] Candidate profiles never emit final `certified`; promoting the identical profile changes run
  identity and authority without changing the recorded statistical evidence.
- [ ] Permuting/removing every outcome table or changing downstream matchup wins leaves the complete
  decision family byte-identical.

### Unit 4: Immutable certificate run and exact-id ledger

**Files**: `src/legacy_engine/analytics/eras/certification_run.py`,
`src/legacy_engine/analytics/eras/certificate_store.py`,
`src/legacy_engine/analytics/eras/__init__.py`,
`tests/analytics/eras/test_certification_run.py`,
`tests/analytics/eras/test_certificate_store.py`
**Story**: `epic-recurrent-stable-era-evidence-certification-certificate-ledger`

```python
from collections.abc import Sequence
from datetime import date

import duckdb

CertificationRunStatus = Literal["complete", "degraded"]
CertificationRunReason = Literal[
    "no-recurrent-candidates", "all-inconclusive", "format-truth-unresolved"
]

class EraCertificate(OutcomeFreeModel):
    certificate_id: str
    entity: str
    candidate_id: str
    historical_segment_id: str
    reference_segment_id: str
    historical_interval: HalfOpenInterval
    reference_interval: HalfOpenInterval
    certification_as_of: date
    discovery_run_id: str
    status: CertificationStatus
    reasons: tuple[CertificationReason, ...]
    feature_schema_version: str
    calibration_profile_id: str
    partition: PartitionManifest
    semantic: SemanticGuardEvidence
    support: SupportEvidence
    context_overlap: ContextOverlapEvidence
    equivalence: EquivalenceEvidence | None
    outcome_columns_accessed: tuple[()] = ()

class EntityCertificationResult(OutcomeFreeModel):
    entity: str
    reference_segment_id: str | None
    reference_interval: HalfOpenInterval | None
    discovery_status: DiscoveryStatus
    candidate_id: str | None
    certificates: tuple[EraCertificate, ...]
    reasons: tuple[str, ...]

class CertificationManifest(OutcomeFreeModel):
    discovery_run_id: str
    discovery_results_sha256: str
    certification_as_of: date
    certification_source_sha256: str
    feature_schema_version: str
    calibration_profile_id: str
    calibration_sha256: str
    partition_sha256: str
    semantic_facts_sha256: str
    format_observation_sha256: str | None
    outcome_feature_allowlist: tuple[str, ...]
    seed: int

class CertificationRun(OutcomeFreeModel):
    run_id: str
    manifest: CertificationManifest
    results_sha256: str
    status: CertificationRunStatus
    reasons: tuple[CertificationRunReason, ...]
    results: tuple[EntityCertificationResult, ...]

def run_recurrent_certification(
    con: duckdb.DuckDBPyConnection,
    *,
    discovery_run_id: str,
    calibration: CertificationCalibration,
    semantic_facts: Sequence[SemanticFact],
    format_observation_sha256: str | None,
    seed: int = 0,
) -> CertificationRun: ...
def init_certificate_schema(con: duckdb.DuckDBPyConnection) -> None: ...
def write_certification_run(con: duckdb.DuckDBPyConnection, run: CertificationRun) -> None: ...
def read_certification_run(
    con: duckdb.DuckDBPyConnection,
    run_id: str,
) -> CertificationRun | None: ...
def certification_run_ids(
    con: duckdb.DuckDBPyConnection,
    *,
    as_of: date | None = None,
) -> tuple[str, ...]: ...
```

**Implementation notes**:

- Compose exact-id discovery read → recomputed certification corpus/partition → semantic snapshot →
  frozen candidate family → ordered gates/equivalence once. `run_id` hashes the manifest and each
  certificate id hashes run/candidate/status/evidence. Canonical order is entity, historical start,
  segment id.
- Persist one canonical `era_certification_runs` JSON ledger row per content-addressed run. The
  DuckDB table is a rebuildable derived cache over corpus, checked-in calibration, curated facts,
  and monitor observation. Same-id/same-bytes retries are idempotent; any divergent collision or
  hash/schema drift fails before overwrite.
- `EntityCertificationResult` is emitted for every discovery result. `no-recurrence` and `degraded`
  results contain the exact current reference evidence/reasons and zero certificates rather than
  disappearing. Only `EraCertificate.status == "certified"` is an admissible downstream historical
  interval; downstream must still add the current reference and intersect both matchup sides.
- `outcome_feature_allowlist` is one module-level sorted tuple of deck/configuration, event/context,
  semantic, and version paths. It cannot be caller-extended, and `outcome_columns_accessed` validates
  to the empty tuple. No `latest` or status-filtered convenience read is exported.

**Acceptance criteria**:

- [ ] One run round-trips every partition, guard, band, support/context diagnostic, status, reason,
  feature/config/fact digest, and explicit no-candidate entity with canonical hash validation.
- [ ] Exact reruns are idempotent; same-id byte divergence, malformed JSON, hash mismatch, unknown
  token, or non-empty `outcome_columns_accessed` fails loudly and preserves the first row.
- [ ] Multiple cutoffs/profiles/discovery runs coexist and are readable only by exact id; absent
  table/run returns an honest `None`/empty tuple without choosing a substitute.
- [ ] A downstream fixture attempting to consume `rejected`, `inconclusive`, parent-as-camp, or an
  uncertified gap receives no admissible historical component.
- [ ] Outcome mutation/removal, result-table absence, and candidate input ordering preserve run and
  certificate bytes; changing one allowed source fact/profile/partition/monitor digest changes run
  identity.

## Implementation order

1. `partition-contract` — repair the independence boundary before any inferential work exists.
2. `guards-support` — freeze the ordered semantic/support/context abstention surface.
3. `family-equivalence` — compute positive equivalence only for the frozen, guarded family.
4. `certificate-ledger` — persist the complete decision/audit contract and exact-id handoff.

## Testing

### Unit tests

- Factory fixtures in `tests/analytics/eras/conftest.py` build event-clustered corpora, partition
  plans, calibration profiles, semantic facts, candidate/reference intervals, and candidate families
  with fixed dates/seeds.
- Source/partition tests prove event atomicity, disjoint union, cutoff identity, role mutation
  isolation, full-corpus-run refusal, and structural outcome absence.
- Guard tests cover affected/unaffected/pending boundaries, hard contract mismatch, thin and
  concentrated samples, effective event support, power abstention, and context-overlap diagnostics.
- Pure equivalence tests cover the three-way simultaneous-band rule, every named discrepancy
  channel, family growth/order invariance, profile authority, and deterministic control behavior.
- Store tests cover DDL idempotence, canonical round trips, immutable collision refusal, exact-id
  coexistence, absent-run honest nulls, and strict empty outcome evidence.

### Integration tests

- A file-backed DuckDB fixture contains deck construction plus rounds/standings/results. Discovery
  and certification are rerun after outcome mutation and after dropping outcome relations; all
  manifests, candidates, bands, statuses, and certificate ids remain byte-identical.
- A paired event fixture mutates only certification-role decks: discovery/candidate ids stay fixed
  while certification rejects/abstains. Mutating only discovery-role decks may change nomination but
  cannot alter the held-out corpus digest for an unchanged partition.
- False-reunion controls cover same parent/different engine, main-equal/side-different,
  equal-average/different-mixture, confirmed affectedness, context non-overlap, one-event duplication,
  and overlapping candidate families. A known-stable event split is the positive control.
- Focused `tests/analytics/eras/test_certif*.py`, all discovery and existing era tests, Ruff, and
  compileall are required before the feature advances to review.

## Implementation notes

- Execution capability: inline single-owner implementation under active AUTOPILOT; the four child
  checkpoints were carried in dependency order and each was advanced directly to `done`.
- Review weight: standard (caller/project default). Feature is intentionally left at `review` for
  the root agent's independent review.
- Child commits: partition `29188d1`; guards/support `4e8fcca`; family equivalence `41583c1`; exact
  ledger `671898e`; immutable knowledge-availability correction `9a0009f`; discovery result digest
  boundary fix `9825a7c`.
- Files changed: `analytics/eras/certification.py` and `certification_source.py` (closed models,
  partition, guards, channels, bootstrap); `certification_run.py` and `certificate_store.py`
  (immutable run/envelope); `discovery_run.py` (partition-marked pure handoff); package exports,
  calibration config/data, and focused certification tests.
- Verification: 34 focused certification/discovery tests passed; all 199 era tests passed with
  `--import-mode=importlib`; Ruff passed on every touched source/test file; compileall passed.
  Default era invocation has a pre-existing `ModuleNotFoundError: tests` collection issue in
  `test_consume.py`, so the importlib run is the authoritative broader result.
- Simplification: one outcome-free source projection, one deterministic whole-event partition, one
  normalized family bootstrap, and one exact-id JSON ledger now carry the contract; no latest read,
  matchup outcome path, or compatibility fallback was introduced.
- Discrepancies from design: v1 simulated power is a deterministic support-only proxy pending a
  future calibrated resampling challenger; semantic facts are used as source boundaries only when
  the discovery run recorded a non-empty boundary catalog; `knowledge_available_at` is immutable
  persistence metadata outside content-addressed run identity. The checked-in candidate profile
  therefore never emits final `certified` authority until operator promotion.
- Adjacent issues parked: the default pytest import-mode collection defect is pre-existing and
  outside this feature; no product bug was hidden or test-gamed.

## Risks

- **Discovery/certification partition gap:** the shipped discovery run lacks the independent split
  required by research. **Fallback:** Unit 1 changes the rebuildable manifest/composition in place,
  rejects all full-corpus rows, and proves role isolation before any certificate code lands.
- **Sparse holdout yields few certificates:** a strict event split may make most Legacy pockets
  inconclusive. **Fallback:** preserve exact abstention/support evidence and evaluate repeated-split
  or valid simultaneous post-selection methods only as later challengers; never reuse held-out events.
- **Bootstrap method is least certain:** clustered, high-dimensional equivalence is not a turnkey
  theorem, and the recent omnibus method is provisional. **Fallback:** require interpretable
  component bounds and outcome-blind controls in addition to MMD, use conservative whole-family
  bands, version everything, and keep the profile candidate until operator promotion.
- **Calibration can encode wishful transport:** numeric margins/floors could be loosened until history
  passes. **Fallback:** bind an outcome-blind control fixture/confusion matrix, prohibit candidate-
  specific tuning, cap candidate profiles at inconclusive, and require a new operator-promoted id for
  any change.
- **Format truth is temporarily pending:** the current local monitor has a pending legality action.
  **Fallback:** pending evidence creates an explicit inconclusive semantic guard and digest; only the
  curated confirmation path can create a hard fact.
- **Context ratios become unstable:** sparse categories can create extreme weights or apparent
  overlap. **Fallback:** keep weighting diagnostic-only, enforce effective-support/max-weight/
  unsupported-share guards, and abstain rather than trim until a result passes.
- **JSON run rows may grow:** whole-family evidence and bootstrap bands can be large. **Fallback:**
  persist only observed/interval summaries plus hashes and seeds, measure ledger size, and normalize
  storage later without changing the typed certificate contract.

## Other agent review

- Invoked because: the independence repair, equivalence burden, and multiplicity family are
  high-consequence design choices.
- Skipped/degraded: the active autopilot caller explicitly forbids nested subagents and peeragent, so
  no design-time advisory pass was run. This is non-blocking under the advisory policy.
- Receiver judgment: the approved research and implemented discovery boundary support the selected
  conservative sample-split design; the standard independent feature review remains required after
  implementation.

## Review findings

- Effective weight: `standard`; one same-harness fresh-context independent pass reviewed the frozen
  `6122716` snapshot on 2026-08-16. Closure requires verification of the named fix set only, not a
  second independent pass.
- Blocker story: `epic-recurrent-stable-era-evidence-certification-review-corrections`.
- Required corrections: coherent high-dimensional discrepancy smoothing; complete and authoritative
  semantic-gap vetoes; a real frozen-family whole-event bootstrap preserving multiplicity and
  context variation; HHI/equivalent observation-weighted support; checked-in hash-bound control
  evidence and honest power semantics; and hash-bound immutable run status/reasons.
- Important findings absorbed into the current-cycle correction set: cutoff-filter future semantic
  facts, include unavailable format truth in run status, and add adversarial tests for every
  reproduced failure. Receiver judgment treats these as necessary cutoff/status integrity work,
  not deferrable debt.
- Rejected: partition atomicity, outcome firewall, parent-only scope, candidate-profile authority
  cap, empty runs, exact-id reads, and UTC knowledge availability behaved as intended. No foundation,
  security, UI, or async finding was confirmed.
