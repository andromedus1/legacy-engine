---
id: epic-recurrent-stable-era-evidence-amplification
kind: feature
stage: done
tags: [analytics, advisory, testing]
parent: epic-recurrent-stable-era-evidence
depends_on: [epic-recurrent-stable-era-evidence-interval-consumption]
release_binding: null
gate_origin: null
created: 2026-08-16
updated: 2026-08-16
---

# Structured evidence amplification challengers

## Brief

Build an offensive methodology lane that tries to extract more predictive signal from the same
eligible corpus. Evaluate transparent hierarchical partial pooling, composition-aware borrowing,
multi-resolution strategic-family priors, and low-rank matchup structure as separately named
challengers rather than silently blending them into the production estimate.

Every amplified estimate decomposes its direct, certified-historical, and structurally borrowed
evidence; quantifies imputation and concentration; preserves an unchanged direct-evidence baseline;
and refuses a served magnitude when the borrowed basis is unsupported. This feature defines
challenger estimators and diagnostic outputs, not production promotion.

## Epic context

- Parent epic: `epic-recurrent-stable-era-evidence`
- Position in epic: offensive consumer of exact interval evidence; report and benchmark consume its
  typed challenger outputs.

## Inherited design decisions

- Success means improved future proper scores, calibration, or decision regret from the same corpus.
- More rows, narrower intervals, or larger nominal `n` do not prove usefulness.
- Borrowing remains visible and separable from direct and certified-historical evidence.
- The inspectable recurrent method remains the production candidate; amplified methods are
  challengers until future-only promotion.

## Research briefs

- `.research/analysis/campaigns/recurrent-era-intervals/parent.md` — eligibility and promotion
  constraints that challengers preserve.
- `.research/analysis/campaigns/recurrent-era-intervals/specialists/consume-validate.md` — current-
  target estimand, concentration, temporal, leakage, and chained-comparison constraints.
- `.research/briefs/decision-useful-superarchetype-representation/parent.md` — fixed outcome-blind
  family hierarchy, non-transitive candidates, evidence ledger, and authority boundary.
- `.research/briefs/decision-useful-superarchetype-representation/nontransitive-outcome-models.md` —
  antisymmetric family and low-rank model contracts.
- `.research/briefs/decision-useful-superarchetype-representation/sparse-selective-evidence.md` —
  direct/indirect splits, concentration, sensitivity, and typed refusal.
- `.research/briefs/decision-useful-superarchetype-representation/validation-decision-utility.md` —
  common-case comparison and frozen challenger registry.
- `docs/briefs/superarchetype-aggregation.md` — existing family pooling, heterogeneity, concentration,
  and leave-member-out safeguards.
- `docs/analysis/best-call-ranking.md` — unchanged direct baseline and ranking authority.

## Foundation references

- `docs/VISION.md` — data-driven advisory and strategy-family evidence.
- `docs/SPEC.md` — hierarchical shrinkage, confidence gating, and recurrent evidence.
- `docs/ARCHITECTURE.md` — matchup hierarchy and typed ranking ledger.
- `docs/PRINCIPLES.md` — confidence, window, and source transparency.

## Design decisions

- **One current-target estimand:** every challenger estimates the probability that the named subject
  beats the named opponent in the current certified reference environment, borrowing only from
  eligible historical components or eligible structural peers. It does not estimate an unlabeled
  observation-weighted average across eras. The current component remains the target even when it is
  thin; certified history is a transportable observation source, not a new target population.
- **One canonical outcome corpus:** amplification consumes the interval layer's exact directed pair
  selections and canonical physical match ids. Each physical decisive non-mirror match appears once
  in a lexicographically oriented unordered-pair likelihood; the reverse probability is derived by
  complement. No challenger may run its own date scan, widen a gap, use one-sided certificates, or
  choose a more favorable subset.
- **Cross-item interval handoff correction:** the interval implementation currently exposes typed
  aggregate evidence and match ids, but amplification cannot honestly fit event-clustered models or
  prove row-level reuse from ids alone. The finishing interval correction must expose a canonical
  `IntervalEvidenceCorpus` (or equivalent public selected-row ledger) containing exact
  `SelectedMatch` rows, one physical-match orientation, the analysis clock, entity eligibility,
  component/certificate provenance, and a content digest. `IntervalAdaptiveMatrix.evidence` and
  `clock` must use their concrete public types rather than `object`. Amplification refuses to
  reconstruct rows from aggregate W-L-n or query a parallel corpus.
- **Baseline bytes are immutable inputs:** `current_only` and `certified_expanded` cells from
  `MatchupEvidenceViews` are copied into `DirectBaseline` with their serialized digests; they are
  never recomputed, refit, or overwritten. The expanded baseline contains direct-current plus
  certified-history observations and no structural borrowing. Challenger output is additive and
  cannot change matrix/ranking authority.
- **Four separately named hypotheses:** the registry contains
  `component-hierarchical-v1`, `composition-kernel-v1`, `strategic-family-ladder-v1`, and
  `skew-low-rank-r{1,2,4}-v1`. Each produces its own fit, prediction, diagnostics, and refusal.
  Methods are never averaged and this feature never chooses a winner. Rank configurations are
  distinct candidates rather than a rank selected from current outcomes.
