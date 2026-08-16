---
id: epic-recurrent-stable-era-evidence-discovery
kind: feature
stage: review
tags: [analytics, testing]
parent: epic-recurrent-stable-era-evidence
depends_on: []
release_binding: null
gate_origin: null
created: 2026-08-16
updated: 2026-08-16
---

# Outcome-firewalled recurrent-state discovery

## Brief

Build an inspectable parent-archetype segmentation and fingerprint pipeline that can nominate older
configuration periods as candidates for recurrence. Discovery may use mainboard and sideboard
composition, deck-level mixture shape, legality, taxonomy, provenance, event support, and field
context at an explicit cutoff. Its input contract must make matchup wins, standings, conversion, and
other outcomes unavailable rather than merely unused by convention.

This feature produces candidates and their evidence; it does not certify equivalence, select matchup
rows, or alter a production ranking. Camps remain outside the first certification surface and retain
their current-only behavior.

## Epic context

- Parent epic: `epic-recurrent-stable-era-evidence`
- Position in epic: foundation feature; certification depends on its cutoff-safe candidate and
  fingerprint contracts.

## Inherited design decisions

- Parent archetypes are the first certification surface; camps do not inherit parent certainty.
- The initial method is inspectable segment/fingerprint comparison with complete-link grouping.
- Discovery is outcome-firewalled and deterministic at an explicit cutoff.
- Complex sticky-state methods remain benchmark challengers rather than production defaults.

## Research briefs

- `.research/analysis/campaigns/recurrent-era-intervals/parent.md` — discovery contract and selected
  first-pass method.
- `.research/analysis/campaigns/recurrent-era-intervals/specialists/discover.md` — candidate methods,
  assumptions, and challenger analysis.
- `docs/briefs/change-point-detection.md` — existing stable-era detector grounding and corpus shape.

## Foundation references

- `docs/VISION.md` — certified per-entity interval evidence.
- `docs/SPEC.md` — recurrent stable-era evidence capability.
- `docs/ARCHITECTURE.md` — `analytics/eras/` discovery and certificate boundaries.

## Design decisions

- **Structural outcome firewall:** recurrent discovery does not reuse `series.EntitySeries`,
  `entity_eras`, or any object that carries `wins`, `losses`, result strings, standings, conversion,
  or matchup cells. A dedicated DuckDB adapter projects only tournament identity/date/source,
  parent labels, deck identity, pilot key, and board-separated card counts into frozen Pydantic
  models with `extra="forbid"`; the pure discovery core receives only that model.
- **Explicit cutoff semantics:** `as_of: date` is required and inclusive for source events. Every
  query is bounded by `event_date <= as_of`; the current reference segment is represented as a
  half-open interval ending at `as_of + 1 day`. Events or configuration vocabulary first observed
  later cannot affect an earlier run.
- **Parent-only first surface:** every labeled parent deck contributes to field context, but only
  parents clearing the configured subject-deck floor are segmented. Variant/camp labels are absent
  from the discovery contract, so a parent candidate cannot be mistaken for camp evidence.
- **Today's-model identity is explicit:** every run requires a taxonomy version and legality version.
  These identify the current model used to reconstruct history; they do not imply an as-known-then
  result. Hard taxonomy/source-contract boundaries split observations unless the caller declares a
  backfilled common contract. Legality boundaries are recorded but are not universal vetoes;
  confirmed entity affectedness remains certification's responsibility.
- **Inspectable first method:** build fixed-calendar, cutoff-derived weekly feature buckets and use
  deterministic cosine-kernel PELT to nominate contiguous segments. Fingerprints preserve separate
  mainboard and sideboard slot distributions, deck-level mixture evidence, field context, source
  mix, distinct-event/pilot support, missingness, and exact deck/event membership.
- **Complete-link recurrence:** historical segments join the current state only when every named
  distance channel clears its discovery threshold against every segment already in the current
  group. Candidates are considered closest-to-current first with lexical tie-breaking. Direct
  near-misses and complete-link conflicts remain persisted with reason codes.
- **Discovery is nomination, never equivalence:** checked-in `recurrent-segment-fingerprint-v1`
  calibration uses 7-day buckets, a 3-bucket/30-deck/3-event segment floor, cosine-PELT penalty
  `0.5`, additive smoothing `0.5`, and maximum distances `main=0.12`, `side=0.18`,
  `mixture=0.20`, `field=0.25`, `source=0.25`. These are conservative, outcome-free discovery
  gates—not certification margins—and changing any value requires a new calibration id.
- **Immutable handoff:** a run id hashes the manifest (cutoff, source digest, exact allowlist,
  method/calibration versions, semantic-boundary facts, provenance filter, and seed). The result
  digest is stored beside it. Rewriting the same run id with different bytes fails loudly; later
  certification may consume only a persisted run id.
- **Honest no-candidate states:** thin current references, unsupported historical segments, or no
  recurrent group produce typed `degraded` / `no-recurrence` results with named reasons. They do not
  fabricate a candidate or widen the current-only fallback.
- **Direct-read design:** the feature is bounded to `analytics/eras/`, its DuckDB source tables, and
  mirrored era tests; local inspection resolved the remaining interface questions without an
  exploratory fan-out.
- **No UI surface:** this feature emits typed analytical artifacts only. The parent epic already
  assigns report composition to the later Best Call integration feature, so no mockup is required.
- **Review policy:** effective review weight is `standard` from the project default. Child stories
  close on implementation verification; the integrated feature receives the one required standard
  independent review pass.

## Architectural choice

Three approaches were considered. Reusing `EntitySeries` and the existing accepted `entity_eras`
boundaries would be compact, but both carry round-derived win/loss evidence and therefore fail the
structural firewall even if recurrence code promises not to inspect it. Keeping the existing types
and adding a SQL view that omits outcome columns would narrow the query, but the discovery algorithm
would still own a live connection to tables containing outcomes and future edits could cross the
boundary accidentally.

The chosen approach is a dedicated outcome-free snapshot port followed by a pure segmentation and
fingerprint core. The adapter can see the source database only long enough to construct a closed,
extra-forbidden model; the core cannot name or access outcome facts. A content-addressed DuckDB
ledger persists the manifest and complete candidate evidence as a rebuildable derived artifact.
This costs new types and an explicit source adapter, but makes outcome permutation/removal and
cutoff invariance executable contracts rather than review conventions.

The trickiest unit is the firewall/cutoff boundary because every statistical safeguard downstream
is invalid if the candidate set can depend on a result or a future vocabulary. It is implemented and
adversarially tested first. The segmentation and complete-link layer remains replaceable behind the
same manifest/result contract, leaving sticky-state and TICC methods free to appear later as named
challengers without weakening the first method's audit trail.

## Implementation Units

### Unit 1: Outcome-free corpus, versioned calibration, and cutoff adapter

**Files**: `src/legacy_engine/analytics/eras/discovery.py`,
`src/legacy_engine/analytics/eras/discovery_source.py`, `src/legacy_engine/config.py`,
`src/legacy_engine/data/eras/discovery-v1.json`,
`tests/analytics/eras/test_discovery_source.py`, `tests/analytics/eras/conftest.py`
**Story**: `epic-recurrent-stable-era-evidence-discovery-firewall-corpus`