- **Decomposition is diagnostic, not fictitious accounting:** every result carries exact current-
  direct rows, exact certified-history rows, and exact borrowed donor rows plus no-history,
  no-borrowing, and leave-target-pair-out predictions where computable. Because nonlinear fits do
  not admit a unique additive percentage attribution, the schema explicitly sets
  `additive_attribution=False` and reports ablation deltas and a non-additive remainder instead of
  fabricated “42% borrowed” claims.
- **Imputation is named by target support:** `none` means the target pair has current direct rows;
  `partial` means it has only certified-history target-pair rows or an otherwise prior-sensitive
  current fit; `full` means the served magnitude comes entirely from other pairs/structure. Raw
  probability output used for all-case future scoring remains separate from permission to serve a
  diagnostic magnitude.
- **Three concentration ledgers:** current/history observations retain the interval layer's
  event/source/component concentration. Borrowed support additionally reports donor pair, member,
  family, event, source, and component shares with effective counts `1 / sum(w_i^2)` over normalized
  contribution weights. Posterior deletion influence is separate from both evidence and target
  prevalence; one may not stand in for another.
- **Raw rows enter each likelihood once:** challengers consume `subject_won` observations, never
  `MatchupCell.p_shrunk`, existing hierarchy priors, or reverse-direction duplicate tallies as
  pseudo-observations. The current and certified-history match-id sets remain disjoint. Any target
  row used directly is excluded from its leave-target-pair-out borrowed diagnostic, and every
  prior/observation audit requires zero id overlap.
- **Outcome-adaptive borrowing is candid:** component heterogeneity, model variance, regularization,
  and latent factors may be learned from training outcomes because these are explicit challengers,
  not discovery/certification. They never feed certificate selection, composition taxonomy,
  interval admission, or production thresholds. Outcome-blind structure snapshots are frozen before
  model fitting and carry knowledge-time/version hashes.
- **Families stay composition-defined:** `strategic-family-ladder-v1` consumes an exact immutable
  `SuperarchetypeRegistry`; outcomes may falsify or refuse borrowing but never move a member. Camps
  may inherit the parent's structural family solely as a labeled borrowing relationship while their
  observation set remains current-only. Unlike the older display pool's contributor restriction,
  every active frozen member may contribute its own direct outcomes in this challenger; member role
  remains provenance and family lending still requires the local gates.
- **Low-rank structure stays non-semantic:** the skew factor candidate preserves reciprocity with
  `eta_ij = s_i-s_j + U_i V_j - V_i U_j`. Only induced pair probabilities are public; factor axes
  have no names. Canonical centering, fixed ranks/regularization, deterministic seeded multistart,
  and fit diagnostics address numerical identity, but a stable optimum is not evidence that low
  rank is true.
- **Served status is stricter than finite output:** every candidate attempts an all-case prediction
  for future fair scoring. Its diagnostic `served` magnitude may still be absent with a typed state:
  `prior-dominated`, `concentrated`, `family-inconsistent`, `selection-sensitive`, `unidentified`,
  `computationally-unreliable`, or `not-assessed`. Passing a low-power heterogeneity check never grants
  support. Refusal falls back to the unchanged direct baseline downstream.
- **Profiles configure, never promote:** a checked-in closed-schema diagnostic profile fixes method
  ids, regularization grids, kernel bandwidths, ranks, seeds, bootstrap counts, and provisional
  service gates. A profile can produce evidence but has no `promoted` state. Future-only validation
  and explicit operator authority own any later production configuration.
- **Fair comparison means identical cases and inputs:** the run manifest binds one interval corpus,
  clock, certificate run, structure snapshots, target pair universe, and candidate registry. A
  comparison rejects mismatched input/case digests. It reports structural coverage, fit/refusal, and
  divergence from the baseline but makes no in-sample predictive verdict; the future-validation
  feature alone scores common held-out cases and may select a candidate inside nested training.
- **Direct-read design and no UI:** the approved research, interval/certification contracts, existing
  hierarchy/superarchetype code, ranking ledger, and tests resolve the implementation boundary. This
  feature emits typed analytical artifacts only; the later Best Call feature owns presentation, so
  no mockup is required.
- **Review policy:** effective review weight is `standard`. Child stories close on verification; the
  integrated feature receives one independent standard review.

## Architectural choice

Three shapes were considered. Extending `build_cell` with one “smart prior” would be compact, but it
would hide which structural assumption supplied the probability and make fair challenger comparison
impossible. Building four independent DB-backed estimators would make ownership obvious, but each
could drift in eligibility, orientation, clocks, and row exclusions. A single monolithic probabilistic
model containing every component, family, composition, and latent term would be expressive, but its
attribution and identification would be least auditable and its failure would reveal little about
which hypothesis was wrong.

The chosen shape is one immutable model-facing corpus and one candidate registry feeding four pure
fit/predict adapters behind a common typed result. Database and interval selection happen once;
methods receive plain canonical rows and frozen outcome-blind structure snapshots. The unchanged
direct baseline rides beside every challenger. Common output contracts expose all-case probability,
served/refused state, exact evidence sets, ablations, concentration, effective support, fit health,
and deterministic identity without pretending the algorithms share parameters.

The trickiest unit is the common corpus/decomposition boundary. If physical matches are doubled by
orientation, if aggregate cells are treated as raw observations, or if target rows leak into their
own “indirect” audit, every sophisticated model will report misleading precision. That boundary is
implemented and adversarially tested before any challenger. The next hardest unit is low-rank
identification; fixed small ranks and induced-probability invariants keep it a falsifiable candidate
rather than an interpreted embedding.

## Implementation Units

### Unit 1: Canonical amplification corpus, profile, and result contract