```python
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import Literal

import duckdb
from pydantic import ConfigDict, Field

from legacy_engine.models.base import LegacyEngineModel

BoundaryKind = Literal["legality", "taxonomy", "source-contract"]

class OutcomeFreeModel(LegacyEngineModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

class DiscoveryCard(OutcomeFreeModel):
    name: str
    copies: int = Field(gt=0)

class DiscoveryDeck(OutcomeFreeModel):
    event_id: str
    event_date: date
    deck_idx: int
    pilot_key: str | None
    parent_archetype: str
    source: str
    provenance: str
    mainboard: tuple[DiscoveryCard, ...]
    sideboard: tuple[DiscoveryCard, ...]

class DiscoveryBoundary(OutcomeFreeModel):
    boundary_id: str
    effective_on: date
    kind: BoundaryKind
    hard: bool
    detail: str

class DistanceThresholds(OutcomeFreeModel):
    main_js_max: float
    side_js_max: float
    mixture_energy_max: float
    field_js_max: float
    source_js_max: float

class SegmentationWeights(OutcomeFreeModel):
    main: float
    side: float
    field: float
    source: float
    subject_share: float

class DiscoveryCalibration(OutcomeFreeModel):
    calibration_id: str
    method_id: Literal["segment-fingerprint-complete-link-v1"]
    bucket_days: int
    min_segment_buckets: int
    min_segment_decks: int
    min_segment_events: int
    min_subject_decks: int
    pelt_penalty: float
    smoothing_alpha: float
    weights: SegmentationWeights
    thresholds: DistanceThresholds

class OutcomeFreeCorpus(OutcomeFreeModel):
    as_of: date
    taxonomy_version: str
    legality_version: str
    provenance_filter: str | None
    semantic_boundaries: tuple[DiscoveryBoundary, ...]
    decks: tuple[DiscoveryDeck, ...]
    source_sha256: str

def load_discovery_calibration(path: Path | str) -> DiscoveryCalibration: ...

def load_outcome_free_corpus(
    con: duckdb.DuckDBPyConnection,
    *,
    as_of: date,
    taxonomy_version: str,
    legality_version: str,
    semantic_boundaries: Sequence[DiscoveryBoundary] = (),
    provenance: str | None = None,
) -> OutcomeFreeCorpus: ...
```

**Implementation notes**:

- `OutcomeFreeModel` deliberately tightens the shared `LegacyEngineModel` at this trust boundary:
  all shared types still inherit the project base, while an unknown key such as `wins`, `result`, or
  `standing` is rejected rather than ignored.
- The source adapter executes batched projections over `tournaments`, `decks`, and `deck_cards`
  only. It never selects `decks.result`, and it never references `rounds` or `standings`. The core
  takes `OutcomeFreeCorpus`, not a connection or callback.
- Mainboard and sideboard remain separate; cards sort by normalized name and decks by
  `(event_date, event_id, deck_idx)`. `pilot_key` is a normalized tournament-local identity used
  only for concentration diagnostics, never linked to outcomes.
- The source digest hashes the canonical typed payload after cutoff filtering. It therefore binds
  the exact evidence available to discovery, excluding only the digest field itself. It therefore
  remains invariant to outcome-only mutations without creating a recursive hash definition.
- `load_discovery_calibration` is path-taking and fail-fast with path/key context. The shipped JSON
  carries the exact operating point above and the five segmentation weights
  `main=.40, side=.25, field=.20, source=.10, subject_share=.05`; values must be finite,
  nonnegative, and sum to one. Missing or malformed calibration blocks a run rather than selecting
  history under an implicit fallback.
- `DiscoveryBoundary.hard=True` forces a segment boundary and prevents comparison across different
  observation-contract epochs. Shipped legality events are non-hard facts unless a later operator-
  confirmed entity rule says otherwise; discovery does not duplicate certification's affectedness
  veto.

**Acceptance criteria**:

- [ ] Constructing any outcome-free model with an outcome/standing/conversion key fails validation.
- [ ] Dropping `rounds` and `standings` entirely does not prevent corpus construction; mutating
  `decks.result`, rounds, or standings leaves canonical corpus bytes and `source_sha256` identical.
- [ ] An event on `as_of` is included, an event after it is excluded, and adding any later-only card
  cannot change an earlier cutoff's vocabulary or digest.
- [ ] Board identity, copies, event/source/provenance, pilot key, and parent label round-trip exactly
  in deterministic order; camp/variant is structurally absent.
- [ ] Unknown/conflict labels do not become subjects, while their omission cannot consult outcomes.
- [ ] Invalid versions, boundary kinds, weights, thresholds, or calibration files fail fast with the
  offending value/path named.

### Unit 2: Cutoff-refit segments, fingerprints, and complete-link candidates

**Files**: `src/legacy_engine/analytics/eras/discovery.py`,
`tests/analytics/eras/test_discovery.py`, `tests/analytics/eras/conftest.py`
**Story**: `epic-recurrent-stable-era-evidence-discovery-segments-fingerprints`

```python
from datetime import date
from typing import Literal

DiscoveryStatus = Literal["candidate", "no-recurrence", "degraded"]
DiscoveryReason = Literal[
    "insufficient-subject-decks",
    "insufficient-reference-buckets",
    "insufficient-reference-decks",
    "insufficient-reference-events",
    "insufficient-historical-decks",
    "insufficient-historical-events",
    "main-shift",
    "sideboard-shift",
    "mixed-configuration",
    "field-shift",
    "source-shift",
    "contract-incompatible",
    "complete-link-conflict",
    "no-historical-segment",
]

class NamedMass(OutcomeFreeModel):
    key: str
    mass: float

class SegmentSupport(OutcomeFreeModel):
    decks: int
    events: int
    pilots: int
    buckets: int
    max_event_share: float | None
    max_pilot_share: float | None
    missing_bucket_fraction: float

class SegmentFingerprint(OutcomeFreeModel):
    segment_id: str
    entity: str
    start: date
    end: date                 # exclusive
    reference: bool
    contract_epoch: str
    crossed_boundary_ids: tuple[str, ...]
    support: SegmentSupport
    deck_ids: tuple[str, ...]
    event_ids: tuple[str, ...]
    main_slots: tuple[NamedMass, ...]
    side_slots: tuple[NamedMass, ...]
    field_context: tuple[NamedMass, ...]
    source_mix: tuple[NamedMass, ...]
    deck_vectors_sha256: str

class SegmentDistances(OutcomeFreeModel):
    main_js: float
    side_js: float
    mixture_energy: float
    field_js: float
    source_js: float
    normalized_max: float

class SegmentComparison(OutcomeFreeModel):
    comparison_id: str
    left_segment_id: str
    right_segment_id: str
    distances: SegmentDistances | None
    compatible: bool
    reasons: tuple[DiscoveryReason, ...]

class RecurrentCandidateGroup(OutcomeFreeModel):
    candidate_id: str
    reference_segment_id: str
    historical_segment_ids: tuple[str, ...]
    comparison_ids: tuple[str, ...]

class EntityDiscoveryResult(OutcomeFreeModel):
    entity: str
    status: DiscoveryStatus
    reference_segment_id: str | None
    segments: tuple[SegmentFingerprint, ...]
    comparisons: tuple[SegmentComparison, ...]
    candidate: RecurrentCandidateGroup | None
    reasons: tuple[DiscoveryReason, ...]

def segment_parent_archetype(
    corpus: OutcomeFreeCorpus,
    entity: str,
    calibration: DiscoveryCalibration,
    *,
    seed: int = 0,
) -> tuple[SegmentFingerprint, ...]: ...

def compare_segment_fingerprints(
    corpus: OutcomeFreeCorpus,
    left: SegmentFingerprint,
    right: SegmentFingerprint,
    calibration: DiscoveryCalibration,
) -> SegmentComparison: ...

def discover_recurrent_states(
    corpus: OutcomeFreeCorpus,
    calibration: DiscoveryCalibration,
    *,
    seed: int = 0,
) -> tuple[EntityDiscoveryResult, ...]: ...
```

**Implementation notes**:

- Derive the vocabulary and every active ISO-week bucket from `OutcomeFreeCorpus` only. A bucket
  carries separately normalized main/side slot vectors, opponent-parent field shares excluding the
  subject, source/provenance shares, and subject field share. Concatenate square-root-weighted
  channels and run `ruptures.KernelCPD(kernel="cosine", min_size=3)` with the versioned penalty.
- Split each hard contract epoch independently and union deterministic PELT boundaries with exact
  hard dates. Segment identifiers hash entity, half-open bounds, source digest, and method version.
  Current reference end is `as_of + 1 day`; every earlier segment is completed.