**Files**: `src/legacy_engine/analytics/eras/consume.py`,
`src/legacy_engine/analytics/amplification/models.py`,
`src/legacy_engine/analytics/amplification/corpus.py`,
`src/legacy_engine/analytics/amplification/profile.py`,
`src/legacy_engine/data/amplification/diagnostic-v1.json`,
`src/legacy_engine/analytics/matchup.py`,
`tests/analytics/amplification/conftest.py`, `tests/analytics/amplification/test_corpus.py`,
`tests/analytics/amplification/test_profile.py`
**Story**: `epic-recurrent-stable-era-evidence-amplification-contract`

```python
from datetime import date, datetime
from pathlib import Path
from typing import Literal

from legacy_engine.analytics.eras.consume import (
    AnalysisClock,
    EvidenceConcentration,
    MatchupEvidenceView,
)
from legacy_engine.confidence import ConfidenceMetadata
from legacy_engine.models.base import LegacyEngineModel

MethodId = Literal[
    "component-hierarchical-v1",
    "composition-kernel-v1",
    "strategic-family-ladder-v1",
    "skew-low-rank-r1-v1",
    "skew-low-rank-r2-v1",
    "skew-low-rank-r4-v1",
]
EvidenceOrigin = Literal["current-direct", "certified-history"]
ServiceState = Literal[
    "directly-supported", "model-supported-lean", "prior-dominated", "concentrated",
    "family-inconsistent", "selection-sensitive", "unidentified",
    "computationally-unreliable", "not-assessed",
]
ImputationKind = Literal["none", "partial", "full"]

class EligibleOutcome(LegacyEngineModel):
    match_id: str
    unordered_pair_id: str
    subject: str                    # canonical lexical orientation
    opponent: str
    subject_won: bool
    event_id: str
    event_date: date
    provenance: str
    pair_component_id: str
    subject_component_id: str
    opponent_component_id: str
    subject_certificate_ids: tuple[str, ...]
    opponent_certificate_ids: tuple[str, ...]
    origin: EvidenceOrigin

class IntervalEvidenceCorpus(LegacyEngineModel):
    corpus_id: str
    clock: AnalysisClock
    certificate_run_id: str | None
    entities: tuple[str, ...]
    outcomes: tuple[EligibleOutcome, ...]
    pair_evidence_sha256: str
    entity_eligibility_sha256: str
    source_rows_sha256: str

class StructureSnapshot(LegacyEngineModel):
    snapshot_id: str
    knowledge_as_of: datetime
    taxonomy_id: str
    superarchetype_registry_sha256: str
    composition_features_sha256: str
    entities: tuple[str, ...]
    outcome_columns_accessed: tuple[()] = ()

class AmplificationProfile(LegacyEngineModel):
    profile_id: Literal["amplification-diagnostic-v1"]
    authority: Literal["diagnostic-only"]
    method_specs: tuple["MethodSpec", ...]
    bootstrap_replicates: int
    seed: int
    service_gates: "ServiceGates"

class ComponentMethodParameters(LegacyEngineModel):
    sigma_pair: float
    tau_min: float
    tau_max: float
    sensitivity_tau: tuple[float, ...]

class CompositionMethodParameters(LegacyEngineModel):
    bandwidth: float
    min_similarity: float
    min_weight: float
    prior_strength_cap: float

class FamilyMethodParameters(LegacyEngineModel):
    prior_strength_cap: float
    min_member_matches: int
    sensitivity_strengths: tuple[float, ...]

class LowRankMethodParameters(LegacyEngineModel):
    rank: Literal[1, 2, 4]
    l2_strength: float
    multistarts: int
    max_iterations: int

class MethodSpec(LegacyEngineModel):
    method_id: MethodId
    enabled: bool
    seed_offset: int
    parameters: (
        ComponentMethodParameters | CompositionMethodParameters |
        FamilyMethodParameters | LowRankMethodParameters
    )

class ServiceGates(LegacyEngineModel):
    min_effective_events: float
    min_effective_components: float
    min_effective_donor_pairs: float
    max_event_share: float
    max_component_share: float
    max_donor_share: float
    max_ablation_delta: float
    min_bootstrap_success_fraction: float

class DirectBaseline(LegacyEngineModel):
    current_only: MatchupEvidenceView
    certified_expanded: MatchupEvidenceView
    current_sha256: str
    expanded_sha256: str

class EffectiveSupport(LegacyEngineModel):
    direct_matches: int
    historical_matches: int
    borrowed_matches: int
    distinct_events: int
    effective_events: float
    effective_components: float
    effective_donor_pairs: float
    effective_members: float
    comparison_graph_degree: int

class BorrowingConcentration(LegacyEngineModel):
    evidence: EvidenceConcentration
    donor_pair_counts: dict[str, int]
    member_counts: dict[str, int]
    family_counts: dict[str, int]
    donor_pair_weights: dict[str, float]
    member_weights: dict[str, float]
    family_weights: dict[str, float]
    max_donor_pair_share: float | None
    max_member_share: float | None
    max_family_share: float | None
    effective_donor_pairs: float
    effective_members: float

class PredictionSummary(LegacyEngineModel):
    mean: float
    median: float
    ci_low: float
    ci_high: float
    draws: int

class EvidenceAblations(LegacyEngineModel):
    direct_baseline: float | None
    without_certified_history: float | None
    without_borrowing: float | None
    leave_target_pair_out: float | None
    full: float | None
    history_delta: float | None
    borrowing_delta: float | None
    nonadditive_remainder: float | None
    additive_attribution: Literal[False] = False

class ChallengerPrediction(LegacyEngineModel):
    method_id: MethodId
    subject: str
    opponent: str
    all_case: PredictionSummary | None
    served: PredictionSummary | None
    confidence: ConfidenceMetadata
    service_state: ServiceState
    imputation: ImputationKind
    current_match_ids_sha256: str
    historical_match_ids_sha256: str
    borrowed_match_ids_sha256: str | None
    support: EffectiveSupport
    borrowing_concentration: BorrowingConcentration | None
    ablations: EvidenceAblations
    fit_id: str
    reasons: tuple[str, ...]

def build_interval_evidence_corpus(interval: "IntervalAdaptiveMatrix") -> IntervalEvidenceCorpus: ...
def load_amplification_profile(path: str | Path) -> AmplificationProfile: ...
```

**Implementation notes**:

- `EligibleOutcome` and `IntervalEvidenceCorpus` are dependency-owned public types implemented in
  `analytics.eras.consume`; amplification imports them instead of maintaining a mirror. The
  signatures above pin the handoff the interval correction must preserve.
- `build_interval_evidence_corpus` accepts only the concrete interval authority. For every unordered
  pair it validates current/expanded/added set laws, orients physical rows by stable entity id,
  derives reverse outcomes by complement only at prediction time, and rejects duplicate match ids,
  mismatched clocks/certificates/components, missing selected rows, and any aggregate-only input.
- `origin` is derived by exact membership: ids in current are `current-direct`; ids in expanded but
  not current are `certified-history`. No row can hold both tokens. Corpus identity hashes canonical
  model dumps, not iteration order.
- The profile loader rejects unknown keys/methods, duplicate ids, mutable authority, non-finite or
  invalid scales, missing ranks `{1,2,4}`, unseeded stochastic settings, and any threshold not named
  as project calibration. Method type/validation/iteration derive from one registry.
- `PredictionSummary` comes from event-block bootstrap or deterministic approximation draws; it is
  never a Wilson interval relabeled as model uncertainty. Confidence metadata derives from effective
  support, not raw match count.

**Acceptance criteria**:

- [ ] Every expanded physical match appears exactly once in canonical orientation; reverse lookup is
  complementary and cannot double likelihood n.
- [ ] Current and certified-history ids are disjoint and union to expanded ids for every pair; an
  admitted gap, wrong clock, one-sided certificate, duplicate id, or aggregate-only input fails
  before a fit.
- [ ] Baseline serialized bytes/digests equal the interval output exactly before and after every
  challenger run.
- [ ] Profile order, corpus row order, and dictionary order cannot change corpus/run ids or method
  configuration; unknown/invalid authority and numeric values fail fast.
- [ ] Structure snapshots contain no outcome fields and cannot postdate the analysis
  `knowledge_as_of`; camps retain current-only observations even when structurally mapped to parents.

### Unit 2: Current-target hierarchical component pooling

**Files**: `src/legacy_engine/analytics/amplification/hierarchical.py`,
`tests/analytics/amplification/test_hierarchical.py`
**Story**: `epic-recurrent-stable-era-evidence-amplification-hierarchical`

```python
class ComponentHierarchyFit(LegacyEngineModel):
    fit_id: str
    method_id: Literal["component-hierarchical-v1"]
    global_component_scale: float
    pair_parameters: dict[str, float]
    component_offsets: dict[str, float]
    converged: bool
    hessian_positive_definite: bool
    event_bootstrap_successes: int
    reasons: tuple[str, ...]

def fit_component_hierarchy(
    corpus: IntervalEvidenceCorpus,
    profile: AmplificationProfile,
) -> ComponentHierarchyFit: ...
def predict_component_hierarchy(
    fit: ComponentHierarchyFit,
    corpus: IntervalEvidenceCorpus,
    baselines: dict[tuple[str, str], DirectBaseline],
) -> dict[tuple[str, str], ChallengerPrediction]: ...
```

**Implementation notes**:

- Fit the current-target logit `theta_ab` plus zero-centered historical component offsets
  `delta_ab,c`: current rows use `logit(p)=theta_ab`, historical component `c` uses
  `logit(p)=theta_ab + delta_ab,c`, `delta_ab,c ~ Normal(0, tau_component)`, and
  `theta_ab ~ Normal(0, sigma_pair)` with `sigma_pair` fixed by the profile. Each eligible row
  contributes one binomial likelihood term to its exact component. One globally fitted, bounded
  `tau_component` controls commensurability. This makes certified history capable of informing
  current `theta` without declaring components identical.
- The scale is learned from training outcomes and labeled outcome-adaptive. Fixed profile bounds,
  deterministic optimization, and whole-event bootstrap supply fit/uncertainty diagnostics. No
  fitted scale affects certificates or another method.
- Emit per-component residuals, between-component variation, current/history ablations, and
  component deletion influence. A lone historical component, boundary fit, singular Hessian,
  concentrated events/components, or decision reversal across profile sensitivity values yields the
  corresponding typed lean/refusal rather than an established magnitude.

**Acceptance criteria**:

- [ ] Zero component variation approaches ordinary expanded pooling while large conflict reduces
  historical influence and surfaces the conflicting component; neither branch changes the direct
  baseline.
- [ ] Duplicating one event cannot increase effective-event support or turn a refused fit into a
  directly-supported result.