- Jensen-Shannon distances use base 2 and additive smoothing over the cutoff-derived union
  vocabulary. `mixture_energy` is the multivariate energy distance over board-tagged per-deck copy
  vectors, normalized to `[0, 1]`; averages alone can therefore never clear the mixture channel.
- Unsupported segments remain in `segments` and receive named comparison refusals. No p-value from
  off-the-shelf PELT is reported as calibrated evidence; segmentation is nomination only.
- Build the current complete-link group greedily from direct-compatible historical segments sorted
  by `(normalized_max, start, segment_id)`. Add a segment only if all pairwise comparisons with the
  group clear every threshold and contract guard. Persist excluded direct-near candidates as
  `complete-link-conflict` rather than hiding them.
- Empty/zero-mass channels yield a named degraded/refusal reason instead of a numeric zero. The
  current segment must independently clear bucket/deck/event floors before any candidate is emitted.

**Acceptance criteria**:

- [ ] Same cutoff/corpus/config/seed produces byte-identical segment ids, distances, reasons, and
  candidate ids; adding post-cutoff data changes none of them.
- [ ] Mainboard equality cannot hide a sideboard shift, and equal mean card shares cannot hide a
  50/50 deck-mixture change.
- [ ] A→B and B→C similarity cannot reunite A with C when their direct comparison fails; emitted
  groups satisfy every pairwise threshold.
- [ ] Field/source shift and hard-contract incompatibility remain separate, inspectable reasons;
  a non-hard legality boundary is recorded without becoming a blanket reset.
- [ ] Thin current and historical segments honest-degrade independently with deck/event/bucket
  evidence, and a no-recurrence result is a valid deterministic output.
- [ ] The algorithm returns parent entities only and never exposes a matchup, standing, conversion,
  win, or loss field in a fingerprint/comparison/candidate payload.

### Unit 3: Content-addressed discovery run and candidate ledger

**Files**: `src/legacy_engine/analytics/eras/discovery_run.py`,
`src/legacy_engine/analytics/eras/discovery_store.py`,
`src/legacy_engine/analytics/eras/__init__.py`,
`tests/analytics/eras/test_discovery_run.py`, `tests/analytics/eras/test_discovery_store.py`
**Story**: `epic-recurrent-stable-era-evidence-discovery-candidate-ledger`

```python
from collections.abc import Sequence
from datetime import date
from typing import Literal

import duckdb

DiscoveryRunStatus = Literal["complete", "degraded"]
DiscoveryRunReason = Literal["no-eligible-parent-archetypes"]

class DiscoveryManifest(OutcomeFreeModel):
    method_id: str
    calibration_id: str
    calibration_sha256: str
    as_of: date
    taxonomy_version: str
    legality_version: str
    provenance_filter: str | None
    semantic_boundaries_sha256: str
    source_sha256: str
    feature_allowlist: tuple[str, ...]
    seed: int

class DiscoveryRun(OutcomeFreeModel):
    run_id: str
    manifest: DiscoveryManifest
    results_sha256: str
    status: DiscoveryRunStatus
    reasons: tuple[DiscoveryRunReason, ...]
    results: tuple[EntityDiscoveryResult, ...]

def build_discovery_manifest(
    corpus: OutcomeFreeCorpus,
    calibration: DiscoveryCalibration,
    *,
    seed: int,
) -> DiscoveryManifest: ...

def run_recurrent_discovery(
    con: duckdb.DuckDBPyConnection,
    *,
    as_of: date,
    taxonomy_version: str,
    legality_version: str,
    calibration: DiscoveryCalibration,
    semantic_boundaries: Sequence[DiscoveryBoundary] = (),
    provenance: str | None = None,
    seed: int = 0,
) -> DiscoveryRun: ...

def init_discovery_schema(con: duckdb.DuckDBPyConnection) -> None: ...
def write_discovery_run(con: duckdb.DuckDBPyConnection, run: DiscoveryRun) -> None: ...
def read_discovery_run(
    con: duckdb.DuckDBPyConnection,
    run_id: str,
) -> DiscoveryRun | None: ...
def discovery_run_ids(
    con: duckdb.DuckDBPyConnection,
    *,
    as_of: date | None = None,
) -> tuple[str, ...]: ...
```