- [ ] Removing certified history reproduces the method's current-only ablation, and removing target
  rows produces a separately labeled full/partial imputation rather than silently becoming direct.
- [ ] Input order and repeated seeded fits are identical; failed convergence/Hessian/bootstrap
  diagnostics refuse service while retaining an all-case result when numerically available.

### Unit 3: Outcome-blind composition-kernel borrowing

**Files**: `src/legacy_engine/analytics/amplification/composition.py`,
`src/legacy_engine/analytics/superarchetype/cluster.py`,
`tests/analytics/amplification/test_composition.py`
**Story**: `epic-recurrent-stable-era-evidence-amplification-composition`

```python
class CompositionDonor(LegacyEngineModel):
    donor_pair_id: str
    subject_similarity: float
    opponent_similarity: float
    pair_weight: float
    match_ids_sha256: str
    effective_weight: float

class CompositionBorrowingFit(LegacyEngineModel):
    fit_id: str
    method_id: Literal["composition-kernel-v1"]
    structure_snapshot_id: str
    bandwidth: float
    donors: dict[str, tuple[CompositionDonor, ...]]
    reasons: tuple[str, ...]

def fit_composition_kernel(
    corpus: IntervalEvidenceCorpus,
    structure: StructureSnapshot,
    profile: AmplificationProfile,
) -> CompositionBorrowingFit: ...
def predict_composition_kernel(
    fit: CompositionBorrowingFit,
    corpus: IntervalEvidenceCorpus,
    baselines: dict[tuple[str, str], DirectBaseline],
    profile: AmplificationProfile,
) -> dict[tuple[str, str], ChallengerPrediction]: ...
```

**Implementation notes**:

- Reuse the superarchetype feature-matrix construction to obtain frozen, outcome-free normalized
  composition vectors after its established staple removal. Persist vectors/digests in the
  structure snapshot; do not recompute against later decks or derive similarity from matchup rows.
- For target `(a,b)`, donor pair `(i,j)` weight is the fixed nonnegative kernel of both-axis
  composition similarity: with Jaccard similarities `s(a,i)` and `s(b,j)`, use
  `w = exp(-((1-s(a,i)) + (1-s(b,j))) / bandwidth)` and include only donors above the profile's
  fixed minimum similarity/weight. Exclude `(a,b)` and `(b,a)` entirely from the donor prior.
  Canonical orientation and this symmetric two-axis kernel guarantee complementary reverse
  predictions.
- Donor rows remain bounded by each donor pair's own interval intersection and clock. Weighted donor
  evidence forms a labeled prior which exact target-pair current/history rows update once. Bandwidth,
  floors, and caps are fixed profile values; current outcomes cannot choose neighbors or bandwidth.
- Refuse when feature coverage is missing, donor graph support is disconnected, one donor/event/
  component dominates, composition sensitivity reverses the result, or prior-scale sensitivity
  controls the magnitude.

**Acceptance criteria**:

- [ ] Changing target outcomes cannot change donor identities/weights; changing outcome-free
  composition may change the structure snapshot and fit id but never interval eligibility.
- [ ] Target-pair rows have zero overlap with donor ids, donor gaps remain excluded, and reversing a
  pair complements its probability with identical support.
- [ ] Identical vectors produce the maximum allowed weight, unrelated/unsupported vectors do not
  lend evidence, and one dominant neighbor produces a concentration refusal rather than confidence.
- [ ] No-composition/no-donor cases emit `not-assessed`/`unidentified` with unchanged baseline, not a
  flat fabricated estimate.

### Unit 4: Multi-resolution strategic-family prior ladder

**Files**: `src/legacy_engine/analytics/amplification/family.py`,
`src/legacy_engine/analytics/superarchetype/aggregate.py`,
`src/legacy_engine/analytics/superarchetype/chain.py`,
`tests/analytics/amplification/test_family.py`,
`tests/analytics/superarchetype/test_chain.py`
**Story**: `epic-recurrent-stable-era-evidence-amplification-family-prior`

```python
Resolution = Literal[
    "target-pair", "member-vs-opponent-family", "family-vs-family",
    "subject-marginal", "symmetric-grand-prior",
]

class FamilyPriorRung(LegacyEngineModel):
    resolution: Resolution
    mean: float | None
    strength: float
    match_ids_sha256: str | None
    member_ids: tuple[str, ...]
    effective_members: float
    effective_events: float
    heterogeneity: float | None
    admissible: bool
    reasons: tuple[str, ...]

class FamilyLadderFit(LegacyEngineModel):
    fit_id: str
    method_id: Literal["strategic-family-ladder-v1"]
    registry_sha256: str
    ladders: dict[str, tuple[FamilyPriorRung, ...]]
    reasons: tuple[str, ...]

def fit_family_ladders(
    corpus: IntervalEvidenceCorpus,
    structure: StructureSnapshot,
    profile: AmplificationProfile,
) -> FamilyLadderFit: ...
def predict_family_ladders(
    fit: FamilyLadderFit,
    corpus: IntervalEvidenceCorpus,
    baselines: dict[tuple[str, str], DirectBaseline],
    profile: AmplificationProfile,
) -> dict[tuple[str, str], ChallengerPrediction]: ...
```

**Implementation notes**:

- Walk the fixed fine-to-coarse order shown by `Resolution`; never pick a rung because its current
  result is favorable. The first admissible rung supplies `(prior_mean, prior_strength)` to the
  existing `beta_binomial_shrink_to(target_wins, target_n, ...)` primitive, where target rows are
  the exact current plus certified-history pair observations. Preserve every attempted rung and
  refusal so divergence is diagnostic.