**Implementation notes**:

- `run_recurrent_discovery` composes the adapter once, closes the outcome-bearing boundary by
  retaining only `OutcomeFreeCorpus`, runs the pure engine, computes canonical manifest/result
  SHA-256 digests, and commits one immutable `era_discovery_runs` row in a transaction.
- `run_id` is the manifest digest, and `calibration_sha256` binds the canonical config bytes rather
  than trusting the human-readable id alone. Changing a cutoff, allowlist, source row, method/config
  bytes, semantic boundary, provenance, or seed creates a distinct identity. Same-id/same-bytes is
  idempotent; same-id/different-bytes raises before overwrite.
- The table stores canonical `manifest_json` and `results_json` plus indexed identity columns. It is
  a derived cache over the corpus and checked-in calibration, but old content-addressed cutoffs are
  retained so future-only validation can refer to exact discovery evidence.
- Reads degrade only for an absent table/run (`None`/empty tuple). Invalid JSON, schema drift, hash
  mismatch, or a noncanonical rewrite fails loudly. No `latest` convenience API may silently choose
  evidence for certification.
- The exported feature allowlist is a literal sorted tuple of typed paths such as
  `deck.mainboard`, `deck.sideboard`, `event.date`, `event.source`, `event.provenance`,
  `deck.parent_archetype`, `deck.pilot_key`, and semantic/version facts. It is not caller-extensible
  free text.

**Acceptance criteria**:

- [ ] One run persists and round-trips every manifest, segment, support diagnostic, distance,
  rejection, and candidate field with validated hashes.
- [ ] Identical reruns are idempotent; any same-id byte divergence is rejected and the first row
  remains intact.
- [ ] Outcome mutation/removal and post-cutoff corpus additions preserve run id and result digest;
  changing one allowed pre-cutoff fact changes the source/run identity.
- [ ] Earlier and later cutoff runs coexist, are selected only by exact id, and never overwrite one
  another.
- [ ] Empty fleets, thin references, and no-recurrence fleets persist explicit typed evidence rather
  than disappearing as missing rows.
- [ ] Later code can consume a `DiscoveryRun` without a source DB connection, while no discovery
  API accepts outcome-bearing inputs.

## Implementation order

1. `firewall-corpus` — establish the only admissible input and cutoff/config identity first.
2. `segments-fingerprints` — implement the pure statistical nomination layer against that closed
   input.
3. `candidate-ledger` — persist the complete immutable handoff only after the pure output is stable.

## Testing

### Unit tests

- Factory fixtures in `tests/analytics/eras/conftest.py` build extra-forbidden outcome-free decks,
  corpora, boundaries, calibrations, segments, and mixture cases with fixed dates and seeds.
- Source tests cover cutoff edges, parent-only semantics, board separation, canonical ordering,
  invalid calibration, and outcome-key rejection.
- Pure discovery tests cover known recurrence, main-only/side-only/mixture/field/source shifts, hard
  versus non-hard boundaries, complete-link anti-chaining, support floors, empty channels, and
  deterministic tie-breaking.
- Store tests cover DDL idempotence, immutable collision refusal, digest validation, missing-run
  honest nulls, and coexistence of multiple cutoffs.

### Integration tests

- An in-memory DuckDB corpus includes decks, cards, rounds, standings, and future events. Mutating or
  dropping outcome relations must leave discovery identical, while one allowed input mutation must
  change its identity.
- A historical cutoff run is captured, later events/cards are added, and the original run is rebuilt
  byte-identically to prove cutoff-safe vocabulary, segmentation, and fingerprints.
- An A→B→C synthetic history proves a returning A state is nominated across B, while a chained-only
  endpoint is refused by complete-link evidence.
- Focused `tests/analytics/eras/test_discovery*.py`, the existing era suite, Ruff, and compileall are
  required before the feature advances to review.