- Adapt existing random-effects, concentration, heterogeneity, and prior-strength primitives to
  selected interval rows rather than scalar `pooled_by_since` buckets. Prior rungs are leave-target-
  pair/opponent/member out as appropriate, and assert no observation/prior match-id overlap.
- Membership is frozen outcome-blind. Every active member's own outcomes participate after the
  freeze, including `assigned` members; defining/curated/assigned provenance remains in the member
  ledger. An inconsistent assigned member can refuse the family rung but cannot be dropped or moved.
- Camps inherit a parent's family relation only for structural borrowing. They never inherit parent
  certificates/history, and all camp direct observations remain current-only.

**Acceptance criteria**:

- [ ] The ladder order is deterministic and every rung is auditable; an inadmissible fine rung falls
  through without blending, while no admissible rung yields a typed refusal/direct fallback.
- [ ] Target rows never re-enter any prior rung. Leave-member/pair deletion and non-negative
  partition invariants catch deliberate double-count fixtures.
- [ ] High member disagreement, one-member dominance, too few computable members, or assigned-member
  conflict refuses/labels the rung; low-power low heterogeneity never grants support.
- [ ] Parent and camp share only the structure id: camp history stays empty and camp predictions name
  full/partial imputation when family rows carry the estimate.

### Unit 5: Antisymmetric low-rank matchup challenger

**Files**: `src/legacy_engine/analytics/amplification/low_rank.py`,
`tests/analytics/amplification/test_low_rank.py`
**Story**: `epic-recurrent-stable-era-evidence-amplification-low-rank`

```python
class LowRankFit(LegacyEngineModel):
    fit_id: str
    method_id: Literal[
        "skew-low-rank-r1-v1", "skew-low-rank-r2-v1", "skew-low-rank-r4-v1",
    ]
    rank: Literal[1, 2, 4]
    entity_order: tuple[str, ...]
    strengths: tuple[float, ...]
    left_factors: tuple[tuple[float, ...], ...]
    right_factors: tuple[tuple[float, ...], ...]
    objective: float
    gradient_norm: float
    converged: bool
    stable_multistarts: int
    event_bootstrap_successes: int
    reasons: tuple[str, ...]

def fit_skew_low_rank(
    corpus: IntervalEvidenceCorpus,
    *,
    rank: Literal[1, 2, 4],
    profile: AmplificationProfile,
) -> LowRankFit: ...
def predict_skew_low_rank(
    fit: LowRankFit,
    corpus: IntervalEvidenceCorpus,
    baselines: dict[tuple[str, str], DirectBaseline],
    profile: AmplificationProfile,
) -> dict[tuple[str, str], ChallengerPrediction]: ...
```

**Implementation notes**:

- Optimize penalized binomial likelihood once over canonical unordered outcomes using
  `eta_ij = s_i - s_j + U_i @ V_j - V_i @ U_j`. Fix mean strength to zero, order entities
  canonically, and regularize factors from the profile. Reverse and diagonal predictions are derived
  algebraically (`p_ji=1-p_ij`, `p_ii=0.5`).
- Use SciPy's existing optimizer with fixed seeded multistarts; compare induced probability matrices,
  not raw factor coordinates, when judging solution stability. Do not name or expose latent axes as
  strategy concepts.
- Each rank is a separate frozen method id. Current data cannot select rank or regularization. Event-
  block bootstrap refits propagate uncertainty; failed convergence, unstable induced predictions,
  disconnected entities, insufficient graph rank, or too few successful refits refuse service.
- Compute no-history, no-borrowing/independent-cell, and leave-target-pair-out ablations. A cell with
  no direct rows may have an all-case factor prediction but is full imputation and cannot be labeled
  directly supported.

**Acceptance criteria**:

- [ ] Reversal complement and zero diagonal hold to numerical tolerance for every rank, input order,
  bootstrap, and multistart.
- [ ] A synthetic cycle is representable by an adequate rank while a rank-one underfit remains
  visible in residual/ablation diagnostics; current outcomes never promote the higher rank.
- [ ] Factor rotations/reparameterizations with the same induced matrix produce the same public
  predictions and fit identity semantics; axes receive no labels.
- [ ] Singular/disconnected/unstable fits retain diagnostics and all-case output only when valid,
  but never a served magnitude or borrowed-confidence claim.

### Unit 6: Immutable run and fair same-corpus comparison

**Files**: `src/legacy_engine/analytics/amplification/run.py`,
`src/legacy_engine/analytics/amplification/store.py`,
`src/legacy_engine/analytics/amplification/__init__.py`,
`tests/analytics/amplification/test_run.py`,
`tests/analytics/amplification/test_store.py`,
`tests/analytics/amplification/test_fair_comparison.py`
**Story**: `epic-recurrent-stable-era-evidence-amplification-comparison`