## Risks

- **Outcome leakage through a reused type or query:** the current `EntitySeries` already carries
  wins/losses, so a seemingly convenient reuse would invalidate discovery. **Fallback:** keep the
  dedicated extra-forbidden corpus, forbid connection access in the core, and make outcome-table
  removal/mutation an integration invariant.
- **Discovery thresholds are not equivalence margins:** the least-certain values are the first
  distance thresholds on sparse Legacy segments. **Fallback:** version them as conservative
  nomination-only calibration, persist all distances/near misses, allow certification to abstain,
  and change them only under a new id with future-only comparison.
- **Similar averages hide different deck mixtures:** pooled main/side shares can reunite two
  bimodal populations incorrectly. **Fallback:** require the deck-level mixture-energy channel and
  persist the exact deck membership/vector digest.
- **Event/pilot dependence inflates apparent support:** many decks can come from one event or a few
  repeated pilots. **Fallback:** gate discovery independently on distinct events and expose maximum
  event/pilot share; certification applies stronger effective-support/concentration rules.
- **Complete-link conservatism excludes a useful pocket:** the closest-first current group can reject
  a directly similar segment because it conflicts with another admitted history. **Fallback:**
  persist the direct-compatible comparison as `complete-link-conflict`; future challengers may test
  alternative state models without silently widening v1.
- **Taxonomy time travel is mislabeled:** reclassifying old decks with current rules is not what was
  known then. **Fallback:** bind taxonomy/legality versions and label the artifact as today's-model;
  as-known-then waits for dated reproducible inputs.
- **Large JSON rows become awkward:** exact segment evidence can grow with the corpus. **Fallback:**
  persist compact deck/event ids and vector digests now; normalize storage only after measured size
  warrants it, without changing the typed run contract.

## Other agent review

- Invoked because: the outcome firewall and statistical candidate contract are high-consequence.
- Skipped/degraded: a design-time advisory pass was not run because this worker is already the
  delegated autopilot endpoint and the caller explicitly forbids nested subagents or peeragent
  recursion. This is non-blocking under the advisory policy.
- Receiver judgment: research, code, and adversarial invariants support the typed-firewall design;
  the normal standard independent feature review remains required after implementation.

## Implementation summary

- Execution capability: delegated standard implementation owner carrying the three cohesive child
  checkpoints sequentially; no nested delegation was used.
- Review weight: standard from the project default; this feature is intentionally handed to the
  independent standard review lane at `stage: review`.
- Delivered outcome-free frozen models and a cutoff-bounded DuckDB adapter, deterministic weekly
  parent segmentation/fingerprints, board/mixture/field/source comparisons, hard-contract epochs,
  complete-link candidate nomination, and immutable content-addressed run/ledger handoff.
- Child checkpoints: `firewall-corpus` done, `segments-fingerprints` done, `candidate-ledger` done.
- Verification: `.venv/bin/pytest -q tests/analytics/eras/test_discovery*.py` — 11 passed;
  integrated era suite (`test_attribution`, `test_bocpd`, `test_detect`, `test_ensemble`,
  `test_run`, `test_series`, `test_store`, plus discovery tests) — 153 passed; `.venv/bin/python
  -m compileall -q src` — passed.
- Acceptance walk: the corpus models reject outcome/standing/conversion extras; source projection
  ignores outcome relations and future rows; board identity, field/source context, mixture vectors,
  support refusals, hard/non-hard contract distinctions, complete-link conflicts, exact manifest and
  result digests, idempotent retries, collision refusal, multiple cutoffs, and explicit degraded
  fleets are all covered by the focused/integrated tests.
- Simplifications/deviations: v1 segmentation is a deterministic weighted local PELT-style gain
  guard behind the versioned contract, with no mutable fit state; future-effective semantic
  boundaries are cutoff-filtered so they cannot perturb earlier identities. No unrelated files were
  changed; pre-existing `uv.lock` remains dirty and unstaged.
- Adjacent issues parked: none.