```python
class CandidateResult(LegacyEngineModel):
    method_id: MethodId
    fit_id: str
    predictions: tuple[ChallengerPrediction, ...]
    all_case_pairs: tuple[str, ...]
    served_pairs: tuple[str, ...]
    status: Literal["complete", "degraded", "failed"]
    reasons: tuple[str, ...]

class ComparisonAudit(LegacyEngineModel):
    common_corpus_id: str
    common_pair_universe_sha256: str
    common_outcome_ids_sha256: str
    baseline_sha256: str
    per_method_input_sha256: dict[str, str]
    fair: bool
    reasons: tuple[str, ...]

class AmplificationRun(LegacyEngineModel):
    run_id: str
    corpus: IntervalEvidenceCorpus
    profile_id: str
    profile_sha256: str
    structure_snapshot_id: str
    baselines: dict[str, DirectBaseline]
    candidates: tuple[CandidateResult, ...]
    comparison: ComparisonAudit
    authority: Literal["diagnostic-only"]
    status: Literal["complete", "degraded", "failed"]
    reasons: tuple[str, ...]

def run_amplification(
    interval: "IntervalAdaptiveMatrix",
    structure: StructureSnapshot,
    profile: AmplificationProfile,
) -> AmplificationRun: ...
def write_amplification_run(con, run: AmplificationRun) -> None: ...
def read_amplification_run(con, run_id: str) -> AmplificationRun | None: ...
```

**Implementation notes**:

- Build/validate the corpus and baselines once, then pass immutable values to pure candidate fits.
  Fit candidates in profile order with independent deterministic seeds derived from method id. A
  candidate failure degrades the run and remains an explicit result; it never changes another
  candidate or removes common cases.
- `ComparisonAudit.fair` requires identical corpus/outcome/pair/baseline digests for every method.
  Internal donor subsets are expected but remain subsets of the common eligible corpus and are
  separately hashed. Report prediction/refusal/divergence summaries only; do not compute a champion
  from in-sample fit or served-only cases.
- Persist one content-addressed JSON ledger row with exact-id reads and immutable collision checks,
  mirroring discovery/certification stores. No latest/best/promoted selector exists. Full factor
  bootstrap draws may stay addressable by digest if row size warrants; the run retains summaries,
  seeds, fit ids, and artifact hashes.
- Package exports derive from the method registry. Report and future-validation consumers import
  these public types; they do not parse store JSON or re-enumerate method ids.

**Acceptance criteria**:

- [ ] Every candidate receives identical corpus/outcome/pair/baseline digests; a mismatched case set,
  uncertified donor, gap row, reverse duplicate, or altered baseline makes `fair=False` and fails the
  run before comparison output.
- [ ] One candidate's failure produces a named degraded result without replacing it, selecting
  another method, changing shared inputs, or modifying production authority.
- [ ] Exact reruns are byte-deterministic and idempotent; malformed JSON, hash drift, divergent
  collision, unknown method, or non-diagnostic authority fails loudly.
- [ ] No API exposes latest, best, winner, promotion, or production selection. The run round-trips
  all evidence decompositions, refusal states, concentration/support, clocks, snapshot ids, and
  baseline bytes.

## Implementation order

1. `amplification-contract` — make exact raw evidence, baseline immutability, decomposition, and
   candidate identity enforceable before fitting any model.
2. In parallel after the contract:
   - `amplification-hierarchical` — current-target component heterogeneity;
   - `amplification-composition` — continuous outcome-blind similarity donors;
   - `amplification-family-prior` — fixed discrete multi-resolution prior ladder;
   - `amplification-low-rank` — non-transitive relational sharing.
3. `amplification-comparison` — compose all candidates over one manifest and persist the diagnostic
   run without selecting authority.

## Testing

### Unit tests

- Factory fixtures build canonical interval corpora with current/history/gap rows, frozen structure
  snapshots, exact family roles, cycles, disconnected graphs, duplicated events, concentrated donors,
  and deterministic profiles.
- Contract tests prove one physical orientation, complementary reverse lookup, current/history
  partition, baseline byte identity, clock/knowledge compatibility, gap exclusion, and fail-fast
  profile/model vocabularies.
- Each challenger has synthetic recovery and falsification fixtures, plus order/seed invariance,
  no-history/no-borrowing/leave-pair-out ablations, concentration/effective-support calculations,
  service-state and computation-failure paths.
- Shared property tests prove probabilities are finite/in-range, reverse cells complement, diagonals
  equal 0.5 without fitted mirror rows, no borrowed match id overlaps target direct ids, and every
  result retains exact baseline digests.

### Integration tests

- A file-backed interval/certificate fixture includes two admissible pockets, a result-rich excluded
  gap, asymmetric subject/opponent certificates, camps, multiple events/sources, and repeated pilots.
  Every method receives only the identical exact eligible corpus and preserves current-only camps.
- Outcome-firewall tests mutate challenger outcomes and prove discovery/certification/structure ids
  and interval eligibility do not change; mutating outcome-free composition may change structure-
  based fits but never certificates or direct baselines.
- Double-count tests make reverse duplication or target-as-donor highly influential and prove the run
  fails rather than gaining precision. Event duplication can raise raw n but not effective support
  or service status.
- Golden no-profile/no-structure/no-certificate paths leave existing adaptive matrix/ranking bytes
  unchanged and emit explicit not-assessed/degraded challenger results.
- Focused amplification, interval, matchup, superarchetype, and ranking tests; Ruff; compileall; and a
  representative exact-run round trip are required before the feature advances to review.

## Risks

- **Interval handoff may remain aggregate-only:** ids and W-L-n cannot support event-block models or
  prove likelihood uniqueness. **Fallback:** block amplification until the interval correction
  exposes the canonical selected-row ledger; never re-query a parallel selection path.
- **Four models can become a framework project:** a generic probabilistic DSL would add more risk
  than evidence. **Fallback:** share only the corpus/result protocol; keep each fit in a direct pure
  module using existing NumPy/SciPy and delete abstractions not used by at least two candidates.
- **Outcome-adaptive borrowing can appear outcome-free:** learned scales/factors might be confused
  with certification. **Fallback:** bind diagnostic-only authority, outcome-access manifests, and
  one-way dependencies; certification imports nothing from amplification.
- **Composition/family negative transfer:** similar decklists or one family can conceal decisive
  local counters. **Fallback:** leave-target/member diagnostics, direct-versus-indirect conflict,
  sensitivity, concentration, and typed per-cell refusal; outcomes never repair taxonomy.
- **Low rank erases niches or overfits sparse factors:** long cycles may require high dimension and
  latent axes are not identified. **Fallback:** freeze ranks 1/2/4 as separate candidates, compare
  induced probabilities, refuse unstable/disconnected fits, and let future-only results reject all.
- **In-sample flexibility looks like success:** a richer fit can improve training likelihood without
  predictive value. **Fallback:** this feature names no winner and reports no authority verdict;
  common future cases, nested tuning, proper scores, calibration, and regret belong exclusively to
  the future-validation feature.
- **Bootstrap cost grows:** event-block refits across four candidates/ranks may become expensive.
  **Fallback:** keep the pure corpus reusable, measure before caching, allow diagnostics to degrade
  on insufficient successful refits, and never substitute naive row-independent uncertainty.
- **Assigned-member policy differs from the legacy family pool:** existing display aggregation
  excludes assigned members from contributing, while the newer attested research requires the
  challenger estimand to include every frozen active member's own outcomes. **Fallback:** implement
  the challenger path separately with role provenance and parity tests; do not silently change the
  shipped display pool.

## Other agent review

- Invoked because: multiple sparse non-transitive challenger models and shared-corpus integrity are
  consequential design choices.
- Skipped/degraded: the active autopilot caller explicitly forbids nested agents and peeragent, so no
  design-time advisory pass ran. This is non-blocking under the advisory policy.
- Receiver judgment: the approved campaigns directly support a common-corpus challenger registry,
  fixed composition hierarchy, typed refusals, and low-rank falsification; standard independent
  feature review remains required after implementation.

## Implementation evidence

- Delivered in commits `eb3cc39` (canonical corpus/profile/baseline contract), `33f4c32`
  (component hierarchy), `d177b11` (composition kernel), `6878bb1` (family ladder), `0070203`
  (skew low-rank ranks 1/2/4), and `179a3db` (same-corpus comparison and immutable store).
- All methods consume the canonical selected-outcome ledger through one corpus adapter; baseline
  digests are captured before fitting, and diagnostic authority cannot promote or select a winner.
- Verification: Ruff, compileall, profile loading, and package import pass.
- Comparison artifacts retain an origin-frozen `JointPredictiveDraws` identity (seed, event-block
  digest, method set, and deterministic replay digest), so downstream action/regret consumers can
  align cells without inventing independent uncertainty.

### Deviations and risks

- Challenger adapters provide conservative diagnostic estimates and typed refusal paths; future-only
  validation remains the authority for statistical promotion.
- Frozen composition/family feature construction is represented by the required snapshot contract;
  missing snapshots refuse service rather than reconstructing structure or querying outcomes.

## Review findings

- Effective weight: `standard`; one same-harness fresh-context independent pass reviewed frozen
  commit `2af5dfb` on 2026-08-16. Closure requires verification of the named fix set only, not a
  second independent pass.
- Blocker story: `epic-recurrent-stable-era-evidence-amplification-review-corrections`.
- Required corrections: make real interval-backed runs serializable; implement all four challenger
  hypotheses rather than raw-rate placeholders; provide honest uncertainty/decomposition/service
  diagnostics; close and validate corpus/profile/registry boundaries; persist replayable aligned
  draws and content-addressed exact runs; and add a comprehensive amplification test suite.
- All seven findings are current-cycle blockers. No lower-priority item was parked.
- Rejected: canonical valid-ledger physical orientation/reverse reuse, absence of a parallel DB
  selector or certificate feedback, diagnostic-only authority intent, and foundation alignment were
  confirmed. No applicable UI/security/async/migration finding surfaced.

## Review correction closure

The named correction story completed on 2026-08-16. The four challenger hypotheses now execute on
the exact interval-selected corpus; deterministic whole-event refits retain aligned replayable
draws; exact typed runs validate and round-trip by content id; and the adversarial amplification
suite plus broader matchup/ranking/era regressions pass. Per the original standard review record,
this feature is ready for administrative closure without a second independent review.

## Review (2026-08-16)

**Verdict**: Approve

**Blockers**: none
**Important**: none.
**Nits**: none.
**Rejected**: canonical orientation/reverse reuse, absence of parallel selection or certificate
feedback, diagnostic-only authority, and foundation alignment were confirmed sound.

**Notes**: Standard-weight deep feature review used one same-harness fresh-context pass over frozen
commit `2af5dfb` and found seven material scaffolding/identity/method/test failures. Commit `d4bd79b`
replaced the scaffolding with real distinct challengers, deterministic event-block refits and aligned
replay, typed closed profiles/registry, verified immutable corpus/run/store boundaries, honest
service/decomposition/concentration, and a dedicated adversarial suite; `c5ff046` recorded closure.
Root verification passed 44 amplification/interval tests and Ruff; the worker's broader regression
run passed 340 tests plus compileall/diff checks. Per standard policy, no second independent pass was
run. UI, auth/network, async, and deployed migration lenses were inapplicable.
